# Deployment Configuration Guide - Render

This guide outlines the production deployment setup for the Kannada Literature RAG Agent, detailing the transition to Render and the technical reasons for rejecting Vercel.

---

## 1. Production Target: Render

The production deployment runs as a stateful **Web Service** on Render.

- **Primary Entry Point:** `app.py` (Streamlit-based user interface / FastAPI backend wrapper)
- **Deployment Manifest:** `render.yaml`
- **Execution Script:** `Procfile`

### In-Code Infrastructure (`render.yaml`)
```yaml
services:
  - type: web
    name: kannada-rag-agent
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
    autoDeploy: true
```

### Execution Script (`Procfile`)
```text
web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

---

## 2. Why Render Was Chosen

Render's containerized Web Service environment provides several advantages critical to running a complete RAG system:
1. **Persistent Local Storage:** Native ChromaDB uses a local filesystem directory (`chroma_db`) to read/write persistent indexes. Render allows persistent disk attachments, keeping index loading speeds instantaneous.
2. **Dedicated CPU/RAM Memory Allocations:** Loading complex models (such as the sentence transformer embeddings) requires persistent memory allocation rather than ephemeral serverless containers.
3. **No Execution Timeout Constraints:** The heavy processing involved in RRF merging, Cross-Encoder reranking, and text-to-speech queries can occasionally exceed standard serverless execution limits (e.g., 10-15 seconds). Render handles long-lived requests seamlessly.

---

## 3. Why Vercel Was Rejected

Although Vercel is an exceptional platform for frontend frameworks and lightweight APIs, it is technically incompatible with the computational and architectural requirements of this RAG agent.

### A. Serverless Size Limits
Vercel enforces a strict **250MB limit** (compressed) on serverless function deployment bundles. The Kannada RAG stack includes:
- `sentence-transformers`
- `chromadb`
- `langchain` & `langchain-community`
- `torch` & `numpy`

Together, these packages and their associated shared objects exceed the size limitations, resulting in deployment failures during build time.

### B. ChromaDB Limitations
ChromaDB is a database engine. Running it in a serverless context on Vercel requires connecting to a remote Chroma hosting service (which increases latency and configuration overhead). Attempting to run ChromaDB locally in a Vercel serverless function fails because Vercel functions run in read-only, stateless environments where local files cannot be safely persisted or loaded across separate execution instances.

### C. Cross-Encoder & ML Model Footprint
The Cross-Encoder pipeline (`BAAI/bge-reranker-v2-m3`) runs sequence classification on candidates. Loading this model, alongside sentence transformer embeddings, requires initializing PyTorch/ONNX runtimes. The cold start time of loading these libraries inside a Vercel function exceeds Vercel's maximum startup threshold, leading to standard 504 Gateway Timeouts.
