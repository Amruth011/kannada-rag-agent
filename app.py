# app.py — Kannada Book AI Agent v2
# Run: kannada-rag-env\Scripts\python.exe -m streamlit run app.py

import os
import re
import base64
import requests
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# v2: LangChain-backed retrieval with metadata filtering + fallback
from rag_agent_v2 import (
    retrieve_v2,
    detect_page_filter,
    NOT_FOUND_MSG,
)

load_dotenv()

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "").strip()

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ಹೇಳಿ ಹೋಗು ಕಾರಣ — AI Agent v2",
    page_icon="📚",
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
    if not SARVAM_API_KEY: return None
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
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
        payload = {"inputs": [chunk.strip()], "target_language_code": language, "speaker": "priya", "model": "bulbul:v3", "pace": 1.0}
        resp = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers, json=payload, timeout=60)
        if resp.status_code == 200:
            audio_bytes_list.append(base64.b64decode(resp.json()["audios"][0]))
    if not audio_bytes_list: return None
    import wave, io
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

    st.markdown("""<div style='background:rgba(236,72,153,0.08);border:1px solid rgba(236,72,153,0.2);border-radius:14px;padding:0.6rem 1rem;margin-bottom:0.5rem;margin-top:0.3rem;backdrop-filter:blur(10px);'><p style='color:#f472b6;font-size:0.8rem;font-weight:600;margin:0;'>🔊 Audio</p></div>""", unsafe_allow_html=True)
    enable_tts = st.checkbox("Read answer aloud (TTS)", value=False)

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

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("pages"):
            st.caption(f"📄 Sources: Pages {', '.join(map(str, msg['pages']))}")
        if msg.get("audio"):
            st.audio(msg["audio"], format="audio/wav")

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
            progress.progress(20, text="📖 Retrieving passages...")
            general = is_general_question(question)
            is_char = is_character_question(question)

            # ── v2: metadata-filtered retrieval ──────────────────────────────
            auto_page, auto_range = detect_page_filter(question)

            # Sidebar filter overrides auto-detection
            final_page  = sidebar_page_exact if sidebar_page_exact else auto_page
            final_range = sidebar_page_range if sidebar_page_range else auto_range
            # Clear range if exact page set
            if final_page:
                final_range = None

            chunks, fallback_msg = retrieve_v2(
                query        = question,
                page         = final_page if not general else None,
                page_range   = final_range if not general else None,
                is_character = is_char,
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

            progress.progress(55, text="🧠 Building prompt...")
            prompt = build_prompt(question, chunks, current_lang,
                                  use_book_context_only=(general and not chunks))

            chat_history = []
            for msg in st.session_state.messages[-5:-1]:
                if msg["role"] in ["user", "assistant"]:
                    clean = re.sub(r'\[Page \d+\]:', '', msg["content"]).strip()
                    chat_history.append({"role": msg["role"], "content": clean})
            chat_history.append({"role": "user", "content": prompt})

            progress.progress(75, text="✨ Generating answer...")
            answer = call_sarvam_llm(chat_history)
            progress.progress(100, text="Done!")
            progress.empty()

            pages = sorted(set(c["page"] for c in chunks)) if chunks else []
            st.write(answer)
            if pages:
                page_info = ""
                if final_range:
                    page_info = f" (filtered: pages {final_range[0]}–{final_range[1]})"
                elif final_page:
                    page_info = f" (filtered: page {final_page})"
                st.caption(f"📄 Sources: Pages {', '.join(map(str, pages))}{page_info}")
            elif general:
                st.caption("📖 Answer based on book knowledge")

            if show_chunks and chunks:
                with st.expander("📑 Source chunks"):
                    for c in chunks:
                        st.markdown(f"**Page {c['page']}** (score: {c['score']})")
                        st.text(c["text"][:300])
                        st.divider()

            audio_bytes = None
            if enable_tts and answer and SARVAM_API_KEY:
                tts_lang = "kn-IN" if current_lang == "Kannada" else "en-IN"
                try:
                    audio_bytes = call_sarvam_tts(answer, tts_lang)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/wav")
                except Exception as e:
                    st.warning(f"TTS error: {e}")

            st.session_state.messages.append({
                "role": "assistant", "content": answer,
                "pages": pages, "audio": audio_bytes
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