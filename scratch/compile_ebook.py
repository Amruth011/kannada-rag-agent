# scratch/compile_ebook.py
# Compiles page files and cover images into beautiful HTML e-books with Dark Indic UI.
# Run: python scratch/compile_ebook.py

import os
import re
import sys
import base64
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define directories
KANNADA_DIR = os.path.join(BASE_DIR, "data", "normalized_text")
ENGLISH_DIR = os.path.join(BASE_DIR, "data", "english_translated")
OUTPUT_DIR  = os.path.join(BASE_DIR, "data", "ebooks")
API_DATA_DIR = os.path.join(BASE_DIR, "api", "data", "ebooks")

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
            --bg-color: #fffcf8;
            --text-color: #0f172a;
            --primary: #c2410c;
            --secondary: #4338ca;
            --accent-pink: #cc2366;
            --card-bg: #ffffff;
            --border-color: rgba(194, 65, 12, 0.08);
            --sidebar-width: 300px;
        }}
        
        body {{
            background: radial-gradient(circle at 50% 0%, #fffefc 0%, #fdf5ee 80%);
            color: var(--text-color);
            font-family: 'Plus Jakarta Sans', sans-serif;
            line-height: 1.8;
            margin: 0;
            padding: 0;
            min-height: 100vh;
        }}
        
        .top-navbar {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 70px;
            background: rgba(253, 245, 238, 0.85);
            backdrop-filter: blur(24px) saturate(180%);
            border-bottom: 1px solid rgba(194, 65, 12, 0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2rem;
            z-index: 1000;
        }}
        
        .navbar-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.3rem;
            font-weight: 800;
            background: linear-gradient(to right, #c2410c, #4338ca);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        
        .navbar-nav {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .nav-btn {{
            background: rgba(194, 65, 12, 0.04);
            border: 1px solid rgba(194, 65, 12, 0.15);
            border-radius: 999px;
            color: #64748b;
            padding: 0.4rem 1rem;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
        }}
        
        .nav-btn:hover {{
            background: rgba(194, 65, 12, 0.1);
            border-color: #c2410c;
            color: #c2410c;
            box-shadow: 0 0 12px rgba(194, 65, 12, 0.1);
            transform: translateY(-1px);
        }}
        
        .page-input-wrapper {{
            display: flex;
            align-items: center;
            background: #fffcf8;
            border: 1px solid rgba(194, 65, 12, 0.2);
            border-radius: 24px;
            padding: 0.2rem 0.5rem;
            margin: 0 0.5rem;
        }}
        
        .page-input-wrapper span {{
            color: #64748b;
            font-size: 0.85rem;
            margin: 0 0.4rem;
        }}
        
        .page-input {{
            background: transparent;
            border: none;
            color: #0f172a;
            width: 40px;
            text-align: center;
            font-size: 0.9rem;
            font-family: inherit;
            outline: none;
            -moz-appearance: textfield;
        }}
        
        .page-input::-webkit-outer-spin-button,
        .page-input::-webkit-inner-spin-button {{
            -webkit-appearance: none;
            margin: 0;
        }}
        
        .navbar-author {{
            font-size: 0.9rem;
            color: #64748b;
            font-family: 'Outfit', sans-serif;
        }}
        
        .reader-layout {{
            display: flex;
            margin-top: 70px;
        }}
        
        .sidebar {{
            width: var(--sidebar-width);
            position: fixed;
            top: 70px;
            bottom: 0;
            left: 0;
            background: rgba(253, 245, 238, 0.6);
            backdrop-filter: blur(20px);
            border-right: 1px solid rgba(194, 65, 12, 0.1);
            padding: 1.5rem;
            overflow-y: auto;
            z-index: 900;
        }}
        
        /* Custom Scrollbar for Sidebar */
        .sidebar::-webkit-scrollbar {{
            width: 6px;
        }}
        .sidebar::-webkit-scrollbar-track {{
            background: transparent;
        }}
        .sidebar::-webkit-scrollbar-thumb {{
            background: rgba(194, 65, 12, 0.1);
            border-radius: 10px;
        }}
        .sidebar::-webkit-scrollbar-thumb:hover {{
            background: rgba(194, 65, 12, 0.2);
        }}
        
        .sidebar-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            color: var(--primary);
            margin-top: 0;
            margin-bottom: 1.2rem;
            border-bottom: 1px solid rgba(194, 65, 12, 0.1);
            padding-bottom: 0.5rem;
        }}
        
        .sidebar-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
            gap: 0.5rem;
        }}
        
        .sidebar-link {{
            display: block;
            text-align: center;
            padding: 0.5rem;
            background: rgba(194, 65, 12, 0.02);
            border: 1px solid rgba(194, 65, 12, 0.08);
            border-radius: 8px;
            color: #64748b;
            text-decoration: none;
            font-size: 0.85rem;
            font-weight: 500;
            transition: all 0.2s ease;
        }}
        
        .sidebar-link:hover {{
            background: rgba(194, 65, 12, 0.08);
            border-color: rgba(194, 65, 12, 0.3);
            color: #c2410c;
        }}
        
        .sidebar-link.active {{
            background: linear-gradient(135deg, #ffedd5, rgba(194, 65, 12, 0.2));
            border-color: var(--primary);
            color: #c2410c;
            box-shadow: 0 0 10px rgba(194, 65, 12, 0.15);
        }}
        
        .main-content {{
            flex: 1;
            margin-left: var(--sidebar-width);
            padding: 3rem 2rem;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        
        .page-container-inner {{
            max-width: 900px;
            width: 100%;
        }}
        
        .book-cover-section {{
            text-align: center;
            margin-bottom: 4rem;
            padding: 2rem;
        }}
        
        .cover-img {{
            max-width: 320px;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(194, 65, 12, 0.15);
            border: 1px solid rgba(194, 65, 12, 0.1);
        }}
        
        .page-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            padding: 2.5rem;
            margin-bottom: 3rem;
            backdrop-filter: blur(10px);
            box-shadow: 0 10px 30px -10px rgba(194, 65, 12, 0.08);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            scroll-margin-top: 90px;
        }}
        
        .page-card:hover {{
            transform: translateY(-3px);
            border-color: rgba(194, 65, 12, 0.2);
            box-shadow: 0 20px 40px -10px rgba(194, 65, 12, 0.15);
        }}
        
        .page-header {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.1rem;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 0;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid rgba(194, 65, 12, 0.1);
            padding-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .kannada-text {{
            font-family: 'Noto Serif Kannada', serif;
            font-size: 1.15rem;
            letter-spacing: 0.02em;
            color: #0f172a;
        }}
        
        .english-text {{
            font-size: 1.05rem;
            color: #334155;
        }}
        
        /* Bilingual Layout CSS Grid */
        .bilingual-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2.5rem;
        }}
        
        @media (min-width: 1024px) {{
            .bilingual-grid {{
                grid-template-columns: 1fr 1fr;
            }}
            .kannada-column {{
                border-right: 1px solid rgba(194, 65, 12, 0.1);
                padding-right: 2.5rem;
            }}
        }}
        
        .column-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--secondary);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-top: 0;
            margin-bottom: 1.2rem;
        }}
        
        .column-title.kn {{
            color: var(--primary);
        }}
        
        /* Responsive / Mobile */
        @media (max-width: 1023px) {{
            .sidebar {{
                display: none;
            }}
            .main-content {{
                margin-left: 0;
                padding: 2rem 1rem;
            }}
            .navbar-author {{
                display: none;
            }}
            .top-navbar {{
                padding: 0 1rem;
            }}
            .navbar-title {{
                font-size: 1.1rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="top-navbar">
        <div class="navbar-title">{title}</div>
        <div class="navbar-nav">
            <button id="prev-btn" class="nav-btn">← Prev</button>
            <div class="page-input-wrapper">
                <span>Page</span>
                <input type="number" id="page-input" class="page-input" min="1" value="1">
                <span>/ <span id="total-pages"></span></span>
            </div>
            <button id="go-btn" class="nav-btn">Go</button>
            <button id="next-btn" class="nav-btn">Next →</button>
        </div>
        <div class="navbar-author">{author}</div>
    </div>
    
    <div class="reader-layout">
        <aside class="sidebar">
            <h3 class="sidebar-title">ಪುಟಗಳು / Pages</h3>
            <div class="sidebar-grid">
                {toc_html}
            </div>
        </aside>
        
        <main class="main-content">
            <div class="page-container-inner">
                <div class="book-cover-section">
                    {cover_html}
                </div>
                {content_html}
            </div>
        </main>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', () => {{
            const pageCards = document.querySelectorAll('.page-card');
            const pageInput = document.getElementById('page-input');
            const totalPagesSpan = document.getElementById('total-pages');
            const goBtn = document.getElementById('go-btn');
            const prevBtn = document.getElementById('prev-btn');
            const nextBtn = document.getElementById('next-btn');
            const sidebarLinks = document.querySelectorAll('.sidebar-link');
            
            let currentPageNum = 1;
            
            if(pageCards.length > 0) {{
                // Extract highest page number from cards
                let maxPage = 0;
                pageCards.forEach(card => {{
                    const num = parseInt(card.id.replace('page-', ''));
                    if(num > maxPage) maxPage = num;
                }});
                totalPagesSpan.textContent = maxPage;
                pageInput.max = maxPage;
            }}            let isProgrammaticScroll = false;
            let programmaticScrollTimeout = null;

            // Function to scroll to a page
            function scrollToPage(pageNum) {{
                const targetCard = document.getElementById('page-' + pageNum);
                if (targetCard) {{
                    isProgrammaticScroll = true;
                    clearTimeout(programmaticScrollTimeout);
                    targetCard.scrollIntoView({{ behavior: 'smooth' }});
                    updateActiveState(pageNum);
                    
                    programmaticScrollTimeout = setTimeout(() => {{
                        isProgrammaticScroll = false;
                    }}, 800);
                }} else {{
                    // If exact page not found, find nearest
                    let nearest = null;
                    let minDiff = Infinity;
                    pageCards.forEach(card => {{
                        const num = parseInt(card.id.replace('page-', ''));
                        const diff = Math.abs(num - pageNum);
                        if(diff < minDiff) {{
                            minDiff = diff;
                            nearest = num;
                        }}
                    }});
                    if(nearest) {{
                        isProgrammaticScroll = true;
                        clearTimeout(programmaticScrollTimeout);
                        document.getElementById('page-' + nearest).scrollIntoView({{ behavior: 'smooth' }});
                        updateActiveState(nearest);
                        
                        programmaticScrollTimeout = setTimeout(() => {{
                            isProgrammaticScroll = false;
                        }}, 800);
                    }}
                }}
            }}
            
            // Update active states in navbar and sidebar
            function updateActiveState(pageNum) {{
                currentPageNum = parseInt(pageNum);
                pageInput.value = pageNum;
                
                // Highlight sidebar link
                sidebarLinks.forEach(link => {{
                    const linkPageNum = link.getAttribute('href').replace('#page-', '');
                    if (linkPageNum === pageNum.toString()) {{
                        link.classList.add('active');
                        // Scroll sidebar to keep active link in view
                        link.scrollIntoView({{ behavior: 'nearest', block: 'nearest' }});
                    }} else {{
                        link.classList.remove('active');
                    }}
                }});
            }}
            
            // Input Enter key listener
            pageInput.addEventListener('keypress', (e) => {{
                if (e.key === 'Enter') {{
                    scrollToPage(pageInput.value);
                }}
            }});
            
            // Go button listener
            goBtn.addEventListener('click', () => {{
                scrollToPage(pageInput.value);
            }});
            
            // Prev button click listener
            prevBtn.addEventListener('click', () => {{
                const index = Array.from(pageCards).findIndex(card => parseInt(card.id.replace('page-', '')) === currentPageNum);
                if (index > 0) {{
                    const prevPageNum = pageCards[index - 1].id.replace('page-', '');
                    scrollToPage(prevPageNum);
                }}
            }});
            
            // Next button click listener
            nextBtn.addEventListener('click', () => {{
                const index = Array.from(pageCards).findIndex(card => parseInt(card.id.replace('page-', '')) === currentPageNum);
                if (index < pageCards.length - 1) {{
                    const nextPageNum = pageCards[index + 1].id.replace('page-', '');
                    scrollToPage(nextPageNum);
                }}
            }});
            
            // Sidebar link click listeners
            sidebarLinks.forEach(link => {{
                link.addEventListener('click', (e) => {{
                    e.preventDefault();
                    const pageNum = link.getAttribute('href').replace('#page-', '');
                    scrollToPage(pageNum);
                    // Update URL hash without scrolling
                    history.pushState(null, null, '#page-' + pageNum);
                }});
            }});
            
            // Scroll spy using IntersectionObserver
            const observerOptions = {{
                root: null,
                rootMargin: '-80px 0px -50% 0px', // Trigger when card enters upper-middle viewport
                threshold: 0
            }};
            
            const observer = new IntersectionObserver((entries) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting && !isProgrammaticScroll) {{
                        const pageNum = entry.target.id.replace('page-', '');
                        updateActiveState(pageNum);
                    }}
                }});
            }}, observerOptions);
            
            pageCards.forEach(card => observer.observe(card));
            
            // Handle initial page load from hash
            const hash = window.location.hash;
            if (hash && hash.startsWith('#page-')) {{
                const pageNum = hash.replace('#page-', '');
                setTimeout(() => scrollToPage(pageNum), 500);
            }} else if (pageCards.length > 0) {{
                // Set page 1 active by default
                const firstPageNum = pageCards[0].id.replace('page-', '');
                updateActiveState(firstPageNum);
            }}
        }});
    </script>
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
        toc_items.append(f'<a class="sidebar-link" href="#page-{page_num}">{page_num}</a>')
        content_cards.append(f"""
        <div class="page-card" id="page-{page_num}">
            <div class="page-header"><span>ಪುಟ {page_num}</span></div>
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
            content_html="".join(content_cards),
            edition="kannada"
        ))
        
    # 2. English Only
    en_html_path = None
    if english_pages:
        toc_items = []
        content_cards = []
        for page_num in sorted(english_pages.keys()):
            toc_items.append(f'<a class="sidebar-link" href="#page-{page_num}">{page_num}</a>')
            content_cards.append(f"""
            <div class="page-card" id="page-{page_num}">
                <div class="page-header"><span>Page {page_num}</span></div>
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
                content_html="".join(content_cards),
                edition="english"
            ))
            
    # 3. Bilingual
    bi_html_path = None
    if english_pages:
        toc_items = []
        content_cards = []
        all_pages = sorted(list(set(kannada_pages.keys()) | set(english_pages.keys())))
        for page_num in all_pages:
            toc_items.append(f'<a class="sidebar-link" href="#page-{page_num}">{page_num}</a>')
            kn_text = kannada_pages.get(page_num, "*ಪುಟ ಖಾಲಿ ಇದೆ*").replace(chr(10), '<br>')
            en_text = english_pages.get(page_num, "*Translation in progress*").replace(chr(10), '<br>')
            
            content_cards.append(f"""
            <div class="page-card" id="page-{page_num}">
                <div class="page-header"><span>Page {page_num} | ಪುಟ {page_num}</span></div>
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
                content_html="".join(content_cards),
                edition="bilingual"
            ))
            
    return kn_html_path, en_html_path, bi_html_path


def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    print("[RUN]: Running E-Book Compiler (HTML Only)...")
    
    kn_pages = load_pages(KANNADA_DIR)
    en_pages = load_pages(ENGLISH_DIR)
    
    if not kn_pages:
        print("[ERROR]: No Kannada page data found.")
        sys.exit(1)
        
    cover_path = find_cover_image()
    cover_b64 = None
    if cover_path:
        with open(cover_path, "rb") as f:
            cover_b64 = base64.b64encode(f.read()).decode("utf-8")
            
    print("[COMPILE]: Generating Premium HTML files with Dark Indic Theme...")
    kn_html, en_html, bi_html = compile_html(kn_pages, en_pages, cover_b64, OUTPUT_DIR)
    print(f"   Created: {kn_html}")
    if en_html: print(f"   Created: {en_html}")
    if bi_html: print(f"   Created: {bi_html}")
    
    print("\n[DEPLOY]: Copying to Vercel API directory...")
    os.makedirs(API_DATA_DIR, exist_ok=True)
    
    # We delete old markdown/epub files from both places
    for f in os.listdir(OUTPUT_DIR):
        if not f.endswith('.html'):
            try: os.remove(os.path.join(OUTPUT_DIR, f))
            except: pass
            
    for f in os.listdir(API_DATA_DIR):
        if not f.endswith('.html'):
            try: os.remove(os.path.join(API_DATA_DIR, f))
            except: pass
    
    # Copy html files
    for fname in os.listdir(OUTPUT_DIR):
        if fname.endswith('.html'):
            shutil.copy(os.path.join(OUTPUT_DIR, fname), os.path.join(API_DATA_DIR, fname))
            print(f"   Copied: {fname}")
            
    print("[DONE]: E-Book compilation finished!")

if __name__ == "__main__":
    main()
