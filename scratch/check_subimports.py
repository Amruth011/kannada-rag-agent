import sys
import subprocess

def check_package_imports(package_name):
    cmd = [
        r"C:\Users\shara\AppData\Local\Programs\Python\Python313\python.exe",
        "-c",
        f"import {package_name}; import sys; print('torch' in sys.modules, 'transformers' in sys.modules, 'pydantic' in sys.modules)"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[{package_name}] Imports under-the-hood:")
        out = res.stdout.strip().split()
        print(f"  - torch in sys.modules: {out[0]}")
        print(f"  - transformers in sys.modules: {out[1]}")
        print(f"  - pydantic in sys.modules: {out[2]}")
    except Exception as e:
        print(f"Error checking {package_name}: {e}")

if __name__ == "__main__":
    check_package_imports("langchain_google_genai")
    check_package_imports("langchain_groq")
    check_package_imports("google.generativeai")
    check_package_imports("groq")
