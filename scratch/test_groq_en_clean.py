# scratch/test_groq_en_clean.py
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

PROOFREAD_PROMPT = """You are an expert English book editor. You are given a page of a translated novel that contains errors, especially:
- Severe word or sentence repetitions (e.g. sentences or phrases repeated multiple times in a row).
- Loops where the model got stuck repeating the same text.
- Minor translation flow issues.

Your task:
1. Proofread and clean the English text. Remove all repetitive sentences, phrases, and word loops.
2. Keep only one clean instance of the text. Ensure the narrative flows naturally, is grammatically correct, and sounds like a professional novel.
3. Do not add any introduction, explanations, or notes. Output ONLY the clean, polished English text.
"""

def clean_english_groq(text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": PROOFREAD_PROMPT},
            {"role": "user", "content": text}
        ],
        "temperature": 0.1,
        "max_tokens": 1200
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

    page_num = 14
    en_path = os.path.join(BASE_DIR, "data", "english_translated", f"page_{page_num:04d}.txt")
    
    with open(en_path, "r", encoding="utf-8") as f:
        raw_text = f.read()
        
    print(f"--- ORIGINAL PAGE {page_num} ENGLISH TEXT (first 400 chars) ---")
    print(raw_text[:400])
    print("...")
    
    print("\nCleaning English text with Groq llama-3.1-8b-instant...")
    try:
        cleaned_text = clean_english_groq(raw_text)
        print(f"\n--- CLEANED PAGE {page_num} ENGLISH TEXT ---")
        print(cleaned_text)
        print("---------------------------------------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
