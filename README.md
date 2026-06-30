<div align="center">

![Banner](https://raw.githubusercontent.com/Amruth011/kannada-rag-agent/main/banner.svg)

<br/>

<p>
<a href="https://heli-hogu-kaarana.vercel.app/">
  <img src="https://img.shields.io/badge/🚀 Live App-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white"/>
</a>
<a href="https://kannada-rag-agent-hqvwhfejguymb9ijrvz4hd.streamlit.app/">
  <img src="https://img.shields.io/badge/📊 Dashboard-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
</a>
<a href="https://github.com/Amruth011/kannada-rag-agent">
  <img src="https://img.shields.io/badge/GitHub-Source Code-181717?style=for-the-badge&logo=github&logoColor=white"/>
</a>
<a href="https://sarvam.ai">
  <img src="https://img.shields.io/badge/Powered by-Sarvam AI-f59e0b?style=for-the-badge"/>
</a>
<img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>
</p>

<p>
<img src="https://img.shields.io/badge/346 Pages-Processed-10b981?style=flat-square"/>
<img src="https://img.shields.io/badge/687 Chunks-Indexed-7c3aed?style=flat-square"/>
<img src="https://img.shields.io/badge/Bilingual-EN + KN-0891b2?style=flat-square"/>
<img src="https://img.shields.io/badge/TTS-Audio Answers-db2777?style=flat-square"/>
<img src="https://img.shields.io/badge/Re--Ranked-BGE v2 m3-7c3aed?style=flat-square"/>
<img src="https://img.shields.io/badge/RAGAS-Evaluated-f59e0b?style=flat-square"/>
<img src="https://img.shields.io/badge/Deployed-Live-16a34a?style=flat-square"/>
</p>

</div>

---

## 📌 Table of Contents

| | Section |
|:--|:--------|
| 🎬 | [Demo](#-demo) |
| 💜 | [Why Kannada?](#-why-kannada) |
| 🤔 | [How It Works](#-how-it-works) |
| ✨ | [What Makes This Different](#-what-makes-this-different) |
| 🧰 | [Skills Demonstrated](#-skills-demonstrated) |
| 🎯 | [Features](#-features) |
| 🏗️ | [Architecture](#%EF%B8%8F-architecture) |
| 🧠 | [Tech Stack](#-tech-stack) |
| 📁 | [Project Structure](#-project-structure) |
| 🚀 | [Quick Start](#-quick-start) |
| 💬 | [Example Questions](#-example-questions) |
| 🏅 | [What I Built](#-what-i-built) |
| 🙏 | [Acknowledgements](#-acknowledgements) |
| 📄 | [License](#-license) |
| 👤 | [Author](#-author) |

---

## 🎬 Demo

<div align="center">

> 🎥 **Demo shows:** English Q&A with citations · Kannada Q&A · Kannada TTS audio playback
>
> **[▶ Try the Live Vercel App →](https://heli-hogu-kaarana.vercel.app/)**
>
> **[📊 Open Streamlit Dashboard →](https://kannada-rag-agent-hqvwhfejguymb9ijrvz4hd.streamlit.app/)**

</div>

---

## 💜 Why Kannada?

India has **22 official languages** and over **500 million** Kannada speakers — yet almost all AI tools are built for English first.

When I searched for any AI tool that could interact with Kannada literature, I found nothing. No chatbot. No search. No voice. Just silence.

*ಹೇಳಿ ಹೋಗು ಕಾರಣ* (Heli Hogu Karana) by Ravi Belagere is a celebrated Kannada novel — but like most regional-language books, it exists outside the reach of modern AI.

**I built this to change that.**

This project is my answer to a simple question: *what if AI could speak your mother tongue?*

> *"Technology should cross language barriers, not create them."*

This is the first of many — my long-term mission is to make Indic-language literature, knowledge, and culture accessible through AI. 🇮🇳

---

## 🤔 How It Works

> *No technical background needed — here's the simple version*

**Step 1 — 📄 Read the book**  
The AI scans all 346 pages of the Kannada novel using OCR (like a camera that reads text) and stores everything in its memory.

**Step 2 — 🧠 Understand the text**  
Every paragraph is converted into numbers (called embeddings) that capture meaning — so the AI understands that "Himavant" and "the protagonist" mean the same thing.

**Step 3 — 🗄️ Build a smart library**  
All 687 text chunks are stored in a vector database — think of it as a super-smart search index that finds meaning, not just keywords.

**Step 4 — 🔀 Route your question**  
When you ask something, the AI figures out what kind of question it is:
- *"What's in page 50?"* → goes directly to page 50
- *"Who is Himavant?"* → searches for character mentions
- *"What is this book about?"* → uses general book knowledge
- *"What did he do next?"* → searches the full story

**Step 5 — 🔁 Re-rank for precision**  
The top 15 candidate chunks are scored by a Cross-Encoder (`BAAI/bge-reranker-v2-m3`) that reads the question and each chunk **together** — far more accurate than vector similarity alone. Only the best 4 chunks proceed.

**Step 6 — 🛡️ Confidence guardrail check**  
Before generating an answer, the system computes a confidence score. If it's below 60% (Very Low), the LLM is **skipped entirely** and a clear "Low Evidence" message is shown — preventing hallucinated or speculative answers.

**Step 7 — 🤖 Generate your answer**  
The top reranked passages are sent to Gemini (with Groq as fallback) which writes a clear answer — in English or Kannada, your choice.

**Step 8 — 🔊 Speak the answer**  
If you turn on TTS, the answer is converted to audio in natural Kannada or English voice and played back to you.

---

## ✨ What Makes This Different

```
Most RAG demos:   PDF → Chunks → LLM → Answer

This project:     Scanned Kannada PDF → OCR → Normalize → Chunk → Embed
                  → Smart Router → 4 Retrieval Strategies
                  → ChromaDB top-15 → Cross-Encoder Re-ranking → Top-4
                  → Confidence Guardrail (Very Low = skip LLM)
                  → Gemini / Groq LLM
                  → Bilingual Answer + Confidence Score + TTS Audio + Page Citations
                  → RAGAS Evaluated · Deployed · Durable Cloud DB · Admin Dashboard
```

| | Typical RAG Demo | This Project (v2.5) |
|:--|:--|:--|
| Language | English only | **Kannada + English** |
| Input | Clean text PDF | **Scanned Kannada novel (full OCR pipeline)** |
| Retrieval | Top-K cosine | **Top-15 → Cross-Encoder Re-ranked → Top-4** |
| Reliability | Answer always | **Confidence Guardrail — blocks weak-evidence answers** |
| Intelligence | Single Model | **Dual-Brain (Gemini + Groq Llama Fallback)** |
| Stability | Basic | **Auto-Discovery + Rate Limit Armor (Retries)** |
| Quality | Unverified | **RAGAS Evaluated (Faithfulness, Relevancy, Precision, Recall)** |
| Output | Text only | **Formatted Markdown + Audio Player + Compiled E-Books** |
| Persistence | None | **Durable Cloud DB (Vercel KV / Upstash Redis)** |
| Analytics | None | **Admin Dashboard + Geolocation Tracking** |
| Deployment | Local only | **Vercel Serverless + Streamlit Cloud** |

---

## 🧰 Skills Demonstrated

<div align="center">

![RAG](https://img.shields.io/badge/RAG_Pipelines-000000?style=for-the-badge)
![Re-Ranking](https://img.shields.io/badge/Cross--Encoder_Re--Ranking-7c3aed?style=for-the-badge)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)
![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97_Hugging_Face-FFD21E?style=for-the-badge&logoColor=black)
![LLM](https://img.shields.io/badge/LLM_Integration-7c3aed?style=for-the-badge)
![RAGAS](https://img.shields.io/badge/RAGAS_Evaluation-f59e0b?style=for-the-badge)
![OCR](https://img.shields.io/badge/OCR_Pipeline-0891b2?style=for-the-badge)
![Databases](https://img.shields.io/badge/Databases-ChromaDB%20%7C%20Upstash%20Redis-7c3aed?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![TTS](https://img.shields.io/badge/Text_to_Speech-db2777?style=for-the-badge)
![Deployment](https://img.shields.io/badge/Cloud_Deployment-16a34a?style=for-the-badge)
![API](https://img.shields.io/badge/REST_API_Integration-f59e0b?style=for-the-badge)

</div>

---

## 🎯 Features

<table>
<tr>
<td width="50%">

**🧠 AI & Retrieval Capabilities**
- Smart query routing — 4 retrieval strategies
- Character-specific RAG (θ=0.20)
- Page-level direct lookup
- Conversational memory (last 4 messages)
- Bilingual answers — English & Kannada
- **Cross-Encoder Re-ranking**: ChromaDB fetches 15 candidates; `BAAI/bge-reranker-v2-m3` re-scores all (query, chunk) pairs directly and selects the best 4 — dramatically improving context precision for Kannada + English queries.
- **Retrieval Confidence Scoring**: Cosine similarity scores are mapped to a 0–100% confidence percentage with 4 tiers: High (≥85%), Medium (70–84%), Low (60–69%), Very Low (<60%).
- **Low Confidence Guardrail**: If confidence drops below 60%, the LLM call is skipped entirely and a bilingual "Low Evidence" warning is shown — preventing speculative or hallucinated answers.

</td>
<td width="50%">

**🎨 UI & E-Book Experience**
- Glassmorphism dark mode UI
- 6 clickable suggestion chips
- Live progress bar (Search → Generate)
- Page citations on every answer
- Source snippets with per-page best passage
- Color-coded confidence badge (green/amber/orange/red)
- **Debug Mode**: Toggle to reveal per-chunk cosine similarity scores and cross-encoder reranker scores side-by-side
- **Interactive E-Book Suite**: Automated compilation of Kannada, English, and side-by-side Bilingual HTML ebooks with custom viewport-based scroll-spy

</td>
</tr>
<tr>
<td width="50%">

**🔊 Audio Performance**
- TTS via Sarvam bulbul:v3
- kn-IN (Kannada) + en-IN (English)
- Long answers auto-chunked + WAV stitched
- **Parallel Fallback Engine**: ThreadPoolExecutor-based fallback gTTS downloads (<2s latency) preventing Gateway timeouts.

</td>
<td width="50%">

**📊 Evaluation & Analytics**
- **RAGAS Evaluation Pipeline** (`eval_ragas.py`): Computes Faithfulness, Answer Relevancy, Context Precision, Context Recall for every sample. Outputs CSV + JSON + human-readable report.
- **Re-Ranking Comparison** (`eval_reranking.py`): Runs both baseline (no reranking) and reranked pipelines side-by-side and generates a Δ comparison report.
- Password-protected Admin Dashboard at `/admin` with User Activity, Feedback, and Geolocation tabs.

</td>
</tr>
</table>

---

## 🏗️ Architecture

<div align="center">

![Architecture](https://raw.githubusercontent.com/Amruth011/kannada-rag-agent/main/architecture.svg)

</div>

<details>
<summary><b>📐 Full pipeline walkthrough — click to expand</b></summary>

### 🔁 Streamlit RAG Pipeline (v2.5)

```
User Query
    ↓
[Smart Router]  ─── general question?  ──→  Book-level knowledge
    ↓                  character?       ──→  θ = 0.20
    ↓                  page/range?      ──→  Metadata filter
    ↓
ChromaDB bi-encoder similarity search
    top_k = 15  (wide candidate pool)
    ↓
Cross-Encoder Re-ranker  (BAAI/bge-reranker-v2-m3)
    scores every (query, chunk) pair
    sorts by relevance → keeps Top 4
    ↓
Confidence Score computation
    avg cosine score → mapped to 0–100%
    ↓
[Guardrail Check]
    confidence ≥ 60%  →  proceed to LLM
    confidence < 60%  →  skip LLM, show Low Evidence warning
    ↓
LangChain LCEL Chain  (Gemini → Sarvam → Groq fallback)
    ↓
Answer  +  Confidence Badge  +  Citations  +  Source Snippets
    ↓
[Optional] TTS (Sarvam bulbul:v3 / gTTS fallback)
```

### 🛡️ Stability-First Architecture

1. **Dual-Brain Fallback**: Defaults to Gemini Flash Lite; auto-falls back to Groq (Llama 3.1) on quota errors.
2. **Auto-Discovery**: Queries API keys to find the best available model version for your region.
3. **Rate Limit Armor**: Automatic retry with exponential backoff on `429` errors.
4. **Vercel Optimized**: FastAPI backend under 250MB bundle, strict 10s timeout management.
5. **Smart Context Capping**: Context capped at ~5,000 characters for free-tier LLM reliability.

### 🏗️ Dual-Deployment Architecture

#### 1. Serverless Edge Architecture (Vercel)
- **Frontend/Backend**: FastAPI with premium HTML5/CSS3/JS UI
- **Serverless Vector Search**: Custom NumPy cosine similarity over `vectors.npz` (pre-computed 687 embeddings) — no heavy local packages
- **LLM Engine**: Dual-Brain fallback with 5-turn conversational memory
- **Speech Engine**: Sarvam AI (bulbul:v3) → gTTS fallback

#### 2. Full Semantic RAG Architecture (Streamlit Cloud)
- **Frontend**: Glassmorphism Streamlit UI (`app.py`)
- **Retrieval**: ChromaDB + multilingual sentence-transformers → Cross-Encoder Re-ranker → Confidence Guardrail
- **LLM Chain**: LangChain LCEL with Gemini → Sarvam → Groq fallback
- **Evaluation**: RAGAS pipeline + before/after re-ranking comparison

---

### Pipeline Comparison: Streamlit vs Vercel

| Pipeline Phase | Vercel (Serverless) | Streamlit (Semantic App) |
|:---|:---|:---|
| **1 · OCR Ingestion** | Surya OCR (CPU) | Surya OCR (CPU) |
| **2 · Chunking** | Page-level | 400-char semantic (50 overlap) |
| **3 · Vector Indexing** | NumPy (`vectors.npz`) | ChromaDB + Multilingual ST |
| **4 · Re-Ranking** | — | CrossEncoder `bge-reranker-v2-m3` top-15→4 |
| **5 · Confidence Check** | — | Score mapping + Very Low guardrail |
| **6 · Query Routing** | Fallback chain + memory | LangChain LCEL + metadata filters |
| **7 · Primary LLM** | Gemini Flash | Gemini Flash Lite |
| **8 · Fallback LLM** | Groq Llama 3.3 | Groq Llama 3.1 |
| **9 · Speech** | Sarvam bulbul:v3 + gTTS | Sarvam bulbul:v3 + gTTS |
| **10 · Evaluation** | — | RAGAS (Faithfulness, Relevancy, Precision, Recall) |
| **11 · Hosting** | Vercel Serverless | Streamlit Cloud |

</details>

---

## 🧠 Tech Stack

<div align="center">

| Layer | Component | Technology |
|:--|:--|:--|
| 📄 PDF Processing | Page extraction | pdf2image + Poppler |
| 👁️ OCR | Text extraction | Surya OCR (Kannada + English) |
| 🤗 Embeddings | Multilingual vectorization | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| 🗄️ Vector DB | Semantic search | ChromaDB (cosine similarity) |
| 🔁 Re-Ranker | Cross-Encoder precision | **`BAAI/bge-reranker-v2-m3`** (multilingual, CPU, local) |
| 🛡️ Guardrail | Confidence gating | Custom score mapping + Very Low threshold |
| 🧠 Primary LLM | Language model | **Gemini Flash Lite (Google GenAI SDK)** |
| 🧠 Secondary LLM | Multilingual fallback | **Groq Llama 3.1 (Safety Net)** |
| 🦜 Orchestration | Agent & LCEL chain | **LangChain (LCEL, Custom Fallback ChatModel)** |
| 💾 Cloud DB | Permanent storage | **Vercel KV / Upstash Redis (Logs & Feedback)** |
| 📊 Evaluation | RAG quality metrics | **RAGAS (Faithfulness · Relevancy · Precision · Recall)** |
| 🔊 TTS | Audio synthesis | Sarvam bulbul:v3 · priya speaker |
| 🎨 UI & API | Product | Streamlit + FastAPI (Deployed on Vercel) |
| ☁️ Hosting | Cloud | Vercel (API) + Streamlit Cloud (UI) |

</div>

---

## 📁 Project Structure

```
kannada-rag-agent/
│
├── 📂 api/
│   └── index.py                 # ✅ FastAPI server — Vercel Serverless entry point
│                                #    └─ RAG engine · E-Book reader · Admin dashboard
│                                #    └─ Vercel KV (Upstash Redis) persistence layer
│                                #    └─ IP geolocation · User session tracking
│
├── 📂 data/
│   ├── raw_images/              # PDF pages as PNG — not in repo
│   ├── processed_images/        # OpenCV output — not in repo
│   ├── cleaned_text/            # Raw OCR text — not in repo
│   ├── normalized_text/         # Unicode fixed — not in repo
│   └── chunks.json              # ✅ 687 semantic chunks
│
├── 📂 chroma_db/                # ✅ Vector store (shipped for deployment)
│
├── 📂 ingest/
│   ├── pdf_to_images.py         # Phase 1 — PDF → PNG
│   ├── preprocess_images.py     # Phase 2 — OpenCV
│   ├── ocr_surya.py             # Phase 3 — Surya OCR
│   ├── clean_text.py            # Phase 4 — Normalization
│   └── chunker.py               # Phase 5 — Chunking
│
├── 📂 vectorstore/
│   └── embed_and_store.py       # Embeddings → ChromaDB
│
├── 📂 rag/
│   └── rag_agent.py             # CLI RAG pipeline
│
├── app.py                       # ✅ Main Streamlit app (UI + guardrail + debug mode)
├── rag_agent_v2.py              # ✅ Retrieval engine (ChromaDB + CrossEncoder reranker)
├── eval_ragas.py                # ✅ RAGAS evaluation pipeline
├── eval_reranking.py            # ✅ Before/after re-ranking comparison script
├── evaluation_dataset.json      # ✅ Evaluation Q&A samples
├── banner.svg                   # ✅ Banner image
├── architecture.svg             # ✅ Architecture diagram
├── vercel.json                  # ✅ Vercel routing config
├── streamlit_requirements.txt   # ✅ Streamlit/local deps (includes sentence-transformers)
├── requirements.txt             # ✅ Vercel serverless deps
├── LICENSE                      # ✅ MIT License
├── .env                         # API keys (not committed)
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Poppler (for pdf2image)
- [Sarvam AI API key](https://dashboard.sarvam.ai)
- [Gemini API key](https://aistudio.google.com)
- [Groq API key](https://console.groq.com)

### Setup

```bash
# 1. Clone
git clone https://github.com/Amruth011/kannada-rag-agent.git
cd kannada-rag-agent

# 2. Virtual environment
python -m venv kannada-rag-env
kannada-rag-env\Scripts\activate        # Windows
# source kannada-rag-env/bin/activate   # Mac/Linux

# 3. Install (Streamlit / local)
pip install -r streamlit_requirements.txt

# 4. Create .env file
SARVAM_API_KEY=your_sarvam_api_key
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
ADMIN_PASSWORD=your_admin_password

# 5. Run locally
kannada-rag-env\Scripts\python.exe -m streamlit run app.py
```

Open **[http://localhost:8501](http://localhost:8501)** 🎉

> **Note on first run:** The re-ranker model (`BAAI/bge-reranker-v2-m3`, ~570 MB) will be downloaded automatically from HuggingFace and cached. Subsequent starts are instant.

### Run RAGAS Evaluation

```bash
# Evaluate RAG quality (Faithfulness, Relevancy, Precision, Recall)
python eval_ragas.py

# Compare before vs after re-ranking
python eval_reranking.py
```

### Vercel Deployment (FastAPI)

```bash
npm i -g vercel
vercel --prod
# Add Environment Variables in Vercel Dashboard:
# SARVAM_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, ADMIN_PASSWORD
# Then connect Vercel KV (Storage tab) for persistent data
```

---

## 🔄 Rebuild Pipeline from Scratch

<details>
<summary><b>Only needed if you want to re-process the original PDF — click to expand</b></summary>

<br/>

```bash
python pdf_to_images.py        # Phase 1 — PDF → 346 PNGs     (~5 min)
python preprocess_images.py    # Phase 2 — OpenCV denoise      (~3 min)
python ocr_surya.py            # Phase 3 — Surya OCR           (~3 hrs CPU)
python clean_text.py           # Phase 4 — Unicode normalize   (~1 min)
python chunker.py              # Phase 5 — 687 chunks          (~1 min)
python embed_and_store.py      # Phase 6 — Embed → ChromaDB   (~40 min)
streamlit run app.py           # Phase 7 — Launch
```

</details>

---

## 💬 Example Questions

<table>
<tr>
<td width="50%">

**🇬🇧 English**
```
What is this book about?
Who is Himavant?
Who is Prarthana?
What is in page 50?
What is the relationship
between Himavant and Prarthana?
```

</td>
<td width="50%">

**🇮🇳 Kannada**
```
ಹಿಮವಂತ ಯಾರು?
ಪ್ರಾರ್ಥನಾ ಯಾರು?
ಈ ಕಾದಂಬರಿ ಬಗ್ಗೆ ಹೇಳಿ
50ನೇ ಪುಟದಲ್ಲಿ ಏನಿದೆ?
ಹಿಮವಂತ ಮತ್ತು ಪ್ರಾರ್ಥನಾ ಸಂಬಂಧ?
```

</td>
</tr>
</table>

---

## 🏅 What I Built

A complete, production-deployed AI system — built from scratch with no starter templates:

| | Deliverable | Detail |
|:--|:------------|:-------|
| ✅ | Full OCR pipeline | Scanned PDF → clean Kannada + English text |
| ✅ | Vector search engine | 687 chunks · ChromaDB · cosine similarity |
| ✅ | Smart RAG agent | 4-strategy router · LangChain LCEL · Gemini/Groq |
| ✅ | Cross-Encoder Re-ranking | ChromaDB top-15 → `BAAI/bge-reranker-v2-m3` → top-4 · multilingual · CPU-only |
| ✅ | Retrieval Confidence Scoring | Cosine-to-percentage mapping · 4-tier label (High/Medium/Low/Very Low) |
| ✅ | Low Confidence Guardrail | Very Low (<60%) blocks LLM call · bilingual warning card · sources still shown |
| ✅ | RAGAS Evaluation | Faithfulness · Answer Relevancy · Context Precision · Recall · CSV + JSON + report |
| ✅ | Re-Ranking Comparison | Baseline vs reranked RAGAS metrics · Δ improvement report |
| ✅ | Bilingual TTS | WAV stitching · kn-IN + en-IN · bulbul:v3 |
| ✅ | Production UI | Glassmorphism dark mode · chips · progress bar · debug mode · feedback |
| ✅ | Interactive E-Book Suite | Compiled Kannada, English & Bilingual HTML readers with scroll-spy |
| ✅ | Durable Cloud DB | Vercel KV / Upstash Redis REST — persists logs & feedback across cold starts |
| ✅ | Geolocation Analytics | Background-thread IP-to-location resolver (city, region, country) |
| ✅ | User Session Tracking | Persistent browser UUID (`localStorage`) + optional name |
| ✅ | Admin Dashboard | Password-protected · 3 tabs: Users, Activity Log, Feedback |
| ✅ | Live deployment | Vercel Serverless + Streamlit Cloud · fully managed secrets |

---

## 🙏 Acknowledgements

| | Project | Used For |
|:--|:--------|:---------|
| 🤖 | [Sarvam AI](https://sarvam.ai) | Indic LLM (Sarvam-M) + TTS (bulbul:v3) |
| 👁️ | [Surya OCR](https://github.com/vikpar/surya) | Kannada + English OCR |
| 🦜 | [LangChain](https://github.com/langchain-ai/langchain) | Agent & RAG orchestration, custom ChatModel fallback |
| 🤗 | [Hugging Face](https://huggingface.co/) | Multilingual embeddings + `BAAI/bge-reranker-v2-m3` Cross-Encoder |
| 🗄️ | [ChromaDB](https://www.trychroma.com/) | Vector database |
| 📊 | [RAGAS](https://github.com/explodinggradients/ragas) | RAG evaluation framework |
| 🔤 | [indic-nlp-library](https://github.com/anoopkunchukuttan/indic_nlp_library) | Kannada Unicode normalization |
| 🧠 | [sentence-transformers](https://www.sbert.net/) | Multilingual embeddings + CrossEncoder reranking |
| 📚 | Ravi Belagere | Author of *ಹೇಳಿ ಹೋಗು ಕಾರಣ* |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License — free to use, modify and distribute with attribution.
```

---

## 👤 Author

<div align="center">

**Amruth Kumar M** — AI Engineer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://linkedin.com/in/amruth-kumar-m)
[![Portfolio](https://img.shields.io/badge/Portfolio-amruthportfolio.me-58a6ff?style=for-the-badge&logo=firefox&logoColor=white)](https://amruthportfolio.me)
[![GitHub](https://img.shields.io/badge/GitHub-Amruth011-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Amruth011)

</div>

---

<div align="center">

*Built with ❤️ for Kannada literature and Indic AI*

**⭐ Star this repo if you found it useful — it genuinely helps!**

</div>
