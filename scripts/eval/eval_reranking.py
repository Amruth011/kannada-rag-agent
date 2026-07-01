"""
eval_reranking.py — Before vs After Re-ranking Comparison
==========================================================
Runs the evaluation dataset through two pipelines:
  1. Baseline  : ChromaDB top-5 only (no cross-encoder reranking)
  2. Reranked  : ChromaDB top-15 -> BAAI/bge-reranker-v2-m3 -> top-4

Computes RAGAS metrics for both and writes a comparison report.
"""

import os
import json
import time
import pandas as pd
from datasets import Dataset
from dotenv import load_dotenv

load_dotenv()

# -- RAGAS ---------------------------------------------------------------------
from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from ragas import evaluate
from ragas.llms import llm_factory
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_huggingface import HuggingFaceEmbeddings
from openai import OpenAI
from google import genai

# -- RAG pipeline --------------------------------------------------------------
from rag_agent_v2 import (
    retrieve_v2, detect_page_filter, get_rag_chain,
    RERANK_FETCH_K, RERANK_TOP_N,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BOOK_CONTEXT = """
Book Title  : Heli Hogu Karana
Author      : Ravi Belagere
Language    : Kannada | Genre: Novel | Pages: 346
Known characters: Himavant is the main protagonist. Prarthana is his wife.
"""

EVAL_FILE = os.path.join(BASE_DIR, "evaluation_dataset.json")


# -- Load evaluation dataset ---------------------------------------------------
def load_eval_dataset():
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    samples = []
    for item in raw:
        q  = item.get("question", "")
        gt = item.get("ground_truth", item.get("answer", ""))
        lang = item.get("language", "English")
        if q and gt:
            samples.append({"question": q, "ground_truth": gt, "language": lang})
    print(f"Loaded {len(samples)} evaluation samples.")
    return samples


# -- Run one pipeline pass -----------------------------------------------------
def run_pipeline(samples: list, use_reranking: bool) -> list:
    label = "WITH reranking" if use_reranking else "WITHOUT reranking (baseline)"
    print(f"\n{'='*60}")
    print(f"  Running pipeline: {label}")
    print(f"{'='*60}")

    eval_data = []
    for i, sample in enumerate(samples):
        question     = sample["question"]
        ground_truth = sample["ground_truth"]
        lang         = sample["language"]

        print(f"\n[{i+1}/{len(samples)}] {question!r} ({lang})...")

        page, page_range = detect_page_filter(question)

        chunks, fallback_msg, meta = retrieve_v2(
            query        = question,
            page         = page,
            page_range   = page_range,
            language     = lang,
            use_reranking= use_reranking,
        )

        if use_reranking:
            print(f"  Fetched: {meta['fetched']}  ->  After rerank: {meta['final']}")
        else:
            print(f"  Fetched: {meta['fetched']}  (no reranking)")

        rag_section = (
            "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks])
            if chunks else fallback_msg or "(No passages found.)"
        )

        chain  = get_rag_chain(lang)
        answer = chain.invoke({
            "book_context": BOOK_CONTEXT,
            "context"     : rag_section,
            "history"     : [],
            "question"    : question,
        })
        print(f"  Answer: {answer[:100]}...")

        contexts = [c["text"] for c in chunks] if chunks else [rag_section]

        eval_data.append({
            "question"    : question,
            "contexts"    : contexts,
            "answer"      : answer,
            "ground_truth": ground_truth,
        })

        time.sleep(12)

    return eval_data


# -- Configure RAGAS LLM -------------------------------------------------------
def build_ragas_llm():
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    groq_key   = os.getenv("GROQ_API_KEY", "").strip()

    if gemini_key:
        print("\nUsing Gemini (gemini-flash-lite-latest) for Ragas evaluation...")
        client = genai.Client(api_key=gemini_key)
        return llm_factory("gemini-flash-lite-latest", provider="google", client=client)
    elif groq_key:
        print("\nUsing Groq (llama-3.1-8b-instant) for Ragas evaluation...")
        oc = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=groq_key)
        return llm_factory("llama-3.1-8b-instant", provider="openai", client=oc)
    else:
        raise ValueError("Neither GEMINI_API_KEY nor GROQ_API_KEY set in environment.")


# -- Run RAGAS evaluation ------------------------------------------------------
def run_ragas(eval_data: list, ragas_llm, ragas_embeddings) -> dict:
    dataset = Dataset.from_pandas(pd.DataFrame(eval_data))
    result  = evaluate(
        dataset,
        metrics      = [faithfulness, answer_relevancy, context_precision, context_recall],
        llm          = ragas_llm,
        embeddings   = ragas_embeddings,
        raise_exceptions=False,
    )
    return {
        "faithfulness"      : round(result["faithfulness"], 4),
        "answer_relevancy"  : round(result["answer_relevancy"], 4),
        "context_precision" : round(result["context_precision"], 4),
        "context_recall"    : round(result["context_recall"], 4),
    }


# -- Generate comparison report ------------------------------------------------
def write_report(baseline: dict, reranked: dict):
    def pct(v):
        return f"{v*100:.1f}%" if isinstance(v, float) else "N/A"

    def delta(b, r):
        if not isinstance(b, float) or not isinstance(r, float):
            return ""
        diff = (r - b) * 100
        arrow = "up" if diff >= 0 else "down"
        sign  = "+" if diff >= 0 else "-"
        return f"{sign}{abs(diff):.1f}% ({arrow})"

    report = f"""# Re-Ranking Evaluation Comparison Report

## Configuration
- Baseline : ChromaDB top-{RERANK_TOP_N} (no cross-encoder)
- Reranked : ChromaDB top-{RERANK_FETCH_K} -> BAAI/bge-reranker-v2-m3 -> top-{RERANK_TOP_N}

## Results

| Metric             | Baseline | Reranked | Change |
|--------------------|----------|----------|--------|
| Faithfulness       | {pct(baseline['faithfulness'])} | {pct(reranked['faithfulness'])} | {delta(baseline['faithfulness'], reranked['faithfulness'])} |
| Answer Relevancy   | {pct(baseline['answer_relevancy'])} | {pct(reranked['answer_relevancy'])} | {delta(baseline['answer_relevancy'], reranked['answer_relevancy'])} |
| Context Precision  | {pct(baseline['context_precision'])} | {pct(reranked['context_precision'])} | {delta(baseline['context_precision'], reranked['context_precision'])} |
| Context Recall     | {pct(baseline['context_recall'])} | {pct(reranked['context_recall'])} | {delta(baseline['context_recall'], reranked['context_recall'])} |

## What Each Metric Means
- Faithfulness: % of answer claims grounded in retrieved context.
- Answer Relevancy: How well answers match the questions.
- Context Precision: % of retrieved chunks that are truly relevant.
- Context Recall: % of ground-truth info covered by retrieved chunks.

## Conclusion
Re-ranking with BAAI/bge-reranker-v2-m3 narrows {RERANK_FETCH_K} retrieved chunks
down to {RERANK_TOP_N}, selecting only the most query-relevant passages.
A higher Context Precision delta indicates the reranker is filtering noise effectively.
"""

    report_path = os.path.join(BASE_DIR, "reranking_comparison_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nComparison report saved: {report_path}")
    print(report)


# -- Main ----------------------------------------------------------------------
def main():
    samples = load_eval_dataset()

    ragas_llm = build_ragas_llm()
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    ragas_embeddings = LangchainEmbeddingsWrapper(embeddings)

    # Baseline (no reranking)
    baseline_data = run_pipeline(samples, use_reranking=False)
    print("\nRunning RAGAS on baseline...")
    baseline_scores = run_ragas(baseline_data, ragas_llm, ragas_embeddings)
    print(f"Baseline scores: {baseline_scores}")

    time.sleep(30)

    # Reranked
    reranked_data = run_pipeline(samples, use_reranking=True)
    print("\nRunning RAGAS on reranked results...")
    reranked_scores = run_ragas(reranked_data, ragas_llm, ragas_embeddings)
    print(f"Reranked scores: {reranked_scores}")

    results_path = os.path.join(BASE_DIR, "reranking_eval_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "baseline": baseline_scores,
            "reranked": reranked_scores,
        }, f, ensure_ascii=False, indent=2)
    print(f"Raw results saved: {results_path}")

    write_report(baseline_scores, reranked_scores)


if __name__ == "__main__":
    main()
