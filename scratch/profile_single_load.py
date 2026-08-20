import os
import sys
import psutil
import time

# Ensure we can load rag_agent_v2
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

process = psutil.Process(os.getpid())
total_system_memory = psutil.virtual_memory().total / (1024 * 1024)

def get_ram():
    return process.memory_info().rss / (1024 * 1024)

stats = []

def record_stat(name, before, after):
    delta = after - before
    pct_sys = (delta / total_system_memory) * 100
    stats.append({
        "component": name,
        "before": before,
        "after": after,
        "delta": delta,
        "pct_sys": pct_sys
    })
    print(f"[{name}] RAM Before: {before:.2f} MB | After: {after:.2f} MB | Delta: {delta:.2f} MB | {pct_sys:.4f}% of System RAM")

print(f"System Total Memory: {total_system_memory:.2f} MB")
print(f"Initial Baseline RAM: {get_ram():.2f} MB\n")

# 1. Streamlit startup
before = get_ram()
import streamlit as st
after = get_ram()
record_stat("Streamlit Startup", before, after)

# 2. Gemini client initialization
before = get_ram()
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
after = get_ram()
record_stat("Gemini Client Init", before, after)

# 3. Groq client initialization
before = get_ram()
from langchain_groq import ChatGroq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
chat_groq = None
if GROQ_API_KEY:
    chat_groq = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=800,
        api_key=GROQ_API_KEY
    )
after = get_ram()
record_stat("Groq Client Init", before, after)

# 4. LangChain initialization (Bilingual fallback chain)
before = get_ram()
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
# Import custom chat model class and chain builder
from rag_agent_v2 import BilingualFallbackChatModel, get_rag_chain
chain = get_rag_chain("English")
after = get_ram()
record_stat("LangChain Initialization", before, after)

# 5. ChromaDB loading (Library imports)
before = get_ram()
import chromadb
from langchain_community.vectorstores import Chroma
after = get_ram()
record_stat("ChromaDB Library Import", before, after)

# 6. Embedding model loading
before = get_ram()
from langchain_huggingface import HuggingFaceEmbeddings
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embeddings = HuggingFaceEmbeddings(model_name=MODEL_NAME)
after = get_ram()
record_stat("Embedding Model Loading", before, after)

# 7. ChromaDB database instantiation (vector store loading)
before = get_ram()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
COLLECTION = "kannada_book"
vectorstore = Chroma(
    collection_name=COLLECTION,
    embedding_function=embeddings,
    persist_directory=CHROMA_DIR,
)
after = get_ram()
record_stat("ChromaDB Vector Store Loading", before, after)

# 8. BM25 index creation/loading
before = get_ram()
from rank_bm25 import BM25Okapi
data = vectorstore.get()
all_chunks = [{"text": doc, "page": meta.get("page", "?")} for doc, meta in zip(data["documents"], data["metadatas"])]
tokenized_corpus = [doc["text"].lower().split() for doc in all_chunks]
bm25_model = BM25Okapi(tokenized_corpus)
after = get_ram()
record_stat("BM25 Index Creation", before, after)

# 9. CrossEncoder reranker loading
before = get_ram()
from sentence_transformers import CrossEncoder
RERANK_MODEL = "BAAI/bge-reranker-v2-m3"
reranker = CrossEncoder(RERANK_MODEL, max_length=512)
after = get_ram()
record_stat("CrossEncoder Reranker Loading", before, after)

# Inject the already-loaded components into rag_agent_v2 globals to prevent reloading!
import rag_agent_v2
rag_agent_v2._vectorstore = vectorstore
rag_agent_v2._bm25_model = bm25_model
rag_agent_v2._all_chunks = all_chunks
rag_agent_v2._reranker = reranker

print("\n--- Running Query Simulation (With Injected/Cached Objects) ---")
before_query = get_ram()
print(f"RAM Before Query: {before_query:.2f} MB")

# Run query retrieval + reranking
chunks, fallback, meta = rag_agent_v2.retrieve_v2("Who is Himavant?", is_character=True, use_reranking=True)

during_query = get_ram()
print(f"RAM After Retrieval/Reranking (during query): {during_query:.2f} MB")
delta_query_retrieval = during_query - before_query
print(f"Delta RAM consumed for Retrieval/Reranking: {delta_query_retrieval:.2f} MB")

# Invoke the chain
before_chain = get_ram()
rag_section = "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks])
try:
    ans = chain.invoke({
        "book_context": "Book Context",
        "context": rag_section,
        "history": [],
        "question": "Who is Himavant?"
    })
    print(f"Chain Answer: {ans[:60]}...")
except Exception as e:
    print(f"Chain invoke failed/skipped: {e}")

after_chain = get_ram()
delta_chain = after_chain - before_chain
print(f"RAM After Chain Invoke: {after_chain:.2f} MB | Delta: {delta_chain:.2f} MB")

final_ram = get_ram()
print(f"\nTotal Process RAM at end: {final_ram:.2f} MB")

# Print Summary Table
print("\n=== SUMMARY TABLE ===")
print("| Component | RAM Before (MB) | RAM After (MB) | Delta RAM (MB) | % of System RAM |")
print("| --- | --- | --- | --- | --- |")
total_delta = final_ram - stats[0]["before"]
for s in stats:
    print(f"| {s['component']} | {s['before']:.2f} | {s['after']:.2f} | {s['delta']:.2f} | {s['pct_sys']:.4f}% |")
print(f"| Query Retrieval + Reranking (Cached) | {before_query:.2f} | {during_query:.2f} | {delta_query_retrieval:.2f} | {(delta_query_retrieval/total_system_memory)*100:.4f}% |")
print(f"| Query LLM Generation | {before_chain:.2f} | {after_chain:.2f} | {delta_chain:.2f} | {(delta_chain/total_system_memory)*100:.4f}% |")
print(f"| **Total Process RAM** | - | **{final_ram:.2f}** | **{total_delta:.2f}** | **{(total_delta/total_system_memory)*100:.4f}%** |")
