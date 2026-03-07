# 📚 ಹೇಳಿ ಹೋಗು ಕಾರಣ — Kannada Book AI Agent

An end-to-end Premium AI-powered RAG chatbot for the Kannada novel **"ಹೇಳಿ ಹೋಗು ಕಾರಣ" (Heli Hogu Karana)** by Ravi Belagere.
Ask questions in **Kannada or English** and get grounded answers with page citations and flawless audio output.

🚀 **Current Version: v2.0.0 (Premium Architecture Upgrade)**
🌐 **[Live Premium Demo](https://kannada-rag-agent-hqvwhfejguymb9ijrvz4hd.streamlit.app/)**

---

## 🎯 Project Highlights

- **Scanned PDF → Premium AI Chatbot** pipeline built entirely from scratch
- **Bilingual Q&A** — Kannada and English with Conversational Memory
- **Flawless Text-to-Speech Streaming** via Sarvam AI (End-to-end stitched audio)
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
OCR (Surya OCR v0.17.1 — High Accuracy Batched Tensor Processing)
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
RAG Agent (Sarvam-M LLM with Chat History Memory)
      │
      ▼
Glassmorphism Premium Streamlit UI + Stitched Sarvam TTS Audio Streams
```

---

## 🧠 Tech Stack

| Component | Technology |
|-----------|-----------|
| PDF Processing | pdf2image, Poppler |
| Image Preprocessing | OpenCV |
| OCR | **Surya OCR v0.17.1** (GPU/CPU Batched Processing) |
| Text Normalization | indic-nlp-library |
| Embeddings | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
| Vector Database | ChromaDB |
| LLM | Sarvam-M (via Sarvam AI API) + Conversational Memory |
| Text-to-Speech | Sarvam AI bulbul:v3 (Kannada TTS with API Chunking & Stitching) |
| UI | **Streamlit with Custom $100k Glassmorphism CSS styling** |
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
│   ├── ocr_surya.py         # Phase 3: Surya OCR (Batched)
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

- **Conversational Memory** — The bot remembers chat history like ChatGPT for perfect follow-up questions.
- **Flawless TTS Streaming** — Backend dynamically splices 450-char blocks and stitches wav bytes to perfectly read 100% of large outputs.
- **Premium UI** — Dark mode glassmorphism overlays with vivid gradient response bubbles and hovering animations.
- **Smart query routing** — general questions use book knowledge, specific questions use RAG
- **Page-specific queries** — "what is in page 50?" fetches directly from that page
- **Bilingual answers** — switch between Kannada and English
- **Source citations** — every answer shows which pages were used
- **Source chunks** — toggle to see raw retrieved passages

---

## 🗺️ Roadmap (Completed ✅)

- [x] Fix Sarvam TTS audio API cutoff block limit (Implemented byte streaming)
- [x] Re-OCR with better preprocessing for cleaner text (Migrated to highly accurate Surya OCR)
- [x] Re-chunk with 800-char chunks for better context
- [x] Re-embed with improved chunks into ChromaDB
- [x] Implement Conversational Memory state for fluent context logic
- [x] Build an enterprise-grade UI using custom CSS

---

## 🙏 Acknowledgements

- [Sarvam AI](https://sarvam.ai) — Indic LLM + TTS
- [Surya OCR](https://github.com/VikParuchuri/surya) — High-Accuracy ML OCR Engine
- [ChromaDB](https://www.trychroma.com/) — Vector store
- [indic-nlp-library](https://github.com/anoopkunchukuttan/indic_nlp_library) — Kannada Unicode normalization

---

## 👤 Author

**Amruth** — AI Engineer  
[GitHub](https://github.com/Amruth011)