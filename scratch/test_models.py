# scratch/test_models.py
import google.generativeai as genai
import os
import sys
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
genai.configure(api_key=GEMINI_API_KEY)

models = [
    'models/gemini-2.5-flash',
    'models/gemini-3.5-flash',
    'models/gemini-2.5-pro',
    'models/gemini-2.5-flash-lite',
    'models/gemini-flash-latest',
    'models/gemini-2.0-flash',
    'models/gemini-1.5-pro'
]

print("--- TESTING GEMINI MODELS ---")
for model_name in models:
    print(f"Testing {model_name}...", end=" ", flush=True)
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello")
        print(f"SUCCESS: {response.text.strip()}")
    except Exception as e:
        err_msg = str(e)
        if "quota" in err_msg.lower() or "429" in err_msg:
            print("FAILED (Quota/Rate Limit)")
        else:
            print(f"FAILED: {err_msg[:100]}")

print("\n--- TESTING GROQ MODELS ---")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
if GROQ_API_KEY:
    import requests
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    groq_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "gemma2-9b-it",
        "mixtral-8x7b-32768"
    ]
    for m in groq_models:
        print(f"Testing Groq {m}...", end=" ", flush=True)
        try:
            payload = {
                "model": m,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 10
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=5)
            if resp.status_code == 200:
                print("SUCCESS")
            else:
                print(f"FAILED (HTTP {resp.status_code}): {resp.text[:100]}")
        except Exception as e:
            print(f"FAILED: {e}")
else:
    print("Groq API Key not found.")
