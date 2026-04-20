# api/index.py - FastAPI version for Vercel deployment
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import re
import base64
import requests
import json
import io
import wave
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
COLLECTION = "kannada_book"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

BOOK_CONTEXT = """
Book Title  : ಹೇಳಿ ಹೋಗು ಕಾರಣ (Heli Hogu Karana — meaning "Tell the reason before you go")
Author      : ರವಿ ಬೆಳಗೆರೆ (Ravi Belagere) — prominent Kannada journalist and bold social writer based in Bengaluru
Publisher   : Bhavana Prakashan, Bengaluru (#2, 80 Aadi Raste, Banashankari 2nd Stage)
Language    : Kannada | Genre: Novel (ಕಾದಂಬರಿ) | Pages: 346

Title meaning: "ಹೇಳಿ ಹೋಗು ಕಾರಣ" means "Tell the reason before you go" — a moral challenge
posed to characters who leave without explanation or abandon their responsibilities.

Theme: The novel explores philosophical and existential themes — human morality, guilt,
truth-telling, the relationship between humans and the divine, and moral accountability.
Style: Bold journalistic prose, episodic structure, multiple philosophical perspectives.
Key themes: Human deception, divine justice, moral accountability, existential questioning, social critique.

Known characters in this novel: ಹಿಮವಂತ (Himavant) is the main protagonist. ಪ್ರಾರ್ಥನಾ (Prarthana) is his wife. Their relationship is central to the story.
"""

# General book/author questions — answered from BOOK_CONTEXT only
GENERAL_PATTERNS = [
    r'what is (this|the) book',
    r'about (this|the) book',
    r'book (about|summary|theme)',
    r'who (is|wrote|is the author).*ravi',
    r'ravi belagere',
    r'author',
    r'ಪುಸ್ತಕ(ದ|ವು|ದ ಬಗ್ಗೆ)',
    r'ಕಾದಂಬರಿ',
    r'ರವಿ ಬೆಳಗೆರೆ',
    r'ವಿಷಯ ಏನು',
    r'ಯಾರು ಬರೆದ',
    r'ಮುಖ್ಯ ವಿಷಯ',
    r'summary',
    r'theme',
    r'title mean',
    r'ಶೀರ್ಷಿಕೆ',
]

# Character questions — answered from RAG retrieval
CHARACTER_PATTERNS = [
    r'himavant', r'prarthana', r'pratana', r'prathana',
    r'ಹಿಮವಂತ', r'ಪ್ರಾರ್ಥನಾ',
    r'main character', r'protagonist', r'ಮುಖ್ಯ ಪಾತ್ರ',
    r'who is', r'who are', r'character', r'ಪಾತ್ರ',
    r'wife', r'husband', r'ಹೆಂಡತಿ', r'ಗಂಡ',
    r'relationship', r'ಸಂಬಂಧ', r'name of', r'tell me about',
]

app = FastAPI(title="Kannada Book AI Agent", description="AI Agent for Kannada Novel")

# Global variables for caching
embed_model = None
collection = None

class ChatRequest(BaseModel):
    question: str
    language: str = "English"
    show_chunks: bool = False
    enable_tts: bool = False

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    chunks: List[dict] = []
    audio_available: bool = False

def is_general_question(q):
    return any(re.search(p, q, re.IGNORECASE) for p in GENERAL_PATTERNS)

def is_character_question(q):
    return any(re.search(p, q, re.IGNORECASE) for p in CHARACTER_PATTERNS)

def load_agent():
    global embed_model, collection
    if embed_model is None or collection is None:
        from sentence_transformers import SentenceTransformer
        import chromadb
        embed_model = SentenceTransformer(MODEL_NAME)
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        try:
            collection = client.get_collection(COLLECTION)
        except Exception:
            collection = client.get_or_create_collection(
                COLLECTION, metadata={"hnsw:space": "cosine"}
            )
    return embed_model, collection

def retrieve(query, embed_model, collection, top_k=5):
    qe = embed_model.encode([query])[0].tolist()
    results = collection.query(query_embeddings=[qe], n_results=top_k)
    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        score = 1 - results["distances"][0][i]
        if score >= 0.25:
            chunks.append({
                "text": doc,
                "page": results["metadatas"][0][i]["page"],
                "score": round(score, 3)
            })
    return chunks

def retrieve_character(query, embed_model, collection):
    """Higher recall retrieval for character questions — more chunks, lower threshold."""
    qe = embed_model.encode([query])[0].tolist()
    results = collection.query(query_embeddings=[qe], n_results=10)
    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        score = 1 - results["distances"][0][i]
        if score >= 0.20:
            chunks.append({
                "text": doc,
                "page": results["metadatas"][0][i]["page"],
                "score": round(score, 3)
            })
    return chunks

def retrieve_by_page(page_num, collection):
    results = collection.get(where={"page": page_num}, limit=5)
    return [{"text": d, "page": m["page"], "score": 1.0}
            for d, m in zip(results["documents"], results["metadatas"])]

def detect_page_query(question):
    m = re.search(r'page\s*(\d+)|ಪುಟ\s*(\d+)|(\d+)\s*(?:page|ಪುಟ)', question, re.IGNORECASE)
    if m:
        return int(next(g for g in m.groups() if g))
    return None

def build_prompt(question, chunks, language, use_book_context_only=False):
    rag_section = "" if use_book_context_only else (
        "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks])
        if chunks else "(No specific passages retrieved.)"
    )
    if language == "English":
        return f"""You are an AI assistant for the Kannada novel "Heli Hogu Karana".

BOOK INFORMATION:
{BOOK_CONTEXT}

{"" if use_book_context_only else f"RETRIEVED PASSAGES FROM BOOK:{chr(10)}{rag_section}{chr(10)}"}
Answer the question using the information above. Be informative and helpful.
{"" if use_book_context_only else "Cite page numbers when using retrieved passages."}

QUESTION: {question}

ANSWER in English:"""
    else:
        return f"""ನೀವು "ಹೇಳಿ ಹೋಗು ಕಾರಣ" ಕನ್ನಡ ಕಾದಂಬರಿಯ AI ಸಹಾಯಕರು.

ಪುಸ್ತಕದ ಮಾಹಿತಿ:
{BOOK_CONTEXT}

{"" if use_book_context_only else f"ಪುಸ್ತಕದಿಂದ ತೆಗೆದ ವಿಷಯ:{chr(10)}{rag_section}{chr(10)}"}
ಮೇಲಿನ ಮಾಹಿತಿ ಬಳಸಿ ಕನ್ನಡದಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರಿಸಿ.

ಪ್ರಶ್ನೆ: {question}

ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರ:"""

def call_sarvam_llm(messages):
    if not SARVAM_API_KEY:
        return "⚠️ SARVAM_API_KEY not set in .env"
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "sarvam-m",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 600
    }
    resp = requests.post(
        "https://api.sarvam.ai/v1/chat/completions",
        headers=headers, json=payload, timeout=30
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()

def call_sarvam_tts(text, language="kn-IN"):
    if not SARVAM_API_KEY:
        return None
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    clean = re.sub(r'\[Page \d+\]:', '', text).strip()
    words = clean.split()
    chunks_list, current = [], ""
    for word in words:
        if len(current) + len(word) + 1 < 450:
            current += (" " if current else "") + word
        else:
            if current: chunks_list.append(current)
            current = word
    if current: chunks_list.append(current)

    audio_bytes_list = []
    for chunk in chunks_list:
        if not chunk.strip(): continue
        payload = {
            "inputs": [chunk.strip()],
            "target_language_code": language,
            "speaker": "priya",
            "model": "bulbul:v3",
            "pace": 1.0
        }
        resp = requests.post(
            "https://api.sarvam.ai/text-to-speech",
            headers=headers, json=payload, timeout=60
        )
        if resp.status_code == 200:
            audio_bytes_list.append(base64.b64decode(resp.json()["audios"][0]))

    if not audio_bytes_list:
        return None

    output_wav = io.BytesIO()
    with wave.open(output_wav, 'wb') as wav_out:
        for i, ab in enumerate(audio_bytes_list):
            seg = io.BytesIO(ab)
            try:
                with wave.open(seg, 'rb') as wav_in:
                    if i == 0: wav_out.setparams(wav_in.getparams())
                    wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))
            except wave.Error:
                continue
    return output_wav.getvalue()

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ಹೇಳಿ ಹೋಗು ಕಾರಣ — AI Agent</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
            * { font-family: 'Plus Jakarta Sans', sans-serif; }
            body {
                background: radial-gradient(circle at 15% 50%, #130b29, #09090e 50%, #050a16 100%);
                color: #e2e8f0;
                margin: 0;
                padding: 2rem;
                min-height: 100vh;
            }
            .container { max-width: 800px; margin: 0 auto; }
            h1 {
                background: linear-gradient(to right, #38bdf8, #c084fc, #f472b6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                font-weight: 800;
                font-size: 3rem;
                margin-bottom: 1rem;
            }
            .form-container {
                background: rgba(255,255,255,0.02);
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 20px;
                padding: 2rem;
                backdrop-filter: blur(20px);
            }
            input, select, button {
                width: 100%;
                padding: 1rem;
                margin: 0.5rem 0;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 12px;
                background: rgba(255,255,255,0.04);
                color: #e2e8f0;
                font-size: 1rem;
            }
            button {
                background: linear-gradient(135deg, rgba(139,92,246,0.2) 0%, rgba(236,72,153,0.1) 100%);
                border: 1px solid rgba(139,92,246,0.3);
                cursor: pointer;
                font-weight: 600;
                transition: all 0.2s;
            }
            button:hover {
                border-color: #8b5cf6;
                box-shadow: 0 0 15px rgba(139,92,246,0.3);
                transform: translateY(-1px);
            }
            .response {
                background: rgba(20,20,35,0.4);
                border: 1px solid rgba(255,255,255,0.03);
                border-radius: 20px;
                padding: 1.5rem;
                margin: 1rem 0;
                line-height: 1.6;
            }
            .sources { color: #94a3b8; font-size: 0.9rem; margin-top: 0.5rem; }
            .chips { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 1rem 0; }
            .chip {
                background: rgba(255,255,255,0.04);
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 999px;
                padding: 0.3rem 0.9rem;
                font-size: 0.8rem;
                cursor: pointer;
                transition: all 0.2s;
            }
            .chip:hover {
                background: rgba(139,92,246,0.15);
                border-color: rgba(139,92,246,0.4);
                color: #c084fc;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 ಹೇಳಿ ಹೋಗು ಕಾರಣ</h1>
            <p>Premium AI Knowledge Agent</p>
            
            <div class="form-container">
                <div class="chips">
                    <div class="chip" onclick="setQuestion('What is this book about?')">What is this book about?</div>
                    <div class="chip" onclick="setQuestion('Who is Himavant?')">Who is Himavant?</div>
                    <div class="chip" onclick="setQuestion('Who is Prarthana?')">Who is Prarthana?</div>
                    <div class="chip" onclick="setQuestion('What is in page 50?')">What is in page 50?</div>
                    <div class="chip" onclick="setQuestion('ಹಿಮವಂತ ಯಾರು?')">ಹಿಮವಂತ ಯಾರು?</div>
                    <div class="chip" onclick="setQuestion('ಕಾದಂಬರಿ ವಿಷಯ ಏನು?')">ಕಾದಂಬರಿ ವಿಷಯ ಏನು?</div>
                </div>
                
                <form id="chatForm">
                    <input type="text" id="question" placeholder="Ask about the book... (ಪ್ರಶ್ನೆ ಕೇಳಿ...)" required>
                    <select id="language">
                        <option value="English">English</option>
                        <option value="Kannada">Kannada</option>
                    </select>
                    <label style="display: block; margin: 0.5rem 0;">
                        <input type="checkbox" id="showChunks"> Show source chunks
                    </label>
                    <label style="display: block; margin: 0.5rem 0;">
                        <input type="checkbox" id="enableTts"> Read answer aloud (TTS)
                    </label>
                    <button type="submit">Ask Question</button>
                </form>
                
                <div id="response"></div>
            </div>
        </div>
        
        <script>
            function setQuestion(q) {
                document.getElementById('question').value = q;
            }
            
            document.getElementById('chatForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const question = document.getElementById('question').value;
                const language = document.getElementById('language').value;
                const showChunks = document.getElementById('showChunks').checked;
                const enableTts = document.getElementById('enableTts').checked;
                
                const responseDiv = document.getElementById('response');
                responseDiv.innerHTML = '<div class="response">🔍 Searching book...</div>';
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            question,
                            language,
                            show_chunks: showChunks,
                            enable_tts: enableTts
                        })
                    });
                    
                    const data = await response.json();
                    
                    let html = `<div class="response">${data.answer}`;
                    if (data.sources && data.sources.length > 0) {
                        html += `<div class="sources">📄 Sources: Pages ${data.sources.join(', ')}</div>`;
                    }
                    if (data.chunks && data.chunks.length > 0 && showChunks) {
                        html += '<div style="margin-top: 1rem;"><strong>Source chunks:</strong>';
                        data.chunks.forEach(chunk => {
                            html += `<div style="margin: 0.5rem 0; padding: 0.5rem; background: rgba(255,255,255,0.02); border-radius: 8px;">
                                <strong>Page ${chunk.page}</strong> (score: ${chunk.score})<br>
                                ${chunk.text.substring(0, 300)}...
                            </div>`;
                        });
                        html += '</div>';
                    }
                    if (data.audio_available) {
                        html += `<div style="margin-top: 1rem;">
                            <audio controls>
                                <source src="/audio/${encodeURIComponent(question)}" type="audio/wav">
                            </audio>
                        </div>`;
                    }
                    html += '</div>';
                    responseDiv.innerHTML = html;
                } catch (error) {
                    responseDiv.innerHTML = `<div class="response">Error: ${error.message}</div>`;
                }
            });
        </script>
    </body>
    </html>
    """

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        embed_model, collection = load_agent()
        
        general = is_general_question(request.question)
        page_num = detect_page_query(request.question)
        chunks = []

        if page_num:
            chunks = retrieve_by_page(page_num, collection)
            if not chunks:
                chunks = retrieve(request.question, embed_model, collection)
        elif is_character_question(request.question):
            chunks = retrieve_character(request.question, embed_model, collection)
        elif not general:
            chunks = retrieve(request.question, embed_model, collection)

        prompt = build_prompt(request.question, chunks, request.language,
                             use_book_context_only=(general and not chunks))

        chat_history = [{"role": "user", "content": prompt}]
        answer = call_sarvam_llm(chat_history)
        
        pages = sorted(set(c["page"] for c in chunks)) if chunks else []
        sources = [str(p) for p in pages]
        
        # Generate audio if requested
        audio_available = False
        if request.enable_tts and answer and SARVAM_API_KEY:
            tts_lang = "kn-IN" if request.language == "Kannada" else "en-IN"
            try:
                audio_bytes = call_sarvam_tts(answer, tts_lang)
                if audio_bytes:
                    # Store audio in memory or temporary storage
                    audio_available = True
            except Exception:
                pass

        return ChatResponse(
            answer=answer,
            sources=sources,
            chunks=chunks if request.show_chunks else [],
            audio_available=audio_available
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audio/{question}")
async def get_audio(question: str):
    # This is a simplified version - in production, you'd want to cache audio
    try:
        embed_model, collection = load_agent()
        chunks = retrieve(question, embed_model, collection)
        prompt = build_prompt(question, chunks, "English", use_book_context_only=False)
        chat_history = [{"role": "user", "content": prompt}]
        answer = call_sarvam_llm(chat_history)
        
        audio_bytes = call_sarvam_tts(answer, "en-IN")
        if audio_bytes:
            return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/wav")
        else:
            raise HTTPException(status_code=404, detail="Audio not available")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# For Vercel serverless deployment
handler = app
