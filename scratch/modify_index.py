# scratch/modify_index.py
import os

FILE_PATH = "api/index.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. ChatRequest schema replacement
request_old = """class ChatRequest(BaseModel):
    question: str
    language: str = "English"
    history: Optional[List[dict]] = []"""

request_new = """class ChatRequest(BaseModel):
    question: str
    language: str = "English"
    history: Optional[List[dict]] = []
    threshold: Optional[float] = 0.35
    top_k: Optional[int] = 4
    model: Optional[str] = "gemini\""""

# 2. call_gtts_parallel and clean_markdown_for_tts helper
gtts_old = """def call_gtts_parallel(text, language="kn-IN"):
    \"\"\"Fetch Google TTS chunks in parallel, concatenate as raw MP3 bytes.\"\"\"
    try:
        is_kannada = "kn" in language.lower()
        lang = "kn" if is_kannada else "en"
        
        # Split text into chunks < 200 characters to comply with Google TTS limits
        sentences = re.split(r'(?<=[.!?।])\\s+', text)"""

gtts_new = """def clean_markdown_for_tts(text: str) -> str:
    if not text:
        return ""
    # Clean citations and errors
    clean = re.sub(r'\\[Page \\d+\\]:', '', text).strip()
    clean = re.sub(r'📄 Sources:.*', '', clean).strip()
    clean = re.sub(r'\\[\\(?:GEMINI FAILED|GROQ FAILED|BACKEND ERROR|ERROR\\)[^\\]]*\\]', '', clean).strip()

    # Strip Markdown syntax for cleaner TTS audio reading
    clean = re.sub(r'```[\\s\\S]*?```', '', clean)
    clean = re.sub(r'`([^`]+)`', r'\\1', clean)
    clean = re.sub(r'#+\\s*(.*)', r'\\1', clean)
    clean = re.sub(r'\\[([^\\]]+)\\]\\([^)]+\\)', r'\\1', clean)
    clean = re.sub(r'\\*\\*([^*]+)\\*\\*', r'\\1', clean)
    clean = re.sub(r'\\*([^*]+)\\*', r'\\1', clean)
    clean = re.sub(r'__([^_]+)__', r'\\1', clean)
    clean = re.sub(r'_([^_]+)_', r'\\1', clean)
    clean = re.sub(r'^\\s*[-*+]\\s+', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^\\s*>[\\s\\S]*', '', clean, flags=re.MULTILINE)
    # Remove any stray asterisks, underscores, backticks, or hashes
    clean = clean.replace("*", "").replace("_", "").replace("#", "").replace("`", "")
    clean = re.sub(r'\\n+', ' ', clean)
    clean = re.sub(r'\\s+', ' ', clean)
    return clean.strip()

def call_gtts_parallel(text, language="kn-IN"):
    \"\"\"Fetch Google TTS chunks in parallel, concatenate as raw MP3 bytes.\"\"\"
    try:
        clean = clean_markdown_for_tts(text)
        is_kannada = "kn" in language.lower()
        lang = "kn" if is_kannada else "en"
        
        # Split text into chunks < 200 characters to comply with Google TTS limits
        sentences = re.split(r'(?<=[.!?।])\\s+', clean)"""

# 3. call_sarvam_tts cleaning block
sarvam_old = """def call_sarvam_tts(text, language="kn-IN"):
    \"\"\"Call Sarvam TTS 'Meera' voice (bulbul:v3) in parallel with fallback to Google TTS (gTTS).\"\"\"
    # Clean citations and errors
    clean = re.sub(r'\\[Page \\d+\\]:', '', text).strip()
    clean = re.sub(r'📄 Sources:.*', '', clean).strip()
    clean = re.sub(r'\\[\\(?:GEMINI FAILED|GROQ FAILED|BACKEND ERROR|ERROR\\)[^\\]]*\\]', '', clean).strip()

    # Strip Markdown syntax for cleaner TTS audio reading (e.g. asterisks, code blocks, headers, bullet symbols)
    clean = re.sub(r'```[\\s\\S]*?```', '', clean)
    clean = re.sub(r'`([^`]+)`', r'\\1', clean)
    clean = re.sub(r'#+\\s*(.*)', r'\\1', clean)
    clean = re.sub(r'\\[([^\\]]+)\\]\\([^)]+\\)', r'\\1', clean)
    clean = re.sub(r'\\*\\*([^*]+)\\*\\*', r'\\1', clean)
    clean = re.sub(r'\\*([^*]+)\\*', r'\\1', clean)
    clean = re.sub(r'__([^_]+)__', r'\\1', clean)
    clean = re.sub(r'_([^_]+)_', r'\\1', clean)
    clean = re.sub(r'^\\s*[-*+]\\s+', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'^\\s*>[\\s\\S]*', '', clean, flags=re.MULTILINE)
    clean = re.sub(r'\\n+', ' ', clean)
    clean = re.sub(r'\\s+', ' ', clean)"""

sarvam_new = """def call_sarvam_tts(text, language="kn-IN"):
    \"\"\"Call Sarvam TTS 'Meera' voice (bulbul:v3) in parallel with fallback to Google TTS (gTTS).\"\"\"
    clean = clean_markdown_for_tts(text)"""

# 4. /chat route implementation
chat_old = """@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Use globally loaded BOOK_DATA
        chunks = search_text(request.question, BOOK_DATA, top_k=4) 
        retrieved_pages = [str(c['page']) for c in chunks]
        
        # Implement safe character capping (approx 5,000 chars for Groq)
        pagetext = ""
        current_len = 0
        for c in chunks:
            text_block = f"[Passage from Page {c['page']}]: {c['text']}\\n\\n"
            if current_len + len(text_block) > 5000:
                break
            pagetext += text_block
            current_len += len(text_block)
            
        if not pagetext: pagetext = "No direct passages found."
        
        # Build prompt based on requested language
        if request.language == "English":
            sys_instruction = (
                "You are a professional literary assistant for the Kannada novel 'Heli Hogu Kaarana'. "
                "Use the retrieved passages to answer the user's question. "
                "CRITICAL RULE: You must answer ONLY in English. Do NOT write in Kannada, and do NOT mix Kannada and English in your reply. "
                "All explanations, analysis, and text must be in English. "
                "If the conversation history contains messages in Kannada, ignore their language and reply only in English. "
                "Always cite the exact page numbers from the passages in your answer."
            )
            full_prompt = f\"\"\"RETRIEVED NOVEL PASSAGES:
{pagetext}

Answer the user's question in detail using the retrieved passages. Follow the instructions to write the entire answer in English.

QUESTION: {request.question}
ANSWER in English:\"\"\"
        else:
            sys_instruction = (
                "ನೀವು 'ಹೇಳಿ ಹೋಗು ಕಾರಣ' ಕಾದಂಬರಿಯ ವೃತ್ತಿಪರ ಸಾಹಿತ್ಯ ಸಹಾಯಕರು. "
                "ಹಿಂಪಡೆದ ಪುಸ್ತಕದ ಭಾಗಗಳನ್ನು ಬಳಸಿಕೊಂಡು ಬಳಕೆದಾರರ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರಿಸಿ. "
                "ಪ್ರಮುಖ ನಿಯಮ: ನೀವು ಕಡ್ಡಾಯವಾಗಿ ಮತ್ತು ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡದಲ್ಲೇ ಉತ್ತರಿಸಬೇಕು. "
                "ಯಾವುದೇ ಕಾರಣಕ್ಕೂ ಇಂಗ್ಲಿಷ್ ಬಳಸಬೇಡಿ, ಮತ್ತು ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡದ ಮಿಶ್ರಣವನ್ನು ಬಳಸಬೇಡಿ. "
                "ಎಲ್ಲಾ ವಿವರಣೆಗಳು, ವಿಶ್ಲೇಷಣೆಗಳು ಮತ್ತು ಪಠ್ಯಗಳು ಕಡ್ಡಾಯವಾಗಿ ಕನ್ನಡದಲ್ಲೇ ಇರಬೇಕು. "
                "ಸಂಭಾಷಣೆಯ ಇತಿಹಾಸದಲ್ಲಿ (history) ಇಂಗ್ಲಿಷ್ ಸಂದೇಶಗಳಿದ್ದರೂ ಸಹ, ಅವುಗಳನ್ನು ನಿರ್ಲಕ್ಷಿಸಿ ಮತ್ತು ಈ ಪ್ರಸ್ತುತ ಪ್ರಶ್ನೆಗೆ ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡದಲ್ಲೇ ಉತ್ತರಿಸಿ. "
                "ಉತ್ತರದಲ್ಲಿ ಕಡ್ಡಾಯವಾಗಿ ಸೂಕ್ತ ಪುಟ ಸಂಖ್ಯೆಗಳನ್ನು ಉಲ್ಲೇಖಿಸಿ."
            )
            full_prompt = f\"\"\"ಪುಸ್ತಕದಿಂದ ತೆಗೆದ ವಿಷಯ (RETRIEVED NOVEL PASSAGES):
{pagetext}

ಹಿಂಪಡೆದ ಭಾಗಗಳನ್ನು ಬಳಸಿಕೊಂಡು ಬಳಕೆದಾರರ ಪ್ರಶ್ನೆಗೆ ವಿವರವಾಗಿ ಉತ್ತರಿಸಿ. ಸಂಪೂರ್ಣ ಉತ್ತರವನ್ನು ಕನ್ನಡದಲ್ಲೇ ಬರೆಯುವ ನಿಯಮವನ್ನು ಪಾಲಿಸಿ.

ಪ್ರಶ್ನೆ (QUESTION): {request.question}
ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರ (ANSWER in Kannada):\"\"\"
        
        answer = call_gemini(full_prompt, history=request.history, system_instruction=sys_instruction)
        return ChatResponse(answer=answer, sources=retrieved_pages)
    except Exception:
        return ChatResponse(answer=f"[BACKEND ERROR]: {traceback.format_exc()[:500]}", sources=[])"""

chat_new = """@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        top_k = request.top_k or 4
        threshold = request.threshold if request.threshold is not None else 0.35
        model_choice = request.model or "gemini"

        # Retrieve a pool of candidate chunks first
        candidates = search_text(request.question, BOOK_DATA, top_k=20)
        
        query_words = [w for w in request.question.lower().split() if len(w) > 0]
        max_possible_score = len(query_words) * 10 if query_words else 10
        
        filtered_chunks = []
        retrieved_pages = []
        
        for c in candidates:
            score = c.get('score', 0)
            score_percent = min(100, int((score / max_possible_score) * 100))
            if (score_percent / 100.0) >= threshold:
                filtered_chunks.append(c)
                retrieved_pages.append(f"Page {c['page']} ({score_percent}% Match)")
        
        # Slice to requested depth
        chunks = filtered_chunks[:top_k]
        retrieved_pages = retrieved_pages[:top_k]
        
        # Implement safe character capping (approx 5,000 chars for Groq)
        pagetext = ""
        current_len = 0
        for c in chunks:
            text_block = f"[Passage from Page {c['page']}]: {c['text']}\\n\\n"
            if current_len + len(text_block) > 5000:
                break
            pagetext += text_block
            current_len += len(text_block)
            
        if not pagetext: 
            pagetext = "No direct passages found matching the current similarity threshold."
        
        # Build prompt based on requested language
        if request.language == "English":
            sys_instruction = (
                "You are a professional literary assistant for the Kannada novel 'Heli Hogu Kaarana'. "
                "Use the retrieved passages to answer the user's question. "
                "CRITICAL RULE: You must answer ONLY in English. Do NOT write in Kannada script, and do NOT mix Kannada and English in your reply. "
                "All explanations, character names, and text must be in English. "
                "If the conversation history contains messages in Kannada, ignore their language and reply only in English. "
                "Always cite the exact page numbers from the passages in your answer (e.g. '(Page 24)')."
            )
            full_prompt = f\"\"\"RETRIEVED NOVEL PASSAGES:
{pagetext}

Answer the user's question in detail using the retrieved passages. Follow the instructions to write the entire answer in English. Do not use Kannada words.

QUESTION: {request.question}
ANSWER in English:\"\"\"
        else:
            sys_instruction = (
                "ನೀವು 'ಹೇಳಿ ಹೋಗು ಕಾರಣ' ಕಾದಂಬರಿಯ ವೃತ್ತಿಪರ ಸಾಹಿತ್ಯ ಸಹಾಯಕರು. "
                "ಹಿಂಪಡೆದ ಪುಸ್ತಕದ ಭಾಗಗಳನ್ನು ಬಳಸಿಕೊಂಡು ಬಳಕೆದಾರರ ಪ್ರಶ್ನೆಗೆ ಉತ್ತರಿಸಿ. "
                "ಪ್ರಮುಖ ನಿಯಮ: ನೀವು ಕಡ್ಡಾಯವಾಗಿ ಮತ್ತು ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡದಲ್ಲೇ ಉತ್ತರಿಸಬೇಕು. "
                "ಯಾವುದೇ ಕಾರಣಕ್ಕೂ ಇಂಗ್ಲಿಷ್ ಬಳಸಬೇಡಿ, ಮತ್ತು ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡದ ಮಿಶ್ರಣವನ್ನು ಬಳಸಬೇಡಿ. "
                "ಎಲ್ಲಾ ವಿವರಣೆಗಳು, ಪಾತ್ರಗಳ ಹೆಸರುಗಳು ಮತ್ತು ವಿಶ್ಲೇಷಣೆಗಳು ಕಡ್ಡಾಯವಾಗಿ ಕನ್ನಡದಲ್ಲೇ ಇರಬೇಕು. "
                "ಸಂಭಾಷಣೆಯ ಇತಿಹಾಸದಲ್ಲಿ (history) ಇಂಗ್ಲಿಷ್ ಸಂದೇಶಗಳಿದ್ದರೂ ಸಹ, ಅವುಗಳನ್ನು ನಿರ್ಲಕ್ಷಿಸಿ ಮತ್ತು ಈ ಪ್ರಸ್ತುತ ಪ್ರಶ್ನೆಗೆ ಸಂಪೂರ್ಣವಾಗಿ ಕನ್ನಡದಲ್ಲೇ ಉತ್ತರಿಸಿ. "
                "ಉತ್ತರದಲ್ಲಿ ಕಡ್ಡಾಯವಾಗಿ ಸೂಕ್ತ ಪುಟ ಸಂಖ್ಯೆಗಳನ್ನು ಉಲ್ಲೇಖಿಸಿ (ಉದಾಹರಣೆಗೆ: '(ಪುಟ 24)')."
            )
            full_prompt = f\"\"\"ಪುಸ್ತಕದಿಂದ ತೆಗೆದ ವಿಷಯ (RETRIEVED NOVEL PASSAGES):
{pagetext}

ಹಿಂಪಡೆದ ಭಾಗಗಳನ್ನು ಬಳಸಿಕೊಂಡು ಬಳಕೆದಾರರ ಪ್ರಶ್ನೆಗೆ ವಿವರವಾಗಿ ಉತ್ತರಿಸಿ. ಸಂಪೂರ್ಣ ಉತ್ತರವನ್ನು ಕನ್ನಡದಲ್ಲೇ ಬರೆಯುವ ನಿಯಮವನ್ನು ಪಾಲಿಸಿ. ಇಂಗ್ಲಿಷ್ ಪದಗಳನ್ನು ಬಳಸಬೇಡಿ.

ಪ್ರಶ್ನೆ (QUESTION): {request.question}
ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರ (ANSWER in Kannada):\"\"\"
        
        if model_choice == "groq":
            answer = call_groq(full_prompt, history=request.history, system_instruction=sys_instruction)
        else:
            answer = call_gemini(full_prompt, history=request.history, system_instruction=sys_instruction)
            
        return ChatResponse(answer=answer, sources=retrieved_pages)
    except Exception:
        return ChatResponse(answer=f"[BACKEND ERROR]: {traceback.format_exc()[:500]}", sources=[])"""

# 5. HTML sources container
sources_old = """                    <div id="ans-container">
                        <div id="ans">
                            <div id="text-res"></div>
                            <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">"""

sources_new = """                    <div id="ans-container">
                        <div id="ans">
                            <div id="text-res"></div>
                            <div id="sources-container" style="display: none; margin-top: 1.2rem; margin-bottom: 1.2rem; padding: 0.8rem 1rem; background: var(--bg-secondary); border: 1px dashed var(--primary-light); border-radius: 12px;">
                                <div style="font-size: 0.72rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
                                    <span>📖</span> Cited Sources & Match Scores
                                </div>
                                <div id="sources-list" style="display: flex; gap: 8px; flex-wrap: wrap;"></div>
                            </div>
                            <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">"""

# 6. HTML playback speed control button
speed_old = """                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <button id="play-pause-btn" class="player-btn" onclick="togglePlayPause()" style="background: var(--primary); border: none; width: 32px; height: 32px; border-radius: 50%; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; outline: none;">▶</button>
                                        <button class="player-btn" onclick="skipAudio(-5)" style="background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.85rem; font-weight: bold; outline: none; padding: 2px;">↩ 5s</button>
                                        <button class="player-btn" onclick="skipAudio(5)" style="background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.85rem; font-weight: bold; outline: none; padding: 2px;">5s ↪</button>
                                    </div>"""

speed_new = """                                    <div style="display: flex; align-items: center; gap: 8px;">
                                        <button id="play-pause-btn" class="player-btn" onclick="togglePlayPause()" style="background: var(--primary); border: none; width: 32px; height: 32px; border-radius: 50%; color: white; cursor: pointer; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; outline: none;">▶</button>
                                        <button class="player-btn" onclick="skipAudio(-5)" style="background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.85rem; font-weight: bold; outline: none; padding: 2px;">↩ 5s</button>
                                        <button class="player-btn" onclick="skipAudio(5)" style="background: none; border: none; color: var(--primary); cursor: pointer; font-size: 0.85rem; font-weight: bold; outline: none; padding: 2px;">5s ↪</button>
                                        <button id="audio-speed-btn" class="player-btn" onclick="changePlaybackSpeed()" style="background: none; border: 1px solid var(--primary); color: var(--primary); cursor: pointer; font-size: 0.75rem; font-weight: 800; padding: 3px 6px; border-radius: 6px; outline: none; min-width: 42px;">1.0x</button>
                                    </div>"""

# 7. Character detail card enhancements placeholder
char_card_old = """                        <!-- Character Biography Card -->
                        <div id="char-detail-card" class="char-card" style="display:none;">
                            <div class="char-tabs">
                                <button class="char-tab-btn active" id="btn-char-en" onclick="setCharLang('en')">English</button>
                                <button class="char-tab-btn" id="btn-char-kn" onclick="setCharLang('kn')">ಕನ್ನಡ</button>
                            </div>
                            <h3 id="char-name">Character Name <span class="badge" id="char-badge">Protagonist</span></h3>
                            <p id="char-desc" style="color: var(--text-muted); font-size: 0.92rem; line-height: 1.6;"></p>
                            <div style="margin-top: 0.8rem;">
                                <strong style="font-size: 0.85rem; color: var(--primary);">📖 Key Pages:</strong>
                                <span id="char-pages" style="font-size: 0.85rem; color: var(--text-muted);"></span>
                            </div>
                        </div>"""

char_card_new = """                        <!-- Character Biography Card -->
                        <div id="char-detail-card" class="char-card" style="display:none;">
                            <div class="char-tabs">
                                <button class="char-tab-btn active" id="btn-char-en" onclick="setCharLang('en')">English</button>
                                <button class="char-tab-btn" id="btn-char-kn" onclick="setCharLang('kn')">ಕನ್ನಡ</button>
                            </div>
                            <h3 id="char-name">Character Name <span class="badge" id="char-badge">Protagonist</span></h3>
                            <p id="char-desc" style="color: var(--text-muted); font-size: 0.92rem; line-height: 1.6;"></p>
                            <div style="margin-top: 0.8rem;">
                                <strong style="font-size: 0.85rem; color: var(--primary);">📖 Key Pages:</strong>
                                <span id="char-pages" style="font-size: 0.85rem; color: var(--text-muted);"></span>
                            </div>
                            <div style="margin-top: 1rem; padding-top: 0.8rem; border-top: 1px solid var(--border);">
                                <strong style="font-size: 0.85rem; color: var(--primary); display: flex; align-items: center; gap: 6px;">
                                    🎭 Sentiment & Tone:
                                </strong>
                                <div id="char-sentiment" style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px; font-style: italic;"></div>
                            </div>
                            <div style="margin-top: 1rem;">
                                <strong style="font-size: 0.85rem; color: var(--primary);">🔗 Key Relationships:</strong>
                                <div id="char-relations" style="display: flex; flex-direction: column; gap: 6px; margin-top: 6px;"></div>
                            </div>
                            <div style="margin-top: 1.2rem; text-align: right;">
                                <button id="char-ask-btn" onclick="askAboutActiveChar()" class="main-btn" style="padding: 0.4rem 1rem; font-size: 0.8rem; width: auto; display: inline-flex; align-items: center; gap: 6px; border-radius: 8px;">
                                    💬 Ask AI about Character
                                </button>
                            </div>
                        </div>"""

# 8. CHAR_DATA JS object replacement
char_data_old = """            // --- CHARACTER MAP DATA & LOGIC ---
            const CHAR_DATA = {
                himavant: {
                    name_en: "Himavant",
                    name_kn: "ಹಿಮವಂತ್",
                    badge_en: "Protagonist",
                    badge_kn: "ಕಥಾನಾಯಕ",
                    desc_en: "The passionate, intense protagonist of Heli Hogu Kaarana. He is a man of deep emotions, conflicted by his love for Prarthana and his complex life choices in a gritty underworld environment.",
                    desc_kn: "ಕಾದಂಬರಿಯ ಕಥಾನಾಯಕ. ತೀವ್ರವಾದ ಭಾವನೆಗಳುಳ್ಳ, ಪ್ರಾರ್ಥನಾಳ ಮೇಲಿನ ಪ್ರೀತಿ ಹಾಗೂ ತನ್ನ ಜೀವನದ ಸಂಕೀರ್ಣ ನಿರ್ಧಾರಗಳ ನಡುವೆ ಒದ್ದಾಡುವ ತೇಜಸ್ವಿ ವ್ಯಕ್ತಿತ್ವ.",
                    pages: "Major presence throughout the novel (e.g. Pages 1, 10, 45, 120, 240, 310)"
                },
                prarthana: {
                    name_en: "Prarthana",
                    name_kn: "ಪ್ರಾರ್ಥನಾ",
                    badge_en: "Female Lead",
                    badge_kn: "ನಾಯಕಿ",
                    desc_en: "The mysterious, beautiful female lead. Her relationship with Himavant is full of emotional depth, silence, and unspoken words, driving much of the story's emotional tension.",
                    desc_kn: "ಕಾದಂಬರಿಯ ನಾಯಕಿ. ಹಿಮವಂತನ ಪ್ರೀತಿಯ ಸೆಲೆ. ಅವಳ ಮೌನ, ಗಾಂಭೀರ್ಯ ಮತ್ತು ರಹಸ್ಯಮಯ ನಡವಳಿಕೆ ಇಡೀ ಕಥೆಗೆ ಹೊಸ ಭಾವನಾತ್ಮಕ ತಿರುವು ನೀಡುತ್ತದೆ.",
                    pages: "Pages 5, 22, 54, 108, 195, 280, 340"
                },
                ravi: {
                    name_en: "Ravi",
                    name_kn: "ರವಿ",
                    badge_en: "Close Friend",
                    badge_kn: "ಆತ್ಮೀಯ ಗೆಳೆಯ",
                    desc_en: "Himavant's close companion and sounding board. He plays a vital role in balancing Himavant's volatile decisions and acts as a bridge of sanity in his turbulent life.",
                    desc_kn: "ಹಿಮವಂತನ ನಿಷ್ಠಾವಂತ ಒಡನಾಡಿ. ಕಷ್ಟದ ಸಮಯದಲ್ಲಿ ಜೊತೆಯಾಗಿ ನಿಂತು, ಜೀವನದ ಮಹತ್ತರ ತಿರುವುಗಳಲ್ಲಿ ಮಾರ್ಗದರ್ಶನ ನೀಡುವ ವಿಶ್ವಾಸಾರ್ಹ ಗೆಳೆಯ.",
                    pages: "Pages 15, 42, 87, 134, 210, 295"
                },
                rasool: {
                    name_en: "Rasool Jamadar",
                    name_kn: "ರಸೂಲ್ ಜಮಾದಾರ",
                    badge_en: "Companion / Protector",
                    badge_kn: "ನಿಷ್ಠಾವಂತ ರಕ್ಷಕ",
                    desc_en: "A rugged associate and protector, representing the fierce and loyal underground world elements in Ravi Belagere's classic narrative landscape.",
                    desc_kn: "ಹಿಮವಂತನಿಗೆ ನೆರಳಾಗಿ ನಿಲ್ಲುವ ಒರಟು ಸ್ವಭಾವದ ನಿಷ್ಠಾವಂತ ಸಾಥಿ. ಭೂಗತ ಜಗತ್ತಿನ ಕಥಾ ಹೆಣಿಗೆಯಲ್ಲಿ ಧೈರ್ಯ ಮತ್ತು ನಿಷ್ಠೆಯ ಸಂಕೇತ.",
                    pages: "Pages 34, 78, 112, 160, 255"
                },
                belagere: {
                    name_en: "Ravi Belagere",
                    name_kn: "ರವಿ ಬೆಳಗೆರೆ",
                    badge_en: "Author / Narrator",
                    badge_kn: "ಲೇಖಕ / ನಿರೂಪಕ",
                    desc_en: "The author and narrator who weaves himself directly into the story's atmosphere. He narrates with his signature intensity, suspense, and emotional attachment to his characters.",
                    desc_kn: "ಕಾದಂಬರಿಯ ಕರ್ತೃ ಮತ್ತು ಸೂತ್ರಧಾರ. ತಮ್ಮದೇ ಆದ ವಿಶಿಷ್ಟ ಪತ್ರಿಕೋದ್ಯಮ ಮತ್ತು ಸಾಹಿತ್ಯ ಶೈಲಿಯಲ್ಲಿ ಕಥೆಯನ್ನು ಕಟ್ಟಿಕೊಡುತ್ತಾ, ಓದುಗರನ್ನು ಸೆಳೆಯುವ ನಿರೂಪಕ.",
                    pages: "Narrates and comments throughout the entire novel"
                }
            };"""

char_data_new = """            // --- CHARACTER MAP DATA & LOGIC ---
            const CHAR_DATA = {
                himavant: {
                    name_en: "Himavant",
                    name_kn: "ಹಿಮವಂತ್",
                    badge_en: "Protagonist",
                    badge_kn: "ಕಥಾನಾಯಕ",
                    desc_en: "The passionate, intense protagonist of Heli Hogu Kaarana. He is a man of deep emotions, conflicted by his love for Prarthana and his complex life choices in a gritty underworld environment.",
                    desc_kn: "ಕಾದಂಬರಿಯ ಕಥಾನಾಯಕ. ತೀವ್ರವಾದ ಭಾವನೆಗಳುಳ್ಳ, ಪ್ರಾರ್ಥನಾಳ ಮೇಲಿನ ಪ್ರೀತಿ ಹಾಗೂ ತನ್ನ ಜೀವನದ ಸಂಕೀರ್ಣ ನಿರ್ಧಾರಗಳ ನಡುವೆ ಒದ್ದಾಡುವ ತೇಜಸ್ವಿ ವ್ಯಕ್ತಿತ್ವ.",
                    pages: "Major presence throughout the novel (e.g. Pages 1, 10, 45, 120, 240, 310)",
                    sentiment_en: "Highly volatile, deeply nostalgic and passionate (fluctuates between determination and intense regret).",
                    sentiment_kn: "ಅತ್ಯಂತ ತೀವ್ರವಾದ ಭಾವನಾತ್ಮಕ ವ್ಯಕ್ತಿತ್ವ (ಆತ್ಮವಿಶ್ವಾಸ ಮತ್ತು ತೀವ್ರ ವಿಷಾದಗಳ ನಡುವೆ ಬದಲಾಗುತ್ತಿರುತ್ತದೆ).",
                    query_en: "Tell me about Himavant's journey and choices in Heli Hogu Kaarana",
                    query_kn: "ಹಿಮವಂತನ ಪಾತ್ರ ಮತ್ತು ಅವನ ಪ್ರಮುಖ ನಿರ್ಧಾರಗಳ ಬಗ್ಗೆ ತಿಳಿಸಿ",
                    relations: [
                        { name_en: "Prarthana", name_kn: "ಪ್ರಾರ್ಥನಾ", role_en: "Love interest, source of tension", role_kn: "ಪ್ರೀತಿಪಾತ್ರರು, ಕಥೆಯ ತಿರುವು" },
                        { name_en: "Ravi", name_kn: "ರವಿ", role_en: "Loyal companion, advisor", role_kn: "ನಿಷ್ಠಾವಂತ ಗೆಳೆಯ, ಸಮಾಲೋಚಕ" },
                        { name_en: "Rasool Jamadar", name_kn: "ರಸೂಲ್ ಜಮಾದಾರ", role_en: "Protector in underworld", role_kn: "ಭೂಗತ ಜಗತ್ತಿನ ರಕ್ಷಕ" }
                    ]
                },
                prarthana: {
                    name_en: "Prarthana",
                    name_kn: "ಪ್ರಾರ್ಥನಾ",
                    badge_en: "Female Lead",
                    badge_kn: "ನಾಯಕಿ",
                    desc_en: "The mysterious, beautiful female lead. Her relationship with Himavant is full of emotional depth, silence, and unspoken words, driving much of the story's emotional tension.",
                    desc_kn: "ಕಾದಂಬರಿಯ ನಾಯಕಿ. ಹಿಮವಂತನ ಪ್ರೀತಿಯ ಸೆಲೆ. ಅವಳ ಮೌನ, ಗಾಂಭೀರ್ಯ ಮತ್ತು ರಹಸ್ಯಮಯ ನಡವಳಿಕೆ ಇಡೀ ಕಥೆಗೆ ಹೊಸ ಭಾವನಾತ್ಮಕ ತಿರುವು ನೀಡುತ್ತದೆ.",
                    pages: "Pages 5, 22, 54, 108, 195, 280, 340",
                    sentiment_en: "Intense, silent, and resilient (carries unspoken grief and quiet resolve).",
                    sentiment_kn: "ಗಂಭೀರ, ಮೌನ ಮತ್ತು ಸ್ಥಿತಪ್ರಜ್ಞೆ (ಹೇಳಲಾಗದ ದುಃಖ ಹಾಗೂ ಮೌನ ನಿರ್ಧಾರದ ಪ್ರತಿರೂಪ).",
                    query_en: "Analyze Prarthana's character and her silence in Heli Hogu Kaarana",
                    query_kn: "ಪ್ರಾರ್ಥನಾಳ ಪಾತ್ರ ಮತ್ತು ಅವಳ ಮೌನದ ಮಹತ್ವವನ್ನು ವಿವರಿಸಿ",
                    relations: [
                        { name_en: "Himavant", name_kn: "ಹಿಮವಂತ್", role_en: "Beloved partner, emotional anchor", role_kn: "ಪ್ರೀತಿಯ ಸೆಲೆ, ಭಾವನಾತ್ಮಕ ಆಸರೆ" },
                        { name_en: "Ravi", name_kn: "ರವಿ", role_en: "Confidant, helper", role_kn: "ಗೆಳೆಯ, ಕಷ್ಟಕಾಲದ ಸಹಾಯಕಿ" }
                    ]
                },
                ravi: {
                    name_en: "Ravi",
                    name_kn: "ರವಿ",
                    badge_en: "Close Friend",
                    badge_kn: "ಆತ್ಮೀಯ ಗೆಳೆಯ",
                    desc_en: "Himavant's close companion and sounding board. He plays a vital role in balancing Himavant's volatile decisions and acts as a bridge of sanity in his turbulent life.",
                    desc_kn: "ಹಿಮವಂತನ ನಿಷ್ಠಾವಂತ ಒಡನಾಡಿ. ಕಷ್ಟದ ಸಮಯದಲ್ಲಿ ಜೊತೆಯಾಗಿ ನಿಂತು, ಜೀವನದ ಮಹತ್ತರ ತಿರುವುಗಳಲ್ಲಿ ಮಾರ್ಗದರ್ಶನ ನೀಡುವ ವಿಶ್ವಾಸಾರ್ಹ ಗೆಳೆಯ.",
                    pages: "Pages 15, 42, 87, 134, 210, 295",
                    sentiment_en: "Balanced, rational, and protective (the voice of sanity and caution).",
                    sentiment_kn: "ಸ್ಥಿರ, ವಿವೇಚನಾಶೀಲ ಮತ್ತು ರಕ್ಷಣಾತ್ಮಕ (ಬುದ್ಧಿವಂತಿಕೆ ಮತ್ತು ಎಚ್ಚರಿಕೆಯ ಧ್ವನಿ).",
                    query_en: "What is Ravi's role in guiding Himavant through his struggles?",
                    query_kn: "ಹಿಮವಂತನ ಸಂಕಷ್ಟಗಳಲ್ಲಿ ರವಿಯ ಪಾತ್ರವೇನು?",
                    relations: [
                        { name_en: "Himavant", name_kn: "ಹಿಮವಂತ್", role_en: "Best friend, companion", role_kn: "ಆತ್ಮೀಯ ಗೆಳೆಯ, ಸಹಚರ" },
                        { name_en: "Prarthana", name_kn: "ಪ್ರಾರ್ಥನಾ", role_en: "Supporter, emotional bridge", role_kn: "ಸಹಾಯಕಿ, ಭಾವನಾತ್ಮಕ ಸೇತುವೆ" }
                    ]
                },
                rasool: {
                    name_en: "Rasool Jamadar",
                    name_kn: "ರಸೂಲ್ ಜಮಾದಾರ",
                    badge_en: "Companion / Protector",
                    badge_kn: "ನಿಷ್ಠಾವಂತ ರಕ್ಷಕ",
                    desc_en: "A rugged associate and protector, representing the fierce and loyal underground world elements in Ravi Belagere's classic narrative landscape.",
                    desc_kn: "ಹಿಮವಂತನಿಗೆ ನೆರಳಾಗಿ ನಿಲ್ಲುವ ಒರಟು ಸ್ವಭಾವದ ನಿಷ್ಠಾವಂತ ಸಾಥಿ. ಭೂಗತ ಜಗತ್ತಿನ ಕಥಾ ಹೆಣಿಗೆಯಲ್ಲಿ ಧೈರ್ಯ ಮತ್ತು ನಿಷ್ಠೆಯ ಸಂಕೇತ.",
                    pages: "Pages 34, 78, 112, 160, 255",
                    sentiment_en: "Fierce, unyielding loyalty (grounded, gritty protector).",
                    sentiment_kn: "ಉಗ್ರವಾದ ಮತ್ತು ಅಚಲವಾದ ನಿಷ್ಠೆ (ಭೂಗತ ಜಗತ್ತಿನ ರಕ್ಷಣಾತ್ಮಕ ಶಕ್ತಿ).",
                    query_en: "Explain Rasool Jamadar's loyalty and action in the story",
                    query_kn: "ಕಥೆಯಲ್ಲಿ ರಸೂಲ್ ಜಮಾದಾರನ ನಿಷ್ಠೆ ಮತ್ತು ಪಾತ್ರದ ಮಹತ್ವವೇನು?",
                    relations: [
                        { name_en: "Himavant", name_kn: "ಹಿಮವಂತ್", role_en: "Underworld boss, ally", role_kn: "ಭೂಗತ ಲೋಕದ ನಾಯಕ, ಮಿತ್ರ" }
                    ]
                },
                belagere: {
                    name_en: "Ravi Belagere",
                    name_kn: "ರವಿ ಬೆಳಗೆರೆ",
                    badge_en: "Author / Narrator",
                    badge_kn: "ಲೇಖಕ / ನಿರೂಪಕ",
                    desc_en: "The author and narrator who weaves himself directly into the story's atmosphere. He narrates with his signature intensity, suspense, and emotional attachment to his characters.",
                    desc_kn: "ಕಾದಂಬರಿಯ ಕರ್ತೃ ಮತ್ತು ಸೂತ್ರಧಾರ. ತಮ್ಮದೇ ಆದ ವಿಶಿಷ್ಟ ಪತ್ರಿಕೋದ್ಯಮ ಮತ್ತು ಸಾಹಿತ್ಯ ಶೈಲಿಯಲ್ಲಿ ಕಥೆಯನ್ನು ಕಟ್ಟಿಕೊಡುತ್ತಾ, ಓದುಗರನ್ನು ಸೆಳೆಯುವ ನಿರೂಪಕ.",
                    pages: "Narrates and comments throughout the entire novel",
                    sentiment_en: "Authoritative, poetic, and dramatic (expresses deep passion for characters).",
                    sentiment_kn: "ಅಧಿಕೃತ, ಕಾವ್ಯಾತ್ಮಕ ಮತ್ತು ನಾಟಕೀಯ (ಪಾತ್ರಗಳ ಮೇಲಿನ ಅಪಾರ ಪ್ರೀತಿ ಮತ್ತು ನಿರೂಪಣೆಯ ಶಕ್ತಿ).",
                    query_en: "How does Ravi Belagere narrate Heli Hogu Kaarana and inject himself into the narrative?",
                    query_kn: "ರವಿ ಬೆಳಗೆರೆಯವರು 'ಹೇಳಿ ಹೋಗು ಕಾರಣ'ದಲ್ಲಿ ತಮ್ಮ ನಿರೂಪಣಾ ಶೈಲಿಯನ್ನು ಹೇಗೆ ಬಳಸಿದ್ದಾರೆ?",
                    relations: [
                        { name_en: "Himavant", name_kn: "ಹಿಮವಂತ್", role_en: "His primary creation", role_kn: "ಅವನ ಕಥಾ ನಾಯಕ" },
                        { name_en: "Prarthana", name_kn: "ಪ್ರಾರ್ಥನಾ", role_en: "His lead heroine", role_kn: "ಅವನ ಕಥಾ ನಾಯಕಿ" }
                    ]
                }
            };"""

# 9. renderCharCard replacement
render_char_card_old = """            function renderCharCard() {
                if (!activeCharId) return;
                const char = CHAR_DATA[activeCharId];
                
                if (activeCharLang === 'en') {
                    document.getElementById('char-name').innerHTML = `${char.name_en} <span class="badge">${char.badge_en}</span>`;
                    document.getElementById('char-desc').innerText = char.desc_en;
                    document.getElementById('char-pages').innerText = char.pages;
                } else {
                    document.getElementById('char-name').innerHTML = `${char.name_kn} <span class="badge">${char.badge_kn}</span>`;
                    document.getElementById('char-desc').innerText = char.desc_kn;
                    document.getElementById('char-pages').innerText = char.pages;
                }
            }"""

render_char_card_new = """            function renderCharCard() {
                if (!activeCharId) return;
                const char = CHAR_DATA[activeCharId];
                
                const sentimentEl = document.getElementById('char-sentiment');
                const relationsEl = document.getElementById('char-relations');
                const askBtn = document.getElementById('char-ask-btn');
                
                if (activeCharLang === 'en') {
                    document.getElementById('char-name').innerHTML = `${char.name_en} <span class="badge">${char.badge_en}</span>`;
                    document.getElementById('char-desc').innerText = char.desc_en;
                    document.getElementById('char-pages').innerText = char.pages;
                    if (sentimentEl) sentimentEl.innerText = char.sentiment_en;
                    
                    if (relationsEl) {
                        relationsEl.innerHTML = '';
                        char.relations.forEach(rel => {
                            const row = document.createElement('div');
                            row.style.fontSize = '0.82rem';
                            row.style.color = 'var(--text-muted)';
                            row.style.display = 'flex';
                            row.style.gap = '6px';
                            row.innerHTML = `<span style="font-weight: 700; color: var(--text);">${rel.name_en}</span> <span style="opacity: 0.85;">— ${rel.role_en}</span>`;
                            relationsEl.appendChild(row);
                        });
                    }
                    if (askBtn) askBtn.innerText = `💬 Ask AI about ${char.name_en}`;
                } else {
                    document.getElementById('char-name').innerHTML = `${char.name_kn} <span class="badge">${char.badge_kn}</span>`;
                    document.getElementById('char-desc').innerText = char.desc_kn;
                    document.getElementById('char-pages').innerText = char.pages;
                    if (sentimentEl) sentimentEl.innerText = char.sentiment_kn;
                    
                    if (relationsEl) {
                        relationsEl.innerHTML = '';
                        char.relations.forEach(rel => {
                            const row = document.createElement('div');
                            row.style.fontSize = '0.82rem';
                            row.style.color = 'var(--text-muted)';
                            row.style.display = 'flex';
                            row.style.gap = '6px';
                            row.innerHTML = `<span style="font-weight: 700; color: var(--text);">${rel.name_kn}</span> <span style="opacity: 0.85;">— ${rel.role_kn}</span>`;
                            relationsEl.appendChild(row);
                        });
                    }
                    if (askBtn) askBtn.innerText = `💬 ${char.name_kn} ಬಗ್ಗೆ ಎಐ ಸಹಾಯ ಕೇಳಿ`;
                }
            }

            function askAboutActiveChar() {
                if (!activeCharId) return;
                const char = CHAR_DATA[activeCharId];
                const query = activeCharLang === 'en' ? char.query_en : char.query_kn;
                switchTab('chat');
                document.getElementById('q').value = query;
                ask();
            }"""

# 10. initAudio speed control setup
init_audio_old = """            // Initialize Custom Audio Listeners
            function initAudio(base64Audio) {
                if (currentAudio) {
                    currentAudio.pause();
                }
                currentAudio = new Audio("data:audio/mp3;base64," + base64Audio);
                
                const slider = document.getElementById('audio-slider');"""

init_audio_new = """            let currentSpeed = 1.0;
            function changePlaybackSpeed() {
                const speeds = [0.75, 1.0, 1.25, 1.5, 2.0];
                let idx = speeds.indexOf(currentSpeed);
                idx = (idx + 1) % speeds.length;
                currentSpeed = speeds[idx];
                
                const btn = document.getElementById('audio-speed-btn');
                if (btn) btn.innerText = currentSpeed + 'x';
                if (currentAudio) {
                    currentAudio.playbackRate = currentSpeed;
                }
            }

            // Initialize Custom Audio Listeners
            function initAudio(base64Audio) {
                if (currentAudio) {
                    currentAudio.pause();
                }
                currentAudio = new Audio("data:audio/mp3;base64," + base64Audio);
                currentAudio.playbackRate = currentSpeed;
                
                const slider = document.getElementById('audio-slider');"""

# 11. ask() JS fetch payload replacement
ask_fetch_old = """                try {
                    const r = await fetch('/chat', { 
                        method: 'POST', 
                        headers: {'Content-Type': 'application/json'}, 
                        body: JSON.stringify({question: q, language: lang, history: chatHistory})
                    });
                    const d = await r.json();
                    
                    // Increment and update local usage count
                    incrementUsage();
                    
                    currentText = d.answer;
                    res.innerHTML = formatMarkdown(d.answer);"""

ask_fetch_new = """                try {
                    const threshold = document.getElementById('rag-threshold').value;
                    const topK = document.getElementById('rag-top-k').value;
                    const model = document.getElementById('rag-model').value;
                    const r = await fetch('/chat', { 
                        method: 'POST', 
                        headers: {'Content-Type': 'application/json'}, 
                        body: JSON.stringify({
                            question: q, 
                            language: lang, 
                            history: chatHistory,
                            threshold: parseFloat(threshold),
                            top_k: parseInt(topK),
                            model: model
                        })
                    });
                    const d = await r.json();
                    
                    // Increment and update local usage count
                    incrementUsage();
                    
                    currentText = d.answer;
                    res.innerHTML = formatMarkdown(d.answer);

                    // Render sources
                    const sourcesContainer = document.getElementById('sources-container');
                    const sourcesList = document.getElementById('sources-list');
                    if (d.sources && d.sources.length > 0) {
                        sourcesList.innerHTML = '';
                        d.sources.forEach(src => {
                            const pill = document.createElement('span');
                            pill.style.background = 'var(--primary-light)';
                            pill.style.color = 'var(--primary)';
                            pill.style.fontSize = '0.78rem';
                            pill.style.fontWeight = '700';
                            pill.style.padding = '4px 10px';
                            pill.style.borderRadius = '20px';
                            pill.style.display = 'inline-block';
                            pill.innerText = src;
                            sourcesList.appendChild(pill);
                        });
                        sourcesContainer.style.display = 'block';
                    } else {
                        sourcesContainer.style.display = 'none';
                    }"""

# 12. toggleRagSettings placement
toggle_settings_old = """            function setQ(txt) {
                chatHistory = []; // Reset history to start a fresh thread
                document.getElementById('q').value = txt;
                ask();
            }"""

toggle_settings_new = """            function setQ(txt) {
                chatHistory = []; // Reset history to start a fresh thread
                document.getElementById('q').value = txt;
                ask();
            }

            function toggleRagSettings() {
                const panel = document.getElementById('rag-settings-panel');
                const icon = document.getElementById('rag-toggle-icon');
                if (panel.style.display === 'none') {
                    panel.style.display = 'grid';
                    icon.innerText = '🔼';
                } else {
                    panel.style.display = 'none';
                    icon.innerText = '⚙️';
                }
            }"""


# Run replacements
replacements = [
    (request_old, request_new, "ChatRequest Schema"),
    (gtts_old, gtts_new, "gTTS parallel & markdown cleaner"),
    (sarvam_old, sarvam_new, "Sarvam cleaning delegate"),
    (chat_old, chat_new, "/chat endpoint RAG logic"),
    (sources_old, sources_new, "HTML sources container"),
    (speed_old, speed_new, "HTML playback speed btn"),
    (char_card_old, char_card_new, "HTML character detail card cards"),
    (char_data_old, char_data_new, "CHAR_DATA JS data object"),
    (render_char_card_old, render_char_card_new, "renderCharCard() JS function"),
    (init_audio_old, init_audio_new, "initAudio speed control"),
    (ask_fetch_old, ask_fetch_new, "ask() JS fetch payload & sources rendering"),
    (toggle_settings_old, toggle_settings_new, "toggleRagSettings() JS placement")
]

success = True
for old, new, label in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"[OK] Replaced: {label}")
    else:
        print(f"[FAILED] Target not found: {label}")
        success = False

if success:
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("[SUCCESS] All replacements completed successfully!")
else:
    print("[ERROR] Some target replacements were missing. File not written.")
