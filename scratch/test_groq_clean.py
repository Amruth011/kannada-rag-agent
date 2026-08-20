# scratch/test_groq_clean.py
import os
import sys
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY is not set.")
    sys.exit(1)

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

def clean_page_groq(text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": CLEAN_PROMPT},
            {"role": "user", "content": text}
        ],
        "temperature": 0.2,
        "max_tokens": 1000
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code == 200:
        return resp.json()["choices"][0]["message"]["content"].strip()
    else:
        raise ValueError(f"HTTP {resp.status_code}: {resp.text}")

def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    page_num = 11
    kn_path = os.path.join(BASE_DIR, "data", "normalized_text", f"page_{page_num:04d}.txt")
    
    with open(kn_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
        
    print(f"--- ORIGINAL PAGE {page_num} KANNADA TEXT ---")
    print(raw_text[:400])
    print("...")
    
    print("\nCleaning page with Groq Llama-3.3-70b...")
    try:
        cleaned_text = clean_page_groq(raw_text)
        print(f"\n--- CLEANED PAGE {page_num} KANNADA TEXT ---")
        print(cleaned_text)
        print("---------------------------------------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
