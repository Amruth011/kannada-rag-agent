import json
import os

def run_analysis():
    output = []
    
    output.append("# Page 100 Ingestion Analysis\n")
    
    # 2. OCR Output
    try:
        with open("data/normalized_text/page_0100.txt", "r", encoding="utf-8") as f:
            ocr_text = f.read()
        output.append("## 2. OCR / Normalized Text")
        output.append(f"- **Character Count:** {len(ocr_text)}")
        output.append("### Full OCR Text:\n```text\n" + ocr_text + "\n```\n")
    except Exception as e:
        ocr_text = ""
        output.append(f"## 2. OCR / Normalized Text\nError loading: {e}\n")
        
    # 3. Cleaned Text
    try:
        with open("data/cleaned_text/page_0100.txt", "r", encoding="utf-8") as f:
            cleaned_text = f.read()
        output.append("## 3. Cleaned Text")
        output.append(f"- **Character Count:** {len(cleaned_text)}")
        output.append("### Full Cleaned Text:\n```text\n" + cleaned_text + "\n```\n")
    except Exception as e:
        cleaned_text = ""
        output.append(f"## 3. Cleaned Text\nError loading: {e}\n")
        
    # 4. Chunks
    try:
        with open("data/chunks.json", "r", encoding="utf-8") as f:
            all_chunks = json.load(f)
        p100_chunks = [c for c in all_chunks if str(c.get("page")) == "100"]
        
        output.append("## 4. Chunking")
        output.append(f"- **Number of Chunks:** {len(p100_chunks)}")
        
        chunk_total_chars = sum(len(c["text"]) for c in p100_chunks)
        output.append(f"- **Total Characters in Chunks:** {chunk_total_chars}\n")
        
        for i, c in enumerate(p100_chunks):
            output.append(f"### Chunk {i+1} (Length: {len(c['text'])})")
            output.append(f"```text\n{c['text']}\n```\n")
            
    except Exception as e:
        output.append(f"## 4. Chunking\nError loading: {e}\n")

    # Conclusion
    output.append("## Conclusion (Data Loss Analysis)\n")
    if ocr_text and cleaned_text:
        diff = len(ocr_text) - len(cleaned_text)
        output.append(f"- **Cleaning Loss:** {diff} characters were removed during cleaning (likely whitespace, newlines, and unprintable characters).\n")
    if cleaned_text and p100_chunks:
        diff = len(cleaned_text) - chunk_total_chars
        # Taking overlap into account, chunks should actually be larger
        if chunk_total_chars > len(cleaned_text):
            output.append(f"- **Chunking Loss:** None. Chunks contain {chunk_total_chars - len(cleaned_text)} MORE characters than the cleaned text due to chunk overlap.\n")
        else:
            output.append(f"- **Chunking Loss:** {diff} characters were lost during chunking.\n")
            
    with open("C:/Users/shara/.gemini/antigravity-ide/brain/4541cbe1-32b9-4de0-8913-c4f4e9912647/page_100_analysis.md", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    run_analysis()
