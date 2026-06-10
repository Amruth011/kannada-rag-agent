import os
import shutil

def prepare():
    dist = "deploy_dist"
    if os.path.exists(dist):
        shutil.rmtree(dist)
    os.makedirs(dist)
    os.makedirs(os.path.join(dist, "public"))

    # Copy files
    shutil.copytree("api", os.path.join(dist, "api"))
    
    # Ensure data.json and vectors.npz are inside api
    if os.path.exists("data.json"):
        shutil.copy("data.json", os.path.join(dist, "api", "data.json"))
    if os.path.exists("vectors.npz"):
        shutil.copy("vectors.npz", os.path.join(dist, "api", "vectors.npz"))
    
    # Requirements and Config
    shutil.copy("requirements.txt", os.path.join(dist, "requirements.txt"))
    shutil.copy("vercel.json", os.path.join(dist, "vercel.json"))
    if os.path.exists(".vercel"):
        shutil.copytree(".vercel", os.path.join(dist, ".vercel"))
    
    # Dummy index.html
    with open(os.path.join(dist, "public", "index.html"), "w") as f:
        f.write("<h1>Kannada RAG Agent Live</h1>")

    print("Pure Python Preparation complete!")
    
if __name__ == "__main__":
    prepare()
