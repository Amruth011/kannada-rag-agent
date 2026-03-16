# 📚 ಹೇಳಿ ಹೋಗು ಕಾರಣ — Kannada Book AI Agent

An end-to-end AI-powered RAG chatbot for the Kannada novel **"ಹೇಳಿ ಹೋಗು ಕಾರಣ" (Heli Hogu Karana)** by Ravi Belagere.
Ask questions in **Kannada or English** and get grounded answers with page citations and audio output.

🚀 **[Live Demo](https://kannada-rag-agent-hqvwhfejguymb9ijrvz4hd.streamlit.app/)**

---

## 🎯 Project Highlights

- **Scanned PDF → AI Chatbot** pipeline built entirely from scratch
- **Bilingual Q&A** — Kannada and English with conversational memory
- **Text-to-Speech** via Sarvam AI bulbul:v3 (Kannada & English audio)
- **346 pages** processed, **687 semantic chunks** indexed
- **Smart query routing** — characters, pages, general questions handled differently
- **Suggestion chips** — clickable quick-questions for easy exploration
- **Feedback system** — public feedback with private admin viewer
- Built as a portfolio project targeting **AI Engineer** roles

---

## 🏗️ Architecture

```
Scanned PDF (357MB)
      │
      ▼
PDF → Images (pdf2image + Poppler)
      │
      ▼
Image Preprocessing (OpenCV — denoise, threshold, sharpen)
      │
      ▼
OCR (EasyOCR — Kannada + English, CPU)
      │
      ▼
Unicode Normalization (indic-nlp-library)
      │
      ▼
Semantic Chunking (400 char chunks, 50 char overlap → 687 chunks)
      │
      ▼
Embeddings (paraphrase-multilingual-MiniLM-L12-v2)
      │
      ▼
Vector Store (ChromaDB — cosine similarity)
      │
      ▼
Smart Query Router (page / character / general / RAG)
      │
      ▼
RAG Agent (Sarvam-M LLM + conversational memory)
      │
      ▼
Glassmorphism Streamlit UI + Sarvam TTS Audio
```

---

## 🧠 Tech Stack

| Component | Technology |
|-----------|-----------|
| PDF Processing | pdf2image, Poppler |
| Image Preprocessing | OpenCV |
| OCR | EasyOCR (Kannada + English, CPU) |
| Text Normalization | indic-nlp-library |
| Embeddings | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| Vector Database | ChromaDB (cosine similarity) |
| LLM | Sarvam-M via Sarvam AI API |
| Text-to-Speech | Sarvam AI bulbul:v3 - priya speaker, WAV stitching |
| UI | Streamlit - custom glassmorphism CSS |
| Language | Python 3.13 |

---

## 📁 Project Structure

```
kannada-rag-agent/
├── data/
│   ├── raw_images/          # PDF pages as PNG (346 files, not in git)
│   ├── processed_images/    # Preprocessed images (not in git)
│   ├── cleaned_text/        # Raw OCR output (not in git)
│   ├── normalized_text/     # Unicode normalized text (not in git)
│   └── chunks.json          # 687 semantic chunks
├── chroma_db/               # ChromaDB vector store (shipped for deployment)
├── ingest/
│   ├── pdf_to_images.py     # Phase 1: PDF → images
│   ├── preprocess_images.py # Phase 2: OpenCV preprocessing
│   ├── ocr_surya.py         # Phase 3: EasyOCR
│   ├── clean_text.py        # Phase 4: Unicode normalization
│   └── chunker.py           # Phase 5: Semantic chunking
├── vectorstore/
│   └── embed_and_store.py   # Embeddings + ChromaDB
├── rag/
│   └── rag_agent.py         # RAG pipeline (CLI version)
├── app.py                   # Streamlit UI (main app)
├── .env                     # API keys (not committed)
├── .gitignore
└── requirements.txt
```

---

## 🚀 Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/Amruth011/kannada-rag-agent.git
cd kannada-rag-agent
```

### 2. Create virtual environment
```bash
python -m venv kannada-rag-env
# Windows:
kannada-rag-env\Scripts\activate
# Mac/Linux:
source kannada-rag-env/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
Create a `.env` file:
```
SARVAM_API_KEY=your_sarvam_api_key_here
ADMIN_PASSWORD=your_admin_password_here
```
Get your Sarvam key at [dashboard.sarvam.ai](https://dashboard.sarvam.ai)

### 5. Run the app
```bash
kannada-rag-env\Scripts\python.exe -m streamlit run app.py
```

---

## 🔄 Rebuild Pipeline (optional)

Only needed if you want to re-OCR or re-chunk from scratch:

```bash
python pdf_to_images.py       # PDF → PNG images
python preprocess_images.py   # OpenCV preprocessing(removing noise)
python ocr_surya.py           # EasyOCR → text files
python clean_text.py          # Unicode normalization
python chunker.py             # Chunking → chunks.json
python embed_and_store.py     # Embeddings → ChromaDB
streamlit run app.py          # Launch app
```

---

## 💡 Features

- **Smart query routing** — detects page queries, character questions, general book questions and routes each differently
- **Character retrieval** — uses high-recall RAG (top 10 chunks, threshold 0.2) for character questions
- **Page-specific queries** — "what is in page 50?" fetches directly from ChromaDB by page number
- **Conversational memory** — keeps last 4 messages for follow-up question context
- **Bilingual answers** — toggle between Kannada and English
- **Source citations** — every answer shows which pages were used
- **TTS audio** — answers read aloud with WAV chunk stitching for long responses
- **Suggestion chips** — 6 clickable quick-questions above the input box
- **Progress bar** — shows live steps: Searching → Retrieving → Building → Generating
- **Glassmorphism UI** — premium dark mode with glass cards, gradient bubbles, animations
- **Feedback system** — public form with star rating; admin-only viewer in sidebar
- **Source chunks toggle** — see raw retrieved passages with relevance scores

---

## 🗺️ Roadmap

- [x] PDF ingestion + OCR pipeline
- [x] ChromaDB vector store with cosine similarity
- [x] Sarvam-M RAG agent
- [x] Bilingual Streamlit UI
- [x] TTS with bulbul:v3 + WAV stitching
- [x] Smart query routing (page / character / general)
- [x] Conversational memory
- [x] Glassmorphism CSS UI
- [x] Suggestion chips + progress bar
- [x] Feedback system with admin viewer
- [x] Streamlit Cloud deployment
- [ ] Re-OCR with Surya for better Kannada accuracy
- [ ] Re-chunk with 800-char chunks for better context
- [ ] Mobile responsive layout
- [ ] Docker deployment
- [ ] Multi-book support

---

## 🙏 Acknowledgements

- [Sarvam AI](https://sarvam.ai) — Indic LLM + TTS
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — Kannada OCR
- [ChromaDB](https://www.trychroma.com/) — Vector store
- [indic-nlp-library](https://github.com/anoopkunchukuttan/indic_nlp_library) — Kannada Unicode normalization
- [sentence-transformers](https://www.sbert.net/) — Multilingual embeddings

---

## 👤 Author

**Amruth Kumar M** - AI Engineer  
[GitHub](https://github.com/Amruth011)
