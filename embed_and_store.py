# app.py — Kannada Book AI Agent
# Run: kannada-rag-env\Scripts\python.exe -m streamlit run app.py

import os
import re
import base64
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
CHROMA_DIR     = r"chroma_db"
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
    r'ಹಿಮವಂತ',
    r'ಪ್ರಾರ್ಥನಾ',
    r'main character',
    r'protagonist',
    r'ಮುಖ್ಯ ಪಾತ್ರ',
]

def is_general_question(question):
    q = question.lower()
    return any(re.search(p, q, re.IGNORECASE) for p in GENERAL_PATTERNS)

st.set_page_config(
    page_title="ಹೇಳಿ ಹೋಗು ಕಾರಣ — AI Agent",
    page_icon="📚",
    layout="wide"
)

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

def call_sarvam_llm(prompt):
    if not SARVAM_API_KEY:
        return "⚠️ SARVAM_API_KEY not set in .env"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "model"      : "sarvam-m",
        "messages"   : [{"role": "user", "content": prompt}],
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
    clean = re.sub(r'\[Page \d+\]:', '', text)[:400].strip()
    payload = {
        "inputs"              : [clean],
        "target_language_code": language,
        "speaker"             : "amol",
        "model"               : "bulbul:v1",
        "pace"                : 1.0,
        "loudness"            : 1.5,
        "speech_sample_rate"  : 22050,
        "enable_preprocessing": False
    }
    resp = requests.post(
        "https://api.sarvam.ai/text-to-speech",
        headers=headers, json=payload, timeout=30
    )
    resp.raise_for_status()
    return base64.b64decode(resp.json()["audios"][0])

# ── UI ───────────────────────────────────────────────
st.title("📚 ಹೇಳಿ ಹೋಗು ಕಾರಣ — AI Agent")
st.caption("Kannada Book AI Agent by Ravi Belagere — Ask in Kannada or English")

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
                answer = call_sarvam_llm(prompt)
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