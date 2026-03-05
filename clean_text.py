# ingest/clean_text.py
# Phase 2.4 — Normalize Kannada Unicode from OCR output
# Run: kannada-rag-env\Scripts\python.exe clean_text.py

import os
import json
from tqdm import tqdm

# ── Config ──────────────────────────────────────────
INPUT_DIR  = r"data\cleaned_text"
OUTPUT_DIR = r"data\normalized_text"
# ────────────────────────────────────────────────────

def normalize_kannada(text):
    from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
    factory    = IndicNormalizerFactory()
    normalizer = factory.get_normalizer("kn")
    
    lines     = text.split("\n")
    cleaned   = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Normalize Unicode
        line = normalizer.normalize(line)
        # Remove lines that are too short to be real text (OCR noise)
        if len(line) < 3:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def clean_all(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    txt_files = sorted([
        f for f in os.listdir(input_dir)
        if f.endswith(".txt") and not f.startswith("_")
    ])

    if not txt_files:
        print(f"❌ No .txt files found in {input_dir}")
        return

    print(f"📄 Found {len(txt_files)} text files to clean\n")

    processed = 0
    empty     = 0

    for fname in tqdm(txt_files, desc="Cleaning"):
        in_path  = os.path.join(input_dir, fname)
        out_path = os.path.join(output_dir, fname)

        with open(in_path, "r", encoding="utf-8") as f:
            raw = f.read()

        cleaned = normalize_kannada(raw)

        if not cleaned.strip():
            empty += 1
            continue

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        processed += 1

    print(f"\n✅ Done!")
    print(f"   Cleaned  : {processed}")
    print(f"   Empty    : {empty} (cover/blank pages — skipped)")
    print(f"   Output   : {output_dir}")

    # Show sample from page 4 (dedication page — good test)
    sample = os.path.join(output_dir, "page_0004.txt")
    if os.path.exists(sample):
        print(f"\n📖 Sample (page 4):")
        print("-" * 40)
        with open(sample, "r", encoding="utf-8") as f:
            print(f.read()[:300])
        print("-" * 40)

    with open(os.path.join(output_dir, "_clean_summary.json"), "w") as f:
        json.dump({"cleaned": processed, "empty_skipped": empty}, f)


if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR):
        print(f"❌ Not found: {INPUT_DIR} — run ocr_surya.py first")
    else:
        clean_all(INPUT_DIR, OUTPUT_DIR)
