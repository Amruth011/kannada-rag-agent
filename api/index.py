# api/index.py - FastAPI version for Vercel deployment Final v5 (Stable)
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os, re, requests, json, traceback, base64
from typing import List
from dotenv import load_dotenv

load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME_GROQ = "llama-3.1-8b-instant"

BOOK_CONTEXT = "You are a helpful assistant. Use these Kannada book passages to answer the user question in English. Be direct and cite page numbers."

app = FastAPI(title="Kannada Book AI Agent + Voice")

class ChatRequest(BaseModel):
    question: str
    language: str = "English"

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    audio_base64: str = "" # New: returned if voice is requested

class VoiceRequest(BaseModel):
    text: str

TRANSLIT_MAP = {
    "himavant": "ಹಿಮವಂತ್",
    "prarthana": "ಪ್ರಾರ್ಥನಾ",
    "ravi": "ರವಿ",
    "belagere": "ಬೆಳಗೆರೆ",
    "shivamogga": "ಶಿವಮೊಗ್ಗ",
    "davangere": "ದಾವಣಗೆರೆ",
    "book": "ಕಾದಂಬರಿ",
    "author": "ಲೇಖಕ",
    "who": "ಯಾರು",
    "himavanth": "ಹಿಮವಂತ್",
    "karana": "ಕಾರಣ",
    "heli": "ಹೇಳಿ",
    "hogu": "ಹೋಗು"
}

def load_data():
    paths = [
        os.path.join(os.path.dirname(__file__), "data.json"),
        "api/data.json", 
        "data.json", 
        "/var/task/api/data.json", 
        "/var/task/data.json"
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
    return []

def search_text(query, data, top_k=8):
    """Refined search: Splits pages into paragraphs for high precision RAG."""
    query_words = set(query.lower().split())
    results = []
    
    for item in data:
        page_num = item.get('page', 0)
        text = item.get('text', '')
        # Split into paragraphs to reduce payload size and increase focus
        paragraphs = [p.strip() for p in text.replace("\r", "").split("\n") if len(p.strip()) > 30]
        
        for p_index, para in enumerate(paragraphs):
            para_lower = para.lower()
            score = 0
            for word in query_words:
                if word in para_lower:
                    score += 5
                # Simple transliteration bridge for English queries
                mapped = TRANSLIT_MAP.get(word, "")
                if mapped and mapped in para_lower:
                    score += 10
            
            if score > 0:
                results.append({
                    'page': page_num,
                    'text': para,
                    'score': score
                })
                
    # Rank by score and pick top_k paragraph fragments
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]

def call_gemini(prompt):
    """Call Gemini 1.5 Flash (Primary)."""
    if not GEMINI_API_KEY: return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return None
    except Exception: return None

def call_groq(prompt):
    """Call Groq Llama 3 (Fallback)."""
    if not GROQ_API_KEY: return "[ERROR]: API Key missing."
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    payload = {"model": MODEL_NAME_GROQ, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"[AI ERROR]: Groq status {resp.status_code}"
    except Exception as e:
        return f"[AI ERROR]: {str(e)}"

def call_ai_resilient(prompt):
    """Dual-Brain Logic: Gemini first, Groq as fallback."""
    answer = call_gemini(prompt)
    if answer: return answer
    # Fallback to Groq if Gemini fails/limits out
    return call_groq(prompt)

def call_sarvam_tts(text):
    """Call Sarvam TTS 'Meera' voice (bulbul:v3)."""
    if not SARVAM_API_KEY: return ""
    url = "https://api.sarvam.ai/text-to-speech"
    headers = {"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": text,
        "target_language_code": "kn-IN",
        "speaker": "meera",
        "model": "bulbul:v3",
        "speech_sample_rate": 24000
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        res_json = resp.json()
        # Handle both formats: direct string or nested string
        return res_json.get("audios", [""])[0] if "audios" in res_json else res_json.get("audio", "")
    except Exception:
        return ""

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        data = load_data()
        chunks = search_text(request.question, data)
        retrieved_pages = [str(c['page']) for c in chunks]
        
        pagetext = "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks]) if chunks else "No direct passages found."
        
        full_prompt = f"{BOOK_CONTEXT}\n\nRETRIEVED PASSAGES:\n{pagetext}\n\nUSER QUESTION: {request.question}\n\nAnswer concisely. If text is Kannada, interpret it and answer in {request.language}."
        
        answer = call_ai_resilient(full_prompt)
        return ChatResponse(answer=answer, sources=retrieved_pages)
    except Exception:
        return ChatResponse(answer=f"[BACKEND ERROR]: {traceback.format_exc()[:500]}", sources=[])

@app.post("/voice")
async def voice(request: VoiceRequest):
    # To keep it fast, we do TTS on a separate click
    audio_b64 = call_sarvam_tts(request.text)
    return {"audio": audio_b64}

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="kn">
    <head>
        <title>ಹೇಳಿ ಹೋಗು ಕಾರಣ — AI Flagship</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;800&display=swap" rel="stylesheet">
        <style>
            :root { --primary: #a855f7; --bg: #020617; --card: rgba(15, 23, 42, 0.6); --text: #f8fafc; }
            body { background: var(--bg); color: var(--text); font-family: 'Outfit', sans-serif; min-height: 100vh; margin: 0; display: flex; flex-direction: column; align-items: center; overflow-x: hidden; }
            
            /* HERO SECTION */
            .hero { padding: 6rem 2rem 4rem; text-align: center; background: radial-gradient(circle at top, rgba(168, 85, 247, 0.15) 0%, transparent 70%); width: 100%; box-sizing: border-box; }
            .hero h1 { font-size: clamp(3rem, 10vw, 5.5rem); font-weight: 800; letter-spacing: -4px; margin: 0; line-height: 0.9; background: linear-gradient(to bottom, #fff 30%, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .hero p { color: #94a3b8; font-size: 1.25rem; margin-top: 1.5rem; max-width: 600px; margin-left: auto; margin-right: auto; }
            
            .container { width: 100%; max-width: 700px; padding: 0 1.5rem; box-sizing: border-box; z-index: 10; transform: translateY(-20px); }
            .card { background: var(--card); border: 1px solid rgba(255,255,255,0.1); padding: 2.5rem; border-radius: 40px; backdrop-filter: blur(24px); box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
            
            /* INPUT & BUTTONS */
            input { width: 100%; background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1); padding: 1.5rem; border-radius: 20px; color: #fff; margin-bottom: 1rem; font-size: 1.2rem; outline: none; transition: all 0.3s; box-sizing: border-box; }
            input:focus { border-color: var(--primary); box-shadow: 0 0 20px rgba(168, 85, 247, 0.2); }
            
            .main-btn { width: 100%; background: linear-gradient(135deg, #a855f7, #7c3aed); color: #fff; border: none; padding: 1.4rem; border-radius: 20px; font-weight: 800; cursor: pointer; font-size: 1.2rem; transition: all 0.3s; margin-bottom: 2rem; box-shadow: 0 10px 20px -5px rgba(168, 85, 247, 0.4); }
            .main-btn:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 20px 30px -5px rgba(168, 85, 247, 0.6); }

            /* SUGGESTIONS */
            .suggestions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 2rem; justify-content: center; }
            .sug-btn { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: #94a3b8; padding: 0.6rem 1.2rem; border-radius: 99px; font-size: 0.9rem; cursor: pointer; transition: all 0.2s; }
            .sug-btn:hover { background: rgba(168, 85, 247, 0.1); border-color: var(--primary); color: #fff; }

            /* TOGGLE */
            .settings { display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: rgba(255,255,255,0.03); border-radius: 16px; margin-bottom: 1.5rem; }
            .toggle-label { font-size: 0.9rem; color: #94a3b8; display: flex; align-items: center; gap: 8px; cursor: pointer; }
            input[type="checkbox"] { width: auto; margin: 0; }

            #ans-container { margin-top: 2rem; display: none; transform: translateY(20px); transition: all 0.5s; }
            #ans { background: rgba(168, 85, 247, 0.03); border: 1px solid rgba(168, 85, 247, 0.1); padding: 2.5rem; border-radius: 32px; line-height: 1.9; position: relative; font-size: 1.1rem; }
            .voice-btn { background: #1e1b4b; border: 1px solid #312e81; width: auto; display: inline-flex; align-items: center; gap: 8px; padding: 0.8rem 1.5rem; border-radius: 16px; margin-top: 1.5rem; color: #fff; font-weight: 700; transition: all 0.3s; }
            .voice-btn:hover { background: #312e81; transform: scale(1.05); }

            .loader { width: 24px; height: 24px; border: 3px solid rgba(168, 85, 247, 0.2); border-top-color: #a855f7; border-radius: 50%; animation: spin 1s infinite linear; display: inline-block; }
            @keyframes spin { to { transform: rotate(360deg); } }
            .fade-in { animation: fadeIn 0.8s forwards; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        </style>
    </head>
    <body>
        <div class="hero">
            <h1 class="fade-in">ಹೇಳಿ ಹೋಗು ಕಾರಣ</h1>
            <p class="fade-in" style="animation-delay: 0.1s">Your AI-powered guide through the literary world of Heli Hogu Karana. Ask anything about characters, themes, or the story.</p>
        </div>

        <div class="container fade-in" style="animation-delay: 0.2s">
            <div class="card">
                <div class="settings">
                    <label class="toggle-label">
                        <input type="checkbox" id="auto-speak"> 🔊 Auto-play Voice Output
                    </label>
                    <span style="font-size: 0.8rem; color: #64748b;">Powered by Groq & Sarvam</span>
                </div>

                <div class="suggestions">
                    <button class="sug-btn" onclick="setQ('Who is Himavant?')">Who is Himavant?</button>
                    <button class="sug-btn" onclick="setQ('Describe Prarthana')">About Prarthana</button>
                    <button class="sug-btn" onclick="setQ('What are the main themes?')">Main Themes</button>
                    <button class="sug-btn" onclick="setQ('How is Ravi related?')">Ravi's Role</button>
                </div>

                <input type="text" id="q" placeholder="What would you like to know?" required autoComplete="off">
                <button id="btn" class="main-btn" onclick="ask()">Analyze the Book</button>
                
                <div id="loading" style="display:none; text-align:center; margin-top:1rem; color: var(--primary);"><div class="loader"></div> Thinking...</div>
                
                <div id="ans-container">
                    <div id="ans">
                        <div id="text-res"></div>
                        <div style="display: flex; gap: 10px; align-items: center;">
                            <button id="v-btn" class="voice-btn" onclick="speak()">
                                <span>🔊 Hear in Kannada</span>
                            </button>
                            <div id="v-loading" style="display:none; text-align:center;"><div class="loader"></div></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentText = "";
            let isSpeaking = false;

            function setQ(txt) {
                document.getElementById('q').value = txt;
                ask();
            }

            async function ask() {
                const q = document.getElementById('q').value;
                const btn = document.getElementById('btn');
                const load = document.getElementById('loading');
                const cont = document.getElementById('ans-container');
                const res = document.getElementById('text-res');
                if (!q) return;
                
                btn.disabled = true; load.style.display = 'block'; cont.style.display = 'none';
                try {
                    const r = await fetch('/chat', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question: q})});
                    const d = await r.json();
                    currentText = d.answer;
                    res.innerHTML = d.answer.replace(/\\n/g, '<br>');
                    cont.style.display = 'block';
                    cont.classList.add('fade-in');
                    
                    if (document.getElementById('auto-speak').checked) {
                        speak();
                    }
                } catch (e) { alert("Error: " + e.message); }
                btn.disabled = false; load.style.display = 'none';
            }

            async function speak() {
                if (isSpeaking) return;
                const vBtn = document.getElementById('v-btn');
                const vLoad = document.getElementById('v-loading');
                vBtn.style.display = 'none'; vLoad.style.display = 'block';
                isSpeaking = true;

                try {
                    const r = await fetch('/voice', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: currentText})});
                    const d = await r.json();
                    if (d.audio) {
                        const audio = new Audio("data:audio/mp3;base64," + d.audio);
                        audio.onended = () => { isSpeaking = false; vBtn.style.display = 'inline-flex'; vLoad.style.display = 'none'; };
                        audio.play();
                    } else { 
                        alert("Voice engine unavailable. Please try again."); 
                        isSpeaking = false; vBtn.style.display = 'inline-flex'; vLoad.style.display = 'none';
                    }
                } catch (e) { 
                    alert("Voice Error: " + e.message); 
                    isSpeaking = false; vBtn.style.display = 'inline-flex'; vLoad.style.display = 'none';
                }
            }
        </script>
    </body>
    </html>
    """
handler = app
