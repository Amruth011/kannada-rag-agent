# Kannada RAG Agent & Voice Assistant - Project File Catalog

An enterprise-grade, memory-optimized **Retrieval-Augmented Generation (RAG) Agent and Voice Assistant** specialized in Kannada literature, based on the Kannada novel *"ಹೇಳಿ ಹೋಗು ಕಾರಣ"* (*Heli Hogu Kaarana* - 346 pages).

---

## 📊 Project Statistics

- **Total Project Files**: 1,848 files
- **Total Project Directories**: 25 directories
- **Application & Core Scripts**: 78 Python scripts & config files
- **Extracted Page Data Assets**: 1,730 text & image page files (346-page pipeline)
- **Interactive Digital Readers**: 3 standalone HTML eBook applications
- **Documentation & Benchmarks**: 7 markdown specs, diagrams, and architecture guides

---

## 🗂️ Directory Tree

```text
kannada-rag-agent/
├── .devcontainer/              # VS Code Development Container setup
│   └── devcontainer.json
├── api/                        # FastAPI Serverless backend (Vercel deployment)
│   ├── cover.png
│   ├── data.json
│   ├── favicon.png
│   ├── index.py
│   └── data/
│       ├── cover.png
│       └── ebooks/             # HTML Readers served by FastAPI
│           ├── heli_hogu_karana_bilingual.html
│           ├── heli_hogu_karana_english.html
│           └── heli_hogu_karana_kannada.html
├── assets/                     # Repository branding & graphics
│   ├── banner.svg
│   └── favicon.png
├── chroma_db/                  # Persistent Vector Database (ChromaDB + HNSW)
│   ├── chroma.sqlite3
│   └── 03e0be5e-1e0c-.../      # HNSW index binaries (.bin)
├── data/                       # Novel PDF, processed chunks, & page datasets
│   ├── Heli hogu kaarana.pdf   # Scanned Kannada book (680.9 MB, 346 pages)
│   ├── chunks.json             # Processed semantic text chunks & page metadata
│   ├── cover.png               # High-res novel cover image
│   ├── eval_dataset.json       # Benchmark evaluation dataset for RAGAS
│   ├── feedback.json           # User query feedback log
│   ├── raw_images/             # 346 raw page PNGs extracted from PDF
│   ├── processed_images/       # 346 deskewed/denoised images for OCR
│   ├── cleaned_text/           # 346 OCR-extracted text files + summary
│   ├── normalized_text/        # 345 cleaned & normalized Kannada text pages + summary
│   ├── english_translated/     # 345 machine-translated English text pages + summary
│   └── ebooks/                 # Standalone interactive eBook readers (3 HTML files)
├── deploy_dist/                # Serverless deployment bundle (Vercel lightweight distribution)
│   ├── requirements.txt
│   ├── vercel.json
│   ├── api/
│   │   ├── data.json
│   │   ├── index.py
│   │   └── vectors.npz         # Precomputed NumPy embeddings (bypasses heavy PyTorch)
│   └── public/
│       └── index.html
├── docs/                       # Architectural & evaluation documentation
│   ├── architecture.md
│   ├── benchmarks.md
│   ├── deployment.md
│   ├── evaluation.md
│   └── archive/
│       ├── system_design.md
│       └── assets/
│           ├── architecture.mmd
│           └── architecture.svg
├── scripts/
│   ├── ingest/                 # 6-step data ingestion & embedding pipeline
│   ├── eval/                   # 4 RAGAS, Hybrid search & Re-ranking benchmark scripts
│   └── utils/                  # 6 database export, page mapping, & model verification tools
├── scratch/                    # 46 R&D experiments (TTS, profiling, text fixes, compilers)
└── [Root Config Files]         # App, Procfile, Render, Vercel, requirements, and env files
```

---

## 1. Root Configuration & Application Core

| File | Size | Role & Description |
| :--- | :--- | :--- |
| [app.py](file:///d:/personal%20files/Projects/kannada-rag-agent/app.py) | 65.1 KB | **Main Streamlit Web Application**: Local/Cloud frontend providing bilingual UI (Kannada/English), conversational chat, voice recording and synthesis (gTTS / Sarvam), page-by-page explorer, hybrid search retriever, and guardrails against hallucination. |
| [requirements.txt](file:///d:/personal%20files/Projects/kannada-rag-agent/requirements.txt) | 230 B | Core Python dependencies (Streamlit, ChromaDB, LangChain, Groq, Google Generative AI, gTTS). |
| [streamlit_requirements.txt](file:///d:/personal%20files/Projects/kannada-rag-agent/streamlit_requirements.txt) | 392 B | Tailored, pinned requirements file for deployment on Streamlit Community Cloud. |
| [packages.txt](file:///d:/personal%20files/Projects/kannada-rag-agent/packages.txt) | 34 B | Linux system packages (`ffmpeg`, `libgl1`) required for audio decoding and image manipulation on cloud hosts. |
| [runtime.txt](file:///d:/personal%20files/Projects/kannada-rag-agent/runtime.txt) | 14 B | Declares Python runtime (`python-3.11.9`) for cloud build environments. |
| [vercel.json](file:///d:/personal%20files/Projects/kannada-rag-agent/vercel.json) | 266 B | Vercel serverless routing configuration routing all web requests to `/api/index.py`. |
| [render.yaml](file:///d:/personal%20files/Projects/kannada-rag-agent/render.yaml) | 421 B | Infrastructure-as-code specification for deploying the application as a persistent web service on Render. |
| [Procfile](file:///d:/personal%20files/Projects/kannada-rag-agent/Procfile) | 71 B | Startup command (`web: streamlit run app.py`) for PaaS deployment environments. |
| [.env](file:///d:/personal%20files/Projects/kannada-rag-agent/.env) | 241 B | Local environment file holding confidential API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`, `SARVAM_API_KEY`, KV credentials). |
| [.env.example](file:///d:/personal%20files/Projects/kannada-rag-agent/.env.example) | 480 B | Template documenting all mandatory and optional environment variables. |
| [.gitignore](file:///d:/personal%20files/Projects/kannada-rag-agent/.gitignore) | 485 B | Git ignore rules excluding virtual environments, raw image folders, credentials, and local caches. |
| [.gitattributes](file:///d:/personal%20files/Projects/kannada-rag-agent/.gitattributes) | 241 B | Configures Git line endings and binary attributes. |
| [.vercelignore](file:///d:/personal%20files/Projects/kannada-rag-agent/.vercelignore) | 438 B | Prevents bulky raw assets, docs, and intermediate data files from exceeding Vercel's serverless function size limits. |
| [.devcontainer/devcontainer.json](file:///d:/personal%20files/Projects/kannada-rag-agent/.devcontainer/devcontainer.json) | 280 B | VS Code Dev Container definition for a standardized containerized development environment. |
| [README.md](file:///d:/personal%20files/Projects/kannada-rag-agent/README.md) | 8.8 KB | Main project documentation detailing system architecture, live demo links, problem statement, and setup steps. |
| [CONTRIBUTING.md](file:///d:/personal%20files/Projects/kannada-rag-agent/CONTRIBUTING.md) | 1.4 KB | Development guidelines, pull-request requirements, and code style conventions. |
| [CODE_OF_CONDUCT.md](file:///d:/personal%20files/Projects/kannada-rag-agent/CODE_OF_CONDUCT.md) | 1.8 KB | Contributor Covenant Code of Conduct. |
| [SECURITY.md](file:///d:/personal%20files/Projects/kannada-rag-agent/SECURITY.md) | 1.4 KB | Security guidelines and vulnerability reporting policy. |
| [LICENSE](file:///d:/personal%20files/Projects/kannada-rag-agent/LICENSE) | 1.1 KB | MIT Open Source License. |

---

## 2. Serverless API Layer (`api/`)

Optimized FastAPI deployment engineered to operate within Vercel's 250 MB serverless ceiling:

| File | Size | Role & Description |
| :--- | :--- | :--- |
| [api/index.py](file:///d:/personal%20files/Projects/kannada-rag-agent/api/index.py) | 326.3 KB | **Production FastAPI Serverless App**: Full backend serving embedded web UI, REST API endpoints (`/api/query`, `/api/tts`, `/api/page/{n}`, `/api/feedback`, `/api/analytics`), Upstash/Vercel KV persistence, and Sarvam/Gemini integration. |
| [api/data.json](file:///d:/personal%20files/Projects/kannada-rag-agent/api/data.json) | 1.9 MB | Serialized metadata and text chunks enabling serverless search without launching heavy external database engines. |
| [api/cover.png](file:///d:/personal%20files/Projects/kannada-rag-agent/api/cover.png) | 1.0 MB | Book cover graphic served by the web interface. |
| [api/favicon.png](file:///d:/personal%20files/Projects/kannada-rag-agent/api/favicon.png) | 266.2 KB | Web application favicon. |
| [api/data/cover.png](file:///d:/personal%20files/Projects/kannada-rag-agent/api/data/cover.png) | 1.0 MB | Cover image embedded within the standalone eBook readers. |
| [api/data/ebooks/heli_hogu_karana_kannada.html](file:///d:/personal%20files/Projects/kannada-rag-agent/api/data/ebooks/heli_hogu_karana_kannada.html) | 3.3 MB | Interactive digital reader for the full 345-page Kannada novel with font customization and search. |
| [api/data/ebooks/heli_hogu_karana_english.html](file:///d:/personal%20files/Projects/kannada-rag-agent/api/data/ebooks/heli_hogu_karana_english.html) | 2.2 MB | Interactive digital reader for the complete English translation of the novel. |
| [api/data/ebooks/heli_hogu_karana_bilingual.html](file:///d:/personal%20files/Projects/kannada-rag-agent/api/data/ebooks/heli_hogu_karana_bilingual.html) | 4.2 MB | Synchronized dual-column reader displaying original Kannada on the left and English translation on the right. |

---

## 3. Data Processing & Ingestion Pipeline (`scripts/ingest/`)

The 6-stage ingestion pipeline transforming raw scanned PDF pages into indexed embeddings:

| Stage & Script | Size | Function in Ingestion Pipeline |
| :--- | :--- | :--- |
| **Stage 1**: [scripts/ingest/pdf_to_images.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/ingest/pdf_to_images.py) | 2.4 KB | Converts the source PDF into 300 DPI high-resolution PNG images (`data/raw_images/page_0001.png` - `page_0346.png`). |
| **Stage 2**: [scripts/ingest/preprocess_images.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/ingest/preprocess_images.py) | 2.9 KB | Preprocesses images with adaptive thresholding, deskewing, and noise removal for maximum OCR readability (`data/processed_images/`). |
| **Stage 3**: [scripts/ingest/ocr_surya.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/ingest/ocr_surya.py) | 4.0 KB | Executes the Surya OCR model to extract Kannada text line-by-line (`data/cleaned_text/`). |
| **Stage 4**: [scripts/ingest/clean_text.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/ingest/clean_text.py) | 2.9 KB | Normalizes Kannada Unicode glyphs, cleans OCR artifacts, and standardizes punctuation (`data/normalized_text/`). |
| **Stage 5**: [scripts/ingest/chunker.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/ingest/chunker.py) | 4.1 KB | Executes sliding-window semantic chunking with page-number metadata retention (`data/chunks.json`). |
| **Stage 6**: [scripts/ingest/embed_and_store.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/ingest/embed_and_store.py) | 3.1 KB | Generates multilingual dense embeddings and indexes them into ChromaDB (`chroma_db/`). |

---

## 4. Evaluation & Benchmarking Suite (`scripts/eval/`)

Rigorous evaluation scripts verifying retrieval precision and hallucination prevention:

| Script | Size | Focus Area & Metric |
| :--- | :--- | :--- |
| [scripts/eval/eval_ragas.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/eval/eval_ragas.py) | 7.9 KB | Computes automated **RAGAS** metrics across the test dataset: Faithfulness (0.92), Answer Relevancy (0.88), Context Precision (0.85), Context Recall (0.89). |
| [scripts/eval/eval_hybrid.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/eval/eval_hybrid.py) | 6.4 KB | Benchmarks BM25 sparse keyword search vs. ChromaDB dense semantic vector search vs. Reciprocal Rank Fusion (RRF). |
| [scripts/eval/eval_reranking.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/eval/eval_reranking.py) | 9.0 KB | Measures precision gains when passing candidate chunks through a Cross-Encoder re-ranker. |
| [scripts/eval/eval_query_rewriting.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/eval/eval_query_rewriting.py) | 7.3 KB | Evaluates conversational query expansion, Kannada transliteration, and intent normalization. |

---

## 5. Utilities & Verification Tools (`scripts/utils/`)

| Script | Size | Purpose |
| :--- | :--- | :--- |
| [scripts/utils/deploy_prepare.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/utils/deploy_prepare.py) | 1.1 KB | Generates deployable serverless packages by exporting vectors and chunk metadata. |
| [scripts/utils/export_db.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/utils/export_db.py) | 878 B | Dumps ChromaDB embeddings and metadata into lightweight `.npz` and `.json` formats. |
| [scripts/utils/verify_page_mapping.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/utils/verify_page_mapping.py) | 2.3 KB | Verifies that all indexed chunks correctly map to their physical novel page numbers. |
| [scripts/utils/verify_setup.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/utils/verify_setup.py) | 2.9 KB | Smoke-tests the environment, verifying dependencies, CUDA availability, and API keys. |
| [scripts/utils/download_model.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/utils/download_model.py) | 629 B | Downloads embedding models to a local cache to prevent cold-start download delays. |
| [scripts/utils/analyze_page_100.py](file:///d:/personal%20files/Projects/kannada-rag-agent/scripts/utils/analyze_page_100.py) | 2.9 KB | Diagnostic script inspecting OCR fidelity and chunk boundaries on test page 100. |

---

## 6. Architecture & System Documentation (`docs/`)

| Document | Size | Description |
| :--- | :--- | :--- |
| [docs/architecture.md](file:///d:/personal%20files/Projects/kannada-rag-agent/docs/architecture.md) | 3.0 KB | Comprehensive explanation of the query router, RRF hybrid retrieval, cross-encoder re-ranking, and TTS architecture. |
| [docs/benchmarks.md](file:///d:/personal%20files/Projects/kannada-rag-agent/docs/benchmarks.md) | 2.5 KB | Retrieval latencies, memory footprints, and inference response-time benchmarks. |
| [docs/deployment.md](file:///d:/personal%20files/Projects/kannada-rag-agent/docs/deployment.md) | 2.3 KB | Production deployment manual covering Vercel, Streamlit Cloud, and Render setups. |
| [docs/evaluation.md](file:///d:/personal%20files/Projects/kannada-rag-agent/docs/evaluation.md) | 2.2 KB | Detailed breakdown of the RAGAS evaluation methodology and results. |
| [docs/archive/system_design.md](file:///d:/personal%20files/Projects/kannada-rag-agent/docs/archive/system_design.md) | 13.8 KB | Original system design document and historical specifications. |
| [docs/archive/assets/architecture.mmd](file:///d:/personal%20files/Projects/kannada-rag-agent/docs/archive/assets/architecture.mmd) | 1.9 KB | Mermaid diagram source code of the system architecture. |
| [docs/archive/assets/architecture.svg](file:///d:/personal%20files/Projects/kannada-rag-agent/docs/archive/assets/architecture.svg) | 17.7 KB | Vector architecture diagram graphic. |

---

## 7. Corpora & Text Stores (`data/` & `chroma_db/`)

### Core Corpora Files
- [data/Heli hogu kaarana.pdf](file:///d:/personal%20files/Projects/kannada-rag-agent/data/Heli%20hogu%20kaarana.pdf) (680.9 MB): Source scanned PDF of the Kannada novel (346 pages).
- [data/chunks.json](file:///d:/personal%20files/Projects/kannada-rag-agent/data/chunks.json) (1.98 MB): Semantic chunks with token overlap and page metadata for RAG indexing.
- [data/cover.png](file:///d:/personal%20files/Projects/kannada-rag-agent/data/cover.png) (1.0 MB): High-resolution book cover image.
- [data/eval_dataset.json](file:///d:/personal%20files/Projects/kannada-rag-agent/data/eval_dataset.json) (1.4 KB): Golden evaluation dataset of questions and ground-truth answers.
- [data/feedback.json](file:///d:/personal%20files/Projects/kannada-rag-agent/data/feedback.json) (131 B): Recorded user query feedback ratings.

### Page-by-Page Ingestion Stages
- `data/raw_images/` (346 files, ~960.5 MB): `page_0001.png` to `page_0346.png` extracted at 300 DPI from PDF.
- `data/processed_images/` (346 files, ~56.3 MB): `page_0001.png` to `page_0346.png` contrast-enhanced, deskewed, and binarized for OCR.
- `data/cleaned_text/` (347 files, ~1.8 MB): `page_0001.txt` to `page_0346.txt` containing OCR-extracted Kannada text + `_ocr_summary.json`.
- `data/normalized_text/` (346 files, ~1.8 MB): `page_0001.txt` to `page_0345.txt` containing cleaned, normalized text + `_clean_summary.json`.
- `data/english_translated/` (346 files, ~0.7 MB): `page_0001.txt` to `page_0345.txt` containing full English translation + `_translation_summary.json`.
- `data/ebooks/`: Master copy of the 3 standalone HTML readers (`heli_hogu_karana_kannada.html`, `heli_hogu_karana_english.html`, `heli_hogu_karana_bilingual.html`).

### Vector Storage
- [chroma_db/chroma.sqlite3](file:///d:/personal%20files/Projects/kannada-rag-agent/chroma_db/chroma.sqlite3) (14.2 MB): SQLite database storing collections, metadata, and chunk mappings.
- `chroma_db/03e0be5e-1e0c-4bd9-921d-370df123adf9/`: HNSW graph index files (`data_level0.bin`, `header.bin`, `length.bin`, `link_list.bin`) for high-speed approximate nearest neighbor search.

---

## 8. Serverless Distribution Bundle (`deploy_dist/`)

Lightweight deployment artifact designed to deploy to serverless platforms without heavy ML libraries:

| File | Size | Role |
| :--- | :--- | :--- |
| [deploy_dist/vercel.json](file:///d:/personal%20files/Projects/kannada-rag-agent/deploy_dist/vercel.json) | 233 B | Serverless routing config. |
| [deploy_dist/requirements.txt](file:///d:/personal%20files/Projects/kannada-rag-agent/deploy_dist/requirements.txt) | 216 B | Lightweight serverless dependencies (`fastapi`, `numpy`, `requests`). |
| [deploy_dist/api/index.py](file:///d:/personal%20files/Projects/kannada-rag-agent/deploy_dist/api/index.py) | 58.7 KB | Serverless endpoint using NumPy cosine similarity over precomputed embeddings. |
| [deploy_dist/api/data.json](file:///d:/personal%20files/Projects/kannada-rag-agent/deploy_dist/api/data.json) | 1.9 MB | Serialized chunks and metadata. |
| [deploy_dist/api/vectors.npz](file:///d:/personal%20files/Projects/kannada-rag-agent/deploy_dist/api/vectors.npz) | 1.7 MB | Precomputed embedding vectors stored as compressed NumPy arrays. |
| [deploy_dist/public/index.html](file:///d:/personal%20files/Projects/kannada-rag-agent/deploy_dist/public/index.html) | 31 B | Public static entrypoint. |

---

## 9. Research, Experiments & Diagnostics (`scratch/` - 46 files)

The `scratch/` folder contains exploratory tools, audio tests, RAM benchmarks, and text-cleaning scripts:

### Audio & Speech Synthesis Tests
- `test_tts.py`: Sarvam AI Kannada TTS API latency and audio synthesis test.
- `test_gtts.py`: Google Text-to-Speech (gTTS) generation benchmark in Kannada.
- `test_parallel_gtts.py`: Multithreaded chunked TTS generation test.
- `test_index_tts.py`: Validates FastAPI TTS endpoint streaming.
- `test_voice.py`: Verifies audio stream parameters and sample headers.
- `test_en.mp3`, `test_kn.mp3`, `test_out.mp3`, `test_parallel_out.mp3`: Output audio samples generated during testing.

### Translation & LLM Experiments
- `translate_book.py`: Batch translation pipeline translating all 345 Kannada pages to English using LLMs.
- `test_single_translation.py`: Evaluates single-page translation quality and formatting.
- `list_groq_models.py`: Queries Groq API to enumerate current inference models.
- `test_models.py`: Runs comparative generation across multiple LLM endpoints.
- `test_gemini_35.py`: Tests Google Gemini API calls.
- `test_gemini_lite.py`: Tests lightweight Gemini configurations.
- `test_gemini_kn_clean.py`: Tests Gemini for cleaning OCR-corrupted Kannada characters.
- `test_groq_clean.py`: Tests Groq LLaMA models for OCR cleanup.
- `test_groq_en_clean.py`: Tests English translation cleanup via Groq.
- `test_groq_kn_few_shot.py`: Few-shot prompting experiment for Kannada text restoration.

### eBook Compilers & Text Cleansing
- `compile_ebook.py`: Master compiler generating self-contained HTML readers with embedded styling, search, and navigation.
- `compile_all_subpages.py`: Compiles page sets into interactive HTML modules.
- `build_pages.py`: Generates HTML page structures from raw text files.
- `generate_subpages.py`: Generates subpage HTML components.
- `rewrite_compile.py`: Compiles refined and cleaned text into final eBook formats.
- `deduplicate_paragraphs.py`: Removes duplicate text segments resulting from overlapping OCR captures.
- `deloop_english_pages.py`: Eliminates repetition loops in machine-translated English pages.
- `fix_book_content.py`: Fixes encoding and formatting issues in the extracted text.
- `fix_book_content_v2.py`: Second-generation text repair script with enhanced regex and Unicode handling.
- `fix_index.py`: Script to patch index endpoints and metadata mappings.
- `modify_index.py`: Script for updating the embedded HTML and API handlers in `index.py`.
- `inject_privacy.py`: Script to inject privacy and security headers/disclaimers into the web UI.
- `live_page.html`: Sample HTML template used during reader UI development.

### Memory & Performance Profiling
- `profile_memory.py`: Measures RAM consumption across the retrieval pipeline.
- `profile_imports.py`: Times Python module import overhead.
- `profile_single_load.py`: Profiles memory spikes during single vector model loading.
- `trace_imports.py`: Traces dependency import chains.
- `test_threads_ram.py`: Analyzes memory behavior under multithreaded query loads.
- `test_threads_large_reranker_ram.py`: Profiles memory footprint when running heavy cross-encoder rerankers in threads.
- `test_reranker_ram.py`: Evaluates RAM requirements for cross-encoder rerankers.
- `test_mock_transformers.py`: Tests mocking of transformer libraries to minimize serverless footprint.
- `test_b64.py`: Tests base64 serialization for audio and vector transport.
- `test_clean_page.py`: Unit test verifying single-page text cleaner.
- `analyze_pages.py`: Scans all extracted page texts and generates statistical quality reports.
- `analysis_report.txt`: Output text report detailing page lengths, missing characters, and OCR anomalies.
- `inspect_out.txt`: Diagnostic log from test executions.
