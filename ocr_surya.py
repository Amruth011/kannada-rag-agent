# ingest/ocr_surya.py
# Phase 2.3 — EasyOCR (Kannada support, no compatibility issues)
# Run: kannada-rag-env\Scripts\python.exe ocr_surya.py

import os
import json
import easyocr
from PIL import Image
from tqdm import tqdm

# ── Config ──────────────────────────────────────────
INPUT_DIR  = r"data\processed_images"
OUTPUT_DIR = r"data\cleaned_text"
# ────────────────────────────────────────────────────

def run_ocr_pipeline(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    images = sorted([
        f for f in os.listdir(input_dir)
        if f.endswith(".png") or f.endswith(".jpg")
    ])

    if not images:
        print(f"❌ No images in {input_dir}")
        return

    print(f"📄 Found {len(images)} images to OCR\n")

    print("🔄 Loading EasyOCR model (downloading on first run ~500MB)...")
    # kn = Kannada, en = English (handles mixed pages like copyright page)
    reader = easyocr.Reader(['kn', 'en'], gpu=False)
    print("✅ Model loaded\n")

    processed = 0
    failed    = []

    for fname in tqdm(images, desc="Running OCR"):
        txt_path = os.path.join(output_dir, fname.replace(".png", ".txt"))

        # Resume — skip already done pages
        if os.path.exists(txt_path):
            continue

        img_path = os.path.join(input_dir, fname)
        try:
            results = reader.readtext(img_path, detail=0, paragraph=True)
            text    = "\n".join([r for r in results if r.strip()])

            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            processed += 1

        except Exception as e:
            failed.append((fname, str(e)))

    print(f"\n✅ OCR complete!")
    print(f"   Processed : {processed}")
    print(f"   Failed    : {len(failed)}")
    if failed:
        for f, e in failed[:5]:
            print(f"   ⚠️  {f} → {e}")

    with open(os.path.join(output_dir, "_ocr_summary.json"), "w") as f:
        json.dump({"processed": processed, "failed": len(failed)}, f)


if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR):
        print(f"❌ Not found: {INPUT_DIR} — run preprocess_images.py first")
    else:
        run_ocr_pipeline(INPUT_DIR, OUTPUT_DIR)