# api/index.py - FastAPI version for Vercel deployment Final v5 (Stable)
from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import os, re, requests, json, traceback, base64, time, threading
from typing import List, Optional
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123").strip()

# Configure Gemini SDK with strict key cleaning
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"SDK Config Error: {e}")

# ── Vercel KV / Upstash Redis REST Helpers ─────────────────────────────
def run_kv_command(cmd_args: list):
    url = os.environ.get("KV_REST_API_URL")
    token = os.environ.get("KV_REST_API_TOKEN")
    if not url or not token:
        return None
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        url = url.strip()
        resp = requests.post(url, headers=headers, json=cmd_args, timeout=5)
        if resp.status_code == 200:
            return resp.json().get("result")
    except Exception as e:
        print(f"[ERROR] KV command {cmd_args[0]} failed: {e}")
    return None

def get_kv_data(key: str, default=None):
    res = run_kv_command(["GET", key])
    if res is not None:
        try:
            return json.loads(res)
        except Exception:
            pass
    return default

def set_kv_data(key: str, value) -> bool:
    try:
        payload = json.dumps(value)
        res = run_kv_command(["SET", key, payload])
        return res == "OK"
    except Exception:
        return False

BOOK_CONTEXT = "You are a professional literary assistant. Use these Kannada book passages to answer the user question in English. Provide deep analysis and always cite page numbers."

app = FastAPI(title="Kannada Book AI Agent + Voice")

class ChatRequest(BaseModel):
    question: str
    language: str = "English"
    history: Optional[List[dict]] = []

class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = []
    audio_base64: str = "" # New: returned if voice is requested

class VoiceRequest(BaseModel):
    text: str
    language: str = "English"

class FeedbackRequest(BaseModel):
    name: str
    rating: int
    comment: str
    uid: Optional[str] = None

class PaymentLog(BaseModel):
    payer_name: str
    amount: str
    utr_ref: Optional[str] = None
    note: Optional[str] = None
    uid: Optional[str] = None

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

def call_groq(prompt, history=None, system_instruction=None, retries=1):
    """Fallback to Groq with active model fallbacks (Llama 3.3 -> Llama 3.1 -> Llama 4 Scout)."""
    if not GROQ_API_KEY:
        return "[ERROR]: GROQ_API_KEY is missing."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "meta-llama/llama-4-scout-17b-16e-instruct"]
    
    sys_instruction = system_instruction if system_instruction else BOOK_CONTEXT
    
    last_err = ""
    for model in models:
        for attempt in range(retries + 1):
            messages = [{"role": "system", "content": sys_instruction}]
            if history:
                for msg in history:
                    role = "user" if msg.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": msg.get("content", "")})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 1024
            }
            
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=20)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                elif resp.status_code == 429:
                    last_err = f"Rate limit 429 on {model}"
                    if model != models[-1]:
                        break
                    time.sleep(2)
                    continue
                resp.raise_for_status()
            except Exception as e:
                last_err = f"{model} error: {str(e)}"
                if attempt < retries:
                    time.sleep(1.5)
                    continue
                break
                
    return f"[GROQ FAILED]: {last_err}"

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

def call_gemini(prompt, history=None, system_instruction=None, retries=1):
    """Deepest Gemini Safety Bypass + System Prompting."""
    if not GEMINI_API_KEY: 
        return call_groq(prompt, history=history, system_instruction=system_instruction)
    
    last_error = ""
    model_name = get_best_gemini_model()
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    sys_instruction = system_instruction if system_instruction else BOOK_CONTEXT
    
    for attempt in range(retries + 1):
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=sys_instruction
            )
            if history:
                contents = []
                for msg in history:
                    role = "user" if msg.get("role") == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
                contents.append({"role": "user", "parts": [{"text": prompt}]})
                response = model.generate_content(contents, safety_settings=safety_settings)
            else:
                response = model.generate_content(prompt, safety_settings=safety_settings)
            
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    return response.text.strip()
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
                
    return call_groq(prompt, history=history, system_instruction=system_instruction)

def call_gtts_parallel(text, language="kn-IN"):
    """Fetch Google TTS chunks in parallel, concatenate as raw MP3 bytes."""
    try:
        is_kannada = "kn" in language.lower()
        lang = "kn" if is_kannada else "en"
        
        # Split text into chunks < 200 characters to comply with Google TTS limits
        sentences = re.split(r'(?<=[.!?।])\s+', text)
        chunks = []
        current_chunk = ""
        for s in sentences:
            if len(current_chunk) + len(s) + 1 < 200:
                current_chunk += (" " if current_chunk else "") + s
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = s
        if current_chunk:
            chunks.append(current_chunk)
            
        def fetch_chunk(chunk_info):
            idx, chunk = chunk_info
            if not chunk.strip():
                return idx, b""
            url = "https://translate.google.com/translate_tts"
            params = {
                "ie": "UTF-8",
                "tl": lang,
                "client": "tw-ob",
                "q": chunk.strip()
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            for attempt in range(3):
                try:
                    resp = requests.get(url, params=params, headers=headers, timeout=8)
                    if resp.status_code == 200:
                        return idx, resp.content
                    time.sleep(0.3)
                except Exception:
                    time.sleep(0.3)
            return idx, b""

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(len(chunks) or 1, 10)) as executor:
            results = list(executor.map(fetch_chunk, enumerate(chunks)))
            
        results.sort(key=lambda x: x[0])
        audio_bytes = b"".join(r[1] for r in results if r[1])
        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print(f"Parallel gTTS fallback failed: {e}")
    return ""

def call_sarvam_tts(text, language="kn-IN"):
    """Call Sarvam TTS 'Meera' voice (bulbul:v3) in parallel with fallback to Google TTS (gTTS)."""
    # Clean citations and errors
    clean = re.sub(r'\[Page \d+\]:', '', text).strip()
    clean = re.sub(r'📄 Sources:.*', '', clean).strip()
    clean = re.sub(r'\[\(?:GEMINI FAILED|GROQ FAILED|BACKEND ERROR|ERROR\)[^\]]*\]', '', clean).strip()

    # Strip Markdown syntax for cleaner TTS audio reading (e.g. asterisks, code blocks, headers, bullet symbols)
    clean = re.sub(r'```[\s\S]*?```', '', clean)
    clean = re.sub(r'`([^`]+)`', r'\1', clean)
    clean = re.sub(r'#+\s*(.*)', r'\1', clean)
    clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
    clean = re.sub(r'\*\*([^*]+)\*\*', r'\1', clean)
    clean = re.sub(r'\*([^*]+)\*', r'\1', clean)
    clean = re.sub(r'__([^_]+)__', r'\1', clean)
    clean = re.sub(r'_([^_]+)_', r'\1', clean)
    clean = re.sub(r'^\s*[-*+]\s+', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^\s*>\s+', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'\n+', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean)

    # Limit text length to avoid excessive API usage
    if len(clean) > 4000:
        truncated = clean[:4000]
        # Find last sentence boundary
        last_boundary = max(truncated.rfind('.'), truncated.rfind('।'), truncated.rfind('?'), truncated.rfind('!'))
        if last_boundary > 3500:
            clean = truncated[:last_boundary + 1]
        else:
            clean = truncated.strip() + "..."

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
            
            headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
            headers_key = {"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"}
            
            def fetch_chunk_audio(chunk):
                if not chunk.strip():
                    return None
                payload = {
                    "inputs": [chunk.strip()],
                    "target_language_code": target_lang,
                    "speaker": "meera",
                    "model": "bulbul:v3",
                    "pace": 1.0
                }
                try:
                    resp = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers, json=payload, timeout=15)
                    if resp.status_code != 200:
                        resp = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers_key, json=payload, timeout=15)
                    if resp.status_code == 200:
                        res_json = resp.json()
                        aud_b64 = res_json.get("audios", [""])[0] if "audios" in res_json else res_json.get("audio", "")
                        if aud_b64:
                            return base64.b64decode(aud_b64)
                except Exception as e:
                    print(f"Error fetching chunk: {e}")
                return None

            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=min(len(chunks_list) or 1, 6)) as executor:
                audio_bytes_list = list(executor.map(fetch_chunk_audio, chunks_list))
                
            audio_bytes_list = [ab for ab in audio_bytes_list if ab is not None]
            
            if len(audio_bytes_list) < len(chunks_list) or not audio_bytes_list:
                print("One or more chunks failed in Sarvam TTS. Falling back to parallel gTTS.")
                return call_gtts_parallel(clean, language=language)
            
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
            print(f"Sarvam TTS failed, falling back to parallel gTTS: {e}")

    # 2. Fallback to Google TTS (gTTS)
    return call_gtts_parallel(clean, language=language)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Use globally loaded BOOK_DATA
        chunks = search_text(request.question, BOOK_DATA, top_k=4) 
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
            sys_instruction = (
                "You are a professional literary assistant for the Kannada novel 'Heli Hogu Kaarana'. "
                "The novel was written by the famous Kannada author and journalist Ravi Belagere (ರವಿ ಬೆಳಗೆರೆ). "
                "Note that Ravi Belagere is the author and narrator of the story; he is not a character inside the novel itself. "
                "If the user asks about 'Ravi' or 'Ravi Belagere' or 'Ravi\'s role', explain that he is the author and narrator of the novel, and describe his narrative style and connection as the author. "
                "Use the retrieved passages and this context to answer the user's question. "
                "CRITICAL RULE: You must answer ONLY in English. Do NOT write in Kannada, and do NOT mix Kannada and English in your reply. "
                "All explanations, analysis, and text must be in English. "
                "If the conversation history contains messages in Kannada, ignore their language and reply only in English. "
                "Always cite the exact page numbers from the passages in your answer when referencing the text."
            )
            full_prompt = f"""NOVEL METADATA:
- Title: Heli Hogu Kaarana (ಹೇಳಿ ಹೋಗು ಕಾರಣ)
- Author: Ravi Belagere (ರವಿ ಬೆಳಗೆರೆ) (Note: Ravi Belagere is the author and narrator of the novel, not a character in the story.)
- Main Characters: Himavant (ಹಿಮವಂತ್), Prarthana (ಪ್ರಾರ್ಥನಾ)

RETRIEVED NOVEL PASSAGES:
{pagetext}

Answer the user's question in detail using the retrieved passages and the novel metadata context. Follow the instructions to write the entire answer in English.

QUESTION: {request.question}
ANSWER in English:"""
        else:
            sys_instruction = (
                "ನೀವು ರವಿ ಬೆಳಗೆರೆ ಅವರು ಬರೆದ 'ಹೇಳಿ ಹೋಗು ಕಾರಣ' ಕಾದಂಬರಿಯ ವೃತ್ತಿಪರ ಸಾಹಿತ್ಯ ಸಹಾಯಕರು. "
                "ರವಿ ಬೆಳಗೆರೆ ಅವರು ಈ ಕಾದಂಬರಿಯ ಕರ್ತೃ ಮತ್ತು ಸೂತ್ರಧಾರ/ನಿರೂಪಕರಾಗಿದ್ದಾರೆ; ಅವರು ಕಥೆಯ ಒಳಗಿನ ಪಾತ್ರವಲ್ಲ ಎಂಬುದನ್ನು ಗಮನಿಸಿ. "
                "ಬಳಕೆದಾರರು 'ರವಿ' ಅಥವಾ 'ರವಿ ಬೆಳಗೆರೆ' ಅಥವಾ ಅವರ ಪಾತ್ರದ ಬಗ್ಗೆ ಕೇಳಿದರೆ, ಅವರು ಕಾದಂಬರಿಯ ಕರ್ತೃ/ನಿರೂಪಕರು ಎಂದು ವಿವರಿಸಿ. "
                "ಹಿಂಪಡೆದ ಪುಸ್ತಕದ ಭಾಗಗಳನ್ನು ಮತ್ತು ಈ ಹಿನ್ನೆಲೆಯನ್ನು ಬಳಸಿಕೊಂಡು ಬಳಕೆದಾರರ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರಿಸಿ. "
                "ಪ್ರಮುಖ ನಿಯಮ: ನೀವು ಕಡ್ಡಾಯವಾಗಿ ಮತ್ತು ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡದಲ್ಲೇ ಉತ್ತರಿಸಬೇಕು. "
                "ಯಾವುದೇ ಕಾರಣಕ್ಕೂ ಇಂಗ್ಲಿಷ್ ಬಳಸಬೇಡಿ, ಮತ್ತು ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡದ ಮಿಶ್ರಣವನ್ನು ಬಳಸಬೇಡಿ. "
                "ಎಲ್ಲಾ ವಿವರಣೆಗಳು, ವಿಶ್ಲೇಷಣೆಗಳು ಮತ್ತು ಪಠ್ಯಗಳು ಕಡ್ಡಾಯವಾಗಿ ಕನ್ನಡದಲ್ಲೇ ಇರಬೇಕು. "
                "ಸಂಭಾಷಣೆಯ ಇತಿಹಾಸದಲ್ಲಿ (history) ಇಂಗ್ಲಿಷ್ ಸಂದೇಶಗಳಿದ್ದರೂ ಸಹ, ಅವುಗಳನ್ನು ನಿರ್ಲಕ್ಷಿಸಿ ಮತ್ತು ಈ ಪ್ರಸ್ತುತ ಪ್ರಶ್ನೆಗೆ ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡದಲ್ಲೇ ಉತ್ತರಿಸಿ. "
                "ಉತ್ತರದಲ್ಲಿ ಕಡ್ಡಾಯವಾಗಿ ಸೂಕ್ತ ಪುಟ ಸಂಖ್ಯೆಗಳನ್ನು ಉಲ್ಲೇಖಿಸಿ."
            )
            full_prompt = f"""ಕಾದಂಬರಿಯ ಮಾಹಿತಿ (NOVEL METADATA):
- ಶೀರ್ಷಿಕೆ: ಹೇಳಿ ಹೋಗು ಕಾರಣ
- ಲೇಖಕರು: ರವಿ ಬೆಳಗೆರೆ (ಗಮನಿಸಿ: ರವಿ ಬೆಳಗೆರೆ ಅವರು ಕಾದಂಬರಿಯ ಲೇಖಕ ಮತ್ತು ನಿರೂಪಕರಾಗಿದ್ದಾರೆ; ಅವರು ಕಥೆಯ ಒಳಗಿನ ಪಾತ್ರವಲ್ಲ.)
- ಮುಖ್ಯ ಪಾತ್ರಗಳು: ಹಿಮವಂತ್ (ಹಿಮವಂತ), ಪ್ರಾರ್ಥನಾ

ಪುಸ್ತಕದಿಂದ ತೆಗೆದ ವಿಷಯ (RETRIEVED NOVEL PASSAGES):
{pagetext}

ಹಿಂಪಡೆದ ಭಾಗಗಳನ್ನು ಮತ್ತು ಕಾದಂಬರಿಯ ಮಾಹಿತಿಯನ್ನು ಬಳಸಿಕೊಂಡು ಬಳಕೆದಾರರ ಪ್ರಶ್ನೆಗೆ ವಿವರವಾಗಿ ಉತ್ತರಿಸಿ. ಸಂಪೂರ್ಣ ಉತ್ತರವನ್ನು ಕನ್ನಡದಲ್ಲೇ ಬರೆಯುವ ನಿಯಮವನ್ನು ಪಾಲಿಸಿ.

ಪ್ರಶ್ನೆ (QUESTION): {request.question}
ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರ (ANSWER in Kannada):"""
        
        answer = call_gemini(full_prompt, history=request.history, system_instruction=sys_instruction)
        return ChatResponse(answer=answer, sources=retrieved_pages)
    except Exception:
        return ChatResponse(answer=f"[BACKEND ERROR]: {traceback.format_exc()[:500]}", sources=[])

@app.post("/voice")
async def voice(request: VoiceRequest):
    # Map requested language option to ISO code
    lang_code = "kn-IN" if request.language == "Kannada" else "en-IN"
    audio_b64 = call_sarvam_tts(request.text, language=lang_code)
    return {"audio": audio_b64}

def get_ip_location(ip: str) -> str:
    """Fetch client location (City, Region, Country) using ip-api.com API."""
    if not ip or ip in ["127.0.0.1", "localhost", "Unknown"] or ip.startswith("192.168.") or ip.startswith("10."):
        return "Local Test / Unknown"
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                city = data.get("city", "")
                region = data.get("regionName", "")
                country = data.get("country", "")
                parts = [p for p in [city, region, country] if p]
                if parts:
                    return ", ".join(parts)
    except Exception as e:
        print(f"[WARNING] Geolocation lookup failed for IP {ip}: {e}")
    return "Unknown Location"

def log_download(edition: str, is_download: bool, ip: str, user_agent: str, uid: Optional[str] = None, uname: Optional[str] = None):
    try:
        location = get_ip_location(ip)
        
        log_data = {
            "edition": edition,
            "type": "Offline Download" if is_download else "Online Read",
            "ip": ip,
            "location": location,
            "user_agent": user_agent,
            "uid": uid or "Unknown",
            "uname": uname or "",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Load existing download logs from bundled path
        bundled_logs = []
        log_dir = os.path.join(os.path.dirname(__file__), "data")
        if not os.path.exists(log_dir):
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            if not os.path.exists(log_dir):
                log_dir = "data"
        log_file = os.path.join(log_dir, "downloads.json")
        
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    bundled_logs = json.load(f)
            except Exception:
                pass

        # Load existing logs from /tmp for Vercel persistence
        tmp_log_file = "/tmp/downloads.json"
        tmp_logs = []
        if os.path.exists(tmp_log_file):
            try:
                with open(tmp_log_file, "r", encoding="utf-8") as f:
                    tmp_logs = json.load(f)
            except Exception:
                pass

        # Load existing logs from Vercel KV
        kv_logs = get_kv_data("kannada_rag_downloads", [])

        # Combine logs to prevent loss
        seen = set()
        logs = []
        def get_log_key(l):
            return (l.get("edition", ""), l.get("type", ""), l.get("ip", ""), l.get("user_agent", ""), l.get("timestamp", ""))

        for l in kv_logs + bundled_logs + tmp_logs:
            key = get_log_key(l)
            if key not in seen:
                seen.add(key)
                logs.append(l)

        # Append new log
        new_key = get_log_key(log_data)
        if new_key not in seen:
            logs.append(log_data)
            
        if len(logs) > 500:
            logs = logs[-500:]

        # Save to Vercel KV
        set_kv_data("kannada_rag_downloads", logs)

        # Try to write to bundled directory
        write_success = False
        try:
            os.makedirs(log_dir, exist_ok=True)
            with open(log_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
            write_success = True
        except Exception as file_err:
            print(f"[WARNING]: Could not write download logs to bundled folder: {file_err}")
            
        # Fallback to write to /tmp on serverless environments
        if not write_success:
            try:
                with open(tmp_log_file, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=2, ensure_ascii=False)
            except Exception as tmp_err:
                print(f"[ERROR]: Could not write download logs to /tmp fallback: {tmp_err}")
    except Exception as e:
        print(f"[ERROR] Failed logging download: {e}")

def get_download_logs():
    # Read from Vercel KV first
    kv_logs = get_kv_data("kannada_rag_downloads", [])

    # Read download logs from bundled data
    log_dir = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(log_dir):
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        if not os.path.exists(log_dir):
            log_dir = "data"
            
    log_file = os.path.join(log_dir, "downloads.json")
    
    bundled_logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                bundled_logs = json.load(f)
        except Exception:
            pass

    # Read logs from /tmp for Vercel persistence
    tmp_log_file = "/tmp/downloads.json"
    tmp_logs = []
    if os.path.exists(tmp_log_file):
        try:
            with open(tmp_log_file, "r", encoding="utf-8") as f:
                tmp_logs = json.load(f)
        except Exception:
            pass

    # Combine feeds to avoid duplication
    seen = set()
    logs = []
    def get_log_key(l):
        return (l.get("edition", ""), l.get("type", ""), l.get("ip", ""), l.get("user_agent", ""), l.get("timestamp", ""))

    for l in kv_logs + bundled_logs + tmp_logs:
        key = get_log_key(l)
        if key not in seen:
            seen.add(key)
            logs.append(l)
            
    # Sort logs by timestamp descending
    try:
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception:
        pass
        
    return logs

# ── E-Book Read Route ───────────────────────────────────────────────────
@app.get("/api/read/{edition}")
async def read_ebook(edition: str, request: Request, download: Optional[bool] = False, uid: Optional[str] = None, uname: Optional[str] = None):
    """
    Read a compiled HTML e-book online.
    edition: 'kannada', 'english', or 'bilingual'
    """
    edition = edition.lower()
    
    if edition not in ["kannada", "english", "bilingual"]:
        raise HTTPException(status_code=400, detail="Invalid edition. Choose 'kannada', 'english', or 'bilingual'.")
        
    # Extract client IP address
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "Unknown"
        
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Run logging and geolocation in a background thread to prevent delay in serving ebook
    threading.Thread(target=log_download, args=(edition, download, ip, user_agent, uid, uname)).start()
    
    filename = f"heli_hogu_karana_{edition}.html"
    
    # Check possible search paths for compiled ebooks
    search_paths = [
        os.path.join(os.path.dirname(__file__), "data", "ebooks", filename),
        os.path.join(os.path.dirname(__file__), "..", "data", "ebooks", filename),
        os.path.join("data", "ebooks", filename),
        os.path.join("/var/task/data/ebooks", filename),
        os.path.join("/var/task/api/data/ebooks", filename),
    ]
    
    file_path = None
    for p in search_paths:
        if os.path.exists(p):
            file_path = p
            break
            
    if not file_path:
        raise HTTPException(
            status_code=404, 
            detail=f"E-book file '{filename}' not found. Please compile it first using local administrative scripts."
        )
        
    if download:
        return FileResponse(
            file_path,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    # Serve directly inline in browser
    return FileResponse(file_path, media_type="text/html")

@app.post("/api/feedback")
async def save_feedback(request: FeedbackRequest, req_obj: Request):
    try:
        # Extract client IP address to link user identity on dashboard
        forwarded = req_obj.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = req_obj.client.host if req_obj.client else "Unknown"
            
        feedback_data = {
            "name": request.name,
            "rating": request.rating,
            "comment": request.comment,
            "ip": ip,
            "uid": request.uid or "Unknown",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Log to stdout for real-time Vercel logs
        print(f"[FEEDBACK SUBMISSION] Name: {feedback_data['name']} | Rating: {feedback_data['rating']} stars | Comment: {feedback_data['comment']} | IP: {ip}")
        
        # Load existing feedback from bundled path
        bundled_feedbacks = []
        feedback_dir = os.path.join(os.path.dirname(__file__), "data")
        if not os.path.exists(feedback_dir):
            feedback_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            if not os.path.exists(feedback_dir):
                feedback_dir = "data"
        feedback_file = os.path.join(feedback_dir, "feedback.json")
        
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, "r", encoding="utf-8") as f:
                    bundled_feedbacks = json.load(f)
            except Exception:
                pass

        # Load existing feedback from /tmp for Vercel persistence
        tmp_feedback_file = "/tmp/feedback.json"
        tmp_feedbacks = []
        if os.path.exists(tmp_feedback_file):
            try:
                with open(tmp_feedback_file, "r", encoding="utf-8") as f:
                    tmp_feedbacks = json.load(f)
            except Exception:
                pass

        # Load existing feedback from Vercel KV
        kv_feedbacks = get_kv_data("kannada_rag_feedback", [])

        # Combine feedback to prevent loss of local or remote inputs
        seen = set()
        feedbacks = []
        def get_fb_key(fb):
            return (fb.get("name", ""), fb.get("rating", 0), fb.get("comment", ""), fb.get("timestamp", ""))

        for fb in kv_feedbacks + bundled_feedbacks + tmp_feedbacks:
            key = get_fb_key(fb)
            if key not in seen:
                seen.add(key)
                feedbacks.append(fb)

        # Append new feedback
        new_key = get_fb_key(feedback_data)
        if new_key not in seen:
            feedbacks.append(feedback_data)
        
        # Save to Vercel KV
        set_kv_data("kannada_rag_feedback", feedbacks)
        
        # Try to write to bundled directory (local testing environments)
        write_success = False
        try:
            os.makedirs(feedback_dir, exist_ok=True)
            with open(feedback_file, "w", encoding="utf-8") as f:
                json.dump(feedbacks, f, indent=2, ensure_ascii=False)
            write_success = True
        except Exception as file_err:
            print(f"[WARNING]: Could not write feedback to bundled data folder: {file_err}")
            
        # Fallback to write to /tmp on serverless environments
        if not write_success:
            try:
                with open(tmp_feedback_file, "w", encoding="utf-8") as f:
                    json.dump(feedbacks, f, indent=2, ensure_ascii=False)
                print("[INFO]: Successfully wrote feedback to /tmp/feedback.json")
            except Exception as tmp_err:
                print(f"[ERROR]: Could not write feedback to /tmp fallback: {tmp_err}")
                
        return {"status": "success", "message": "Feedback submitted successfully!"}
    except Exception as e:
        print(f"[ERROR]: Feedback submission failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/log-payment")
async def log_payment(req: PaymentLog, req_obj: Request):
    """Log a payment acknowledgment from a user after they paid via UPI."""
    from datetime import datetime, timezone
    import socket
    try:
        ip = req_obj.headers.get("x-forwarded-for", req_obj.client.host if req_obj.client else "Unknown")
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()
    except Exception:
        ip = "Unknown"

    entry = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "payer_name": req.payer_name.strip() or "Anonymous",
        "amount": req.amount.strip(),
        "utr_ref": req.utr_ref.strip() if req.utr_ref else "Not provided",
        "note": req.note.strip() if req.note else "",
        "uid": req.uid or "Unknown",
        "ip": ip,
    }

    # Load existing, append, save back to KV
    existing = get_kv_data("kannada_rag_payments", [])
    if not isinstance(existing, list):
        existing = []
    existing.append(entry)
    # Also try /tmp fallback
    try:
        set_kv_data("kannada_rag_payments", existing)
    except Exception:
        pass
    try:
        with open("/tmp/payments.json", "w", encoding="utf-8") as f:
            json.dump(existing, f)
    except Exception:
        pass

    return {"status": "success", "message": "Thank you! Payment noted."}


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(password: Optional[str] = None):
    if not password or password.strip() != ADMIN_PASSWORD:
        return HTMLResponse(
            status_code=401,
            content=f"""
            <html>
                <head>
                    <title>401 Unauthorized</title>
                    <style>
                        body {{ font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #fffcf8; color: #0f172a; margin: 0; }}
                        .card {{ padding: 2rem; border: 1px solid rgba(194, 65, 12, 0.2); border-radius: 12px; background: white; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
                        input {{ padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; margin: 10px 0; outline: none; width: 220px; text-align: center; }}
                        button {{ padding: 8px 16px; border: none; background: #c2410c; color: white; border-radius: 6px; cursor: pointer; font-weight: bold; }}
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h2>🔒 Admin Login</h2>
                        <p>Please enter the admin password.</p>
                        <form method="get">
                            <input type="password" name="password" placeholder="Password" autofocus><br>
                            <button type="submit">Unlock</button>
                        </form>
                    </div>
                </body>
            </html>
            """
        )
        
    # Read feedback from bundled data
    feedback_dir = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(feedback_dir):
        feedback_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        if not os.path.exists(feedback_dir):
            feedback_dir = "data"
            
    feedback_file = os.path.join(feedback_dir, "feedback.json")
    
    bundled_feedbacks = []
    if os.path.exists(feedback_file):
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                bundled_feedbacks = json.load(f)
        except Exception:
            pass

    # Read feedback from /tmp for Vercel persistence
    tmp_feedback_file = "/tmp/feedback.json"
    tmp_feedbacks = []
    if os.path.exists(tmp_feedback_file):
        try:
            with open(tmp_feedback_file, "r", encoding="utf-8") as f:
                tmp_feedbacks = json.load(f)
        except Exception:
            pass

    # Combine feeds to avoid duplication
    seen = set()
    feedbacks = []
    def get_fb_key(fb):
        return (fb.get("name", ""), fb.get("rating", 0), fb.get("comment", ""), fb.get("timestamp", ""))

    kv_feedbacks = get_kv_data("kannada_rag_feedback", [])

    for fb in kv_feedbacks + bundled_feedbacks + tmp_feedbacks:
        key = get_fb_key(fb)
        if key not in seen:
            seen.add(key)
            feedbacks.append(fb)
            
    # Sort feedbacks by timestamp descending
    try:
        feedbacks.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception:
        pass
        
    # Read payment logs
    kv_payments = get_kv_data("kannada_rag_payments", [])
    tmp_payments = []
    try:
        with open("/tmp/payments.json", "r", encoding="utf-8") as f:
            tmp_payments = json.load(f)
    except Exception:
        pass
    seen_pay = set()
    payments = []
    for p in (kv_payments if isinstance(kv_payments, list) else []) + tmp_payments:
        key = (p.get("timestamp", ""), p.get("payer_name", ""), p.get("amount", ""))
        if key not in seen_pay:
            seen_pay.add(key)
            payments.append(p)
    payments.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    total_payments = len(payments)
    
    # Compute total payments amount
    total_amount = 0.0
    for p in payments:
        amt_str = p.get("amount", "0").replace("₹", "").replace(",", "").strip()
        try:
            total_amount += float(amt_str)
        except Exception:
            pass

    # Read download logs
    logs = get_download_logs()
    
    # Calculate stats
    total_fb = len(feedbacks)
    avg_rating = sum(fb.get("rating", 0) for fb in feedbacks) / total_fb if total_fb > 0 else 0
    total_reads = sum(1 for l in logs if "Read" in l.get("type", ""))
    total_downloads = sum(1 for l in logs if "Download" in l.get("type", ""))
    total_logs = len(logs)

    # Calculate star rating frequency
    star_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for fb in feedbacks:
        r = fb.get("rating", 0)
        if r in star_counts:
            star_counts[r] += 1
            
    rating_rows = ""
    for star in [5, 4, 3, 2, 1]:
        count = star_counts[star]
        pct = (count / total_fb * 100) if total_fb > 0 else 0
        rating_rows += f"""
        <div style="display: flex; align-items: center; gap: 10px; font-size: 0.88rem; margin-bottom: 6px;">
            <span style="width: 32px; font-weight: bold; color: var(--primary);">{star} ★</span>
            <div style="flex-grow: 1; height: 8px; background: rgba(0,0,0,0.05); border-radius: 4px; overflow: hidden;">
                <div style="height: 100%; width: {pct}%; background: linear-gradient(90deg, var(--primary), #fb923c); border-radius: 4px;"></div>
            </div>
            <span style="width: 25px; text-align: right; color: var(--text-muted); font-weight: 600;">{count}</span>
        </div>
        """
        
    feedbacks_json = json.dumps(feedbacks, ensure_ascii=False)
    payments_json = json.dumps(payments, ensure_ascii=False)
    
    # Map IP and UID addresses to names from feedback
    ip_to_name = {}
    uid_to_name = {}
    for fb in feedbacks:
        fb_ip = fb.get("ip")
        fb_uid = fb.get("uid")
        fb_name = fb.get("name")
        if fb_name:
            if fb_ip:
                ip_to_name[fb_ip] = fb_name
            if fb_uid and fb_uid != "Unknown":
                uid_to_name[fb_uid] = fb_name
            
    feedback_rows = ""
    for fb in feedbacks:
        stars = "★" * fb.get("rating", 0) + "☆" * (5 - fb.get("rating", 0))
        feedback_rows += f"""
        <div class="fb-card">
            <div class="fb-header">
                <span class="fb-name">{fb.get('name', 'Anonymous')}</span>
                <span class="fb-stars">{stars}</span>
            </div>
            <div class="fb-time">{fb.get('timestamp', '')}</div>
            <div class="fb-comment">{fb.get('comment', '')}</div>
        </div>
        """
        
    if not feedbacks:
        feedback_rows = "<div class='no-data'>No feedback submitted yet.</div>"
        
    log_rows = ""
    user_activities = {}
    for l in logs:
        badge_class = "badge-download" if "Download" in l.get("type", "") else "badge-read"
        
        # Look up linked name
        log_ip = l.get("ip", "Unknown")
        log_uid = l.get("uid", "Unknown")
        log_uname = l.get("uname", "")
        
        resolved_name = "Anonymous"
        if log_uid and log_uid in uid_to_name:
            resolved_name = uid_to_name[log_uid]
        elif log_ip and log_ip in ip_to_name:
            resolved_name = ip_to_name[log_ip]
        elif log_uname:
            resolved_name = log_uname
            
        if resolved_name != "Anonymous":
            resolved_name_display = f"{resolved_name} (via Feedback)" if (log_uid in uid_to_name or log_ip in ip_to_name) else resolved_name
        else:
            resolved_name_display = "Anonymous"
            
        resolved_location = l.get("location", "Unknown Location")
        
        log_rows += f"""
        <tr>
            <td>{l.get('timestamp', '')}</td>
            <td><span class="{badge_class}">{l.get('type', 'Online Read')}</span></td>
            <td><strong>{l.get('edition', '').upper()}</strong></td>
            <td><span style="font-weight: 600; color: var(--primary);">{resolved_name_display}</span></td>
            <td>{resolved_location}</td>
            <td><code>{log_ip}</code></td>
            <td style="font-size:0.8rem; color:var(--text-muted); max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="{l.get('user_agent', '')}">{l.get('user_agent', 'Unknown')}</td>
        </tr>
        """
        
        # Group under user activities
        if log_uid == "Unknown":
            key = f"ip_{log_ip}"
            display_id = f"IP: {log_ip}"
        else:
            key = f"uid_{log_uid}"
            display_id = f"UID: {log_uid}"
            
        if key not in user_activities:
            user_activities[key] = {
                "name": resolved_name,
                "display_id": display_id,
                "reads": 0,
                "downloads": 0,
                "locations": set(),
                "last_active": "",
                "details": []
            }
            
        is_download = "Download" in l.get("type", "")
        if is_download:
            user_activities[key]["downloads"] += 1
        else:
            user_activities[key]["reads"] += 1
            
        if resolved_location and resolved_location != "Unknown Location":
            user_activities[key]["locations"].add(resolved_location)
            
        ts = l.get("timestamp", "")
        if ts > user_activities[key]["last_active"]:
            user_activities[key]["last_active"] = ts
            
        edition = l.get("edition", "").upper()
        action_type = "Download" if is_download else "Read"
        user_activities[key]["details"].append(f"{edition} ({action_type})")
        
    user_rows = ""
    sorted_users = sorted(user_activities.items(), key=lambda x: x[1]["last_active"], reverse=True)
    for key, info in sorted_users:
        locs = ", ".join(info["locations"]) if info["locations"] else "Unknown Location"
        history = ", ".join(info["details"][:10])
        if len(info["details"]) > 10:
            history += f" (+{len(info['details']) - 10} more)"
            
        name_style = "font-weight: 600; color: var(--primary);" if info["name"] != "Anonymous" else "color: var(--text-muted);"
        
        user_rows += f"""
        <tr>
            <td><span style="{name_style}">{info['name']}</span></td>
            <td><code>{info['display_id']}</code></td>
            <td><strong>{info['reads']}</strong></td>
            <td><strong>{info['downloads']}</strong></td>
            <td style="font-size:0.85rem;">{locs}</td>
            <td>{info['last_active']}</td>
            <td style="font-size:0.8rem; color:var(--text-muted);" title="{history}">{history}</td>
        </tr>
        """
        
    if not user_activities:
        users_html = "<div class='no-data'>No active users tracked yet.</div>"
    else:
        users_html = f"""
        <table>
            <thead>
                <tr>
                    <th>User / Name</th>
                    <th>Identifier</th>
                    <th>Reads</th>
                    <th>Downloads</th>
                    <th>Location(s)</th>
                    <th>Last Active</th>
                    <th>Action History</th>
                </tr>
            </thead>
            <tbody>
                {user_rows}
            </tbody>
        </table>
        """
        
    if not logs:
        logs_html = "<div class='no-data'>No access logs found.</div>"
    else:
        logs_html = f"""
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Action</th>
                    <th>Edition</th>
                    <th>User / Name</th>
                    <th>Location</th>
                    <th>IP Address</th>
                    <th>User-Agent</th>
                </tr>
            </thead>
            <tbody>
                {log_rows}
            </tbody>
        </table>
        """

    # Build payments HTML table
    if not payments:
        payments_html = "<div class='no-data'>No payment acknowledgments yet.</div>"
    else:
        pay_rows = ""
        for p in payments:
            pay_rows += f"""
            <tr>
                <td>{p.get('timestamp', '')}</td>
                <td><strong style="color:#16a34a;">{p.get('payer_name', 'Anonymous')}</strong></td>
                <td><strong style="font-size:1.1rem;">&#8377;{p.get('amount', '—')}</strong></td>
                <td><code style="font-size:0.8rem;">{p.get('utr_ref', 'Not provided')}</code></td>
                <td><code style="font-size:0.75rem;">{p.get('ip', 'Unknown')}</code></td>
                <td style="font-size:0.8rem;color:var(--text-muted);">{p.get('uid', 'Unknown')}</td>
            </tr>
            """
        payments_html = f"""
        <table>
            <thead><tr>
                <th>Date &amp; Time</th><th>Payer Name</th><th>Amount</th>
                <th>UPI Ref / UTR</th><th>IP Address</th><th>Session UID</th>
            </tr></thead>
            <tbody>{pay_rows}</tbody>
        </table>
        """

    admin_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Heli Hogu Kaarana — Admin Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            :root {{
                --primary: #c2410c;
                --primary-light: rgba(194, 65, 12, 0.08);
                --bg-main: #fffcf8;
                --bg-card: #ffffff;
                --text-main: #0f172a;
                --text-muted: #64748b;
                --border: rgba(194, 65, 12, 0.15);
            }}
            body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--bg-main); color: var(--text-main); margin: 0; padding: 2rem 1rem; }}
            .container {{ max-width: 1000px; margin: 0 auto; }}
            h1 {{ font-family: Georgia, serif; color: var(--primary); margin-bottom: 0.5rem; }}
            .subtitle {{ color: var(--text-muted); margin-bottom: 2rem; }}
            
            /* Stats Grid Layout */
            .stats-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; margin-bottom: 2.2rem; }}
            .stats-subgrid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }}
            
            .stat-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.2rem; text-align: center; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.02); display: flex; flex-direction: column; justify-content: center; }}
            .stat-val {{ font-size: 2.2rem; font-weight: 800; color: var(--primary); margin-bottom: 0.25rem; }}
            .stat-label {{ font-size: 0.82rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
            
            /* Tabs */
            .tabs {{ display: flex; gap: 8px; border-bottom: 2px solid var(--border); margin-bottom: 1.5rem; flex-wrap: wrap; }}
            .tab-btn {{ padding: 10px 20px; border: none; background: none; font-size: 0.95rem; font-weight: 700; color: var(--text-muted); cursor: pointer; border-bottom: 3px solid transparent; transition: all 0.2s; }}
            .tab-btn:hover {{ color: var(--primary); }}
            .tab-btn.active {{ color: var(--primary); border-bottom-color: var(--primary); }}
            .tab-content {{ display: none; }}
            .tab-content.active {{ display: block; }}
            
            /* Lists & Tables */
            .fb-card {{ background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.02); }}
            .fb-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem; }}
            .fb-name {{ font-weight: bold; font-size: 1.1rem; }}
            .fb-stars {{ color: #fb923c; font-size: 1.1rem; letter-spacing: 2px; }}
            .fb-time {{ font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.75rem; }}
            .fb-comment {{ line-height: 1.5; color: #334155; }}
            
            table {{ width: 100%; border-collapse: collapse; background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.02); margin-bottom: 2rem; }}
            th, td {{ padding: 12px 16px; text-align: left; border-bottom: 1px solid rgba(0,0,0,0.05); }}
            th {{ background: var(--primary-light); color: var(--primary); font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; }}
            tr:hover {{ background: rgba(0,0,0,0.01); }}
            .badge-read {{ background: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; }}
            .badge-download {{ background: #eff6ff; color: #1d4ed8; padding: 2px 8px; border-radius: 9999px; font-size: 0.75rem; font-weight: 700; }}
            
            .no-data {{ text-align: center; color: var(--text-muted); padding: 3rem; }}
            @media (max-width: 600px) {{
                .stats-container {{ grid-template-columns: 1fr; }}
            }}
        </style>
        <script>
            function showTab(btnEl, tabId) {{
                document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                btnEl.classList.add('active');
            }}
            
            const feedbacksData = {feedbacks_json};
            const paymentsData = {payments_json};
            
            function exportJSON(type) {{
                const data = type === 'feedback' ? feedbacksData : paymentsData;
                const jsonStr = JSON.stringify(data, null, 2);
                const blob = new Blob([jsonStr], {{ type: 'application/json' }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `kannada_rag_${{type}}_export_${{Date.now()}}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }}
            
            function filterTable() {{
                const query = document.getElementById('admin-search').value.toLowerCase();
                
                // Filter feedbacks
                const fbCards = document.querySelectorAll('.fb-card');
                fbCards.forEach(card => {{
                    const text = card.innerText.toLowerCase();
                    card.style.display = text.includes(query) ? '' : 'none';
                }});
                
                // Filter user activity table, log table, and payments table rows
                const rows = document.querySelectorAll('table tbody tr');
                rows.forEach(row => {{
                    const text = row.innerText.toLowerCase();
                    row.style.display = text.includes(query) ? '' : 'none';
                }});
            }}
            
            function clearSearch() {{
                document.getElementById('admin-search').value = '';
                filterTable();
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>📚 Admin Dashboard</h1>
            <p class="subtitle">Bilingual RAG Assistant feedback, e-book usage metrics, and logs.</p>
            
            <!-- Stats Grid & Ratings Distribution Chart Layout -->
            <div class="stats-container">
                <!-- Grid Stats (Left) -->
                <div class="stats-subgrid">
                    <div class="stat-card">
                        <div class="stat-val">{total_fb}</div>
                        <div class="stat-label">Feedbacks</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-val">{avg_rating:.1f} ★</div>
                        <div class="stat-label">Avg Rating</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-val">{total_reads}</div>
                        <div class="stat-label">Online Reads</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-val">{total_downloads}</div>
                        <div class="stat-label">Downloads</div>
                    </div>
                    <div class="stat-card" style="border-color:#16a34a33; grid-column: span 2;">
                        <div class="stat-val" style="color:#16a34a;">{total_payments} (&#8377;{total_amount:,.2f})</div>
                        <div class="stat-label">💰 Total Payments</div>
                    </div>
                </div>
                
                <!-- Ratings Distribution (Right) -->
                <div class="stat-card" style="text-align: left; padding: 1.5rem 1.8rem; display: flex; flex-direction: column; justify-content: flex-start;">
                    <h3 style="margin-top: 0; margin-bottom: 1rem; color: var(--primary); font-size: 1.05rem; text-transform: uppercase; letter-spacing: 0.5px;">⭐ Rating Distribution</h3>
                    {rating_rows}
                </div>
            </div>

            <!-- Search / Filter Bar -->
            <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 0.8rem 1.2rem; margin-bottom: 1.8rem; display: flex; gap: 12px; align-items: center; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.02);">
                <span style="font-size: 1.2rem; color: var(--primary);">🔍</span>
                <input type="text" id="admin-search" oninput="filterTable()" placeholder="Search feedbacks, activities, logs, or payments..." style="flex-grow: 1; padding: 10px 14px; border: 1px solid var(--border); border-radius: 8px; outline: none; font-size: 0.95rem; background: var(--bg-main); color: var(--text-main); font-family: inherit; transition: border-color 0.2s;" onfocus="this.style.borderColor='var(--primary)'" onblur="this.style.borderColor='var(--border)'" />
                <button onclick="clearSearch()" style="background: var(--primary-light); color: var(--primary); border: 1px solid rgba(194, 65, 12, 0.15); padding: 10px 18px; border-radius: 8px; font-weight: 700; cursor: pointer; transition: all 0.2s; font-size: 0.9rem;">Clear</button>
            </div>
            
            <!-- Navigation Tabs -->
            <div class="tabs">
                <button class="tab-btn active" onclick="showTab(this, 'tab-feedback')">Feedbacks ({total_fb})</button>
                <button class="tab-btn" onclick="showTab(this, 'tab-users')">User Activity ({len(user_activities)})</button>
                <button class="tab-btn" onclick="showTab(this, 'tab-logs')">Read & Download ({total_logs})</button>
                <button class="tab-btn" onclick="showTab(this, 'tab-payments')" style="color:#16a34a;">💰 Payments ({total_payments})</button>
            </div>
            
            <!-- Feedback Tab -->
            <div id="tab-feedback" class="tab-content active">
                <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
                    <button onclick="exportJSON('feedback')" style="background: var(--primary); color: white; border: none; padding: 8px 16px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 0.8rem; box-shadow: 0 4px 10px rgba(194,65,12,0.15); transition: all 0.2s; outline: none;">📥 Export Feedbacks JSON</button>
                </div>
                <div class="fb-list">
                    {feedback_rows}
                </div>
            </div>
            
            <!-- User Activity Tab -->
            <div id="tab-users" class="tab-content">
                {users_html}
            </div>
            
            <!-- Logs Tab -->
            <div id="tab-logs" class="tab-content">
                {logs_html}
            </div>

            <!-- Payments Tab -->
            <div id="tab-payments" class="tab-content">
                <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
                    <button onclick="exportJSON('payments')" style="background: var(--primary); color: white; border: none; padding: 8px 16px; border-radius: 8px; font-weight: bold; cursor: pointer; font-size: 0.8rem; box-shadow: 0 4px 10px rgba(194,65,12,0.15); transition: all 0.2s; outline: none;">📥 Export Payments JSON</button>
                </div>
                {payments_html}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=admin_html)

@app.get("/admin/feedback")
async def admin_feedback_redirect(password: Optional[str] = None):
    from fastapi.responses import RedirectResponse
    url = "/admin"
    if password:
        url += f"?password={password}"
    return RedirectResponse(url=url)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    icon_b64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAC2klEQVR4nO2WzWtcVRjGf885d2YySaY6lmibSiG0xS8QUXDRnVBxVXAhSPeuXAru+y+o4MJF/wClq9KFIFTNSkHBryIUS6tFK2mCmWk+Zu4953GRyUczM0kUsih6uJzFfS/P7zznfc99j9Z7f3KYIxyq+v+A/wag2CvojDMSaDDviGEPZgU0dqHjAc7Up1EdMi6peqQ+IQLkRKxTa6AaBNynf38cYxzA1Fvc+kyLN33kOK0nac8xMUPVBai3WV/g3s/q3qF71+055s5R3n/Q4t6AVLlail+/p++vMQVF8JGTPn3eZ9/B6POL8cZVd26TMqv4+VfSsRcVAqF2EICJDTq/8c2HnmiHyUijcO5r+ZaufZDTClB8cYlHUAiE6CaeaGv+Ii+9TfsUqbfLxxDAgMilcikyOdkAKuqaTO4tYWhGZOWcJo9qfVHO5ApXILx7n4YysxGW0FbdKADO5KRQSNEBt57IbuSz73LslMoVQsQjEjAK4N0wgcFy3gimvqceTS+8lS5cZnVRS79TTOA8KsEjAUMwgTHeVhCJ1qwWfqB1wiSPF9gPAIYsDw7aJkGpdH2a7z721IxytZP8DwACFB0iikiADdkUdXVX4rcfceZc/Op9ShEamMEzNIaqaHMVRu53tJpQAqhnQiQIk2tRN+fj9XlHKKG3TG0KjXYwskwB4exn36R4jLRM5w6dX/VXh/4KFmspP97OJ07SmkUtP/Uqt78c1OhBHUis3OWZN/z06+REuUb3D//yKXIGZl/W6deYPk6tSQhWwfVPdiZpPwe5ojkjRS5fIAQABWpNcvbMc0gs/Mi9n6jWcQaUMyrcPEoqhxkadaswigDV2uYxAEWtLnDjCsCZ856cwWnTrymawI43+wC2gjtrzIQasQWQuuTyAS3ncRp7NBzjtIUCqHqUqxtuNsXHHN+DAYa3U2jr+6G/2pjxr3vy3urbBXtITX8b//BfWx5+wN+tZC4TtUtAXgAAAABJRU5ErkJggg=="
    return Response(content=base64.b64decode(icon_b64), media_type="image/x-icon")

@app.get("/robots.txt")
async def robots_txt():
    from fastapi.responses import PlainTextResponse
    content = """User-agent: *
Allow: /
Disallow: /admin
Disallow: /admin/feedback

Sitemap: https://heli-hogu-kaarana.vercel.app/sitemap.xml
"""
    return PlainTextResponse(content=content)

@app.get("/sitemap.xml")
async def sitemap_xml():
    from fastapi.responses import Response
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://heli-hogu-kaarana.vercel.app/</loc>
        <lastmod>2026-06-12</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>""".strip()
    return Response(content=content, media_type="application/xml")

@app.get("/", response_class=HTMLResponse)
async def root():
    # Load Google Analytics & Search Console from environment variables
    ga_id = os.getenv("GOOGLE_ANALYTICS_ID", "").strip()
    gsv_id = os.getenv("GOOGLE_SITE_VERIFICATION", "0_vVD90Xv95sFLOEhxmSuiopJFfZAPkp25ZSXSrseBk").strip()
    
    ga_script = f"""<!-- Google tag (gtag.js) -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={ga_id}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{ga_id}');
    </script>""" if ga_id else ""
    
    gsv_meta = f'<meta name="google-site-verification" content="{gsv_id}" />' if gsv_id else ""

    html_content = r"""    <!DOCTYPE html>
    <html lang="kn">
    <head>
        <!-- {{GOOGLE_SITE_VERIFICATION}} -->
        <!-- {{GOOGLE_ANALYTICS_SCRIPT}} -->
        
        <!-- Primary Meta Tags -->
        <meta name="title" content="ಹೇಳಿ ಹೋಗು ಕಾರಣ — Bilingual AI Book Guide" />
        <meta name="description" content="Read Ravi Belagere's classic Kannada novel 'Heli Hogu Kaarana' (ಹೇಳಿ ಹೋಗು ಕಾರಣ) online or download the E-Book/PDF for offline reading. Use our AI Guide for bilingual audio playbacks, D3 character maps, and deep novel analysis." />

        <!-- Open Graph / Facebook -->
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://heli-hogu-kaarana.vercel.app/" />
        <meta property="og:site_name" content="Heli Hogu Kaarana" />
        <meta property="og:title" content="ಹೇಳಿ ಹೋಗು ಕಾರಣ — Bilingual AI Book Guide" />
        <meta property="og:description" content="Read Ravi Belagere's classic Kannada novel 'Heli Hogu Kaarana' (ಹೇಳಿ ಹೋಗು ಕಾರಣ) online or download the E-Book/PDF for offline reading. Use our AI Guide for bilingual audio playbacks, D3 character maps, and deep novel analysis." />
        <meta property="og:image" content="https://raw.githubusercontent.com/Amruth011/kannada-rag-agent/main/banner.svg" />

        <!-- Google Site Name Structured Data -->
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "WebSite",
          "name": "Heli Hogu Kaarana",
          "alternateName": ["ಹೇಳಿ ಹೋಗು ಕಾರಣ", "Heli Hogu Kaarana AI"],
          "url": "https://heli-hogu-kaarana.vercel.app/"
        }
        </script>

        <!-- Google FAQ Page Structured Data (SEO & AI Search Optimization) -->
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          "mainEntity": [
            {
              "@type": "Question",
              "name": "Heli Hogu Kaarana PDF download free: Is it available?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Yes! You can read the full text of 'Heli Hogu Kaarana' (ಹೇಳಿ ಹೋಗು ಕಾರಣ) online or download the E-Book (HTML/offline edition) for free on our official AI Novel Guide website (https://heli-hogu-kaarana.vercel.app/). We support Kannada, English, and side-by-side Bilingual editions."
              }
            },
            {
              "@type": "Question",
              "name": "Where can I buy a physical copy of Heli Hogu Kaarana by Ravi Belagere online?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "You can purchase physical print copies of the novel 'Heli Hogu Kaarana' from online portals like Amazon, Flipkart, or local Kannada book dealers (e.g. Sapna Book House). Our website serves as an interactive AI-powered reading companion and bilingual audio guide."
              }
            },
            {
              "@type": "Question",
              "name": "How do I read Heli Hogu Kaarana online in Kannada and English?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Our AI Guide website features a dedicated E-Book section where you can read the novel online in original Kannada, translated English, or a side-by-side Bilingual layout. You can also listen to audio chapter playbacks in both languages."
              }
            },
            {
              "@type": "Question",
              "name": "Who is Himavanth (Himavant / ಹಿಮವಂತ) in Heli Hogu Kaarana?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Himavanth is the protagonist of Ravi Belagere's classic Kannada romance. He is known for his silent, deep love and ultimate sacrifice. Our AI Guide allows you to explore his detailed character map, visual connections, and ask specific questions about his motives."
              }
            }
          ]
        }
        </script>

        <!-- Twitter -->
        <meta property="twitter:card" content="summary_large_image" />
        <meta property="twitter:url" content="https://heli-hogu-kaarana.vercel.app/" />
        <meta property="twitter:title" content="ಹೇಳಿ ಹೋಗು ಕಾರಣ — Bilingual AI Book Guide" />
        <meta property="twitter:description" content="Read Ravi Belagere's classic Kannada novel 'Heli Hogu Kaarana' (ಹೇಳಿ ಹೋಗು ಕಾರಣ) online or download the E-Book/PDF for offline reading. Use our AI Guide for bilingual audio playbacks, D3 character maps, and deep novel analysis." />
        <meta property="twitter:image" content="https://raw.githubusercontent.com/Amruth011/kannada-rag-agent/main/banner.svg" />

        <title>ಹೇಳಿ ಹೋಗು ಕಾರಣ — Bilingual AI Book Guide</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="icon" type="image/x-icon" href="/favicon.ico">
        <link rel="shortcut icon" type="image/x-icon" href="/favicon.ico">
        <link rel="apple-touch-icon" href="/favicon.ico">
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
                --transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            /* DARK MODE VARIATIONS */
            body.dark-mode {
                --bg: #090d16;
                --bg-secondary: #0f172a;
                --card: #1e293b;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --border: rgba(249, 115, 22, 0.15);
                --shadow: 0 20px 50px -15px rgba(0, 0, 0, 0.5);
                --primary-light: rgba(249, 115, 22, 0.12);
                --accent-light: rgba(99, 102, 241, 0.15);
            }
            body.dark-mode .nav-header {
                background: rgba(15, 23, 42, 0.85);
            }
            body.dark-mode .logo-title {
                color: #f8fafc;
            }
            body.dark-mode .settings {
                background: #131d31;
                border-color: rgba(249, 115, 22, 0.1);
            }
            body.dark-mode #ans {
                background: #111a2e;
                border-color: rgba(249, 115, 22, 0.15);
            }
            body.dark-mode #media-player {
                background: #131d31;
                border-color: rgba(249, 115, 22, 0.12);
            }
            body.dark-mode .sug-btn {
                background: linear-gradient(145deg, #1e293b 0%, #131d31 100%);
                border-color: rgba(249, 115, 22, 0.12);
            }
            body.dark-mode .sug-btn:hover {
                background: var(--primary-light);
                border-color: var(--primary);
            }
            body.dark-mode input[type="text"] {
                background: #1e293b;
                border-color: rgba(249, 115, 22, 0.2);
            }
            body.dark-mode input[type="text"]:focus {
                border-color: var(--primary);
            }
            body.dark-mode .network-svg {
                background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
                border-color: rgba(249, 115, 22, 0.15);
            }
            body.dark-mode .node circle {
                fill: #1e293b;
            }
            body.dark-mode .node text {
                fill: #f8fafc;
            }
            body.dark-mode .char-card {
                background: #1e293b;
                border-color: rgba(249, 115, 22, 0.15);
            }
            body.dark-mode .feedback-card {
                background: #1e293b;
                border-color: rgba(249, 115, 22, 0.15);
            }
            body.dark-mode .download-box {
                background: #1e293b;
                border-color: rgba(249, 115, 22, 0.15);
            }
            body.dark-mode .nav-item:hover {
                background: rgba(249, 115, 22, 0.1);
            }
            body.dark-mode .hero h1 {
                background: linear-gradient(135deg, #ffedd5 30%, #f97316);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
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
                transition: background 0.3s, color 0.3s;
            }
            body.dark-mode {
                background: radial-gradient(circle at 50% 0%, #0f172a 0%, #090d16 100%);
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
                flex-wrap: wrap;
                gap: 0.3rem;
                align-items: center;
            }
            .nav-item {
                font-size: 0.72rem;
                font-weight: 700;
                color: var(--text-muted);
                cursor: pointer;
                letter-spacing: 0.3px;
                transition: all 0.25s;
                padding: 0.35rem 0.6rem;
                border-radius: 8px;
                border: none;
                background: none;
                font-family: inherit;
                white-space: nowrap;
                display: inline-flex;
                align-items: center;
                gap: 4px;
            }
            .nav-item:hover {
                color: var(--primary);
                background: rgba(194, 65, 12, 0.06);
            }
            .nav-item.active {
                color: #fff;
                background: var(--primary);
                border-radius: 20px;
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
            #text-res blockquote {
                border-left: 4px solid var(--primary);
                background: var(--primary-light);
                padding: 0.8rem 1.2rem;
                margin: 1.2rem 0;
                border-radius: 0 12px 12px 0;
                font-style: italic;
                color: var(--text);
                opacity: 0.95;
            }
            #text-res ul, #text-res ol {
                margin: 1rem 0;
                padding-left: 1.8rem;
            }
            #text-res li {
                margin-bottom: 0.5rem;
                line-height: 1.7;
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
            
            /* CUSTOM MEDIA PLAYER & VISUALIZER */
            .player-btn {
                transition: all 0.2s;
            }
            .player-btn:hover {
                transform: scale(1.1);
            }
            .player-btn:active {
                transform: scale(0.95);
            }
            
            .audio-visualizer {
                display: flex;
                align-items: center;
                gap: 3px;
                height: 24px;
                padding: 0 4px;
            }
            .audio-visualizer .bar {
                width: 3px;
                height: 4px;
                background: linear-gradient(180deg, var(--primary) 0%, #fb923c 100%);
                border-radius: 2px;
                transition: height 0.15s ease;
            }
            .audio-visualizer.playing .bar {
                animation: bounce-bar 0.8s ease-in-out infinite alternate;
            }
            .audio-visualizer.playing .bar:nth-child(1), .audio-visualizer.playing .bar:nth-child(15) { animation-delay: 0.1s; animation-duration: 0.5s; }
            .audio-visualizer.playing .bar:nth-child(2), .audio-visualizer.playing .bar:nth-child(14) { animation-delay: 0.25s; animation-duration: 0.75s; }
            .audio-visualizer.playing .bar:nth-child(3), .audio-visualizer.playing .bar:nth-child(13) { animation-delay: 0.15s; animation-duration: 0.6s; }
            .audio-visualizer.playing .bar:nth-child(4), .audio-visualizer.playing .bar:nth-child(12) { animation-delay: 0.3s; animation-duration: 0.85s; }
            .audio-visualizer.playing .bar:nth-child(5), .audio-visualizer.playing .bar:nth-child(11) { animation-delay: 0.05s; animation-duration: 0.55s; }
            .audio-visualizer.playing .bar:nth-child(6), .audio-visualizer.playing .bar:nth-child(10) { animation-delay: 0.2s; animation-duration: 0.7s; }
            .audio-visualizer.playing .bar:nth-child(7), .audio-visualizer.playing .bar:nth-child(9) { animation-delay: 0.35s; animation-duration: 0.8s; }
            .audio-visualizer.playing .bar:nth-child(8) { animation-delay: 0.12s; animation-duration: 0.95s; }

            @keyframes bounce-bar {
                0% { height: 4px; }
                100% { height: 24px; }
            }
            
            .fade-in { animation: fadeIn 0.8s forwards; }
            @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }

            /* DOWNLOAD SECTION STYLES */
            .download-box {
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .download-box:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 30px -10px rgba(194, 65, 12, 0.15);
                border-color: rgba(194, 65, 12, 0.35) !important;
            }
            .dl-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px -2px rgba(194, 65, 12, 0.2);
                filter: brightness(0.95);
            }

            /* TABS NAVIGATION */
            .tabs-nav {
                display: flex;
                border-bottom: 2px solid rgba(194, 65, 12, 0.08);
                margin-bottom: 2.2rem;
                gap: 0.2rem;
                padding-bottom: 0.5rem;
                justify-content: center;
            }
            .tab-btn {
                background: none;
                border: none;
                font-family: inherit;
                font-size: 0.78rem;
                font-weight: 700;
                color: var(--text-muted);
                border-bottom: 3px solid transparent;
                padding: 0.45rem 0.6rem;
                cursor: pointer;
                outline: none;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                white-space: nowrap;
                display: inline-flex;
                align-items: center;
                gap: 4px;
                border-radius: 8px 8px 0 0;
            }
            .tab-btn:hover {
                color: var(--primary);
                background: rgba(194, 65, 12, 0.02);
            }
            .tab-btn.active {
                color: var(--primary);
                border-bottom-color: var(--primary);
            }
            .tab-section {
                display: none;
            }
            .tab-section.active {
                display: block;
            }

            /* CHARACTER MAP */
            .map-container {
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
                align-items: center;
                margin-top: 1rem;
            }
            .network-svg {
                width: 100%;
                max-width: 550px;
                height: auto;
                background: linear-gradient(145deg, #ffffff 0%, #fffbf8 100%);
                border: 1px solid rgba(194, 65, 12, 0.1);
                border-radius: 20px;
                box-shadow: inset 0 4px 15px rgba(194, 65, 12, 0.01);
            }
            .node {
                cursor: pointer;
                transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .node circle {
                transition: r 0.3s, fill 0.3s, stroke 0.3s, stroke-width 0.3s;
            }
            .node:hover circle {
                r: 28;
                stroke-width: 3.5;
            }
            .node text {
                font-family: var(--font-sans);
                font-weight: 700;
                transition: font-size 0.3s, fill 0.3s;
                pointer-events: none;
            }
            .node:hover text {
                font-size: 13px;
                fill: var(--primary);
            }
            .edge {
                transition: stroke-width 0.3s, stroke 0.3s, opacity 0.3s;
            }
            .edge-label {
                font-family: var(--font-sans);
                font-weight: 600;
                pointer-events: none;
            }
            .char-card {
                background: #fbf9f6;
                border: 1px solid rgba(194, 65, 12, 0.12);
                border-left: 4px solid var(--primary);
                padding: 1.8rem;
                border-radius: 18px;
                width: 100%;
                box-sizing: border-box;
                text-align: left;
                transition: all 0.3s;
            }
            .char-card h3 {
                margin-top: 0;
                color: var(--primary);
                font-family: var(--font-serif);
                font-size: 1.4rem;
                margin-bottom: 0.5rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .char-card .badge {
                font-family: var(--font-sans);
                font-size: 0.75rem;
                font-weight: 700;
                background: var(--primary-light);
                color: var(--primary);
                padding: 4px 10px;
                border-radius: 99px;
            }
            .char-card .meta-title {
                font-size: 0.8rem;
                font-weight: 700;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
                margin-top: 1.2rem;
            }
            .char-card .desc {
                line-height: 1.6;
                color: var(--text);
                font-size: 0.95rem;
            }
            .char-tabs {
                display: flex;
                gap: 8px;
                margin-bottom: 1rem;
            }
            .char-tab-btn {
                background: white;
                border: 1px solid rgba(194, 65, 12, 0.15);
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 0.8rem;
                font-weight: 600;
                cursor: pointer;
                color: var(--text-muted);
            }
            .char-tab-btn.active {
                background: var(--primary);
                color: white;
                border-color: var(--primary);
            }

            /* QUOTE MAKER */
            .quote-creator-box {
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
                align-items: center;
                margin-top: 1rem;
            }
            .creator-controls {
                width: 100%;
                display: flex;
                flex-direction: column;
                gap: 1.2rem;
                text-align: left;
            }
            .control-group {
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            .control-group label {
                font-size: 0.8rem;
                font-weight: 700;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .control-group select, .control-group textarea {
                background: #ffffff;
                border: 1.5px solid rgba(194, 65, 12, 0.15);
                padding: 10px 12px;
                border-radius: 10px;
                font-family: inherit;
                font-size: 0.95rem;
                outline: none;
                box-sizing: border-box;
                color: var(--text);
                transition: border-color 0.2s;
            }
            .control-group select:focus, .control-group textarea:focus {
                border-color: var(--primary);
            }
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
                <nav class="nav-menu" id="top-nav-menu">
                    <button class="nav-item active" id="nav-chat" onclick="switchTab('chat')">💬 AI Guide</button>
                    <button class="nav-item" id="nav-charmap" onclick="switchTab('charmap')">🗺️ Characters</button>
                    <button class="nav-item" id="nav-quotemaker" onclick="switchTab('quotemaker')">🎨 Quotes</button>
                    <button class="nav-item" id="nav-downloads" onclick="switchTab('downloads')">📚 E-Books</button>
                    <button class="nav-item" id="nav-feedback" onclick="switchTab('feedback')">✍️ Feedback</button>
                    <button id="theme-toggle-btn" class="nav-item" onclick="toggleTheme()" aria-label="Toggle Theme" style="cursor: pointer; padding: 0.35rem 0.6rem; border-radius: 8px; font-size: 1.05rem;">🌓</button>
                </nav>
            </div>
        </header>

        <!-- HERO SECTION -->
        <div class="hero">
            <h1 class="fade-in">ಹೇಳಿ ಹೋಗು ಕಾರಣ</h1>
            <p class="fade-in" style="animation-delay: 0.1s">Your AI-powered guide through the literary world of Heli Hogu Kaarana. Ask anything about characters, themes, or the story.</p>
        </div>

        <!-- MAIN INTERACTION CONTAINER -->
        <div class="container fade-in" style="animation-delay: 0.2s">
            <div class="card">
                <!-- SECTION 1: AI CHAT GUIDE -->
                <div id="section-chat" class="tab-section active">
                    <!-- MEHRAB / ARCH SILHOUETTE -->
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
                        <button class="sug-btn" onclick="setQ('How is Ravi Belagere related to the book?')">Ravi's Role</button>
                    </div>

                    <input type="text" id="q" placeholder="What would you like to know?" required autoComplete="off">
                    <button id="btn" class="main-btn" onclick="ask()">Analyze the Book</button>
                    <div style="text-align: center; margin-top: 0.6rem;">
                        <button onclick="clearChatHistory()" style="background: none; border: none; color: var(--text-muted); font-size: 0.82rem; cursor: pointer; text-decoration: underline; display: none;" id="clear-history-btn">🗑️ Reset Conversation</button>
                    </div>
                    
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
                                <button id="copy-btn" class="voice-btn" onclick="copyAnswer()" style="background: rgba(194, 65, 12, 0.05); border: 1px solid rgba(194, 65, 12, 0.12); color: var(--primary);">
                                    <span>📋 Copy Text</span>
                                </button>
                                <div id="v-loading" style="display:none;"><div class="loader"></div></div>
                                
                                <!-- CUSTOM VOICE PLAYER WIDGET -->
                                <div id="media-player" style="display: none; align-items: center; gap: 12px; padding: 0.6rem 1rem; background: #faf6f0; border: 1px solid rgba(194, 65, 12, 0.1); border-radius: 14px; flex-grow: 1; min-width: 260px;">
                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <button id="play-pause-btn" class="player-btn" onclick="togglePlayPause()" style="background: var(--primary); border: none; width: 32px; height: 32px; border-radius: 50%; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; outline: none;">▶</button>
                                        <button class="player-btn" onclick="skipAudio(-5)" style="background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.85rem; font-weight: bold; outline: none; padding: 2px;">↩ 5s</button>
                                        <button class="player-btn" onclick="skipAudio(5)" style="background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.85rem; font-weight: bold; outline: none; padding: 2px;">5s ↪</button>
                                        
                                        <!-- PLAYBACK SPEED SELECTOR -->
                                        <select id="audio-speed" onchange="setPlaybackSpeed(this.value)" style="background: transparent; border: 1.5px solid rgba(194, 65, 12, 0.2); color: var(--primary); border-radius: 8px; padding: 4px 6px; font-size: 0.72rem; font-weight: 700; cursor: pointer; outline: none; font-family: inherit;">
                                            <option value="1.0">1.0x</option>
                                            <option value="1.25">1.25x</option>
                                            <option value="1.5">1.5x</option>
                                            <option value="2.0">2.0x</option>
                                        </select>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 8px; flex-grow: 1;">
                                        <span id="audio-current-time" style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">0:00</span>
                                        <input type="range" id="audio-slider" value="0" style="flex-grow: 1; height: 5px; border-radius: 3px; cursor: pointer; accent-color: var(--primary); outline: none;">
                                        <span id="audio-duration" style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">0:00</span>
                                    </div>
                                    
                                    <!-- DYNAMIC AUDIO WAVEFORM VISUALIZER (15 BARS) -->
                                    <div id="audio-visualizer" class="audio-visualizer">
                                        <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                        <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                        <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                        <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                        <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- FAQ ACCORDION COMPONENT (SEO & AI CRAWLER OPTIMIZED) -->
                    <div class="faq-accordion-section" style="margin-top: 4rem; border-top: 1px solid var(--border); padding-top: 3rem;">
                        <style>
                            .faq-badge {
                                display: inline-flex;
                                align-items: center;
                                background: var(--primary-light);
                                color: var(--primary);
                                border: 1px solid rgba(194, 65, 12, 0.2);
                                font-size: 0.75rem;
                                font-weight: 700;
                                letter-spacing: 1.5px;
                                text-transform: uppercase;
                                padding: 6px 16px;
                                border-radius: 50px;
                                margin-bottom: 16px;
                            }
                            .faq-container {
                                max-width: 800px;
                                margin: 0 auto;
                                display: flex;
                                flex-direction: column;
                                gap: 14px;
                            }
                            .faq-item {
                                background: rgba(194, 65, 12, 0.04);
                                border: 1.5px solid transparent;
                                border-radius: 16px;
                                padding: 20px 24px;
                                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                                text-align: left;
                            }
                            .faq-item[open] {
                                border-color: var(--primary);
                                background: var(--card);
                                box-shadow: 0 10px 30px rgba(194, 65, 12, 0.06);
                            }
                            .faq-question {
                                font-size: 1.05rem;
                                font-weight: 700;
                                color: var(--text);
                                cursor: pointer;
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                outline: none;
                                list-style: none;
                                user-select: none;
                            }
                            .faq-question::-webkit-details-marker {
                                display: none;
                            }
                            .faq-question::after {
                                content: '+';
                                font-size: 1.4rem;
                                color: var(--text-muted);
                                font-weight: 500;
                                transition: transform 0.2s ease;
                            }
                            .faq-item[open] .faq-question::after {
                                content: '−';
                                color: var(--primary);
                                font-weight: 700;
                            }
                            .faq-answer {
                                margin-top: 14px;
                                font-size: 0.92rem;
                                color: var(--text-muted);
                                line-height: 1.6;
                                border-top: 1px solid rgba(194, 65, 12, 0.08);
                                padding-top: 14px;
                            }
                            .faq-answer strong {
                                color: var(--text);
                            }
                            .faq-contact-card {
                                background: rgba(194, 65, 12, 0.04);
                                border: 1px solid rgba(194, 65, 12, 0.08);
                                border-radius: 16px;
                                padding: 1.5rem 2rem;
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                flex-wrap: wrap;
                                gap: 1.5rem;
                                margin-top: 2rem;
                                text-align: left;
                            }
                            .faq-contact-btn {
                                background: transparent;
                                border: 1.5px solid var(--text);
                                color: var(--text) !important;
                                text-decoration: none;
                                padding: 10px 22px;
                                border-radius: 50px;
                                font-weight: 700;
                                font-size: 0.88rem;
                                display: inline-flex;
                                align-items: center;
                                transition: all 0.2s;
                            }
                            .faq-contact-btn:hover {
                                background: var(--text);
                                color: var(--card) !important;
                                transform: translateY(-1px);
                            }
                            @media (max-width: 768px) {
                                .faq-doodles, .faq-doodle-notepad {
                                    display: none !important;
                                }
                            }
                            @media (max-width: 576px) {
                                .faq-contact-card {
                                    flex-direction: column;
                                    text-align: center;
                                    align-items: center;
                                }
                            }
                        </style>

                        <div style="text-align: center; margin-bottom: 2.2rem; position: relative;">
                            <!-- Floating decorative outline icons matching screenshot -->
                            <svg class="faq-doodles" width="120" height="90" viewBox="0 0 120 90" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="position: absolute; right: 20px; top: -15px; color: var(--text-muted); opacity: 0.25; pointer-events: none;">
                                <!-- Question bubble ? -->
                                <path d="M40 50 C30 55, 20 45, 18 35 C15 22, 28 12, 40 15 C52 18, 58 32, 50 45 Z" />
                                <path d="M18 35 C15 38, 12 40, 10 40 C14 43, 16 46, 18 48" /> <!-- small tail -->
                                <path d="M30 25 C31 21, 36 20, 38 23 C39 25, 37 27, 35 29 C34 30, 34 32, 34 33" />
                                <circle cx="34" cy="37" r="1.2" fill="currentColor" />

                                <!-- Info bubble i -->
                                <path d="M85 35 C95 38, 108 30, 110 20 C112 10, 98 4, 88 5 C75 6, 68 18, 75 28 Z" />
                                <path d="M75 28 C74 32, 70 35, 68 38 C72 38, 74 37, 76 36" /> <!-- tail -->
                                <circle cx="92" cy="12" r="1.5" fill="currentColor" />
                                <path d="M92 16 L92 24 M90 16 L94 16 M90 24 L94 24" />
                            </svg>
                            
                            <div class="faq-badge">📖 FAQ / ಸಹಾಯ ಕೇಂದ್ರ</div>
                            <h2 style="font-family: var(--font-serif); color: var(--primary); margin-bottom: 0.5rem; font-size: 1.8rem; font-weight: 700;">Frequently Asked Questions</h2>
                            <p style="color: var(--text-muted); font-size: 0.95rem; max-width: 600px; margin: 0 auto; line-height: 1.45;">
                                Find answers to common questions about reading online, PDF downloads, and using the AI Guide.
                            </p>
                        </div>

                        <div class="faq-container">
                            <!-- Question 1 -->
                            <details class="faq-item">
                                <summary class="faq-question">Is the Heli Hogu Kaarana PDF download available for free?</summary>
                                <div class="faq-answer">
                                    <strong>Answer:</strong> Yes! You can read the entire novel online or download it as an offline E-Book for free. Click the <strong>E-Books</strong> tab in the navigation menu to access Kannada, English, or Bilingual (side-by-side) editions.
                                    <br><br>
                                    <span style="color: var(--primary); font-style: italic; font-size: 0.88rem;">ಹೌದು! ಕಾದಂಬರಿಯ ಕನ್ನಡ ಆವೃತ್ತಿ, ಇಂಗ್ಲಿಷ್ ಅನುವಾದ ಮತ್ತು ದ್ವಿಭಾಷಾ ಇ-ಪುಸ್ತಕಗಳನ್ನು ನೀವು ಆನ್‌ಲೈನ್‌ನಲ್ಲಿ ಓದಬಹುದು ಅಥವಾ ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿ ಓದಲು ಉಚಿತವಾಗಿ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿಕೊಳ್ಳಬಹುದು.</span>
                                </div>
                            </details>

                            <!-- Question 2 -->
                            <details class="faq-item">
                                <summary class="faq-question">Where can I buy a physical copy of Heli Hogu Kaarana online?</summary>
                                <div class="faq-answer">
                                    <strong>Answer:</strong> Physical paperback print copies of the novel can be purchased online from e-commerce portals like <strong>Amazon</strong> or <strong>Flipkart</strong>, or bought directly from local Kannada book dealers (e.g. Sapna Book House).
                                    <br><br>
                                    <span style="color: var(--primary); font-style: italic; font-size: 0.88rem;">ರವಿ ಬೆಳಗರೆ ಅವರ ಹೇಳಿ ಹೋಗು ಕಾರಣ ಮುದ್ರಿತ ಪುಸ್ತಕವನ್ನು ಖರೀದಿಸಲು ಬಯಸಿದರೆ, ಅಮೆಜಾನ್ ಅಥವಾ ಫ್ಲಿಪ್‌ಕಾರ್ಟ್ ಮತ್ತು ಸ್ಥಳೀಯ ಕನ್ನಡ ಪುಸ್ತಕದ ಅಂಗಡಿಗಳಲ್ಲಿ ಪತ್ತೆಹಚ್ಚಬಹುದು.</span>
                                </div>
                            </details>

                            <!-- Question 3 -->
                            <details class="faq-item">
                                <summary class="faq-question">How do I read Heli Hogu Kaarana online in Kannada & English?</summary>
                                <div class="faq-answer">
                                    <strong>Answer:</strong> This website acts as a digital reading companion. You can read the novel chapter-by-chapter under the <strong>E-Books</strong> tab. For a comparative reading experience, the Bilingual Edition displays the Kannada and English translations side-by-side.
                                    <br><br>
                                    <span style="color: var(--primary); font-style: italic; font-size: 0.88rem;">ಕನ್ನಡ ಮತ್ತು ಇಂಗ್ಲಿಷ್ ಭಾಷೆಗಳನ್ನು ಒಟ್ಟಿಗೆ ಓದಲು ದ್ವಿಭಾಷಾ ಆವೃತ್ತಿ ಅತ್ಯಂತ ಸೂಕ್ತವಾಗಿದೆ, ಇದು ಎರಡೂ ಭಾಷೆಗಳನ್ನು ಅಕ್ಕಪಕ್ಕದಲ್ಲಿ ಪ್ರದರ್ಶಿಸುತ್ತದೆ.</span>
                                </div>
                            </details>

                            <!-- Question 4 -->
                            <details class="faq-item">
                                <summary class="faq-question">Who is Himavanth (ಹಿಮವಂತ) in Heli Hogu Kaarana?</summary>
                                <div class="faq-answer">
                                    <strong>Answer:</strong> Himavanth is the protagonist of the novel, representing the pinnacle of silent, selfless love and sacrifice. If you want a deep analysis of his character arc and relationships, open the <strong>Characters</strong> tab to view our D3 relationship node map.
                                    <br><br>
                                    <span style="color: var(--primary); font-style: italic; font-size: 0.88rem;">ಹಿಮವಂತ ಕಾದಂಬರಿಯ ನಾಯಕನಾಗಿದ್ದು, ತನ್ನ ನಿಸ್ವಾರ್ಥ ಪ್ರೀತಿ ಮತ್ತು ತ್ಯಾಗಕ್ಕೆ ಹೆಸರಾಗಿದ್ದಾನೆ. ಅವನ ಕಥೆಯನ್ನು ಪಾತ್ರಗಳ ಲಿಂಕ್‌ನಲ್ಲಿ ವಿಶ್ಯುಯಲ್ ಮ್ಯಾಪ್ ಮೂಲಕ ನೋಡಬಹುದು.</span>
                                </div>
                            </details>

                            <!-- Contact Us Section matching screenshot -->
                            <div class="faq-contact-card">
                                <div style="display: flex; align-items: center; gap: 14px; text-align: left; flex: 1;">
                                    <!-- info icon -->
                                    <div style="width: 36px; height: 36px; border-radius: 50%; background: var(--primary-light); display: flex; align-items: center; justify-content: center; color: var(--primary); font-weight: 800; font-size: 1.1rem; flex-shrink: 0;">
                                        i
                                    </div>
                                    <div>
                                        <h4 style="font-family: var(--font-serif); font-size: 1.2rem; font-weight: 700; margin: 0; color: var(--text);">Still have a question?</h4>
                                        <p style="margin: 4px 0 0 0; font-size: 0.88rem; color: var(--text-muted); line-height: 1.4;">If you didn't find your answer, feel free to reach out to us.</p>
                                    </div>
                                </div>
                                <!-- Button and Doodle Container -->
                                <div style="display: flex; align-items: center; gap: 12px; flex-shrink: 0;">
                                    <!-- notepad/pen SVG doodle -->
                                    <svg class="faq-doodle-notepad" width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--text-muted); opacity: 0.8;">
                                        <!-- notepad -->
                                        <rect x="8" y="10" width="18" height="22" rx="3" />
                                        <!-- rings of notebook -->
                                        <path d="M12 7 L12 11 M16 7 L16 11 M20 7 L20 11 M24 7 L24 11" />
                                        <!-- lines -->
                                        <path d="M12 16 L22 16 M12 21 L22 21 M12 26 L18 26" />
                                        <!-- pen -->
                                        <path d="M30 12 L32 10 C33 9, 35 9, 36 10 C37 11, 37 13, 36 14 L30 20 L27 20 L27 17 Z" fill="rgba(194, 65, 12, 0.05)" />
                                    </svg>
                                    <a href="https://instagram.com/heli.hogu.kaarana" target="_blank" class="faq-contact-btn">
                                        Contact us
                                    </a>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SECTION 2: CHARACTER MAP -->
                <div id="section-charmap" class="tab-section">
                    <h2 style="font-family: var(--font-serif); color: var(--primary); text-align: center; margin-top: 1rem; margin-bottom: 0.5rem; font-size: 1.6rem; font-weight: 700;">🗺️ ಪಾತ್ರಗಳ ನಕ್ಷೆ / Character Relationship Map</h2>
                    <p style="text-align: center; color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem; line-height: 1.5;">
                        Click on character nodes to explore their background, key page references, and dynamic connections in the story.
                    </p>
                    <div class="map-container">
                        <!-- Responsive SVG Network Graph -->
                        <svg viewBox="0 0 500 360" class="network-svg">
                            <defs>
                                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                                    <feGaussianBlur stdDeviation="3" result="blur" />
                                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                </filter>
                            </defs>
                            <!-- Connection Lines (Edges) -->
                            <g stroke="#c2410c" stroke-linecap="round">
                                <!-- Himavant <-> Prarthana -->
                                <path d="M 250,180 L 120,110" stroke-width="2.5" fill="none" opacity="0.4" class="edge" id="edge-him-pra" />
                                <!-- Himavant <-> Debu -->
                                <path d="M 250,180 L 380,110" stroke-width="2.5" fill="none" opacity="0.4" class="edge" id="edge-him-deb" />
                                <!-- Prarthana <-> Debu -->
                                <path d="M 120,110 Q 250,80 380,110" stroke-width="1.5" stroke-dasharray="3,3" fill="none" opacity="0.3" class="edge" id="edge-pra-deb" />
                                <!-- Himavant <-> Rasool -->
                                <path d="M 250,180 L 110,240" stroke-width="2" fill="none" opacity="0.4" class="edge" id="edge-him-ras" />
                                <!-- Himavant <-> Urmila -->
                                <path d="M 250,180 L 390,240" stroke-width="2" fill="none" opacity="0.4" class="edge" id="edge-him-urm" />
                                <!-- Himavant <-> Ravi Belagere -->
                                <path d="M 250,180 L 250,60" stroke-width="2" fill="none" opacity="0.4" class="edge" id="edge-him-bel" />
                                <!-- Himavant <-> Kasuthi Kaveramma -->
                                <path d="M 250,180 L 250,300" stroke-width="2" fill="none" opacity="0.4" class="edge" id="edge-him-kav" />
                            </g>

                            <!-- Edge Labels -->
                            <g font-size="8" fill="var(--text-muted)" text-anchor="middle" class="edge-label">
                                <text x="185" y="135" transform="rotate(-28 185 135)">Love / ಪ್ರೇಮ</text>
                                <text x="315" y="135" transform="rotate(28 315 135)">Conflict / ಸಂಘರ್ಷ</text>
                                <text x="180" y="220" transform="rotate(23 180 220)">Loyalty / ನಿಷ್ಠೆ</text>
                                <text x="320" y="220" transform="rotate(-23 320 220)">Devotion / ಭಕ್ತಿ</text>
                                <text x="235" y="120" transform="rotate(90 235 120)">Narrator / ನಿರೂಪಕ</text>
                                <text x="265" y="240" transform="rotate(90 265 240)">Impact / ಪ್ರಭಾವ</text>
                            </g>

                            <!-- Character Nodes -->
                            <!-- Prarthana -->
                            <g class="node" onclick="clickChar('prarthana')" id="node-prarthana">
                                <circle cx="120" cy="110" r="22" fill="#fff" stroke="#ca8a04" stroke-width="2.5" filter="url(#glow)" />
                                <text x="120" y="114" font-size="10" text-anchor="middle" fill="#0f172a">ಪ್ರಾರ್ಥನಾ</text>
                            </g>
                            <!-- Debu -->
                            <g class="node" onclick="clickChar('debu')" id="node-debu">
                                <circle cx="380" cy="110" r="22" fill="#fff" stroke="#4338ca" stroke-width="2.5" filter="url(#glow)" />
                                <text x="380" y="114" font-size="10" text-anchor="middle" fill="#0f172a">ದೇಬು</text>
                            </g>
                            <!-- Rasool -->
                            <g class="node" onclick="clickChar('rasool')" id="node-rasool">
                                <circle cx="110" cy="240" r="22" fill="#fff" stroke="#475569" stroke-width="2" />
                                <text x="110" y="244" font-size="9" text-anchor="middle" fill="#0f172a">ರಸೂಲ್</text>
                            </g>
                            <!-- Urmila -->
                            <g class="node" onclick="clickChar('urmila')" id="node-urmila">
                                <circle cx="390" cy="240" r="22" fill="#fff" stroke="#9333ea" stroke-width="2" />
                                <text x="390" y="244" font-size="9" text-anchor="middle" fill="#0f172a">ಉರ್ಮಿಳಾ</text>
                            </g>
                            <!-- Ravi Belagere -->
                            <g class="node" onclick="clickChar('belagere')" id="node-belagere">
                                <circle cx="250" cy="60" r="22" fill="#fff" stroke="#dc2626" stroke-width="2" />
                                <text x="250" y="64" font-size="9" text-anchor="middle" fill="#0f172a">ಬೆಳಗರೆ</text>
                            </g>
                            <!-- Kasuthi Kaveramma -->
                            <g class="node" onclick="clickChar('kaveramma')" id="node-kaveramma">
                                <circle cx="250" cy="300" r="22" fill="#fff" stroke="#16a34a" stroke-width="2" />
                                <text x="250" y="304" font-size="9" text-anchor="middle" fill="#0f172a">ಕಾವೇರಮ್ಮ</text>
                            </g>
                            <!-- Himavant (Protagonist) -->
                            <g class="node" onclick="clickChar('himavant')" id="node-himavant">
                                <circle cx="250" cy="180" r="25" fill="#fff" stroke="#c2410c" stroke-width="3" filter="url(#glow)" />
                                <text x="250" y="184" font-size="11" font-weight="bold" text-anchor="middle" fill="#c2410c">ಹಿಮವಂತ</text>
                            </g>
                        </svg>

                        <!-- Character Biography Card -->
                        <div id="char-detail-card" class="char-card" style="display:none;">
                            <div class="char-tabs">
                                <button class="char-tab-btn active" id="btn-char-en" onclick="setCharLang('en')">English</button>
                                <button class="char-tab-btn" id="btn-char-kn" onclick="setCharLang('kn')">ಕನ್ನಡ</button>
                            </div>
                            <h3 id="char-name">Character Name <span class="badge" id="char-badge">Protagonist</span></h3>
                            <p id="char-desc" style="color: var(--text-muted); font-size: 0.92rem; line-height: 1.6;"></p>
                            <div style="margin-top: 0.8rem;">
                                <strong style="font-size: 0.85rem; color: var(--primary);">📖 Key Pages:</strong>
                                <span id="char-pages" style="font-size: 0.85rem; color: var(--text-muted);"></span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SECTION 3: QUOTE CREATOR -->
                <div id="section-quotemaker" class="tab-section">
                    <h2 style="font-family: var(--font-serif); color: var(--primary); text-align: center; margin-top: 1rem; margin-bottom: 0.5rem; font-size: 1.6rem; font-weight: 700;">🎨 ಕೋಟ್ ಕಾರ್ಡ್ ರಚಿಸಿ / Create Quote Card</h2>
                    <p style="text-align: center; color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem; line-height: 1.5;">
                        Design beautiful Instagram-ready quote cards from the novel's most powerful lines.
                    </p>
                    <div class="quote-creator-box">
                        <canvas id="quote-canvas" width="1080" height="1080" style="width: 100%; max-width: 380px; border-radius: 16px; border: 1px solid rgba(194, 65, 12, 0.15); display: block; margin: 0 auto; box-shadow: 0 10px 30px rgba(0,0,0,0.06);"></canvas>
                        
                        <div class="creator-controls">
                            <!-- Language Toggle -->
                            <div class="control-group">
                                <label>1. Choose Quote Language / ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ</label>
                                <div style="display: flex; gap: 8px; margin-top: 6px;">
                                    <button id="ql-btn-kn" class="char-tab-btn active" onclick="setQuoteLang('kn')" style="flex:1;">🇮🇳 ಕನ್ನಡ</button>
                                    <button id="ql-btn-en" class="char-tab-btn" onclick="setQuoteLang('en')" style="flex:1;">🇬🇧 English</button>
                                </div>
                            </div>

                            <div class="control-group">
                                <label>2. Aspect Ratio / ಅನುಪಾತ</label>
                                <select id="quote-ratio" onchange="drawQuoteCard()">
                                    <option value="1:1">1:1 (Square / ಚೌಕ)</option>
                                    <option value="4:5">4:5 (Instagram Portrait Feed / ಇನ್‌ಸ್ಟಾಗ್ರಾಮ್ ಫೀಡ್)</option>
                                    <option value="9:16">9:16 (Stories/Reels / ಸ್ಟೋರಿಗಳು)</option>
                                </select>
                            </div>

                            <div class="control-group">
                                <label>3. Pick a Famous Quote / ಕೋಟ್ ಆಯ್ಕೆ ಮಾಡಿ</label>
                                <!-- Kannada Quotes -->
                                <select id="quote-presets-kn" onchange="applyQuotePreset(this.value)">
                                    <option value="">-- Custom Quote / ನಿಮ್ಮದೇ ಆದ ವಾಕ್ಯ --</option>
                                    <option value="ಹೇಳಿ ಹೋಗು ಕಾರಣ... ಯಾಕೆಂದರೆ ನಿನಗಾಗಿ ಕಾಯುವ ಹೃದಯ ಇಲ್ಲಿದೆ.">ಹೇಳಿ ಹೋಗು ಕಾರಣ (ಮೂಲ ಥೀಮ್)</option>
                                    <option value="ಪ್ರೀತಿ ಎಂದರೆ ಕೇವಲ ಮುಖ ನೋಡುವುದಲ್ಲ, ಪರಸ್ಪರ ಮೌನವನ್ನು ಅರ್ಥ ಮಾಡಿಕೊಳ್ಳುವುದು.">ಪ್ರೀತಿ ಮತ್ತು ಮೌನ</option>
                                    <option value="ಜೀವನದಲ್ಲಿ ಕೆಲವೊಮ್ಮೆ ಉತ್ತರಗಳಿಗಿಂತ ಪ್ರಶ್ನೆಗಳೇ ಹೆಚ್ಚು ಸುಂದರವಾಗಿರುತ್ತವೆ.">ಸುಂದರ ಪ್ರಶ್ನೆಗಳು</option>
                                    <option value="ಮೌನಕ್ಕೂ ಒಂದು ಭಾಷೆಯಿದೆ, ಅದನ್ನ ಆಲಿಸಲು ಒಂದು ವಿಶೇಷವಾದ ಪ್ರೇಮ ಬೇಕು.">ಮೌನದ ಭಾಷೆ</option>
                                    <option value="ನಾವು ಪ್ರೀತಿಸುವವರ ಕೊರತೆಗಿಂತ, ನಮ್ಮನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುವವರ ಕೊರತೆಯೇ ಹೆಚ್ಚು ನೋವು ಕೊಡುತ್ತದೆ.">ಅರ್ಥ ಮಾಡಿಕೊಳ್ಳುವಿಕೆ</option>
                                    <option value="ನೆನಪುಗಳು ಕಳೆದುಹೋದ ನಂತರವೂ ಉಳಿಯುತ್ತವೆ, ಅದೇ ಪ್ರೇಮದ ಶಕ್ತಿ.">ನೆನಪಿನ ಶಕ್ತಿ</option>
                                    <option value="ಕಣ್ಣೀರು ಯಾವಾಗಲೂ ದೌರ್ಬಲ್ಯದ ಗುರುತಲ್ಲ, ಕೆಲವೊಮ್ಮೆ ಅದು ಧೈರ್ಯದ ಅಭಿವ್ಯಕ್ತಿ.">ಕಣ್ಣೀರು ಮತ್ತು ಧೈರ್ಯ</option>
                                    <option value="ದೂರವಿದ್ದರೂ ಹೃದಯ ಹತ್ತಿರದಲ್ಲಿಯೇ ಇರುತ್ತದೆ.">ದೂರ ಮತ್ತು ಹತ್ತಿರ</option>
                                    <option value="ಬದುಕು ಒಂದು ಸಂಗೀತ; ಕೆಲವೊಮ್ಮೆ ನೋವೇ ಅದರ ಅತ್ಯಂತ ಸುಂದರ ರಾಗ.">ಬದುಕಿನ ಸಂಗೀತ</option>
                                    <option value="ಹಿಮವಂತ ಮಾಡಿದ ತಪ್ಪುಗಳು ಅವನನ್ನು ನಾಶ ಮಾಡಲಿಲ್ಲ, ಅವನನ್ನು ರೂಪಿಸಿದವು.">ತಪ್ಪುಗಳು ರೂಪಿಸುತ್ತವೆ</option>
                                    <option value="ಪ್ರೀತಿಯಲ್ಲಿ ಸೋಲು ಇಲ್ಲ, ಇರುವುದು ಕೇವಲ ಪಾಠಗಳು.">ಪ್ರೀತಿಯ ಪಾಠ</option>
                                </select>
                                <!-- English Quotes -->
                                <select id="quote-presets-en" onchange="applyQuotePreset(this.value)" style="display:none;">
                                    <option value="">-- Custom Quote --</option>
                                    <option value="Tell me before you leave... because there's a heart here waiting for you.">Tell me before you leave... (Theme)</option>
                                    <option value="Love is not just seeing each other's face — it is understanding each other's silence.">Love &amp; Silence</option>
                                    <option value="Sometimes in life, questions are more beautiful than the answers.">Beautiful Questions</option>
                                    <option value="Even silence has a language — you need a very special kind of love to hear it.">Language of Silence</option>
                                    <option value="It hurts more to not be understood than to not be loved.">Being Understood</option>
                                    <option value="Memories outlast their moments. That is the power of love.">Power of Memory</option>
                                    <option value="Tears are not always a sign of weakness — sometimes they are the bravest thing you can feel.">Tears &amp; Courage</option>
                                    <option value="Even when you are far away, the heart stays close.">Distance &amp; Closeness</option>
                                    <option value="Life is music; sometimes pain is its most beautiful note.">Life's Music</option>
                                    <option value="Himavant's mistakes didn't destroy him — they defined him.">Defined by Mistakes</option>
                                    <option value="In love, there is no defeat — only lessons.">Lessons of Love</option>
                                    <option value="The saddest goodbyes are the ones that were never said.">Unsaid Goodbyes</option>
                                </select>
                            </div>
                            
                            <div class="control-group">
                                <label>4. Customize Quote Text / ವಾಕ್ಯವನ್ನು ಬದಲಿಸಿ</label>
                                <textarea id="quote-text" rows="3" oninput="drawQuoteCard()" placeholder="Type your custom quote here..."></textarea>
                            </div>
                            
                            <div class="control-group">
                                <label>5. Select Style Theme / ಶೈಲಿ ಆಯ್ಕೆ</label>
                                <select id="quote-style" onchange="drawQuoteCard()">
                                    <option value="saffron">Saffron Gold / ಕೇಸರಿ ಚಿನ್ನ</option>
                                    <option value="vintage">Terracotta Vintage / ವಿಂಟೇಜ್ ಮಣ್ಣು</option>
                                    <option value="midnight">Midnight Shadow / ಕತ್ತಲೆಯ ನೆರಳು</option>
                                    <option value="rose">Rose Blush / ಗುಲಾಬಿ ಬಣ್ಣ</option>
                                    <option value="forest">Forest Night / ಅರಣ್ಯದ ರಾತ್ರಿ</option>
                                </select>
                            </div>
                            
                            <button onclick="downloadQuoteCard()" class="main-btn" style="margin-top: 0.5rem; display: flex; align-items: center; justify-content: center; gap: 8px;">
                                <span>📥 Save Quote Card to Device</span>
                            </button>
                            <button onclick="shareQuoteCard()" class="main-btn" style="margin-top: 0.5rem; display: flex; align-items: center; justify-content: center; gap: 8px; background: linear-gradient(135deg, var(--accent), #4f46e5); box-shadow: 0 10px 25px -5px rgba(67, 56, 202, 0.25);">
                                <span>📤 Share Quote Card</span>
                            </button>
                        </div>
                    </div>
                </div>


                <!-- SECTION 4: E-BOOK DOWNLOADS -->
                <div id="section-downloads" class="tab-section">
                    <h2 style="font-family: var(--font-serif); color: var(--primary); text-align: center; margin-top: 1rem; margin-bottom: 0.5rem; font-size: 1.6rem; font-weight: 700;">📚 ಇ-ಪುಸ್ತಕಗಳನ್ನು ಓದಿ / Read E-Books Online</h2>
                    <p style="text-align: center; color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.8rem; line-height: 1.5;">
                        Read the novel directly in your browser with our new dark-themed Indic reading experience!
                    </p>
                    
                    <!-- Optional Profile Name Setup -->
                    <div style="max-width: 480px; margin: 0 auto 1.8rem auto; background: var(--bg-secondary); border: 1px dashed var(--primary); border-radius: 12px; padding: 1rem; display: flex; flex-direction: column; gap: 8px;">
                        <label for="user-custom-name" style="font-size: 0.8rem; font-weight: 700; color: var(--primary); text-transform: uppercase; letter-spacing: 0.5px; display: block; text-align: left; margin: 0;">👤 Personalize Downloads (Optional / ಐಚ್ಛಿಕ)</label>
                        <p style="font-size: 0.72rem; color: var(--text-muted); margin: 0; text-align: left; line-height: 1.35;">
                            Enter your name to personalize your offline ebooks and let the developers know you read it. If left blank, you will remain anonymous.
                        </p>
                        <div style="display: flex; gap: 8px; margin-top: 4px; position: relative;">
                            <input type="text" id="user-custom-name" placeholder="Enter your name" style="flex-grow: 1; padding: 8px 12px; border: 1px solid rgba(0,0,0,0.1); border-radius: 8px; font-family: inherit; font-size: 0.85rem; outline: none; background: white;" oninput="saveUserName(this.value)">
                            <span id="name-save-status" style="position: absolute; right: 12px; top: 50%; transform: translateY(-50%); font-size: 0.75rem; color: #10b981; font-weight: bold; display: none;">Saved!</span>
                        </div>
                    </div>

                    <div class="download-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.2rem;">
                        <!-- KANNADA EDITION -->
                        <div class="download-box" style="background: var(--bg-secondary); border: 1px solid rgba(194, 65, 12, 0.1); border-radius: 16px; padding: 1.5rem; display: flex; flex-direction: column; align-items: center; text-align: center;">
                            <h3 style="font-family: var(--font-serif); margin-top: 0; margin-bottom: 0.5rem; color: var(--primary); font-size: 1.25rem; font-weight: 700;">ಕನ್ನಡ ಆವೃತ್ತಿ<br><span style="font-size: 0.85rem; font-family: var(--font-sans); color: var(--text-muted); font-weight: 500;">Kannada Edition</span></h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1.2rem; flex-grow: 1; line-height: 1.4;">Original Kannada text of the novel, structured with chapter-by-chapter formatting.</p>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; width: 100%;">
                                <a href="/api/read/kannada" target="_blank" class="dl-btn" style="text-decoration: none; background: var(--primary); color: white; padding: 8px 14px; border-radius: 6px; font-size: 0.85rem; font-weight: 700; border: none; cursor: pointer; outline: none; display: flex; align-items: center; gap: 4px;">
                                    📖 Read Online
                                </a>
                                <a href="/api/read/kannada?download=true" download class="dl-btn" style="text-decoration: none; background: white; border: 1.5px solid var(--primary); color: var(--primary); padding: 7px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 700; cursor: pointer; outline: none; display: flex; align-items: center; gap: 4px;">
                                    📥 Read Offline
                                </a>
                            </div>
                        </div>

                        <!-- BILINGUAL EDITION -->
                        <div class="download-box" style="background: var(--bg-secondary); border: 2px solid var(--primary); border-radius: 16px; padding: 1.5rem; display: flex; flex-direction: column; align-items: center; text-align: center; position: relative;">
                            <div style="position: absolute; top: 0; right: 0; background: var(--primary); color: white; font-size: 0.6rem; font-weight: 800; padding: 4px 8px; border-bottom-left-radius: 6px; text-transform: uppercase;">Best</div>
                            <h3 style="font-family: var(--font-serif); margin-top: 0; margin-bottom: 0.5rem; color: var(--primary); font-size: 1.25rem; font-weight: 700;">ದ್ವಿಭಾಷಾ ಆವೃತ್ತಿ<br><span style="font-size: 0.85rem; font-family: var(--font-sans); color: var(--text-muted); font-weight: 500;">Bilingual Edition</span></h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1.2rem; flex-grow: 1; line-height: 1.4;">Side-by-side Kannada and English columns. Ideal for comparative reading.</p>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; width: 100%;">
                                <a href="/api/read/bilingual" target="_blank" class="dl-btn" style="text-decoration: none; background: var(--primary); color: white; padding: 8px 14px; border-radius: 6px; font-size: 0.85rem; font-weight: 700; border: none; cursor: pointer; outline: none; display: flex; align-items: center; gap: 4px;">
                                    📖 Read Online
                                </a>
                                <a href="/api/read/bilingual?download=true" download class="dl-btn" style="text-decoration: none; background: white; border: 1.5px solid var(--primary); color: var(--primary); padding: 7px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 700; cursor: pointer; outline: none; display: flex; align-items: center; gap: 4px;">
                                    📥 Read Offline
                                </a>
                            </div>
                        </div>

                        <!-- ENGLISH EDITION -->
                        <div class="download-box" style="background: var(--bg-secondary); border: 1px solid rgba(194, 65, 12, 0.1); border-radius: 16px; padding: 1.5rem; display: flex; flex-direction: column; align-items: center; text-align: center;">
                            <h3 style="font-family: var(--font-serif); margin-top: 0; margin-bottom: 0.5rem; color: var(--primary); font-size: 1.25rem; font-weight: 700;">ಇಂಗ್ಲಿಷ್ ಆವೃತ್ತಿ<br><span style="font-size: 0.85rem; font-family: var(--font-sans); color: var(--text-muted); font-weight: 500;">English Edition</span></h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1.2rem; flex-grow: 1; line-height: 1.4;">Complete English literary translation reflecting the author's intense story arc.</p>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; width: 100%;">
                                <a href="/api/read/english" target="_blank" class="dl-btn" style="text-decoration: none; background: var(--primary); color: white; padding: 8px 14px; border-radius: 6px; font-size: 0.85rem; font-weight: 700; border: none; cursor: pointer; outline: none; display: flex; align-items: center; gap: 4px;">
                                    📖 Read Online
                                </a>
                                <a href="/api/read/english?download=true" download class="dl-btn" style="text-decoration: none; background: white; border: 1.5px solid var(--primary); color: var(--primary); padding: 7px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 700; cursor: pointer; outline: none; display: flex; align-items: center; gap: 4px;">
                                    📥 Read Offline
                                </a>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- SECTION 5: FEEDBACK -->
                <div id="section-feedback" class="tab-section">
                    <h2 style="font-family: var(--font-serif); color: var(--primary); text-align: center; margin-top: 1rem; margin-bottom: 0.5rem; font-size: 1.6rem; font-weight: 700;">✍️ ನಿಮ್ಮ ಅನಿಸಿಕೆ ತಿಳಿಸಿ / Share Your Feedback</h2>
                    <p style="text-align: center; color: var(--text-muted); font-size: 0.9rem; margin-bottom: 2rem; max-width: 600px; margin-left: auto; margin-right: auto; line-height: 1.6;">
                        Have suggestions or feedback about this bilingual RAG assistant? Share your experience below!
                    </p>

                    <form id="feedback-form" onsubmit="submitFeedback(event)" style="max-width: 500px; margin: 0 auto; display: flex; flex-direction: column; gap: 1.2rem;">
                        <div style="text-align: left;">
                            <label for="fb-name" style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">Your Name / ನಿಮ್ಮ ಹೆಸರು</label>
                            <input type="text" id="fb-name" placeholder="Enter your name" required style="width: 100%; padding: 12px; border: 1px solid rgba(0,0,0,0.1); border-radius: 10px; font-family: inherit; font-size: 0.95rem; outline: none; box-sizing: border-box; background: var(--bg-secondary);">
                        </div>
                        
                        <div style="text-align: left;">
                            <label style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 8px; text-align: center;">Rating / ರೇಟಿಂಗ್</label>
                            <div class="star-rating" style="display: flex; gap: 8px; justify-content: center; font-size: 2.2rem; color: #cbd5e1; cursor: pointer;">
                                <span class="star" onclick="setRating(1)" onmouseover="highlightStars(1)" onmouseout="resetStars()" style="transition: color 0.15s;">★</span>
                                <span class="star" onclick="setRating(2)" onmouseover="highlightStars(2)" onmouseout="resetStars()" style="transition: color 0.15s;">★</span>
                                <span class="star" onclick="setRating(3)" onmouseover="highlightStars(3)" onmouseout="resetStars()" style="transition: color 0.15s;">★</span>
                                <span class="star" onclick="setRating(4)" onmouseover="highlightStars(4)" onmouseout="resetStars()" style="transition: color 0.15s;">★</span>
                                <span class="star" onclick="setRating(5)" onmouseover="highlightStars(5)" onmouseout="resetStars()" style="transition: color 0.15s;">★</span>
                            </div>
                            <input type="hidden" id="fb-rating" value="5">
                        </div>
                        
                        <div style="text-align: left;">
                            <label for="fb-comment" style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">Comment / ಅನಿಸಿಕೆ</label>
                            <textarea id="fb-comment" placeholder="Write your feedback here..." required style="width: 100%; height: 100px; padding: 12px; border: 1px solid rgba(0,0,0,0.1); border-radius: 10px; font-family: inherit; font-size: 0.95rem; outline: none; box-sizing: border-box; resize: vertical; background: var(--bg-secondary);"></textarea>
                        </div>
                        
                        <button type="submit" id="fb-submit-btn" style="width: 100%; background: var(--primary); color: white; padding: 12px; border: none; border-radius: 10px; font-size: 0.95rem; font-weight: 700; cursor: pointer; transition: all 0.2s; outline: none; box-shadow: 0 4px 12px rgba(194, 65, 12, 0.25);">Submit Feedback / ಅನಿಸಿಕೆ ಕಳುಹಿಸಿ</button>
                        <div id="fb-success-msg" style="color: #10b981; font-weight: 700; text-align: center; display: none; margin-top: 10px; font-size: 0.95rem;">✅ Thank you! Your feedback has been submitted. / ಧನ್ಯವಾದ!</div>
                    </form>
                </div>
        </div>

        <!-- FAQ SECTION MOVED TO AI GUIDE TAB -->
        
        <!-- FOOTER WITH CREDITS & SUPPORT -->
        <footer style="margin-top: 4rem; border-top: 1px solid var(--border); padding-top: 3rem; padding-bottom: 4rem; text-align: center; font-family: var(--font-sans); width: 100%;">
            <div style="max-width: 680px; margin: 0 auto; padding: 0 1.5rem; display: flex; flex-direction: column; gap: 2rem; align-items: center;">
                
                <!-- Support & Follow Hub Card -->
                <div class="footer-hub-card" style="background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 20px; padding: 1.8rem 2rem; width: 100%; box-sizing: border-box; text-align: left; display: flex; flex-direction: column; gap: 1.2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.02); transition: transform 0.25s;">
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <span style="font-size: 0.75rem; font-weight: 800; color: var(--primary); text-transform: uppercase; letter-spacing: 1.5px;">Support & Community</span>
                        <h4 style="font-family: var(--font-serif); font-size: 1.25rem; font-weight: 800; margin: 0; color: var(--text);">Loved the AI Book Guide? Here is how you can help:</h4>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1.2rem; width: 100%;">
                        <!-- Support block -->
                        <div style="display: flex; flex-direction: column; justify-content: space-between; gap: 1rem; padding: 1rem; background: var(--card); border: 1px solid var(--border); border-radius: 12px;">
                            <div>
                                <h5 style="margin: 0 0 6px 0; font-size: 0.95rem; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 6px;">☕ Keep the AI Online</h5>
                                <p style="margin: 0; font-size: 0.78rem; color: var(--text-muted); line-height: 1.45;">Contributions keep the AI voice & search servers active. Even ₹20 makes a big difference!</p>
                            </div>
                            <button onclick="document.getElementById('pay-modal').style.display='flex'" style="background: var(--primary); color: white; border: none; padding: 10px 18px; border-radius: 8px; font-size: 0.85rem; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(194, 65, 12, 0.2); outline: none;" onmouseover="this.style.transform='translateY(-1px)';this.style.boxShadow='0 6px 15px rgba(194, 65, 12, 0.3)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 12px rgba(194, 65, 12, 0.2)'">
                                ☕ Support Developer
                            </button>
                        </div>
                        
                        <!-- Follow block -->
                        <div style="display: flex; flex-direction: column; justify-content: space-between; gap: 1rem; padding: 1rem; background: var(--card); border: 1px solid var(--border); border-radius: 12px;">
                            <div>
                                <h5 style="margin: 0 0 6px 0; font-size: 0.95rem; font-weight: 700; color: var(--text); display: flex; align-items: center; gap: 6px;">📢 Join the Community</h5>
                                <p style="margin: 0; font-size: 0.78rem; color: var(--text-muted); line-height: 1.45;">Follow us on Instagram for regular quotes, character analysis, and updates on new book guides.</p>
                            </div>
                            <a href="https://instagram.com/heli.hogu.kaarana" target="_blank" style="text-decoration: none; background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); color: white; padding: 10px 18px; border-radius: 8px; font-size: 0.85rem; font-weight: 700; display: flex; align-items: center; justify-content: center; gap: 6px; width: 100%; box-sizing: border-box; transition: transform 0.2s, box-shadow 0.2s; box-shadow: 0 4px 12px rgba(220, 39, 67, 0.2);" onmouseover="this.style.transform='translateY(-1px)';this.style.boxShadow='0 6px 15px rgba(220, 39, 67, 0.3)'" onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 12px rgba(220, 39, 67, 0.2)'">
                                📸 Follow on Instagram
                            </a>
                        </div>
                    </div>
                </div>

                <!-- Credits line -->
                <p style="margin: 0; font-size: 0.82rem; line-height: 1.6; color: var(--text-muted);">
                    📚 <em>ಹೇಳಿ ಹೋಗು ಕಾರಣ</em> by <strong style="color:var(--text); font-weight:700;">Ravi Belagere</strong> · Published by <strong style="color:var(--text); font-weight:700;">Bhavana Prakashana</strong>, Bengaluru.<br>
                    All book rights belong to the original author &amp; publisher. This AI guide is an independent educational tribute.
                </p>

                <p style="margin: 0; font-size: 0.72rem; color: var(--text-muted);">© 2026 Heli Hogu Kaarana AI Guide · Built with ❤️ for Kannada literature</p>
            </div>
        </footer>

        <!-- PAYMENT MODAL -->
        <div id="pay-modal" style="display:none; position:fixed; inset:0; background:rgba(0,0,0,0.55); z-index:9999; align-items:center; justify-content:center; padding:1rem;" onclick="if(event.target===this)this.style.display='none'">
            <div style="background:var(--bg-card,#fffcf8); border-radius:20px; padding:2rem 1.5rem; max-width:380px; width:100%; box-shadow:0 20px 60px rgba(0,0,0,0.25); position:relative; text-align:center;">
                <button onclick="document.getElementById('pay-modal').style.display='none'" style="position:absolute; top:12px; right:14px; background:none; border:none; font-size:1.4rem; cursor:pointer; color:var(--text-muted);">✕</button>

                <p style="margin:0 0 0.3rem; font-family:var(--font-serif); font-size:1.15rem; font-weight:700; color:var(--primary);">☕ Support Development</p>
                <p style="margin:0 0 1rem; font-size:0.78rem; color:var(--text-muted); line-height:1.5;">This is completely optional. Any contribution helps keep the AI APIs running. Scan the QR below with any UPI app.</p>

                <!-- QR Code (encodes UPI, but ID not shown as text) -->
                <div style="background:white; border-radius:14px; padding:1rem; display:inline-block; box-shadow:0 4px 16px rgba(0,0,0,0.08); margin-bottom:1rem;">
                    <img src="data:image/png;base64,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" 
                         style="width:180px;height:180px;display:block;" alt="UPI QR Code" onerror="this.style.display='none';document.getElementById('qr-fallback').style.display='block'">
                    <div id="qr-fallback" style="display:none;width:180px;height:180px;background:#f1f5f9;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:0.75rem;color:#64748b;">QR code</div>
                </div>

                <!-- UPI deep-link button (opens any UPI app, doesn't expose ID as text) -->
                <a href="upi://pay?pa=amruthambu320@okaxis&pn=Amruth%20Ambu&tn=Heli%20Hogu%20Kaarana%20AI%20Support&cu=INR" style="display:block; background:var(--primary); color:white; text-decoration:none; padding:10px 20px; border-radius:10px; font-weight:700; font-size:0.9rem; margin-bottom:0.75rem;">⚡ Open UPI App to Pay</a>

                <!-- After-payment acknowledgment form -->
                <div id="pay-form-wrap" style="border-top:1px solid rgba(0,0,0,0.07); padding-top:0.9rem; margin-top:0.25rem;">
                    <p style="margin:0 0 0.6rem; font-size:0.78rem; color:var(--text-muted);">Paid? Let us know so we can thank you! 🙏</p>
                    <form id="pay-ack-form" onsubmit="submitPayment(event)" style="display:flex;flex-direction:column;gap:8px;">
                        <input type="text" id="pay-name" placeholder="Your name" required style="padding:7px 10px;border:1px solid rgba(0,0,0,0.12);border-radius:7px;font-family:inherit;font-size:0.82rem;outline:none;">
                        <input type="text" id="pay-amount" placeholder="Amount paid (e.g. ₹50)" required style="padding:7px 10px;border:1px solid rgba(0,0,0,0.12);border-radius:7px;font-family:inherit;font-size:0.82rem;outline:none;">
                        <input type="text" id="pay-utr" placeholder="UPI Ref / UTR No. (optional)" style="padding:7px 10px;border:1px solid rgba(0,0,0,0.12);border-radius:7px;font-family:inherit;font-size:0.82rem;outline:none;">
                        <button type="submit" id="pay-submit-btn" style="padding:8px;background:#16a34a;color:white;border:none;border-radius:8px;font-weight:700;cursor:pointer;font-size:0.85rem;">✅ Confirm Payment</button>
                        <p id="pay-success-msg" style="display:none;color:#16a34a;font-size:0.8rem;font-weight:700;">Thank you! Your support means a lot 🙏</p>
                    </form>
                </div>
            </div>
        </div>

        <script>
            async function submitPayment(e) {
                e.preventDefault();
                const btn = document.getElementById('pay-submit-btn');
                btn.disabled = true; btn.innerText = 'Sending...';
                const uid = localStorage.getItem('kannada_rag_uid') || 'Unknown';
                try {
                    const res = await fetch('/api/log-payment', {
                        method: 'POST',
                        headers: {'Content-Type':'application/json'},
                        body: JSON.stringify({
                            payer_name: document.getElementById('pay-name').value,
                            amount: document.getElementById('pay-amount').value,
                            utr_ref: document.getElementById('pay-utr').value,
                            uid: uid
                        })
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                        document.getElementById('pay-ack-form').style.display = 'none';
                        document.getElementById('pay-success-msg').style.display = 'block';
                    }
                } catch(err) {
                    alert('Network error, please try again.');
                } finally {
                    btn.disabled = false; btn.innerText = '✅ Confirm Payment';
                }
            }
        </script>

        <script>
            // --- TAB SWITCHER LOGIC ---
            function switchTab(tabId) {
                // Update top navbar active state
                const navItems = document.querySelectorAll('#top-nav-menu .nav-item');
                navItems.forEach(btn => btn.classList.remove('active'));
                const activeNav = document.getElementById('nav-' + tabId);
                if (activeNav) activeNav.classList.add('active');
                
                // Switch section visibility
                const sections = document.querySelectorAll('.tab-section');
                sections.forEach(sec => sec.classList.remove('active'));
                
                const targetSec = document.getElementById(`section-${tabId}`);
                if (targetSec) targetSec.classList.add('active');
                
                if (tabId === 'quotemaker') {
                    setTimeout(drawQuoteCard, 20);
                }
            }

            // --- CHARACTER MAP DATA & LOGIC ---
            const CHAR_DATA = {
                himavant: {
                    name_en: "Himavant",
                    name_kn: "ಹಿಮವಂತ",
                    badge_en: "Protagonist",
                    badge_kn: "ಕಥಾನಾಯಕ",
                    desc_en: "The simple, deeply loving, and innocent protagonist of Heli Hogu Kaarana. After losing his true love Prarthana, his life spirals into tragedy and emotional despair.",
                    desc_kn: "ಕಾದಂಬರಿಯ ಕಥಾನಾಯಕ. ಸರಳ, ಅತ್ಯಂತ ಪ್ರೀತಿಯುಳ್ಳ ಮತ್ತು ಮುಗ್ಧ ವ್ಯಕ್ತಿತ್ವ. ಪ್ರಾರ್ಥನಾಳನ್ನು ಕಳೆದುಕೊಂಡ ನಂತರ ಈತನ ಜೀವನವು ಭಾವನಾತ್ಮಕ ದುರಂತದ ಕಡೆಗೆ ಸಾಗುತ್ತದೆ.",
                    pages: "Major presence throughout the novel (e.g. Pages 1, 10, 45, 120, 240, 310)"
                },
                prarthana: {
                    name_en: "Prarthana",
                    name_kn: "ಪ್ರಾರ್ಥನಾ",
                    badge_en: "Female Lead",
                    badge_kn: "ನಾಯಕಿ",
                    desc_en: "The practical female lead who represents the intense struggle between secure social status, practical life choices, and genuine love for Himavant.",
                    desc_kn: "ಕಾದಂಬರಿಯ ನಾಯಕಿ. ವ್ಯವಹಾರಿಕ ಜಗತ್ತಿನ ಭದ್ರತೆ, ಸಾಮಾಜಿಕ ಗೌರವ ಮತ್ತು ಹಿಮವಂತನ ಮೇಲಿರುವ ನೈಜ ಪ್ರೀತಿಯ ನಡುವಿನ ತಳಮಳವನ್ನು ಪ್ರತಿನಿಧಿಸುವ ಪಾತ್ರ.",
                    pages: "Pages 5, 22, 54, 108, 195, 280, 340"
                },
                debu: {
                    name_en: "Debashish (Debu)",
                    name_kn: "ದೇಬು",
                    badge_en: "Husband / Catalyst",
                    badge_kn: "ಪತಿ / ಮಹತ್ವದ ತಿರುವು",
                    desc_en: "Debashish Bandopadhyaya (Debu) is a wealthy man who marries Prarthana, weaving his way into the love triangle and bringing intense conflict to the plot.",
                    desc_kn: "ಪ್ರಾರ್ಥನಾಳನ್ನು ಮದುವೆಯಾಗುವ ಶ್ರೀಮಂತ ವ್ಯಕ್ತಿ. ಪ್ರೇಮ ತ್ರಿಕೋನದಲ್ಲಿ ಭಾಗಿಯಾಗಿ ಕಥೆಗೆ ಪ್ರಮುಖ ತಿರುವು ಮತ್ತು ಸಂಘರ್ಷ ತರುವ ಪಾತ್ರ.",
                    pages: "Pages 55, 78, 122, 190, 260"
                },
                rasool: {
                    name_en: "Rasool",
                    name_kn: "ರಸೂಲ್",
                    badge_en: "Loyal Friend",
                    badge_kn: "ನಿಷ್ಠಾವಂತ ಗೆಳೆಯ",
                    desc_en: "Himavant's loyal and rugged friend who stays with him through his darkest times, representing true loyalty and companionship.",
                    desc_kn: "ಹಿಮವಂತನ ನಿಷ್ಠಾವಂತ ಒಡನಾಡಿ. ಕಷ್ಟದ ಸಮಯದಲ್ಲಿ ನೆರಳಾಗಿ ನಿಂತು ಸ್ನೇಹ ಮತ್ತು ನಿಷ್ಠೆಯನ್ನು ಎತ್ತಿಹಿಡಿಯುವ ಪಾತ್ರ.",
                    pages: "Pages 34, 78, 112, 160, 255"
                },
                urmila: {
                    name_en: "Urmila",
                    name_kn: "ಉರ್ಮಿಳಾ",
                    badge_en: "Devoted Companion",
                    badge_kn: "ನಿಷ್ಠಾವಂತ ಒಡನಾಡಿ",
                    desc_en: "A devoted, loyal, and supportive character who stands by Himavant through thick and thin, providing emotional stability.",
                    desc_kn: "ಹಿಮವಂತನಿಗೆ ಕಷ್ಟಸುಖಗಳಲ್ಲಿ ಜೊತೆಯಾಗಿ ನಿಲ್ಲುವ, ಪ್ರೀತಿ ಮತ್ತು ನಿಷ್ಠೆಯ ಮೂಲಕ ಕಥೆಯಲ್ಲಿ ಮಹತ್ವದ ಬೆಂಬಲ ನೀಡುವ ಸದ್ಗುಣಿ ಪಾತ್ರ.",
                    pages: "Pages 67, 110, 145, 230, 290"
                },
                belagere: {
                    name_en: "Ravi Belagere",
                    name_kn: "ರವಿ ಬೆಳಗೆರೆ",
                    badge_en: "Author / Narrator",
                    badge_kn: "ಲೇಖಕ / ನಿರೂಪಕ",
                    desc_en: "The author and narrator of Heli Hogu Kaarana. He weaves his distinct journalistic intensity and emotional voice into the backdrop of the entire story.",
                    desc_kn: "ಕಾದಂಬರಿಯ ಲೇಖಕರು ಮತ್ತು ನಿರೂಪಕರು. ಇಡೀ ಕಥೆಯ ಹೆಣಿಗೆಯಲ್ಲಿ ತಮ್ಮದೇ ಆದ ವಿಶಿಷ್ಟ ಮತ್ತು ಭಾವನಾತ್ಮಕ ನಿರೂಪಣಾ ಶೈಲಿಯನ್ನು ತಂದಿದ್ದಾರೆ.",
                    pages: "Narrates and comments throughout the entire novel"
                },
                kaveramma: {
                    name_en: "Kasuthi Kaveramma",
                    name_kn: "ಕಸೂತಿ ಕಾವೇರಮ್ಮ",
                    badge_en: "Notable Figure",
                    badge_kn: "ಪ್ರಮುಖ ಪಾತ್ರ",
                    desc_en: "An influential character who plays a key role in driving the narrative forward and affecting the lives of the main characters.",
                    desc_kn: "ಕಥಾಹಂದರದಲ್ಲಿ ಪ್ರಮುಖ ಪಾತ್ರ ವಹಿಸುವ, ಮುಖ್ಯ ಪಾತ್ರಗಳ ಜೀವನದ ಮೇಲೆ ಪ್ರಭಾವ ಬೀರುವ ವಿಶಿಷ್ಟ ವ್ಯಕ್ತಿತ್ವ.",
                    pages: "Pages 82, 115, 148, 202, 275"
                }
            };

            let activeCharId = "";
            let activeCharLang = "en";

            function clickChar(charId) {
                activeCharId = charId;
                
                // Highlight active node in SVG and dim others
                const nodes = document.querySelectorAll('.node');
                nodes.forEach(node => {
                    const circle = node.querySelector('circle');
                    const text = node.querySelector('text');
                    const nodeId = node.getAttribute('id');
                    
                    if (nodeId === `node-${charId}`) {
                        circle.style.r = "28";
                        circle.style.strokeWidth = "3.5";
                        circle.style.fill = "var(--primary-light)";
                        text.style.fontWeight = "bold";
                        text.style.fontSize = "13px";
                    } else {
                        circle.style.r = nodeId === 'node-himavant' ? '25' : '22';
                        circle.style.strokeWidth = nodeId === 'node-himavant' ? '3' : '2';
                        circle.style.fill = "#fff";
                        text.style.fontWeight = nodeId === 'node-himavant' ? 'bold' : 'normal';
                        text.style.fontSize = nodeId === 'node-himavant' ? '11px' : '10px';
                    }
                });

                // Highlight active connections in SVG
                const edges = document.querySelectorAll('.edge');
                edges.forEach(edge => {
                    const id = edge.getAttribute('id');
                    if (id.includes(charId.substring(0, 3))) {
                        edge.style.strokeWidth = "4";
                        edge.style.opacity = "0.9";
                    } else {
                        edge.style.strokeWidth = id.includes('pra-deb') ? '1.5' : '2.5';
                        edge.style.opacity = "0.4";
                    }
                });

                // Show details card
                document.getElementById('char-detail-card').style.display = 'block';
                document.getElementById('char-detail-card').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                
                renderCharCard();
            }

            function setCharLang(lang) {
                activeCharLang = lang;
                document.getElementById('btn-char-en').classList.toggle('active', lang === 'en');
                document.getElementById('btn-char-kn').classList.toggle('active', lang === 'kn');
                renderCharCard();
            }

            function renderCharCard() {
                if (!activeCharId) return;
                const char = CHAR_DATA[activeCharId];
                
                if (activeCharLang === 'en') {
                    document.getElementById('char-name').innerHTML = `${char.name_en} <span class="badge">${char.badge_en}</span>`;
                    document.getElementById('char-desc').innerText = char.desc_en;
                    document.getElementById('char-pages').innerText = char.pages;
                } else {
                    document.getElementById('char-name').innerHTML = `${char.name_kn} <span class="badge">${char.badge_kn}</span>`;
                    document.getElementById('char-desc').innerText = char.desc_kn;
                    document.getElementById('char-pages').innerText = char.pages;
                }
            }

            // --- INSTAGRAM QUOTE CREATOR LOGIC ---
            let activeQuoteLang = 'kn';

            function setQuoteLang(lang) {
                activeQuoteLang = lang;
                document.getElementById('ql-btn-kn').classList.toggle('active', lang === 'kn');
                document.getElementById('ql-btn-en').classList.toggle('active', lang === 'en');
                document.getElementById('quote-presets-kn').style.display = lang === 'kn' ? '' : 'none';
                document.getElementById('quote-presets-en').style.display = lang === 'en' ? '' : 'none';
                // Reset both selects
                document.getElementById('quote-presets-kn').value = '';
                document.getElementById('quote-presets-en').value = '';
            }

            function applyQuotePreset(quote) {
                if (!quote) return;
                document.getElementById('quote-text').value = quote;
                drawQuoteCard();
            }

            function getWrappedLines(ctx, text, maxWidth) {
                const words = text.split(' ');
                let line = '';
                let lines = [];
                for (let n = 0; n < words.length; n++) {
                    let testLine = line + words[n] + ' ';
                    let metrics = ctx.measureText(testLine);
                    let testWidth = metrics.width;
                    if (testWidth > maxWidth && n > 0) {
                        lines.push(line.trim());
                        line = words[n] + ' ';
                    } else {
                        line = testLine;
                    }
                }
                lines.push(line.trim());
                return lines;
            }

            function drawQuoteCard() {
                const canvas = document.getElementById('quote-canvas');
                if (!canvas) return;
                const ctx = canvas.getContext('2d');
                const quoteText = document.getElementById('quote-text').value.trim() || "ಹೇಳಿ ಹೋಗು ಕಾರಣ...";
                const style = document.getElementById('quote-style').value;
                const ratio = document.getElementById('quote-ratio') ? document.getElementById('quote-ratio').value : '1:1';
                
                let W = 1080;
                let H = 1080;
                if (ratio === '4:5') {
                    H = 1350;
                } else if (ratio === '9:16') {
                    H = 1920;
                }
                
                if (canvas.width !== W || canvas.height !== H) {
                    canvas.width = W;
                    canvas.height = H;
                }
                
                ctx.clearRect(0, 0, W, H);
                
                // Draw template background
                if (style === 'saffron') {
                    let grad = ctx.createLinearGradient(0, 0, W, H);
                    grad.addColorStop(0, '#c2410c');
                    grad.addColorStop(0.5, '#ea580c');
                    grad.addColorStop(1, '#ca8a04');
                    ctx.fillStyle = grad;
                    ctx.fillRect(0, 0, W, H);
                    
                    ctx.strokeStyle = 'rgba(254, 243, 199, 0.4)';
                    ctx.lineWidth = 27;
                    ctx.strokeRect(36, 36, W - 72, H - 72);
                    
                    ctx.strokeStyle = 'rgba(254, 243, 199, 0.2)';
                    ctx.lineWidth = 3.6;
                    ctx.strokeRect(63, 63, W - 126, H - 126);
                    
                    ctx.fillStyle = '#fef3c7';
                } else if (style === 'vintage') {
                    ctx.fillStyle = '#fffbeb';
                    ctx.fillRect(0, 0, W, H);
                    
                    ctx.strokeStyle = '#c2410c';
                    ctx.lineWidth = 22;
                    ctx.strokeRect(36, 36, W - 72, H - 72);
                    
                    ctx.fillStyle = '#c2410c';
                    let sq = 18;
                    ctx.fillRect(63, 63, sq, sq);
                    ctx.fillRect(W - 63 - sq, 63, sq, sq);
                    ctx.fillRect(63, H - 63 - sq, sq, sq);
                    ctx.fillRect(W - 63 - sq, H - 63 - sq, sq, sq);
                    
                    ctx.fillStyle = '#0f172a';
                } else if (style === 'rose') {
                    let grad = ctx.createLinearGradient(0, 0, W, H);
                    grad.addColorStop(0, '#fce7f3');
                    grad.addColorStop(1, '#fbcfe8');
                    ctx.fillStyle = grad;
                    ctx.fillRect(0, 0, W, H);
                    ctx.strokeStyle = '#db2777';
                    ctx.lineWidth = 14;
                    ctx.strokeRect(36, 36, W - 72, H - 72);
                    ctx.fillStyle = '#831843';
                } else if (style === 'forest') {
                    let grad = ctx.createLinearGradient(0, 0, 0, H);
                    grad.addColorStop(0, '#052e16');
                    grad.addColorStop(1, '#14532d');
                    ctx.fillStyle = grad;
                    ctx.fillRect(0, 0, W, H);
                    ctx.strokeStyle = '#4ade80';
                    ctx.lineWidth = 7.2;
                    ctx.strokeRect(36, 36, W - 72, H - 72);
                    ctx.fillStyle = '#dcfce7';
                } else {
                    ctx.fillStyle = '#0f172a';
                    ctx.fillRect(0, 0, W, H);
                    ctx.strokeStyle = '#ea580c';
                    ctx.lineWidth = 7.2;
                    ctx.strokeRect(45, 45, W - 90, H - 90);
                    ctx.fillStyle = '#f8fafc';
                }
                
                // Set font for quote text so we can measure it
                ctx.font = 'italic 45px Georgia, serif';
                const lines = getWrappedLines(ctx, quoteText, W - 220);
                const lineHeight = 68;
                const textHeight = lines.length * lineHeight;
                const cY = H / 2;
                const startY = cY - (textHeight / 2);
                
                // Draw Quote marks
                ctx.font = '160px Georgia, serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                if (style === 'saffron') {
                    ctx.fillStyle = 'rgba(254, 243, 199, 0.15)';
                } else if (style === 'vintage') {
                    ctx.fillStyle = 'rgba(194, 65, 12, 0.08)';
                } else {
                    ctx.fillStyle = 'rgba(234, 88, 12, 0.12)';
                }
                ctx.fillText('“', W / 2, startY - 60);
                
                // Draw Quote Content
                if (style === 'saffron') {
                    ctx.fillStyle = '#fffbeb';
                } else if (style === 'vintage') {
                    ctx.fillStyle = '#1e293b';
                } else {
                    ctx.fillStyle = '#f1f5f9';
                }
                
                ctx.font = 'italic 45px Georgia, serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'top';
                for (let k = 0; k < lines.length; k++) {
                    ctx.fillText(lines[k], W / 2, startY + (k * lineHeight));
                }
                
                // Draw Watermark
                ctx.textBaseline = 'middle';
                ctx.font = 'bold 28px "Plus Jakarta Sans", sans-serif';
                if (style === 'saffron') {
                    ctx.fillStyle = '#fef3c7';
                } else if (style === 'vintage') {
                    ctx.fillStyle = '#c2410c';
                } else {
                    ctx.fillStyle = '#ea580c';
                }
                ctx.fillText('— ಹೇಳಿ ಹೋಗು ಕಾರಣ / Heli Hogu Kaarana', W / 2, H - 140);
                
                ctx.font = '22px monospace';
                if (style === 'saffron') {
                    ctx.fillStyle = 'rgba(254, 243, 199, 0.7)';
                } else if (style === 'vintage') {
                    ctx.fillStyle = '#64748b';
                } else {
                    ctx.fillStyle = '#94a3b8';
                }
                ctx.fillText('Instagram: @heli.hogu.kaarana', W / 2, H - 80);
            }

            function downloadQuoteCard() {
                const canvas = document.getElementById('quote-canvas');
                const dataURL = canvas.toDataURL("image/png");
                const link = document.createElement('a');
                link.download = 'heli_hogu_karana_quote.png';
                link.href = dataURL;
                link.click();
            }

            async function shareQuoteCard() {
                const canvas = document.getElementById('quote-canvas');
                if (!canvas) return;
                try {
                    canvas.toBlob(async (blob) => {
                        if (!blob) {
                            alert("Failed to generate image.");
                            return;
                        }
                        const file = new File([blob], 'heli_hogu_karana_quote.png', { type: 'image/png' });
                        if (navigator.canShare && navigator.canShare({ files: [file] })) {
                            await navigator.share({
                                files: [file],
                                title: 'Heli Hogu Kaarana Novel Quote',
                                text: 'Designed this beautiful quote card from the Kannada novel "Heli Hogu Kaarana"!'
                            });
                        } else {
                            // Fallback if sharing is not supported
                            downloadQuoteCard();
                        }
                    }, 'image/png');
                } catch (err) {
                    console.error("Error sharing:", err);
                    downloadQuoteCard(); // Fallback
                }
            }

            // Star Rating Logic
            let currentRating = 5;
            
            function setRating(val) {
                currentRating = val;
                document.getElementById('fb-rating').value = val;
                renderStars(val);
            }
            
            function highlightStars(val) {
                renderStars(val);
            }
            
            function resetStars() {
                renderStars(currentRating);
            }
            
            function renderStars(val) {
                const stars = document.querySelectorAll('.star');
                stars.forEach((star, idx) => {
                    if (idx < val) {
                        star.style.color = '#fb923c';
                    } else {
                        star.style.color = '#cbd5e1';
                    }
                });
            }

            // --- USER PERSONALIZATION LOGIC ---
            function updateEbookLinks() {
                let currentUid = localStorage.getItem('kannada_rag_uid') || 'Unknown';
                let currentUname = localStorage.getItem('kannada_rag_uname') || '';
                
                const links = document.querySelectorAll('a[href^="/api/read/"]');
                links.forEach(link => {
                    let originalHref = link.getAttribute('data-base-href') || link.getAttribute('href');
                    if (!link.getAttribute('data-base-href')) {
                        link.setAttribute('data-base-href', originalHref);
                    }
                    
                    let separator = originalHref.includes('?') ? '&' : '?';
                    let newHref = originalHref + separator + 'uid=' + encodeURIComponent(currentUid);
                    if (currentUname) {
                        newHref += '&uname=' + encodeURIComponent(currentUname);
                    }
                    link.setAttribute('href', newHref);
                });
            }

            function saveUserName(name) {
                localStorage.setItem('kannada_rag_uname', name.trim());
                
                // Sync with feedback name field
                const fbNameInput = document.getElementById('fb-name');
                if (fbNameInput) fbNameInput.value = name.trim();
                
                updateEbookLinks();
                
                // Show saved indicator briefly
                const status = document.getElementById('name-save-status');
                if (status) {
                    status.style.display = 'inline';
                    setTimeout(() => { status.style.display = 'none'; }, 1500);
                }
            }

            async function submitFeedback(event) {
                event.preventDefault();
                
                const name = document.getElementById('fb-name').value.trim();
                const rating = parseInt(document.getElementById('fb-rating').value);
                const comment = document.getElementById('fb-comment').value.trim();
                const uid = localStorage.getItem('kannada_rag_uid') || 'Unknown';
                const submitBtn = document.getElementById('fb-submit-btn');
                const successMsg = document.getElementById('fb-success-msg');
                
                submitBtn.disabled = true;
                submitBtn.innerText = "Submitting...";
                
                try {
                    const response = await fetch('/api/feedback', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, rating, comment, uid })
                    });
                    
                    const res = await response.json();
                    if (res.status === 'success') {
                        logGAEvent('submit_feedback', { rating: rating, comment_length: comment.length });
                        successMsg.style.display = 'block';
                        document.getElementById('feedback-form').reset();
                        currentRating = 5;
                        renderStars(5);
                        setTimeout(() => { successMsg.style.display = 'none'; }, 5000);
                    } else {
                        alert("Submission failed: " + res.message);
                    }
                } catch (e) {
                    alert("Network error. Please try again.");
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerText = "Submit Feedback";
                }
            }

            function logGAEvent(eventName, params) {
                if (typeof gtag === 'function') {
                    gtag('event', eventName, params);
                }
            }

            // Initialize ratings and user info display on load
            window.addEventListener('DOMContentLoaded', () => {
                renderStars(5);
                
                // Initialize UID
                let uid = localStorage.getItem('kannada_rag_uid');
                if (!uid) {
                    const randHex = Math.floor(1000 + Math.random() * 9000).toString();
                    uid = 'Guest-' + randHex;
                    localStorage.setItem('kannada_rag_uid', uid);
                }
                
                let uname = localStorage.getItem('kannada_rag_uname') || '';
                const nameInput = document.getElementById('user-custom-name');
                if (nameInput) nameInput.value = uname;
                
                const fbName = document.getElementById('fb-name');
                if (fbName) fbName.value = uname;
                
                updateEbookLinks();
            });

            let currentText = "";
            let isSpeaking = false;
            let currentAudio = null;
            let isSeeking = false;
            let chatHistory = [];
            try {
                chatHistory = JSON.parse(localStorage.getItem('chatHistory') || '[]');
            } catch(e) {
                chatHistory = [];
            }

            function clearChatHistory() {
                chatHistory = [];
                localStorage.removeItem('chatHistory');
                localStorage.removeItem('lastQuestion');
                localStorage.removeItem('lastAnswer');
                document.getElementById('q').value = '';
                document.getElementById('ans-container').style.display = 'none';
                document.getElementById('clear-history-btn').style.display = 'none';
                if (currentAudio) {
                    currentAudio.pause();
                    currentAudio = null;
                }
                isSpeaking = false;
                document.getElementById('media-player').style.display = 'none';
            }

            function copyAnswer() {
                const btn = document.getElementById('copy-btn');
                const btnSpan = btn.querySelector('span');
                navigator.clipboard.writeText(currentText).then(() => {
                    logGAEvent('copy_answer', { text_length: currentText.length });
                    const origText = btnSpan.innerText;
                    btnSpan.innerText = "✅ Copied!";
                    btn.style.background = "#dcfce7";
                    btn.style.color = "#15803d";
                    btn.style.borderColor = "rgba(21, 128, 61, 0.2)";
                    setTimeout(() => {
                        btnSpan.innerText = origText;
                        btn.style.background = "rgba(194, 65, 12, 0.05)";
                        btn.style.color = "var(--primary)";
                        btn.style.borderColor = "rgba(194, 65, 12, 0.12)";
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy: ', err);
                });
            }

            function setPlaybackSpeed(speed) {
                if (currentAudio) {
                    currentAudio.playbackRate = parseFloat(speed);
                }
            }

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
                
                // Restore previous query if exists
                const lastQ = localStorage.getItem('lastQuestion');
                const lastAns = localStorage.getItem('lastAnswer');
                if (lastQ && lastAns) {
                    document.getElementById('q').value = lastQ;
                    currentText = lastAns;
                    document.getElementById('text-res').innerHTML = formatMarkdown(lastAns);
                    document.getElementById('ans-container').style.display = 'block';
                    const clearBtn = document.getElementById('clear-history-btn');
                    if (clearBtn) clearBtn.style.display = 'inline-block';
                }
                
                // Auto-focus input box and handle Enter key
                const qInput = document.getElementById('q');
                if (qInput) {
                    qInput.focus();
                    qInput.addEventListener('keydown', (e) => {
                        if (e.key === 'Enter') {
                            e.preventDefault();
                            ask();
                        }
                    });
                }
            });

            // Time Formatter
            function formatTime(secs) {
                if (isNaN(secs)) return "0:00";
                const m = Math.floor(secs / 60);
                const s = Math.floor(secs % 60);
                return `${m}:${s < 10 ? '0' : ''}${s}`;
            }

            function setQ(txt) {
                chatHistory = []; // Reset history to start a fresh thread
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

                // Blockquotes: lines starting with &gt;
                html = html.replace(/^\s*&gt;\s+(.*?)$/gm, '<blockquote>$1</blockquote>');

                // Headers: ###, ##, #
                html = html.replace(/^### (.*?)$/gm, '<h3 style="color: var(--primary); margin-top: 1rem; margin-bottom: 0.5rem; font-family: var(--font-serif);">$1</h3>');
                html = html.replace(/^## (.*?)$/gm, '<h2 style="color: var(--primary); margin-top: 1.2rem; margin-bottom: 0.6rem; font-family: var(--font-serif);">$1</h2>');
                html = html.replace(/^# (.*?)$/gm, '<h1 style="color: var(--primary); margin-top: 1.5rem; margin-bottom: 0.8rem; font-family: var(--font-serif);">$1</h1>');

                // Lists: lines starting with * or - followed by a space
                html = html.replace(/^\s*[\*\-]\s+(.*?)$/gm, '<li style="margin-bottom: 0.25rem;">$1</li>');
                
                // Wrap contiguous <li> tags with <ul>...</ul>
                html = html.replace(/(<li.*?>.*?<\/li>)+/g, '<ul>$&</ul>');

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

                // Convert remaining newlines to <br> (excluding ones inside lists/blockquotes if we want, but simple replace is fine)
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
                    currentAudio.playbackRate = parseFloat(document.getElementById('audio-speed').value || '1.0');
                });

                currentAudio.addEventListener('play', () => {
                    const viz = document.getElementById('audio-visualizer');
                    if (viz) viz.classList.add('playing');
                });

                currentAudio.addEventListener('pause', () => {
                    const viz = document.getElementById('audio-visualizer');
                    if (viz) viz.classList.remove('playing');
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
                    const viz = document.getElementById('audio-visualizer');
                    if (viz) viz.classList.remove('playing');
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
                
                btn.disabled = true;
                const origBtnText = btn.innerText;
                btn.innerText = "Analyzing...";
                const qField = document.getElementById('q');
                qField.readOnly = true;
                
                load.style.display = 'flex'; 
                cont.style.display = 'none';
                
                try {
                    const r = await fetch('/chat', { 
                        method: 'POST', 
                        headers: {'Content-Type': 'application/json'}, 
                        body: JSON.stringify({question: q, language: lang, history: chatHistory})
                    });
                    const d = await r.json();
                    
                    // Increment and update local usage count
                    incrementUsage();
                    
                    currentText = d.answer;
                    logGAEvent('ask_query', { question: q, language: lang });
                    res.innerHTML = formatMarkdown(d.answer);
                    
                    // Update conversational memory if it is a successful non-error response
                    const isError = d.answer.startsWith('[GROQ FAILED]') || d.answer.startsWith('[BACKEND ERROR]') || d.answer.startsWith('[ERROR]');
                    if (!isError) {
                        chatHistory.push({role: "user", content: q});
                        chatHistory.push({role: "assistant", content: d.answer});
                        // Limit to last 10 messages (5 turns)
                        if (chatHistory.length > 10) {
                            chatHistory = chatHistory.slice(chatHistory.length - 10);
                        }
                        try {
                            localStorage.setItem('chatHistory', JSON.stringify(chatHistory));
                            localStorage.setItem('lastQuestion', q);
                            localStorage.setItem('lastAnswer', d.answer);
                            const clearBtn = document.getElementById('clear-history-btn');
                            if (clearBtn) clearBtn.style.display = 'inline-block';
                        } catch(e) {}
                    }
                    
                    cont.style.display = 'block';
                    cont.classList.add('fade-in');
                    
                    // Smooth scroll to answer
                    setTimeout(() => {
                        cont.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                    }, 50);
                    
                    // Reset voice buttons state
                    document.getElementById('v-btn').style.display = 'inline-flex';
                    document.getElementById('v-loading').style.display = 'none';
                    document.getElementById('media-player').style.display = 'none';
                    
                    if (document.getElementById('auto-speak').checked) {
                        speak();
                    }
                } catch (e) { 
                    alert("Error: " + e.message); 
                } finally {
                    btn.disabled = false;
                    btn.innerText = origBtnText;
                    qField.readOnly = false;
                    load.style.display = 'none';
                }
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
                
                // Block speech if the output is an error message
                const isError = currentText.startsWith('[GROQ FAILED]') || 
                                currentText.startsWith('[BACKEND ERROR]') || 
                                currentText.startsWith('[ERROR]') || 
                                currentText.includes('exceeded your current quota') || 
                                currentText.includes('error:');
                                
                if (isError) {
                    return;
                }
                
                vBtn.style.display = 'none'; vLoad.style.display = 'block';
                isSpeaking = true;

                try {
                    const r = await fetch('/voice', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({text: currentText, language: lang})});
                    const d = await r.json();
                    vLoad.style.display = 'none';
                    if (d.audio) {
                        logGAEvent('speak_voice', { language: lang });
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

            // Theme Management (Light / Dark Mode)
            function toggleTheme() {
                const body = document.body;
                const btn = document.getElementById('theme-toggle-btn');
                body.classList.toggle('dark-mode');
                const isDark = body.classList.contains('dark-mode');
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
                if (btn) btn.innerHTML = isDark ? '☀️' : '🌓';
            }

            // Restore theme preferences on initialization (Default to Light Mode)
            (function() {
                const savedTheme = localStorage.getItem('theme');
                if (savedTheme === 'dark') {
                    document.body.classList.add('dark-mode');
                    window.addEventListener('DOMContentLoaded', () => {
                        const btn = document.getElementById('theme-toggle-btn');
                        if (btn) btn.innerHTML = '☀️';
                    });
                }
            })();
        </script>
    </body>
    </html>

    """
    html_content = html_content.replace("<!-- {{GOOGLE_SITE_VERIFICATION}} -->", gsv_meta)
    html_content = html_content.replace("<!-- {{GOOGLE_ANALYTICS_SCRIPT}} -->", ga_script)
    return HTMLResponse(content=html_content)

handler = app
