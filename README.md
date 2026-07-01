# Kannada RAG Agent & Voice Assistant

> **An enterprise-grade, memory-optimized Retrieval-Augmented Generation (RAG) agent specialized in Kannada literature and seamless voice synthesis.**

[![Vercel Deployment](https://img.shields.io/badge/Deployed_on-Vercel-black?logo=vercel)](https://heli-hogu-kaarana.vercel.app/)
[![Streamlit Cloud](https://img.shields.io/badge/Streamlit-Community_Cloud-FF4B4B?logo=streamlit)](#deployment)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Live Demo

🚀 **[Access the Vercel Production Deployment](https://heli-hogu-kaarana.vercel.app/)**

---

## Problem Statement

Interacting with complex, low-resource language literature (such as Kannada novels) requires high-accuracy contextual understanding that generic LLMs fail to provide due to token limits and language sparsity. Furthermore, rendering accurate Kannada text-to-speech for long-form narrative content requires dynamic chunking, real-time synthesis, and exact source-attribution. 

This project solves these challenges by combining state-of-the-art hybrid search (BM25 + Dense embeddings), Cross-Encoder reranking, and deterministic page-level metadata routing to ground the LLM precisely in the source material, effectively minimizing hallucinations.

---

## Enterprise Architecture

The architecture is built for high-throughput, accurate semantic retrieval, and low-latency rendering across both text and voice.

### Key Features
- ✓ **Hybrid Retrieval**: Combines semantic meaning with keyword relevance.
- ✓ **Dense Retrieval**: Utilizes highly optimized multilingual embedding vectors.
- ✓ **BM25**: Lexical, sparse retrieval for exact keyword matching.
- ✓ **Reciprocal Rank Fusion (RRF)**: Merges dense and sparse ranks intelligently.
- ✓ **Cross Encoder Re-ranking**: Final precision scoring over candidate chunks.
- ✓ **Metadata Routing**: Dynamically filters chunks based on extracted metadata.
- ✓ **Exact Page Retrieval**: Deterministic paths for explicit user queries.
- ✓ **ChromaDB**: Lightweight, memory-mapped vector storage.
- ✓ **OCR Pipeline**: High-accuracy Surya OCR for original document ingestion.
- ✓ **Gemini & Groq**: Dynamic fallback between models for high availability.
- ✓ **RAGAS Evaluation**: Automated CI/CD metrics for Answer Relevancy and Faithfulness.
- ✓ **Memory Optimization**: Batched query processing for constrained Vercel/Streamlit instances.

---

## Architecture Diagram

```mermaid
graph TD
    %% User Query Flow
    User((User)) -->|Input Query| QR[Query Router]
    
    %% Routing Logic
    QR -->|Regex Match| MR{Metadata Route?}
    
    %% Deterministic Path
    MR -->|Yes (Exact Page)| PR[Page Router / Exact Match]
    PR --> Context[Context Builder]
    
    %% Semantic Path
    MR -->|No (Semantic)| HS[Hybrid Search]
    
    %% Hybrid Search Components
    HS --> Dense[Dense Retrieval ChromaDB]
    HS --> Sparse[BM25 Lexical]
    
    Dense --> RRF[Reciprocal Rank Fusion]
    Sparse --> RRF
    
    RRF --> Rerank[CrossEncoder Reranker]
    Rerank --> Context
    
    %% Generation
    Context --> LLM{Gemini / Groq Fallback}
    LLM --> Response[Final Text Response]
    
    %% TTS
    Response --> TTS[Sarvam TTS / Google TTS]
    TTS --> User
```

---

## Retrieval Pipeline

1. **Ingestion**: Documents are chunked (semantic chunking) and embedded into ChromaDB. BM25 indexes are simultaneously created for lexical exact-matches.
2. **Querying**: The query is classified by the Router. If the user asks for a specific page, the system bypasses semantic search for absolute determinism.
3. **Hybrid Search**: For semantic queries, the system pulls top-k chunks from both ChromaDB and BM25.
4. **RRF & Reranking**: Reciprocal Rank Fusion aligns the results, and a robust Cross-Encoder assigns the ultimate relevancy scores.
5. **Generation**: The highest-confidence contexts are passed to the Gemini-based LLM. If confidence is beneath the established threshold, an automated guardrail prevents hallucination.

---

## Evaluation Results

Evaluated rigorously using the **RAGAS** framework across a benchmark dataset.

- **Faithfulness**: `0.92`
- **Answer Relevancy**: `0.88`
- **Context Precision**: `0.85`
- **Context Recall**: `0.89`

See the detailed evaluations in `docs/evaluation.md`.

---

## Benchmarks

- **Latency (P95)**: < 1.2s for end-to-end text retrieval and generation.
- **Memory**: Optimized to consume < 250MB RAM during heavy RRF operations.
- **Voice TTS Generation**: Parallel chunking ensures continuous audio playback with < 2.5s initial TTFB (Time To First Byte).

See detailed memory footprints and latency testing in `docs/benchmarks.md`.

---

## Repository Structure

```text
.
├── api/                  # Vercel Serverless API
├── assets/               # Public UI and brand assets
├── chroma_db/            # Persistent Vector Database
├── data/                 # Raw and processed JSON corpus
├── docs/                 # Enterprise documentation
│   ├── architecture.md
│   ├── benchmarks.md
│   ├── deployment.md
│   ├── evaluation.md
│   └── archive/          # Historical audits and legacy docs
├── scripts/              # Independent tooling
│   ├── ingest/           # OCR and ChromaDB ingestion pipeline
│   ├── eval/             # RAGAS evaluation scripts
│   └── utils/            # Debugging and validation tools
├── app.py                # Streamlit Application Entrypoint
└── vercel.json           # Vercel Configuration
```

---

## Deployment

### Vercel Serverless (Recommended)
This repository is optimized for Vercel's Edge/Serverless functions. 
1. Link your GitHub repository in the Vercel dashboard.
2. Set the Environment Variables (`GEMINI_API_KEY`, `GROQ_API_KEY`, `SARVAM_API_KEY`).
3. Deploy.

### Streamlit Community Cloud
1. Deploy via Streamlit.
2. Add dependencies required in `packages.txt` (`libgl1`, `libglib2.0-0`, `poppler-utils`).
3. Set your Streamlit Secrets.

For detailed local, Docker, and cloud deployments, see `docs/deployment.md`.

---

## Screenshots

*(Coming Soon - Refer to `docs/assets/` for UI diagrams)*

---

## Roadmap

- [ ] Multi-document vector clustering.
- [ ] Implement self-reflection evaluation (Agentic RAG).
- [ ] Full local offline-first fallback using Llama.cpp.
- [ ] Enterprise SSO and Auth integration.

---

## License

This project is licensed under the [MIT License](LICENSE).
