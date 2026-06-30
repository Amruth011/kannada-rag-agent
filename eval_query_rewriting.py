import os
import sys
import re
import pandas as pd
from dotenv import load_dotenv

# Reconfigure stdout for UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from datasets import Dataset

# Ragas imports
from ragas import evaluate
from ragas.metrics import faithfulness, context_precision, context_recall
from ragas.llms import llm_factory
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_huggingface import HuggingFaceEmbeddings
from ragas.run_config import RunConfig
from google import genai
from openai import OpenAI

# Kannada RAG pipeline imports
from rag_agent_v2 import retrieve_v2, detect_page_filter, get_rag_chain
from app import rewrite_query, BOOK_CONTEXT

# Dummy dataset for query rewriting evaluation
# The history provided leads to the ambiguous question.
EVAL_DATASET = [
    {
        "history": [
            {"role": "user", "content": "Who is Prarthana?"},
            {"role": "assistant", "content": "Prarthana is Himavant's wife."}
        ],
        "question": "What happened to her?",
        "ground_truth": "Prarthana faced struggles in her marriage with Himavant.",
        "language": "English"
    },
    {
        "history": [
            {"role": "user", "content": "Who is Himavant?"},
            {"role": "assistant", "content": "Himavant is the main protagonist of the novel."}
        ],
        "question": "Tell me more about him.",
        "ground_truth": "Himavant is a complex character grappling with moral and existential questions throughout the novel.",
        "language": "English"
    },
    {
        "history": [
            {"role": "user", "content": "What is the novel about?"},
            {"role": "assistant", "content": "The novel explores themes of morality and truth-telling."}
        ],
        "question": "Who wrote it?",
        "ground_truth": "The novel was written by Ravi Belagere.",
        "language": "English"
    }
]

def run_pipeline(question, history, lang):
    page, page_range = detect_page_filter(question)
    chunks, _ = retrieve_v2(question, page=page, page_range=page_range, is_character=False, language=lang)
    if chunks:
        rag_section = "\n\n---\n\n".join(f"[Page {c['page']}]:\n{c['text']}" for c in chunks)
    else:
        rag_section = "Not found in database."
        
    chain = get_rag_chain(lang)
    # Convert history dicts to Langchain Messages
    from langchain_core.messages import HumanMessage, AIMessage
    lc_history = []
    for msg in history:
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=msg["content"]))
        else:
            lc_history.append(AIMessage(content=msg["content"]))

    answer = chain.invoke({
        "book_context": BOOK_CONTEXT,
        "context": rag_section,
        "history": lc_history,
        "question": question
    })
    
    contexts = [c["text"] for c in chunks] if chunks else [rag_section]
    return answer, contexts

def main():
    load_dotenv()
    
    print(f"Running Query Rewriting Evaluation on {len(EVAL_DATASET)} samples...\n")
    
    original_results = []
    rewritten_results = []
    
    for idx, sample in enumerate(EVAL_DATASET):
        original_q = sample["question"]
        history = sample["history"]
        lang = sample["language"]
        ground_truth = sample["ground_truth"]
        
        print(f"[{idx+1}/{len(EVAL_DATASET)}] Original Question: '{original_q}'")
        
        # 1. Run WITHOUT Rewriting
        ans_orig, ctx_orig = run_pipeline(original_q, history, lang)
        original_results.append({
            "question": original_q,
            "contexts": ctx_orig,
            "answer": ans_orig,
            "ground_truth": ground_truth
        })
        
        # Sleep to avoid rate limits
        import time
        time.sleep(12)
        
        # 2. Rewrite Query
        rewritten_q = rewrite_query(original_q, history)
        print(f"Rewritten Query: '{rewritten_q}'")
        
        # 3. Run WITH Rewriting
        ans_rewritten, ctx_rewritten = run_pipeline(rewritten_q, history, lang)
        rewritten_results.append({
            "question": rewritten_q, # Must be rewritten query
            "contexts": ctx_rewritten,
            "answer": ans_rewritten,
            "ground_truth": ground_truth
        })
        
        time.sleep(12)
        
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
        print("Error: Neither GEMINI_API_KEY nor GROQ_API_KEY found in environment.")
        return
        
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    ragas_embeddings = LangchainEmbeddingsWrapper(embeddings)
    
    metrics = [faithfulness, context_precision, context_recall]
    for m in metrics:
        m.llm = ragas_llm
        if hasattr(m, "embeddings"):
            m.embeddings = ragas_embeddings
            
    run_config = RunConfig(max_workers=1, timeout=90)
    
    print("\n--- Evaluating Original Queries ---")
    ds_orig = Dataset.from_pandas(pd.DataFrame(original_results))
    res_orig = evaluate(dataset=ds_orig, metrics=metrics, llm=ragas_llm, embeddings=ragas_embeddings, run_config=run_config)
    
    print("\n--- Evaluating Rewritten Queries ---")
    ds_rewritten = Dataset.from_pandas(pd.DataFrame(rewritten_results))
    res_rewritten = evaluate(dataset=ds_rewritten, metrics=metrics, llm=ragas_llm, embeddings=ragas_embeddings, run_config=run_config)
    
    print("\n=== Comparison Report ===")
    print("Metrics | Without Rewriting | With Rewriting")
    print("--- | --- | ---")
    for metric_name in ["faithfulness", "context_precision", "context_recall"]:
        val_orig = res_orig[metric_name] if metric_name in res_orig else 0
        val_rewritten = res_rewritten[metric_name] if metric_name in res_rewritten else 0
        print(f"{metric_name.replace('_', ' ').title()} | {val_orig:.4f} | {val_rewritten:.4f}")
        
    # Save report
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_rewriting_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Query Rewriting Evaluation\n\n")
        f.write("Metrics | Without Rewriting | With Rewriting\n")
        f.write("--- | --- | ---\n")
        for metric_name in ["faithfulness", "context_precision", "context_recall"]:
            val_orig = res_orig[metric_name] if metric_name in res_orig else 0
            val_rewritten = res_rewritten[metric_name] if metric_name in res_rewritten else 0
            f.write(f"{metric_name.replace('_', ' ').title()} | {val_orig:.4f} | {val_rewritten:.4f}\n")
            
    print(f"\nReport saved to: {report_path}")

if __name__ == "__main__":
    main()
