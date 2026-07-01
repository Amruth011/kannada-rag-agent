# System Architecture

This document details the system design, routing logic, and retrieval flows for the Kannada RAG Agent.

## High-Level System Design

The architecture is built upon a **stateless Serverless/Edge API** communicating with a persistent vector database (ChromaDB) and an LLM API layer (Gemini / Groq).

1. **Frontend**: Streamlit or Next.js (interacting with the Vercel FastAPI backend).
2. **Backend**: FastAPI Serverless functions.
3. **Storage**: ChromaDB (Dense) + Local JSON/In-memory dictionary (Sparse/BM25).
4. **LLM Orchestrator**: Gemini 1.5 Flash (Primary) with Groq Llama 3 (Fallback).
5. **TTS Engine**: Sarvam API (Meera model) with Google TTS fallback.

## Query Routing Logic

To optimize context relevance and eliminate hallucination, queries pass through a deterministic router:

- **Metadata Routing**: If a query explicitly mentions "page [X]", the regex-based router bypasses semantic search entirely. It directly queries the local JSON dataset for the exact page contents.
- **Semantic Routing**: If the query is conversational or conceptual, the query is passed into the Hybrid Retrieval pipeline.

## Hybrid Retrieval Flow

1. **Sparse Retrieval (BM25)**: Evaluates the lexical overlap between the user query and chunked Kannada documents. Extremely effective for proper nouns and exact quotes.
2. **Dense Retrieval (ChromaDB)**: Evaluates the semantic cosine distance between the embedded query and chunk embeddings. Effective for conceptual questions and paraphrased intents.
3. **Reciprocal Rank Fusion (RRF)**: The results from both BM25 and Dense search are merged. RRF penalizes chunks that only perform well in one modality, surfacing chunks that are both semantically and lexically relevant.

## CrossEncoder Re-ranking Flow

The top-k chunks from the RRF output are passed to a Cross-Encoder (`cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`). 
- The Cross-Encoder scores the exact relationship between the Query and the Chunk.
- If the top chunk scores below a predefined threshold, the system triggers a **"Low Evidence Guardrail"**, refusing to hallucinate an answer.

## Memory Optimization Design

Due to the constraints of Serverless limits (Vercel 1024MB / Streamlit Cloud 1GB), the system employs aggressive memory optimizations:
- **Lazy Loading**: Cross-encoder models and heavy transformers are only loaded into memory during the execution phase and immediately cleared.
- **Generator Pipelines**: Document chunking and BM25 tokenization use generator functions rather than loading the entire corpus into lists.
- **Garbage Collection (GC)**: Explicit `gc.collect()` calls are placed after heavy matrix multiplications in the RRF phase.

## Deployment Architecture

- **Vercel API**: Hosts the FastAPI backend. Configured in `vercel.json` to handle chunked responses and extended timeouts.
- **Streamlit**: Operates as a thin client connecting to the Vercel API, maintaining chat state and rendering TTS audio blocks.
