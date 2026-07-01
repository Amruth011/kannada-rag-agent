# ingest/preprocess_images.py
# Phase 2.2 — Clean raw images using OpenCV
# Removes bleed-through, fixes contrast, denoises
# Run: kannada-rag-env\Scripts\python.exe preprocess_images.py

import os
import cv2
import numpy as np
from tqdm import tqdm

# ── Config ──────────────────────────────────────────
INPUT_DIR  = r"data\raw_images"
OUTPUT_DIR = r"data\processed_images"
# ────────────────────────────────────────────────────

def preprocess(img_path, out_path):
    # Load image
    img = cv2.imread(img_path)
    if img is None:
        print(f"⚠️  Could not read: {img_path}")
        return False

    # Step 1: Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Step 2: Adaptive threshold
    # This removes shadows and bleed-through from opposite page
    # Best setting for your book (tested on your sample pages)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,   # Large block = better at removing bleed-through
        C=15            # Higher C = more aggressive cleaning
    )

    # Step 3: Denoise — removes small specks/noise
    denoised = cv2.fastNlMeansDenoising(
        binary,
        h=10,           # Filter strength — 10 is safe for Kannada strokes
        templateWindowSize=7,
        searchWindowSize=21
    )

    # Step 4: Slight sharpening — makes Kannada curves clearer for OCR
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, kernel)

    # Save processed image
    cv2.imwrite(out_path, sharpened)
    return True


def process_all(input_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    images = sorted([
        f for f in os.listdir(input_dir)
        if f.endswith(".png") or f.endswith(".jpg")
    ])

    if not images:
        print(f"❌ No images found in {input_dir}")
        return

    print(f"\n🖼️  Found {len(images)} images to process")
    print(f"📁 Output: {output_dir}\n")

    ok = 0
    for fname in tqdm(images, desc="Preprocessing"):
        in_path  = os.path.join(input_dir, fname)
        out_path = os.path.join(output_dir, fname)
        if preprocess(in_path, out_path):
            ok += 1

    print(f"\n✅ Done! {ok}/{len(images)} images processed")
    print(f"📁 Cleaned images saved to: {output_dir}")


if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR):
        print(f"❌ Input folder not found: {INPUT_DIR}")
        print("   Run pdf_to_images.py first")
    else:
        process_all(INPUT_DIR, OUTPUT_DIR)
