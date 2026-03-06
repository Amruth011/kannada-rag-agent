# 📚 ಹೇಳಿ ಹೋಗು ಕಾರಣ — Kannada Book AI Agent

An end-to-end AI-powered RAG chatbot for the Kannada novel **"ಹೇಳಿ ಹೋಗು ಕಾರಣ" (Heli Hogu Karana)** by Ravi Belagere.
Ask questions in **Kannada or English** and get grounded answers with page citations and audio output.

---

## 🎯 Project Highlights

- **Scanned PDF → AI Chatbot** pipeline built entirely from scratch
- **Bilingual Q&A** — Kannada and English
- **Text-to-Speech** via Sarvam AI (Kannada audio output)
- **346 pages** processed, **687 semantic chunks** indexed
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
OCR (EasyOCR — Kannada + English)
      │
      ▼
Unicode Normalization (indic-nlp-library)
      │
      ▼
Semantic Chunking (800 char chunks, 100 char overlap)
      │
      ▼
Embeddings (paraphrase-multilingual-MiniLM-L12-v2)
      │
      ▼
Vector Store (ChromaDB — cosine similarity)
      │
      ▼
RAG Agent (Sarvam-M LLM)
      │
      ▼
Streamlit UI + Sarvam TTS Audio
```

---

## 🧠 Tech Stack

| Component | Technology |
|-----------|-----------|
| PDF Processing | pdf2image, Poppler |
| Image Preprocessing | OpenCV |
| OCR | EasyOCR (Kannada + English) |
| Text Normalization | indic-nlp-library |
| Embeddings | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| Vector Database | ChromaDB |
| LLM | Sarvam-M (via Sarvam AI API) |
| Text-to-Speech | Sarvam AI bulbul:v3 (Kannada TTS) — *fix in progress* |
| UI | Streamlit |
| Language | Python 3.13 |

---

## 📁 Project Structure

```
kannada-rag-agent/
├── data/
│   ├── raw_images/          # PDF pages as PNG (346 files)
│   ├── processed_images/    # Preprocessed images
│   ├── cleaned_text/        # Raw OCR output
│   ├── normalized_text/     # Unicode normalized text
│   └── chunks.json          # 687 semantic chunks
├── chroma_db/               # ChromaDB vector store
├── ingest/
│   ├── pdf_to_images.py     # Phase 1: PDF → images
│   ├── preprocess_images.py # Phase 2: OpenCV preprocessing
│   ├── ocr_surya.py         # Phase 3: EasyOCR
│   ├── clean_text.py        # Phase 4: Unicode normalization
│   └── chunker.py           # Phase 5: Semantic chunking
├── vectorstore/
│   └── embed_and_store.py   # Embeddings + ChromaDB
├── rag/
│   └── rag_agent.py         # RAG pipeline
├── app.py                   # Streamlit UI
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
```
Get your key at [dashboard.sarvam.ai](https://dashboard.sarvam.ai)

### 5. Run the app
```bash
streamlit run app.py
```

---

## 🔄 Rebuild Pipeline (if needed)

Run these in order:
```bash
# 1. PDF to images
python pdf_to_images.py

# 2. Preprocess images
python preprocess_images.py

# 3. OCR
python ocr_surya.py

# 4. Normalize text
python clean_text.py

# 5. Chunk text
python chunker.py

# 6. Build vector store
python embed_and_store.py

# 7. Run app
streamlit run app.py
```

---

## 💡 Features

- **Smart query routing** — general questions use book knowledge, specific questions use RAG
- **Page-specific queries** — "what is in page 50?" fetches directly from that page
- **Bilingual answers** — switch between Kannada and English
- **Source citations** — every answer shows which pages were used
- **TTS audio** — answers read aloud in Kannada or English *(fix in progress)*
- **Source chunks** — toggle to see raw retrieved passages

---

## 🗺️ Roadmap

- [ ] Fix Sarvam TTS audio (bulbul:v3 speaker validation)
- [ ] Re-OCR with better preprocessing for cleaner text
- [ ] Re-chunk with 800-char chunks for better context
- [ ] Re-embed with improved chunks
- [ ] Docker deployment
- [ ] Add more Kannada books to the corpus

---

## 📸 Demo

> *Screenshots coming soon*

---

## 🙏 Acknowledgements

- [Sarvam AI](https://sarvam.ai) — Indic LLM + TTS
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) — Kannada OCR
- [ChromaDB](https://www.trychroma.com/) — Vector store
- [indic-nlp-library](https://github.com/anoopkunchukuttan/indic_nlp_library) — Kannada Unicode normalization

---

## 👤 Author

**Amruth** — AI Engineer  
[GitHub](https://github.com/Amruth011)