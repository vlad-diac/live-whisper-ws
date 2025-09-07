# Railway Deployment Checklist

## Pre-Deployment Checklist ✅

- [x] **railway.json** configured with start command, health check and deployment settings
- [x] **requirements.txt** updated with PostgreSQL dependencies
- [x] **database.py** created with SQLAlchemy models and Railway integration
- [x] **server.py** updated with database integration and improved CORS
- [x] **.env.example** created with all required environment variables
- [x] **RAILWAY_DEPLOYMENT.md** comprehensive guide created

## Railway Setup Checklist

### 1. Railway Project Setup
- [ ] Create new Railway project
- [ ] Connect GitHub repository
- [ ] Add PostgreSQL database service

### 2. Environment Variables
- [ ] Set `SECRET_KEY` (generate a secure key)
- [ ] Set `WHISPER_LANG=en`
- [ ] Set `MODEL_NAME=small.en`
- [ ] Set `COMPUTE_TYPE=int8`
- [ ] Set `RAILWAY_ENVIRONMENT=production`
- [ ] Set `FRONTEND_URL` (if deploying frontend separately)

### 3. Deployment Verification
- [ ] Check deployment logs for errors
- [ ] Verify `/health` endpoint returns "healthy" status
- [ ] Confirm database connection shows "connected"
- [ ] Test WebSocket endpoints with valid JWT token

### 4. Frontend Integration (if separate)
- [ ] Deploy React frontend to Vercel/Netlify
- [ ] Update WebSocket URLs to point to Railway domain
- [ ] Update CORS settings with frontend domain
- [ ] Test end-to-end functionality

## Production Optimizations

### Security
- [ ] Generate strong SECRET_KEY (32+ characters)
- [ ] Restrict CORS origins to frontend domain only
- [ ] Implement rate limiting if needed
- [ ] Use HTTPS for all connections

### Performance
- [ ] Monitor Railway metrics dashboard
- [ ] Consider upgrading memory for larger Whisper models
- [ ] Implement connection pooling if high traffic
- [ ] Set up monitoring/alerting

### Maintenance
- [ ] Set up database backups
- [ ] Monitor application logs
- [ ] Plan for scaling based on usage
- [ ] Document API endpoints for frontend team

## Quick Commands

### Generate SECRET_KEY
```python
import secrets
print(secrets.token_urlsafe(32))
```

### Test Health Endpoint
```bash
curl https://your-app.railway.app/health
```

### Test WebSocket (with valid token)
```javascript
const ws = new WebSocket('wss://your-app.railway.app/ws-pcm16?token=YOUR_JWT_TOKEN');
```

## Troubleshooting

### Common Issues
- **Database connection failed**: Check DATABASE_URL format and PostgreSQL service status
- **Model loading timeout**: Increase memory allocation or use smaller model
- **WebSocket authentication failed**: Verify JWT token is valid and SECRET_KEY matches
- **CORS errors**: Update FRONTEND_URL environment variable

### Useful Railway Commands
```bash
# Login to Railway CLI
railway login

# Link to project
railway link

# View logs
railway logs

# Open project in browser
railway open
```
