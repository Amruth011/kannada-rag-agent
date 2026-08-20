# scratch/list_groq_models.py
import requests
import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

if GROQ_API_KEY:
    url = "https://api.groq.com/openai/v1/models"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
    }
    try:
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            print("--- ACTIVE GROQ MODELS ---")
            for m in data:
                print(m.get("id"))
        else:
            print(f"Failed to fetch models (HTTP {resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("GROQ_API_KEY not found.")
