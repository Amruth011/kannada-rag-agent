# scratch/generate_subpages.py
import re

def count_words(html_text):
    # Strip HTML tags and entities
    text = re.sub(r'<[^>]+>', ' ', html_text)
    text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
    words = text.split()
    return len(words)

# Common Navigation Header & Footer Generator for Subpages
def get_subpage_header(active_nav="about"):
    return f"""    <div class="top-banner">✦ CELEBRATING KANNADA LITERATURE WITH ADVANCED BILINGUAL AI ✦</div>
    <header class="nav-header">
        <div class="nav-inner">
            <a href="/" class="logo">ಹೇಳಿ ಹೋಗು <span>ಕಾರಣ</span></a>
            <div class="nav-actions">
                <nav class="subpage-nav">
                    <a href="/" class="subpage-nav-link">🏠 Home</a>
                    <a href="/about" class="subpage-nav-link {'active' if active_nav == 'about' else ''}">📖 About Us</a>
                    <a href="/contact" class="subpage-nav-link {'active' if active_nav == 'contact' else ''}">📬 Contact Us</a>
                    <a href="/privacy" class="subpage-nav-link {'active' if active_nav == 'privacy' else ''}">🔒 Privacy Policy</a>
                </nav>
                <button id="theme-toggle-btn" class="theme-btn" onclick="toggleTheme()" aria-label="Toggle Theme">🌓</button>
            </div>
        </div>
    </header>"""

def get_subpage_footer():
    return """    <footer>
        <div class="footer-container">
            <div class="footer-links">
                <a href="/">Home</a>
                <span class="sep">|</span>
                <a href="/about">About Us</a>
                <span class="sep">|</span>
                <a href="/contact">Contact Us</a>
                <span class="sep">|</span>
                <a href="/privacy">Privacy Policy</a>
                <span class="sep">|</span>
                <a href="https://github.com/Amruth011/kannada-rag-agent" target="_blank" rel="noopener noreferrer">GitHub</a>
            </div>
            <p class="footer-copy">© 2026 <strong>Heli Hogu Kaarana</strong> — Bilingual AI Literary Companion. Dedicated to the celebration and digital preservation of Kannada Literature.</p>
            <p class="footer-adsense-notice">This website displays advertisements delivered via Google AdSense and analyzes traffic via Google Analytics. By browsing our website, you agree to our <a href="/privacy">Privacy Policy</a>.</p>
        </div>
    </footer>"""

print("Subpage builder loaded.")
