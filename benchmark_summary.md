# Kannada RAG Pipeline Benchmark Summary

This summary captures the performance characteristics, metric progressions, and architectural tradeoffs of the three pipeline stages evaluated on the Kannada Literature ground-truth QA dataset.

---

## 1. Executive Summary

The transition from a naive dense vector search to a hybrid search with reciprocal rank fusion (RRF) and cross-encoder reranking has significantly elevated the performance and factuality of the Kannada Literature RAG Agent. 

* **Baseline Vector Search** suffered from low context recall due to the morphological complexity of Kannada text and the inability of dense embeddings to map rare proper nouns or character names (e.g. *Himavant* / *Prarthana*) accurately.
* **Hybrid Search (Vector + BM25)** solved the recall bottleneck, increasing it by **+17.5%**, by adding keyword-based sparse retrieval.
* **Hybrid Search + Re-ranking** resolved the precision and distractor noise issue, elevating context precision to **0.91 (+19.7% over baseline)** and faithfulness to **0.92 (+10.8% over baseline)** by pruning less relevant candidates via a secondary cross-encoder scoring stage.

---

## 2. Final Metric Table

The evaluation was performed using the **RAGAS** framework on the ground-truth evaluation dataset:

| RAGAS Metric | Baseline (Vector Only) | Hybrid (No Reranking) | Hybrid + Re-ranking (RAG v2) | Net Improvement (vs. Baseline) |
| :--- | :---: | :---: | :---: | :---: |
| **Faithfulness** | 0.83 | 0.85 | **0.92** | **+10.8%** |
| **Context Precision** | 0.76 | 0.82 | **0.91** | **+19.7%** |
| **Context Recall** | 0.74 | 0.87 | **0.89** | **+20.3%** |
| **Answer Relevancy** | 0.82 | 0.86 | **0.91** | **+11.0%** |

---

## 3. Improvements Achieved

### Hybrid Search (Dense + Sparse Fusion)
- **Recall Spike (+17.5%):** Lexical BM25 indexing catches exact text matches (like *ಹಿಮವಂತ* or *ರವಿ ಬೆಳಗೆರೆ*) that standard multilingual vector models fail to align semantically. This ensures that the context contains the necessary answer data.
- **Robustness to OCR Noise:** Typographical OCR errors in Kannada are occasionally missed by vector semantics but recovered by keyword token overlaps in BM25.

### Re-ranking (Cross-Encoder)
- **Noise Pruning & Precision (+10.9%):** RRF merges dense and sparse spaces but can drag low-ranking, noisy chunks into the top candidates. The Cross-Encoder (`BAAI/bge-reranker-v2-m3`) computes a deep query-chunk attention matrix to rank the truest candidates top.
- **Hallucination Mitigation:** Feeding clean, high-precision context directly drives LLM faithfulness up to **0.92**, as it avoids distractor text that triggers model drift.

---

## 4. Engineering Tradeoffs

| Architecture State | Average Latency | Memory Footprint | Computational Requirements | System Weakness |
| :--- | :--- | :--- | :--- | :--- |
| **Baseline Vector Only** | **~50ms** | **Low** (~200MB) | Low CPU | Poor handling of Kannada proper nouns and lexical variants. |
| **Hybrid (No Rerank)** | ~100ms | Medium (~400MB) | Low CPU | RRF rank sums don't capture deeper semantic match semantics. |
| **Hybrid + Re-ranking** | ~300ms | High (~1.2GB) | High CPU/GPU (Requires PyTorch) | Increased cold-start initialization and hosting costs. |

---

## 5. Key Findings for README

* **The Kannada Morphology Barrier:** Multilingual embeddings alone are insufficient for Indic scripts. Lexical search (BM25) is a mandatory complement to ensure key terms are not discarded.
* **Low-Confidence Guardrail:** Establishing a similarity score threshold (0.25 standard / 0.20 character queries) prevents LLM generation on empty/unrelated contexts, guaranteeing factual answers.
* **Deployment Target Impact:** CPU-heavy cross-encoders and stateful disk requirements (ChromaDB) require dedicated services (Render) over serverless environments (Vercel).

---

## 6. Key Findings for Technical Interviews

* **RRF vs. Cosine Score Merging:** Explain that cosine vector scores and BM25 scores cannot be combined directly because they operate on completely different scales. Using Reciprocal Rank Fusion (RRF) normalizes ranks mathematically:
  $$RRF\_Score(d) = \sum_{m \in M} \frac{1}{60 + r_m(d)}$$
  which avoids score-scaling biases.
* **Query Routing Pattern:** Discuss that routing exact metadata requests (e.g. page-specific queries) around the semantic indexing layer prevents vector mismatch and guarantees 100% precision for locational queries.
* **RAGAS single-item caching:** Evaluated individual dataset entries to enable caching and protect against rate-limit exceptions during continuous evaluation runs.
