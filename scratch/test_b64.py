import requests
from PIL import Image
import io

r = requests.get('https://kannada-rag-agent.vercel.app/favicon.ico')
print("Status:", r.status_code)
print("Headers content-type:", r.headers.get('content-type'))
print("Bytes length:", len(r.content))

try:
    img = Image.open(io.BytesIO(r.content))
    print("PNG Format:", img.format)
    print("PNG Size:", img.size)
    print("Pillow loaded image successfully!")
except Exception as e:
    print("Pillow load failed:", e)
