# ingest/ocr_surya.py
# Phase 2.3 — Surya OCR (State-of-the-art Kannada support)
# Run: kannada-rag-env\Scripts\python.exe ocr_surya.py

import os
import json
from PIL import Image
from tqdm import tqdm

from surya.common.surya.schema import TaskNames
from surya.detection import DetectionPredictor
from surya.foundation import FoundationPredictor
from surya.recognition import RecognitionPredictor

# Load models/predictors once
foundation_predictor = FoundationPredictor()
det_predictor = DetectionPredictor()
rec_predictor = RecognitionPredictor(foundation_predictor)

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

    print("✅ Models loaded\n")

    processed = 0
    failed    = []

    BATCH_SIZE = 8
    print(f"🔄 Using Batch Size: {BATCH_SIZE}\n")

    for i in tqdm(range(0, len(images), BATCH_SIZE), desc="Running OCR in Batches"):
        batch_fnames = images[i:i + BATCH_SIZE]
        batch_images = []
        batch_img_paths = [] # Initialize batch_img_paths here
        
        for fname in batch_fnames:
            img_path = os.path.join(input_dir, fname)
            batch_images.append(Image.open(img_path))
            batch_img_paths.append(img_path) # Store full path

        try:
            # Run recognition on the batch of 8 images using the v0.17 Predictor API
            task_names = [TaskNames.ocr_with_boxes] * len(batch_images)
            predictions = rec_predictor(
                batch_images, 
                task_names=task_names,
                det_predictor=det_predictor,
                recognition_batch_size=8,
                detection_batch_size=8
            )
            
            # Unpack results and save
            for img_path, pred in zip(batch_img_paths, predictions):
                base_name = os.path.basename(img_path)
                
                # Extract recognized text strings from the prediction objects
                try:
                    # Based on the new Surya inference output dict/object structure
                    extracted_lines = [line.text for line in pred.text_lines]
                    full_text = "\\n".join(extracted_lines)
                except Exception as e:
                    # Fallback if structure is slightly different
                    full_text = str(pred)

                # Save to file, similar to original logic
                txt_path = os.path.join(output_dir, base_name.replace(".png", ".txt").replace(".jpg", ".txt"))
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                processed += 1

        except Exception as e:
            for fname in batch_fnames:
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