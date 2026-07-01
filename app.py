# app.py — Kannada Book AI Agent v2
# Run: kannada-rag-env\Scripts\python.exe -m streamlit run app.py

import sys
from unittest.mock import MagicMock
sys.modules['transformers'] = MagicMock()
sys.modules['torch'] = MagicMock()

import os
import re
import base64
import requests
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import csv
import datetime

# v2: LangChain-backed retrieval with metadata filtering + fallback
from rag_agent_v2 import (
    retrieve_v2,
    detect_page_filter,
    is_page_only_query,
    retrieve_exact_page,
    get_rag_chain,
)

load_dotenv()

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "").strip()

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def save_inline_feedback(feedback_type, assistant_msg, user_msg):
    feedback_file = os.path.join(BASE_DIR, "feedback.csv")
    file_exists = os.path.isfile(feedback_file)
    
    question = user_msg["content"] if user_msg and user_msg["role"] == "user" else "N/A"
    answer = assistant_msg.get("content", "")
    confidence_score = assistant_msg.get("confidence_pct", "N/A")
    pages = assistant_msg.get("pages", [])
    
    with open(feedback_file, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Question", "Generated Answer", "Confidence Score", "Retrieved Pages", "Feedback Type"])
        
        writer.writerow([
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            question,
            answer,
            confidence_score,
            ",".join(map(str, pages)) if pages else "None",
            feedback_type
        ])

def check_and_compile_ebooks():
    ebook_dir = os.path.join(BASE_DIR, "data", "ebooks")
    os.makedirs(ebook_dir, exist_ok=True)
    kn_epub = os.path.join(ebook_dir, "heli_hogu_karana_kannada.epub")
    kn_html = os.path.join(ebook_dir, "heli_hogu_karana_kannada.html")
    
    # Auto-compile if Kannada version is missing
    if not os.path.exists(kn_epub) or not os.path.exists(kn_html):
        try:
            import sys
            # Append scratch directory so compile_ebook functions can be imported
            scratch_path = os.path.join(BASE_DIR, "scratch")
            if scratch_path not in sys.path:
                sys.path.append(scratch_path)
            from compile_ebook import load_pages, find_cover_image, compile_markdown, compile_html, compile_epub
            import base64
            
            kn_dir = os.path.join(BASE_DIR, "data", "normalized_text")
            en_dir = os.path.join(BASE_DIR, "data", "english_translated")
            
            kn_pages = load_pages(kn_dir)
            en_pages = load_pages(en_dir)
            
            if kn_pages:
                cover_path = find_cover_image()
                cover_b64 = None
                if cover_path:
                    with open(cover_path, "rb") as f:
                        cover_b64 = base64.b64encode(f.read()).decode("utf-8")
                
                compile_markdown(kn_pages, en_pages, cover_path, ebook_dir)
                compile_html(kn_pages, en_pages, cover_b64, ebook_dir)
                compile_epub(kn_pages, en_pages, cover_path, ebook_dir)
        except Exception as e:
            print(f"Auto-compilation error: {e}")

check_and_compile_ebooks()

BOOK_CONTEXT = """
Book Title  : ಹೇಳಿ ಹೋಗು ಕಾರಣ (Heli Hogu Karana — "Tell the reason before you go")
Author      : ರವಿ ಬೆಳಗೆರೆ (Ravi Belagere) — prominent Kannada journalist, Bengaluru
Publisher   : Bhavana Prakashan, Bengaluru
Language    : Kannada | Genre: Novel | Pages: 346

Theme: Human morality, guilt, truth-telling, divine justice, moral accountability,
       existential questioning, social critique.
Style: Bold journalistic prose, episodic structure, multiple philosophical perspectives.

Known characters: ಹಿಮವಂತ (Himavant) is the main protagonist. ಪ್ರಾರ್ಥನಾ (Prarthana) is his wife.
"""

GENERAL_PATTERNS = [
    r'what is (this|the) book', r'about (this|the) book',
    r'book (about|summary|theme)', r'who (is|wrote|is the author).*ravi',
    r'ravi belagere', r'author', r'ಪುಸ್ತಕ(ದ|ವು|ದ ಬಗ್ಗೆ)', r'ಕಾದಂಬರಿ',
    r'ರವಿ ಬೆಳಗೆರೆ', r'ವಿಷಯ ಏನು', r'ಯಾರು ಬರೆದ', r'ಮುಖ್ಯ ವಿಷಯ',
    r'summary', r'theme', r'title mean', r'ಶೀರ್ಷಿಕೆ',
]
CHARACTER_PATTERNS = [
    r'himavant', r'prarthana', r'pratana', r'prathana',
    r'ಹಿಮವಂತ', r'ಪ್ರಾರ್ಥನಾ', r'main character', r'protagonist',
    r'ಮುಖ್ಯ ಪಾತ್ರ', r'who is', r'who are', r'character', r'ಪಾತ್ರ',
    r'wife', r'husband', r'ಹೆಂಡತಿ', r'ಗಂಡ', r'relationship',
    r'ಸಂಬಂಧ', r'name of', r'tell me about',
]

def is_general_question(q):
    return any(re.search(p, q, re.IGNORECASE) for p in GENERAL_PATTERNS)

def is_character_question(q):
    return any(re.search(p, q, re.IGNORECASE) for p in CHARACTER_PATTERNS)

def calculate_confidence(chunks):
    if not chunks:
        return 0.0
    avg_score = sum(c.get("score", 0.0) for c in chunks) / len(chunks)
    # Cosine similarity mapping
    if avg_score >= 0.35:
        p = 85 + (avg_score - 0.35) * 23.0 # maps 0.35-1.0 to 85%-100%
    elif avg_score >= 0.25:
        p = 70 + (avg_score - 0.25) * 150.0 # maps 0.25-0.35 to 70%-85%
    else:
        p = 50 + (avg_score - 0.20) * 400.0 # maps 0.20-0.25 to 50%-70%
    return min(100.0, max(0.0, p))

def get_confidence_label(pct: float) -> str:
    if pct >= 85:  return "High"
    if pct >= 70:  return "Medium"
    if pct >= 60:  return "Low"
    return "Very Low"

VERY_LOW_THRESHOLD = 60  # Below this -> skip LLM, show guardrail

GUARDRAIL_MSG_EN = (
    "I could not find sufficient evidence in the novel to answer this question reliably. "
    "The retrieved passages do not contain enough relevant information."
)
GUARDRAIL_MSG_KN = (
    "ಈ ಪ್ರಶ್ನೆಗೆ ಪುಸ್ತಕದಲ್ಲಿ ಸಾಕಷ್ಟು ಆಧಾರ ಸಿಗಲಿಲ್ಲ. "
    "ಪಡೆದ ಭಾಗಗಳಲ್ಲಿ ಸಾಕಷ್ಟು ಮಾಹಿತಿ ಇಲ್ಲ."
)


# ── Page config ───────────────────────────────────────────────────────────────
from PIL import Image
favicon_img = "📚"
try:
    favicon_path = os.path.join(BASE_DIR, "favicon.png")
    if os.path.exists(favicon_path):
        favicon_img = Image.open(favicon_path)
except Exception:
    pass

st.set_page_config(
    page_title="ಹೇಳಿ ಹೋಗು ಕಾರಣ — AI Agent v2",
    page_icon=favicon_img,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    h1, h2, h3 { font-family: 'Outfit', sans-serif; }
    div[data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 15% 50%, #130b29, #09090e 50%, #050a16 100%);
        color: #e2e8f0;
    }
    header[data-testid="stHeader"] { background: transparent !important; }
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    div[data-testid="stSidebar"] {
        background-color: rgba(10, 10, 20, 0.4) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    .block-container { padding-top: 2rem !important; padding-bottom: 5rem !important; }
    div[data-testid="stChatMessage"] {
        background: rgba(20, 20, 35, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 20px;
        padding: 1.5rem 1.75rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        line-height: 1.6;
        font-size: 1.05rem;
    }
    div[data-testid="stChatMessage"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 20px 40px -10px rgba(0,0,0,0.6);
        border-color: rgba(255,255,255,0.08);
    }
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: linear-gradient(145deg, rgba(8,145,178,0.08) 0%, rgba(56,189,248,0.03) 100%);
        border-left: 3px solid #06b6d4;
    }
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background: linear-gradient(145deg, rgba(168,85,247,0.08) 0%, rgba(236,72,153,0.03) 100%);
        border-left: 3px solid #d946ef;
    }
    div[data-testid="stChatInput"] {
        background: rgba(15,15,25,0.7) !important;
        backdrop-filter: blur(24px) saturate(180%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 24px;
        padding: 0.25rem 0.5rem;
        box-shadow: 0 0 40px rgba(139,92,246,0.15), 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: rgba(139,92,246,0.5);
        box-shadow: 0 0 40px rgba(139,92,246,0.3), 0 4px 6px rgba(0,0,0,0.3);
    }
    hr { border-color: rgba(255,255,255,0.06) !important; margin: 2rem 0; }
    h1 {
        background: linear-gradient(to right, #38bdf8, #c084fc, #f472b6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3rem; letter-spacing: -1px; margin-bottom: 0.2rem;
    }
    .stMarkdown p { color: #94a3b8; }
    div[data-testid="stHorizontalBlock"] .stButton > button {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 999px !important;
        padding: 0.3rem 0.9rem !important;
        font-size: 0.8rem !important;
        color: #94a3b8 !important;
        font-weight: 400 !important;
        transition: all 0.2s ease !important;
        white-space: nowrap !important;
    }
    div[data-testid="stHorizontalBlock"] .stButton > button:hover {
        background: rgba(139,92,246,0.15) !important;
        border-color: rgba(139,92,246,0.4) !important;
        color: #c084fc !important;
        box-shadow: 0 0 12px rgba(139,92,246,0.2) !important;
        transform: translateY(-1px) !important;
    }
    div[data-testid="stSidebar"] .stRadio,
    div[data-testid="stSidebar"] .stCheckbox {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 14px !important;
        padding: 0.75rem 1rem !important;
        margin-bottom: 0.5rem !important;
        backdrop-filter: blur(10px) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stSidebar"] .stRadio:hover,
    div[data-testid="stSidebar"] .stCheckbox:hover {
        background: rgba(255,255,255,0.07) !important;
        border-color: rgba(139,92,246,0.4) !important;
        box-shadow: 0 0 15px rgba(139,92,246,0.15) !important;
    }
    div[data-testid="stSidebar"] .stRadio label,
    div[data-testid="stSidebar"] .stCheckbox label {
        color: #e2e8f0 !important; font-weight: 500 !important;
    }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 6px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
    .stButton > button {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.1); border-radius: 12px;
        color: #fff; font-weight: 600; transition: all 0.2s;
    }
    .stButton > button:hover {
        border-color: #8b5cf6;
        box-shadow: 0 0 15px rgba(139,92,246,0.3);
        transform: translateY(-1px);
    }
    .stForm { background: rgba(255,255,255,0.02) !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 20px !important; padding: 1.5rem !important; backdrop-filter: blur(20px) !important; }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea { background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 12px !important; color: #e2e8f0 !important; }
    /* v2 badge */
    .v2-badge {
        display: inline-block;
        background: linear-gradient(135deg, #7c3aed, #2563eb);
        color: white; font-size: 0.65rem; font-weight: 700;
        padding: 2px 8px; border-radius: 999px;
        letter-spacing: 0.05em; vertical-align: middle;
        margin-left: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ── LLM functions (unchanged from v1) ────────────────────────────────────────
def get_best_gemini_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for model in models:
            if "gemini-1.5-flash" in model: return model
        for model in models:
            if "gemini-1.5-pro" in model: return model
        return models[0] if models else "gemini-1.5-flash"
    except Exception:
        return "gemini-1.5-flash"

def call_gemini_llm(messages, retries=1):
    if not GEMINI_API_KEY: return None
    model_name = get_best_gemini_model()
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    system_instr = ""
    chat_contents = []
    for m in messages:
        if m["role"] == "system":
            system_instr = m["content"]
        else:
            role = "user" if m["role"] == "user" else "model"
            chat_contents.append({"role": role, "parts": [{"text": m["content"]}]})
    for attempt in range(retries + 1):
        try:
            model = genai.GenerativeModel(model_name=model_name, system_instruction=system_instr)
            response = model.generate_content(chat_contents, safety_settings=safety_settings)
            if response.candidates and response.candidates[0].content.parts:
                return response.text.strip()
            return None
        except Exception:
            break
    return None

def call_groq_llm(messages, retries=2):
    if not GROQ_API_KEY: return "⚠️ GROQ_API_KEY not set"
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.1, "max_tokens": 800}
    for attempt in range(retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            if resp.status_code == 429 and attempt < retries:
                import time; time.sleep(5); continue
            resp.raise_for_status()
        except Exception as e:
            if attempt < retries: import time; time.sleep(2); continue
            return f"❌ Groq Error: {e}"
    return "❌ Groq rate limit exhausted."

def call_sarvam_llm(messages):
    gemini_resp = call_gemini_llm(messages)
    if gemini_resp: return gemini_resp
    if not SARVAM_API_KEY: return call_groq_llm(messages)
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "sarvam-m", "messages": messages, "temperature": 0.1, "max_tokens": 600}
    try:
        resp = requests.post("https://api.sarvam.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return call_groq_llm(messages)
    except Exception:
        return call_groq_llm(messages)

def call_sarvam_tts(text, language="kn-IN"):
    # Clear page citations from text
    clean = re.sub(r'\[Page \d+\]:', '', text).strip()
    clean = re.sub(r'📄 Sources:.*', '', clean).strip()

    # 1. Try Sarvam TTS first if API Key is configured
    if SARVAM_API_KEY:
        try:
            headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
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
                payload = {"inputs": [chunk.strip()], "target_language_code": language, "speaker": "priya", "model": "bulbul:v3", "pace": 1.0}
                resp = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers, json=payload, timeout=60)
                if resp.status_code == 200:
                    audio_bytes_list.append(base64.b64decode(resp.json()["audios"][0]))
            
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
                return output_wav.getvalue()
        except Exception as e:
            print(f"Sarvam TTS failed: {e}. Falling back to Google TTS.")

    # 2. Fallback to Google TTS (gTTS)
    try:
        from gtts import gTTS
        import io
        gtts_lang = "kn" if "kn" in language.lower() else "en"
        tts = gTTS(text=clean, lang=gtts_lang)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except Exception as e:
        print(f"Google TTS fallback failed: {e}")
        return None

def rewrite_query(current_query, chat_history):
    if not chat_history:
        return current_query
    if detect_page_filter(current_query) != (None, None):
        return current_query
    if is_general_question(current_query):
        return current_query
    if is_character_question(current_query) and not re.search(r'\b(he|she|they|him|her|his|hers|their|theirs|it|ಈ|ಆ|ಅವನು|ಅವಳು|ಅವರು|ಇವನು|ಇವಳು)\b', current_query, re.IGNORECASE):
        return current_query
        
    has_pronoun = bool(re.search(r'\b(he|she|they|him|her|his|hers|their|theirs|it|this|that|ಈ|ಆ|ಅವನು|ಅವಳು|ಅವರು|ಇವನು|ಇವಳು)\b', current_query, re.IGNORECASE))
    is_short = len(current_query.split()) <= 4
    
    if not (has_pronoun or is_short):
        return current_query
        
    history_text = ""
    for msg in chat_history[-6:]:
        if msg["role"] in ["user", "assistant"]:
            content = re.sub(r'\[Page \d+\]:', '', msg["content"]).strip()
            history_text += f"{msg['role'].capitalize()}: {content}\n"
            
    prompt = f"""Given the following conversation history and a new user query, rewrite the user query to be a standalone, clear question that can be understood without the history.
Resolve any pronouns (e.g., he, she, him, her, they) to their specific entity (e.g., character names) mentioned in the history.
Expand vague references (e.g., "Tell me more about him" -> "Tell me more about Himavant in the novel").
If the query is already clear and standalone, return it exactly as is. Do not answer the question. Only output the rewritten query.

Conversation History:
{history_text}

User Query: {current_query}
Rewritten Query:"""

    messages = [{"role": "system", "content": "You are a query rewriting assistant."},
                {"role": "user", "content": prompt}]
    
    rewritten = call_gemini_llm(messages)
    if rewritten:
        return rewritten.strip(' "\'')
    return current_query

def build_prompt(question, chunks, language, use_book_context_only=False):
    rag_section = "" if use_book_context_only else (
        "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks])
        if chunks else "(No specific passages retrieved.)"
    )
    if language == "English":
        return f"""You are an AI assistant for the Kannada novel "Heli Hogu Karana".

BOOK INFORMATION:
{BOOK_CONTEXT}

{"" if use_book_context_only else f"RETRIEVED PASSAGES:{chr(10)}{rag_section}{chr(10)}"}
Answer using the information above. Be informative and cite page numbers when using passages.
If passages say "Not found in document", tell the user clearly.

QUESTION: {question}
ANSWER in English:"""
    else:
        return f"""ನೀವು "ಹೇಳಿ ಹೋಗು ಕಾರಣ" ಕನ್ನಡ ಕಾದಂಬರಿಯ AI ಸಹಾಯಕರು.

ಪುಸ್ತಕದ ಮಾಹಿತಿ:
{BOOK_CONTEXT}

{"" if use_book_context_only else f"ಪುಸ್ತಕದಿಂದ ತೆಗೆದ ವಿಷಯ:{chr(10)}{rag_section}{chr(10)}"}
ಕನ್ನಡದಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರಿಸಿ.

ಪ್ರಶ್ನೆ: {question}
ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರ:"""


# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1>📚 ಹೇಳಿ ಹೋಗು ಕಾರಣ"
    "<span class='v2-badge'>v2</span>"
    "<br><span style='font-size:1.5rem;color:#94a3b8;font-weight:400;'>Premium AI Knowledge Agent</span></h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='margin-bottom:2rem;'>Masterpiece Kannada Novel Intelligence — "
    "Powered by Gemini · Sarvam · Groq · LangChain</p>",
    unsafe_allow_html=True
)

with st.sidebar:
    # ── Language ──────────────────────────────────────────────────────────────
    st.markdown("""<div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:1rem 1.2rem;margin-bottom:0.8rem;backdrop-filter:blur(20px);'>
<p style='color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.6rem;'>⚙️ Settings</p>
</div>""", unsafe_allow_html=True)

    st.markdown("""<div style='background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.2);border-radius:14px;padding:0.6rem 1rem;margin-bottom:0.5rem;backdrop-filter:blur(10px);'><p style='color:#c084fc;font-size:0.8rem;font-weight:600;margin:0;'>🌐 Answer Language</p></div>""", unsafe_allow_html=True)
    language = st.radio("", ["English", "Kannada"], key="lang", label_visibility="collapsed")

    # ── v2: Page Filter ───────────────────────────────────────────────────────
    st.markdown("""<div style='background:rgba(56,189,248,0.08);border:1px solid rgba(56,189,248,0.2);border-radius:14px;padding:0.6rem 1rem;margin-bottom:0.5rem;margin-top:0.3rem;backdrop-filter:blur(10px);'><p style='color:#38bdf8;font-size:0.8rem;font-weight:600;margin:0;'>🔢 Page Filter <span style="font-size:0.7rem;opacity:0.6">(v2)</span></p></div>""", unsafe_allow_html=True)
    page_filter_mode = st.radio(
        "Filter by", ["None", "Exact page", "Page range"],
        key="page_filter_mode", label_visibility="collapsed"
    )
    sidebar_page_exact = None
    sidebar_page_range = None
    if page_filter_mode == "Exact page":
        sidebar_page_exact = st.number_input(
            "Page number", min_value=1, max_value=346, value=1, key="pf_exact"
        )
    elif page_filter_mode == "Page range":
        col_a, col_b = st.columns(2)
        with col_a:
            pf_start = st.number_input("From", min_value=1, max_value=346, value=1, key="pf_start")
        with col_b:
            pf_end = st.number_input("To", min_value=1, max_value=346, value=50, key="pf_end")
        sidebar_page_range = (int(pf_start), int(pf_end))

    # ── Display Options ───────────────────────────────────────────────────────
    st.markdown("""<div style='background:rgba(6,182,212,0.08);border:1px solid rgba(6,182,212,0.2);border-radius:14px;padding:0.6rem 1rem;margin-bottom:0.5rem;margin-top:0.3rem;backdrop-filter:blur(10px);'><p style='color:#38bdf8;font-size:0.8rem;font-weight:600;margin:0;'>🔍 Display Options</p></div>""", unsafe_allow_html=True)
    show_chunks = st.checkbox("Show source chunks", value=False)
    debug_mode  = st.checkbox("🔬 Debug Mode (show reranking scores)", value=False)

    st.markdown("""<div style='background:rgba(236,72,153,0.08);border:1px solid rgba(236,72,153,0.2);border-radius:14px;padding:0.6rem 1rem;margin-bottom:0.5rem;margin-top:0.3rem;backdrop-filter:blur(10px);'><p style='color:#f472b6;font-size:0.8rem;font-weight:600;margin:0;'>🔊 Audio</p></div>""", unsafe_allow_html=True)
    enable_tts = st.checkbox("Read answer aloud (TTS)", value=False)

    # ── E-Book Downloads ──────────────────────────────────────────────────────
    st.markdown("""<div style='background:rgba(168,85,247,0.08);border:1px solid rgba(168,85,247,0.2);border-radius:14px;padding:0.6rem 1rem;margin-bottom:0.5rem;margin-top:0.3rem;backdrop-filter:blur(10px);'><p style='color:#a855f7;font-size:0.8rem;font-weight:600;margin:0;'>📚 Download E-Books</p></div>""", unsafe_allow_html=True)
    
    with st.expander("Available Editions", expanded=False):
        ebook_dir = os.path.join(BASE_DIR, "data", "ebooks")
        kn_dir = os.path.join(BASE_DIR, "data", "normalized_text")
        en_dir = os.path.join(BASE_DIR, "data", "english_translated")
        
        # Calculate progress
        total_pages = 346
        translated_pages = 0
        if os.path.exists(en_dir):
            translated_pages = len([f for f in os.listdir(en_dir) if f.startswith("page_") and f.endswith(".txt")])
            
        progress_pct = int((translated_pages / total_pages) * 100) if total_pages > 0 else 0
        
        # Recompile button
        if st.button("🔄 Recompile Files", use_container_width=True):
            with st.spinner("Compiling e-books..."):
                try:
                    import sys
                    scratch_path = os.path.join(BASE_DIR, "scratch")
                    if scratch_path not in sys.path:
                        sys.path.append(scratch_path)
                    from compile_ebook import load_pages, find_cover_image, compile_markdown, compile_html, compile_epub
                    import base64
                    
                    kn_pages = load_pages(kn_dir)
                    en_pages = load_pages(en_dir)
                    
                    if kn_pages:
                        cover_path = find_cover_image()
                        cover_b64 = None
                        if cover_path:
                            with open(cover_path, "rb") as f:
                                cover_b64 = base64.b64encode(f.read()).decode("utf-8")
                        
                        compile_markdown(kn_pages, en_pages, cover_path, ebook_dir)
                        compile_html(kn_pages, en_pages, cover_b64, ebook_dir)
                        compile_epub(kn_pages, en_pages, cover_path, ebook_dir)
                        st.success("E-books compiled successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Compilation error: {e}")
        
        st.divider()
        
        # 1. Kannada Edition
        st.markdown("**📖 Kannada Edition** (Complete)")
        kn_epub_file = os.path.join(ebook_dir, "heli_hogu_karana_kannada.epub")
        kn_html_file = os.path.join(ebook_dir, "heli_hogu_karana_kannada.html")
        
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(kn_epub_file):
                with open(kn_epub_file, "rb") as f:
                    st.download_button("EPUB format", f, "heli_hogu_karana_kannada.epub", "application/epub+zip", use_container_width=True)
            else:
                st.button("EPUB (N/A)", disabled=True, use_container_width=True)
        with col2:
            if os.path.exists(kn_html_file):
                with open(kn_html_file, "rb") as f:
                    st.download_button("HTML format", f, "heli_hogu_karana_kannada.html", "text/html", use_container_width=True)
            else:
                st.button("HTML (N/A)", disabled=True, use_container_width=True)
                
        # 2. English & Bilingual Edition
        st.divider()
        st.markdown(f"**🇬🇧 English & Bilingual**")
        st.caption(f"Translation Progress: {translated_pages}/{total_pages} pages ({progress_pct}%)")
        if progress_pct < 100:
            st.progress(progress_pct / 100.0)
            
        # English Buttons (allow download of partial translation)
        st.markdown("*English Edition:*")
        en_epub_file = os.path.join(ebook_dir, "heli_hogu_karana_english.epub")
        en_html_file = os.path.join(ebook_dir, "heli_hogu_karana_english.html")
        
        col_en1, col_en2 = st.columns(2)
        with col_en1:
            if os.path.exists(en_epub_file):
                with open(en_epub_file, "rb") as f:
                    st.download_button("EPUB", f, "heli_hogu_karana_english.epub", "application/epub+zip", use_container_width=True, key="dl_en_epub")
            else:
                st.button("EPUB (N/A)", disabled=True, use_container_width=True, key="dl_en_epub_na")
        with col_en2:
            if os.path.exists(en_html_file):
                with open(en_html_file, "rb") as f:
                    st.download_button("HTML", f, "heli_hogu_karana_english.html", "text/html", use_container_width=True, key="dl_en_html")
            else:
                st.button("HTML (N/A)", disabled=True, use_container_width=True, key="dl_en_html_na")
                
        # Bilingual Buttons
        st.markdown("*Bilingual (Side-by-Side):*")
        bi_epub_file = os.path.join(ebook_dir, "heli_hogu_karana_bilingual.epub")
        bi_html_file = os.path.join(ebook_dir, "heli_hogu_karana_bilingual.html")
        
        col_bi1, col_bi2 = st.columns(2)
        with col_bi1:
            if os.path.exists(bi_epub_file):
                with open(bi_epub_file, "rb") as f:
                    st.download_button("EPUB", f, "heli_hogu_karana_bilingual.epub", "application/epub+zip", use_container_width=True, key="dl_bi_epub")
            else:
                st.button("EPUB (N/A)", disabled=True, use_container_width=True, key="dl_bi_epub_na")
        with col_bi2:
            if os.path.exists(bi_html_file):
                with open(bi_html_file, "rb") as f:
                    st.download_button("HTML", f, "heli_hogu_karana_bilingual.html", "text/html", use_container_width=True, key="dl_bi_html")
            else:
                st.button("HTML (N/A)", disabled=True, use_container_width=True, key="dl_bi_html_na")

    st.markdown("""
<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:0.8rem 1rem;margin-top:0.8rem;backdrop-filter:blur(10px);'>
<p style='color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;'>📖 About</p>
<p style='color:#64748b;font-size:0.85rem;margin:0;'><em>ಹೇಳಿ ಹೋಗು ಕಾರಣ</em> by Ravi Belagere — Kannada novel</p>
</div>
<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:0.8rem 1rem;margin-top:0.5rem;backdrop-filter:blur(10px);'>
<p style='color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;'>📊 Stats</p>
<p style='color:#64748b;font-size:0.85rem;margin:0;'>346 pages · 687 chunks · v2 RAG</p>
</div>
<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:0.8rem 1rem;margin-top:0.5rem;backdrop-filter:blur(10px);'>
<p style='color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;'>💡 Try asking</p>
<p style='color:#64748b;font-size:0.82rem;margin:0;line-height:1.7;'>Who is Himavant?<br>What is in pages 10 to 30?<br>What is in page 50?<br>ಹಿಮವಂತ ಯಾರು?<br>ಈ ಪುಸ್ತಕದ ವಿಷಯ ಏನು?</p>
</div>
""", unsafe_allow_html=True)


# ── Chat history ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg.get("original_query") and msg.get("rewritten_query") and debug_mode:
            st.markdown("**Original Query:**")
            st.markdown(f"> \"{msg['original_query']}\"")
            st.markdown("**Rewritten Query:**")
            st.markdown(f"> \"{msg['rewritten_query']}\"")
            
        st.write(msg["content"])
        if msg.get("confidence_pct") is not None:
            pct = msg["confidence_pct"]
            lbl = msg["confidence_label"]
            if not msg.get("deterministic"):
                conf_color = "#22c55e" if pct >= 85 else ("#f59e0b" if pct >= 70 else ("#f97316" if pct >= 60 else "#ef4444"))
                st.markdown(
                    f"<span style='font-weight:600;color:{conf_color};'>Confidence: {lbl} ({int(pct)}%)</span>",
                    unsafe_allow_html=True
                )
            if msg.get("guardrail"):
                st.markdown("""
<div style='background:rgba(239,68,68,0.10);border:1px solid rgba(239,68,68,0.35);
            border-left:4px solid #ef4444;border-radius:12px;padding:0.8rem 1.1rem;
            margin:0.5rem 0;backdrop-filter:blur(8px);'>
  <p style='color:#fca5a5;font-weight:700;margin:0 0 0.3rem 0;font-size:0.95rem;'>&#9888; Low Evidence</p>
  <p style='color:#fecaca;margin:0;font-size:0.88rem;'>Retrieved passages may not contain enough information.</p>
</div>""", unsafe_allow_html=True)
            elif pct < 70 and not msg.get("deterministic"):
                st.warning("Low confidence: Retrieved evidence may be insufficient.")
        if msg.get("pages"):
            st.caption(f"📄 Sources: Pages {', '.join(map(str, msg['pages']))}")
        if msg.get("snippets"):
            st.markdown("**Sources:**")
            for snip in msg["snippets"]:
                st.markdown(f"**Page {snip['page']}:**  \n> \"{snip['text']}\"")
        if msg.get("audio"):
            st.audio(msg["audio"])
            
        if msg["role"] == "assistant":
            if not msg.get("inline_feedback_submitted"):
                col1, col2, _ = st.columns([1, 1, 8])
                with col1:
                    if st.button("👍 Helpful", key=f"helpful_{i}"):
                        user_msg = st.session_state.messages[i-1] if i > 0 else None
                        save_inline_feedback("Helpful", msg, user_msg)
                        msg["inline_feedback_submitted"] = True
                        st.rerun()
                with col2:
                    if st.button("👎 Not Helpful", key=f"not_helpful_{i}"):
                        user_msg = st.session_state.messages[i-1] if i > 0 else None
                        save_inline_feedback("Not Helpful", msg, user_msg)
                        msg["inline_feedback_submitted"] = True
                        st.rerun()
            else:
                st.caption("Thank you for your feedback.")

# ── Suggestion chips ──────────────────────────────────────────────────────────
CHIPS = [
    "What is this book about?",
    "Who is Himavant?",
    "Who is Prarthana?",
    "What is in page 50?",
    "ಹಿಮವಂತ ಯಾರು?",
    "ಕಾದಂಬರಿ ವಿಷಯ ಏನು?",
]
if "chip_question" not in st.session_state:
    st.session_state.chip_question = None

chip_cols = st.columns(len(CHIPS))
for i, chip in enumerate(CHIPS):
    with chip_cols[i]:
        if st.button(chip, key=f"chip_{i}"):
            st.session_state.chip_question = chip

question = st.chat_input("Ask about the book... (ಪ್ರಶ್ನೆ ಕೇಳಿ...)")
if st.session_state.chip_question:
    question = st.session_state.chip_question
    st.session_state.chip_question = None

# ── Main answer loop ──────────────────────────────────────────────────────────
if question:
    current_lang = st.session_state.get("lang", "English")
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        progress = st.progress(0, text="🔍 Searching book...")
        try:
            # ── v2: exact page bypass check ──────────────────────────────────
            auto_page, auto_range = detect_page_filter(question)
            page_only = is_page_only_query(question) if auto_page else False

            # Sidebar filter overrides auto-detection
            final_page  = sidebar_page_exact if sidebar_page_exact else auto_page
            final_range = sidebar_page_range if sidebar_page_range else auto_range
            if final_page:
                final_range = None
            
            if page_only and final_page:
                progress.progress(20, text=f"📖 Retrieving exact page {final_page}...")
                rewritten_q = question
                is_rewritten = False
                chunks = retrieve_exact_page(final_page)
                fallback_msg = "" if chunks else f"Page {final_page} not found in the book."
                retrieval_meta = {"fetched": len(chunks), "final": len(chunks), "exact_page": True}
                general = False
                is_char = False
            else:
                progress.progress(10, text="✍️ Rewriting query...")
                rewritten_q = rewrite_query(question, st.session_state.messages[:-1])
                is_rewritten = (rewritten_q.lower() != question.lower())
                
                progress.progress(20, text="📖 Retrieving passages...")
                general = is_general_question(rewritten_q)
                is_char = is_character_question(rewritten_q)
                
                # Update auto-detect just in case rewrite stripped it but sidebar didn't
                # Actually, we rely on original question for auto_page, but fallback to rewritten for edge cases
                if not auto_page and not auto_range:
                    ap, ar = detect_page_filter(rewritten_q)
                    if not sidebar_page_exact: final_page = ap
                    if not sidebar_page_range: final_range = ar
                    if final_page: final_range = None

                chunks, fallback_msg, retrieval_meta = retrieve_v2(
                    query        = rewritten_q,
                    page         = final_page if not general else None,
                    page_range   = final_range if not general else None,
                    is_character = is_char,
                    language     = current_lang,
                )

            # ── v2: explicit NOT FOUND fallback ──────────────────────────────
            if fallback_msg and not general:
                progress.empty()
                st.warning(fallback_msg)
                st.session_state.messages.append({
                    "role": "assistant", "content": fallback_msg,
                    "pages": [], "audio": None
                })
                st.stop()

            # Cap context for free-tier LLMs
            capped, cur_len = [], 0
            for c in chunks:
                if cur_len + len(c["text"]) > 5000: break
                capped.append(c); cur_len += len(c["text"])
            chunks = capped

            progress.progress(55, text="Organizing context...")

            # ── Compute confidence BEFORE LLM (guardrail decision) ───────────
            confidence_pct   = calculate_confidence(chunks) if not general else 100.0
            confidence_label = get_confidence_label(confidence_pct)
            # Suppress guardrail for deterministic paths
            is_very_low      = (confidence_pct < VERY_LOW_THRESHOLD) and not general and chunks and not (final_page or final_range or page_only)
            guardrail_msg    = GUARDRAIL_MSG_EN if current_lang == "English" else GUARDRAIL_MSG_KN

            if is_very_low:
                # ── GUARDRAIL: skip LLM, return insufficient-evidence message ─
                progress.progress(100, text="Done!")
                progress.empty()

                # Confidence badge
                conf_color = "#ef4444"
                st.markdown(
                    f"<span style='font-weight:600;color:{conf_color};'>Confidence: {confidence_label} ({int(confidence_pct)}%)</span>",
                    unsafe_allow_html=True
                )

                # Low Evidence warning card
                st.markdown(f"""
<div style='background:rgba(239,68,68,0.10);border:1px solid rgba(239,68,68,0.35);
            border-left:4px solid #ef4444;border-radius:12px;padding:0.9rem 1.2rem;
            margin:0.5rem 0;backdrop-filter:blur(8px);'>
  <p style='color:#fca5a5;font-weight:700;margin:0 0 0.4rem 0;font-size:1rem;'>&#9888; Low Evidence</p>
  <p style='color:#fecaca;margin:0 0 0.5rem 0;font-size:0.88rem;'>Retrieved passages may not contain enough information.</p>
  <p style='color:#f8fafc;margin:0;font-size:0.92rem;'>{guardrail_msg}</p>
</div>""", unsafe_allow_html=True)

                # Still show sources
                pages = sorted(set(c["page"] for c in chunks)) if chunks else []
                msg_snippets = []
                if pages:
                    st.caption(f"Sources: Pages {', '.join(map(str, pages))}")
                    st.markdown("**Sources:**")
                    for p in pages:
                        pg_chunks = [c for c in chunks if c["page"] == p]
                        if pg_chunks:
                            best = max(pg_chunks, key=lambda x: x.get("score", 0))
                            snippet = best["text"][:150] + "..." if len(best["text"]) > 150 else best["text"]
                            msg_snippets.append({"page": p, "text": snippet})
                            st.markdown(f"**Page {p}:**  \n> \"{snippet}\"")

                if show_chunks and chunks:
                    with st.expander("Source chunks"):
                        for c in chunks:
                            score_str = f"cosine: {c['score']}"
                            if debug_mode and "rerank_score" in c:
                                score_str += f" | reranker: {c['rerank_score']:.4f}"
                            st.markdown(f"**Page {c['page']}** ({score_str})")
                            st.text(c["text"][:300])
                            st.divider()

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": guardrail_msg,
                    "pages": pages,
                    "snippets": msg_snippets,
                    "confidence_pct": confidence_pct,
                    "confidence_label": confidence_label,
                    "guardrail": True,
                    "audio": None,
                    "original_query": question if is_rewritten else None,
                    "rewritten_query": rewritten_q if is_rewritten else None
                })
                st.stop()

            # ── Normal path: confidence is sufficient, call LLM ──────────────
            rag_section = (
                "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks])
                if chunks else "(No specific passages retrieved.)"
            )

            # Construct history as LangChain messages
            from langchain_core.messages import HumanMessage, AIMessage
            history = []
            for msg in st.session_state.messages[-5:-1]:
                if msg["role"] == "user":
                    history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    clean = re.sub(r'\[Page \d+\]:', '', msg["content"]).strip()
                    history.append(AIMessage(content=clean))

            progress.progress(75, text="Generating answer...")
            chain = get_rag_chain(current_lang, is_page_summary=page_only)
            answer = chain.invoke({
                "book_context": BOOK_CONTEXT,
                "context": rag_section,
                "history": history,
                "question": rewritten_q
            })
            progress.progress(100, text="Done!")
            progress.empty()

            if debug_mode:
                if page_only:
                    st.markdown("**Page Query Router Debug:**")
                    st.code(f"Page Query Detected: Yes\nRequested Page: {final_page}\nChunks Retrieved: {len(chunks)}\nRouter Path: Metadata Filter", language="text")
                elif is_rewritten:
                    st.markdown("**Original Query:**")
                    st.markdown(f"> \"{question}\"")
                    st.markdown("**Rewritten Query:**")
                    st.markdown(f"> \"{rewritten_q}\"")

            pages = sorted(set(c["page"] for c in chunks)) if chunks else []
            st.write(answer)

            # Display confidence (already computed above)
            if page_only:
                page_status = "Success" if chunks else "Failed"
                conf_color = "#22c55e" if chunks else "#ef4444"
                st.markdown(
                    f"<span style='font-weight:600;color:{conf_color};'>Page Retrieval: {page_status}</span>",
                    unsafe_allow_html=True
                )
            elif not general and chunks and not (final_page or final_range or page_only):
                conf_color = "#22c55e" if confidence_pct >= 85 else ("#f59e0b" if confidence_pct >= 70 else ("#f97316" if confidence_pct >= 60 else "#ef4444"))
                st.markdown(
                    f"<span style='font-weight:600;color:{conf_color};'>Confidence: {confidence_label} ({int(confidence_pct)}%)</span>",
                    unsafe_allow_html=True
                )
                if confidence_pct < 70:
                    st.warning("Low confidence: Retrieved evidence may be insufficient.")
            
            msg_snippets = []
            if pages:
                page_info = ""
                if final_range:
                    page_info = f" (filtered: pages {final_range[0]}–{final_range[1]})"
                elif final_page:
                    page_info = f" (filtered: page {final_page})"
                st.caption(f"📄 Sources: Pages {', '.join(map(str, pages))}{page_info}")
                
                st.markdown("**Sources:**")
                for p in pages:
                    pg_chunks = [c for c in chunks if c["page"] == p]
                    if pg_chunks:
                        best_chunk = max(pg_chunks, key=lambda x: x.get("score", 0))
                        snippet = best_chunk["text"][:150] + "..." if len(best_chunk["text"]) > 150 else best_chunk["text"]
                        msg_snippets.append({"page": p, "text": snippet})
                        st.markdown(f"**Page {p}:**  \n> \"{snippet}\"")
            elif general:
                st.caption("📖 Answer based on book knowledge")

            if show_chunks and chunks:
                with st.expander("📑 Source chunks"):
                    # Retrieval stats header
                    if "merged_fetched" in retrieval_meta:
                        st.markdown("**Hybrid Retrieval Stats**")
                        st.markdown(f"- Vector Chunks: {retrieval_meta.get('vector_fetched', 0)}")
                        st.markdown(f"- BM25 Chunks: {retrieval_meta.get('bm25_fetched', 0)}")
                        st.markdown(f"- Merged Chunks: {retrieval_meta.get('merged_fetched', 0)}")
                        st.markdown(f"- Reranked Chunks: {retrieval_meta.get('final', 0)}")
                        st.divider()
                    elif retrieval_meta.get("reranked"):
                        st.markdown(
                            f"📥 **Retrieval:** {retrieval_meta['fetched']} chunks fetched &nbsp;→&nbsp; "
                            f"✅ **After Re-ranking:** Top {retrieval_meta['final']} selected",
                            unsafe_allow_html=True
                        )
                        st.divider()
                    for c in chunks:
                        score_str = f"cosine: {c.get('score', 0)}"
                        if debug_mode and "rrf_score" in c:
                            score_str += f" | rrf: {c['rrf_score']:.4f}"
                        if debug_mode and "rerank_score" in c:
                            score_str += f" | reranker: {c['rerank_score']:.4f}"
                        st.markdown(f"**Page {c['page']}** ({score_str})")
                        st.text(c["text"][:300])
                        st.divider()

            audio_bytes = None
            if enable_tts and answer:
                tts_lang = "kn-IN" if current_lang == "Kannada" else "en-IN"
                try:
                    audio_bytes = call_sarvam_tts(answer, tts_lang)
                    if audio_bytes:
                        st.audio(audio_bytes)
                except Exception as e:
                    st.warning(f"TTS error: {e}")

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "pages": pages,
                "snippets": msg_snippets,
                "confidence_pct": confidence_pct if not general and chunks else None,
                "confidence_label": confidence_label if not general and chunks else None,
                "guardrail": False,
                "deterministic": bool(final_page or final_range or page_only),
                "audio": audio_bytes,
                "original_query": question if is_rewritten else None,
                "rewritten_query": rewritten_q if is_rewritten else None
            })

        except Exception as e:
            progress.empty()
            st.error(f"Error: {e}")

if st.session_state.messages:
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ── Feedback ──────────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("💬 Share Feedback", expanded=False):
    st.markdown("<p style='color:#64748b;font-size:0.85rem;margin-bottom:1rem;'>Help us improve — anonymous & appreciated</p>", unsafe_allow_html=True)
    with st.form("feedback_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            feedback_name = st.text_input("Your name (optional)", placeholder="Anonymous")
        with col2:
            feedback_rating = st.selectbox("Rating", ["⭐⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐", "⭐"])
        feedback_text = st.text_area("Your feedback", placeholder="What did you like? What can be improved?", height=100)
        submitted = st.form_submit_button("Submit Feedback ✨")
        if submitted and feedback_text.strip():
            import json, datetime
            feedback_file = os.path.join(BASE_DIR, "feedback.json")
            try:
                with open(feedback_file, "r", encoding="utf-8") as f:
                    all_feedback = json.load(f)
            except:
                all_feedback = []
            all_feedback.append({
                "name": feedback_name.strip() or "Anonymous",
                "rating": feedback_rating,
                "feedback": feedback_text.strip(),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            with open(feedback_file, "w", encoding="utf-8") as f:
                json.dump(all_feedback, f, ensure_ascii=False, indent=2)
            st.success("✅ Thank you!")
        elif submitted:
            st.warning("Please write something before submitting.")

# ── Admin ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.divider()
    st.markdown("**🔐 Admin**")
    admin_pass = st.text_input("Admin password", type="password", key="admin_pass")
    if admin_pass == os.getenv("ADMIN_PASSWORD", "amruth123"):
        import json
        feedback_file = os.path.join(BASE_DIR, "feedback.json")
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                all_feedback = json.load(f)
            st.markdown(f"**{len(all_feedback)} responses**")
            for fb in reversed(all_feedback):
                st.markdown(f"**{fb['rating']}** — *{fb['name']}*  \n{fb['feedback']}  \n<small style='color:#475569'>{fb['timestamp']}</small>", unsafe_allow_html=True)
                st.divider()
        except:
            st.info("No feedback yet.")

        st.divider()
        st.markdown("**📊 Inline Feedback Analytics**")
        csv_file = os.path.join(BASE_DIR, "feedback.csv")
        if os.path.exists(csv_file):
            try:
                import csv
                total = 0
                helpful = 0
                with open(csv_file, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        total += 1
                        if row.get("Feedback Type") == "Helpful":
                            helpful += 1
                
                not_helpful = total - helpful
                pct = (helpful / total * 100) if total > 0 else 0
                
                st.markdown(f"- **Total Feedback**: {total}")
                st.markdown(f"- **Helpful Count**: {helpful}")
                st.markdown(f"- **Not Helpful Count**: {not_helpful}")
                st.markdown(f"- **Helpful Percentage**: {pct:.1f}%")
            except Exception as e:
                st.error(f"Error reading feedback: {e}")
        else:
            st.info("No inline feedback yet.")