# Deploy Kannada RAG Agent on Vercel

This guide explains how to deploy the Kannada Book AI Agent on Vercel using FastAPI instead of Streamlit.

## Overview

The original Streamlit app has been converted to a FastAPI application that runs on Vercel's serverless platform. This provides better performance and scalability for production deployment.

## Key Changes

### 1. Architecture
- **Original**: Streamlit app (`app.py`)
- **Vercel**: FastAPI serverless function (`api/index.py`)

### 2. Dependencies
- Removed heavy dependencies not suitable for serverless:
  - `streamlit` → `fastapi` + `uvicorn`
  - `pdf2image`, `opencv-python`, `surya-ocr` (commented out)
  - `langchain` packages (not needed for simplified version)

### 3. Features
- ✅ Core RAG functionality preserved
- ✅ Sarvam AI integration for LLM and TTS
- ✅ Multi-language support (English/Kannada)
- ✅ Web-based UI with modern styling
- ✅ Source chunk display
- ✅ Audio generation for answers

## Deployment Steps

### Prerequisites
1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **GitHub Repository**: Push your code to GitHub
3. **Environment Variables**: Set up required API keys

### Step 1: Prepare Environment Variables
In your Vercel dashboard, set these environment variables:

```
SARVAM_API_KEY=your_sarvam_api_key_here
ADMIN_PASSWORD=your_admin_password_here
```

### Step 2: Deploy to Vercel

#### Option A: Via Vercel CLI
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy from project root
cd kannada-rag-agent
vercel --prod
```

#### Option B: Via GitHub Integration
1. Connect your GitHub repository to Vercel
2. Import the project
3. Configure environment variables
4. Deploy

### Step 3: Verify Deployment
- Visit your Vercel URL
- Test the chat functionality
- Verify TTS audio works
- Check source chunk display

## File Structure for Vercel

```
kannada-rag-agent/
├── api/
│   └── index.py          # FastAPI serverless function
├── chroma_db/            # Vector database (must be included)
├── package.json          # Node.js configuration for Vercel
├── vercel.json          # Vercel deployment configuration
├── requirements.txt     # Python dependencies (serverless-optimized)
├── .env                 # Environment variables (local only)
└── README-VERCEL.md     # This file
```

## Configuration Files

### vercel.json
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ],
  "functions": {
    "api/index.py": {
      "runtime": "python3.9"
    }
  }
}
```

### package.json
```json
{
  "name": "kannada-rag-agent",
  "version": "1.0.0",
  "scripts": {
    "dev": "vercel dev",
    "build": "echo 'No build step required'"
  }
}
```

## API Endpoints

### Main Chat Endpoint
- **POST** `/chat`
- **Body**: 
  ```json
  {
    "question": "Who is Himavant?",
    "language": "English",
    "show_chunks": false,
    "enable_tts": false
  }
  ```

### Audio Endpoint
- **GET** `/audio/{question}` - Returns WAV audio for TTS

### Health Check
- **GET** `/health` - Returns health status

## Local Development

### Using Vercel CLI
```bash
# Install dependencies
pip install -r requirements.txt

# Start local development server
vercel dev
```

### Using Python Directly
```bash
# Install additional dependencies
pip install uvicorn

# Run FastAPI server locally
python -m uvicorn api.index:app --reload --host 0.0.0.0 --port 8000
```

## Limitations & Considerations

### Serverless Constraints
1. **Cold Starts**: First request may be slower
2. **Memory Limits**: Vercel functions have memory constraints
3. **Execution Time**: Limited to 10-60 seconds depending on plan
4. **File Storage**: No persistent file system

### Optimizations Made
1. **Reduced Dependencies**: Removed heavy packages
2. **Caching**: Models are cached in memory
3. **Async Processing**: FastAPI for better performance
4. **Minimal UI**: Lightweight HTML/CSS/JS

### Database Considerations
- The `chroma_db` directory is included in deployment
- For production, consider using external vector database
- Current setup works for small to medium datasets

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check `requirements.txt` for incompatible packages
   - Verify Python version compatibility (3.9+)

2. **Runtime Errors**:
   - Check environment variables in Vercel dashboard
   - Verify `chroma_db` directory is included

3. **Performance Issues**:
   - Model loading time on cold starts
   - Consider using smaller models for faster startup

4. **Memory Issues**:
   - Monitor function memory usage
   - Optimize model loading and caching

### Debugging
```bash
# View deployment logs
vercel logs

# Local debugging
vercel dev --debug
```

## Migration from Streamlit

### What's Preserved
- ✅ All core RAG functionality
- ✅ Sarvam AI integration
- ✅ Multi-language support
- ✅ Audio TTS
- ✅ Source citation
- ✅ Modern UI design

### What's Different
- **UI**: Web-based instead of Streamlit components
- **Deployment**: Serverless instead of dedicated server
- **Performance**: Faster after initial load
- **Scalability**: Better for production use

## Next Steps

### Production Enhancements
1. **External Database**: Move ChromaDB to cloud storage
2. **Model Optimization**: Use smaller/faster models
3. **Caching**: Implement Redis for response caching
4. **Monitoring**: Add error tracking and analytics
5. **Authentication**: Add user management

### Advanced Features
1. **Batch Processing**: Handle multiple queries
2. **Document Upload**: Allow new book ingestion
3. **User Sessions**: Persistent conversation history
4. **Analytics**: Track usage patterns

## Support

For issues related to:
- **Vercel Deployment**: Check [Vercel Docs](https://vercel.com/docs)
- **FastAPI**: Check [FastAPI Documentation](https://fastapi.tiangolo.com/)
- **Original Project**: Refer to main README.md

---

**Note**: This deployment maintains all the core functionality of the original Streamlit app while providing better scalability and performance for production use.
