# scratch/test_gemini_lite.py
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

def test_model(model_name):
    print(f"Testing {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hello in Kannada")
        print(f"Success: {response.text.strip()}")
        return True
    except Exception as e:
        print(f"Failed for {model_name}: {e}")
        return False

def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    models = [
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash-lite-001",
        "gemini-flash-lite-latest",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-2.5-flash"
    ]
    for m in models:
        test_model(m)
        print("-" * 40)

if __name__ == "__main__":
    main()
