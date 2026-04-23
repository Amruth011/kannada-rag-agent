import os
from fastembed import TextEmbedding

# We switch to a smaller model (110MB) to stay under Vercel's 245MB bundle limit
MODEL_NAME = "intfloat/multilingual-e5-small"


def download():
    print(f"Downloading {MODEL_NAME}...")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(BASE_DIR, "model_cache")
    os.makedirs(model_path, exist_ok=True)
    os.environ["FASTEMBED_CACHE_PATH"] = model_path
    
    
    # This triggers the download
    model = TextEmbedding(model_name=MODEL_NAME)
    print(f"Success! Model cached in {model_path}")

if __name__ == "__main__":
    download()
