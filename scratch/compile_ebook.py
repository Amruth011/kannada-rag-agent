# scratch/compile_ebook.py
# Compiles page files and cover images into beautiful Markdown, HTML, and EPUB e-books.
# Run: python scratch/compile_ebook.py

import os
import re
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define directories
KANNADA_DIR = os.path.join(BASE_DIR, "data", "normalized_text")
ENGLISH_DIR = os.path.join(BASE_DIR, "data", "english_translated")
OUTPUT_DIR  = os.path.join(BASE_DIR, "data", "ebooks")

# Check for cover image
COVER_IMAGE_PATHS = [
    os.path.join(BASE_DIR, "data", "cover.png"),
    os.path.join(BASE_DIR, "data", "cover.jpg"),
    os.path.join(BASE_DIR, "favicon.png"), # Fallback to favicon if no cover
]

def find_cover_image():
    for p in COVER_IMAGE_PATHS:
        if os.path.exists(p):
            return p
    return None

def load_pages(directory):
    """Loads all page text files in sorted order."""
    if not os.path.exists(directory):
        return {}
        
    pages = {}
    for fname in os.listdir(directory):
        match = re.search(r"page_(\d+)\.txt", fname)
        if match:
            page_num = int(match.group(1))
            with open(os.path.join(directory, fname), "r", encoding="utf-8") as f:
                pages[page_num] = f.read().strip()
    return pages

# --- MARKDOWN COMPILATION ---
def compile_markdown(kannada_pages, english_pages, cover_path, output_dir):
    """Compiles pages into .md files."""
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Kannada Only
    kn_path = os.path.join(output_dir, "heli_hogu_karana_kannada.md")
    with open(kn_path, "w", encoding="utf-8") as f:
        f.write("# ಹೇಳಿ ಹೋಗು ಕಾರಣ (Heli Hogu Karana)\n\n")
        f.write("**ಲೇಖಕರು**: ರವಿ ಬೆಳಗೆರೆ\n\n")
        if cover_path:
            f.write(f"![Cover]({os.path.basename(cover_path)})\n\n")
        f.write("---\n\n")
        for page_num in sorted(kannada_pages.keys()):
            f.write(f"## ಪುಟ {page_num}\n\n")
            f.write(kannada_pages[page_num] + "\n\n")
            f.write("---\n\n")
            
    # 2. English Only (if translations exist)
    en_path = None
    if english_pages:
        en_path = os.path.join(output_dir, "heli_hogu_karana_english.md")
        with open(en_path, "w", encoding="utf-8") as f:
            f.write("# Heli Hogu Karana (Tell the Reason Before You Go)\n\n")
            f.write("**Author**: Ravi Belagere\n\n")
            if cover_path:
                f.write(f"![Cover]({os.path.basename(cover_path)})\n\n")
            f.write("---\n\n")
            for page_num in sorted(english_pages.keys()):
                f.write(f"## Page {page_num}\n\n")
                f.write(english_pages[page_num] + "\n\n")
                f.write("---\n\n")
                
    # 3. Bilingual (if translations exist)
    bi_path = None
    if english_pages:
        bi_path = os.path.join(output_dir, "heli_hogu_karana_bilingual.md")
        with open(bi_path, "w", encoding="utf-8") as f:
            f.write("# ಹೇಳಿ ಹೋಗು ಕಾರಣ | Heli Hogu Karana\n\n")
            f.write("**ಲೇಖಕರು / Author**: ರವಿ ಬೆಳಗೆರೆ / Ravi Belagere\n\n")
            if cover_path:
                f.write(f"![Cover]({os.path.basename(cover_path)})\n\n")
            f.write("---\n\n")
            
            # Combine page-by-page
            all_pages = sorted(list(set(kannada_pages.keys()) | set(english_pages.keys())))
            for page_num in all_pages:
                f.write(f"## Page {page_num} | ಪುಟ {page_num}\n\n")
                
                # Kannada text
                f.write("### ಕನ್ನಡ (Kannada)\n\n")
                f.write(kannada_pages.get(page_num, "*ಪುಟ ಖಾಲಿ ಇದೆ*") + "\n\n")
                
                # English text
                f.write("### English\n\n")
                f.write(english_pages.get(page_num, "*Translation in progress*") + "\n\n")
                f.write("---\n\n")
                
    return kn_path, en_path, bi_path

# --- HTML COMPILATION ---
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Plus+Jakarta+Sans:ital,wght@0,300;0,400;0,600;1,400&family=Noto+Serif+Kannada:wght@400;700&display=swap');
        
        :root {{
            --bg-color: #0f172a;
            --text-color: #e2e8f0;
            --primary: #8b5cf6;
            --secondary: #06b6d4;
            --card-bg: rgba(30, 41, 59, 0.5);
            --border-color: rgba(255, 255, 255, 0.08);
        }}
        
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Plus Jakarta Sans', sans-serif;
            line-height: 1.8;
            margin: 0;
            padding: 0;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 2rem 1rem;
        }}
        
        header {{
            text-align: center;
            padding: 4rem 1rem;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 3rem;
        }}
        
        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 3rem;
            margin: 0 0 1rem 0;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .subtitle {{
            color: #94a3b8;
            font-size: 1.2rem;
            margin: 0;
        }}
        
        .cover-container {{
            text-align: center;
            margin: 2rem 0;
        }}
        
        .cover-img {{
            max-width: 320px;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            border: 1px solid var(--border-color);
        }}
        
        .page-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2.5rem;
            margin-bottom: 3rem;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }}
        
        .page-header {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 0;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 0.5rem;
        }}
        
        .kannada-text {{
            font-family: 'Noto Serif Kannada', serif;
            font-size: 1.15rem;
            letter-spacing: 0.02em;
        }}
        
        .english-text {{
            font-size: 1.05rem;
        }}
        
        /* Bilingual Layout CSS Grid */
        .bilingual-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }}
        
        @media (min-width: 768px) {{
            .bilingual-grid {{
                grid-template-columns: 1fr 1fr;
            }}
            .kannada-column {{
                border-right: 1px solid rgba(255, 255, 255, 0.05);
                padding-right: 2rem;
            }}
        }}
        
        .column-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 0.9rem;
            color: var(--secondary);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-top: 0;
            margin-bottom: 1rem;
        }}
        
        .column-title.kn {{
            color: var(--primary);
        }}
        
        .toc {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2rem;
            margin-bottom: 4rem;
        }}
        
        .toc-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.3rem;
            margin-top: 0;
            margin-bottom: 1rem;
            color: var(--secondary);
        }}
        
        .toc-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
            gap: 0.5rem;
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .toc-link {{
            display: block;
            text-align: center;
            padding: 0.4rem;
            background: rgba(255, 255, 255, 0.04);
            border-radius: 8px;
            color: var(--text-color);
            text-decoration: none;
            font-size: 0.9rem;
            transition: all 0.2s ease;
        }}
        
        .toc-link:hover {{
            background: var(--primary);
            transform: translateY(-2px);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <p class="subtitle">{author}</p>
            {cover_html}
        </header>
        
        <div class="toc">
            <h3 class="toc-title">Table of Contents</h3>
            <ul class="toc-list">
                {toc_html}
            </ul>
        </div>
        
        <main>
            {content_html}
        </main>
    </div>
</body>
</html>
"""

def compile_html(kannada_pages, english_pages, cover_base64, output_dir):
    """Compiles pages into premium responsive HTML files."""
    os.makedirs(output_dir, exist_ok=True)
    
    # Prep cover tag
    cover_html = ""
    if cover_base64:
        cover_html = f'<div class="cover-container"><img class="cover-img" src="data:image/png;base64,{cover_base64}" alt="Book Cover"></div>'
        
    # 1. Kannada Only
    toc_items = []
    content_cards = []
    for page_num in sorted(kannada_pages.keys()):
        toc_items.append(f'<li><a class="toc-link" href="#page-{page_num}">{page_num}</a></li>')
        content_cards.append(f"""
        <div class="page-card" id="page-{page_num}">
            <div class="page-header">ಪುಟ {page_num}</div>
            <div class="kannada-text">
                {kannada_pages[page_num].replace(chr(10), '<br>')}
            </div>
        </div>
        """)
        
    kn_html_path = os.path.join(output_dir, "heli_hogu_karana_kannada.html")
    with open(kn_html_path, "w", encoding="utf-8") as f:
        f.write(HTML_TEMPLATE.format(
            lang="kn",
            title="ಹೇಳಿ ಹೋಗು ಕಾರಣ",
            author="ರವಿ ಬೆಳಗೆರೆ",
            cover_html=cover_html,
            toc_html="".join(toc_items),
            content_html="".join(content_cards)
        ))
        
    # 2. English Only
    en_html_path = None
    if english_pages:
        toc_items = []
        content_cards = []
        for page_num in sorted(english_pages.keys()):
            toc_items.append(f'<li><a class="toc-link" href="#page-{page_num}">{page_num}</a></li>')
            content_cards.append(f"""
            <div class="page-card" id="page-{page_num}">
                <div class="page-header">Page {page_num}</div>
                <div class="english-text">
                    {english_pages[page_num].replace(chr(10), '<br>')}
                </div>
            </div>
            """)
            
        en_html_path = os.path.join(output_dir, "heli_hogu_karana_english.html")
        with open(en_html_path, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE.format(
                lang="en",
                title="Heli Hogu Karana",
                author="Ravi Belagere",
                cover_html=cover_html,
                toc_html="".join(toc_items),
                content_html="".join(content_cards)
            ))
            
    # 3. Bilingual
    bi_html_path = None
    if english_pages:
        toc_items = []
        content_cards = []
        all_pages = sorted(list(set(kannada_pages.keys()) | set(english_pages.keys())))
        for page_num in all_pages:
            toc_items.append(f'<li><a class="toc-link" href="#page-{page_num}">{page_num}</a></li>')
            kn_text = kannada_pages.get(page_num, "*ಪುಟ ಖಾಲಿ ಇದೆ*").replace(chr(10), '<br>')
            en_text = english_pages.get(page_num, "*Translation in progress*").replace(chr(10), '<br>')
            
            content_cards.append(f"""
            <div class="page-card" id="page-{page_num}">
                <div class="page-header">Page {page_num} | ಪುಟ {page_num}</div>
                <div class="bilingual-grid">
                    <div class="kannada-column">
                        <p class="column-title kn">ಕನ್ನಡ</p>
                        <div class="kannada-text">{kn_text}</div>
                    </div>
                    <div class="english-column">
                        <p class="column-title">English</p>
                        <div class="english-text">{en_text}</div>
                    </div>
                </div>
            </div>
            """)
            
        bi_html_path = os.path.join(output_dir, "heli_hogu_karana_bilingual.html")
        with open(bi_html_path, "w", encoding="utf-8") as f:
            f.write(HTML_TEMPLATE.format(
                lang="en",
                title="ಹೇಳಿ ಹೋಗು ಕಾರಣ | Heli Hogu Karana",
                author="ರವಿ ಬೆಳಗೆರೆ / Ravi Belagere",
                cover_html=cover_html,
                toc_html="".join(toc_items),
                content_html="".join(content_cards)
            ))
            
    return kn_html_path, en_html_path, bi_html_path

# --- EPUB COMPILATION ---
def compile_epub(kannada_pages, english_pages, cover_path, output_dir):
    """Compiles pages into standard EPUB format using ebooklib."""
    try:
        from ebooklib import epub
    except ImportError:
        print("\n[WARNING]: EbookLib is not installed. Skipping EPUB creation.")
        print("Hint: run 'pip install ebooklib' to enable EPUB file compilation.")
        return None, None, None
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Define generic style
    epub_style = """
    body { font-family: sans-serif; padding: 5%; line-height: 1.6; }
    h1 { text-align: center; color: #8b5cf6; }
    .page-header { font-size: 0.8em; color: #666; border-bottom: 1px solid #ddd; padding-bottom: 3px; margin-bottom: 20px; }
    .kannada { font-family: serif; font-size: 1.1em; }
    .english { font-size: 1.0em; }
    .bi-container { margin-bottom: 30px; }
    .bi-lang-title { font-weight: bold; font-size: 0.9em; color: #06b6d4; margin-top: 15px; }
    """
    
    def create_base_epub(title, lang, author):
        book = epub.EpubBook()
        book.set_identifier(f"kannada-rag-agent-{lang}")
        book.set_title(title)
        book.set_language(lang)
        book.add_author(author)
        
        # Add stylesheet
        style_item = epub.EpubItem(uid="style_default", file_name="style/default.css", media_type="text/css", content=epub_style)
        book.add_item(style_item)
        
        # Add cover
        if cover_path and os.path.exists(cover_path):
            try:
                # Add cover image file
                filename = os.path.basename(cover_path)
                with open(cover_path, "rb") as f:
                    book.set_cover(filename, f.read())
            except Exception as e:
                print(f"[WARNING]: Failed to set EPUB cover: {e}")
                
        return book, style_item

    # 1. Kannada Only
    kn_epub = os.path.join(output_dir, "heli_hogu_karana_kannada.epub")
    book, style_item = create_base_epub("ಹೇಳಿ ಹೋಗು ಕಾರಣ", "kn", "ರವಿ ಬೆಳಗೆರೆ")
    
    spine = ['nav']
    toc = []
    
    for page_num in sorted(kannada_pages.keys()):
        content = f"""
        <html>
        <head><link rel="stylesheet" href="style/default.css" type="text/css"/></head>
        <body>
            <div class="page-header">ಪುಟ {page_num}</div>
            <div class="kannada">
                {kannada_pages[page_num].replace(chr(10), '<br/>')}
            </div>
        </body>
        </html>
        """
        epub_page = epub.EpubHtml(
            title=f"Page {page_num}",
            file_name=f"page_{page_num:04d}.xhtml",
            lang="kn",
            content=content
        )
        book.add_item(epub_page)
        spine.append(epub_page)
        toc.append(epub_page)
        
    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine
    epub.write_epub(kn_epub, book, {})
    
    # 2. English Only
    en_epub = None
    if english_pages:
        en_epub = os.path.join(output_dir, "heli_hogu_karana_english.epub")
        book, style_item = create_base_epub("Heli Hogu Karana", "en", "Ravi Belagere")
        
        spine = ['nav']
        toc = []
        for page_num in sorted(english_pages.keys()):
            content = f"""
            <html>
            <head><link rel="stylesheet" href="style/default.css" type="text/css"/></head>
            <body>
                <div class="page-header">Page {page_num}</div>
                <div class="english">
                    {english_pages[page_num].replace(chr(10), '<br/>')}
                </div>
            </body>
            </html>
            """
            epub_page = epub.EpubHtml(
                title=f"Page {page_num}",
                file_name=f"page_{page_num:04d}.xhtml",
                lang="en",
                content=content
            )
            book.add_item(epub_page)
            spine.append(epub_page)
            toc.append(epub_page)
            
        book.toc = tuple(toc)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = spine
        epub.write_epub(en_epub, book, {})
        
    # 3. Bilingual
    bi_epub = None
    if english_pages:
        bi_epub = os.path.join(output_dir, "heli_hogu_karana_bilingual.epub")
        book, style_item = create_base_epub("ಹೇಳಿ ಹೋಗು ಕಾರಣ (Bilingual)", "mul", "ರವಿ ಬೆಳಗೆರೆ / Ravi Belagere")
        
        spine = ['nav']
        toc = []
        all_pages = sorted(list(set(kannada_pages.keys()) | set(english_pages.keys())))
        for page_num in all_pages:
            kn_text = kannada_pages.get(page_num, "*ಪುಟ ಖಾಲಿ ಇದೆ*").replace(chr(10), '<br/>')
            en_text = english_pages.get(page_num, "*Translation in progress*").replace(chr(10), '<br/>')
            
            content = f"""
            <html>
            <head><link rel="stylesheet" href="style/default.css" type="text/css"/></head>
            <body>
                <div class="page-header">Page {page_num} | ಪುಟ {page_num}</div>
                <div class="bi-container">
                    <div class="bi-lang-title">ಕನ್ನಡ</div>
                    <div class="kannada">{kn_text}</div>
                </div>
                <div class="bi-container">
                    <div class="bi-lang-title">English</div>
                    <div class="english">{en_text}</div>
                </div>
            </body>
            </html>
            """
            epub_page = epub.EpubHtml(
                title=f"Page {page_num}",
                file_name=f"page_{page_num:04d}.xhtml",
                lang="en",
                content=content
            )
            book.add_item(epub_page)
            spine.append(epub_page)
            toc.append(epub_page)
            
        book.toc = tuple(toc)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        book.spine = spine
        epub.write_epub(bi_epub, book, {})
        
    return kn_epub, en_epub, bi_epub

def main():
    # Force standard output to UTF-8 on Windows
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("[RUN]: Running E-Book Compiler...")
    
    # Load Kannada and English pages
    print(f"[LOAD]: Loading Kannada pages from: {KANNADA_DIR}")
    kn_pages = load_pages(KANNADA_DIR)
    print(f"   Loaded {len(kn_pages)} Kannada pages.")
    
    print(f"[LOAD]: Loading English pages from: {ENGLISH_DIR}")
    en_pages = load_pages(ENGLISH_DIR)
    print(f"   Loaded {len(en_pages)} translated English pages.")
    
    if not kn_pages:
        print("[ERROR]: No Kannada page data found. Cannot compile.")
        sys.exit(1)
        
    cover_path = find_cover_image()
    if cover_path:
        print(f"[COVER]: Cover image found: {cover_path}")
    else:
        print("[COVER]: Cover image not found. Proceeding without a cover page.")
        
    # Get base64 cover if image exists
    cover_b64 = None
    if cover_path:
        import base64
        with open(cover_path, "rb") as f:
            cover_b64 = base64.b64encode(f.read()).decode("utf-8")
            
    # Compile MD
    print("[COMPILE]: Generating Markdown files...")
    kn_md, en_md, bi_md = compile_markdown(kn_pages, en_pages, cover_path, OUTPUT_DIR)
    print(f"   Created: {kn_md}")
    if en_md: print(f"   Created: {en_md}")
    if bi_md: print(f"   Created: {bi_md}")
    
    # Compile HTML
    print("[COMPILE]: Generating Premium HTML files...")
    kn_html, en_html, bi_html = compile_html(kn_pages, en_pages, cover_b64, OUTPUT_DIR)
    print(f"   Created: {kn_html}")
    if en_html: print(f"   Created: {en_html}")
    if bi_html: print(f"   Created: {bi_html}")
    
    # Compile EPUB
    print("[COMPILE]: Generating EPUB files...")
    kn_epub, en_epub, bi_epub = compile_epub(kn_pages, en_pages, cover_path, OUTPUT_DIR)
    if kn_epub: print(f"   Created: {kn_epub}")
    if en_epub: print(f"   Created: {en_epub}")
    if bi_epub: print(f"   Created: {bi_epub}")
    
    print("\n[DONE]: E-Book compilation finished!")
    print(f"   Output directory: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
