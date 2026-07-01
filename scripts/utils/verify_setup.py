"""
Run this after installing requirements:
    python verify_setup.py
All checks should show OK before moving to Phase 2.
"""

import sys

results = []

def check(label, fn):
    try:
        fn()
        results.append((label, True, ""))
    except Exception as e:
        results.append((label, False, str(e)))

# Python version
check("Python 3.10+", lambda: (
    (_ for _ in ()).throw(Exception(f"Need 3.10+, got {sys.version}"))
    if sys.version_info < (3, 10) else None
))

# Libraries
check("opencv-python",         lambda: __import__("cv2"))
check("Pillow",                lambda: __import__("PIL"))
check("pdf2image",             lambda: __import__("pdf2image"))
check("numpy",                 lambda: __import__("numpy"))
check("surya-ocr",             lambda: __import__("surya"))
check("indic-nlp-library",     lambda: __import__("indicnlp"))
check("sentence-transformers", lambda: __import__("sentence_transformers"))
check("chromadb",              lambda: __import__("chromadb"))
check("langchain",             lambda: __import__("langchain"))
check("streamlit",             lambda: __import__("streamlit"))
check("python-dotenv",         lambda: __import__("dotenv"))
check("requests",              lambda: __import__("requests"))

# Kannada normalizer works
def test_indic():
    from indicnlp.normalize.indic_normalize import IndicNormalizerFactory
    n = IndicNormalizerFactory().get_normalizer("kn")
    assert n.normalize("ಕನ್ನಡ") != ""
check("Kannada normalizer (kn)", test_indic)

# .env key set
def test_env():
    from dotenv import load_dotenv
    import os
    load_dotenv()
    key = os.getenv("SARVAM_API_KEY", "")
    assert key and key != "your_sarvam_api_key_here", \
        "Add your SARVAM_API_KEY to .env file"
check(".env → SARVAM_API_KEY set", test_env)

# Sarvam reachable
def test_sarvam():
    from dotenv import load_dotenv
    import os, requests
    load_dotenv()
    key = os.getenv("SARVAM_API_KEY", "")
    if not key or key == "your_sarvam_api_key_here":
        raise Exception("Key not set — skipping")
    r = requests.get("https://api.sarvam.ai/", timeout=5)
    assert r.status_code < 500
check("Sarvam API reachable", test_sarvam)

# ── Print results ──────────────────────────────
print()
print("=" * 52)
print("   KANNADA RAG — SETUP CHECK")
print("=" * 52)
for label, ok, err in results:
    icon = "✅" if ok else "❌"
    print(f"  {icon}  {label}")
    if err:
        print(f"       → {err}")
print("=" * 52)

failed = [r for r in results if not r[1]]
if not failed:
    print("\n  🎉 All good! Move to Phase 2.\n")
else:
    print(f"\n  ⚠️  {len(failed)} issue(s) to fix:\n")
    print("  1. pip install -r requirements.txt")
    print("  2. cp .env.example .env  →  add Sarvam key")
    print("  3. Get key free at: https://sarvam.ai\n")
