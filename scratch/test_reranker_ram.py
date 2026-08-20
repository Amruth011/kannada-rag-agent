import os
import sys
import psutil

process = psutil.Process(os.getpid())
def get_ram():
    return process.memory_info().rss / (1024 * 1024)

print("Baseline RAM:", get_ram())

from sentence_transformers import CrossEncoder

before = get_ram()
model_name = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
print(f"Loading {model_name}...")
model = CrossEncoder(model_name, max_length=512)
after = get_ram()
print(f"Loaded {model_name}. Delta RAM: {after - before:.2f} MB")

# Test prediction
before_pred = get_ram()
pairs = [("ಹಿಮವಂತ ಯಾರು?", "ಹಿಮವಂತ ಪ್ರಮುಖ ಪಾತ್ರ.")] * 10
scores = model.predict(pairs)
after_pred = get_ram()
print(f"Prediction done. Delta RAM during prediction: {after_pred - before_pred:.2f} MB")
print(f"Total Process RAM: {get_ram():.2f} MB")
