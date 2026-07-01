# ingest/pdf_to_images.py
# Phase 2.1 — Convert PDF pages to PNG images (batch mode)
# Run: kannada-rag-env\Scripts\python.exe pdf_to_images.py

import os
from pdf2image import convert_from_path
from pdf2image.pdf2image import pdfinfo_from_path
from tqdm import tqdm

# ── Config ──────────────────────────────────────────
PDF_PATH     = r"data\Heli hogu kaarana.pdf"
OUTPUT_DIR   = r"data\raw_images"
DPI          = 200       # Reduced to save memory — still great for OCR
IMG_FORMAT   = "PNG"
POPPLER_PATH = r"poppler-25.12.0\Library\bin"
BATCH_SIZE   = 10        # Process 10 pages at a time
# ────────────────────────────────────────────────────

def pdf_to_images(pdf_path, output_dir, dpi=200):
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n📄 Loading PDF: {pdf_path}")
    print(f"📁 Saving images to: {output_dir}")
    print(f"🔍 DPI: {dpi} | Batch size: {BATCH_SIZE}\n")

    # Get total page count without loading all pages into RAM
    info  = pdfinfo_from_path(pdf_path, poppler_path=POPPLER_PATH)
    total = info["Pages"]
    print(f"✅ Found {total} pages — processing in batches\n")

    saved = []
    for start in tqdm(range(1, total + 1, BATCH_SIZE), desc="Converting"):
        end = min(start + BATCH_SIZE - 1, total)

        pages = convert_from_path(
            pdf_path,
            dpi=dpi,
            poppler_path=POPPLER_PATH,
            first_page=start,
            last_page=end
        )

        for i, page in enumerate(pages):
            page_num = start + i
            filename = f"page_{page_num:04d}.png"
            filepath = os.path.join(output_dir, filename)
            page.save(filepath, IMG_FORMAT)
            saved.append(filepath)

        del pages  # free RAM after each batch

    print(f"\n✅ Done! {len(saved)} images saved to '{output_dir}'")
    return saved


if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"❌ PDF not found at: {PDF_PATH}")
        print("   Make sure 'Heli hogu kaarana.pdf' is in the data/ folder")
    else:
        images = pdf_to_images(PDF_PATH, OUTPUT_DIR, DPI)
        print(f"\n🖼️  First 3 images:")
        for p in images[:3]:
            print(f"   {p}")