# scratch/translate_book.py
# Programmatic page-by-page Kannada to English translation script
# Run: python scratch/translate_book.py --pages 5 (for testing) or python scratch/translate_book.py (for full book)

import os
import re
import sys
import time
import argparse
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load env variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

if not GEMINI_API_KEY and not GROQ_API_KEY:
    print("[ERROR]: Neither GEMINI_API_KEY nor GROQ_API_KEY found in .env file.")
    sys.exit(1)

# Configure Gemini if key exists
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"[WARNING]: Failed to configure Gemini SDK: {e}")

# Define directories
INPUT_DIR = os.path.join(BASE_DIR, "data", "normalized_text")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "english_translated")

# Translation Prompt
SYSTEM_PROMPT = """You are a professional literary translator specializing in translating Kannada literature to English.
Your goal is to translate the following page of the Kannada novel 'Heli Hogu Karana' (ಹೇಳಿ ಹೋಗು ಕಾರಣ) by Ravi Belagere into English.

Literary Guidelines:
1. Maintain the emotional depth, intense narrative tone, and writing style of the author.
2. Keep character names consistent in English:
   - ಹಿಮವಂತ -> Himavant
   - ಪ್ರಾರ್ಥನಾ -> Prarthana
   - ಶಿವಮೊಗ್ಗ -> Shivamogga
   - ಚನ್ನರಾಯಪಟ್ಟಣ -> Channarayapatna
   - ರಸೂಲ್ ಜಮಾದಾರ -> Rasool Jamadar
3. Translate the text accurately, sentence by sentence. Do NOT summarize or skip paragraphs.
4. Output ONLY the translated English text. Do not add any introductory or concluding comments, translator notes, or formatting markers.
"""

def get_best_gemini_model():
    """Helper to find the best available model for this specific API key."""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # Prefer 2.5 flash, 2.0 flash, then other flash models
        for model in models:
            if "gemini-2.5-flash" in model: return model
        for model in models:
            if "gemini-2.0-flash" in model: return model
        for model in models:
            if "gemini-flash-latest" in model: return model
        for model in models:
            if "gemini-1.5-flash" in model: return model
        for model in models:
            if "gemini-1.5-pro" in model: return model
        return models[0] if models else "gemini-1.5-flash"
    except Exception as e:
        print(f"[WARNING]: Error listing models: {e}. Defaulting to gemini-1.5-flash.")
        return "gemini-1.5-flash"

def translate_page_groq(page_num, text, model_name="auto"):
    """Translates a page of Kannada text using Groq API as a fallback or primary."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is missing.")
        
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text}
    ]
    
    # Check if a specific model was requested
    if model_name != "auto" and model_name:
        models = [model_name, "llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    else:
        models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    last_err = ""
    for model in models:
        # Retry up to 4 times per model for rate limits
        for attempt in range(4):
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 2048
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"].strip()
                elif resp.status_code == 429:
                    # Parse retry delay
                    retry_after = 20.0 # Default delay
                    try:
                        if "retry-after" in resp.headers:
                            retry_after = float(resp.headers["retry-after"])
                        else:
                            body = resp.json()
                            err_msg = body.get("error", {}).get("message", "")
                            match = re.search(r"retry in ([\d\.]+)s", err_msg, re.IGNORECASE)
                            if match:
                                retry_after = float(match.group(1)) + 1.0
                    except Exception:
                        pass
                    print(f"[RATE-LIMIT]: Groq 429 rate limit hit on {model} (Attempt {attempt+1}/4). Retrying in {retry_after:.1f} seconds...")
                    time.sleep(retry_after)
                    continue
                else:
                    last_err = f"HTTP {resp.status_code}: {resp.text}"
                    break # Break retry loop to try next model or raise error
            except Exception as e:
                last_err = str(e)
                time.sleep(2)
                
    raise ValueError(f"Groq translation failed: {last_err}")

def translate_page(page_num, text, model_name="auto", provider="auto"):
    """Translates a page of Kannada text using either Gemini (preferred) or Groq API."""
    
    if provider == "groq":
        return translate_page_groq(page_num, text, model_name)
        
    # Standard Gemini translation logic
    prompt = f"{SYSTEM_PROMPT}\n\n--- KANNADA TEXT (PAGE {page_num}) ---\n{text}\n\n--- ENGLISH TRANSLATION ---"
    
    # If Gemini key is not set, force Groq fallback immediately
    if not GEMINI_API_KEY:
        if GROQ_API_KEY:
            print(f"[FALLBACK]: Gemini API key not set. Using Groq Llama for page {page_num}...")
            return translate_page_groq(page_num, text)
        else:
            raise ValueError("Neither Gemini nor Groq API keys are configured.")
            
    # Retry logic for rate limits/network glitches
    max_retries = 3
    backoff = 2
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            translated_text = response.text.strip()
            
            # Simple validation to ensure we got a valid translation
            if translated_text and len(translated_text) > 10:
                return translated_text
            
            raise ValueError("Empty or too short translation response.")
        except Exception as e:
            # Check for quota exceeded or other rate limits
            is_quota_error = "429" in str(e) or "quota" in str(e).lower()
            
            if is_quota_error and GROQ_API_KEY:
                print(f"[FALLBACK]: Gemini quota exceeded on page {page_num} ({e}). Falling back to Groq Llama...")
                try:
                    return translate_page_groq(page_num, text)
                except Exception as groq_err:
                    print(f"[ERROR]: Groq fallback failed: {groq_err}")
            
            print(f"[WARNING]: Attempt {attempt + 1} failed for page {page_num}: {e}")
            if attempt == max_retries - 1:
                # If final attempt fails, try Groq fallback once more as a last resort
                if GROQ_API_KEY:
                    print(f"[FALLBACK]: Gemini failed completely. Trying Groq Llama as last resort for page {page_num}...")
                    return translate_page_groq(page_num, text)
                raise e
            time.sleep(backoff)
            backoff *= 2
            
    return None

def main():
    parser = argparse.ArgumentParser(description="Translate Kannada book pages to English.")
    parser.add_argument("--pages", type=int, default=0, help="Limit number of pages to translate in this run (0 for all).")
    parser.add_argument("--model", type=str, default="auto", help="Gemini model to use (default: auto).")
    parser.add_argument("--provider", type=str, default="auto", choices=["auto", "gemini", "groq"], help="LLM provider to use (default: auto).")
    args = parser.parse_args()
    
    # Resolve parameters
    model_name = args.model
    provider = args.provider
    
    # Force standard output to UTF-8 on Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    if not os.path.exists(INPUT_DIR):
        print(f"[ERROR]: Input directory {INPUT_DIR} does not exist. Please check your data ingestion pipeline.")
        sys.exit(1)
        
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Get all page files
    page_files = sorted([
        f for f in os.listdir(INPUT_DIR)
        if f.startswith("page_") and f.endswith(".txt")
    ])
    
    if not page_files:
        print("[ERROR]: No page files found in input directory.")
        sys.exit(1)
        
    if model_name == "auto" and (provider == "auto" or provider == "gemini") and GEMINI_API_KEY:
        model_name = get_best_gemini_model()
        
    print(f"[BOOK]: Starting translation using provider '{provider}' (model: '{model_name}')...")
    print(f"[DIR]: Source: {INPUT_DIR}")
    print(f"[DIR]: Destination: {OUTPUT_DIR}")
    print(f"[INFO]: Total pages found: {len(page_files)}")
    
    translated_count = 0
    skipped_count = 0
    pages_to_translate = args.pages
    
    for fname in page_files:
        # Extract page number
        match = re.search(r"page_(\d+)\.txt", fname)
        if not match:
            continue
            
        page_num = int(match.group(1))
        out_fname = f"page_{page_num:04d}.txt"
        out_path = os.path.join(OUTPUT_DIR, out_fname)
        
        # Check if already translated (Checkpointing)
        if os.path.exists(out_path):
            skipped_count += 1
            continue
            
        # Check if limit reached
        if pages_to_translate > 0 and translated_count >= pages_to_translate:
            print(f"\n[LIMIT]: Reached configured limit of {pages_to_translate} pages for this run.")
            break
            
        print(f"[RUN]: Translating page {page_num}...")
        
        in_path = os.path.join(INPUT_DIR, fname)
        with open(in_path, "r", encoding="utf-8") as f:
            kannada_text = f.read().strip()
            
        if not kannada_text:
            print(f"[INFO]: Page {page_num} is empty, skipping.")
            # Create an empty file to mark it as processed
            with open(out_path, "w", encoding="utf-8") as out_f:
                out_f.write("")
            continue
            
        try:
            english_text = translate_page(page_num, kannada_text, model_name, provider=provider)
            with open(out_path, "w", encoding="utf-8") as out_f:
                out_f.write(english_text)
            
            translated_count += 1
            print(f"[SUCCESS]: Page {page_num} translated and saved.")
            
            # Rate limit politeness delay: longer for Groq to protect TPM limits
            delay = 5.0 if provider == "groq" or (provider == "auto" and not GEMINI_API_KEY) else 1.5
            time.sleep(delay)
            
        except Exception as e:
            print(f"[ERROR]: Failed to translate page {page_num}. Stopping pipeline.")
            print(f"Error: {e}")
            break
            
    print(f"\n[DONE]: Translation run finished!")
    print(f"   Skipped (already translated): {skipped_count}")
    print(f"   Newly translated           : {translated_count}")
    print(f"   Total translated pages     : {skipped_count + translated_count}/{len(page_files)}")
    
    # Write a status summary
    status_file = os.path.join(OUTPUT_DIR, "_translation_summary.json")
    import json
    with open(status_file, "w", encoding="utf-8") as sf:
        json.dump({
            "total_pages": len(page_files),
            "translated_pages": skipped_count + translated_count,
            "status": "complete" if (skipped_count + translated_count) >= len(page_files) else "in_progress",
            "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
        }, sf, indent=2)

    # Auto-compile e-books at the end of the run
    print("\n[AUTO-COMPILE]: Compiling e-books with latest translations...")
    try:
        import subprocess
        compile_script = os.path.join(BASE_DIR, "scratch", "compile_ebook.py")
        subprocess.run([sys.executable, compile_script], check=True)
        print("[AUTO-COMPILE]: E-books compiled successfully!")
    except Exception as e:
        print(f"[AUTO-COMPILE-ERROR]: Failed to compile e-books: {e}")

if __name__ == "__main__":
    main()
