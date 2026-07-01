# Deployment Guide

The Kannada RAG Agent is designed to be highly portable, with first-class support for **Vercel Serverless** and **Streamlit Community Cloud**.

## 1. Vercel Serverless (Recommended)

Vercel provides the most scalable, low-latency deployment for the FastAPI backend, easily handling concurrent TTFB (Time To First Byte) requests for the TTS engine.

### Prerequisites
- A Vercel Account linked to your GitHub.
- API Keys: `GEMINI_API_KEY`, `GROQ_API_KEY`, `SARVAM_API_KEY`.

### Steps
1. Push your repository to GitHub.
2. In the Vercel Dashboard, select **Add New Project** and import your repository.
3. Vercel will automatically detect the `vercel.json` and the `api/index.py` FastAPI structure.
4. **Environment Variables**: Add your API keys in the Vercel Environment settings.
5. Click **Deploy**. 
6. Vercel will bundle the Python environment and ChromaDB dependencies. (Note: The repository uses a `.vercelignore` to keep the bundle size under the 250MB AWS Lambda limit).

## 2. Streamlit Community Cloud

Streamlit provides a fast, interactive UI for the application.

### Prerequisites
- A Streamlit Cloud account linked to your GitHub.

### Steps
1. Go to share.streamlit.io and click **New app**.
2. Select your repository and branch.
3. Set the **Main file path** to `app.py`.
4. Click **Advanced Settings** and enter your secrets in TOML format:
   ```toml
   GEMINI_API_KEY = "your-key"
   GROQ_API_KEY = "your-key"
   SARVAM_API_KEY = "your-key"
   ```
5. Click **Deploy**.
6. Streamlit Cloud will automatically install OS dependencies from `packages.txt` (e.g., `libgl1`) and Python dependencies from `requirements.txt`.

## 3. Local Development Setup

To run the application locally for debugging or development:

```bash
# 1. Clone the repository
git clone https://github.com/YourOrg/kannada-rag-agent.git
cd kannada-rag-agent

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your actual API keys

# 5. Run the Streamlit UI
streamlit run app.py
```

### Local API Testing
If you are developing the Vercel backend locally, you can use `uvicorn`:
```bash
uvicorn api.index:app --reload
```
