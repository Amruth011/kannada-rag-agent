# Kannada RAG Project - Feature Inventory

This document represents a comprehensive audit of all components, features, and pipelines implemented within the Kannada RAG repository.

## 1. OCR Pipeline
- **PDF to Images**: `pdf_to_images.py` converts input PDF files into high-resolution images for OCR processing.
- **Image Preprocessing**: `preprocess_images.py` utilizes OpenCV to enhance image quality, adjust contrast, and denoise for optimal character recognition.
- **Surya OCR Extraction**: `ocr_surya.py` integrates the state-of-the-art Surya OCR model specifically optimized for detecting and extracting Kannada scripts.
- **Unicode Normalization**: `clean_text.py` normalizes Kannada Unicode characters, fixing zero-width joiners and rendering artifacts common in Indic scripts.

## 2. Knowledge Base Management
- **Semantic Chunking**: `chunker.py` segments the extensive book text into semantically cohesive chunks.
- **Chunk Overlap Strategy**: Implements overlapping sliding windows to ensure cross-chunk context is preserved for the embedding model.
- **Metadata Handling**: Extracts and attaches physical page numbers to every single text chunk.
- **Page Tracking**: Enables precise back-referencing to the original 346-page PDF.

## 3. Retrieval Pipeline
- **Embeddings Model**: Utilizes `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` for dense vector representations.
- **ChromaDB**: Acts as the high-performance local vector store.
- **Query Rewriting**: Intercepts user queries and utilizes Gemini to rewrite ambiguous questions (resolving pronouns like 'he', 'she' based on chat history).
- **Hybrid Search**: Executes parallel retrieval across both Semantic and Keyword dimensions.
  - **BM25 Retrieval**: Leverages `rank-bm25` for exact keyword and rare term matching.
  - **Vector Retrieval**: Leverages ChromaDB for semantic intent matching.
- **Fusion Strategy**: Implements **Reciprocal Rank Fusion (RRF)** to mathematically merge and deduplicate Vector and BM25 chunks based on their ranks, eliminating score scale biases.
- **Cross-Encoder Reranking**: Utilizes `BAAI/bge-reranker-v2-m3` to deeply re-evaluate the fused candidate pool and select the ultimate top 4 chunks.
- **Metadata Filtering**: Supports hard-filtering the retrieval space to specific pages or page ranges based on the user's prompt (e.g., "On page 50...").

## 4. Generation Pipeline
- **LangChain Orchestration**: Manages the end-to-end prompt chain and message history formatting.
- **Bilingual Generation**: Supports answering in both English and Kannada dynamically.
- **Primary LLM**: Integrates with Google's Gemini models for high-quality generation.
- **Groq Fallback**: Implements a robust fallback mechanism to switch to Groq (Llama-3) if the Gemini API fails or rate limits.
- **Prompt Engineering**: Enforces strict grounding rules, instructing the LLM to refuse answers if context is insufficient.

## 5. Trust & Explainability
- **Citations**: Automatically cites the exact page numbers used to generate the answer.
- **Source Snippets**: Displays the raw Kannada text chunks that were retrieved as evidence.
- **Confidence Scoring**: Calculates a confidence percentage based on the Cross-Encoder scores and visually displays it (Green/Yellow/Red).
- **Low-Confidence Guardrails**: Intercepts the pipeline and returns a "Not Found" message if no chunks pass the strict similarity thresholds, preventing LLM hallucination.

## 6. Evaluation Framework
- **Evaluation Dataset**: `data/eval_dataset.json` contains a curated ground-truth QA dataset.
- **RAGAS Integration**: Utilizes the RAGAS framework for automated, LLM-as-a-judge evaluation.
- **Core Metrics Tracked**:
  - Faithfulness
  - Context Precision
  - Context Recall
  - Answer Relevancy
- **Benchmark Scripts**: Dedicated scripts to evaluate Query Rewriting (`eval_query_rewriting.py`), Reranking (`eval_reranking.py`), and Hybrid Search (`eval_hybrid.py`).

## 7. Accessibility
- **Sarvam AI TTS**: Integrates native Kannada Text-to-Speech using the Sarvam API for natural, localized audio playback of the answers.
- **gTTS Fallback**: Automatically falls back to Google TTS if the Sarvam API is unavailable.
- **Audio Generation**: Renders an inline audio player directly in the Streamlit UI.

## 8. Other Utility Features
- **Feedback System**: Allows users to rate answers (👍 / 👎) with controls embedded below every response.
- **Feedback Storage**: Persists all interactions, contexts, and ratings locally into `feedback.csv`.
- **Admin Tools**: `feedback_report.py` generates analytics on model helpfulness.
- **Debug Mode**: A sidebar toggle that exposes the inner workings of the pipeline, displaying Original vs Rewritten Queries, Hybrid chunk stats (Vector, BM25, Merged, Reranked), and chunk-level RRF/Cosine scores.
- **Export Capabilities**: Utilities to extract the vector database and conversation logs.
