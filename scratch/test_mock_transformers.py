import sys
import psutil
from unittest.mock import MagicMock

process = psutil.Process(os.getpid() if 'os' in globals() else 0)
# We need to import os to get pid
import os
process = psutil.Process(os.getpid())

def get_ram():
    return process.memory_info().rss / (1024 * 1024)

print("Baseline RAM:", get_ram())

# Mock transformers to prevent loading it and torch
sys.modules['transformers'] = MagicMock()

before = get_ram()
print("Importing langchain_google_genai with mocked transformers...")
import langchain_google_genai
after = get_ram()
print(f"Import complete. RAM Delta: {after - before:.2f} MB")
print("Is torch in sys.modules?", 'torch' in sys.modules)
print("Is transformers in sys.modules?", 'transformers' in sys.modules)
print("Total RAM:", get_ram())
