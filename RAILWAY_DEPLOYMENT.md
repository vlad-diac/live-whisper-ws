# Railway Deployment Guide

This guide explains how to deploy the Whisper WebSocket Server to Railway.

## Prerequisites

- Railway account ([railway.app](https://railway.app))
- Railway CLI installed (optional but recommended)

## Deployment Steps

### 1. Connect Repository to Railway

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub repository containing this code

### 2. Environment Variables

Set the following environment variables in Railway:

**Required:**
- `SECRET_KEY`: JWT secret for authentication (generate a secure random string)

**Optional (with defaults):**
- `MODEL_NAME`: Whisper model to use (default: "small.en")
  - Options: "tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v1", "large-v2", "large-v3"
- `WHISPER_LANG`: Target language for transcription (default: "en")
- `COMPUTE_TYPE`: Computation type (default: "int8")
  - Options: "int8", "int16", "float16", "float32"
- `CHUNK_WINDOW_SEC`: Rolling window size in seconds (default: "10.0")
- `CHUNK_OVERLAP_SEC`: Overlap between chunks in seconds (default: "2.0")
- `SAMPLE_RATE`: Audio sample rate (default: "16000")

### 3. Build Configuration

The project uses a multi-stage Docker build that:
1. Installs system dependencies (ffmpeg, Node.js)
2. Builds the React frontend
3. Sets up the Python backend
4. Serves both frontend and backend from a single container

Railway will automatically detect the `Dockerfile` and `railway.json` configuration.

### 4. Health Check

The deployment includes a health check endpoint at `/health` that Railway can use to verify the service is running.

## API Endpoints

Once deployed, your Railway app will expose:

- `GET /`: Serves the React frontend UI
- `GET /health`: Health check endpoint
- `GET /static/*`: Static assets for the frontend
- `WebSocket /ws`: Original WebSocket endpoint for audio streaming
- `WebSocket /ws-pcm16`: PCM16 audio WebSocket endpoint
- `POST /transcribe`: HTTP file upload for transcription

## Authentication

The WebSocket endpoints require a JWT token passed as a query parameter:
```
wss://your-app.railway.app/ws?token=YOUR_JWT_TOKEN
```

Generate a JWT token using the `SECRET_KEY` you set in environment variables.

## Frontend Configuration

The React frontend will need to be configured to connect to your Railway deployment URL. Update the WebSocket connection URLs in your frontend code to point to:
```
wss://your-railway-app.railway.app/ws-pcm16?token=YOUR_TOKEN
```

## Resource Requirements

- **Memory**: At least 2GB RAM recommended for the Whisper models
- **CPU**: Multi-core recommended for better transcription performance
- **Storage**: Minimal storage requirements as models are downloaded at startup

## Model Performance

Different Whisper models have different resource requirements:
- `tiny`: Fastest, least accurate, ~1GB RAM
- `base`: Good balance, ~1.5GB RAM
- `small`: Recommended default, ~2GB RAM
- `medium`: Better accuracy, ~4GB RAM
- `large`: Best accuracy, ~8GB RAM

Choose based on your Railway plan limits and accuracy requirements.

## Troubleshooting

1. **Build fails**: Check that all dependencies in `requirements.txt` are compatible
2. **Model loading slow**: This is normal on first startup as the model downloads
3. **Memory errors**: Try a smaller model (e.g., "tiny.en" or "base.en")
4. **WebSocket connection fails**: Verify the JWT token and SECRET_KEY configuration

## Local Testing

To test locally before deployment:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SECRET_KEY="your-secret-key"
export MODEL_NAME="small.en"

# Run the server
python server.py
```

The server will be available at `http://localhost:8000`.
