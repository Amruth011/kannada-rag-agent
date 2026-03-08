# app.py — Kannada Book AI Agent
# Run: kannada-rag-env\Scripts\python.exe -m streamlit run app.py

import os
import re
import base64
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
CHROMA_DIR     = os.path.join(BASE_DIR, "chroma_db")
COLLECTION     = "kannada_book"
MODEL_NAME     = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

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

def is_general_question(q):
    return any(re.search(p, q, re.IGNORECASE) for p in GENERAL_PATTERNS)

def is_character_question(q):
    return any(re.search(p, q, re.IGNORECASE) for p in CHARACTER_PATTERNS)

st.set_page_config(
    page_title="ಹೇಳಿ ಹೋಗು ಕಾರಣ — AI Agent",
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
        transition: all 0.3s ease;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: rgba(139,92,246,0.5);
        box-shadow: 0 0 40px rgba(139,92,246,0.3), 0 4px 6px rgba(0,0,0,0.3);
    }
    hr { border-color: rgba(255,255,255,0.06) !important; margin: 2rem 0; }
    h1 {
        background: linear-gradient(to right, #38bdf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 3rem;
        letter-spacing: -1px;
        margin-bottom: 0.2rem;
    }
    .stMarkdown p { color: #94a3b8; }

    /* Suggestion chips */
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

    /* Glass effect for sidebar widgets */
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
        color: #e2e8f0 !important;
        font-weight: 500 !important;
    }
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 6px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
    .stButton > button {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        color: #fff;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stForm { background: rgba(255,255,255,0.02) !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 20px !important; padding: 1.5rem !important; backdrop-filter: blur(20px) !important; }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div { background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 12px !important; color: #e2e8f0 !important; }
    .stButton > button:hover {
        border-color: #8b5cf6;
        box-shadow: 0 0 15px rgba(139,92,246,0.3);
        transform: translateY(-1px);
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_agent():
    from sentence_transformers import SentenceTransformer
    import chromadb
    embed_model = SentenceTransformer(MODEL_NAME)
    client      = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        collection = client.get_collection(COLLECTION)
    except Exception:
        collection = client.get_or_create_collection(
            COLLECTION, metadata={"hnsw:space": "cosine"}
        )
    return embed_model, collection

def retrieve(query, embed_model, collection, top_k=5):
    qe      = embed_model.encode([query])[0].tolist()
    results = collection.query(query_embeddings=[qe], n_results=top_k)
    chunks  = []
    for i, doc in enumerate(results["documents"][0]):
        score = 1 - results["distances"][0][i]
        if score >= 0.25:
            chunks.append({
                "text" : doc,
                "page" : results["metadatas"][0][i]["page"],
                "score": round(score, 3)
            })
    return chunks

def retrieve_character(query, embed_model, collection):
    """Higher recall retrieval for character questions — more chunks, lower threshold."""
    qe      = embed_model.encode([query])[0].tolist()
    results = collection.query(query_embeddings=[qe], n_results=10)
    chunks  = []
    for i, doc in enumerate(results["documents"][0]):
        score = 1 - results["distances"][0][i]
        if score >= 0.20:
            chunks.append({
                "text" : doc,
                "page" : results["metadatas"][0][i]["page"],
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
    # ✅ FIXED auth header
    headers = {
        "Authorization": f"Bearer {SARVAM_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model"      : "sarvam-m",
        "messages"   : messages,
        "temperature": 0.1,
        "max_tokens" : 600
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
    # ✅ FIXED auth header
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
            "inputs"              : [chunk.strip()],
            "target_language_code": language,
            "speaker"             : "priya",
            "model"               : "bulbul:v3",
            "pace"                : 1.0
        }
        resp = requests.post(
            "https://api.sarvam.ai/text-to-speech",
            headers=headers, json=payload, timeout=60
        )
        if resp.status_code == 200:
            audio_bytes_list.append(base64.b64decode(resp.json()["audios"][0]))

    if not audio_bytes_list:
        return None

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

# ── UI ───────────────────────────────────────────────
st.markdown("<h1>📚 ಹೇಳಿ ಹೋಗು ಕಾರಣ<br><span style='font-size: 1.5rem; color: #94a3b8; font-weight: 400;'>Premium AI Knowledge Agent</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='margin-bottom: 2rem;'>Masterpiece Kannada Novel Intelligence — Powered by Sarvam & EasyOCR</p>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
<div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:1rem 1.2rem;margin-bottom:0.8rem;backdrop-filter:blur(20px);box-shadow:0 4px 20px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.06);'>
<p style='color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.6rem;'>⚙️ Settings</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("""<div style='background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.2);border-radius:14px;padding:0.6rem 1rem;margin-bottom:0.5rem;backdrop-filter:blur(10px);'><p style='color:#c084fc;font-size:0.8rem;font-weight:600;margin:0;'>🌐 Answer Language</p></div>""", unsafe_allow_html=True)
    language    = st.radio("", ["English", "Kannada"], key="lang", label_visibility="collapsed")

    st.markdown("""<div style='background:rgba(6,182,212,0.08);border:1px solid rgba(6,182,212,0.2);border-radius:14px;padding:0.6rem 1rem;margin-bottom:0.5rem;margin-top:0.3rem;backdrop-filter:blur(10px);'><p style='color:#38bdf8;font-size:0.8rem;font-weight:600;margin:0;'>🔍 Display Options</p></div>""", unsafe_allow_html=True)
    show_chunks = st.checkbox("Show source chunks", value=False)

    st.markdown("""<div style='background:rgba(236,72,153,0.08);border:1px solid rgba(236,72,153,0.2);border-radius:14px;padding:0.6rem 1rem;margin-bottom:0.5rem;margin-top:0.3rem;backdrop-filter:blur(10px);'><p style='color:#f472b6;font-size:0.8rem;font-weight:600;margin:0;'>🔊 Audio</p></div>""", unsafe_allow_html=True)
    enable_tts  = st.checkbox("Read answer aloud (TTS)", value=False)

    st.markdown("""
<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:0.8rem 1rem;margin-top:0.8rem;backdrop-filter:blur(10px);'>
<p style='color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;'>📖 About</p>
<p style='color:#64748b;font-size:0.85rem;margin:0;'><em>ಹೇಳಿ ಹೋಗು ಕಾರಣ</em> by Ravi Belagere — a Kannada novel.</p>
</div>
<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:0.8rem 1rem;margin-top:0.5rem;backdrop-filter:blur(10px);'>
<p style='color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;'>📊 Stats</p>
<p style='color:#64748b;font-size:0.85rem;margin:0;'>346 pages · 687 chunks · Sarvam AI</p>
</div>
<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:0.8rem 1rem;margin-top:0.5rem;backdrop-filter:blur(10px);'>
<p style='color:#94a3b8;font-size:0.75rem;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;'>💡 Try asking</p>
<p style='color:#64748b;font-size:0.82rem;margin:0;line-height:1.7;'>Who is Himavant?<br>Who is Prarthana?<br>What is in page 50?<br>ಹಿಮವಂತ ಯಾರು?<br>ಈ ಪುಸ್ತಕದ ವಿಷಯ ಏನು?</p>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("pages"):
            st.caption(f"📄 Sources: Pages {', '.join(map(str, msg['pages']))}")
        if msg.get("audio"):
            st.audio(msg["audio"], format="audio/wav")

# ── SUGGESTED QUESTION CHIPS ──────────────────────────
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

# Use chip question if clicked
if st.session_state.chip_question:
    question = st.session_state.chip_question
    st.session_state.chip_question = None

if question:
    current_lang = st.session_state.get("lang", "English")
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        progress = st.progress(0, text="🔍 Searching book...")
        try:
                embed_model, collection = load_agent()
                progress.progress(25, text="📖 Retrieving passages...")
                general  = is_general_question(question)
                page_num = detect_page_query(question)
                chunks   = []

                if page_num:
                    chunks = retrieve_by_page(page_num, collection)
                    if not chunks:
                        chunks = retrieve(question, embed_model, collection)
                elif is_character_question(question):
                    # Use RAG — no hardcoding, answer from actual book chunks
                    chunks = retrieve_character(question, embed_model, collection)
                elif not general:
                    chunks = retrieve(question, embed_model, collection)

                progress.progress(55, text="🧠 Building prompt...")
                prompt = build_prompt(question, chunks, current_lang,
                                      use_book_context_only=(general and not chunks))

                chat_history = []
                for msg in st.session_state.messages[-5:-1]:
                    if msg["role"] in ["user", "assistant"]:
                        clean_content = re.sub(r'\[Page \d+\]:', '', msg["content"]).strip()
                        chat_history.append({"role": msg["role"], "content": clean_content})
                chat_history.append({"role": "user", "content": prompt})

                progress.progress(75, text="✨ Generating answer...")
                answer = call_sarvam_llm(chat_history)
                progress.progress(100, text="Done!")
                progress.empty()
                pages  = sorted(set(c["page"] for c in chunks)) if chunks else []

                st.write(answer)
                if pages:
                    st.caption(f"📄 Sources: Pages {', '.join(map(str, pages))}")
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
                    "role"   : "assistant",
                    "content": answer,
                    "pages"  : pages,
                    "audio"  : audio_bytes
                })

        except Exception as e:
            progress.empty()
            st.error(f"Error: {e}")

if st.session_state.messages:
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ── FEEDBACK SECTION ─────────────────────────────────
st.markdown("---")
with st.expander("💬 Share Feedback", expanded=False):
    st.markdown("""
<p style='color: #64748b; font-size: 0.85rem; margin-bottom: 1rem;'>Help us improve — your feedback is anonymous and appreciated</p>
""", unsafe_allow_html=True)
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
                "name"     : feedback_name.strip() or "Anonymous",
                "rating"   : feedback_rating,
                "feedback" : feedback_text.strip(),
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            with open(feedback_file, "w", encoding="utf-8") as f:
                json.dump(all_feedback, f, ensure_ascii=False, indent=2)
            st.success("✅ Thank you for your feedback!")
        elif submitted:
            st.warning("Please write something before submitting.")

# ── ADMIN FEEDBACK VIEWER (private) ──────────────────
with st.sidebar:
    st.divider()
    st.markdown("**🔒 Admin**")
    admin_pass = st.text_input("Admin password", type="password", key="admin_pass")
    if admin_pass == os.getenv("ADMIN_PASSWORD", "amruth123"):
        import json
        feedback_file = os.path.join(BASE_DIR, "feedback.json")
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                all_feedback = json.load(f)
            st.markdown(f"**{len(all_feedback)} responses**")
            for fb in reversed(all_feedback):
                st.markdown(f"""
**{fb['rating']}** — *{fb['name']}*  
{fb['feedback']}  
<small style='color:#475569'>{fb['timestamp']}</small>
""", unsafe_allow_html=True)
                st.divider()
        except:
            st.info("No feedback yet.")