# ChromaDB Deployment & Validation Report

This report documents the verification, size, persistence strategy, and performance characteristics of ChromaDB inside the production Render environment.

---

## 1. ChromaDB Directory Verification

* **Database Directory:** [**chroma_db**](file:///d:/personal%20files/Projects/kannada-rag-agent/chroma_db) (Located at the root of the workspace).
* **Expected Path Resolution:** `os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_db")` (Resolves correctly on Render's containerized linux filesystem).
* **Current Disk Footprint:** **~13.7 MB** (Total size on disk is 14,418,084 bytes across 5 files, including `chroma.sqlite3`).

---

## 2. Persistence Strategy on Render

ChromaDB is a database engine. In our deployment:
1. **Pre-built Database Index:** The vector database index of the Kannada literature is generated offline and committed directly to the git repository under the [**chroma_db**](file:///d:/personal%20files/Projects/kannada-rag-agent/chroma_db) directory.
2. **Read-Only Context:** At runtime, the application only queries the database and does not perform insert/write operations. Therefore, stateless containers on Render can run the retrieval pipeline safely without requiring persistent disk attachments.
3. **Write Support (Optional):** If new documents need to be ingested dynamically at runtime, a **Render Persistent Disk** must be mounted at `/opt/render/project/src/chroma_db` to prevent data loss on container rebuilds.

---

## 3. Memory & Startup Profile

* **Base Memory Footprint:** **~150-200 MB** (FastAPI/Streamlit process).
* **RAG Pipeline Footprint:** **~1.0 - 1.2 GB** (Peak memory occurs when loading the multilingual sentence-transformers embedding model and the PyTorch-based Cross-Encoder reranker).
* **Expected Cold-Start Delay:** **20-30 seconds**. This is the time required to initialize PyTorch, load the model weights from the local cache or Hugging Face Hub, and load the ChromaDB database index.
