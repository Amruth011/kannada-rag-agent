# System Architecture - Kannada RAG Agent

This document details the system architecture of the Kannada Literature RAG (Retrieval-Augmented Generation) Agent, covering both the offline document ingestion pipeline and the online query execution pipeline.

---

## 1. Document Ingestion (Offline Pipeline)

The document ingestion pipeline processes physical/scanned Kannada literature (PDFs) and prepares them for semantic retrieval.

```
Scanned PDF Document
        │
        ▼
┌─────────────────────────┐
│   OpenCV Preprocessing  │  <-- Denoising, contrast adjustment, skew correction
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│        Surya OCR        │  <-- Specialized layout analysis & Kannada text detection
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Unicode Normalization  │  <-- Resolving zero-width joiner anomalies & Indic font issues
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│    Semantic Chunking    │  <-- Decoupling page boundaries into contextual text segments
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Multilingual Embeddings │  <-- paraphrase-multilingual-MiniLM-L12-v2 (384-dim)
└───────────┬─────────────┘
            │
            ▼
 ┌───────────────────────┐
 │   Chroma DB Vector    │  <-- Metadata attached: exact page numbers, token count
 └───────────────────────┘
```

### Ingestion Components:
1. **OpenCV Preprocessing (`preprocess_images.py`):** Converts PDF pages to high-resolution PNG images. Applies bilateral filtering for denoising and adaptive thresholding to maximize character contrast.
2. **Surya OCR (`ocr_surya.py`):** A line-level OCR model used to extract native Kannada text. Handles complex columns and keeps structural layouts intact.
3. **Unicode Normalization (`clean_text.py`):** Replaces broken ZWJ (Zero Width Joiners) and ZWNJ sequences. Normalizes Kannada unicode glyphs to ensure consistent text matching.
4. **Semantic Chunker & Metadata Tracker (`chunker.py`):** Divides the parsed text into sliding window chunks while maintaining a hard mapping back to the source PDF page numbers.

---

## 2. Query Execution (Online Pipeline)

The online query flow evaluates user prompts, dynamically determines the retrieval path, fetches context, applies safety guardrails, queries the LLMs, and synthesizes audio.

```
                 User Question / Prompt
                           │
                           ▼
             ┌───────────────────────────┐
             │  Intelligent Query Router │
             └─────────────┬─────────────┘
                           │
             ┌─────────────┴─────────────┐
             │                           │
    [Page Query Detected]        [General Query]
             │                           │
             ▼                           ▼
 ┌───────────────────────┐   ┌───────────────────────┐
 │  Exact Page Filter    │   │    Query Rewriting    │ <-- Contextualized with Chat History
 └───────────┬───────────┘   └───────────┬───────────┘
             │                           │
             ▼                           ▼
 ┌───────────────────────┐   ┌───────────────────────┐
 │  Chroma Metadata      │   │     Hybrid Search     │
 │  Retrieval            │   │ (Chroma Vector + BM25)│
 └───────────┬───────────┘   └───────────┬───────────┘
             │                           │
             │                           ▼
             │               ┌───────────────────────┐
             │               │    RRF Rank Fusion    │ <-- Merges vector and keyword spaces
             │               └───────────┬───────────┘
             │                           │
             │                           ▼
             │               ┌───────────────────────┐
             │               │ Cross-Encoder Rerank  │ <-- BAAI/bge-reranker-v2-m3
             │               └───────────┬───────────┘
             │                           │
             └─────────────┬─────────────┘
                           │
                           ▼
             ┌───────────────────────────┐
             │    Similarity Guardrails  │ <-- Verifies if chunk score exceeds threshold
             └─────────────┬─────────────┘
                           │
                           ▼
             ┌───────────────────────────┐
             │      Bilingual Prompt     │
             └─────────────┬─────────────┘
                           │
                           ▼
             ┌───────────────────────────┐
             │   Gemini 1.5 Pro / Flash  │
             └─────────────┬─────────────┘
                           │ (Fallback)
                           ▼
             ┌───────────────────────────┐
             │  Groq (Llama 3) Fallback  │
             └─────────────┬─────────────┘
                           │
                           ▼
             ┌───────────────────────────┐
             │ Confidence Score & Sources│ <-- Appends Citations, Chunks, and UI Labels
             └─────────────┬─────────────┘
                           │
                           ▼
             ┌───────────────────────────┐
             │      Sarvam TTS Engine    │ <-- Speaks Kannada responses
             └─────────────┬─────────────┘
                           │ (Fallback)
                           ▼
             ┌───────────────────────────┐
             │       gTTS Fallback       │
             └───────────────────────────┘
```

### Retrieval & Generation Components:
- **Intelligent Query Router:** Uses regex and rule-based heuristics (e.g., "Page 10", "ಪುಟ 25") to classify the request.
  - **Path A (Exact Page):** Bypasses vector index. Directly queries Chroma using metadata schema filters (e.g., `{"page": 42}`).
  - **Path B (Semantic):** Rewrites query via LLM using context history (e.g., resolving "who did he fight?"). Conducts dense retrieval (Chroma Cosine) and sparse retrieval (BM25), combining ranks mathematically via Reciprocal Rank Fusion (RRF). Passes candidates to a Cross-Encoder to compute a precise final score.
- **Guardrails:** Under the semantic path, if the highest reranked chunk score falls below `0.25` (or `0.20` for entity/character lookups), the system terminates RAG and returns a localized "Not Found" message to prevent hallucinations.
- **Fallback LLM Engine:** Utilizes Google Gemini API. In case of API quota depletion, request timeouts, or failures, a fallback handler catches the exception and routes the request to Groq (Llama-3-70b-8192) seamlessly.
- **Bilingual TTS Generation:** Sends the Kannada output to the Sarvam AI TTS endpoint. If the call fails or exceeds 5 seconds, it falls back to Google Translator's gTTS.
