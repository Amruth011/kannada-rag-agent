# api/index.py - FastAPI version for Vercel deployment Final v5 (Stable)
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os, re, requests, json, traceback, base64, time
from typing import List
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

# Configure Gemini SDK with strict key cleaning
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"SDK Config Error: {e}")

BOOK_CONTEXT = "You are a professional literary assistant. Use these Kannada book passages to answer the user question in English. Provide deep analysis and always cite page numbers."

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
    language: str = "English"

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

# Load data once at startup to prevent Vercel timeouts
BOOK_DATA = load_data()

def search_text(query, data, top_k=5):
    """Retrieves full pages for Gemini's large context window."""
    query_words = set(query.lower().split())
    results = []
    
    for item in data:
        page_num = item.get('page', 0)
        text = item.get('text', '')
        text_lower = text.lower()
        score = 0
        for word in query_words:
            if word in text_lower:
                score += 5
            # Simple transliteration bridge for English queries
            mapped = TRANSLIT_MAP.get(word, "")
            if mapped and mapped in text_lower:
                score += 10
        
        if score > 0:
            results.append({
                'page': page_num,
                'text': text,
                'score': score
            })
                
    # Rank by score and pick top_k full pages for Gemini
    results.sort(key=lambda x: x['score'], reverse=True)
    return results[:top_k]

def call_groq(prompt, retries=2):
    """Fallback to Groq (Llama 3.3) with Rate Limit Armor."""
    if not GROQ_API_KEY:
        return "[ERROR]: GROQ_API_KEY is missing."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": BOOK_CONTEXT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1024
    }
    
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            
            if resp.status_code == 429: # Rate Limit
                if attempt < retries:
                    time.sleep(3) # Shorter sleep to avoid Vercel 10s timeout
                    continue
            
            resp.raise_for_status()
        except Exception as e:
            if attempt < retries:
                time.sleep(2)
                continue
            return f"[GROQ ERROR]: {str(e)}"
    return "[ERROR]: Groq rate limit exhausted."

def get_best_gemini_model():
    """Helper to find the best available model for this specific API key."""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prefer 2.5 flash, 2.0 flash, then other flash models
        for model in models:
            if "gemini-2.5-flash" in model: return model
        for model in models:
            if "gemini-2.0-flash" in model: return model
        for model in models:
            if "gemini-flash-latest" in model: return model
        for model in models:
            if "gemini-1.5-flash" in model: return model
        for model in models:
            if "gemini-1.5-pro" in model: return model
        return models[0] if models else "gemini-2.5-flash"
    except Exception:
        return "gemini-2.5-flash"

def call_gemini(prompt, retries=1):
    """Deepest Gemini Safety Bypass + System Prompting."""
    if not GEMINI_API_KEY: 
        return call_groq(prompt)
    
    last_error = ""
    model_name = get_best_gemini_model()
    
    # 1. Standard Safety Settings (Guaranteed compatibility)
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    for attempt in range(retries + 1):
        try:
            # 2. Use System Instruction (Makes Gemini less sensitive to content blocks)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=BOOK_CONTEXT
            )
            response = model.generate_content(prompt, safety_settings=safety_settings)
            
            # 3. Robust candidate checking
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    return response.text
                if candidate.finish_reason:
                    last_error = f"Blocked (Reason: {candidate.finish_reason})"
            else:
                last_error = "No candidates returned (Safety Blocked)"
            break 
        except Exception as e:
            last_error = str(e)
            if "429" in last_error:
                if attempt < retries:
                    time.sleep(3)
                    continue
            break 
                
    return f"[GEMINI FAILED ({model_name}): {last_error[:100]}] " + call_groq(prompt)

def call_sarvam_tts(text, language="kn-IN"):
    """Call Sarvam TTS 'Meera' voice (bulbul:v3) with fallback to Google TTS (gTTS)."""
    # Clean citations and errors
    clean = re.sub(r'\[Page \d+\]:', '', text).strip()
    clean = re.sub(r'📄 Sources:.*', '', clean).strip()
    clean = re.sub(r'\[GEMINI FAILED.*\]', '', clean).strip()
    clean = re.sub(r'\[GROQ ERROR.*\]', '', clean).strip()
    clean = re.sub(r'\[BACKEND ERROR.*\]', '', clean).strip()
    clean = re.sub(r'\[ERROR.*\]', '', clean).strip()

    # 1. Try Sarvam TTS first if API Key is configured and language is Kannada
    is_kannada = "kn" in language.lower()
    target_lang = "kn-IN" if is_kannada else "en-IN"
    
    if SARVAM_API_KEY and is_kannada:
        try:
            # Split text into chunks < 450 chars to avoid API failures
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
            headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
            headers_key = {"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"}
            
            for chunk in chunks_list:
                if not chunk.strip(): continue
                payload = {
                    "inputs": [chunk.strip()],
                    "target_language_code": target_lang,
                    "speaker": "meera",
                    "model": "bulbul:v3",
                    "pace": 1.0
                }
                # Try standard Bearer header
                resp = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers, json=payload, timeout=20)
                if resp.status_code != 200:
                    # Try subscription key header
                    resp = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers_key, json=payload, timeout=20)
                
                if resp.status_code == 200:
                    res_json = resp.json()
                    aud_b64 = res_json.get("audios", [""])[0] if "audios" in res_json else res_json.get("audio", "")
                    if aud_b64:
                        audio_bytes_list.append(base64.b64decode(aud_b64))
            
            if audio_bytes_list:
                import wave, io
                output_wav = io.BytesIO()
                with wave.open(output_wav, 'wb') as wav_out:
                    for i, ab in enumerate(audio_bytes_list):
                        seg = io.BytesIO(ab)
                        try:
                            with wave.open(seg, 'rb') as wav_in:
                                if i == 0: wav_out.setparams(wav_in.getparams())
                                wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))
                        except:
                            continue
                return base64.b64encode(output_wav.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"Sarvam TTS failed, falling back to gTTS: {e}")

    # 2. Fallback to Google TTS (gTTS)
    try:
        from gtts import gTTS
        import io
        gtts_lang = "kn" if is_kannada else "en"
        tts = gTTS(text=clean, lang=gtts_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return base64.b64encode(fp.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"Google TTS fallback failed: {e}")
        return ""

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Use globally loaded BOOK_DATA
        chunks = search_text(request.question, BOOK_DATA, top_k=1) # Reduced to 1 for Groq free-tier stability
        retrieved_pages = [str(c['page']) for c in chunks]
        
        # Implement safe character capping (approx 5,000 chars for Groq)
        pagetext = ""
        current_len = 0
        for c in chunks:
            text_block = f"[Passage from Page {c['page']}]: {c['text']}\n\n"
            if current_len + len(text_block) > 5000:
                break
            pagetext += text_block
            current_len += len(text_block)
            
        if not pagetext: pagetext = "No direct passages found."
        
        # Build prompt based on requested language
        if request.language == "English":
            full_prompt = f"""You are an AI assistant for the Kannada novel "Heli Hogu Karana".

BOOK INFORMATION:
{BOOK_CONTEXT}

RETRIEVED PASSAGES:
{pagetext}

Answer using the information above. Be informative and cite page numbers when using passages.
If passages say "Not found in document", tell the user clearly.

QUESTION: {request.question}
ANSWER in English:"""
        else:
            full_prompt = f"""ನೀವು "ಹೇಳಿ ಹೋಗು ಕಾರಣ" ಕನ್ನಡ ಕಾದಂಬರಿಯ AI ಸಹಾಯಕರು.

ಪುಸ್ತಕದ ಮಾಹಿತಿ / Book Info:
{BOOK_CONTEXT}

ಪುಸ್ತಕದಿಂದ ತೆಗೆದ ವಿಷಯ:
{pagetext}

ಕನ್ನಡದಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರಿಸಿ.

ಪ್ರಶ್ನೆ: {request.question}
ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರ:"""
        
        answer = call_gemini(full_prompt)
        return ChatResponse(answer=answer, sources=retrieved_pages)
    except Exception:
        return ChatResponse(answer=f"[BACKEND ERROR]: {traceback.format_exc()[:500]}", sources=[])

@app.post("/voice")
async def voice(request: VoiceRequest):
    # Map requested language option to ISO code
    lang_code = "kn-IN" if request.language == "Kannada" else "en-IN"
    audio_b64 = call_sarvam_tts(request.text, language=lang_code)
    return {"audio": audio_b64}

@app.get("/", response_class=HTMLResponse)
async def root():
    return r"""    <!DOCTYPE html>
    <html lang="kn">
    <head>
        <title>ಹೇಳಿ ಹೋಗು ಕಾರಣ — Bilingual AI Book Guide</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #c2410c; /* Terracotta / Saffron */
                --primary-light: #ffedd5;
                --primary-glow: rgba(194, 65, 12, 0.15);
                --bg: #fffcf8;
                --bg-secondary: #fdf5ee;
                --card: #ffffff;
                --text: #0f172a;
                --text-muted: #64748b;
                --accent: #4338ca;
                --accent-light: #e0e7ff;
                --border: rgba(194, 65, 12, 0.08);
                --shadow: 0 20px 50px -15px rgba(194, 65, 12, 0.08);
                --font-serif: 'Playfair Display', Georgia, serif;
                --font-sans: 'Plus Jakarta Sans', sans-serif;
            }
            body {
                background: radial-gradient(circle at 50% 0%, #fffefc 0%, var(--bg-secondary) 80%);
                color: var(--text);
                font-family: var(--font-sans);
                min-height: 100vh;
                margin: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                overflow-x: hidden;
                position: relative;
            }
            
            /* DYNAMIC BACKGROUND SHAPES & WATERMARKS */
            .bg-decorations {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                overflow: hidden;
                pointer-events: none;
                z-index: 0;
            }
            .circle {
                position: absolute;
                border-radius: 50%;
                filter: blur(100px);
                opacity: 0.5;
            }
            .circle-1 {
                top: -10%;
                left: 10%;
                width: 40vw;
                height: 40vw;
                background: radial-gradient(circle, rgba(251, 146, 60, 0.12) 0%, transparent 70%);
            }
            .circle-2 {
                top: 30%;
                right: -10%;
                width: 50vw;
                height: 50vw;
                background: radial-gradient(circle, rgba(194, 65, 12, 0.08) 0%, transparent 70%);
            }
            .chakra-watermark {
                position: absolute;
                top: 80px;
                right: -150px;
                width: 500px;
                height: 500px;
                animation: slow-rotate 120s linear infinite;
                transform-origin: center center;
            }
            @keyframes slow-rotate {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            
            /* TOP ANNOUNCEMENT BAR */
            .top-banner {
                width: 100%;
                background: linear-gradient(90deg, #b45309, #c2410c, #b45309);
                color: #ffffff;
                font-size: 0.75rem;
                font-weight: 700;
                text-align: center;
                padding: 0.6rem;
                letter-spacing: 1.5px;
                box-sizing: border-box;
                text-transform: uppercase;
                box-shadow: 0 2px 10px rgba(194, 65, 12, 0.15);
                z-index: 101;
            }
            
            /* NAVBAR */
            .nav-header {
                width: 100%;
                background: rgba(255, 255, 255, 0.85);
                backdrop-filter: blur(20px);
                border-bottom: 1px solid var(--border);
                padding: 0.9rem 2rem;
                box-sizing: border-box;
                position: sticky;
                top: 0;
                z-index: 100;
            }
            .nav-container {
                max-width: 1100px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .logo {
                font-family: var(--font-serif);
                font-size: 1.5rem;
                font-weight: 800;
                letter-spacing: -0.2px;
                display: flex;
                align-items: center;
                gap: 2px;
                cursor: pointer;
            }
            .logo-title {
                color: var(--text);
            }
            .logo-sub {
                color: var(--primary);
                font-weight: 800;
            }
            .nav-menu {
                display: flex;
                gap: 1.5rem;
            }
            .nav-item {
                font-size: 0.8rem;
                font-weight: 700;
                color: var(--text-muted);
                cursor: pointer;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                transition: color 0.2s;
            }
            .nav-item:hover, .nav-item.active {
                color: var(--primary);
            }
            
            /* HERO SECTION */
            .hero {
                padding: 4.5rem 2rem 2.5rem;
                text-align: center;
                width: 100%;
                box-sizing: border-box;
                z-index: 10;
                position: relative;
            }
            .hero h1 {
                font-family: var(--font-serif);
                font-size: clamp(2.8rem, 7vw, 4.8rem);
                font-weight: 900;
                margin: 0;
                line-height: 1.1;
                background: linear-gradient(135deg, #0f172a 30%, #c2410c);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .hero p {
                color: var(--text-muted);
                font-size: 1.1rem;
                margin-top: 1rem;
                max-width: 600px;
                margin-left: auto;
                margin-right: auto;
                line-height: 1.6;
                font-weight: 500;
            }
            
            /* CONTAINER & CARD */
            .container {
                width: 100%;
                max-width: 720px;
                padding: 0 1.5rem 5rem;
                box-sizing: border-box;
                z-index: 10;
                position: relative;
            }
            .card {
                background: var(--card);
                border: 1px solid var(--border);
                border-top: 5px solid var(--primary);
                padding: 3.5rem 2.2rem 2.2rem 2.2rem; /* Increased top padding for Mehrab arch dome */
                border-radius: 28px;
                box-shadow: var(--shadow);
                position: relative;
                overflow: hidden;
            }
            
            /* SETTINGS / TOGGLE */
            .settings {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.9rem 1.2rem;
                background: #faf6f0;
                border: 1px solid rgba(194, 65, 12, 0.08);
                border-radius: 14px;
                margin-bottom: 1.8rem;
                flex-wrap: wrap;
                gap: 12px;
            }
            .toggle-label {
                font-size: 0.85rem;
                font-weight: 700;
                color: var(--text-muted);
                display: flex;
                align-items: center;
                gap: 8px;
                cursor: pointer;
            }
            .toggle-label input[type="checkbox"] {
                accent-color: var(--primary);
                width: 16px;
                height: 16px;
                cursor: pointer;
            }
            
            /* SUGGESTIONS */
            .suggestions {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                margin-bottom: 1.8rem;
                justify-content: center;
            }
            .sug-btn {
                background: linear-gradient(145deg, #ffffff 0%, #fffbf7 100%);
                border: 1px solid rgba(194, 65, 12, 0.12);
                color: var(--text);
                padding: 0.7rem 1.3rem;
                border-radius: 99px;
                font-size: 0.88rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 2px 6px rgba(194, 65, 12, 0.02);
            }
            .sug-btn:hover {
                transform: translateY(-2px);
                border-color: var(--primary);
                background: var(--primary-light);
                color: var(--primary);
                box-shadow: 0 8px 16px rgba(194, 65, 12, 0.08);
            }
            
            /* INPUT & BUTTON */
            input[type="text"] {
                width: 100%;
                background: #ffffff;
                border: 1.5px solid rgba(194, 65, 12, 0.18);
                padding: 1.3rem;
                border-radius: 18px;
                color: var(--text);
                margin-bottom: 1.2rem;
                font-size: 1.1rem;
                outline: none;
                transition: all 0.25s;
                box-sizing: border-box;
                font-family: inherit;
                font-weight: 550;
                box-shadow: inset 0 2px 4px rgba(194, 65, 12, 0.01);
            }
            input[type="text"]:focus {
                border-color: var(--primary);
                box-shadow: 0 0 0 4px var(--primary-glow);
            }
            
            .main-btn {
                width: 100%;
                background: linear-gradient(135deg, #c2410c, #ea580c);
                color: #fff;
                border: none;
                padding: 1.3rem;
                border-radius: 18px;
                font-weight: 800;
                cursor: pointer;
                font-size: 1.15rem;
                transition: all 0.25s;
                margin-bottom: 0.5rem;
                box-shadow: 0 10px 25px -5px rgba(194, 65, 12, 0.35);
                font-family: inherit;
                letter-spacing: 0.5px;
            }
            .main-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 15px 30px -5px rgba(194, 65, 12, 0.45);
            }
            .main-btn:active {
                transform: translateY(0);
            }
            .main-btn:disabled {
                opacity: 0.55;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            
            /* LOADING / LOADER */
            #loading {
                text-align: center;
                margin-top: 1.5rem;
                color: var(--primary);
                font-weight: 700;
                font-size: 1rem;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
            }
            .loader {
                width: 22px;
                height: 22px;
                border: 3px solid rgba(194, 65, 12, 0.15);
                border-top-color: var(--primary);
                border-radius: 50%;
                animation: spin 0.8s infinite linear;
                display: inline-block;
            }
            @keyframes spin { to { transform: rotate(360deg); } }
            
            /* LOTUS MANDALA CONCENTRIC ANIMATIONS */
            .lotus-container {
                display: none;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 12px;
                margin: 2rem 0;
            }
            .lotus-svg {
                animation: slow-rotate 40s linear infinite;
            }
            .pulsing-ring {
                transform-origin: center center;
                animation: ring-pulse 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
            }
            .ring-1 { animation-delay: 0s; }
            .ring-2 { animation-delay: 1s; }
            .ring-3 { animation-delay: 2s; }
            
            @keyframes ring-pulse {
                0% {
                    transform: scale(0.5);
                    opacity: 0;
                }
                50% {
                    opacity: 0.8;
                }
                100% {
                    transform: scale(1.3);
                    opacity: 0;
                }
            }
            .lotus-petals {
                animation: gentle-beat 4s ease-in-out infinite alternate;
                transform-origin: center center;
            }
            @keyframes gentle-beat {
                from { transform: scale(0.95); }
                to { transform: scale(1.05); }
            }
            
            /* ANSWERS & CITATIONS */
            #ans-container {
                margin-top: 2.2rem;
                display: none;
            }
            #ans {
                background: #fbf9f6;
                border: 1px solid rgba(194, 65, 12, 0.12);
                border-left: 4px solid var(--primary);
                padding: 2.2rem;
                border-radius: 20px;
                line-height: 1.8;
                position: relative;
                font-size: 1.05rem;
                box-shadow: inset 0 2px 8px rgba(194, 65, 12, 0.01);
            }
            #text-res {
                margin-bottom: 1.5rem;
                color: var(--text);
                font-family: var(--font-sans);
            }
            
            /* VOICE BUTTON */
            .voice-btn {
                background: var(--primary);
                border: none;
                width: auto;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 0.85rem 1.6rem;
                border-radius: 14px;
                color: #fff;
                font-weight: 700;
                transition: all 0.25s;
                cursor: pointer;
                font-family: inherit;
                font-size: 0.95rem;
                box-shadow: 0 6px 15px -3px rgba(194, 65, 12, 0.3);
            }
            .voice-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px -3px rgba(194, 65, 12, 0.4);
            }
            .voice-btn:active {
                transform: translateY(0);
            }
            #v-loading {
                display: flex;
                align-items: center;
                justify-content: center;
                width: 44px;
                height: 44px;
            }
            
            /* CUSTOM MEDIA PLAYER */
            .player-btn {
                transition: all 0.2s;
            }
            .player-btn:hover {
                transform: scale(1.1);
            }
            .player-btn:active {
                transform: scale(0.95);
            }
            
            .fade-in { animation: fadeIn 0.8s forwards; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
        </style>
    </head>
    <body>
        <!-- DYNAMIC BACKGROUND -->
        <div class="bg-decorations">
            <div class="circle circle-1"></div>
            <div class="circle circle-2"></div>
            <div class="chakra-watermark">
                <svg viewBox="-50 -50 100 100" width="100%" height="100%">
                    <circle cx="0" cy="0" r="10" fill="#c2410c" opacity="0.04"/>
                    <g stroke="#c2410c" stroke-width="1.2" stroke-linecap="round" opacity="0.04">
                        <line x1="0" y1="-12" x2="0" y2="-45" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(15)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(30)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(45)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(60)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(75)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(90)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(105)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(120)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(135)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(150)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(165)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(180)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(195)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(210)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(225)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(240)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(255)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(270)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(285)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(300)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(315)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(330)" />
                        <line x1="0" y1="-12" x2="0" y2="-45" transform="rotate(345)" />
                    </g>
                </svg>
            </div>
        </div>

        <!-- TOP BANNER -->
        <div class="top-banner">
            ♦♦ Celebrating Kannada Literature with Advanced AI Voice Agent ♦♦
        </div>

        <!-- NAVBAR -->
        <header class="nav-header">
            <div class="nav-container">
                <div class="logo">
                    <span class="logo-title">ಹೇಳಿ ಹೋಗು</span><span class="logo-sub">  ಕಾರಣ</span>
                </div>
                <nav class="nav-menu">
                    <span class="nav-item">ಕಾದಂಬರಿ</span>
                    <span class="nav-item active">AI Guide</span>
                </nav>
            </div>
        </header>

        <!-- HERO SECTION -->
        <div class="hero">
            <h1 class="fade-in">ಹೇಳಿ ಹೋಗು ಕಾರಣ</h1>
            <p class="fade-in" style="animation-delay: 0.1s">Your AI-powered guide through the literary world of Heli Hogu Karana. Ask anything about characters, themes, or the story.</p>
        </div>

        <!-- MAIN INTERACTION CONTAINER -->
        <div class="container fade-in" style="animation-delay: 0.2s">
            <div class="card">
                <!-- MEHRAB / ARCH SILHOUETTE CARD TOP OVERLAY -->
                <div style="position: absolute; top: 0; left: 0; width: 100%; height: 35px; z-index: 2; pointer-events: none; overflow: hidden; margin-top: -1px;">
                    <svg viewBox="0 0 100 20" preserveAspectRatio="none" style="width: 100%; height: 100%; fill: var(--bg-secondary);">
                        <path d="M0,0 L100,0 L100,20 C85,20 75,5 65,5 C58,5 55,2 50,0 C45,2 42,5 35,5 C25,5 15,20 0,20 Z" />
                    </svg>
                </div>
                <div class="settings">
                    <label class="toggle-label">
                        <input type="checkbox" id="auto-speak"> 🔊 Auto-play Voice Output
                    </label>
                    <span id="usage-counter" style="font-size: 0.85rem; font-weight: 700; color: var(--primary); background: var(--primary-light); padding: 4px 10px; border-radius: 99px;">Queries Today: 0 / 100</span>
                    <label class="toggle-label">
                        🌐 Output Language: 
                        <select id="lang-select" style="background:#ffffff; border:1px solid rgba(194, 65, 12, 0.2); color:#0f172a; border-radius:8px; padding:4px 10px; font-family:inherit; outline:none; cursor:pointer; font-weight:600;">
                            <option value="English">English</option>
                            <option value="Kannada">ಕನ್ನಡ (Kannada)</option>
                        </select>
                    </label>
                </div>

                <div class="suggestions">
                    <button class="sug-btn" onclick="setQ('Who is Himavant?')">Who is Himavant?</button>
                    <button class="sug-btn" onclick="setQ('Describe Prarthana')">About Prarthana</button>
                    <button class="sug-btn" onclick="setQ('What are the main themes?')">Main Themes</button>
                    <button class="sug-btn" onclick="setQ('How is Ravi related?')">Ravi's Role</button>
                </div>

                <input type="text" id="q" placeholder="What would you like to know?" required autoComplete="off">
                <button id="btn" class="main-btn" onclick="ask()">Analyze the Book</button>
                
                <div id="loading" class="lotus-container" style="display:none;">
                    <svg viewBox="0 0 100 100" class="lotus-svg" style="width: 80px; height: 80px;">
                        <circle cx="50" cy="50" r="10" fill="none" stroke="var(--primary)" stroke-width="1.2" class="pulsing-ring ring-1" />
                        <circle cx="50" cy="50" r="25" fill="none" stroke="var(--primary)" stroke-width="0.9" class="pulsing-ring ring-2" />
                        <circle cx="50" cy="50" r="40" fill="none" stroke="var(--primary)" stroke-width="0.6" class="pulsing-ring ring-3" />
                        <circle cx="50" cy="50" r="5" fill="var(--primary)" />
                        <g class="lotus-petals" fill="var(--primary)" opacity="0.9">
                            <path d="M50,35 C47,45 47,49 50,50 C53,49 53,45 50,35 Z" />
                            <path d="M50,35 C47,45 47,49 50,50 C53,49 53,45 50,35 Z" transform="rotate(45 50 50)" />
                            <path d="M50,35 C47,45 47,49 50,50 C53,49 53,45 50,35 Z" transform="rotate(90 50 50)" />
                            <path d="M50,35 C47,45 47,49 50,50 C53,49 53,45 50,35 Z" transform="rotate(135 50 50)" />
                            <path d="M50,35 C47,45 47,49 50,50 C53,49 53,45 50,35 Z" transform="rotate(180 50 50)" />
                            <path d="M50,35 C47,45 47,49 50,50 C53,49 53,45 50,35 Z" transform="rotate(225 50 50)" />
                            <path d="M50,35 C47,45 47,49 50,50 C53,49 53,45 50,35 Z" transform="rotate(270 50 50)" />
                            <path d="M50,35 C47,45 47,49 50,50 C53,49 53,45 50,35 Z" transform="rotate(315 50 50)" />
                            
                            <path d="M50,22 C45,40 45,47 50,50 C55,47 55,40 50,22 Z" opacity="0.6" transform="rotate(22.5 50 50)" />
                            <path d="M50,22 C45,40 45,47 50,50 C55,47 55,40 50,22 Z" opacity="0.6" transform="rotate(67.5 50 50)" />
                            <path d="M50,22 C45,40 45,47 50,50 C55,47 55,40 50,22 Z" opacity="0.6" transform="rotate(112.5 50 50)" />
                            <path d="M50,22 C45,40 45,47 50,50 C55,47 55,40 50,22 Z" opacity="0.6" transform="rotate(157.5 50 50)" />
                            <path d="M50,22 C45,40 45,47 50,50 C55,47 55,40 50,22 Z" opacity="0.6" transform="rotate(202.5 50 50)" />
                            <path d="M50,22 C45,40 45,47 50,50 C55,47 55,40 50,22 Z" opacity="0.6" transform="rotate(247.5 50 50)" />
                            <path d="M50,22 C45,40 45,47 50,50 C55,47 55,40 50,22 Z" opacity="0.6" transform="rotate(292.5 50 50)" />
                            <path d="M50,22 C45,40 45,47 50,50 C55,47 55,40 50,22 Z" opacity="0.6" transform="rotate(337.5 50 50)" />
                        </g>
                    </svg>
                    <div style="font-weight: 700; color: var(--primary); font-family: var(--font-serif); letter-spacing: 0.5px;">ಕಾದಂಬರಿ ವಿಶ್ಲೇಷಣೆ ಮಾಡಲಾಗುತ್ತಿದೆ...</div>
                </div>
                
                <div id="ans-container">
                    <div id="ans">
                        <div id="text-res"></div>
                        <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                            <button id="v-btn" class="voice-btn" onclick="speak()">
                                <span>🔊 Hear in English</span>
                            </button>
                            <div id="v-loading" style="display:none;"><div class="loader"></div></div>
                            
                            <!-- CUSTOM VOICE PLAYER WIDGET -->
                            <div id="media-player" style="display: none; align-items: center; gap: 12px; padding: 0.6rem 1rem; background: #faf6f0; border: 1px solid rgba(194, 65, 12, 0.1); border-radius: 14px; flex-grow: 1; min-width: 260px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <button id="play-pause-btn" class="player-btn" onclick="togglePlayPause()" style="background: var(--primary); border: none; width: 32px; height: 32px; border-radius: 50%; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; outline: none;">▶</button>
                                    <button class="player-btn" onclick="skipAudio(-5)" style="background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.85rem; font-weight: bold; outline: none; padding: 2px;">↩ 5s</button>
                                    <button class="player-btn" onclick="skipAudio(5)" style="background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.85rem; font-weight: bold; outline: none; padding: 2px;">5s ↪</button>
                                </div>
                                <div style="display: flex; align-items: center; gap: 8px; flex-grow: 1;">
                                    <span id="audio-current-time" style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">0:00</span>
                                    <input type="range" id="audio-slider" value="0" style="flex-grow: 1; height: 5px; border-radius: 3px; cursor: pointer; accent-color: var(--primary); outline: none;">
                                    <span id="audio-duration" style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">0:00</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentText = "";
            let isSpeaking = false;
            let currentAudio = null;
            let isSeeking = false;

            // Usage Counter Functions
            function updateUsageCounter() {
                const limit = 100;
                const today = new Date().toDateString();
                let count = parseInt(localStorage.getItem('query_count_today') || '0');
                let savedDate = localStorage.getItem('query_date_today');
                
                if (savedDate !== today) {
                    count = 0;
                    localStorage.setItem('query_count_today', '0');
                    localStorage.setItem('query_date_today', today);
                }
                
                document.getElementById('usage-counter').innerText = `Queries Today: ${count} / ${limit}`;
            }
            
            function incrementUsage() {
                let count = parseInt(localStorage.getItem('query_count_today') || '0');
                count += 1;
                localStorage.setItem('query_count_today', count.toString());
                updateUsageCounter();
            }

            // Page Load Initialization
            window.addEventListener('DOMContentLoaded', () => {
                updateUsageCounter();
            });

            // Time Formatter
            function formatTime(secs) {
                if (isNaN(secs)) return "0:00";
                const m = Math.floor(secs / 60);
                const s = Math.floor(secs % 60);
                return `${m}:${s < 10 ? '0' : ''}${s}`;
            }

            function setQ(txt) {
                document.getElementById('q').value = txt;
                ask();
            }

            // Robust Markdown Parser
            function formatMarkdown(text) {
                if (!text) return "";
                let html = text;
                
                // Escape HTML tags to prevent XSS
                html = html
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;");

                // Headers: ###, ##, #
                html = html.replace(/^### (.*?)$/gm, '<h3 style="color: var(--primary); margin-top: 1rem; margin-bottom: 0.5rem; font-family: var(--font-serif);">$1</h3>');
                html = html.replace(/^## (.*?)$/gm, '<h2 style="color: var(--primary); margin-top: 1.2rem; margin-bottom: 0.6rem; font-family: var(--font-serif);">$1</h2>');
                html = html.replace(/^# (.*?)$/gm, '<h1 style="color: var(--primary); margin-top: 1.5rem; margin-bottom: 0.8rem; font-family: var(--font-serif);">$1</h1>');

                // Lists: lines starting with * or - followed by a space
                html = html.replace(/^\s*[\*\-]\s+(.*?)$/gm, '<li style="margin-left: 1.5rem; margin-bottom: 0.25rem;">$1</li>');

                // Bold: **text** -> <strong>text</strong>
                html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

                // Italic: *text* -> <em>text</em>
                html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');

                // Citations: (Page X) or (Page X-Y) -> styled inline badges
                html = html.replace(/\(Page (\d+)\)/gi, '<span style="background:var(--primary-light); color:var(--primary); font-size:0.75rem; font-weight:700; padding:2px 6px; border-radius:4px; margin-left:4px; display:inline-block;">Page $1</span>');
                html = html.replace(/\(Page (\d+)-(\d+)\)/gi, '<span style="background:var(--primary-light); color:var(--primary); font-size:0.75rem; font-weight:700; padding:2px 6px; border-radius:4px; margin-left:4px; display:inline-block;">Pages $1-$2</span>');
                html = html.replace(/\(ಪುಟ (\d+)\)/g, '<span style="background:var(--primary-light); color:var(--primary); font-size:0.75rem; font-weight:700; padding:2px 6px; border-radius:4px; margin-left:4px; display:inline-block;">ಪುಟ $1</span>');
                html = html.replace(/\(ಪುಟ (\d+)-(\d+)\)/g, '<span style="background:var(--primary-light); color:var(--primary); font-size:0.75rem; font-weight:700; padding:2px 6px; border-radius:4px; margin-left:4px; display:inline-block;">ಪುಟ $1-$2</span>');
                html = html.replace(/\(ಪುಟ ([೦-೯]+)\)/g, '<span style="background:var(--primary-light); color:var(--primary); font-size:0.75rem; font-weight:700; padding:2px 6px; border-radius:4px; margin-left:4px; display:inline-block;">ಪುಟ $1</span>');
                html = html.replace(/\(ಪುಟ ([೦-೯]+)-([೦-೯]+)\)/g, '<span style="background:var(--primary-light); color:var(--primary); font-size:0.75rem; font-weight:700; padding:2px 6px; border-radius:4px; margin-left:4px; display:inline-block;">ಪುಟ $1-$2</span>');

                // Convert remaining newlines to <br>
                html = html.replace(/\n/g, '<br>');

                return html;
            }

            // Initialize Custom Audio Listeners
            function initAudio(base64Audio) {
                if (currentAudio) {
                    currentAudio.pause();
                }
                currentAudio = new Audio("data:audio/mp3;base64," + base64Audio);
                
                const slider = document.getElementById('audio-slider');
                const currentTimeEl = document.getElementById('audio-current-time');
                const durationEl = document.getElementById('audio-duration');
                const playPauseBtn = document.getElementById('play-pause-btn');

                currentAudio.addEventListener('loadedmetadata', () => {
                    durationEl.innerText = formatTime(currentAudio.duration);
                    slider.value = 0;
                });

                currentAudio.addEventListener('timeupdate', () => {
                    if (!isSeeking && currentAudio) {
                        slider.value = (currentAudio.currentTime / currentAudio.duration) * 100 || 0;
                        currentTimeEl.innerText = formatTime(currentAudio.currentTime);
                    }
                });

                currentAudio.addEventListener('ended', () => {
                    isSpeaking = false;
                    playPauseBtn.innerText = "▶";
                    document.getElementById('v-btn').style.display = 'inline-flex';
                    document.getElementById('v-loading').style.display = 'none';
                    document.getElementById('media-player').style.display = 'none';
                    slider.value = 0;
                    currentTimeEl.innerText = "0:00";
                    currentAudio = null;
                });
                
                slider.addEventListener('mousedown', () => { isSeeking = true; });
                slider.addEventListener('mouseup', () => {
                    isSeeking = false;
                    if (currentAudio) {
                        const seekTo = (slider.value / 100) * currentAudio.duration;
                        currentAudio.currentTime = seekTo;
                    }
                });
                slider.addEventListener('touchstart', () => { isSeeking = true; });
                slider.addEventListener('touchend', () => {
                    isSeeking = false;
                    if (currentAudio) {
                        const seekTo = (slider.value / 100) * currentAudio.duration;
                        currentAudio.currentTime = seekTo;
                    }
                });
                slider.addEventListener('input', () => {
                    if (currentAudio) {
                        const seekTo = (slider.value / 100) * (currentAudio.duration || 0);
                        currentTimeEl.innerText = formatTime(seekTo);
                    }
                });
            }

            function togglePlayPause() {
                if (!currentAudio) return;
                const playPauseBtn = document.getElementById('play-pause-btn');
                if (currentAudio.paused) {
                    currentAudio.play().then(() => {
                        playPauseBtn.innerText = "⏸";
                        isSpeaking = true;
                    }).catch(err => {
                        console.error('Playback failed:', err);
                    });
                } else {
                    currentAudio.pause();
                    playPauseBtn.innerText = "▶";
                    isSpeaking = false;
                }
            }

            function skipAudio(seconds) {
                if (!currentAudio) return;
                let newTime = currentAudio.currentTime + seconds;
                if (newTime < 0) newTime = 0;
                if (newTime > currentAudio.duration) newTime = currentAudio.duration;
                currentAudio.currentTime = newTime;
                document.getElementById('audio-slider').value = (newTime / currentAudio.duration) * 100 || 0;
                document.getElementById('audio-current-time').innerText = formatTime(newTime);
            }

            async function ask() {
                // Stop any actively playing voice immediately when a new question starts
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }
                isSpeaking = false;
                document.getElementById('media-player').style.display = 'none';
                
                const q = document.getElementById('q').value;
                const btn = document.getElementById('btn');
                const load = document.getElementById('loading');
                const cont = document.getElementById('ans-container');
                const res = document.getElementById('text-res');
                const lang = document.getElementById('lang-select').value;
                if (!q) return;
                
                btn.disabled = true; load.style.display = 'flex'; cont.style.display = 'none';
                try {
                    const r = await fetch('/chat', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({question: q, language: lang})});
                    const d = await r.json();
                    
                    // Increment and update local usage count
                    incrementUsage();
                    
                    currentText = d.answer;
                    res.innerHTML = formatMarkdown(d.answer);
                    cont.style.display = 'block';
                    cont.classList.add('fade-in');
                    
                    // Reset voice buttons state
                    document.getElementById('v-btn').style.display = 'inline-flex';
                    document.getElementById('v-loading').style.display = 'none';
                    document.getElementById('media-player').style.display = 'none';
                    
                    if (document.getElementById('auto-speak').checked) {
                        speak();
                    }
                } catch (e) { alert("Error: " + e.message); }
                btn.disabled = false; load.style.display = 'none';
            }

            async function speak() {
                const vBtn = document.getElementById('v-btn');
                const vLoad = document.getElementById('v-loading');
                const lang = document.getElementById('lang-select').value;
                
                // If speaking, clicking the voice button will stop current playback
                if (isSpeaking) {
                    if (currentAudio) {
                        currentAudio.pause();
                        currentAudio = null;
                    }
                    isSpeaking = false;
                    vBtn.style.display = 'inline-flex';
                    vLoad.style.display = 'none';
                    document.getElementById('media-player').style.display = 'none';
                    return;
                }
                
                vBtn.style.display = 'none'; vLoad.style.display = 'block';
                isSpeaking = true;

                try {
                    const r = await fetch('/voice', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: currentText, language: lang})});
                    const d = await r.json();
                    vLoad.style.display = 'none';
                    if (d.audio) {
                        document.getElementById('media-player').style.display = 'flex';
                        initAudio(d.audio);
                        togglePlayPause(); // Auto play
                    } else { 
                        alert("Voice engine unavailable. Please try again."); 
                        isSpeaking = false; vBtn.style.display = 'inline-flex';
                        document.getElementById('media-player').style.display = 'none';
                    }
                } catch (e) { 
                    alert("Voice Error: " + e.message); 
                    isSpeaking = false; vBtn.style.display = 'inline-flex'; vLoad.style.display = 'none';
                    document.getElementById('media-player').style.display = 'none';
                }
            }

            // Sync dynamic voice button labels to language selection
            document.getElementById('lang-select').addEventListener('change', (e) => {
                const val = e.target.value;
                const vBtnSpan = document.querySelector('#v-btn span');
                if (val === 'Kannada') {
                    vBtnSpan.innerText = '🔊 Hear in Kannada';
                } else {
                    vBtnSpan.innerText = '🔊 Hear in English';
                }
                // Stop any audio playing when language selection shifts
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }
                isSpeaking = false;
                document.getElementById('v-btn').style.display = 'inline-flex';
                document.getElementById('v-loading').style.display = 'none';
                document.getElementById('media-player').style.display = 'none';
            });
        </script>
    </body>
    </html>

    """
handler = app
