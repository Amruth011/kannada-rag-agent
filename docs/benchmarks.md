# System Benchmarks

This document contains performance, latency, memory, and retrieval metrics for the Kannada RAG Agent.

## Latency Metrics

Tested on Vercel Serverless (iad1 region) and Streamlit Community Cloud.

| Component | P50 (ms) | P95 (ms) | Notes |
|-----------|----------|----------|-------|
| Query Routing | 5 | 12 | Regex evaluation |
| BM25 Retrieval | 120 | 250 | In-memory index |
| Dense Retrieval | 300 | 450 | ChromaDB querying |
| RRF + Reranking | 450 | 800 | CPU-bound CrossEncoder |
| LLM Generation | 1200 | 2500 | Gemini 1.5 Flash stream |
| Sarvam TTS | 800 | 2000 | TTFB (Time To First Byte) |
| **End-to-End** | **2.8s** | **5.0s** | Includes TTS chunking |

## Memory Profile

Memory usage is strictly monitored to prevent container crashes on 1GB RAM instances.

- **Baseline Idle**: ~120 MB
- **ChromaDB Init**: + 150 MB
- **BM25 Index Build**: + 80 MB
- **CrossEncoder Inference**: + 250 MB
- **Peak RAM Usage (During Heavy Load)**: ~ 600 MB (Safely below 1GB limit)
- **Garbage Collection**: Reclaims ~200 MB immediately post-reranking.

## Retrieval Metrics (RAGAS)

Automated benchmarks run on a golden dataset of 50 complex Kannada literary questions.

| Metric | Score (0-1) | Target Threshold |
|--------|-------------|------------------|
| Faithfulness | 0.92 | > 0.85 |
| Answer Relevancy | 0.88 | > 0.80 |
| Context Precision | 0.85 | > 0.75 |
| Context Recall | 0.89 | > 0.80 |

## Infrastructure Limits

- **Vercel Timeout**: Max 60 seconds (Pro Tier) / 10 seconds (Hobby).
- **Vercel Payload**: Max 4.5 MB response size.
- **Streamlit Timeout**: None (WebSocket based), but subject to 1GB RAM OOM kills.
