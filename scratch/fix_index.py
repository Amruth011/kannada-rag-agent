from PIL import Image
import io, base64

# 1. Generate correct 32x32 base64
img = Image.open('favicon.png')
img = img.resize((32, 32), Image.Resampling.LANCZOS)
buf = io.BytesIO()
img.save(buf, format='PNG')
correct_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')

# 2. Read api/index.py
filepath = 'api/index.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 3. Find the favicon function and replace the b64 string
import re
pattern = r'(icon_b64\s*=\s*")[^"]+(")'
new_content, count = re.subn(pattern, r'\g<1>' + correct_b64 + r'\g<2>', content)

if count > 0:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Successfully updated api/index.py! Replaced {count} occurrences.")
else:
    print("Error: Could not find the icon_b64 string pattern in api/index.py")
