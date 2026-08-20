import os
import sys
import subprocess
import psutil

PACKAGES = [
    "langchain",
    "langchain_core",
    "langchain_community",
    "langchain_google_genai",
    "langchain_groq",
    "google.generativeai",
    "groq",
    "transformers",
    "torch"
]

def get_isolated_ram(package_name):
    # Runs python in a subprocess to measure isolated import footprint
    cmd = [
        r"C:\Users\shara\AppData\Local\Programs\Python\Python313\python.exe",
        "-c",
        f"import os, psutil; p = psutil.Process(os.getpid()); r0 = p.memory_info().rss; import {package_name}; r1 = p.memory_info().rss; print(f'{{(r1 - r0)/(1024*1024):.2f}}')"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except subprocess.CalledProcessError as e:
        # If the package is not installed (e.g. langchain_google_genai might not be)
        return f"Not Installed / Error: {e.stderr.strip()}"

def run_sequential_profile():
    # Measures sequential imports in the current process
    process = psutil.Process(os.getpid())
    def get_ram():
        return process.memory_info().rss / (1024 * 1024)
        
    print("=== Sequential Import Footprint (Single Process) ===")
    r_base = get_ram()
    print(f"Baseline RAM: {r_base:.2f} MB")
    
    current = r_base
    seq_stats = []
    
    for pkg in PACKAGES:
        before = get_ram()
        try:
            # Dynamically import package
            __import__(pkg)
            after = get_ram()
            delta = after - before
            seq_stats.append((pkg, before, after, delta))
            print(f"Imported [{pkg}]: RAM Before: {before:.2f} MB | After: {after:.2f} MB | Delta: {delta:.2f} MB")
        except ImportError:
            print(f"Imported [{pkg}]: FAILED (Not Installed)")
            seq_stats.append((pkg, before, before, "N/A"))
            
    print(f"Total Process RAM at end: {get_ram():.2f} MB\n")
    return seq_stats

if __name__ == "__main__":
    print("=== Isolated Import Footprint (Subprocess-based) ===")
    isolated_stats = {}
    for pkg in PACKAGES:
        ram = get_isolated_ram(pkg)
        isolated_stats[pkg] = ram
        if isinstance(ram, float):
            print(f"Isolated [{pkg}] RAM consumption: {ram:.2f} MB")
        else:
            print(f"Isolated [{pkg}] RAM consumption: {ram}")
            
    print()
    seq_stats = run_sequential_profile()
    
    # Check if torch loads any models on import
    # PyTorch by default does not load weights, but let's check if it instantiates thread pools or memory arenas
    import torch
    print("PyTorch details:")
    print("- Device Count:", torch.cuda.device_count() if torch.cuda.is_available() else "No GPU (CPU only)")
    print("- Default Num Threads:", torch.get_num_threads())
    
    # Check if transformers does any model loading on import
    import transformers
    print("Transformers version:", transformers.__version__)
