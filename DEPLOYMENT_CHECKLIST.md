# Railway Deployment Checklist

Use this checklist to ensure a successful deployment to Railway.

## Pre-Deployment

- [ ] Repository is pushed to GitHub/GitLab
- [ ] All files are committed:
  - [ ] `Dockerfile`
  - [ ] `railway.json`
  - [ ] `.dockerignore`
  - [ ] `requirements.txt`
  - [ ] Updated `server.py`
  - [ ] `start.py`
  - [ ] `.env.example`

## Railway Setup

- [ ] Railway account created
- [ ] New project created in Railway
- [ ] Repository connected to Railway project

## Environment Variables

Set these in Railway Dashboard > Project > Variables:

- [ ] `SECRET_KEY` - Generate a secure random string (required)
- [ ] `MODEL_NAME` - Choose Whisper model (optional, default: "small.en")
- [ ] `WHISPER_LANG` - Target language (optional, default: "en")
- [ ] `COMPUTE_TYPE` - Computation type (optional, default: "int8")

## Post-Deployment

- [ ] Build completes successfully
- [ ] Health check passes at `/health`
- [ ] Frontend loads at root URL
- [ ] WebSocket endpoints are accessible
- [ ] Test authentication with JWT token

## Frontend Configuration

- [ ] Update frontend WebSocket URLs to point to Railway deployment
- [ ] Test WebSocket connections from frontend
- [ ] Verify JWT token generation and validation

## Testing

- [ ] Health endpoint: `GET https://your-app.railway.app/health`
- [ ] Frontend: `GET https://your-app.railway.app/`
- [ ] WebSocket: `wss://your-app.railway.app/ws-pcm16?token=YOUR_TOKEN`
- [ ] File upload: `POST https://your-app.railway.app/transcribe`

## Troubleshooting

If deployment fails:

1. Check Railway build logs
2. Verify all dependencies in `requirements.txt`
3. Ensure Docker build completes locally
4. Check environment variables are set correctly
5. Monitor memory usage (upgrade plan if needed)

## Performance Optimization

- [ ] Choose appropriate Whisper model for your Railway plan
- [ ] Monitor memory and CPU usage
- [ ] Consider upgrading Railway plan for better performance
- [ ] Test with expected load

## Security

- [ ] Use strong `SECRET_KEY`
- [ ] Consider restricting CORS origins in production
- [ ] Implement proper JWT token validation in frontend
- [ ] Monitor usage and implement rate limiting if needed
