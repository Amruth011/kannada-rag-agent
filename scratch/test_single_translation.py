# scratch/test_single_translation.py
import google.generativeai as genai
from google.api_core import retry
import os
import sys
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
genai.configure(api_key=GEMINI_API_KEY)

text = open("data/normalized_text/page_0209.txt", "r", encoding="utf-8").read().strip()
# Wait, let's actually use page 309 text!
text_309 = open("data/normalized_text/page_0309.txt", "r", encoding="utf-8").read().strip()

model_name = "models/gemini-flash-lite-latest"
print(f"Testing model {model_name} on page 309 with safety settings...")

# Disable retries completely to see the exact API response or error
no_retry = retry.Retry(predicate=lambda e: False)

# Set safety settings to BLOCK_NONE
safety_settings = [
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    }
]

try:
    model = genai.GenerativeModel(model_name)
    SYSTEM_PROMPT = """Translate the following Kannada novel page into English. Keep character names consistent in English:
- Himavant
- Prarthana
- Shivamogga
- Channarayapatna
- Rasool Jamadar
Do not add any comments or notes. Translate accurately:"""
    prompt = f"{SYSTEM_PROMPT}\n\n{text_309}"
    response = model.generate_content(
        prompt,
        safety_settings=safety_settings,
        request_options={
            "timeout": 30.0,
            "retry": no_retry
        }
    )
    print("SUCCESS!")
    print(f"Translated text: {response.text[:300]}...")
except Exception as e:
    print(f"FAILED with error: {type(e).__name__}: {e}")
