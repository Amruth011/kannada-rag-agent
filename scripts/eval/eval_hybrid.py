import os
import sys
import pandas as pd
import json
from dotenv import load_dotenv

# Reconfigure stdout for UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.llms import llm_factory
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_huggingface import HuggingFaceEmbeddings
from ragas.run_config import RunConfig
from google import genai
from openai import OpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Kannada RAG pipeline imports
from rag_agent_v2 import _get_vs, retrieve_with_filter, retrieve_bm25, rerank_chunks, STANDARD_THRESHOLD, RERANK_TOP_N, get_rag_chain
from app import BOOK_CONTEXT

def run_retrieval(question, lang, use_hybrid=False):
    vs = _get_vs()
    
    # 1. Vector Search
    vector_chunks = retrieve_with_filter(
        query=question,
        vectorstore=vs,
        top_k=10,
        threshold=STANDARD_THRESHOLD
    )
    
    if use_hybrid:
        # 2. BM25 Search
        bm25_chunks = retrieve_bm25(query=question, top_k=10)
        
        # Merge and deduplicate
        merged_dict = {}
        for c in vector_chunks:
            merged_dict[c["text"]] = c
        for c in bm25_chunks:
            if c["text"] not in merged_dict:
                merged_dict[c["text"]] = c
        raw_chunks = list(merged_dict.values())
    else:
        raw_chunks = vector_chunks
        
    # Reranking
    if raw_chunks:
        chunks = rerank_chunks(question, raw_chunks, top_n=RERANK_TOP_N)
    else:
        chunks = []
        
    # Formatting Context
    if chunks:
        rag_section = "\n\n---\n\n".join(f"[Page {c['page']}]:\n{c['text']}" for c in chunks)
    else:
        rag_section = "Not found in database."
        
    # Generation
    chain = get_rag_chain(lang)
    answer = chain.invoke({
        "book_context": BOOK_CONTEXT,
        "context": rag_section,
        "history": [],
        "question": question
    })
    
    contexts = [c["text"] for c in chunks] if chunks else [rag_section]
    return answer, contexts

def main():
    load_dotenv()
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(base_dir, "data", "eval_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        return
        
    with open(dataset_path, "r", encoding="utf-8") as f:
        samples = json.load(f)
        
    print(f"Running Hybrid Search Evaluation on {len(samples)} samples...\n")
    
    vector_results = []
    hybrid_results = []
    
    for idx, sample in enumerate(samples):
        question = sample["question"]
        ground_truth = sample["ground_truth"]
        lang = sample.get("language", "English")
        
        print(f"[{idx+1}/{len(samples)}] Query: '{question}'")
        
        # 1. Vector Only
        ans_vec, ctx_vec = run_retrieval(question, lang, use_hybrid=False)
        vector_results.append({
            "question": question,
            "contexts": ctx_vec,
            "answer": ans_vec,
            "ground_truth": ground_truth
        })
        
        # Sleep to avoid rate limits
        import time
        time.sleep(8)
        
        # 2. Hybrid (Vector + BM25)
        ans_hyb, ctx_hyb = run_retrieval(question, lang, use_hybrid=True)
        hybrid_results.append({
            "question": question,
            "contexts": ctx_hyb,
            "answer": ans_hyb,
            "ground_truth": ground_truth
        })
        
        time.sleep(8)
        
    # Set up Ragas
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    
    if gemini_key:
        print("\nUsing Gemini for Ragas evaluation...")
        client = genai.Client(api_key=gemini_key)
        ragas_llm = llm_factory("gemini-flash-lite-latest", provider="google", client=client)
    elif groq_key:
        print("\nUsing Groq for Ragas evaluation...")
        openai_client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key)
        ragas_llm = llm_factory("llama-3.1-8b-instant", provider="openai", client=openai_client)
    else:
        print("Error: Neither API key found.")
        return
        
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    ragas_embeddings = LangchainEmbeddingsWrapper(embeddings)
    
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    for m in metrics:
        m.llm = ragas_llm
        if hasattr(m, "embeddings"):
            m.embeddings = ragas_embeddings
            
    run_config = RunConfig(max_workers=1, timeout=90)
    
    print("\n--- Evaluating Vector Search ---")
    ds_vec = Dataset.from_pandas(pd.DataFrame(vector_results))
    res_vec = evaluate(dataset=ds_vec, metrics=metrics, llm=ragas_llm, embeddings=ragas_embeddings, run_config=run_config)
    
    print("\n--- Evaluating Hybrid Search ---")
    ds_hyb = Dataset.from_pandas(pd.DataFrame(hybrid_results))
    res_hyb = evaluate(dataset=ds_hyb, metrics=metrics, llm=ragas_llm, embeddings=ragas_embeddings, run_config=run_config)
    
    print("\n=== RAGAS Comparison ===")
    
    report_path = os.path.join(base_dir, "hybrid_comparison_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Hybrid Retrieval Stats\n\n")
        f.write("Vector Chunks: 10\nBM25 Chunks: 10\nMerged Chunks: ~15\nReranked Chunks: 4\n\n")
        f.write("# RAGAS Comparison\n\n")
        
        for metric_name in ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]:
            val_vec = res_vec[metric_name] if metric_name in res_vec else 0
            val_hyb = res_hyb[metric_name] if metric_name in res_hyb else 0
            
            # Print to console
            print(f"{metric_name.replace('_', ' ').title()}:")
            print(f"{val_vec:.2f} → {val_hyb:.2f}\n")
            
            # Write to file
            f.write(f"**{metric_name.replace('_', ' ').title()}:**\n")
            f.write(f"{val_vec:.2f} &rarr; {val_hyb:.2f}\n\n")
            
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    main()
