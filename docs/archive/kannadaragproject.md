# Kannada RAG Project: End-to-End Pipeline Breakdown

This document provides a complete, pin-to-pin explanation of how the Kannada RAG (Retrieval-Augmented Generation) agent operates from scratch. It explains how a raw, scanned Kannada PDF is processed into a searchable database and how the agent delivers bilingual, audio-enabled answers.

## Phase 1: From Scanned PDF to Clean Text (The OCR Pipeline)

Because the source material (*Heli Hogu Karana*) is a physical, scanned book, the text cannot be simply extracted like a digital PDF. The pipeline handles this through a multi-step image processing and OCR (Optical Character Recognition) workflow:

1. **PDF to Images (`pdf_to_images.py`)**: 
   - The 346-page PDF is split into 346 individual high-resolution PNG image files using `pdf2image`.

2. **Image Preprocessing (`preprocess_images.py`)**: 
   - Since scanned books often have shadows, dust, and ink bleeding through the pages, the raw images must be cleaned so the AI can read them.
   - **OpenCV** is used to apply Grayscale conversion, Adaptive Thresholding (to remove page shadows and bleed-through), Denoising (to remove specks), and Sharpening (to enhance the curves of Kannada letters).

3. **OCR Extraction (`ocr_surya.py`)**: 
   - The cleaned images are passed in batches to **Surya OCR**, a state-of-the-art deep learning model capable of handling both English and Kannada.
   - Surya detects bounding boxes around each line of text and translates the pixel patterns into raw Unicode strings, saving them into `.txt` files page by page.

4. **Normalization (`clean_text.py`)**: 
   - Finally, Kannada text is often prone to Unicode anomalies. The `indic-nlp-library` is used to normalize the text, ensuring all Kannada characters are standard and clean.

## Phase 2: Building the Knowledge Base

1. **Semantic Chunking (`chunker.py`)**: 
   - The cleaned text is broken down into small, searchable pieces called "chunks". 
   - Each chunk is set to 400 characters with a 50-character overlap.
   - Crucially, the script respects Kannada sentence boundaries (like the *danda* `।` and newlines) to avoid splitting context. This produces 687 semantic chunks from the whole book.

2. **Embedding and Storing (`embed_and_store.py`)**: 
   - The chunks are passed through a multilingual AI model (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`). This converts the text into numerical vectors (embeddings) that capture meaning regardless of the language.
   - These vectors, along with metadata (like page numbers), are stored in **ChromaDB**. 

## Phase 3: The RAG Agent & Output Generation

When a user asks a question, the agent performs the following steps to find and generate an answer.

1. **Query Routing & Vector Search**:
   - The user's query is also converted into a vector. The system calculates "cosine similarity" against ChromaDB to find the top chunks of text that match the meaning of the query.
   - It applies dynamic metadata filtering: if a user asks "What is on page 50?", the router detects this and pulls chunks exclusively from page 50 instead of searching the whole book.

2. **The LLM Dispatcher (Dual-Brain Architecture)**:
   - The system uses a fallback architecture for reliability. It first attempts to use **Gemini 1.5 Flash** via the Google API.
   - If Gemini is rate-limited or fails, the LangChain dispatcher automatically falls back to **Groq (Llama 3.3)** within milliseconds.
   - The relevant book chunks (the "context") are injected into the prompt alongside the user's question.

3. **Bilingual Output Generation**:
   - The RAG system operates through **LangChain LCEL (LangChain Expression Language)** which explicitly governs the output language.
   - Based on the user's selected language in the UI, the agent receives one of two strict System Prompts:
     - **English Selection**: `SYSTEM_PROMPT_EN` instructs the LLM: "Answer using the information above... Answer in English."
     - **Kannada Selection**: `SYSTEM_PROMPT_KN` instructs the LLM: "ಪುಸ್ತಕದಿಂದ ತೆಗೆದ ವಿಷಯ... ಕನ್ನಡದಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರಿಸಿ" (Using the extracted info... Answer strictly in Kannada).
   - Because the embedding model is multilingual, the user can ask a question in English, retrieve Kannada chunks, and have the LLM translate/synthesize the final answer back into English seamlessly, or vice-versa.

## Phase 4: Text-to-Speech (TTS) Integration

A key feature of this RAG pipeline is accessibility through voice. The TTS implementation is designed to handle bilingual outputs natively.

1. **Audio Synthesis via Sarvam AI**:
   - Once the LLM generates the text answer, it is forwarded to the **Sarvam AI TTS API** (specifically the `bulbul:v3` model, which features an Indian female voice named `priya`).
   - Sarvam is specialized for Indic languages, ensuring that the Kannada pronunciation is natural, rather than the robotic mispronunciations common in standard Western TTS engines.
   
2. **Audio Chunking and Stitching**:
   - If the LLM generates a long answer, the text is automatically chunked before being sent to the TTS engine to avoid API timeouts.
   - The resulting `.wav` audio pieces are stitched together sequentially and returned to the UI.
   - In case Sarvam's API is exhausted, the system contains a fast fallback to Google TTS (`gTTS`).

3. **Final Delivery**:
   - The user receives the AI-generated bilingual text answer, the exact page citations (metadata from ChromaDB), and a custom interactive HTML5 media player to listen to the RAG-generated audio output.

## Technologies, Tools & APIs Summary

Here is a consolidated list of the technologies powering this pipeline and where they are used:

| Technology/API | Category | Purpose / Where it is used |
| :--- | :--- | :--- |
| **pdf2image / Poppler** | Ingestion | Used offline in `pdf_to_images.py` to convert the scanned PDF into PNG files. |
| **OpenCV** | Preprocessing | Used offline in `preprocess_images.py` to denoise and adaptively threshold the raw images, removing shadows and bleed-through. |
| **Surya OCR** | OCR | Used offline in `ocr_surya.py` to detect text boxes and extract Kannada/English characters from the cleaned images into text files. |
| **indic-nlp-library** | Text Processing | Used offline in `clean_text.py` to normalize and fix Unicode anomalies in the Kannada text. |
| **Sentence-Transformers (Hugging Face)** | Embedding | Uses `paraphrase-multilingual-MiniLM-L12-v2` locally in `embed_and_store.py` to convert Kannada/English text chunks into multi-dimensional vectors. |
| **ChromaDB** | Database | Local vector database used to store the embedded chunks and their metadata (e.g., page numbers), allowing semantic similarity search during retrieval. |
| **LangChain** | Orchestration | The backbone framework used in `rag_agent.py` to define prompts (LCEL), wrap retrieval tools, manage conversational memory, and route between LLMs. |
| **Google Gemini API (1.5 Flash)** | Primary LLM | The main Large Language Model used by LangChain to read the retrieved contexts and generate the final answer in the requested language. |
| **Groq API (Llama 3.3)** | Secondary LLM | Used as a high-speed fallback in the dual-brain architecture to ensure reliability if the primary LLM hits rate limits. |
| **Sarvam AI API** | Text-to-Speech | Uses the `bulbul:v3` model to dynamically convert the LLM-generated bilingual text answers into highly natural Indic/Kannada `.wav` audio. |

### Deep Dive: Hugging Face & LangChain Integration

Both **Hugging Face** and **LangChain** act as the central nervous system for the AI portion of this pipeline:

#### Hugging Face (The "Understanding" Engine)
Hugging Face is utilized via its open-source embedding model (`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`). 
* **Why it is used**: LLMs cannot inherently search a database of text. Text must be converted into dense mathematical vectors so the system can calculate "semantic similarity".
* **Where it is used**: 
   * **Offline**: In `embed_and_store.py`, it reads all 687 text chunks and converts them into vectors for ChromaDB.
   * **Online**: During a query, it converts the user's question into a vector on the fly to find matching chunks.
* **The Magic**: This specific model is multilingual, meaning it understands that an English question and a Kannada passage share the same semantic vector space!

#### LangChain (The Orchestrator)
LangChain doesn't generate text itself; it acts as the manager that glues all APIs and databases into a cohesive RAG workflow.
* **Vector Store Wrapper**: It seamlessly connects to ChromaDB to pull the top chunks.
* **LCEL Prompting**: It uses LangChain Expression Language to build prompt templates (`SYSTEM_PROMPT_EN` and `SYSTEM_PROMPT_KN`), injecting the raw retrieved chunks and the user's query before sending it to the LLM.
* **Custom LLM Routing**: In `rag_agent_v2.py`, a custom `BilingualFallbackChatModel` intercepts the prompt and attempts to hit Gemini. If that fails, LangChain catches the error and instantly reroutes the payload to Groq.
* **Agent Tools**: It also wraps the semantic search into a standard LangChain `Tool`, enabling the system to act dynamically as a "ReAct Agent".
