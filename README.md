<div align="center">

![Banner](https://raw.githubusercontent.com/Amruth011/kannada-rag-agent/main/banner.svg)

<br/>

<p>
<a href="https://kannada-rag-agent-hqvwhfejguymb9ijrvz4hd.streamlit.app/">
  <img src="https://img.shields.io/badge/🚀 Live App-Streamlit Cloud-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
</a>
<a href="https://github.com/Amruth011/kannada-rag-agent">
  <img src="https://img.shields.io/badge/GitHub-Source Code-181717?style=for-the-badge&logo=github&logoColor=white"/>
</a>
<a href="https://sarvam.ai">
  <img src="https://img.shields.io/badge/Powered by-Sarvam AI-f59e0b?style=for-the-badge"/>
</a>
<img src="https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
</p>

<p>
<img src="https://img.shields.io/badge/346 Pages-Processed-10b981?style=flat-square"/>
<img src="https://img.shields.io/badge/687 Chunks-Indexed-7c3aed?style=flat-square"/>
<img src="https://img.shields.io/badge/Bilingual-EN + KN-0891b2?style=flat-square"/>
<img src="https://img.shields.io/badge/TTS-Audio Answers-db2777?style=flat-square"/>
<img src="https://img.shields.io/badge/Deployed-Live-16a34a?style=flat-square"/>
</p>

</div>

---

## 📌 Table of Contents

- [Demo](#-demo)
- [Why Kannada?](#-why-kannada)
- [How It Works](#-how-it-works)
- [What Makes This Different](#-what-makes-this-different)
- [Skills Demonstrated](#-skills-demonstrated)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Example Questions](#-example-questions)
- [What I Built](#-what-i-built)
- [Acknowledgements](#-acknowledgements)
- [Author](#-author)

---

## 🎬 Demo

<!--
╔══════════════════════════════════════════════════════════════════╗
║   YOUR GIF → D:\personal files\Projects\Heli_Hogo_Karana.gif   ║
║                                                                  ║
║   TO ADD IT:                                                     ║
║   1. Go to → github.com/Amruth011/kannada-rag-agent/issues/new  ║
║   2. Type any title → drag & drop your GIF into the text box    ║
║   3. Wait for upload → copy the URL that appears                 ║
║   4. Paste URL below, remove the comment tags                    ║
╚══════════════════════════════════════════════════════════════════╝
-->

<!-- ![Kannada RAG Agent Demo](YOUR-GIF-URL-HERE) -->

<div align="center">

> 🎥 **Demo shows:** English Q&A · Kannada Q&A · Kannada TTS audio playback
>
> **[▶ Try it live right now →](https://kannada-rag-agent-hqvwhfejguymb9ijrvz4hd.streamlit.app/)**

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

**Step 5 — 🤖 Generate your answer**
The relevant passages are sent to Sarvam-M (an Indian AI model) which reads them and writes a clear answer — in English or Kannada, your choice.

**Step 6 — 🔊 Speak the answer**
If you turn on TTS, the answer is converted to audio in natural Kannada or English voice and played back to you.

---

## ✨ What Makes This Different

```
Most RAG demos:   PDF → Chunks → LLM → Answer
This project:     Scanned Kannada PDF → OCR → Normalize → Chunk → Embed
                  → Smart Router → 4 Retrieval Strategies → Sarvam LLM
                  → Bilingual Answer + TTS Audio + Page Citations
                  → Deployed · Feedback System · Admin Viewer
```

| | Typical RAG Demo | This Project |
|:--|:--|:--|
| Language | English only | **Kannada + English** |
| Input | Clean text PDF | **Scanned Kannada novel (full OCR pipeline)** |
| Retrieval | One strategy | **4 smart strategies** |
| Output | Text only | **Text + TTS audio** |
| Deployment | Local only | **Live on Streamlit Cloud** |

---

## 🧰 Skills Demonstrated

<div align="center">

![RAG](https://img.shields.io/badge/RAG_Pipelines-000000?style=for-the-badge)
![LLM](https://img.shields.io/badge/LLM_Integration-7c3aed?style=for-the-badge)
![OCR](https://img.shields.io/badge/OCR_Pipeline-0891b2?style=for-the-badge)
![NLP](https://img.shields.io/badge/Indic_NLP-10b981?style=for-the-badge)
![ChromaDB](https://img.shields.io/badge/Vector_DB-7c3aed?style=for-the-badge)
![Streamlit](https://img.shields.io/badge/Streamlit_UI-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
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

**🧠 AI Capabilities**
- Smart query routing — 4 retrieval strategies
- Character-specific RAG (top-10, θ=0.20)
- Page-level direct lookup
- Conversational memory (last 4 messages)
- Bilingual answers — English & Kannada

</td>
<td width="50%">

**🎨 UI & Experience**
- Glassmorphism dark mode UI
- 6 clickable suggestion chips
- Live progress bar (Search → Generate)
- Page citations on every answer
- Source chunks toggle

</td>
</tr>
<tr>
<td width="50%">

**🔊 Audio**
- TTS via Sarvam bulbul:v3
- kn-IN (Kannada) + en-IN (English)
- Long answers auto-chunked + WAV stitched

</td>
<td width="50%">

**📊 Feedback & Admin**
- Star rating + text feedback form
- Saves to `feedback.json`
- Password-protected admin viewer in sidebar

</td>
</tr>
</table>

---

## 🏗️ Architecture

<div align="center">

![Architecture](https://raw.githubusercontent.com/Amruth011/kannada-rag-agent/main/architecture.svg)

</div>

<details>
<summary><b>📐 Pipeline walkthrough — click to expand</b></summary>

<br/>

| Phase | Component | Detail |
|:------|:----------|:-------|
| **1 · Ingestion** | pdf2image + Poppler | 346 PDF pages → PNG at 200 DPI |
| **2 · Preprocessing** | OpenCV | Denoise · adaptive threshold · sharpen |
| **3 · OCR** | EasyOCR | Kannada + English dual-language, CPU |
| **4 · Normalization** | indic-nlp-library | Unicode normalization for Kannada script |
| **5 · Chunking** | Custom chunker | 400 char chunks, 50 char overlap → 687 chunks |
| **6 · Embeddings** | sentence-transformers | `paraphrase-multilingual-MiniLM-L12-v2` |
| **7 · Vector Store** | ChromaDB | Persistent · cosine similarity |
| **8 · Routing** | Smart router | Page lookup · Char RAG · Standard RAG · Book context |
| **9 · LLM** | Sarvam-M | Conversational memory · last 4 messages |
| **10 · TTS** | Sarvam bulbul:v3 | kn-IN / en-IN · chunked + WAV stitching |
| **11 · UI** | Streamlit | Glassmorphism · chips · progress bar · feedback |
| **12 · Deploy** | Streamlit Cloud | Live public URL |

</details>

---

## 🧠 Tech Stack

<div align="center">

| Layer | Component | Technology |
|:------|:----------|:-----------|
| 📄 PDF Processing | Page extraction | pdf2image + Poppler |
| 🖼️ Image Prep | Noise removal | OpenCV (denoise · threshold · sharpen) |
| 👁️ OCR | Text extraction | EasyOCR (Kannada + English, CPU) |
| 🔤 Normalization | Script fixing | indic-nlp-library |
| ✂️ Chunking | Text splitting | Custom (400ch · 50 overlap) |
| 🧠 Embeddings | Vector encoding | sentence-transformers MiniLM-L12-v2 |
| 🗄️ Vector DB | Semantic search | ChromaDB (cosine similarity) |
| 🤖 LLM | Answer generation | Sarvam-M via Sarvam AI API |
| 🔊 TTS | Audio synthesis | Sarvam bulbul:v3 · priya speaker |
| 🎨 UI | Frontend | Streamlit + glassmorphism CSS |
| ☁️ Deployment | Hosting | Streamlit Cloud |
| 🐍 Language | Runtime | Python 3.13 |

</div>

---

## 📁 Project Structure

```
kannada-rag-agent/
│
├── 📂 data/
│   ├── raw_images/           # PDF pages as PNG — not in repo
│   ├── processed_images/     # OpenCV output — not in repo
│   ├── cleaned_text/         # Raw OCR text — not in repo
│   ├── normalized_text/      # Unicode fixed — not in repo
│   └── chunks.json           # ✅ 687 semantic chunks
│
├── 📂 chroma_db/             # ✅ Vector store (shipped for deployment)
│
├── 📂 ingest/
│   ├── pdf_to_images.py      # Phase 1 — PDF → PNG
│   ├── preprocess_images.py  # Phase 2 — OpenCV
│   ├── ocr_surya.py          # Phase 3 — EasyOCR
│   ├── clean_text.py         # Phase 4 — Normalization
│   └── chunker.py            # Phase 5 — Chunking
│
├── 📂 vectorstore/
│   └── embed_and_store.py    # Embeddings → ChromaDB
│
├── 📂 rag/
│   └── rag_agent.py          # CLI RAG pipeline
│
├── app.py                    # ✅ Main Streamlit app
├── banner.svg                # ✅ Banner image
├── architecture.svg          # ✅ Architecture diagram
├── .env                      # API keys (not committed)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Poppler (for pdf2image)
- [Sarvam AI API key](https://dashboard.sarvam.ai)

### Setup

```bash
# 1. Clone
git clone https://github.com/Amruth011/kannada-rag-agent.git
cd kannada-rag-agent

# 2. Virtual environment
python -m venv kannada-rag-env
kannada-rag-env\Scripts\activate        # Windows
# source kannada-rag-env/bin/activate   # Mac/Linux

# 3. Install
pip install -r requirements.txt

# 4. Create .env file
SARVAM_API_KEY=your_key_here
ADMIN_PASSWORD=your_admin_password

# 5. Run
kannada-rag-env\Scripts\python.exe -m streamlit run app.py
```

Open **[http://localhost:8501](http://localhost:8501)** 🎉

---

## 🔄 Rebuild Pipeline from Scratch

<details>
<summary><b>Only needed if you want to re-process the original PDF — click to expand</b></summary>

<br/>

```bash
python pdf_to_images.py        # Phase 1 — PDF → 346 PNGs     (~5 min)
python preprocess_images.py    # Phase 2 — OpenCV denoise      (~3 min)
python ocr_surya.py            # Phase 3 — EasyOCR             (~3 hrs CPU)
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
| ✅ | Smart RAG agent | 4-strategy router · Sarvam-M LLM · memory |
| ✅ | Bilingual TTS | WAV stitching · kn-IN + en-IN · bulbul:v3 |
| ✅ | Production UI | Glassmorphism · chips · progress bar · feedback |
| ✅ | Live deployment | Public URL · Streamlit Cloud · secrets managed |
| ✅ | Admin system | Password-protected feedback viewer |

---

## 🙏 Acknowledgements

| | Project | Used For |
|:--|:--------|:---------|
| 🤖 | [Sarvam AI](https://sarvam.ai) | Indic LLM (Sarvam-M) + TTS (bulbul:v3) |
| 👁️ | [EasyOCR](https://github.com/JaidedAI/EasyOCR) | Kannada + English OCR |
| 🗄️ | [ChromaDB](https://www.trychroma.com/) | Vector database |
| 🔤 | [indic-nlp-library](https://github.com/anoopkunchukuttan/indic_nlp_library) | Kannada Unicode normalization |
| 🧠 | [sentence-transformers](https://www.sbert.net/) | Multilingual embeddings |
| 📚 | Ravi Belagere | Author of *ಹೇಳಿ ಹೋಗು ಕಾರಣ* |

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
