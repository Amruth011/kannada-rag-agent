# api/index.py - FastAPI version for Vercel deployment Final v5 (Stable)
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import os, re, requests, json, traceback, base64, time
from typing import List, Optional
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
EBOOK_PASSWORD = os.getenv("EBOOK_PASSWORD", "readkarana").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123").strip()

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

def call_groq(prompt, history=None, retries=1):
    """Fallback to Groq with active model fallbacks (Llama 3.3 -> Llama 3.1 -> Llama 4 Scout)."""
    if not GROQ_API_KEY:
        return "[ERROR]: GROQ_API_KEY is missing."
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "meta-llama/llama-4-scout-17b-16e-instruct"]
    
    last_err = ""
    for model in models:
        for attempt in range(retries + 1):
            messages = [{"role": "system", "content": BOOK_CONTEXT}]
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

def call_gemini(prompt, history=None, retries=1):
    """Deepest Gemini Safety Bypass + System Prompting."""
    if not GEMINI_API_KEY: 
        return call_groq(prompt, history=history)
    
    last_error = ""
    model_name = get_best_gemini_model()
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    for attempt in range(retries + 1):
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=BOOK_CONTEXT
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
                
    return call_groq(prompt, history=history)

def call_sarvam_tts(text, language="kn-IN"):
    """Call Sarvam TTS 'Meera' voice (bulbul:v3) with fallback to Google TTS (gTTS)."""
    # Clean citations and errors
    clean = re.sub(r'\[Page \d+\]:', '', text).strip()
    clean = re.sub(r'📄 Sources:.*', '', clean).strip()
    clean = re.sub(r'\[(?:GEMINI FAILED|GROQ FAILED|BACKEND ERROR|ERROR)[^\]]*\]', '', clean).strip()

    # Limit text length to avoid serverless timeouts (10s limit) on Vercel
    if len(clean) > 500:
        truncated = clean[:500]
        # Find last sentence boundary
        last_boundary = max(truncated.rfind('.'), truncated.rfind('।'), truncated.rfind('?'), truncated.rfind('!'))
        if last_boundary > 200:
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
            full_prompt = f"""You are an AI assistant for the Kannada novel "Heli Hogu Karana".

BOOK INFORMATION:
{BOOK_CONTEXT}

RETRIEVED PASSAGES:
{pagetext}

Answer the question in detail using the information above. Be highly informative, provide thorough explanations, explore context from the passages, and cite page numbers when using passages. Do not give short or brief summaries.

QUESTION: {request.question}
ANSWER in English:"""
        else:
            full_prompt = f"""ನೀವು "ಹೇಳಿ ಹೋಗು ಕಾರಣ" ಕನ್ನಡ ಕಾದಂಬರಿಯ AI ಸಹಾಯಕರು.

ಪುಸ್ತಕದ ಮಾಹಿತಿ / Book Info:
{BOOK_CONTEXT}

ಪುಸ್ತಕದಿಂದ ತೆಗೆದ ವಿಷಯ:
{pagetext}

ಮೇಲಿನ ಮಾಹಿತಿಯನ್ನು ಬಳಸಿಕೊಂಡು ಪ್ರಶ್ನೆಗೆ ವಿವರವಾಗಿ ಉತ್ತರಿಸಿ. ಸಮಗ್ರವಾದ ಮತ್ತು ಆಳವಾದ ವಿವರಣೆಯನ್ನು ನೀಡಿ, ಕಾದಂಬರಿಯ ಸಂದರ್ಭಗಳನ್ನು ವಿವರಿಸಿ ಮತ್ತು ಸೂಕ್ತ ಪುಟಗಳ ಸಂಖ್ಯೆಯನ್ನು ಕಡ್ಡಾಯವಾಗಿ ನಮೂದಿಸಿ. ಯಾವುದೇ ಕಾರಣಕ್ಕೂ ಸಂಕ್ಷಿಪ್ತ ಅಥವಾ ಸಣ್ಣ ಉತ್ತರಗಳನ್ನು ನೀಡಬೇಡಿ.

ಪ್ರಶ್ನೆ: {request.question}
ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರ:"""
        
        answer = call_gemini(full_prompt, history=request.history)
        return ChatResponse(answer=answer, sources=retrieved_pages)
    except Exception:
        return ChatResponse(answer=f"[BACKEND ERROR]: {traceback.format_exc()[:500]}", sources=[])

@app.post("/voice")
async def voice(request: VoiceRequest):
    # Map requested language option to ISO code
    lang_code = "kn-IN" if request.language == "Kannada" else "en-IN"
    audio_b64 = call_sarvam_tts(request.text, language=lang_code)
    return {"audio": audio_b64}

# ── E-Book Download Routes ───────────────────────────────────────────────────
@app.get("/api/download/{edition}/{format}")
async def download_ebook(edition: str, format: str, password: Optional[str] = None):
    """
    Download a compiled e-book file.
    edition: 'kannada', 'english', or 'bilingual'
    format: 'epub', 'html', or 'md'
    """
    if not password or password.strip() != EBOOK_PASSWORD:
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized: Invalid password. Please DM @heli.hogu.kaarana on Instagram to get the access password."
        )

    edition = edition.lower()
    format = format.lower()
    
    if edition not in ["kannada", "english", "bilingual"]:
        raise HTTPException(status_code=400, detail="Invalid edition. Choose 'kannada', 'english', or 'bilingual'.")
        
    if format not in ["epub", "html", "md"]:
        raise HTTPException(status_code=400, detail="Invalid format. Choose 'epub', 'html', or 'md'.")
        
    filename = f"heli_hogu_karana_{edition}.{format}"
    
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
        
    media_types = {
        "epub": "application/epub+zip",
        "html": "text/html",
        "md": "text/markdown"
    }
    
    # Force download (Content-Disposition attachment)
    headers = {
        "Content-Disposition": f"attachment; filename={filename}"
    }
    
    return FileResponse(file_path, media_type=media_types[format], headers=headers)

@app.post("/api/feedback")
async def save_feedback(request: FeedbackRequest):
    try:
        feedback_data = {
            "name": request.name,
            "rating": request.rating,
            "comment": request.comment,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Log to stdout for real-time Vercel logs
        print(f"[FEEDBACK SUBMISSION] Name: {feedback_data['name']} | Rating: {feedback_data['rating']} stars | Comment: {feedback_data['comment']}")
        
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

        # Combine feedback to prevent loss of local or remote inputs
        seen = set()
        feedbacks = []
        def get_fb_key(fb):
            return (fb.get("name", ""), fb.get("rating", 0), fb.get("comment", ""), fb.get("timestamp", ""))

        for fb in bundled_feedbacks + tmp_feedbacks:
            key = get_fb_key(fb)
            if key not in seen:
                seen.add(key)
                feedbacks.append(fb)

        # Append new feedback
        new_key = get_fb_key(feedback_data)
        if new_key not in seen:
            feedbacks.append(feedback_data)
        
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
                return {"status": "error", "message": f"Could not write feedback to /tmp: {tmp_err}"}
                
        return {"status": "success", "message": "Feedback submitted successfully!"}
    except Exception as e:
        print(f"[ERROR]: Feedback submission failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/admin/feedback", response_class=HTMLResponse)
async def admin_feedback(password: Optional[str] = None):
    if not password or password.strip() != ADMIN_PASSWORD:
        return HTMLResponse(
            status_code=401,
            content="""
            <html>
                <head>
                    <title>401 Unauthorized</title>
                    <style>
                        body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #fffcf8; color: #0f172a; margin: 0; }
                        .card { padding: 2rem; border: 1px solid rgba(194, 65, 12, 0.2); border-radius: 12px; background: white; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }
                        input { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 6px; margin: 10px 0; outline: none; width: 220px; text-align: center; }
                        button { padding: 8px 16px; border: none; background: #c2410c; color: white; border-radius: 6px; cursor: pointer; font-weight: bold; }
                    </style>
                </head>
                <body>
                    <div class="card">
                        <h2>🔒 Admin Login</h2>
                        <p>Please enter the admin password to view feedback.</p>
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

    for fb in bundled_feedbacks + tmp_feedbacks:
        key = get_fb_key(fb)
        if key not in seen:
            seen.add(key)
            feedbacks.append(fb)
            
    # Sort feedbacks by timestamp descending
    try:
        feedbacks.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception:
        pass
        
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
        feedback_rows = "<p style='text-align:center; color:#64748b;'>No feedback submitted yet.</p>"
        
    admin_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Heli Hogu Karana — Admin Feedback Panel</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: system-ui, -apple-system, sans-serif; background: #fffcf8; color: #0f172a; margin: 0; padding: 2rem 1rem; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            h1 {{ font-family: Georgia, serif; color: #c2410c; margin-bottom: 0.5rem; }}
            .subtitle {{ color: #64748b; margin-bottom: 2rem; }}
            .fb-card {{ background: white; border: 1px solid rgba(194, 65, 12, 0.1); border-radius: 12px; padding: 1.5rem; margin-bottom: 1rem; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.02); }}
            .fb-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem; }}
            .fb-name {{ font-weight: bold; font-size: 1.1rem; }}
            .fb-stars {{ color: #fb923c; font-size: 1.1rem; letter-spacing: 2px; }}
            .fb-time {{ font-size: 0.8rem; color: #94a3b8; margin-bottom: 0.75rem; }}
            .fb-comment {{ line-height: 1.5; color: #334155; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 User Feedback Panel</h1>
            <p class="subtitle">Real-time reader feedback submitted on the novel AI assistant portal.</p>
            <div class="fb-list">
                {feedback_rows}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=admin_html)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    icon_b64 = "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAC2klEQVR4nO2WzWtcVRjGf885d2YySaY6lmibSiG0xS8QUXDRnVBxVXAhSPeuXAru+y+o4MJF/wClq9KFIFTNSkHBryIUS6tFK2mCmWk+Zu4953GRyUczM0kUsih6uJzFfS/P7zznfc99j9Z7f3KYIxyq+v+A/wag2CvojDMSaDDviGEPZgU0dqHjAc7Up1EdMi6peqQ+IQLkRKxTa6AaBNynf38cYxzA1Fvc+kyLN33kOK0nac8xMUPVBai3WV/g3s/q3qF71+055s5R3n/Q4t6AVLlail+/p++vMQVF8JGTPn3eZ9/B6POL8cZVd26TMqv4+VfSsRcVAqF2EICJDTq/8c2HnmiHyUijcO5r+ZaufZDTClB8cYlHUAiE6CaeaGv+Ii+9TfsUqbfLxxDAgMilcikyOdkAKuqaTO4tYWhGZOWcJo9qfVHO5ApXILx7n4YysxGW0FbdKADO5KRQSNEBt57IbuSz73LslMoVQsQjEjAK4N0wgcFy3gimvqceTS+8lS5cZnVRS79TTOA8KsEjAUMwgTHeVhCJ1qwWfqB1wiSPF9gPAIYsDw7aJkGpdH2a7z721IxytZP8DwACFB0iikiADdkUdXVX4rcfceZc/Op9ShEamMEzNIaqaHMVRu53tJpQAqhnQiQIk2tRN+fj9XlHKKG3TG0KjXYwskwB4exn36R4jLRM5w6dX/VXh/4KFmspP97OJ07SmkUtP/Uqt78c1OhBHUis3OWZN/z06+REuUb3D//yKXIGZl/W6deYPk6tSQhWwfVPdiZpPwe5ojkjRS5fIAQABWpNcvbMc0gs/Mi9n6jWcQaUMyrcPEoqhxkadaswigDV2uYxAEWtLnDjCsCZ856cwWnTrymawI43+wC2gjtrzIQasQWQuuTyAS3ncRp7NBzjtIUCqHqUqxtuNsXHHN+DAYa3U2jr+6G/2pjxr3vy3urbBXtITX8b//BfWx5+wN+tZC4TtUtAXgAAAABJRU5ErkJggg=="
    return Response(content=base64.b64decode(icon_b64), media_type="image/x-icon")

@app.get("/", response_class=HTMLResponse)
async def root():
    return r"""    <!DOCTYPE html>
    <html lang="kn">
    <head>
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
                flex-wrap: wrap;
                border-bottom: 2px solid rgba(194, 65, 12, 0.08);
                margin-bottom: 2.2rem;
                gap: 0.4rem;
                padding-bottom: 0.5rem;
                justify-content: center;
            }
            .tab-btn {
                background: none;
                border: none;
                font-family: inherit;
                font-size: 0.85rem;
                font-weight: 700;
                color: var(--text-muted);
                border-bottom: 3px solid transparent;
                padding: 0.5rem 0.9rem;
                cursor: pointer;
                outline: none;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                white-space: nowrap;
                display: inline-flex;
                align-items: center;
                gap: 5px;
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

                <!-- TABS NAVIGATION -->
                <div class="tabs-nav" style="margin-top: 10px;">
                    <button class="tab-btn active" onclick="switchTab('chat')">💬 AI Guide</button>
                    <button class="tab-btn" onclick="switchTab('charmap')">🗺️ Character Map</button>
                    <button class="tab-btn" onclick="switchTab('quotemaker')">🎨 Quote Creator</button>
                    <button class="tab-btn" onclick="switchTab('downloads')">📚 E-Books</button>
                    <button class="tab-btn" onclick="switchTab('feedback')">✍️ Feedback</button>
                </div>

                <!-- SECTION 1: AI CHAT GUIDE -->
                <div id="section-chat" class="tab-section active">
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
                                <path d="M 250,180 Q 160,135 110,90" stroke-width="2.5" fill="none" opacity="0.4" class="edge" id="edge-him-pra" />
                                <!-- Himavant <-> Ravi -->
                                <path d="M 250,180 Q 340,135 390,90" stroke-width="2.5" fill="none" opacity="0.4" class="edge" id="edge-him-rav" />
                                <!-- Prarthana <-> Ravi -->
                                <path d="M 110,90 Q 250,60 390,90" stroke-width="1.5" stroke-dasharray="3,3" fill="none" opacity="0.3" class="edge" id="edge-pra-rav" />
                                <!-- Himavant <-> Rasool -->
                                <path d="M 250,180 Q 200,240 150,290" stroke-width="2" fill="none" opacity="0.4" class="edge" id="edge-him-ras" />
                                <!-- Himavant <-> Ravi Belagere -->
                                <path d="M 250,180 Q 300,240 350,290" stroke-width="2" fill="none" opacity="0.4" class="edge" id="edge-him-bel" />
                            </g>

                            <!-- Edge Labels -->
                            <g font-size="8" fill="var(--text-muted)" text-anchor="middle" class="edge-label">
                                <text x="170" y="145" transform="rotate(-30 170 145)">Love / ಪ್ರೇಮ</text>
                                <text x="330" y="145" transform="rotate(30 330 145)">Friend / ಸ್ನೇಹ</text>
                                <text x="175" y="225" transform="rotate(30 175 225)">Loyalty / ನಿಷ್ಠೆ</text>
                                <text x="325" y="225" transform="rotate(-30 325 225)">Narrator / ನಿರೂಪಕ</text>
                            </g>

                            <!-- Character Nodes -->
                            <!-- Prarthana -->
                            <g class="node" onclick="clickChar('prarthana')" id="node-prarthana">
                                <circle cx="110" cy="90" r="22" fill="#fff" stroke="#ca8a04" stroke-width="2.5" filter="url(#glow)" />
                                <text x="110" y="94" font-size="10" text-anchor="middle" fill="#0f172a">ಪ್ರಾರ್ಥನಾ</text>
                            </g>
                            <!-- Ravi -->
                            <g class="node" onclick="clickChar('ravi')" id="node-ravi">
                                <circle cx="390" cy="90" r="22" fill="#fff" stroke="#4338ca" stroke-width="2.5" filter="url(#glow)" />
                                <text x="390" y="94" font-size="10" text-anchor="middle" fill="#0f172a">ರವಿ</text>
                            </g>
                            <!-- Rasool Jamadar -->
                            <g class="node" onclick="clickChar('rasool')" id="node-rasool">
                                <circle cx="150" cy="290" r="22" fill="#fff" stroke="#475569" stroke-width="2" />
                                <text x="150" y="294" font-size="9" text-anchor="middle" fill="#0f172a">ರಸೂಲ್</text>
                            </g>
                            <!-- Ravi Belagere -->
                            <g class="node" onclick="clickChar('belagere')" id="node-belagere">
                                <circle cx="350" cy="290" r="22" fill="#fff" stroke="#dc2626" stroke-width="2" />
                                <text x="350" y="294" font-size="9" text-anchor="middle" fill="#0f172a">ಬೆಳಗೆರೆ</text>
                            </g>
                            <!-- Himavant (Protagonist) -->
                            <g class="node" onclick="clickChar('himavant')" id="node-himavant">
                                <circle cx="250" cy="180" r="25" fill="#fff" stroke="#c2410c" stroke-width="3" filter="url(#glow)" />
                                <text x="250" y="184" font-size="11" font-weight="bold" text-anchor="middle" fill="#c2410c">ಹಿಮವಂತ್</text>
                            </g>
                        </svg>

                        <!-- Character Biography Card -->
                        <div id="char-detail-card" class="char-card" style="display:none;">
                            <div class="char-tabs">
                                <button class="char-tab-btn active" id="btn-char-en" onclick="setCharLang('en')">English</button>
                                <button class="char-tab-btn" id="btn-char-kn" onclick="setCharLang('kn')">ಕನ್ನಡ</button>
                            </div>
                            <h3 id="char-name">Character Name <span class="badge" id="char-badge">Protagonist</span><                    <div class="quote-creator-box">
                        <canvas id="quote-canvas" width="600" height="600" style="width: 100%; max-width: 380px; border-radius: 16px; border: 1px solid rgba(194, 65, 12, 0.15); display: block; margin: 0 auto; box-shadow: 0 10px 30px rgba(0,0,0,0.06);"></canvas>
                        
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
                                <label>2. Pick a Famous Quote / ಕೋಟ್ ಆಯ್ಕೆ ಮಾಡಿ</label>
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
                                    <option value="Tell me before you leave... because there's a heart here waiting for you.">Tell me before you leave... (Heli Hogu Karana Theme)</option>
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
                                <label>3. Customize Quote Text / ವಾಕ್ಯವನ್ನು ಬದಲಿಸಿ</label>
                                <textarea id="quote-text" rows="3" oninput="drawQuoteCard()" placeholder="Type your custom quote here..."></textarea>
                            </div>
                            
                            <div class="control-group">
                                <label>4. Select Style Theme / ಶೈಲಿ ಆಯ್ಕೆ</label>
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
                        </div>
                    </div>
                </div>    <option value="ಮೌನಕ್ಕೂ ಒಂದು ಭಾಷೆಯಿದೆ, ಅದನ್ನ ಆಲಿಸಲು ಒಂದು ವಿಶೇಷವಾದ ಪ್ರೇಮ ಬೇಕು.">ಮೌನಕ್ಕೂ ಒಂದು ಭಾಷೆಯಿದೆ (Language of Silence)</option>
                                    <option value="ನಾವು ಪ್ರೀತಿಸುವವರ ಕೊರತೆಗಿಂತ, ನಮ್ಮನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುವವರ ಕೊರತೆಯೇ ಹೆಚ್ಚು ನೋವು ಕೊಡುತ್ತದೆ.">ನಮ್ಮನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳುವವರ ಕೊರತೆ (Being Understood)</option>
                                </select>
                            </div>
                            
                            <div class="control-group">
                                <label>2. Customize Quote Text / ವಾಕ್ಯವನ್ನು ಬದಲಿಸಿ</label>
                                <textarea id="quote-text" rows="3" oninput="drawQuoteCard()" placeholder="Type your custom quote here..."></textarea>
                            </div>
                            
                            <div class="control-group">
                                <label>3. Select Style Theme / ಶೈಲಿ ಆಯ್ಕೆ</label>
                                <select id="quote-style" onchange="drawQuoteCard()">
                                    <option value="saffron">Saffron Gold / ಕೇಸರಿ ಚಿನ್ನ</option>
                                    <option value="vintage">Terracotta Vintage / ವಿಂಟೇಜ್ ಮಣ್ಣು</option>
                                    <option value="midnight">Midnight Shadow / ಕತ್ತಲೆಯ ನೆರಳು</option>
                                </select>
                            </div>
                            
                            <button onclick="downloadQuoteCard()" class="main-btn" style="margin-top: 0.5rem; display: flex; align-items: center; justify-content: center; gap: 8px;">
                                <span>📥 Save Quote Card to Device</span>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- SECTION 4: E-BOOK DOWNLOADS -->
                <div id="section-downloads" class="tab-section">
                    <h2 style="font-family: var(--font-serif); color: var(--primary); text-align: center; margin-top: 1rem; margin-bottom: 0.5rem; font-size: 1.6rem; font-weight: 700;">📚 ಇ-ಪುಸ್ತಕಗಳನ್ನು ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ / Download E-Books</h2>
                    <p style="text-align: center; color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.8rem; line-height: 1.5;">
                        To support translation costs and cover server bills, e-books are password locked. DM `@heli.hogu.kaarana` on Instagram to get the password!
                    </p>
                    <div class="download-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.2rem;">
                        <!-- KANNADA EDITION -->
                        <div class="download-box" style="background: var(--bg-secondary); border: 1px solid rgba(194, 65, 12, 0.1); border-radius: 16px; padding: 1.5rem; display: flex; flex-direction: column; align-items: center; text-align: center;">
                            <h3 style="font-family: var(--font-serif); margin-top: 0; margin-bottom: 0.5rem; color: var(--primary); font-size: 1.25rem; font-weight: 700;">ಕನ್ನಡ ಆವೃತ್ತಿ<br><span style="font-size: 0.85rem; font-family: var(--font-sans); color: var(--text-muted); font-weight: 500;">Kannada Edition</span></h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1.2rem; flex-grow: 1; line-height: 1.4;">Original Kannada text of the novel, structured with chapter-by-chapter formatting.</p>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; width: 100%;">
                                <button onclick="openDownloadModal('kannada', 'epub')" class="dl-btn" style="background: var(--primary); color: white; padding: 8px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; border: none; cursor: pointer; outline: none;">EPUB</button>
                                <button onclick="openDownloadModal('kannada', 'html')" class="dl-btn" style="background: white; border: 1px solid var(--primary); color: var(--primary); padding: 7px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; cursor: pointer; outline: none;">HTML</button>
                                <button onclick="openDownloadModal('kannada', 'md')" class="dl-btn" style="background: white; border: 1px solid rgba(0,0,0,0.1); color: var(--text); padding: 7px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; cursor: pointer; outline: none;">MD</button>
                            </div>
                        </div>

                        <!-- BILINGUAL EDITION -->
                        <div class="download-box" style="background: var(--bg-secondary); border: 2px solid var(--primary); border-radius: 16px; padding: 1.5rem; display: flex; flex-direction: column; align-items: center; text-align: center; position: relative;">
                            <div style="position: absolute; top: 0; right: 0; background: var(--primary); color: white; font-size: 0.6rem; font-weight: 800; padding: 4px 8px; border-bottom-left-radius: 6px; text-transform: uppercase;">Best</div>
                            <h3 style="font-family: var(--font-serif); margin-top: 0; margin-bottom: 0.5rem; color: var(--primary); font-size: 1.25rem; font-weight: 700;">ದ್ವಿಭಾಷಾ ಆವೃತ್ತಿ<br><span style="font-size: 0.85rem; font-family: var(--font-sans); color: var(--text-muted); font-weight: 500;">Bilingual Edition</span></h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1.2rem; flex-grow: 1; line-height: 1.4;">Side-by-side Kannada and English columns. Ideal for comparative reading.</p>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; width: 100%;">
                                <button onclick="openDownloadModal('bilingual', 'epub')" class="dl-btn" style="background: var(--primary); color: white; padding: 8px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; border: none; cursor: pointer; outline: none;">EPUB</button>
                                <button onclick="openDownloadModal('bilingual', 'html')" class="dl-btn" style="background: white; border: 1px solid var(--primary); color: var(--primary); padding: 7px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; cursor: pointer; outline: none;">HTML</button>
                                <button onclick="openDownloadModal('bilingual', 'md')" class="dl-btn" style="background: white; border: 1px solid rgba(0,0,0,0.1); color: var(--text); padding: 7px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; cursor: pointer; outline: none;">MD</button>
                            </div>
                        </div>

                        <!-- ENGLISH EDITION -->
                        <div class="download-box" style="background: var(--bg-secondary); border: 1px solid rgba(194, 65, 12, 0.1); border-radius: 16px; padding: 1.5rem; display: flex; flex-direction: column; align-items: center; text-align: center;">
                            <h3 style="font-family: var(--font-serif); margin-top: 0; margin-bottom: 0.5rem; color: var(--primary); font-size: 1.25rem; font-weight: 700;">ಇಂಗ್ಲಿಷ್ ಆವೃತ್ತಿ<br><span style="font-size: 0.85rem; font-family: var(--font-sans); color: var(--text-muted); font-weight: 500;">English Edition</span></h3>
                            <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 1.2rem; flex-grow: 1; line-height: 1.4;">Complete English literary translation reflecting the author's intense story arc.</p>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap; justify-content: center; width: 100%;">
                                <button onclick="openDownloadModal('english', 'epub')" class="dl-btn" style="background: var(--primary); color: white; padding: 8px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; border: none; cursor: pointer; outline: none;">EPUB</button>
                                <button onclick="openDownloadModal('english', 'html')" class="dl-btn" style="background: white; border: 1px solid var(--primary); color: var(--primary); padding: 7px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; cursor: pointer; outline: none;">HTML</button>
                                <button onclick="openDownloadModal('english', 'md')" class="dl-btn" style="background: white; border: 1px solid rgba(0,0,0,0.1); color: var(--text); padding: 7px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; cursor: pointer; outline: none;">MD</button>
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
        </div>
            </div>
        </div>

        <!-- INSTAGRAM PASSWORD-LOCK MODAL -->
        <div id="pw-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(8px); z-index: 1000; align-items: center; justify-content: center; padding: 1rem; opacity: 0; transition: opacity 0.3s ease;">
            <div class="modal-card" style="background: white; border: 1px solid rgba(194, 65, 12, 0.15); border-radius: 20px; padding: 2.5rem 2rem; width: 100%; max-width: 440px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); position: relative; transform: scale(0.9); transition: transform 0.3s ease; text-align: center; box-sizing: border-box;">
                <!-- Close Button -->
                <button onclick="closeDownloadModal()" style="position: absolute; top: 15px; right: 15px; background: none; border: none; font-size: 1.8rem; color: var(--text-muted); cursor: pointer; outline: none; line-height: 1;">&times;</button>
                
                <div style="font-size: 3rem; margin-bottom: 0.8rem;">🔒</div>
                <h3 style="font-family: var(--font-serif); color: var(--primary); font-size: 1.5rem; margin-top: 0; margin-bottom: 0.5rem; font-weight: 700;">Unlock E-Book Download</h3>
                <p style="font-size: 0.88rem; color: var(--text-muted); line-height: 1.5; margin-bottom: 1.5rem;">
                    To protect copyright and support the project, downloads are password-protected. Send a direct message (DM) to our Instagram account to get the password instantly!
                </p>
                
                <a href="https://instagram.com/heli.hogu.kaarana" target="_blank" style="display: inline-flex; align-items: center; gap: 8px; text-decoration: none; background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%); color: white; padding: 12px 24px; border-radius: 99px; font-weight: 700; font-size: 0.9rem; margin-bottom: 2rem; box-shadow: 0 4px 15px rgba(220, 39, 67, 0.4); transition: transform 0.2s;">
                    <svg style="width: 18px; height: 18px; fill: white;" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/></svg>
                    DM @heli.hogu.kaarana
                </a>
                
                <div style="text-align: left; margin-bottom: 1.5rem;">
                    <label for="ebook-pw" style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">Enter Unlock Password</label>
                    <input type="password" id="ebook-pw" placeholder="Enter password to download" style="width: 100%; padding: 12px; border: 1.5px solid rgba(194, 65, 12, 0.15); border-radius: 10px; font-family: inherit; font-size: 0.95rem; outline: none; box-sizing: border-box; text-align: center; transition: border-color 0.2s;">
                    <div id="pw-error" style="color: #ef4444; font-size: 0.8rem; font-weight: 600; margin-top: 6px; display: none; text-align: center;">Incorrect password. Please try again.</div>
                </div>
                
                <button onclick="submitDownload()" style="width: 100%; background: var(--primary); color: white; padding: 12px; border: none; border-radius: 10px; font-size: 0.95rem; font-weight: 700; cursor: pointer; transition: all 0.2s; outline: none; box-shadow: 0 4px 12px rgba(194, 65, 12, 0.25);">Unlock & Download</button>
            </div>
        </div>

        <script>
            let selectedEdition = "";
            let selectedFormat = "";

            // --- TAB SWITCHER LOGIC ---
            function switchTab(tabId) {
                const buttons = document.querySelectorAll('.tab-btn');
                buttons.forEach(btn => {
                    btn.classList.remove('active');
                });
                
                const clickedBtn = document.querySelector(`.tab-btn[onclick="switchTab('${tabId}')"]`);
                if (clickedBtn) clickedBtn.classList.add('active');
                
                const sections = document.querySelectorAll('.tab-section');
                sections.forEach(sec => sec.classList.remove('active'));
                
                const targetSec = document.getElementById(`section-${tabId}`);
                if (targetSec) targetSec.classList.add('active');
                
                if (tabId === 'quotemaker') {
                    // Slight delay to ensure canvas is rendered
                    setTimeout(drawQuoteCard, 20);
                }
            }

            // --- CHARACTER MAP DATA & LOGIC ---
            const CHAR_DATA = {
                himavant: {
                    name_en: "Himavant",
                    name_kn: "ಹಿಮವಂತ್",
                    badge_en: "Protagonist",
                    badge_kn: "ಕಥಾನಾಯಕ",
                    desc_en: "The passionate, intense protagonist of Heli Hogu Karana. He is a man of deep emotions, conflicted by his love for Prarthana and his complex life choices in a gritty underworld environment.",
                    desc_kn: "ಕಾದಂಬರಿಯ ಕಥಾನಾಯಕ. ತೀವ್ರವಾದ ಭಾವನೆಗಳುಳ್ಳ, ಪ್ರಾರ್ಥನಾಳ ಮೇಲಿನ ಪ್ರೀತಿ ಹಾಗೂ ತನ್ನ ಜೀವನದ ಸಂಕೀರ್ಣ ನಿರ್ಧಾರಗಳ ನಡುವೆ ಒದ್ದಾಡುವ ತೇಜಸ್ವಿ ವ್ಯಕ್ತಿತ್ವ.",
                    pages: "Major presence throughout the novel (e.g. Pages 1, 10, 45, 120, 240, 310)"
                },
                prarthana: {
                    name_en: "Prarthana",
                    name_kn: "ಪ್ರಾರ್ಥನಾ",
                    badge_en: "Female Lead",
                    badge_kn: "ನಾಯಕಿ",
                    desc_en: "The mysterious, beautiful female lead. Her relationship with Himavant is full of emotional depth, silence, and unspoken words, driving much of the story's emotional tension.",
                    desc_kn: "ಕಾದಂಬರಿಯ ನಾಯಕಿ. ಹಿಮವಂತನ ಪ್ರೀತಿಯ ಸೆಲೆ. ಅವಳ ಮೌನ, ಗಾಂಭೀರ್ಯ ಮತ್ತು ರಹಸ್ಯಮಯ ನಡವಳಿಕೆ ಇಡೀ ಕಥೆಗೆ ಹೊಸ ಭಾವನಾತ್ಮಕ ತಿರುವು ನೀಡುತ್ತದೆ.",
                    pages: "Pages 5, 22, 54, 108, 195, 280, 340"
                },
                ravi: {
                    name_en: "Ravi",
                    name_kn: "ರವಿ",
                    badge_en: "Close Friend",
                    badge_kn: "ಆತ್ಮೀಯ ಗೆಳೆಯ",
                    desc_en: "Himavant's close companion and sounding board. He plays a vital role in balancing Himavant's volatile decisions and acts as a bridge of sanity in his turbulent life.",
                    desc_kn: "ಹಿಮವಂತನ ನಿಷ್ಠಾವಂತ ಒಡನಾಡಿ. ಕಷ್ಟದ ಸಮಯದಲ್ಲಿ ಜೊತೆಯಾಗಿ ನಿಂತು, ಜೀವನದ ಮಹತ್ತರ ತಿರುವುಗಳಲ್ಲಿ ಮಾರ್ಗದರ್ಶನ ನೀಡುವ ವಿಶ್ವಾಸಾರ್ಹ ಗೆಳೆಯ.",
                    pages: "Pages 15, 42, 87, 134, 210, 295"
                },
                rasool: {
                    name_en: "Rasool Jamadar",
                    name_kn: "ರಸೂಲ್ ಜಮಾದಾರ",
                    badge_en: "Companion / Protector",
                    badge_kn: "ನಿಷ್ಠಾವಂತ ರಕ್ಷಕ",
                    desc_en: "A rugged associate and protector, representing the fierce and loyal underground world elements in Ravi Belagere's classic narrative landscape.",
                    desc_kn: "ಹಿಮವಂತನಿಗೆ ನೆರಳಾಗಿ ನಿಲ್ಲುವ ಒರಟು ಸ್ವಭಾವದ ನಿಷ್ಠಾವಂತ ಸಾಥಿ. ಭೂಗತ ಜಗತ್ತಿನ ಕಥಾ ಹೆಣಿಗೆಯಲ್ಲಿ ಧೈರ್ಯ ಮತ್ತು ನಿಷ್ಠೆಯ ಸಂಕೇತ.",
                    pages: "Pages 34, 78, 112, 160, 255"
                },
                belagere: {
                    name_en: "Ravi Belagere",
                    name_kn: "ರವಿ ಬೆಳಗೆರೆ",
                    badge_en: "Author / Narrator",
                    badge_kn: "ಲೇಖಕ / ನಿರೂಪಕ",
                    desc_en: "The author and narrator who weaves himself directly into the story's atmosphere. He narrates with his signature intensity, suspense, and emotional attachment to his characters.",
                    desc_kn: "ಕಾದಂಬರಿಯ ಕರ್ತೃ ಮತ್ತು ಸೂತ್ರಧಾರ. ತಮ್ಮದೇ ಆದ ವಿಶಿಷ್ಟ ಪತ್ರಿಕೋದ್ಯಮ ಮತ್ತು ಸಾಹಿತ್ಯ ಶೈಲಿಯಲ್ಲಿ ಕಥೆಯನ್ನು ಕಟ್ಟಿಕೊಡುತ್ತಾ, ಓದುಗರನ್ನು ಸೆಳೆಯುವ ನಿರೂಪಕ.",
                    pages: "Narrates and comments throughout the entire novel"
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
                        edge.style.strokeWidth = id.includes('pra-rav') ? '1.5' : '2.5';
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

            function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
                const words = text.split(' ');
                let line = '';
                let lines = [];
                for (let n = 0; n < words.length; n++) {
                    let testLine = line + words[n] + ' ';
                    let metrics = ctx.measureText(testLine);
                    let testWidth = metrics.width;
                    if (testWidth > maxWidth && n > 0) {
                        lines.push(line);
                        line = words[n] + ' ';
                    } else {
                        line = testLine;
                    }
                }
                lines.push(line);
                
                for (let k = 0; k < lines.length; k++) {
                    ctx.fillText(lines[k].trim(), x, y + (k * lineHeight));
                }
                return lines.length * lineHeight;
            }

            function drawQuoteCard() {
                const canvas = document.getElementById('quote-canvas');
                if (!canvas) return;
                const ctx = canvas.getContext('2d');
                const quoteText = document.getElementById('quote-text').value.trim() || "ಹೇಳಿ ಹೋಗು ಕಾರಣ...";
                const style = document.getElementById('quote-style').value;
                
                ctx.clearRect(0, 0, 600, 600);
                
                // Draw template background
                if (style === 'saffron') {
                    let grad = ctx.createLinearGradient(0, 0, 600, 600);
                    grad.addColorStop(0, '#c2410c');
                    grad.addColorStop(0.5, '#ea580c');
                    grad.addColorStop(1, '#ca8a04');
                    ctx.fillStyle = grad;
                    ctx.fillRect(0, 0, 600, 600);
                    
                    ctx.strokeStyle = 'rgba(254, 243, 199, 0.4)';
                    ctx.lineWidth = 15;
                    ctx.strokeRect(20, 20, 560, 560);
                    
                    ctx.strokeStyle = 'rgba(254, 243, 199, 0.2)';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(35, 35, 530, 530);
                    
                    ctx.fillStyle = '#fef3c7';
                } else if (style === 'vintage') {
                    ctx.fillStyle = '#fffbeb';
                    ctx.fillRect(0, 0, 600, 600);
                    
                    ctx.strokeStyle = '#c2410c';
                    ctx.lineWidth = 12;
                    ctx.strokeRect(20, 20, 560, 560);
                    
                    ctx.fillStyle = '#c2410c';
                    ctx.fillRect(35, 35, 10, 10);
                    ctx.fillRect(555, 35, 10, 10);
                    ctx.fillRect(35, 555, 10, 10);
                    ctx.fillRect(555, 555, 10, 10);
                    
                    ctx.fillStyle = '#0f172a';
                } else if (style === 'rose') {
                    let grad = ctx.createLinearGradient(0, 0, 600, 600);
                    grad.addColorStop(0, '#fce7f3');
                    grad.addColorStop(1, '#fbcfe8');
                    ctx.fillStyle = grad;
                    ctx.fillRect(0, 0, 600, 600);
                    ctx.strokeStyle = '#db2777';
                    ctx.lineWidth = 8;
                    ctx.strokeRect(20, 20, 560, 560);
                    ctx.fillStyle = '#831843';
                } else if (style === 'forest') {
                    let grad = ctx.createLinearGradient(0, 0, 0, 600);
                    grad.addColorStop(0, '#052e16');
                    grad.addColorStop(1, '#14532d');
                    ctx.fillStyle = grad;
                    ctx.fillRect(0, 0, 600, 600);
                    ctx.strokeStyle = '#4ade80';
                    ctx.lineWidth = 4;
                    ctx.strokeRect(20, 20, 560, 560);
                    ctx.fillStyle = '#dcfce7';
                } else {
                    ctx.fillStyle = '#0f172a';
                    ctx.fillRect(0, 0, 600, 600);
                    ctx.strokeStyle = '#ea580c';
                    ctx.lineWidth = 4;
                    ctx.strokeRect(25, 25, 550, 550);
                    ctx.fillStyle = '#f8fafc';
                }
                
                // Draw Quote marks
                ctx.font = '90px Georgia, serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                
                if (style === 'saffron') {
                    ctx.fillStyle = 'rgba(254, 243, 199, 0.15)';
                } else if (style === 'vintage') {
                    ctx.fillStyle = 'rgba(194, 65, 12, 0.08)';
                } else {
                    ctx.fillStyle = 'rgba(234, 88, 12, 0.12)';
                }
                ctx.fillText('“', 300, 130);
                
                // Draw Quote Content
                if (style === 'saffron') {
                    ctx.fillStyle = '#fffbeb';
                } else if (style === 'vintage') {
                    ctx.fillStyle = '#1e293b';
                } else {
                    ctx.fillStyle = '#f1f5f9';
                }
                
                ctx.font = 'italic 25px Georgia, serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                wrapText(ctx, quoteText, 300, 250, 460, 38);
                
                // Draw Watermark
                ctx.font = 'bold 16px "Plus Jakarta Sans", sans-serif';
                if (style === 'saffron') {
                    ctx.fillStyle = '#fef3c7';
                } else if (style === 'vintage') {
                    ctx.fillStyle = '#c2410c';
                } else {
                    ctx.fillStyle = '#ea580c';
                }
                ctx.fillText('— ಹೇಳಿ ಹೋಗು ಕಾರಣ / Heli Hogu Karana', 300, 470);
                
                ctx.font = '13px monospace';
                if (style === 'saffron') {
                    ctx.fillStyle = 'rgba(254, 243, 199, 0.7)';
                } else if (style === 'vintage') {
                    ctx.fillStyle = '#64748b';
                } else {
                    ctx.fillStyle = '#94a3b8';
                }
                ctx.fillText('Instagram: @heli.hogu.kaarana', 300, 510);
            }

            function downloadQuoteCard() {
                const canvas = document.getElementById('quote-canvas');
                const dataURL = canvas.toDataURL("image/png");
                const link = document.createElement('a');
                link.download = 'heli_hogu_karana_quote.png';
                link.href = dataURL;
                link.click();
            }

            function openDownloadModal(edition, format) {
                selectedEdition = edition;
                selectedFormat = format;
                
                const modal = document.getElementById('pw-modal');
                document.getElementById('ebook-pw').value = "";
                document.getElementById('pw-error').style.display = 'none';
                
                modal.style.display = 'flex';
                setTimeout(() => {
                    modal.style.opacity = '1';
                    modal.querySelector('.modal-card').style.transform = 'scale(1)';
                }, 10);
            }

            function closeDownloadModal() {
                const modal = document.getElementById('pw-modal');
                modal.style.opacity = '0';
                modal.querySelector('.modal-card').style.transform = 'scale(0.9)';
                setTimeout(() => {
                    modal.style.display = 'none';
                }, 300);
            }

            async function submitDownload() {
                const pw = document.getElementById('ebook-pw').value.trim();
                const err = document.getElementById('pw-error');
                
                if (!pw) {
                    err.innerText = "Please enter a password.";
                    err.style.display = 'block';
                    return;
                }
                
                try {
                    const testUrl = `/api/download/${selectedEdition}/${selectedFormat}?password=${encodeURIComponent(pw)}`;
                    const resp = await fetch(testUrl, { method: 'GET' });
                    
                    if (resp.status === 200) {
                        window.location.href = testUrl;
                        closeDownloadModal();
                    } else if (resp.status === 401) {
                        err.innerText = "Incorrect password. Please try again.";
                        err.style.display = 'block';
                    } else {
                        err.innerText = "Server error. Please try again later.";
                        err.style.display = 'block';
                    }
                } catch (e) {
                    err.innerText = "Connection failed. Please check your network.";
                    err.style.display = 'block';
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

            async function submitFeedback(event) {
                event.preventDefault();
                
                const name = document.getElementById('fb-name').value.trim();
                const rating = parseInt(document.getElementById('fb-rating').value);
                const comment = document.getElementById('fb-comment').value.trim();
                const submitBtn = document.getElementById('fb-submit-btn');
                const successMsg = document.getElementById('fb-success-msg');
                
                submitBtn.disabled = true;
                submitBtn.innerText = "Submitting...";
                
                try {
                    const response = await fetch('/api/feedback', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ name, rating, comment })
                    });
                    
                    const res = await response.json();
                    if (res.status === 'success') {
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

            // Initialize ratings display on load
            window.addEventListener('DOMContentLoaded', () => {
                renderStars(5);
            });

            let currentText = "";
            let isSpeaking = false;
            let currentAudio = null;
            let isSeeking = false;
            let chatHistory = [];

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
                    const r = await fetch('/chat', { 
                        method: 'POST', 
                        headers: {'Content-Type': 'application/json'}, 
                        body: JSON.stringify({question: q, language: lang, history: chatHistory})
                    });
                    const d = await r.json();
                    
                    // Increment and update local usage count
                    incrementUsage();
                    
                    currentText = d.answer;
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
                    }
                    
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
