# vectorstore/embed_and_store.py
# Phase 4 — Generate embeddings and store in ChromaDB
# Run: kannada-rag-env\Scripts\python.exe embed_and_store.py

import os
import json
from tqdm import tqdm

# ── Config ──────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
CHUNKS_FILE = os.path.join(BASE_DIR, "data", "chunks.json")
CHROMA_DIR  = os.path.join(BASE_DIR, "chroma_db")
COLLECTION  = "kannada_book"
BATCH_SIZE  = 32
# Small 90MB multilingual model — supports Kannada, no RAM issues
MODEL_NAME  = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# ────────────────────────────────────────────────────

def build_vectorstore():
    print("📂 Loading chunks...")
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"✅ Loaded {len(chunks)} chunks\n")

    print(f"🔄 Loading embedding model (downloading ~90MB)...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    print("✅ Model loaded\n")

    print("🗄️  Initializing ChromaDB...")
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        client.delete_collection(COLLECTION)
        print("   Cleared existing collection")
    except:
        pass

    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )
    print(f"✅ Collection '{COLLECTION}' ready\n")

    print(f"🧠 Embedding {len(chunks)} chunks...\n")

    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Embedding"):
        batch      = chunks[i:i+BATCH_SIZE]
        texts      = [c["text"]     for c in batch]
        ids        = [c["chunk_id"] for c in batch]
        metadatas  = [{"page": c["page"], "source": c["source"]} for c in batch]
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

    print(f"\n✅ Done!")
    print(f"   Chunks stored : {collection.count()}")
    print(f"   ChromaDB path : {CHROMA_DIR}")

    # Test search
    print(f"\n🔍 Testing search...")
    test_query      = "ಕಾದಂಬರಿ"
    query_embedding = model.encode([test_query])[0].tolist()
    results         = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )
    print(f"   Query : '{test_query}'")
    print(f"   Top result (page {results['metadatas'][0][0]['page']}):")
    print(f"   {results['documents'][0][0][:150]}")
    print(f"\n✅ Vector store working correctly!")


if __name__ == "__main__":
    if not os.path.exists(CHUNKS_FILE):
        print(f"❌ Not found: {CHUNKS_FILE} — run chunker.py first")
    else:
        build_vectorstore()