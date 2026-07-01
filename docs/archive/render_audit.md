# Render Compatibility Audit Report

This report documents the verification of Render-specific deployment configurations and the deprecation of legacy platform artifacts.

---

## 1. Production Entrypoint Verification

The designated production entrypoint for Render has been verified:
* **Active Entrypoint:** [**app.py**](file:///d:/personal%20files/Projects/kannada-rag-agent/app.py) (Streamlit Application UI and backend orchestration).
* **Inactive/Deprecated Entrypoint:** [**api/index.py**](file:///d:/personal%20files/Projects/kannada-rag-agent/api/index.py) (Legacy serverless FastAPI entrypoint designed for Vercel). 
* **State:** The legacy serverless api folder remains in the codebase but is **not** called by any Render build process. The production web service routes execution exclusively through `app.py`.

---

## 2. Command Syntax Verification

We audited and synchronized the startup commands across all deployment configuration layers to ensure proper port binding and network accessibility on Render:
* **Procfile Configuration:**
  ```text
  web: streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT
  ```
* **render.yaml Configuration:**
  ```yaml
  startCommand: "streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT"
  ```
* **Verification:** The `--server.address=0.0.0.0` directive ensures Streamlit binds to all network interfaces inside the container, and `--server.port=$PORT` maps to the dynamic port allocated by Render's load balancer.

---

## 3. Deprecated Platform Configuration

* **Vercel Configurations (`vercel.json`, `deploy_dist/`):** Deprecated. They contain references to serverless routing which does not support the heavy requirements of our hybrid RAG system (local ChromaDB and Cross-Encoder model).
* **FastAPI Serverless (`api/index.py`):** Retained as legacy code, but completely isolated. No Render pipeline uses it.
