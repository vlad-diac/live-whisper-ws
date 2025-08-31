#!/usr/bin/env python3
"""
Railway startup script for Whisper WebSocket Server
"""
import os
import uvicorn
from server import app

def main():
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting Whisper WebSocket Server on {host}:{port}")
    print(f"Model: {os.environ.get('MODEL_NAME', 'small.en')}")
    print(f"Language: {os.environ.get('WHISPER_LANG', 'en')}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
