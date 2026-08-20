# scratch/deloop_english_pages.py
import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGLISH_DIR = os.path.join(BASE_DIR, "data", "english_translated")

def clean_repetitions(text):
    """
    Cleans severe loops and repetitions from English translated text.
    Handles sentence-level loops and phrase-level loops.
    """
    if not text:
        return ""
        
    paragraphs = text.split("\n\n")
    cleaned_paragraphs = []
    
    for para in paragraphs:
        if not para.strip():
            continue
            
        # Split into sentences using a regex that handles abbreviations reasonably
        # Keep the sentence boundary punctuation with the sentence
        sentences = re.split(r'(?<=[.!?]) +', para.strip())
        cleaned_sentences = []
        
        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
                
            # 1. Skip consecutive sentence-level repetitions
            if cleaned_sentences and cleaned_sentences[-1].lower() == s_clean.lower():
                continue
                
            # 2. Skip non-consecutive repetitions in the same paragraph if the sentence is long
            # (Dialogue or short phrases can be naturally repeated, but long sentences shouldn't)
            if len(s_clean) > 25 and s_clean.lower() in [x.lower() for x in cleaned_sentences]:
                continue
                
            # 3. Clean up internal loops inside a single sentence (e.g. "I can walk. I can walk. I can walk.")
            # Sometimes a single sentence is parsed containing repeated segments
            # E.g. "I can walk. I can walk. I can walk." or phrase repetitions
            # Let's check for repeated words/phrases inside the sentence
            words = s_clean.split()
            if len(words) > 10:
                # Check for consecutive word phrase loops (e.g. "I can walk I can walk I can walk")
                # We look for phrases of length n (from 1 to 6 words) repeated consecutively
                for n in range(6, 0, -1):
                    i = 0
                    while i <= len(words) - 2*n:
                        phrase = words[i:i+n]
                        phrase_str = " ".join(phrase).lower().rstrip(",.?!;:")
                        
                        # Check consecutive matches
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
                            # We found consecutive repetitions! Remove them.
                            # Keep only the first one
                            del words[i+n : i + (rep_count+1)*n]
                            # Don't increment i, check again at same position in case of other loops
                        else:
                            i += 1
                s_clean = " ".join(words)
                
            cleaned_sentences.append(s_clean)
            
        # Join sentences back into paragraph
        para_clean = " ".join(cleaned_sentences)
        
        # 4. Clean up paragraph-level phrase loops (e.g. "completely absorbed... completely absorbed")
        # Split into words and look for repeated phrases of 3 to 6 words that appear within a window of 30 words
        words = para_clean.split()
        if len(words) > 15:
            for n in range(6, 2, -1):
                i = 0
                while i < len(words) - 2*n:
                    phrase = words[i:i+n]
                    phrase_str = " ".join(phrase).lower().rstrip(",.?!;:")
                    
                    found_rep = False
                    for j in range(i + n, min(i + n + 35, len(words) - n + 1)):
                        compare_str = " ".join(words[j:j+n]).lower().rstrip(",.?!;:")
                        if phrase_str == compare_str:
                            # Found a repeated phrase within the window!
                            # Delete the repeated phrase
                            del words[j : j+n]
                            found_rep = True
                            break
                    if not found_rep:
                        i += 1
            para_clean = " ".join(words)
            
        cleaned_paragraphs.append(para_clean)
        
    return "\n\n".join(cleaned_paragraphs)

def main():
    print("Running local English translation de-looping / cleaning pipeline...")
    
    # Process all files in data/english_translated
    files = sorted([f for f in os.listdir(ENGLISH_DIR) if f.startswith("page_") and f.endswith(".txt")])
    
    fixed_count = 0
    for fname in files:
        fpath = os.path.join(ENGLISH_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
            
        cleaned = clean_repetitions(content)
        
        # If content changed, save it
        if cleaned.strip() != content.strip():
            page_num = int(fname[5:9])
            print(f"   Fixed loops/repetitions on page {page_num:03d}")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(cleaned)
            fixed_count += 1
            
    print(f"\n[DONE]: De-looped {fixed_count} English pages.")

if __name__ == "__main__":
    main()
