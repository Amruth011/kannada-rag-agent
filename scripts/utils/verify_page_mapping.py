import os
import chromadb

def run_diagnostics():
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="kannada_book")
    
    data = collection.get()
    
    docs = data.get("documents", [])
    metas = data.get("metadatas", [])
    
    page_to_chunks = {}
    
    for doc, meta in zip(docs, metas):
        page_val = meta.get("page")
        if page_val is not None:
            try:
                page_num = int(page_val)
                if page_num not in page_to_chunks:
                    page_to_chunks[page_num] = []
                page_to_chunks[page_num].append(doc)
            except ValueError:
                pass

    unique_pages = sorted(list(page_to_chunks.keys()))
    
    if not unique_pages:
        print("No pages found in metadata.")
        return
        
    min_page = unique_pages[0]
    max_page = unique_pages[-1]
    total_unique = len(unique_pages)
    
    expected_pages = set(range(min_page, max_page + 1))
    actual_pages = set(unique_pages)
    missing_pages = sorted(list(expected_pages - actual_pages))
    
    with open("diagnostic_output.txt", "w", encoding="utf-8") as f:
        f.write(f"Total Pages: {total_unique}\n")
        f.write(f"Minimum Page: {min_page}\n")
        f.write(f"Maximum Page: {max_page}\n")
        f.write(f"Unique Pages: {unique_pages}\n")
        f.write("\nPages Missing:\n")
        if missing_pages:
            for mp in missing_pages:
                f.write(f"{mp}\n")
        else:
            f.write("None\n")
            
        f.write("\nPage 99:\n")
        if 99 in page_to_chunks:
            f.write(f"Chunks: {len(page_to_chunks[99])}\n")
            f.write("\nSample:\n")
            f.write(f'"{page_to_chunks[99][0][:200]}..."\n')
        else:
            f.write("Chunks: 0\n")
            f.write("\nSample:\nNone\n")
            
        f.write("\nPage 100:\n")
        if 100 in page_to_chunks:
            f.write(f"Chunks: {len(page_to_chunks[100])}\n")
            f.write("\nSample:\n")
            f.write(f'"{page_to_chunks[100][0][:200]}..."\n')
        else:
            f.write("Chunks: 0\n")
            f.write("\nSample:\nNone\n")

if __name__ == "__main__":
    run_diagnostics()
