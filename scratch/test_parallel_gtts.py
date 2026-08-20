import time
import base64
import requests
from concurrent.futures import ThreadPoolExecutor
import re

test_text = """ಪ್ರಾರ್ಥನಾ ಮತ್ತು ಹಿಮವಂತ್ ಅವರ ಪ್ರೇಮ ಕಥೆಯು ಈ ಕಾದಂಬರಿಯ ಜೀವಾಳವಾಗಿದೆ. ರವಿ ಮತ್ತು ಬೆಳಗೆರೆ ಅವರ ಪಾತ್ರಗಳು ಕಥೆಗೆ ಹೊಸ ಆಯಾಮವನ್ನು ನೀಡುತ್ತವೆ. ಕಾದಂಬರಿಯ ಕೊನೆಯ ಭಾಗದಲ್ಲಿ ಹಿಮವಂತ್ ಕೈಗೊಂಡ ನಿರ್ಧಾರಗಳು ಅವನ ಬದುಕಿನ ಹಾದಿಯನ್ನು ಬದಲಾಯಿಸುತ್ತವೆ. ಮೌನ ಮತ್ತು ಸಂಭಾಷಣೆಗಳ ಮೂಲಕ ಲೇಖಕರು ಮಾನವ ಸಂಬಂಧಗಳ ಸಂಕೀರ್ಣತೆಯನ್ನು ಸುಂದರವಾಗಿ ಚಿತ್ರಿಸಿದ್ದಾರೆ. ಪುಟ 338 ಮತ್ತು 341 ರಲ್ಲಿ ಬರುವ ಸಂಭಾಷಣೆಗಳು ಓದುಗರಲ್ಲಿ ಗಾಢವಾದ ಭಾವನೆಗಳನ್ನು ಮೂಡಿಸುತ್ತವೆ. ಪ್ರತಿಯೊಬ್ಬ ಪಾತ್ರಕ್ಕೂ ತನ್ನದೇ ಆದ ಹಿನ್ನೆಲೆ ಮತ್ತು ಕಥೆಯಿದೆ, ಇದು ಒಟ್ಟಾರೆ ಕಾದಂಬರಿಯನ್ನು ಒಂದು ಅದ್ಭುತ ಓದುವ ಅನುಭವವಾಗಿಸುತ್ತದೆ. ನಿಮ್ಮ ಜೀವನದಲ್ಲಿ ಈ ಕಾದಂಬರಿಯು ಒಂದು ಮಹತ್ವದ ಪ್ರಭಾವವನ್ನು ಬೀರಬಹುದು. ಪ್ರಾರ್ಥನಾ ಮತ್ತು ಹಿಮವಂತ್ ಅವರ ಪ್ರೇಮ ಕಥೆಯು ಈ ಕಾದಂಬರಿಯ ಜೀವಾಳವಾಗಿದೆ. ರವಿ ಮತ್ತು ಬೆಳಗೆರೆ ಅವರ ಪಾತ್ರಗಳು ಕಥೆಗೆ ಹೊಸ ಆಯಾಮವನ್ನು ನೀಡುತ್ತವೆ. ಕಾದಂಬರಿಯ ಕೊನೆಯ ಭಾಗದಲ್ಲಿ ಹಿಮವಂತ್ ಕೈಗೊಂಡ ನಿರ್ಧಾರಗಳು ಅವನ ಬದುಕಿನ ಹಾದಿಯನ್ನು ಬದಲಾಯಿಸುತ್ತವೆ. ಮೌನ ಮತ್ತು ಸಂಭಾಷಣೆಗಳ ಮೂಲಕ ಲೇಖಕರು ಮಾನವ ಸಂಬಂಧಗಳ ಸಂಕೀರ್ಣತೆಯನ್ನು ಸುಂದರವಾಗಿ ಚಿತ್ರಿಸಿದ್ದಾರೆ. ಪುಟ 338 ಮತ್ತು 341 ರಲ್ಲಿ ಬರುವ ಸಂಭಾಷಣೆಗಳು ಓದುಗರಲ್ಲಿ ಗಾಢವಾದ ಭಾವನೆಗಳನ್ನು ಮೂಡಿಸುತ್ತವೆ. ಪ್ರತಿಯೊಬ್ಬ ಪಾತ್ರಕ್ಕೂ ತನ್ನದೇ ಆದ ಹಿನ್ನೆಲೆ ಮತ್ತು ಕಥೆಯಿದೆ, ಇದು ಒಟ್ಟಾರೆ ಕಾದಂಬರಿಯನ್ನು ಒಂದು ಅದ್ಭುತ ಓದುವ ಅನುಭವವಾಗಿಸುತ್ತದೆ. ನಿಮ್ಮ ಜೀವನದಲ್ಲಿ ಈ ಕಾದಂಬರಿಯು ಒಂದು ಮಹತ್ವದ ಪ್ರಭಾವವನ್ನು ಬೀರಬಹುದು. ಪ್ರಾರ್ಥನಾ ಮತ್ತು ಹಿಮವಂತ್ ಅವರ ಪ್ರೇಮ ಕಥೆಯು ಈ ಕಾದಂಬರಿಯ ಜೀವಾಳವಾಗಿದೆ. ರವಿ ಮತ್ತು ಬೆಳಗೆರೆ ಅವರ ಪಾತ್ರಗಳು ಕಥೆಗೆ ಹೊಸ ಆಯಾಮವನ್ನು ನೀಡುತ್ತವೆ. ಕಾದಂಬರಿಯ ಕೊನೆಯ ಭಾಗದಲ್ಲಿ ಹಿಮವಂತ್ ಕೈಗೊಂಡ ನಿರ್ಧಾರಗಳು ಅವನ ಬದುಕಿನ ಹಾದಿಯನ್ನು ಬದಲಾಯಿಸುತ್ತವೆ."""

def split_text_into_sentences(text):
    # Split by Kannada and English sentence delimiters
    sentences = re.split(r'(?<=[.!?।])\s+', text)
    chunks = []
    current_chunk = ""
    for s in sentences:
        if len(current_chunk) + len(s) + 1 < 200:
            current_chunk += (" " if current_chunk else "") + s
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = s
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

def fetch_gtts_chunk(chunk_info):
    idx, chunk = chunk_info
    if not chunk.strip():
        return idx, b""
    # Google Translate TTS API URL
    url = "https://translate.google.com/translate_tts"
    params = {
        "ie": "UTF-8",
        "tl": "kn",
        "client": "tw-ob",
        "q": chunk.strip()
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                return idx, resp.content
            time.sleep(0.5)
        except Exception as e:
            time.sleep(0.5)
    return idx, b""

print("Starting Parallel gTTS Test...")
chunks = split_text_into_sentences(test_text)
print(f"Split into {len(chunks)} chunks.")

t0 = time.time()
with ThreadPoolExecutor(max_workers=min(len(chunks) or 1, 10)) as executor:
    results = list(executor.map(fetch_gtts_chunk, enumerate(chunks)))

results.sort(key=lambda x: x[0])
audio_bytes = b"".join(r[1] for r in results if r[1])
t1 = time.time()

print(f"Parallel gTTS completed in {t1-t0:.2f} seconds.")
print(f"Generated audio size: {len(audio_bytes)} bytes.")

with open("scratch/test_parallel_out.mp3", "wb") as f:
    f.write(audio_bytes)
print("Saved to scratch/test_parallel_out.mp3")
