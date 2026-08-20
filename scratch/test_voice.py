import os
import sys
import time
import base64
from dotenv import load_dotenv

# Load env
load_dotenv()

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.index import call_sarvam_tts

text = (
    "Age: He asserts that both he and Prarthana are over eighteen years old Page 7 . "
    "Residence: He states that he lives on rent in the backyard of a Mandi merchant named Shanthayya Page 7 . "
    "Motive for Walking: He reveals a profound reason for their arduous walk, explaining that they want to "
    "\"walk together our whole lives, at least till Shivamogga: let's see if we can grit our teeth and walk\" Page 7 . "
    "This suggests a deep, life-long commitment or a significant test of their relationship."
)

print("Starting TTS generation...")
start_time = time.time()
try:
    audio_b64 = call_sarvam_tts(text, language="en-IN")
    elapsed = time.time() - start_time
    print(f"Success! Time taken: {elapsed:.2f} seconds")
    print(f"Base64 length: {len(audio_b64)}")
    print(f"First 100 chars: {audio_b64[:100]}")
    print(f"Last 100 chars: {audio_b64[-100:]}")
except Exception as e:
    print(f"Failed with exception: {e}")
