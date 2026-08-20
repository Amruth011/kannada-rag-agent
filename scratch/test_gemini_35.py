# scratch/test_gemini_35.py
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

def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("Testing gemini-3.5-flash...")
    try:
        model = genai.GenerativeModel("gemini-3.5-flash")
        response = model.generate_content("Say hello in Kannada")
        print(response.text.strip())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
