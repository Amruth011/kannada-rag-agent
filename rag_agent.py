# rag/rag_agent.py
# Phase 5 — RAG Agent with Sarvam-M
# Run: kannada-rag-env\Scripts\python.exe rag_agent.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ──────────────────────────────────────────
CHROMA_DIR           = r"chroma_db"
COLLECTION           = "kannada_book"
MODEL_NAME           = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SARVAM_API_KEY       = os.getenv("SARVAM_API_KEY", "")
SIMILARITY_THRESHOLD = 0.3
TOP_K                = 5
# ────────────────────────────────────────────────────

class KannadaRAGAgent:

    def __init__(self):
        print("🔄 Loading embedding model...")
        from sentence_transformers import SentenceTransformer
        self.embed_model = SentenceTransformer(MODEL_NAME)

        print("🗄️  Connecting to ChromaDB...")
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = client.get_collection(COLLECTION)
        print(f"✅ Ready — {self.collection.count()} chunks\n")

    def retrieve(self, query: str):
        query_embedding = self.embed_model.encode([query])[0].tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=TOP_K
        )
        chunks = []
        for i, doc in enumerate(results["documents"][0]):
            score = 1 - results["distances"][0][i]
            if score >= SIMILARITY_THRESHOLD:
                chunks.append({
                    "text" : doc,
                    "page" : results["metadatas"][0][i]["page"],
                    "score": round(score, 3)
                })
        return chunks

    def build_prompt(self, question: str, chunks: list, language: str = "kannada"):
        context = "\n\n".join([f"[Page {c['page']}]: {c['text']}" for c in chunks])

        if language == "english":
            return f"""You are an AI assistant for the Kannada book "Heli Hogu Karana".
Answer ONLY using the context below. If not found, say "This information is not in the book."
Always cite page numbers.

CONTEXT:
{context}

QUESTION: {question}

ANSWER (English, with page citations):"""
        else:
            return f"""ನೀವು "ಹೇಳಿ ಹೋಗು ಕಾರಣ" ಪುಸ್ತಕದ AI ಸಹಾಯಕರು.
ಕೆಳಗಿನ ಸನ್ನಿವೇಶ ಮಾತ್ರ ಬಳಸಿ ಉತ್ತರಿಸಿ. ಸಿಗದಿದ್ದರೆ "ಈ ಮಾಹಿತಿ ಪುಸ್ತಕದಲ್ಲಿ ಸಿಗಲಿಲ್ಲ" ಎಂದು ಹೇಳಿ.
ಪುಟ ಸಂಖ್ಯೆ ತಿಳಿಸಿ.

ಸನ್ನಿವೇಶ:
{context}

ಪ್ರಶ್ನೆ: {question}

ಉತ್ತರ (ಕನ್ನಡ, ಪುಟ ಸಂಖ್ಯೆಯೊಂದಿಗೆ):"""

    def call_sarvam(self, prompt: str):
        if not SARVAM_API_KEY:
            return "⚠️ SARVAM_API_KEY not set in .env"

        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "model"      : "sarvam-m",
            "messages"   : [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens" : 512
        }
        try:
            resp = requests.post(
                "https://api.sarvam.ai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            return f"❌ Sarvam API error: {e}"

    def answer(self, question: str, language: str = "kannada"):
        print(f"\n🔍 Searching: '{question}'")
        chunks = self.retrieve(question)

        if not chunks:
            msg = "ಈ ಮಾಹಿತಿ ಪುಸ್ತಕದಲ್ಲಿ ಸಿಗಲಿಲ್ಲ" if language == "kannada" else "Not found in the book."
            return {"answer": msg, "chunks": [], "pages": []}

        print(f"✅ {len(chunks)} chunks found (pages: {[c['page'] for c in chunks]})")
        prompt = self.build_prompt(question, chunks, language)
        answer = self.call_sarvam(prompt)
        pages  = sorted(set(c["page"] for c in chunks))
        return {"answer": answer, "chunks": chunks, "pages": pages}


if __name__ == "__main__":
    agent = KannadaRAGAgent()

    tests = [
        ("ಈ ಪುಸ್ತಕದ ಮುಖ್ಯ ವಿಷಯ ಏನು?", "kannada"),
        ("What is this book about?",     "english"),
    ]

    for question, lang in tests:
        print(f"\n{'='*50}")
        result = agent.answer(question, lang)
        print(f"Q : {question}")
        print(f"A : {result['answer']}")
        print(f"📄 Pages: {result['pages']}")