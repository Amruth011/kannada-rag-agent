import os
import re
import base64
import requests
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

def call_sarvam_tts(text, language="kn-IN"):
    clean = re.sub(r'\[Page \d+\]:', '', text).strip()
    clean = re.sub(r'📄 Sources:.*', '', clean).strip()
    clean = re.sub(r'\[\(?:GEMINI FAILED|GROQ FAILED|BACKEND ERROR|ERROR\)[^\]]*\]', '', clean).strip()

    is_kannada = "kn" in language.lower()
    target_lang = "kn-IN" if is_kannada else "en-IN"
    
    if SARVAM_API_KEY and is_kannada:
        try:
            # Split text into chunks < 450 chars
            words = clean.split()
            chunks_list, current = [], ""
            for word in words:
                if len(current) + len(word) + 1 < 450:
                    current += (" " if current else "") + word
                else:
                    if current: chunks_list.append(current)
                    current = word
            if current: chunks_list.append(current)
            
            print(f"Total Chunks: {len(chunks_list)}")
            for idx, c in enumerate(chunks_list):
                print(f"Chunk {idx+1} length: {len(c)}")
                
            headers = {"Authorization": f"Bearer {SARVAM_API_KEY}", "Content-Type": "application/json"}
            headers_key = {"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"}
            
            def fetch_chunk_audio(chunk_info):
                idx, chunk = chunk_info
                if not chunk.strip():
                    return idx, None
                payload = {
                    "inputs": [chunk.strip()],
                    "target_language_code": target_lang,
                    "speaker": "meera",
                    "model": "bulbul:v3",
                    "pace": 1.0
                }
                for attempt in range(3):
                    try:
                        t0 = time.time()
                        resp = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers, json=payload, timeout=15)
                        if resp.status_code != 200:
                            resp = requests.post("https://api.sarvam.ai/text-to-speech", headers=headers_key, json=payload, timeout=15)
                        t1 = time.time()
                        print(f"Chunk {idx+1} status: {resp.status_code} in {t1-t0:.2f}s")
                        if resp.status_code == 200:
                            res_json = resp.json()
                            aud_b64 = res_json.get("audios", [""])[0] if "audios" in res_json else res_json.get("audio", "")
                            if aud_b64:
                                return idx, base64.b64decode(aud_b64)
                        elif resp.status_code == 429:
                            time.sleep(1)
                    except Exception as e:
                        print(f"Attempt {attempt} failed for chunk {idx+1}: {e}")
                        time.sleep(0.5)
                return idx, None

            with ThreadPoolExecutor(max_workers=min(len(chunks_list) or 1, 6)) as executor:
                results = list(executor.map(fetch_chunk_audio, enumerate(chunks_list)))
                
            # Sort results by index to maintain original order
            results.sort(key=lambda x: x[0])
            audio_bytes_list = [r[1] for r in results]
            
            failed_count = sum(1 for ab in audio_bytes_list if ab is None)
            print(f"Failed chunks count: {failed_count} out of {len(chunks_list)}")
            
            # Filter None
            audio_bytes_list = [ab for ab in audio_bytes_list if ab is not None]
            
            if audio_bytes_list:
                import wave, io
                output_wav = io.BytesIO()
                with wave.open(output_wav, 'wb') as wav_out:
                    for i, ab in enumerate(audio_bytes_list):
                        seg = io.BytesIO(ab)
                        try:
                            with wave.open(seg, 'rb') as wav_in:
                                if i == 0: wav_out.setparams(wav_in.getparams())
                                wav_out.writeframes(wav_in.readframes(wav_in.getnframes()))
                        except Exception as wav_err:
                            print(f"WAV parse error on chunk {i+1}: {wav_err}")
                            continue
                return base64.b64encode(output_wav.getvalue()).decode("utf-8")
        except Exception as e:
            print(f"Sarvam TTS failed: {e}")
    return ""

test_text = """ಪ್ರಾರ್ಥನಾ ಮತ್ತು ಹಿಮವಂತ್ ಅವರ ಪ್ರೇಮ ಕಥೆಯು ಈ ಕಾದಂಬರಿಯ ಜೀವಾಳವಾಗಿದೆ. ರವಿ ಮತ್ತು ಬೆಳಗೆರೆ ಅವರ ಪಾತ್ರಗಳು ಕಥೆಗೆ ಹೊಸ ಆಯಾಮವನ್ನು ನೀಡುತ್ತವೆ. ಕಾದಂಬರಿಯ ಕೊನೆಯ ಭಾಗದಲ್ಲಿ ಹಿಮವಂತ್ ಕೈಗೊಂಡ ನಿರ್ಧಾರಗಳು ಅವನ ಬದುಕಿನ ಹಾದಿಯನ್ನು ಬದಲಾಯಿಸುತ್ತವೆ. ಮೌನ ಮತ್ತು ಸಂಭಾಷಣೆಗಳ ಮೂಲಕ ಲೇಖಕರು ಮಾನವ ಸಂಬಂಧಗಳ ಸಂಕೀರ್ಣತೆಯನ್ನು ಸುಂದರವಾಗಿ ಚಿತ್ರಿಸಿದ್ದಾರೆ. ಪುಟ 338 ಮತ್ತು 341 ರಲ್ಲಿ ಬರುವ ಸಂಭಾಷಣೆಗಳು ಓದುಗರಲ್ಲಿ ಗಾಢವಾದ ಭಾವನೆಗಳನ್ನು ಮೂಡಿಸುತ್ತವೆ. ಪ್ರತಿಯೊಬ್ಬ ಪಾತ್ರಕ್ಕೂ ತನ್ನದೇ ಆದ ಹಿನ್ನೆಲೆ ಮತ್ತು ಕಥೆಯಿದೆ, ಇದು ಒಟ್ಟಾರೆ ಕಾದಂಬರಿಯನ್ನು ಒಂದು ಅದ್ಭುತ ಓದುವ ಅನುಭವವಾಗಿಸುತ್ತದೆ. ನಿಮ್ಮ ಜೀವನದಲ್ಲಿ ಈ ಕಾದಂಬರಿಯು ಒಂದು ಮಹತ್ವದ ಪ್ರಭಾವವನ್ನು ಬೀರಬಹುದು."""
print("Starting TTS Test...")
res = call_sarvam_tts(test_text)
if res:
    print(f"Success! Base64 audio length: {len(res)}")
else:
    print("Failed to generate audio.")
