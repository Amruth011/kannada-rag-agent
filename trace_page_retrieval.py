import os
import chromadb
import sys
import re

def is_page_only_query(query: str) -> bool:
    query = query.lower().strip(" ?.")
    query = re.sub(r'\b(what|is|on|summarize|explain|tell|me|about|the|content|of|in|page|number|ಪುಟ|ದಲ್ಲಿ|ಏನಿದೆ|ಬಗ್ಗೆ|ಹೇಳಿ)\b', '', query).strip()
    return bool(re.fullmatch(r'\d+', query))

def detect_page_filter(question: str):
    range_match = re.search(r'pages?\s*(\d+)\s*(?:to|through|–|-)\s*(\d+)|ಪುಟಗಳು?\s*(\d+)\s*(?:ರಿಂದ|ಇಂದ|-)\s*(\d+)', question, re.IGNORECASE)
    if range_match:
        groups = [g for g in range_match.groups() if g is not None]
        if len(groups) == 2:
            return None, (int(groups[0]), int(groups[1]))

    page_match = re.search(r'page\s*(\d+)|ಪುಟ\s*(\d+)|(\d+)\s*(?:page|ಪುಟ)', question, re.IGNORECASE)
    if page_match:
        return int(next(g for g in page_match.groups() if g)), None
    return None, None

def trace_retrieval(query: str):
    print(f"--- DIAGNOSTIC TRACE FOR: '{query}' ---")
    page, page_range = detect_page_filter(query)
    print(f"\n1. Detected page number: {page} (Range: {page_range})")
    
    page_only = is_page_only_query(query) if page else False
    print(f"2. Router path selected: {'Metadata Filter Bypass' if page_only else 'Hybrid Search Routing'}")
    
    if not page_only:
        print("\nTrace stopping: Query was not routed to the Page Query Router.")
        return
        
    print(f"\n3. Metadata filter used:\nwhere={{\"page\": {page}}}")
    
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="kannada_book")
    
    # Try integer
    data_int = collection.get(where={"page": page})
    
    # Try string just in case
    data_str = collection.get(where={"page": str(page)})
    
    actual_data = data_int if len(data_int.get('documents', [])) > 0 else data_str
    used_type = "int" if len(data_int.get('documents', [])) > 0 else "string" if len(data_str.get('documents', [])) > 0 else "none"
    
    chunks = actual_data.get("documents", [])
    metas = actual_data.get("metadatas", [])
    ids = actual_data.get("ids", [])
    
    print(f"\n4. Number of chunks returned: {len(chunks)}")
    print(f"\n5. Returned chunk IDs: {ids}")
    print(f"\n6. Returned page metadata: {[m.get('page') for m in metas]}")
    
    print("\n7. First 300 characters of each chunk:")
    for i, c in enumerate(chunks):
        print(f"\n--- Chunk {i+1} ---")
        try:
            print(c[:300])
        except UnicodeEncodeError:
            print(c[:300].encode('utf-8', 'ignore').decode('utf-8', 'ignore'))
            
    print(f"\n8. Fallback logic triggered: {not chunks}")
    print(f"9. Guardrail logic triggered: False (Bypassed by router)")
    
    print("\n10. Exact reason why final response says page 100 content was unavailable:")
    if not chunks:
        print("The `where` metadata filter query returned 0 results. This likely means the metadata key 'page' is stored as a different type (string vs int) or the page number doesn't match the query filter.")
        print(f"Debug Info: int query returned {len(data_int.get('documents', []))}, string query returned {len(data_str.get('documents', []))}.")
    else:
        print("Chunks were found successfully. If the UI says unavailable, there is a bug in the UI rendering code, not the retrieval code.")

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')
    trace_retrieval("Summarize page 100")
