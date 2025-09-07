# Railway Deployment Guide

This guide walks you through deploying your FastAPI Whisper WebSocket server on Railway with PostgreSQL database integration.

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Railway CLI** (optional): Install with `npm install -g @railway/cli`

## Step 1: Set Up Railway Project

### 1.1 Create New Project
1. Log into your Railway dashboard
2. Click "New Project"
3. Choose "Deploy from GitHub repo" 
4. Connect and select your repository

### 1.2 Add PostgreSQL Database
1. In your Railway project dashboard, click "Add Service"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create a PostgreSQL instance and provide the `DATABASE_URL` environment variable

## Step 2: Configure Environment Variables

In your Railway project settings, add these environment variables:

### Required Variables
```bash
SECRET_KEY=your-secure-secret-key-here
WHISPER_LANG=en
MODEL_NAME=small.en
COMPUTE_TYPE=int8
RAILWAY_ENVIRONMENT=production
```

### Optional Variables (with defaults)
```bash
CHUNK_WINDOW_SEC=10.0
CHUNK_OVERLAP_SEC=2.0
SAMPLE_RATE=16000
FRONTEND_URL=https://your-frontend-domain.com
```

### Automatic Variables (provided by Railway)
- `DATABASE_URL`: Automatically set by PostgreSQL service
- `PORT`: Automatically set by Railway
- `RAILWAY_ENVIRONMENT`: Set automatically

## Step 3: Deploy Your Application

### 3.1 Automatic Deployment
1. Railway will automatically detect your `railway.json` and `requirements.txt`
2. The build process will install dependencies and start your server using the startCommand
3. Monitor the deployment logs in the Railway dashboard

### 3.2 Deployment Files Explained

**railway.json**: Railway-specific configuration with start command
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "hypercorn server:app --bind \"[::]:$PORT\"",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

## Step 4: Verify Deployment

### 4.1 Health Check
Visit your Railway-provided URL + `/health` to verify:
- Application is running
- Database connection is working
- Model is loaded

Expected response:
```json
{
  "status": "healthy",
  "model": "small.en",
  "database": "connected",
  "environment": "production"
}
```

### 4.2 WebSocket Endpoints
Your WebSocket endpoints will be available at:
- `wss://your-app.railway.app/ws` - For Opus/WebM audio
- `wss://your-app.railway.app/ws-pcm16` - For raw PCM16 audio

## Step 5: Frontend Integration

### 5.1 Separate Frontend Deployment
Since you moved your React app to a separate repository:

1. **Deploy Frontend**: Use Vercel, Netlify, or another platform
2. **Update CORS**: Set `FRONTEND_URL` environment variable in Railway
3. **WebSocket Connection**: Update your React app to connect to Railway's WebSocket URL

### 5.2 Frontend Code Updates
Update your React app's WebSocket connection:

```typescript
// Replace localhost with your Railway domain
const wsUrl = 'wss://your-app.railway.app/ws-pcm16?token=' + yourToken;
const websocket = new WebSocket(wsUrl);
```

## Step 6: Database Operations

### 6.1 View Database Data
Use Railway's database management interface or connect with a PostgreSQL client:
- Host: Provided in `DATABASE_URL`
- Use the connection string from Railway environment variables

### 6.2 Database Schema
The application automatically creates these tables:
- `transcription_sessions`: User session tracking
- `transcription_results`: Transcription history with timestamps

## Step 7: Monitoring and Troubleshooting

### 7.1 Logs
- View application logs in Railway dashboard
- Monitor for startup errors, database connection issues

### 7.2 Common Issues

**Database Connection Errors**:
- Verify `DATABASE_URL` is set correctly
- Check PostgreSQL service is running

**Model Loading Issues**:
- Monitor memory usage (Whisper models require significant RAM)
- Consider using smaller models like `tiny.en` for lower memory usage

**WebSocket Connection Issues**:
- Verify JWT token is valid
- Check CORS settings match your frontend domain

## Step 8: Production Optimizations

### 8.1 Security
- Use strong `SECRET_KEY`
- Restrict CORS origins to your frontend domain
- Implement rate limiting if needed

### 8.2 Performance
- Monitor Railway metrics
- Consider upgrading to higher memory plans for larger models
- Use CDN for frontend assets

### 8.3 Scaling
- Railway automatically handles scaling
- Monitor usage and upgrade plan as needed
- Consider implementing connection pooling for database

## Environment Variables Summary

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | Auto | PostgreSQL connection string |
| `SECRET_KEY` | ✅ | - | JWT secret key |
| `PORT` | ✅ | Auto | Server port (set by Railway) |
| `WHISPER_LANG` | ❌ | en | Whisper language code |
| `MODEL_NAME` | ❌ | small.en | Whisper model size |
| `COMPUTE_TYPE` | ❌ | int8 | Computation precision |
| `FRONTEND_URL` | ❌ | * | Frontend domain for CORS |
| `RAILWAY_ENVIRONMENT` | ❌ | Auto | Environment identifier |

## Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **FastAPI Docs**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **Whisper Docs**: [github.com/openai/whisper](https://github.com/openai/whisper)
