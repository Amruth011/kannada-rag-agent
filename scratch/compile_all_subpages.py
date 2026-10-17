# scratch/compile_all_subpages.py
import re

COMMON_HEAD = """
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" type="image/png" href="/favicon.png">
    <link rel="shortcut icon" type="image/png" href="/favicon.png">
    <link rel="apple-touch-icon" href="/favicon.png">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,700;0,900;1,400&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Noto+Serif+Kannada:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #c2410c;
            --primary-hover: #9a3412;
            --primary-light: rgba(194, 65, 12, 0.08);
            --accent: #d97706;
            --bg: #fffcf8;
            --bg-secondary: #fdf5ee;
            --card: #ffffff;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: rgba(194, 65, 12, 0.12);
            --shadow: 0 10px 30px -10px rgba(194, 65, 12, 0.1);
        }
        body.dark-mode {
            --primary: #ea580c;
            --primary-hover: #f97316;
            --primary-light: rgba(234, 88, 12, 0.15);
            --accent: #f59e0b;
            --bg: #090d16;
            --bg-secondary: #0f172a;
            --card: #1e293b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --border: rgba(249, 115, 22, 0.18);
            --shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.6);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Plus Jakarta Sans', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.7;
            transition: background 0.3s ease, color 0.3s ease;
        }
        .top-banner {
            width: 100%;
            background: linear-gradient(90deg, #b45309, #c2410c, #b45309);
            color: #fff;
            font-size: 0.72rem;
            font-weight: 700;
            text-align: center;
            padding: 0.55rem;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }
        .nav-header {
            width: 100%;
            background: rgba(255, 255, 255, 0.88);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            padding: 0.85rem 1.8rem;
            position: sticky;
            top: 0;
            z-index: 100;
            transition: background 0.3s ease;
        }
        body.dark-mode .nav-header {
            background: rgba(15, 23, 42, 0.88);
        }
        .nav-inner {
            max-width: 1000px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
        }
        .logo {
            font-family: 'Playfair Display', serif;
            font-size: 1.45rem;
            font-weight: 800;
            color: var(--text);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .logo span { color: var(--primary); }
        .nav-links-group {
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .nav-link {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--text-muted);
            text-decoration: none;
            padding: 0.4rem 0.8rem;
            border-radius: 8px;
            transition: all 0.2s ease;
            white-space: nowrap;
        }
        .nav-link:hover {
            color: var(--primary);
            background: var(--primary-light);
        }
        .nav-link.active {
            color: #ffffff;
            background: var(--primary);
            border-radius: 20px;
            font-weight: 700;
        }
        .theme-toggle-btn {
            background: var(--primary-light);
            border: 1px solid var(--border);
            color: var(--text);
            font-size: 1.05rem;
            padding: 0.35rem 0.6rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .theme-toggle-btn:hover {
            transform: scale(1.08);
        }
        main {
            max-width: 940px;
            width: 100%;
            margin: 0 auto;
            padding: 3rem 1.5rem 5rem;
            flex: 1;
        }
        .page-header {
            text-align: center;
            margin-bottom: 3rem;
        }
        .page-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: var(--primary-light);
            color: var(--primary);
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            padding: 5px 14px;
            border-radius: 99px;
            border: 1px solid var(--border);
            margin-bottom: 1rem;
        }
        h1 {
            font-family: 'Playfair Display', serif;
            font-size: clamp(2rem, 5vw, 2.9rem);
            color: var(--text);
            margin-bottom: 0.8rem;
            line-height: 1.2;
            font-weight: 800;
        }
        .page-desc {
            font-size: 1.05rem;
            color: var(--text-muted);
            max-width: 680px;
            margin: 0 auto;
            line-height: 1.6;
        }
        .content-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2.4rem;
            margin-bottom: 2rem;
            box-shadow: var(--shadow);
        }
        h2 {
            font-family: 'Playfair Display', serif;
            font-size: 1.45rem;
            font-weight: 700;
            color: var(--primary);
            margin: 2.2rem 0 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            line-height: 1.3;
        }
        .content-card > h2:first-child { margin-top: 0; }
        h3 {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--text);
            margin: 1.4rem 0 0.5rem;
        }
        p, li {
            font-size: 0.95rem;
            line-height: 1.8;
            color: var(--text);
            margin-bottom: 1rem;
        }
        body.dark-mode p, body.dark-mode li {
            color: #cbd5e1;
        }
        ul, ol {
            padding-left: 1.6rem;
            margin-bottom: 1.2rem;
        }
        li { margin-bottom: 0.5rem; }
        a {
            color: var(--primary);
            text-decoration: underline;
            text-underline-offset: 3px;
        }
        a:hover { color: var(--accent); }
        .highlight-box {
            background: var(--primary-light);
            border-left: 4px solid var(--primary);
            border-radius: 0 12px 12px 0;
            padding: 1.2rem 1.4rem;
            margin: 1.6rem 0;
            font-size: 0.94rem;
            line-height: 1.7;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.2rem;
            margin: 1.8rem 0;
        }
        .feature-box {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 1.4rem;
        }
        .feature-icon {
            font-size: 1.8rem;
            margin-bottom: 0.6rem;
            display: block;
        }
        .feature-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 0.4rem;
        }
        .feature-desc {
            font-size: 0.86rem;
            color: var(--text-muted);
            line-height: 1.55;
            margin: 0;
        }
        .kannada-quote {
            font-family: 'Noto Serif Kannada', 'Playfair Display', serif;
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--primary);
            border-left: 3px solid var(--primary);
            padding-left: 1rem;
            margin: 1.4rem 0;
            line-height: 1.6;
        }
        /* CONTACT FORM STYLES */
        .contact-layout {
            display: grid;
            grid-template-columns: 1fr 1.35fr;
            gap: 2rem;
            align-items: start;
        }
        @media (max-width: 780px) {
            .contact-layout { grid-template-columns: 1fr; }
        }
        .contact-info-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 2rem;
        }
        .info-item {
            display: flex;
            gap: 12px;
            margin-bottom: 1.4rem;
            align-items: flex-start;
        }
        .info-icon {
            font-size: 1.4rem;
            line-height: 1;
        }
        .info-title {
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            margin-bottom: 2px;
        }
        .info-value {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text);
        }
        .form-group {
            margin-bottom: 1.2rem;
            text-align: left;
        }
        .form-label {
            display: block;
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--text);
            margin-bottom: 6px;
            letter-spacing: 0.3px;
        }
        .form-input, .form-select, .form-textarea {
            width: 100%;
            padding: 11px 14px;
            border: 1px solid var(--border);
            border-radius: 10px;
            font-family: inherit;
            font-size: 0.92rem;
            background: var(--bg);
            color: var(--text);
            outline: none;
            transition: border-color 0.2s, box-shadow 0.2s;
        }
        .form-input:focus, .form-select:focus, .form-textarea:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-light);
        }
        .btn-submit {
            background: linear-gradient(135deg, #c2410c, #ea580c);
            color: #ffffff;
            border: none;
            padding: 12px 24px;
            border-radius: 10px;
            font-size: 0.92rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.25s ease;
            box-shadow: 0 4px 14px rgba(194, 65, 12, 0.35);
            font-family: inherit;
            width: 100%;
        }
        .btn-submit:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 18px rgba(194, 65, 12, 0.45);
        }
        .form-status {
            margin-top: 1rem;
            padding: 10px 14px;
            border-radius: 8px;
            font-size: 0.88rem;
            font-weight: 600;
            display: none;
        }
        .form-status.success {
            display: block;
            background: #dcfce7;
            color: #166534;
            border: 1px solid #86efac;
        }
        .form-status.error {
            display: block;
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fca5a5;
        }
        /* FOOTER */
        footer {
            width: 100%;
            background: linear-gradient(90deg, #b45309, #c2410c, #b45309);
            color: #fff;
            padding: 1.8rem 1.5rem;
            box-sizing: border-box;
            text-align: center;
            font-size: 0.78rem;
            margin-top: auto;
        }
        .footer-container {
            max-width: 900px;
            margin: 0 auto;
        }
        .footer-links {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            align-items: center;
            gap: 0.5rem 1.2rem;
            margin-bottom: 0.8rem;
        }
        .footer-links a {
            color: #ffedd5;
            text-decoration: underline;
            font-weight: 600;
        }
        .footer-links .sep { opacity: 0.4; }
        .footer-copy {
            margin-bottom: 0.5rem;
            color: #ffffff;
            opacity: 0.92;
        }
        .footer-adsense-notice {
            font-size: 0.72rem;
            opacity: 0.8;
            margin-top: 0.4rem;
        }
        .footer-adsense-notice a { color: #ffedd5; }
        @media (max-width: 640px) {
            .nav-inner { flex-direction: column; gap: 0.6rem; }
            .nav-links-group { flex-wrap: wrap; justify-content: center; }
            .content-card { padding: 1.6rem 1.2rem; }
        }
    </style>
    <script>
        function toggleTheme() {
            const body = document.body;
            body.classList.toggle('dark-mode');
            const isDark = body.classList.contains('dark-mode');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            const btn = document.getElementById('theme-toggle-btn');
            if (btn) btn.innerHTML = isDark ? '☀️' : '🌓';
        }
        (function() {
            const saved = localStorage.getItem('theme');
            if (saved === 'dark') {
                document.documentElement.classList.add('dark-mode');
                window.addEventListener('DOMContentLoaded', () => {
                    document.body.classList.add('dark-mode');
                    const btn = document.getElementById('theme-toggle-btn');
                    if (btn) btn.innerHTML = '☀️';
                });
            }
        })();
    </script>
"""

print("Common head configured.")
