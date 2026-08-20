import sys
import traceback

class TraceImport:
    def __init__(self):
        self.triggered = set()

    def find_spec(self, fullname, path, target=None):
        if fullname in ["torch", "transformers"] and fullname not in self.triggered:
            self.triggered.add(fullname)
            print(f"\n[TRACE] Package '{fullname}' is being imported!")
            print("Call stack:")
            # Print stack frames, excluding this finder code
            for frame in traceback.extract_stack()[:-1]:
                print(f"  File '{frame.filename}', line {frame.lineno}, in {frame.name}")
                print(f"    {frame.line}")
        return None

# Install our import hook at the very beginning
sys.meta_path.insert(0, TraceImport())

print("Attempting to import langchain_google_genai...")
import langchain_google_genai
print("Import of langchain_google_genai complete.\n")
