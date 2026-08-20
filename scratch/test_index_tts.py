import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "api"))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Mock ADMIN_PASSWORD and other variables if needed, but they are already loaded from dotenv in index.py
from api.index import call_sarvam_tts
import time

text = "ಹಿಮವಂತ್ ಮತ್ತು ಪ್ರಾರ್ಥನಾ ಅವರ ನಡುವಿನ ಮಾತುಕತೆ ತುಂಬಾ ಅದ್ಭುತವಾಗಿತ್ತು. ಕಾದಂಬರಿಯಲ್ಲಿ ಇಬ್ಬರ ಪ್ರೀತಿ ಮತ್ತು ನೋವನ್ನು ಲೇಖಕರು ಅತ್ಯಂತ ಮಾರ್ಮಿಕವಾಗಿ ನಿರೂಪಿಸಿದ್ದಾರೆ. ಇವರ ಕಥೆಯು ಇಡೀ ಕಾದಂಬರಿಯ ಯಶಸ್ಸಿಗೆ ಕಾರಣವಾಗಿದೆ."
print("Testing call_sarvam_tts from index.py...")
t0 = time.time()
res = call_sarvam_tts(text, language="kn-IN")
t1 = time.time()
print(f"Success! Result length: {len(res) if res else 0}")
print(f"Time taken: {t1-t0:.2f} seconds")
