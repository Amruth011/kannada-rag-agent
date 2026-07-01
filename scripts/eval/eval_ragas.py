import os
import sys
import re
import json
import pandas as pd
import traceback
from dotenv import load_dotenv

# Reconfigure stdout for UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from datasets import Dataset

# Ragas imports
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas.llms import llm_factory
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_huggingface import HuggingFaceEmbeddings
from ragas.run_config import RunConfig
from google import genai
from openai import OpenAI

# Kannada RAG pipeline imports
from rag_agent_v2 import retrieve_v2, detect_page_filter, get_rag_chain

BOOK_CONTEXT = """
Book Title  : ಹೇಳಿ ಹೋಗು ಕಾರಣ (Heli Hogu Karana — "Tell the reason before you go")
Author      : ರವಿ ಬೆಳಗೆರೆ (Ravi Belagere) — prominent Kannada journalist, Bengaluru
Publisher   : Bhavana Prakashan, Bengaluru
Language    : Kannada | Genre: Novel | Pages: 346

Theme: Human morality, guilt, truth-telling, divine justice, moral accountability,
       existential questioning, social critique.
Style: Bold journalistic prose, episodic structure, multiple philosophical perspectives.

Known characters: ಹಿಮವಂತ (Himavant) is the main protagonist. ಪ್ರಾರ್ಥನಾ (Prarthana) is his wife.
"""

GENERAL_PATTERNS = [
    r'what is (this|the) book', r'about (this|the) book',
    r'book (about|summary|theme)', r'who (is|wrote|is the author).*ravi',
    r'ravi belagere', r'author', r'ಪುಸ್ತಕ(ದ|ವು|ದ ಬಗ್ಗೆ)', r'ಕಾದಂಬರಿ',
    r'ರವಿ ಬೆಳಗೆರೆ', r'ವಿಷಯ ಏನು', r'ಯಾರು ಬರೆದ', r'ಮುಖ್ಯ ವಿಷಯ',
    r'summary', r'theme', r'title mean', r'ಶೀರ್ಷಿಕೆ',
]

CHARACTER_PATTERNS = [
    r'himavant|prarthana|ಹಿಮವಂತ|ಪ್ರಾರ್ಥನಾ',
    r'who is|character|ಪಾತ್ರ|personality|hero|heroine',
]

def is_general_question(q):
    return any(re.search(p, q, re.IGNORECASE) for p in GENERAL_PATTERNS)

def is_character_question(q):
    return any(re.search(p, q, re.IGNORECASE) for p in CHARACTER_PATTERNS)

def main():
    load_dotenv()
    
    # 1. Load evaluation dataset
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(base_dir, "data", "eval_dataset.json")
    if not os.path.exists(dataset_path):
        print(f"Error: Dataset not found at {dataset_path}")
        return
        
    with open(dataset_path, "r", encoding="utf-8") as f:
        samples = json.load(f)
        
    print(f"Loaded {len(samples)} evaluation samples.")
    
    # 2. Run questions through RAG pipeline to gather responses and contexts
    eval_data = []
    
    for idx, sample in enumerate(samples):
        question = sample["question"]
        ground_truth = sample["ground_truth"]
        lang = sample.get("language", "English")
        
        print(f"[{idx+1}/{len(samples)}] Executing question: '{question}' ({lang})...")
        
        # Detect page filters and question type
        page, page_range = detect_page_filter(question)
        is_char = is_character_question(question)
        is_general = is_general_question(question)
        
        # Retrieval
        if is_general:
            chunks = []
            rag_section = "General question — answered from general book knowledge."
        else:
            chunks, _, _ = retrieve_v2(question, page=page, page_range=page_range, is_character=is_char, language=lang)
            if chunks:
                rag_section = "\n\n---\n\n".join(f"[Page {c['page']}]:\n{c['text']}" for c in chunks)
            else:
                rag_section = "Not found in database."
                
        # Generate Answer using fallback chain
        chain = get_rag_chain(lang)
        answer = chain.invoke({
            "book_context": BOOK_CONTEXT,
            "context": rag_section,
            "history": [],
            "question": question
        })
        
        print(f"Generated Answer:\n{answer}\n")
        
        # Sleep to avoid Groq/Gemini rate limits during RAG answer generation
        import time
        time.sleep(12)
        
        # Collect contexts
        contexts = [c["text"] for c in chunks] if chunks else [rag_section]
        
        eval_data.append({
            "question": question,
            "contexts": contexts,
            "answer": answer,
            "ground_truth": ground_truth
        })
        
    # Create HuggingFace Dataset
    dataset = Dataset.from_pandas(pd.DataFrame(eval_data))
    
    # 3. Configure Ragas with Gemini or Groq
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    
    if gemini_key:
        print("Using Gemini (gemini-flash-lite-latest) for Ragas evaluation...")
        client = genai.Client(api_key=gemini_key)
        ragas_llm = llm_factory("gemini-flash-lite-latest", provider="google", client=client)
    elif groq_key:
        print("Using Groq (llama-3.1-8b-instant) for Ragas evaluation...")
        openai_client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key)
        ragas_llm = llm_factory("llama-3.1-8b-instant", provider="openai", client=openai_client)
    else:
        print("Error: Neither GEMINI_API_KEY nor GROQ_API_KEY found in environment.")
        return
        
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    ragas_embeddings = LangchainEmbeddingsWrapper(embeddings)
    
    # Setup metrics with custom llm/embeddings
    metrics = [
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    ]
    
    # Configure metrics
    for m in metrics:
        m.llm = ragas_llm
        if hasattr(m, "embeddings"):
            m.embeddings = ragas_embeddings
            
    print("Running Ragas evaluation...")
    run_config = RunConfig(max_workers=1, timeout=90)
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=ragas_llm,
        embeddings=ragas_embeddings,
        run_config=run_config
    )
    
    print("\n=== Evaluation Results ===")
    print(result)
    
    # 4. Save results to CSV and JSON
    df_results = result.to_pandas()
    csv_path = os.path.join(base_dir, "eval_results.csv")
    json_path = os.path.join(base_dir, "eval_results.json")
    
    df_results.to_csv(csv_path, index=False)
    df_results.to_json(json_path, orient="records", indent=2)
    print(f"Results saved to:\n- {csv_path}\n- {json_path}")
    
    # 5. Generate aggregate metrics & human-readable report
    scores = {
        "faithfulness": df_results["faithfulness"].mean() if "faithfulness" in df_results.columns else 0.0,
        "answer_relevancy": df_results["answer_relevancy"].mean() if "answer_relevancy" in df_results.columns else 0.0,
        "context_precision": df_results["context_precision"].mean() if "context_precision" in df_results.columns else 0.0,
        "context_recall": df_results["context_recall"].mean() if "context_recall" in df_results.columns else 0.0,
    }
    
    overall_score = sum(scores.values()) / len(scores)
    
    report = f"""## RAG Evaluation Report

Faithfulness: {scores['faithfulness']*100:.0f}%
Answer Relevancy: {scores['answer_relevancy']*100:.0f}%
Context Precision: {scores['context_precision']*100:.0f}%
Context Recall: {scores['context_recall']*100:.0f}%

Overall Quality Score: {overall_score*100:.0f}%
"""
    
    report_path = os.path.join(base_dir, "eval_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Report saved to: {report_path}")
    print("\n" + report)

if __name__ == "__main__":
    main()
