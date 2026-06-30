# Kannada RAG Architecture

This document contains the high-level system architecture diagrams detailing the Document Processing Pipeline, Retrieval Pipeline, and the Trust & Explainability Layer.

## 1. Document Processing Pipeline

The ingestion pipeline converts raw, scanned Kannada literature (PDFs) into queryable vector embeddings and lexical indices.

```mermaid
graph TD
    A[Scanned PDF] -->|Extract Pages| B(pdf_to_images.py)
    B -->|High-Res Images| C(preprocess_images.py)
    C -->|OpenCV Enhancement| D(ocr_surya.py)
    D -->|Raw Kannada Text| E(clean_text.py)
    E -->|Unicode Normalization| F(chunker.py)
    F -->|Semantic Chunks + Metadata| G(embed_and_store.py)
    
    G -->|Embeddings| H[(ChromaDB)]
    G -->|Text Corpus| I[(BM25 Index)]
    
    classDef file fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef db fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    class B,C,D,E,F,G file;
    class H,I db;
```

## 2. Retrieval Pipeline

The retrieval pipeline executes Hybrid Search with Reciprocal Rank Fusion, followed by deep semantic reranking.

```mermaid
graph TD
    Q[User Query] --> R(Query Rewriter)
    R -->|Gemini Context-Aware Rewrite| S{Retrieval Engine}
    
    S -->|Keyword Match| T1[(BM25 Search)]
    S -->|Semantic Match| T2[(ChromaDB Vector Search)]
    
    T1 -->|Top 10 Chunks| U(Hybrid Result Fusion)
    T2 -->|Top 10 Chunks| U
    
    U -->|Reciprocal Rank Fusion| V[Merged Candidate Pool ~15]
    V --> W(Cross-Encoder Re-ranking)
    W -->|BAAI/bge-reranker-v2-m3| X[Top 4 Final Chunks]
    
    X --> Y{Low Confidence Guardrails}
    Y -- Pass --> Z1(Gemini / Groq LLM)
    Y -- Fail --> Z2[Not Found / Fallback Message]
    
    Z1 --> Final[Generated Answer]
    
    classDef engine fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef db fill:#fff3e0,stroke:#e65100,stroke-width:2px;
    class R,U,W,Y engine;
    class T1,T2 db;
```

## 3. Trust & Explainability Layer

Ensures answers are grounded, hallucination-free, and verifiable by the end user.

```mermaid
graph TD
    A[Generated Answer] --> B[Confidence Score Assessment]
    B --> C{Threshold Check}
    C -- High Confidence --> D[Attach Source Snippets]
    C -- Low Confidence --> E[Display Low Confidence Warning]
    E --> D
    
    D --> F[Inject Page Citations]
    F --> G[Render Feedback Module 👍/👎]
    G --> H[Final UI Presentation]
    
    classDef ui fill:#fce4ec,stroke:#880e4f,stroke-width:2px;
    class A,B,D,E,F,G,H ui;
```
