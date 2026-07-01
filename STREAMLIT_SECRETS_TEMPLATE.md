# Streamlit Secrets Configuration Template

This template defines the secrets configuration required to run the application on Streamlit Community Cloud. 

Copy the TOML contents below and paste them into the **Secrets** section under **Advanced settings** in your Streamlit dashboard.

```toml
# Required: Google Gemini API Key
GEMINI_API_KEY = "your_gemini_api_key_here"

# Required: Groq API Key (Fallback and ReAct Agent)
GROQ_API_KEY = "your_groq_api_key_here"

# Optional: Sarvam AI API Key (Bilingual generation and High-fidelity TTS)
SARVAM_API_KEY = "your_sarvam_api_key_here"

# Optional: E-Book and Administration Passwords
EBOOK_PASSWORD = "readkarana"
ADMIN_PASSWORD = "admin123"
```
