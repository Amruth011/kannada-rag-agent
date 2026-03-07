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

Main Characters:
- ಹಿಮವಂತ (Himavant): The main protagonist of the novel. His character development and
  inner conflicts form the central narrative. He struggles with moral dilemmas and the
  tension between truth and deception. His relationship with his wife Prarthana is central.
- ಪ್ರಾರ್ಥನಾ (Prarthana): Himavant's wife. Her relationship with Himavant is a key
  emotional thread in the story. The tension between them reflects the novel's themes
  of accountability and truth-telling in personal relationships.
"""

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
    r'himavant',
    r'prarthana',
    r'pratana',
    r'prathana',
    r'ಹಿಮವಂತ',
    r'ಪ್ರಾರ್ಥನಾ',
    r'main character',
    r'protagonist',
    r'ಮುಖ್ಯ ಪಾತ್ರ',
    r'character',
    r'ಪಾತ್ರ',
    r'wife',
    r'husband',
    r'relationship',
    r'ಹೆಂಡತಿ',
    r'ಗಂಡ',
    r'ಸಂಬಂಧ',
    r'name of',
    r'who are the',
    r'tell me about',
]

def is_general_question(question):
    q = question.lower()
    return any(re.search(p, q, re.IGNORECASE) for p in GENERAL_PATTERNS)

st.set_page_config(
    page_title="ಹೇಳಿ ಹೋಗು ಕಾರಣ — AI Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ULTRA-PREMIUM CSS STYLING ---
st.markdown("""
<style>
    /* Import modern Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
    }

    /* Base theme: Deep rich space dark mode */
    div[data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 15% 50%, #130b29, #09090e 50%, #050a16 100%);
        color: #e2e8f0;
    }
    
    /* Hide Streamlit default UI elements for a SaaS feel */
    header[data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: blur(0px) !important;
    }
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* Sleek Sidebar with blurred frost effect */
    div[data-testid="stSidebar"] {
        background-color: rgba(10, 10, 20, 0.4) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Container Spacing for Header */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 5rem !important;
    }

    /* Modern Chat Messages */
    div[data-testid="stChatMessage"] {
        background: rgba(20, 20, 35, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.03);
        border-radius: 20px;
        padding: 1.5rem 1.75rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        line-height: 1.6;
        font-size: 1.05rem;
    }
    div[data-testid="stChatMessage"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.6), inset 0 1px 0 0 rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.08);
    }

    /* User Chat Bubble - Sleek Neon Blue/Cyan */
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background: linear-gradient(145deg, rgba(8, 145, 178, 0.08) 0%, rgba(56, 189, 248, 0.03) 100%);
        border-left: 3px solid #06b6d4;
    }

    /* Assistant Chat Bubble - Elegant Purple/Pink */
    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background: linear-gradient(145deg, rgba(168, 85, 247, 0.08) 0%, rgba(236, 72, 153, 0.03) 100%);
        border-left: 3px solid #d946ef;
    }
    
    /* Floating, Glowing Input Box */
    div[data-testid="stChatInput"] {
        background: rgba(15, 15, 25, 0.7) !important;
        backdrop-filter: blur(24px) saturate(180%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 24px;
        padding: 0.25rem 0.5rem;
        box-shadow: 0 0 40px rgba(139, 92, 246, 0.15), 0 4px 6px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: rgba(139, 92, 246, 0.5);
        box-shadow: 0 0 40px rgba(139, 92, 246, 0.3), 0 4px 6px rgba(0,0,0,0.3);
    }

    /* Styled Expander / Accordion */
    div[data-testid="stExpander"] {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
        transition: all 0.2s;
    }
    div[data-testid="stExpander"]:hover {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
    }

    /* Elegant Dividers */
    hr {
        border-color: rgba(255,255,255,0.06) !important;
        margin: 2rem 0;
    }
    
    /* Premium Title Text Gradient with glow */
    h1 {
        background: linear-gradient(to right, #38bdf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        font-size: 3rem;
        letter-spacing: -1px;
        margin-bottom: 0.2rem;
        text-shadow: 0 10px 30px rgba(192, 132, 252, 0.2);
    }
    
    /* Subtle subtitle */
    .stMarkdown p {
        color: #94a3b8;
    }

    /* Minimalist Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 6px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.2);
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.01) 100%);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        color: #fff;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        border-color: #8b5cf6;
        box-shadow: 0 0 15px rgba(139, 92, 246, 0.3);
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
    collection  = client.get_collection(COLLECTION)
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
    if use_book_context_only:
        rag_section = ""
    else:
        rag_section = "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks]) if chunks else "(No specific passages retrieved.)"

    if language == "English":
        return f"""You are an AI assistant for the Kannada novel "Heli Hogu Karana".

BOOK INFORMATION (always accurate):
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
        "api-subscription-key": SARVAM_API_KEY,
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
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }

    clean = re.sub(r'\[Page \d+\]:', '', text).strip()
    
    # Split text intelligently to stay under 500 characters (API limit)
    words = clean.split(' ')
    chunks = []
    current_chunk = ""
    
    for word in words:
        if len(current_chunk) + len(word) + 1 < 450:
            current_chunk += (" " if current_chunk else "") + word
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = word
    if current_chunk:
        chunks.append(current_chunk)

    audio_bytes_list = []
    for chunk in chunks:
        if not chunk.strip():
            continue
        payload = {
            "inputs"              : [chunk.strip()],
            "target_language_code": language,
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

    # Stitch WAV files together seamlessly
    import wave
    import io
    
    output_wav = io.BytesIO()
    with wave.open(output_wav, 'wb') as wav_out:
        for i, audio_bytes in enumerate(audio_bytes_list):
            segment = io.BytesIO(audio_bytes)
            try:
                with wave.open(segment, 'rb') as wav_in:
                    if i == 0:
                        # Set audio properties based on the first chunk
                        wav_out.setparams(wav_in.getparams())
                    wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))
            except wave.Error:
                continue

    return output_wav.getvalue()

# ── UI ───────────────────────────────────────────────
st.markdown("<h1>📚 ಹೇಳಿ ಹೋಗು ಕಾರಣ<br><span style='font-size: 1.5rem; color: #94a3b8; font-weight: 400;'>Premium AI Knowledge Agent</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='margin-bottom: 2rem;'>Masterpiece Kannada Novel Intelligence — Powered by Sarvam & Surya OCR</p>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Settings")
    language    = st.radio("Answer language", ["English", "Kannada"], key="lang")
    show_chunks = st.checkbox("Show source chunks", value=False)
    enable_tts  = st.checkbox("🔊 Read answer aloud (TTS)", value=False)
    st.divider()
    st.markdown("**📖 About**")
    st.markdown("*ಹೇಳಿ ಹೋಗು ಕಾರಣ* by Ravi Belagere — a Kannada novel.")
    st.divider()
    st.markdown("**📊 Stats**")
    st.markdown("- 346 pages processed\n- 687 chunks indexed\n- Powered by Sarvam AI")
    st.divider()
    st.markdown("**💡 Try asking:**")
    st.markdown("- What is this book about?\n- Who is Himavant?\n- Who is Prarthana?\n- What is in page 50?\n- ಹಿಮವಂತ ಯಾರು?\n- ಈ ಪುಸ್ತಕದ ವಿಷಯ ಏನು?")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("pages"):
            st.caption(f"📄 Sources: Pages {', '.join(map(str, msg['pages']))}")
        if msg.get("audio"):
            st.audio(msg["audio"], format="audio/wav")

question = st.chat_input("Ask about the book... (ಪ್ರಶ್ನೆ ಕೇಳಿ...)")

if question:
    current_lang = st.session_state.get("lang", "English")

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                embed_model, collection = load_agent()

                general  = is_general_question(question)
                page_num = detect_page_query(question)
                chunks   = []

                if page_num:
                    chunks = retrieve_by_page(page_num, collection)
                    if not chunks:
                        chunks = retrieve(question, embed_model, collection)
                elif not general:
                    chunks = retrieve(question, embed_model, collection)

                prompt = build_prompt(question, chunks, current_lang,
                                      use_book_context_only=general)
                                      
                # Build conversation history for memory
                chat_history = []
                # Keep last 4 messages to preserve context without blowing up token limits
                for msg in st.session_state.messages[-5:-1]:
                    if msg["role"] in ["user", "assistant"]:
                        # Strip citations from history to keep it clean
                        clean_content = re.sub(r'\[Page \d+\]:', '', msg["content"]).strip()
                        chat_history.append({"role": msg["role"], "content": clean_content})
                        
                # Append the current prompt 
                chat_history.append({"role": "user", "content": prompt})

                answer = call_sarvam_llm(chat_history)
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
                st.error(f"Error: {e}")

if st.session_state.messages:
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()