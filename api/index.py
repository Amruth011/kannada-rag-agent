# api/index.py - FastAPI version for Vercel deployment
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
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

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
# Use local model cache for Vercel bundling
MODEL_CACHE_DIR = os.path.join(BASE_DIR, "model_cache")
os.environ["FASTEMBED_CACHE_PATH"] = MODEL_CACHE_DIR

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

GENERAL_PATTERNS = [
    r'what is (this|the) book', r'about (this|the) book', r'book (about|summary|theme)',
    r'who (is|wrote|is the author).*ravi', r'ravi belagere', r'author',
    r'ಪುಸ್ತಕ(ದ|ವು|ದ ಬಗ್ಗೆ)', r'ಕಾದಂಬರಿ', r'ರವಿ ಬೆಳಗೆರೆ', r'ವಿಷಯ ಏನು',
    r'ಯಾರು ಬರೆದ', r'ಮುಖ್ಯ ವಿಷಯ', r'summary', r'theme', r'title mean', r'ಶೀರ್ಷಿಕೆ',
]

CHARACTER_PATTERNS = [
    r'himavant', r'prarthana', r'pratana', r'prathana',
    r'ಹಿಮವಂತ', r'ಪ್ರಾರ್ಥನಾ',
    r'main character', r'protagonist', r'ಮುಖ್ಯ ಪಾತ್ರ',
    r'who is', r'who are', r'character', r'ಪಾತ್ರ',
    r'wife', r'husband', r'ಹೆಂಡತಿ', r'ಗಂಡ',
    r'relationship', r'ಸಂಬಂಧ', r'name of', r'tell me about',
]

app = FastAPI(title="Kannada Book AI Agent")

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
        from fastembed import TextEmbedding
        import chromadb
        
        # Initialize FastEmbed with bundled model
        embed_model = TextEmbedding(model_name=MODEL_NAME)
        
        # Initialize ChromaDB in read-only mode if possible, or just handle errors
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        try:
            collection = client.get_collection(COLLECTION)
        except Exception:
            # On Vercel, this might happen if CHROMA_DIR is missing or read-only issues occur
            # We assume it exists in the repo
            collection = client.get_or_create_collection(COLLECTION)
            
    return embed_model, collection

def retrieve(query, embed_model, collection, top_k=5):
    # FastEmbed returns an iterator of embeddings
    qe = list(embed_model.embed([query]))[0].tolist()
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
    qe = list(embed_model.embed([query]))[0].tolist()
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
        return "⚠️ SARVAM_API_KEY not set in Environment Variables"
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
            except wave.Error: continue
    return output_wav.getvalue()

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="kn">
    <head>
        <title>ಹೇಳಿ ಹೋಗು ಕಾರಣ — AI Intelligence</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Noto+Sans+Kannada:wght@400;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #8b5cf6;
                --secondary: #ec4899;
                --bg: #05050a;
                --surface: rgba(255, 255, 255, 0.03);
                --border: rgba(255, 255, 255, 0.08);
                --text: #f8fafc;
                --text-dim: #94a3b8;
            }
            * { box-sizing: border-box; transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1); }
            body {
                background: radial-gradient(circle at 0% 0%, #1e1b4b 0%, #05050a 50%, #020617 100%);
                color: var(--text);
                font-family: 'Outfit', 'Noto Sans Kannada', sans-serif;
                margin: 0;
                padding: 0;
                min-height: 100vh;
                display: flex;
                justify-content: center;
                overflow-x: hidden;
            }
            .container { width: 100%; max-width: 900px; padding: 3rem 1.5rem; }
            .header { text-align: center; margin-bottom: 4rem; }
            .badge {
                display: inline-block;
                padding: 0.5rem 1rem;
                background: rgba(139, 92, 246, 0.1);
                border: 1px solid rgba(139, 92, 246, 0.2);
                border-radius: 999px;
                color: var(--primary);
                font-size: 0.8rem;
                font-weight: 600;
                letter-spacing: 0.05em;
                margin-bottom: 1rem;
                text-transform: uppercase;
            }
            h1 {
                font-size: clamp(2.5rem, 8vw, 4rem);
                font-weight: 800;
                margin: 0;
                background: linear-gradient(to bottom right, #fff 30%, #94a3b8);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                line-height: 1.1;
            }
            .subtitle { color: var(--text-dim); font-size: 1.2rem; margin-top: 1rem; }
            
            .main-card {
                background: var(--surface);
                backdrop-filter: blur(24px);
                -webkit-backdrop-filter: blur(24px);
                border: 1px solid var(--border);
                border-radius: 24px;
                padding: 2.5rem;
                box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);
                position: relative;
                overflow: hidden;
            }
            .main-card::before {
                content: '';
                position: absolute;
                top: 0; left: 0; right: 0; height: 1px;
                background: linear-gradient(90deg, transparent, var(--primary), transparent);
            }
            
            .search-box { position: relative; margin-bottom: 2rem; }
            input {
                width: 100%;
                background: rgba(0,0,0,0.2);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 1.2rem 1.5rem;
                color: white;
                font-size: 1.1rem;
                outline: none;
            }
            input:focus { border-color: var(--primary); box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.1); }
            
            .controls { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 2rem; }
            select {
                background: rgba(0,0,0,0.2);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 0.8rem;
                color: white;
                cursor: pointer;
            }
            
            .checkbox-group { display: flex; gap: 1.5rem; flex-wrap: wrap; }
            .checkbox-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; color: var(--text-dim); cursor: pointer; }
            .checkbox-item:hover { color: white; }
            
            button {
                width: 100%;
                background: linear-gradient(135deg, var(--primary) 0%, #6d28d9 100%);
                color: white;
                border: none;
                border-radius: 16px;
                padding: 1.2rem;
                font-size: 1.1rem;
                font-weight: 700;
                cursor: pointer;
                margin-top: 1rem;
                box-shadow: 0 10px 20px -5px rgba(139, 92, 246, 0.4);
            }
            button:hover { transform: translateY(-2px); box-shadow: 0 15px 30px -5px rgba(139, 92, 246, 0.6); }
            button:active { transform: translateY(0); }
            
            .chips { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 2rem; }
            .chip {
                background: rgba(255,255,255,0.05);
                border: 1px solid var(--border);
                border-radius: 99px;
                padding: 0.4rem 1rem;
                font-size: 0.85rem;
                cursor: pointer;
                color: var(--text-dim);
            }
            .chip:hover { background: rgba(139, 92, 246, 0.2); color: white; border-color: var(--primary); }
            
            #response-container { margin-top: 3rem; display: none; }
            .result-card {
                background: rgba(139, 92, 246, 0.05);
                border: 1px solid rgba(139, 92, 246, 0.2);
                border-radius: 20px;
                padding: 2rem;
                line-height: 1.7;
                font-size: 1.1rem;
            }
            .sources { 
                margin-top: 1.5rem;
                padding-top: 1rem;
                border-top: 1px solid var(--border);
                color: var(--text-dim);
                font-size: 0.9rem;
                display: flex;
                gap: 0.5rem;
                flex-wrap: wrap;
            }
            .source-tag {
                background: rgba(255,255,255,0.03);
                padding: 0.2rem 0.6rem;
                border-radius: 6px;
                border: 1px solid var(--border);
            }
            
            .loader {
                width: 24px; height: 24px;
                border: 3px solid rgba(139, 92, 246, 0.3);
                border-top-color: var(--primary);
                border-radius: 50%;
                animation: spin 1s infinite linear;
                margin: 2rem auto;
            }
            @keyframes spin { to { transform: rotate(360deg); } }
            
            audio { width: 100%; margin-top: 1.5rem; filter: invert(0.9) hue-rotate(180deg); opacity: 0.7; }
            audio:hover { opacity: 1; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <span class="badge">RAG Powered Agent</span>
                <h1>ಹೇಳಿ ಹೋಗು ಕಾರಣ</h1>
                <p class="subtitle">Intelligent Conversational Guide to Ravi Belagere's Masterpiece</p>
            </div>
            
            <div class="main-card">
                <div class="chips">
                    <div class="chip" onclick="setQ('What is this book about?')">Overview</div>
                    <div class="chip" onclick="setQ('Who is Himavant?')">Himavant</div>
                    <div class="chip" onclick="setQ('Who is Prarthana?')">Prarthana</div>
                    <div class="chip" onclick="setQ('What happens in page 80?')">Page 80</div>
                    <div class="chip" onclick="setQ('ಹಿಮವಂತನ ಪಾತ್ರದ ಬಗ್ಗೆ ತಿಳಿಸಿ')">ಹಿಮವಂತ</div>
                    <div class="chip" onclick="setQ('ಕಾದಂಬರಿಯ ಸಾರಾಂಶ ಏನು?')">ಸಾರಾಂಶ</div>
                </div>
                
                <form id="chatForm">
                    <div class="search-box">
                        <input type="text" id="question" placeholder="Ask anything about the book..." required autocomplete="off">
                    </div>
                    
                    <div class="controls">
                        <select id="language">
                            <option value="English">Respond in English</option>
                            <option value="Kannada">Respond in Kannada</option>
                        </select>
                        <div class="checkbox-group">
                            <label class="checkbox-item">
                                <input type="checkbox" id="showChunks"> Show Passages
                            </label>
                            <label class="checkbox-item">
                                <input type="checkbox" id="enableTts"> Voice (TTS)
                            </label>
                        </div>
                    </div>
                    
                    <button type="submit" id="submitBtn">Analyze & Answer</button>
                </form>
                
                <div id="loading" style="display:none"><div class="loader"></div></div>
                
                <div id="response-container">
                    <div id="answer" class="result-card"></div>
                    <div id="sources" class="sources"></div>
                    <div id="audio-container"></div>
                </div>
            </div>
        </div>

        <script>
            function setQ(q) { document.getElementById('question').value = q; }
            
            document.getElementById('chatForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const question = document.getElementById('question').value;
                const language = document.getElementById('language').value;
                const showChunks = document.getElementById('showChunks').checked;
                const enableTts = document.getElementById('enableTts').checked;
                
                const btn = document.getElementById('submitBtn');
                const loading = document.getElementById('loading');
                const container = document.getElementById('response-container');
                const answerDiv = document.getElementById('answer');
                const sourcesDiv = document.getElementById('sources');
                const audioDiv = document.getElementById('audio-container');
                
                btn.disabled = true;
                loading.style.display = 'block';
                container.style.display = 'none';
                
                try {
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ question, language, show_chunks: showChunks, enable_tts: enableTts })
                    });
                    
                    const data = await response.json();
                    
                    answerDiv.innerHTML = data.answer.replace(/\\n/g, '<br>');
                    
                    sourcesDiv.innerHTML = '';
                    if (data.sources && data.sources.length > 0) {
                        data.sources.forEach(s => {
                            sourcesDiv.innerHTML += `<span class="source-tag">Page ${s}</span>`;
                        });
                    }
                    
                    audioDiv.innerHTML = '';
                    if (data.audio_available) {
                        audioDiv.innerHTML = `
                            <audio controls autoplay>
                                <source src="/audio/${encodeURIComponent(question)}" type="audio/wav">
                            </audio>
                        `;
                    }
                    
                    if (data.chunks && data.chunks.length > 0 && showChunks) {
                        let chunksHtml = '<div style="margin-top:2rem; font-size:0.9rem; color:var(--text-dim)"><strong>Retrieved Passages:</strong>';
                        data.chunks.forEach(c => {
                            chunksHtml += `<div style="margin-top:1rem; padding:1rem; background:rgba(0,0,0,0.2); border-radius:12px; border-left:4px solid var(--primary)">
                                <strong>Page ${c.page}</strong> (match: ${c.score})<br>${c.text}
                            </div>`;
                        });
                        answerDiv.innerHTML += chunksHtml + '</div>';
                    }
                    
                    container.style.display = 'block';
                } catch (err) {
                    answerDiv.innerHTML = `Error: ${err.message}`;
                    container.style.display = 'block';
                } finally {
                    btn.disabled = false;
                    loading.style.display = 'none';
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
            if not chunks: chunks = retrieve(request.question, embed_model, collection)
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
        
        audio_available = False
        if request.enable_tts and answer and SARVAM_API_KEY:
            # We don't store audio but we flag it as available for the /audio endpoint
            audio_available = True

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
    try:
        embed_model, collection = load_agent()
        chunks = retrieve(question, embed_model, collection)
        prompt = build_prompt(question, chunks, "English", use_book_context_only=False)
        chat_history = [{"role": "user", "content": prompt}]
        answer = call_sarvam_llm(chat_history)
        
        audio_bytes = call_sarvam_tts(answer, "kn-IN" if any(ord(c) > 128 for c in answer) else "en-IN")
        if audio_bytes:
            return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/wav")
        raise HTTPException(status_code=404, detail="Audio generation failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": MODEL_NAME, "fastembed": True}

# Vercel entrypoint
handler = app
