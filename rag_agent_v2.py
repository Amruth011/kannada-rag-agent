"""
rag_agent_v2.py — Kannada Book AI Agent v2
Upgrades over v1:
  1. LangChain Tool wrapping  — RAG exposed as proper LangChain Tools
  2. Metadata filtering       — filter by exact page or page range
  3. Explicit NOT FOUND msg   — when score < threshold, return clear message
  4. ReAct Agent              — LangChain agent with tool-use loop (for CLI/API use)
  5. retrieve_v2()            — simple drop-in replacement for app.py
  6. LangChain LCEL Chain     — bilingual prompt and execution chain
"""

import os
import re
import requests
from typing import Optional, List, Any

# LangChain 1.x imports
from langchain_core.tools import Tool
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv
load_dotenv()

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR     = os.path.join(BASE_DIR, "chroma_db")
COLLECTION     = "kannada_book"
MODEL_NAME     = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "").strip()

# Configure Gemini
import google.generativeai as genai
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Gemini configure error: {e}")

STANDARD_THRESHOLD  = 0.25
CHARACTER_THRESHOLD = 0.20

# ── Re-ranking configuration ──────────────────────────────────────────────────
RERANK_MODEL    = "BAAI/bge-reranker-v2-m3"  # multilingual cross-encoder
RERANK_FETCH_K  = 15   # wider initial retrieval
RERANK_TOP_N    = 4    # chunks to keep after reranking
NOT_FOUND_MSG_EN = (
    "⚠️ Not found in document — "
    "no relevant passages matched your query with sufficient confidence."
)
NOT_FOUND_MSG_KN = (
    "⚠️ ಪುಸ್ತಕದಲ್ಲಿ ಮಾಹಿತಿ ಸಿಗಲಿಲ್ಲ — "
    "ನಿಮ್ಮ ಪ್ರಶ್ನೆಗೆ ಸೂಕ್ತವಾದ ಭಾಗಗಳು ಲಭ್ಯವಿಲ್ಲ."
)

# ══════════════════════════════════════════════════════════════════════════════
# 1.  VECTOR STORE
# ══════════════════════════════════════════════════════════════════════════════

def get_vectorstore():
    """Load existing ChromaDB via LangChain wrapper."""
    embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
    return Chroma(
        collection_name  = COLLECTION,
        embedding_function = embeddings,
        persist_directory  = CHROMA_DIR,
    )

# ══════════════════════════════════════════════════════════════════════════════
# 2.  METADATA FILTERING + RETRIEVAL
# ══════════════════════════════════════════════════════════════════════════════

def detect_page_filter(question: str):
    """
    Detect page number or page range from user question.
    Returns:
        (int, None)    — exact page  e.g. "page 50"
        (None, tuple)  — page range  e.g. "pages 10 to 30"
        (None, None)   — no filter
    """
    range_match = re.search(
        r'pages?\s*(\d+)\s*(?:to|through|–|-)\s*(\d+)|ಪುಟಗಳು?\s*(\d+)\s*(?:ರಿಂದ|ಇಂದ|-)\s*(\d+)',
        question, re.IGNORECASE
    )
    if range_match:
        groups = [g for g in range_match.groups() if g is not None]
        if len(groups) == 2:
            return None, (int(groups[0]), int(groups[1]))

    page_match = re.search(
        r'page\s*(\d+)|ಪುಟ\s*(\d+)|(\d+)\s*(?:page|ಪುಟ)',
        question, re.IGNORECASE
    )
    if page_match:
        return int(next(g for g in page_match.groups() if g)), None

    return None, None


# ══════════════════════════════════════════════════════════════════════════════
# 2a. CROSS-ENCODER RE-RANKER
# ══════════════════════════════════════════════════════════════════════════════

_reranker = None  # singleton — loaded once

def _get_reranker():
    """Lazy-load the cross-encoder re-ranker (cached after first call)."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder(RERANK_MODEL, max_length=512)
            print(f"[OK] Re-ranker loaded: {RERANK_MODEL}")
        except Exception as e:
            print(f"[WARN] Re-ranker load failed ({e}) - skipping reranking.")
            _reranker = False  # sentinel: don't retry
    return _reranker if _reranker is not False else None


def rerank_chunks(query: str, chunks: list, top_n: int = RERANK_TOP_N) -> list:
    """
    Re-rank retrieved chunks with a cross-encoder.

    Returns chunks sorted by reranker score descending, capped at top_n.
    Each chunk gains a 'rerank_score' key.
    If the reranker fails to load, returns the original list unchanged.
    """
    if not chunks:
        return chunks

    reranker = _get_reranker()
    if reranker is None:
        # Fallback: return top_n from original cosine ordering
        for c in chunks:
            c["rerank_score"] = c.get("score", 0.0)
        return chunks[:top_n]

    pairs = [(query, c["text"]) for c in chunks]
    scores = reranker.predict(pairs).tolist()

    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = round(float(score), 4)

    reranked = sorted(chunks, key=lambda c: c["rerank_score"], reverse=True)
    return reranked[:top_n]


def retrieve_with_filter(
    query: str,
    vectorstore,
    top_k: int = RERANK_FETCH_K,
    threshold: float = STANDARD_THRESHOLD,
    page: Optional[int] = None,
    page_range: Optional[tuple] = None,
) -> list[dict]:
    """Semantic search with optional metadata filtering."""
    where_filter = None
    if page is not None:
        where_filter = {"page": {"$eq": page}}
    elif page_range is not None:
        start, end = page_range
        where_filter = {
            "$and": [
                {"page": {"$gte": start}},
                {"page": {"$lte": end}},
            ]
        }

    if where_filter:
        results = vectorstore.similarity_search_with_relevance_scores(
            query, k=top_k, filter=where_filter
        )
    else:
        results = vectorstore.similarity_search_with_relevance_scores(
            query, k=top_k
        )

    chunks = []
    for doc, score in results:
        if score >= threshold:
            chunks.append({
                "text" : doc.page_content,
                "page" : doc.metadata.get("page", "?"),
                "score": round(score, 3),
            })
    return chunks

# ══════════════════════════════════════════════════════════════════════════════
# 3.  DROP-IN WRAPPER for app.py
# ══════════════════════════════════════════════════════════════════════════════

_vectorstore = None

def _get_vs():
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = get_vectorstore()
    return _vectorstore


def retrieve_v2(
    query: str,
    page: Optional[int] = None,
    page_range: Optional[tuple] = None,
    is_character: bool = False,
    language: str = "English",
    use_reranking: bool = True,
) -> tuple[list[dict], str, dict]:
    """
    Retrieve and (optionally) rerank chunks for a query.

    Returns:
        chunks       — top-N reranked (or top-K raw) chunks
        fallback_msg — not-found message if no chunks above threshold
        meta         — dict with retrieval stats for UI display
    """
    vs        = _get_vs()
    threshold = CHARACTER_THRESHOLD if is_character else STANDARD_THRESHOLD
    # Always fetch wide pool; reranker will narrow it down
    fetch_k   = RERANK_FETCH_K

    raw_chunks = retrieve_with_filter(
        query       = query,
        vectorstore = vs,
        top_k       = fetch_k,
        threshold   = threshold,
        page        = page,
        page_range  = page_range,
    )

    meta = {
        "fetched":    len(raw_chunks),
        "reranked":   False,
        "final":      len(raw_chunks),
        "rerank_top": RERANK_TOP_N,
    }

    if use_reranking and raw_chunks:
        chunks = rerank_chunks(query, raw_chunks, top_n=RERANK_TOP_N)
        meta["reranked"] = True
        meta["final"]    = len(chunks)
    else:
        # No reranking — just take top chunks by cosine score
        for c in raw_chunks:
            c["rerank_score"] = c.get("score", 0.0)
        chunks = raw_chunks[:RERANK_TOP_N]
        meta["final"] = len(chunks)

    not_found = NOT_FOUND_MSG_EN if language == "English" else NOT_FOUND_MSG_KN
    fallback  = not_found if not chunks else ""
    return chunks, fallback, meta

# ══════════════════════════════════════════════════════════════════════════════
# 4.  LLM DISPATCHERS (Gemini -> Sarvam -> Groq)
# ══════════════════════════════════════════════════════════════════════════════

def get_best_gemini_model():
    return "models/gemini-flash-lite-latest"

def call_gemini_api(messages: list, retries=1) -> Optional[str]:
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

def call_sarvam_api(messages: list) -> Optional[str]:
    if not SARVAM_API_KEY: return None
    headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "sarvam-m", "messages": messages, "temperature": 0.1, "max_tokens": 600}
    try:
        resp = requests.post("https://api.sarvam.ai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass
    return None

def call_groq_api(messages: list, retries=2) -> str:
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

# ══════════════════════════════════════════════════════════════════════════════
# 5.  LANGCHAIN CUSTOM BaseChatModel FOR BILINGUAL FALLBACKS
# ══════════════════════════════════════════════════════════════════════════════

class BilingualFallbackChatModel(BaseChatModel):
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        formatted = []
        for msg in messages:
            role = "user"
            if isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            formatted.append({"role": role, "content": msg.content})

        # Call unified dispatch logic
        ans = call_gemini_api(formatted)
        if not ans:
            ans = call_sarvam_api(formatted)
        if not ans:
            ans = call_groq_api(formatted)

        generation = ChatGeneration(message=AIMessage(content=ans))
        return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "bilingual_fallback_model"

# ══════════════════════════════════════════════════════════════════════════════
# 6.  LANGCHAIN LCEL BILINGUAL CHAIN
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_EN = """You are an AI assistant for the Kannada novel "Heli Hogu Karana" by Ravi Belagere.

BOOK INFORMATION:
{book_context}

RETRIEVED PASSAGES:
{context}

Answer using the information above. Be informative and cite page numbers when using passages.
If passages say "Not found in document", tell the user clearly.
Answer in English."""

SYSTEM_PROMPT_KN = """ನೀವು "ಹೇಳಿ ಹೋಗು ಕಾರಣ" ಕನ್ನಡ ಕಾದಂಬರಿಯ AI ಸಹಾಯಕರು.

ಪುಸ್ತಕದ ಮಾಹಿತಿ:
{book_context}

ಪುಸ್ತಕದಿಂದ ತೆಗೆದ ವಿಷಯ:
{context}

ಕನ್ನಡದಲ್ಲಿ ಮಾತ್ರ ಉತ್ತರಿಸಿ. ಪುಟ ಸಂಖ್ಯೆಗಳನ್ನು ಉಲ್ಲೇಖಿಸಿ.
ಪ್ರಶ್ನೆಗೆ ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರ ನೀಡಿ."""

def get_rag_chain(language: str = "English"):
    system_text = SYSTEM_PROMPT_EN if language == "English" else SYSTEM_PROMPT_KN
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_text),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}")
    ])
    
    llm = BilingualFallbackChatModel()
    chain = prompt | llm | StrOutputParser()
    return chain

# ══════════════════════════════════════════════════════════════════════════════
# 7.  LANGCHAIN TOOLS & legacy ReAct Agent (if needed for APIs)
# ══════════════════════════════════════════════════════════════════════════════

def _rag_search_tool_fn(query: str) -> str:
    page, page_range = detect_page_filter(query)
    is_char = bool(re.search(
        r'himavant|prarthana|ಹಿಮವಂತ|ಪ್ರಾರ್ಥನಾ|who is|character|ಪಾತ್ರ',
        query, re.IGNORECASE
    ))
    chunks, fallback = retrieve_v2(
        query        = query,
        page         = page,
        page_range   = page_range,
        is_character = is_char,
    )
    if fallback:
        return fallback
    parts = [f"[Page {c['page']} | score={c['score']}]\n{c['text']}" for c in chunks]
    return "\n\n---\n\n".join(parts)


def _book_metadata_tool_fn(query: str) -> str:
    return """
Book: ಹೇಳಿ ಹೋಗು ಕಾರಣ (Heli Hogu Karana — "Tell the reason before you go")
Author: Ravi Belagere — prominent Kannada journalist, Bengaluru
Pages: 346 | Language: Kannada | Genre: Novel

Themes: Human morality, guilt, truth-telling, divine justice,
        moral accountability, existential questioning, social critique.

Characters:
  • ಹಿಮವಂತ (Himavant) — main protagonist
  • ಪ್ರಾರ್ಥನಾ (Prarthana) — his wife, central relationship

Style: Bold journalistic prose, episodic structure, philosophical perspectives.
"""

KANNADA_TOOLS = [
    Tool(
        name="KannadaBookSearch",
        func=_rag_search_tool_fn,
        description=(
            "Search the Kannada novel 'Heli Hogu Karana' for specific story passages, "
            "characters, events, or page content. Supports page filters: "
            "'page 50' or 'pages 10 to 30'. Use for any story-specific question."
        ),
    ),
    Tool(
        name="BookMetadata",
        func=_book_metadata_tool_fn,
        description=(
            "Get general information about the book — title, author, themes, "
            "main characters. Use for questions like 'what is this book about' "
            "or 'who is the author'."
        ),
    ),
]

_REACT_TEMPLATE = """You are an expert AI assistant for the Kannada novel "Heli Hogu Karana" by Ravi Belagere.
Answer questions using the tools available. Always cite page numbers from passages.
If a tool returns a "Not found" message, tell the user clearly.
Respond in {language}.

Tools available:
{tools}

Format:
Question: the input question
Thought: think about what to do
Action: tool name (one of [{tool_names}])
Action Input: input to the tool
Observation: tool result
... (repeat as needed)
Thought: I have enough to answer
Final Answer: your complete answer

Question: {input}
Thought:{agent_scratchpad}"""

def get_agent(language: str = "English") -> AgentExecutor:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set")

    llm = ChatGroq(
        model       = "llama-3.3-70b-versatile",
        temperature = 0.1,
        max_tokens  = 800,
        api_key     = GROQ_API_KEY,
    )

    prompt = PromptTemplate.from_template(_REACT_TEMPLATE).partial(language=language)
    agent  = create_react_agent(llm=llm, tools=KANNADA_TOOLS, prompt=prompt)

    return AgentExecutor(
        agent                    = agent,
        tools                    = KANNADA_TOOLS,
        verbose                  = True,
        max_iterations           = 4,
        handle_parsing_errors    = True,
        return_intermediate_steps= True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# CLI TEST
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=== Kannada RAG Agent v2 — CLI Test ===\n")
    vs = get_vectorstore()
    tests = [
        ("Who is Himavant?",              True,  None, None),
        ("What is in page 50?",           False, 50,   None),
        ("What happens in pages 10-20?",  False, None, (10, 20)),
        ("What is the weather on Mars?",  False, None, None),
    ]
    for q, is_char, pg, pr in tests:
        print(f"Q: {q}")
        chunks = retrieve_with_filter(
            q, vs,
            threshold  = CHARACTER_THRESHOLD if is_char else STANDARD_THRESHOLD,
            top_k      = 10 if is_char else 5,
            page       = pg,
            page_range = pr,
        )
        if chunks:
            print(f"  ✅ {len(chunks)} chunks | Pages: {[c['page'] for c in chunks]}")
        else:
            print(f"  ⚠️  {NOT_FOUND_MSG_EN}")
        print()