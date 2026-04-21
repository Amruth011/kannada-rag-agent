import os
import chromadb
import numpy as np

def export_to_numpy():
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path="chroma_db")
    collection = client.get_collection("kannada_book")
    
    # Get all data
    data = collection.get(include=["embeddings", "documents", "metadatas"])
    
    ids = data["ids"]
    embeddings = np.array(data["embeddings"])
    documents = np.array(data["documents"])
    pages = np.array([m["page"] for m in data["metadatas"]])
    
    print(f"Exporting {len(ids)} chunks...")
    
    # Save as compressed NumPy file
    np.savez_compressed(
        "vectors.npz",
        embeddings=embeddings,
        documents=documents,
        pages=pages
    )
    
    print(f"Successfully exported to vectors.npz ({os.path.getsize('vectors.npz') / 1024:.2f} KB)")

if __name__ == "__main__":
    export_to_numpy()
