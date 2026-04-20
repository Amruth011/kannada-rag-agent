# api/app.py - Main entrypoint for Vercel
from .index import app

# Export the FastAPI app for Vercel
handler = app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
