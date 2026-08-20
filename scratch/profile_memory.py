import os
import sys
import psutil
import time

# Ensure we can load rag_agent_v2
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

process = psutil.Process(os.getpid())
total_system_memory = psutil.virtual_memory().total / (1024 * 1024) # in MB

def get_ram():
    return process.memory_info().rss / (1024 * 1024) # in MB

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

# 1. Streamlit startup / import
before = get_ram()
import streamlit as st
after = get_ram()
record_stat("Streamlit Import", before, after)

# 2. Gemini client initialization
before = get_ram()
import google.generativeai as genai
# Configure if API key is present (from dotenv)
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
if GROQ_API_KEY:
    chat_groq = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=800,
        api_key=GROQ_API_KEY
    )
after = get_ram()
record_stat("Groq Client Init", before, after)

# 4. LangChain initialization (Chain instantiation)
before = get_ram()
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from rag_agent_v2 import BilingualFallbackChatModel, get_rag_chain
# Create the chain
chain = get_rag_chain("English")
after = get_ram()
record_stat("LangChain Initialization", before, after)

# 5. ChromaDB loading (Library imports)
before = get_ram()
import chromadb
from langchain_community.vectorstores import Chroma
after = get_ram()
record_stat("ChromaDB Library Loading", before, after)

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

# Calculate total startup memory
startup_ram = get_ram()
print(f"\nFinal Startup RAM: {startup_ram:.2f} MB")
total_startup_delta = startup_ram - stats[0]["before"]
print(f"Total RAM consumed during startup: {total_startup_delta:.2f} MB")

print("\n--- Running Query Simulation ---")
# Let's import the retrieval logic
from rag_agent_v2 import retrieve_v2

# Run a sample query to see memory consumption during query execution
query = "Who is Himavant?"
before_query = get_ram()
print(f"RAM Before Query: {before_query:.2f} MB")

# Execute query (retrieval + reranking)
chunks, fallback, meta = retrieve_v2(query, is_character=True, use_reranking=True)

during_query = get_ram()
print(f"RAM After Retrieval/Reranking (during query): {during_query:.2f} MB")
delta_query_retrieval = during_query - before_query
print(f"Delta RAM consumed for Retrieval/Reranking: {delta_query_retrieval:.2f} MB")

# Mock the chain invocation or actually invoke it if keys are present
# We will do a full mock of chain.invoke or call the chain if API keys are available
import requests
print(f"Chroma fetched: {meta.get('vector_fetched')}, BM25 fetched: {meta.get('bm25_fetched')}, Final chunks: {len(chunks)}")

# Let's run chain invocation
before_chain = get_ram()
try:
    from langchain_core.messages import HumanMessage
    # Mock context setup like app.py
    rag_section = "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks])
    print("Invoking LangChain LCEL chain...")
    ans = chain.invoke({
        "book_context": "Book Context",
        "context": rag_section,
        "history": [],
        "question": query
    })
    print(f"Chain Answer (partial): {ans[:60]}...")
except Exception as e:
    print(f"Chain invocation failed/skipped (expected if keys missing): {e}")

after_chain = get_ram()
delta_chain = after_chain - before_chain
print(f"RAM After Chain Invoke: {after_chain:.2f} MB | Delta: {delta_chain:.2f} MB")

final_ram = get_ram()
print(f"\nTotal Process RAM at end: {final_ram:.2f} MB")

# Print Summary Table
print("\n=== SUMMARY TABLE ===")
print("| Component | RAM Before (MB) | RAM After (MB) | Delta RAM (MB) | % of Total application delta | % of System RAM |")
print("| --- | --- | --- | --- | --- | --- |")
for s in stats:
    pct_app = (s["delta"] / total_startup_delta) * 100 if total_startup_delta > 0 else 0
    print(f"| {s['component']} | {s['before']:.2f} | {s['after']:.2f} | {s['delta']:.2f} | {pct_app:.2f}% | {s['pct_sys']:.4f}% |")

# Also print query stats
pct_app_q = (delta_query_retrieval / total_startup_delta) * 100 if total_startup_delta > 0 else 0
print(f"| Query Retrieval + Reranking | {before_query:.2f} | {during_query:.2f} | {delta_query_retrieval:.2f} | {pct_app_q:.2f}% | {(delta_query_retrieval/total_system_memory)*100:.4f}% |")
pct_app_c = (delta_chain / total_startup_delta) * 100 if total_startup_delta > 0 else 0
print(f"| Query LLM Generation | {before_chain:.2f} | {after_chain:.2f} | {delta_chain:.2f} | {pct_app_c:.2f}% | {(delta_chain/total_system_memory)*100:.4f}% |")
