# ingest/chunker.py
# Phase 3 — Split normalized text into chunks for RAG
# Run: kannada-rag-env\Scripts\python.exe chunker.py

import os
import json
from tqdm import tqdm

# ── Config ──────────────────────────────────────────
INPUT_DIR   = r"data\normalized_text"
OUTPUT_FILE = r"data\chunks.json"
CHUNK_SIZE  = 400    # characters per chunk
OVERLAP     = 50     # overlap between chunks
SOURCE_NAME = "heli_hogu_karana"
# ────────────────────────────────────────────────────

def split_into_chunks(text, page_num, chunk_size=400, overlap=50):
    """Split text into overlapping chunks, respecting Kannada sentence boundaries."""
    
    # Split on Kannada danda (।) and newlines first
    sentences = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        # Split on Kannada sentence boundary
        parts = para.replace("।", "।\n").split("\n")
        sentences.extend([p.strip() for p in parts if p.strip()])

    chunks    = []
    current   = ""
    chunk_idx = 0

    for sentence in sentences:
        # If adding this sentence exceeds chunk size, save current chunk
        if len(current) + len(sentence) > chunk_size and current:
            chunks.append({
                "chunk_id"  : f"{SOURCE_NAME}_p{page_num:04d}_c{chunk_idx:03d}",
                "text"      : current.strip(),
                "page"      : page_num,
                "source"    : SOURCE_NAME,
                "char_count": len(current.strip())
            })
            # Keep overlap — last N chars of current chunk
            current   = current[-overlap:] + " " + sentence
            chunk_idx += 1
        else:
            current += " " + sentence if current else sentence

    # Save the last remaining chunk
    if current.strip():
        chunks.append({
            "chunk_id"  : f"{SOURCE_NAME}_p{page_num:04d}_c{chunk_idx:03d}",
            "text"      : current.strip(),
            "page"      : page_num,
            "source"    : SOURCE_NAME,
            "char_count": len(current.strip())
        })

    return chunks


def chunk_all(input_dir, output_file):
    txt_files = sorted([
        f for f in os.listdir(input_dir)
        if f.endswith(".txt") and not f.startswith("_")
    ])

    if not txt_files:
        print(f"❌ No files in {input_dir}")
        return

    print(f"📄 Found {len(txt_files)} pages to chunk\n")

    all_chunks = []

    for fname in tqdm(txt_files, desc="Chunking"):
        page_num = int(fname.replace("page_", "").replace(".txt", ""))
        fpath    = os.path.join(input_dir, fname)

        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()

        if not text.strip():
            continue

        chunks = split_into_chunks(text, page_num, CHUNK_SIZE, OVERLAP)
        all_chunks.extend(chunks)

    # Save all chunks to JSON
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Done!")
    print(f"   Total chunks : {len(all_chunks)}")
    print(f"   Pages        : {len(txt_files)}")
    print(f"   Avg per page : {len(all_chunks)//len(txt_files)}")
    print(f"   Saved to     : {output_file}")

    # Show sample chunk
    if all_chunks:
        print(f"\n📖 Sample chunk:")
        print("-" * 40)
        sample = all_chunks[10] if len(all_chunks) > 10 else all_chunks[0]
        print(f"ID   : {sample['chunk_id']}")
        print(f"Page : {sample['page']}")
        print(f"Text : {sample['text'][:200]}")
        print("-" * 40)


if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR):
        print(f"❌ Not found: {INPUT_DIR} — run clean_text.py first")
    else:
        chunk_all(INPUT_DIR, OUTPUT_FILE)
