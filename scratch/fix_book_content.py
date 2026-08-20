# scratch/fix_book_content.py
# Fixes translation repetitions and Kannada OCR noise targetedly using Gemini 2.5 Flash Lite.
# Run: python scratch/fix_book_content.py

import os
import re
import sys
import time
import google.generativeai as genai
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY:
    print("[ERROR]: GEMINI_API_KEY is not set.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

KANNADA_DIR = os.path.join(BASE_DIR, "data", "normalized_text")
ENGLISH_DIR = os.path.join(BASE_DIR, "data", "english_translated")
REPORT_PATH = os.path.join(BASE_DIR, "scratch", "analysis_report.txt")

# Prompt to clean Kannada OCR noise
CLEAN_KN_PROMPT = """You are an expert editor for the Kannada novel 'ಹೇಳಿ ಹೋಗು ಕಾರಣ' (Heli Hogu Karana) by Ravi Belagere.
The text below contains severe OCR errors (random English letters, digits, garbage symbols like ^, *, #, and misspelled Kannada words).

Your task:
1. Fix all spelling, word boundaries, and grammatical errors in Kannada. Remove all Latin letters and garbage symbols.
2. Reconstruct any broken sentences so they make sense, flow naturally, and read like a professionally published Kannada novel.
3. Do not add any commentary, notes, or translations. Output ONLY the clean corrected Kannada text.
"""

# Prompt to translate Kannada to English with loop prevention
TRANSLATE_PROMPT = """Translate the following Kannada novel text into English. Keep character names consistent in English:
- Himavant
- Prarthana
- Shivamogga
- Channarayapatna
- Rasool Jamadar

CRITICAL RULES:
1. Do not repeat sentences or fall into translation loops. Do not duplicate paragraphs.
2. Write a clean, natural, and premium book-quality English translation.
3. Do not add any introduction, explanations, or footnotes. Output ONLY the English translation.
"""

def clean_kannada_text(text):
    for attempt in range(5):
        try:
            model = genai.GenerativeModel("gemini-2.5-flash-lite")
            prompt = f"{CLEAN_KN_PROMPT}\n\nRaw OCR Kannada Text:\n{text}"
            response = model.generate_content(prompt)
            cleaned = response.text.strip()
            if cleaned:
                return cleaned
        except Exception as e:
            print(f"      [WARNING] Kannada clean error (attempt {attempt+1}): {e}")
            time.sleep(15)
    raise ValueError("Failed to clean Kannada text after multiple retries.")

def translate_kannada_to_english(text):
    for attempt in range(5):
        try:
            model = genai.GenerativeModel("gemini-2.5-flash-lite")
            prompt = f"{TRANSLATE_PROMPT}\n\nKannada Text:\n{text}"
            response = model.generate_content(prompt)
            translated = response.text.strip()
            if translated and len(translated) > 10:
                return translated
        except Exception as e:
            print(f"      [WARNING] English translation error (attempt {attempt+1}): {e}")
            time.sleep(15)
    raise ValueError("Failed to translate Kannada text after multiple retries.")

def get_pages_with_issues():
    """Parses analysis_report.txt to identify page numbers containing loops or OCR noise."""
    if not os.path.exists(REPORT_PATH):
        print(f"[WARNING]: {REPORT_PATH} not found. Returning empty list.")
        return []
        
    pages = []
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Find patterns like "Page 014 (Kannada words: ..., English words: ...):"
    matches = re.finditer(r"Page (\d+) \(Kannada words: \d+, English words: \d+\):", content)
    for m in matches:
        page_num = int(m.group(1))
        
        # We only re-process if the page has actual loops/OCR issues (not just length mismatch)
        # Check the issues listed under this page
        start_idx = m.start()
        end_idx = content.find("Page ", m.end())
        if end_idx == -1:
            end_idx = len(content)
            
        page_section = content[start_idx:end_idx]
        
        # If it has repeated sentences, repeated phrases, or OCR noise, we fix it
        # We also fix page 11 targetedly (which we know has OCR noise even if it didn't trigger report)
        if "Repeated sentences:" in page_section or "Repeated phrases:" in page_section or "Kannada OCR noise:" in page_section:
            pages.append(page_num)
            
    # Add page 11 targetedly to make sure it's cleaned
    if 11 not in pages:
        pages.append(11)
        
    return sorted(list(set(pages)))

def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

    print("[RUN]: Running targeted e-book page fixer...")
    
    pages_to_fix = get_pages_with_issues()
    print(f"[INFO]: Found {len(pages_to_fix)} pages requiring quality fixes: {pages_to_fix}")
    
    # We also define the list of pages with severe Kannada OCR noise
    ocr_noise_pages = [2, 3, 11, 338, 341]
    
    count = 0
    for page_num in pages_to_fix:
        print(f"\n[PAGE {page_num:03d}] Processing...")
        
        kn_path = os.path.join(KANNADA_DIR, f"page_{page_num:04d}.txt")
        en_path = os.path.join(ENGLISH_DIR, f"page_{page_num:04d}.txt")
        
        if not os.path.exists(kn_path):
            print(f"   [WARNING]: Kannada file for page {page_num} not found. Skipping.")
            continue
            
        with open(kn_path, "r", encoding="utf-8") as f:
            kannada_text = f.read().strip()
            
        # 1. Clean Kannada text if it has OCR noise
        if page_num in ocr_noise_pages:
            print("   -> Cleaning Kannada OCR noise...")
            cleaned_kn = clean_kannada_text(kannada_text)
            
            # Save cleaned Kannada text back
            with open(kn_path, "w", encoding="utf-8") as f:
                f.write(cleaned_kn)
            kannada_text = cleaned_kn
            print("   -> Saved clean Kannada text.")
            time.sleep(4.5)  # RPM limit delay
            
        # 2. Re-translate to clean English (resolving loops)
        print("   -> Re-translating to English (loop prevention enabled)...")
        translated_en = translate_kannada_to_english(kannada_text)
        
        # Save translated English text back
        with open(en_path, "w", encoding="utf-8") as f:
            f.write(translated_en)
        print("   -> Saved clean English translation.")
        
        count += 1
        time.sleep(4.5)  # RPM limit delay
        
    print(f"\n[DONE]: Re-processed and fixed {count} pages.")
    
    # Compile ebooks
    print("\n[AUTO-COMPILE]: Compiling e-books with fixed content...")
    try:
        import subprocess
        compile_script = os.path.join(BASE_DIR, "scratch", "compile_ebook.py")
        subprocess.run([sys.executable, compile_script], check=True)
        print("[AUTO-COMPILE]: E-books successfully compiled!")
    except Exception as e:
        print(f"[AUTO-COMPILE-ERROR]: E-book compilation failed: {e}")

if __name__ == "__main__":
    main()
