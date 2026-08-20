# scratch/analyze_pages.py
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KANNADA_DIR = os.path.join(BASE_DIR, "data", "normalized_text")
ENGLISH_DIR = os.path.join(BASE_DIR, "data", "english_translated")

def count_garbage_kannada(text):
    # Count characters that are English letters (a-z, A-Z) or typical noise symbols (^, @, $, #, %, *, _, {, }, [, ], |, \, /, <, >)
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    noise_symbols = len(re.findall(r'[\^@\$#%\*_\{\}\[\]\|\\/<>]', text))
    total_len = len(text) if len(text) > 0 else 1
    return (latin_chars + noise_symbols) / total_len, latin_chars, noise_symbols

def detect_repetitions(text):
    # Detect if there are consecutive sentences or phrases repeated
    # Let's clean up formatting first
    cleaned = re.sub(r'\s+', ' ', text).strip()
    
    # Check for sentence repetitions
    sentences = re.split(r'(?<=[.!?]) +', cleaned)
    seen_sentences = {}
    repeated_sentences = []
    for s in sentences:
        s_norm = s.lower().strip()
        if len(s_norm) < 5:
            continue
        seen_sentences[s_norm] = seen_sentences.get(s_norm, 0) + 1
        
    for s, count in seen_sentences.items():
        if count >= 3:
            repeated_sentences.append((s, count))
            
    # Check for word repetitions (e.g. "I can walk" looping)
    words = cleaned.split()
    repeated_phrases = []
    # Check 3-word phrase repetition
    phrases = []
    for i in range(len(words) - 2):
        phrase = " ".join(words[i:i+3]).lower()
        phrases.append(phrase)
    
    seen_phrases = {}
    for p in phrases:
        seen_phrases[p] = seen_phrases.get(p, 0) + 1
        
    for p, count in seen_phrases.items():
        if count >= 5:  # If repeated 5+ times
            repeated_phrases.append((p, count))
            
    return repeated_sentences, repeated_phrases

def main():
    print("Analyzing all pages for OCR errors and translation repetitions...")
    
    kn_files = sorted([f for f in os.listdir(KANNADA_DIR) if f.endswith(".txt") and f.startswith("page_")])
    
    issues = []
    
    for f in kn_files:
        page_num = int(re.search(r"page_(\d+)\.txt", f).group(1))
        
        # Read Kannada
        kn_path = os.path.join(KANNADA_DIR, f)
        with open(kn_path, "r", encoding="utf-8") as file:
            kn_text = file.read()
            
        ratio, lat, noise = count_garbage_kannada(kn_text)
        
        # Read English
        en_fname = f"page_{page_num:04d}.txt"
        en_path = os.path.join(ENGLISH_DIR, en_fname)
        en_text = ""
        if os.path.exists(en_path):
            with open(en_path, "r", encoding="utf-8") as file:
                en_text = file.read()
                
        rep_sentences, rep_phrases = detect_repetitions(en_text) if en_text else ([], [])
        
        # Check for length mismatch (e.g. English is much longer than Kannada, or vice versa)
        kn_words = len(kn_text.split())
        en_words = len(en_text.split()) if en_text else 0
        ratio_len = 0
        if kn_words > 0 and en_words > 0:
            ratio_len = en_words / kn_words
            
        has_issue = False
        issue_desc = []
        if ratio > 0.05:  # More than 5% garbage characters
            has_issue = True
            issue_desc.append(f"Kannada OCR noise: {ratio:.1%} ({lat} letters, {noise} symbols)")
        if rep_sentences:
            has_issue = True
            issue_desc.append(f"Repeated sentences: {len(rep_sentences)} (e.g. '{rep_sentences[0][0]}' x{rep_sentences[0][1]})")
        if rep_phrases:
            # Filter repeated phrases to only show unique/important ones
            has_issue = True
            issue_desc.append(f"Repeated phrases: {len(rep_phrases)} (e.g. '{rep_phrases[0][0]}' x{rep_phrases[0][1]})")
        if ratio_len > 2.2 and en_words > 200: # English is more than 2.2x the Kannada word count
            has_issue = True
            issue_desc.append(f"Length Mismatch: English is {ratio_len:.1f}x Kannada ({en_words} words vs {kn_words} words)")
            
        if has_issue:
            issues.append((page_num, issue_desc, kn_words, en_words))
            
def main():
    print("Analyzing all pages for OCR errors and translation repetitions...")
    
    kn_files = sorted([f for f in os.listdir(KANNADA_DIR) if f.endswith(".txt") and f.startswith("page_")])
    
    issues = []
    
    for f in kn_files:
        page_num = int(re.search(r"page_(\d+)\.txt", f).group(1))
        
        # Read Kannada
        kn_path = os.path.join(KANNADA_DIR, f)
        with open(kn_path, "r", encoding="utf-8") as file:
            kn_text = file.read()
            
        ratio, lat, noise = count_garbage_kannada(kn_text)
        
        # Read English
        en_fname = f"page_{page_num:04d}.txt"
        en_path = os.path.join(ENGLISH_DIR, en_fname)
        en_text = ""
        if os.path.exists(en_path):
            with open(en_path, "r", encoding="utf-8") as file:
                en_text = file.read()
                
        rep_sentences, rep_phrases = detect_repetitions(en_text) if en_text else ([], [])
        
        # Check for length mismatch (e.g. English is much longer than Kannada, or vice versa)
        kn_words = len(kn_text.split())
        en_words = len(en_text.split()) if en_text else 0
        ratio_len = 0
        if kn_words > 0 and en_words > 0:
            ratio_len = en_words / kn_words
            
        has_issue = False
        issue_desc = []
        if ratio > 0.05:  # More than 5% garbage characters
            has_issue = True
            issue_desc.append(f"Kannada OCR noise: {ratio:.1%} ({lat} letters, {noise} symbols)")
        if rep_sentences:
            has_issue = True
            issue_desc.append(f"Repeated sentences: {len(rep_sentences)} (e.g. '{rep_sentences[0][0]}' x{rep_sentences[0][1]})")
        if rep_phrases:
            has_issue = True
            issue_desc.append(f"Repeated phrases: {len(rep_phrases)} (e.g. '{rep_phrases[0][0]}' x{rep_phrases[0][1]})")
        if ratio_len > 2.2 and en_words > 200: # English is more than 2.2x the Kannada word count
            has_issue = True
            issue_desc.append(f"Length Mismatch: English is {ratio_len:.1f}x Kannada ({en_words} words vs {kn_words} words)")
            
        if has_issue:
            issues.append((page_num, issue_desc, kn_words, en_words))
            
    report_path = os.path.join(BASE_DIR, "scratch", "analysis_report.txt")
    with open(report_path, "w", encoding="utf-8") as rf:
        rf.write(f"Total pages analyzed: {len(kn_files)}\n")
        rf.write(f"Pages with potential issues: {len(issues)}\n")
        rf.write("-" * 80 + "\n")
        for p_num, desc_list, kn_w, en_w in sorted(issues):
            rf.write(f"Page {p_num:03d} (Kannada words: {kn_w}, English words: {en_w}):\n")
            for d in desc_list:
                rf.write(f"  - {d}\n")
            rf.write("-" * 80 + "\n")
    print(f"Report written to {report_path}")

if __name__ == "__main__":
    main()
