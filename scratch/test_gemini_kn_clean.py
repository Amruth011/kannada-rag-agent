# scratch/test_gemini_kn_clean.py
import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    sys.exit(1)

genai.configure(api_key=GEMINI_API_KEY)

CLEAN_PROMPT = """You are an expert Kannada proofreader and editor. You are given a page of raw OCR-extracted text from the famous Kannada novel 'ಹೇಳಿ ಹೋಗು ಕಾರಣ' (Heli Hogu Karana) by Ravi Belagere.
The text contains OCR errors, such as:
- Random English letters (like C, L, etc.) mixed with Kannada words.
- Garbage symbols (like ^, *, #, etc.).
- Incorrectly merged or split words.
- Misspelled Kannada words due to low OCR quality.

Your task:
1. Clean up the text. Correct all misspelled Kannada words, remove all random English letters and noise symbols.
2. Reconstruct any broken sentences or words so they make grammatical sense and flow naturally in standard Kannada.
3. Keep the meaning, characters (Himavant, Prarthana, etc.), and story exactly as written.
4. Output ONLY the clean, corrected Kannada text. Do not add any introduction, explanations, or notes.
"""

def clean_page(text):
    model = genai.GenerativeModel("gemini-3.5-flash")
    prompt = f"{CLEAN_PROMPT}\n\nRaw OCR Text:\n{text}"
    response = model.generate_content(prompt)
    return response.text.strip()

def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    page_num = 11
    kn_path = os.path.join(BASE_DIR, "data", "normalized_text", f"page_{page_num:04d}.txt")
    
    with open(kn_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
        
    print("Cleaning page 11 with Gemini-3.5-flash...")
    try:
        cleaned_text = clean_page(raw_text)
        print("\n--- CLEANED KANNADA TEXT ---")
        print(cleaned_text)
        print("----------------------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
