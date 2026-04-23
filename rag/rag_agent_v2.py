"""
rag_agent_v2.py — Kannada Book AI Agent v2
Upgrades over v1:
  1. LangChain Tool wrapping  — RAG exposed as proper LangChain Tools
  2. Metadata filtering       — filter by exact page or page range
  3. Explicit NOT FOUND msg   — when score < threshold, return clear message
  4. ReAct Agent              — LangChain agent with tool-use loop (for CLI/API use)
  5. retrieve_v2()            — simple drop-in replacement for app.py
"""

import os
import re
from typing import Optional

from langchain.tools import Tool
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from dotenv import load_dotenv
load_dotenv()

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
CHROMA_DIR   = os.path.join(BASE_DIR, "chroma_db")
COLLECTION   = "kannada_book"
MODEL_NAME   = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

STANDARD_THRESHOLD  = 0.25
CHARACTER_THRESHOLD = 0.20
NOT_FOUND_MSG = (
    "⚠️ Not found in document — "
    "no relevant passages matched your query with sufficient confidence."
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
        r'pages?\s*(\d+)\s*(?:to|through|–|-)\s*(\d+)',
        question, re.IGNORECASE
    )
    if range_match:
        return None, (int(range_match.group(1)), int(range_match.group(2)))

    page_match = re.search(
        r'page\s*(\d+)|ಪುಟ\s*(\d+)|(\d+)\s*(?:page|ಪುಟ)',
        question, re.IGNORECASE
    )
    if page_match:
        return int(next(g for g in page_match.groups() if g)), None

    return None, None


def retrieve_with_filter(
    query: str,
    vectorstore,
    top_k: int = 5,
    threshold: float = STANDARD_THRESHOLD,
    page: Optional[int] = None,
    page_range: Optional[tuple] = None,
) -> list[dict]:
    """
    Semantic search with optional metadata filtering.

    Args:
        query      : User question
        vectorstore: LangChain Chroma instance
        top_k      : Candidate results to fetch
        threshold  : Minimum similarity score (0–1)
        page       : Filter to exact page number
        page_range : Filter to (start_page, end_page) inclusive
    """
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
) -> tuple[list[dict], str]:
    """
    Drop-in replacement for app.py retrieval.

    Returns:
        (chunks, fallback_message)
        chunks          — list of {text, page, score}
        fallback_message — NOT_FOUND_MSG if no results, else ""

    Usage in app.py:
        from rag_agent_v2 import retrieve_v2, detect_page_filter, NOT_FOUND_MSG
        page, page_range = detect_page_filter(question)
        chunks, fallback = retrieve_v2(question, page=page, page_range=page_range,
                                       is_character=is_character_question(question))
        if fallback and not general:
            st.warning(fallback)
        else:
            # use chunks normally
    """
    vs        = _get_vs()
    threshold = CHARACTER_THRESHOLD if is_character else STANDARD_THRESHOLD
    top_k     = 10 if is_character else 5

    chunks = retrieve_with_filter(
        query       = query,
        vectorstore = vs,
        top_k       = top_k,
        threshold   = threshold,
        page        = page,
        page_range  = page_range,
    )

    fallback = NOT_FOUND_MSG if not chunks else ""
    return chunks, fallback


# ══════════════════════════════════════════════════════════════════════════════
# 4.  LANGCHAIN TOOLS
# ══════════════════════════════════════════════════════════════════════════════

def _rag_search_tool_fn(query: str) -> str:
    """Tool function — search the book, return formatted passages or NOT_FOUND."""
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
    """Tool function — return curated book metadata."""
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


# ══════════════════════════════════════════════════════════════════════════════
# 5.  REACT AGENT (for CLI / API use — not needed in Streamlit)
# ══════════════════════════════════════════════════════════════════════════════

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
    """
    Build a LangChain ReAct agent for the Kannada book.
    Requires GROQ_API_KEY in .env
    """
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
            print(f"  ⚠️  {NOT_FOUND_MSG}")
        print()