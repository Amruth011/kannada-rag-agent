# scratch/deduplicate_paragraphs.py
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGLISH_DIR = os.path.join(BASE_DIR, "data", "english_translated")

def is_similar_paragraph(p1, p2):
    # Check if two paragraphs are highly similar (e.g. at least 85% word overlap)
    w1 = set(p1.lower().split())
    w2 = set(p2.lower().split())
    if not w1 or not w2:
        return False
    intersection = w1.intersection(w2)
    smaller_size = min(len(w1), len(w2))
    return len(intersection) / smaller_size > 0.85

def clean_repetitions_and_loops(text):
    if not text:
        return ""
        
    paragraphs = text.split("\n\n")
    unique_paragraphs = []
    
    for para in paragraphs:
        para_strip = para.strip()
        if not para_strip:
            continue
            
        # 1. Check if this paragraph is a duplicate or highly similar to an existing unique paragraph
        is_dup = False
        for up in unique_paragraphs:
            if is_similar_paragraph(up, para_strip):
                is_dup = True
                break
        if is_dup:
            continue
            
        # 2. De-loop at the sentence level
        sentences = re.split(r'(?<=[.!?]) +', para_strip)
        cleaned_sentences = []
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
                
            # Skip consecutive identical sentences
            if cleaned_sentences and cleaned_sentences[-1].lower() == s_clean.lower():
                continue
                
            # Skip non-consecutive repetitions in the same paragraph if long
            if len(s_clean) > 20 and s_clean.lower() in [x.lower() for x in cleaned_sentences]:
                continue
                
            # Clean up internal consecutive word loops (e.g. "I can walk I can walk")
            words = s_clean.split()
            if len(words) > 8:
                for n in range(6, 0, -1):
                    i = 0
                    while i <= len(words) - 2*n:
                        phrase = words[i:i+n]
                        phrase_str = " ".join(phrase).lower().rstrip(",.?!;:")
                        
                        rep_count = 0
                        next_idx = i + n
                        while next_idx <= len(words) - n:
                            next_phrase = words[next_idx:next_idx+n]
                            next_phrase_str = " ".join(next_phrase).lower().rstrip(",.?!;:")
                            if phrase_str == next_phrase_str:
                                rep_count += 1
                                next_idx += n
                            else:
                                break
                                
                        if rep_count > 0:
                            del words[i+n : i + (rep_count+1)*n]
                        else:
                            i += 1
                s_clean = " ".join(words)
                
            cleaned_sentences.append(s_clean)
            
        para_clean = " ".join(cleaned_sentences)
        
        # 3. Clean up paragraph-level phrase loops
        words = para_clean.split()
        if len(words) > 15:
            for n in range(6, 2, -1):
                i = 0
                while i < len(words) - 2*n:
                    phrase = words[i:i+n]
                    phrase_str = " ".join(phrase).lower().rstrip(",.?!;:")
                    
                    found_rep = False
                    for j in range(i + n, min(i + n + 30, len(words) - n + 1)):
                        compare_str = " ".join(words[j:j+n]).lower().rstrip(",.?!;:")
                        if phrase_str == compare_str:
                            del words[j : j+n]
                            found_rep = True
                            break
                    if not found_rep:
                        i += 1
            para_clean = " ".join(words)
            
        unique_paragraphs.append(para_clean)
        
    return "\n\n".join(unique_paragraphs)

def main():
    print("Running advanced paragraph-level and sentence-level de-looping...")
    
    files = sorted([f for f in os.listdir(ENGLISH_DIR) if f.startswith("page_") and f.endswith(".txt")])
    
    fixed_count = 0
    for fname in files:
        fpath = os.path.join(ENGLISH_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            
        cleaned = clean_repetitions_and_loops(content)
        
        if cleaned.strip() != content.strip():
            page_num = int(fname[5:9])
            print(f"   Deduplicated and de-looped page {page_num:03d}")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(cleaned)
            fixed_count += 1
            
    print(f"\n[DONE]: De-looped and deduplicated {fixed_count} English pages.")

if __name__ == "__main__":
    main()
