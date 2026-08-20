# scratch/test_groq_kn_few_shot.py
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

CLEAN_PROMPT_FEW_SHOT = """You are an expert Kannada proofreader and editor. You are given a page of raw OCR-extracted text from the famous Kannada novel 'ಹೇಳಿ ಹೋಗು ಕಾರಣ' (Heli Hogu Karana) by Ravi Belagere.

Your task:
1. Fix all OCR errors (such as random English letters, garbage symbols like ^, *, #, and misspelled Kannada words).
2. Reconstruct broken words and sentences to make them standard, readable Kannada.
3. Keep the meaning and character names (Himavant, Prarthana, etc.) intact.
4. Output ONLY the clean, corrected Kannada text. Do not write any explanations or notes.

Example 1:
Input:
೩೬`  ೬ಇ7L ೯,೯೯ ^೧ ಗಾನನ ನಗಸಯು ನೇಲ ಸ್ಟಲ್ಪ ಹೊತ್ತು ಸಮ್ಮನ ಕುಳತಿದ್ರಣ
Output:
ಗಣೇಶ ದೇವಸ್ಥಾನದ ನೆಲದ ಮೇಲೆ ಸ್ವಲ್ಪ ಹೊತ್ತು ಸುಮ್ಮನೆ ಕುಳಿತಿದ್ದಳು.

Example 2:
Input:
III:AI.I II(JCLJ KAkANA;^/vully IAVI IJlJL.ACYluIxl
Output:
ಹೇಳಿ ಹೋಗು ಕಾರಣ

Example 3:
Input:
ನಜತ್ಕೂನನೊಂದು ಜದಹು ಕೊಡತ್ತೀಯಾ ಹುನುತ್?
Output:
ನಿಜಕ್ಕೂ ನನಗೊಂದು ಬದುಕು ಕೊಡ್ತೀಯಾ ಹಿಮವಂತ್?
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
            {"role": "system", "content": CLEAN_PROMPT_FEW_SHOT},
            {"role": "user", "content": text}
        ],
        "temperature": 0.1,
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
        
    print("Cleaning page 11 with Llama-3.1-8b-instant few-shot...")
    try:
        cleaned_text = clean_page_groq(raw_text)
        print("\n--- CLEANED KANNADA TEXT ---")
        print(cleaned_text)
        print("----------------------------")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
