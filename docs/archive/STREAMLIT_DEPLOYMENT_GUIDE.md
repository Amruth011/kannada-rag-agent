# Streamlit Community Cloud Deployment Guide

This guide details how to deploy the **Kannada Literature RAG Agent** to **Streamlit Community Cloud**.

---

## 📋 Pre-deployment Checklist

1. **GitHub Repository**: Ensure all files (especially `app.py`, `rag_agent_v2.py`, `requirements.txt`, `packages.txt`, and the `chroma_db/` folder) are committed and pushed to your GitHub repository.
2. **Secrets Configuration**: Prepare your API keys (Gemini, Groq, Sarvam) to be pasted into the Streamlit Cloud dashboard.
3. **Database Check**: Verify that `chroma_db/` exists in the repository. Streamlit Community Cloud uses an ephemeral disk, so having the database pre-ingested in your Git repo is required for the RAG search to work instantly.

---

## 🛠️ Step-by-Step Deployment Instructions

1. **Log in to Streamlit Cloud**:
   Go to [share.streamlit.io](https://share.streamlit.io/) and log in with your GitHub account.

2. **Deploy a New App**:
   - Click the **"New app"** button.
   - Select your repository (`kannada-rag-agent`).
   - Select the branch (e.g., `main`).
   - Set the Main file path to: `app.py`.

3. **Configure Advanced Settings (IMPORTANT)**:
   Before clicking "Deploy", click on **"Advanced settings..."** (next to the deploy button).

4. **Set Up Secrets**:
   In the **Secrets** text box, paste the configuration from `STREAMLIT_SECRETS_TEMPLATE.md` and replace the placeholder values with your actual API keys:
   ```toml
   GEMINI_API_KEY = "your-gemini-key"
   GROQ_API_KEY = "your-groq-key"
   SARVAM_API_KEY = "your-sarvam-key" # Optional
   ```
   *Note: Streamlit injects these secrets into the environment, making them accessible via `os.getenv()` in `app.py`.*

5. **Deploy**:
   Click **"Save"** and then **"Deploy!"**. Streamlit will spin up a container, install python dependencies from `requirements.txt`, system packages from `packages.txt`, and start the app.

---

## ⚠️ Streamlit Cloud Resource Management & Limits

Streamlit Community Cloud enforces a strict **1 GB RAM limit** per app container. To prevent Out-Of-Memory (OOM) crashes:

1. **Lazy Model Loading**: The app utilizes lazy loading for heavy machine learning packages (`torch` and `sentence-transformers`). They are mocked at startup and only loaded when a semantic query is processed.
2. **Page-Only Fast Path**: Encourage users to ask page-specific questions (e.g., "What happens on page 50?"). These queries bypass ML loading entirely, consuming **< 15 MB** of RAM.
3. **CPU Thread Capping**: PyTorch is configured to run with a maximum of `4` CPU threads. Do not increase this, as it will lead to high memory consumption and container restarts.
