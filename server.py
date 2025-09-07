import asyncio, io, time, collections, os, uuid
import av, numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from jose import jwt, JWTError
from faster_whisper import WhisperModel
from sqlalchemy.orm import Session
from database import get_db, create_tables, TranscriptionSession, TranscriptionResult

# ---- Config ----
SECRET = os.getenv("SECRET_KEY", "1ZCsvqyHdDd7mK8wr5pkTmLYvvB5DtKm")
ALGO = "HS256"
LANG = os.getenv("WHISPER_LANG", "en")
MODEL_NAME = os.getenv("MODEL_NAME", "small.en")       # try base.en for even lower latency
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "int8")         # int8 for CPU
CHUNK_WINDOW_SEC = float(os.getenv("CHUNK_WINDOW_SEC", "10.0"))       # longer rolling window for better context
CHUNK_OVERLAP_SEC = float(os.getenv("CHUNK_OVERLAP_SEC", "2.0"))       # longer overlap to reduce word cuts
SAMPLE_RATE = int(os.getenv("SAMPLE_RATE", "16000"))           # we'll decode to mono 16k
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

app = FastAPI(title="Whisper WebSocket Server", version="1.0.0")

# Update CORS for production
FRONTEND_URL = os.getenv("FRONTEND_URL", "*")
if FRONTEND_URL == "*":
    allowed_origins = ["*"]
else:
    allowed_origins = [FRONTEND_URL, "https://*.railway.app", "http://localhost:3000", "http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables
@app.on_event("startup")
async def startup_event():
    create_tables()
    print("Database tables created/verified")

# Mount static files for the frontend
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the frontend at root
@app.get("/")
async def read_root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    else:
        return {"message": "Whisper WebSocket Server", "endpoints": {"/ws": "WebSocket for streaming transcription", "/ws-pcm16": "WebSocket for PCM16 audio", "/transcribe": "HTTP file upload"}}

# Health check endpoint for Railway
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy", 
        "model": MODEL_NAME, 
        "database": db_status,
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "local")
    }

print("Loading model...")
model = WhisperModel(MODEL_NAME, device="cpu", compute_type=COMPUTE_TYPE)
print("Model ready.")

def verify(token: str):
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def opus_webm_to_pcm16_mono16k(raw_bytes: bytes) -> bytes:
    try:
        # Skip very small chunks that are likely incomplete
        if len(raw_bytes) < 100:
            return b''
        
        bio = io.BytesIO(raw_bytes)
        with av.open(bio, 'r') as container:
            if not container.streams.audio:
                return b''
            
            stream = container.streams.audio[0]
            resampler = av.audio.resampler.AudioResampler(format='s16', layout='mono', rate=16000)
            pcm_chunks = []
            
            for frame in container.decode(stream):
                resampled_frames = resampler.resample(frame)
                for resampled_frame in resampled_frames:
                    for plane in resampled_frame.planes:
                        pcm_chunks.append(plane.to_bytes())
            
            return b''.join(pcm_chunks)
    except Exception as e:
        # Log the error but don't crash - return empty bytes
        print(f"Audio decode error (chunk size: {len(raw_bytes)}): {e}")
        return b''

# Simple in-memory audio ring buffer per connection
class RingBuffer:
    def __init__(self, max_seconds: float, sr: int):
        self.max_samples = int(max_seconds * sr)
        self.buf = collections.deque(maxlen=self.max_samples)

    def extend_pcm16(self, pcm: bytes):
        # Expect 16-bit mono little-endian PCM at SAMPLE_RATE
        import array
        arr = array.array('h')
        arr.frombytes(pcm)
        self.buf.extend(arr)

    def get_window(self, window_sec: float, overlap_sec: float):
        n = len(self.buf)
        if n == 0:
            return None
        win = int(window_sec * SAMPLE_RATE)
        if n < win:
            win = n
        start = max(0, n - win)
        import array
        out = array.array('h', list(self.buf)[start:])
        # Optionally drop the overlap on the text side client-side
        return out.tobytes()

async def transcribe_window(pcm16_bytes: bytes):
    # Convert raw PCM16 bytes directly to numpy array for faster-whisper
    try:
        import array
        
        duration_sec = len(pcm16_bytes) / (SAMPLE_RATE * 2)
        print(f"[TRANSCRIBE] Processing {len(pcm16_bytes)} bytes of PCM data ({duration_sec:.2f}s) directly")
        
        # Convert PCM16 bytes to numpy array of float32 values
        # PCM16 is signed 16-bit integers, we need to convert to float32 [-1.0, 1.0]
        pcm_array = array.array('h')  # signed short (Int16)
        pcm_array.frombytes(pcm16_bytes)
        
        # Convert to numpy array and normalize to [-1.0, 1.0]
        audio_np = np.array(pcm_array, dtype=np.float32) / 32768.0
        
        print(f"[TRANSCRIBE] Converted to numpy array: shape={audio_np.shape}, dtype={audio_np.dtype}, range=[{audio_np.min():.3f}, {audio_np.max():.3f}]")
        
        # Now transcribe directly with the numpy array - much faster!
        print(f"[TRANSCRIBE] Starting Whisper transcription directly from numpy array...")
        segments, info = model.transcribe(
            audio_np,  # Pass numpy array directly instead of file path
            language=LANG,
            task="transcribe",
            beam_size=1,  # Fastest beam size
            vad_filter=True,  # Enable VAD to filter silence
            word_timestamps=False,
            initial_prompt=None,
            no_speech_threshold=0.6,  # Higher threshold to reduce false positives
            condition_on_previous_text=False  # Don't condition on previous text for streaming
        )
        
        print(f"[TRANSCRIBE] Whisper completed, detected language: {info.language}, probability: {info.language_probability:.2f}")
        segment_texts = []
        for i, segment in enumerate(segments):
            # Filter out very short segments that might be noise
            if len(segment.text.strip()) > 1:
                print(f"[TRANSCRIBE] Segment {i}: '{segment.text}' (start: {segment.start:.2f}s, end: {segment.end:.2f}s)")
                segment_texts.append(segment.text)
        
        text = " ".join(segment_texts)  # Use space to join segments
        print(f"[TRANSCRIBE] Final combined text: '{text}' (length: {len(text)})")
            
        return text.strip()
        
    except Exception as e:
        print(f"[TRANSCRIBE] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return ""

# PCM Ring Buffer for raw audio frames
class PCMRingBuffer:
    def __init__(self, max_seconds: float, sr: int):
        self.max_samples = int(max_seconds * sr)
        self.buf = collections.deque(maxlen=self.max_samples)
        self.sample_rate = sr
        self.total_samples_received = 0
        self.last_transcribed_position = 0

    def extend_pcm16_frame(self, frame_bytes: bytes):
        # Expect raw Int16 little-endian PCM at 16kHz
        import array
        arr = array.array('h')  # signed short (Int16)
        arr.frombytes(frame_bytes)
        self.buf.extend(arr)
        self.total_samples_received += len(arr)

    def get_window_bytes(self, window_sec: float):
        n = len(self.buf)
        if n == 0:
            return None
        win_samples = int(window_sec * self.sample_rate)
        if n < win_samples:
            win_samples = n
        start = max(0, n - win_samples)
        import array
        out = array.array('h', list(self.buf)[start:])
        return out.tobytes()
    
    def get_new_audio_bytes(self, window_sec: float):
        """Get only new audio since last transcription"""
        n = len(self.buf)
        if n == 0:
            return None
        
        # Calculate how many new samples we have
        new_samples = self.total_samples_received - self.last_transcribed_position
        if new_samples <= 0:
            return None
            
        # Get a window that includes some overlap but focuses on new audio
        win_samples = int(window_sec * self.sample_rate)
        overlap_samples = int(2.0 * self.sample_rate)  # 2 second overlap for better context
        
        if n < win_samples:
            # Not enough audio yet, return everything
            start = 0
            win_samples = n
        else:
            # Get window with overlap
            start = max(0, n - win_samples)
        
        import array
        out = array.array('h', list(self.buf)[start:])
        
        # Update position to mark what we've transcribed
        self.last_transcribed_position = self.total_samples_received - overlap_samples
        
        return out.tobytes()

@app.websocket("/ws")
async def ws_transcribe(ws: WebSocket, db: Session = Depends(get_db)):
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4401)
        return
    verify(token)

    await ws.accept()
    
    # Create session in database
    session_id = str(uuid.uuid4())
    session = TranscriptionSession(session_id=session_id, user_token=token)
    db.add(session)
    db.commit()
    print(f"Created transcription session: {session_id}")
    
    ring = RingBuffer(CHUNK_WINDOW_SEC + CHUNK_OVERLAP_SEC, SAMPLE_RATE)

    # A simple loop: receive PCM16 chunks, periodically transcribe the window and send partial text
    last_emit = 0.0
    try:
        while True:
            msg = await ws.receive()
            if "bytes" in msg:
                pcm = opus_webm_to_pcm16_mono16k(msg["bytes"])
                if pcm:  # Only add to buffer if we got valid PCM data
                    ring.extend_pcm16(pcm)
            elif "text" in msg:
                # allow "flush" or "close" messages
                if msg["text"] == "flush":
                    pass
                elif msg["text"] == "bye":
                    break

            now = time.time()
            # Emit every ~1s if we have enough audio
            if now - last_emit > 1.0:
                window = ring.get_window(CHUNK_WINDOW_SEC, CHUNK_OVERLAP_SEC)
                if window and len(window) > 0:
                    text = await transcribe_window(window)
                    if text.strip():
                        # Log transcription result to database
                        result = TranscriptionResult(
                            session_id=session_id,
                            text=text,
                            audio_duration=len(window) // (SAMPLE_RATE * 2) * 1000  # milliseconds
                        )
                        db.add(result)
                        db.commit()
                        await ws.send_text(text)
                last_emit = now
    except WebSocketDisconnect:
        pass

@app.websocket("/ws-pcm16")
async def ws_pcm16(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    verify(token)

    await websocket.accept()
    print("PCM16 WebSocket connection established")
    
    # Use PCM ring buffer for raw frames
    pcm_ring = PCMRingBuffer(CHUNK_WINDOW_SEC + CHUNK_OVERLAP_SEC, SAMPLE_RATE)
    
    last_emit = 0.0
    chunk_count = 0
    transcription_count = 0
    
    try:
        while True:
            # Receive data (could be bytes or text)
            try:
                message = await websocket.receive()
                print(f"[RAW MESSAGE] Received: {message}")
                
                if "bytes" in message:
                    frame_bytes = message["bytes"]
                    
                    # Check if this looks like a text message (small size, printable chars)
                    if len(frame_bytes) < 100:
                        try:
                            text_content = frame_bytes.decode('utf-8')
                            print(f"[TEXT AS BYTES] Received: '{text_content}' ({len(frame_bytes)} bytes)")
                            continue  # Skip processing as audio
                        except UnicodeDecodeError:
                            pass  # Not text, process as audio
                    
                    chunk_count += 1
                    print(f"[CHUNK #{chunk_count}] Received {len(frame_bytes)} bytes of PCM data")
                    
                    # Add frame to ring buffer
                    try:
                        pcm_ring.extend_pcm16_frame(frame_bytes)
                        print(f"[BUFFER] Total samples in buffer: {len(pcm_ring.buf)}, total received: {pcm_ring.total_samples_received}")
                    except Exception as buffer_error:
                        print(f"[BUFFER ERROR] Failed to add frame to buffer: {buffer_error}")
                        continue
                        
                elif "text" in message:
                    print(f"[TEXT MESSAGE] Received: {message['text']}")
                    continue
                else:
                    print(f"[UNKNOWN MESSAGE] Type: {type(message)}, Content: {message}")
                    continue
            except Exception as msg_error:
                print(f"[MESSAGE ERROR] {msg_error}")
                break
            
            now = time.time()
            # Emit transcription every ~2s for longer, more accurate chunks
            if now - last_emit > 2.0:
                try:
                    # Use new audio method for progressive transcription
                    window_bytes = pcm_ring.get_new_audio_bytes(CHUNK_WINDOW_SEC)
                    print(f"[TRANSCRIBE] Attempting transcription with {len(window_bytes) if window_bytes else 0} bytes of new audio")
                    
                    # Require at least 2 seconds of audio (64000 bytes = 32000 samples * 2 bytes) for better accuracy
                    if window_bytes and len(window_bytes) >= 64000:
                        transcription_count += 1
                        print(f"[TRANSCRIBE #{transcription_count}] Starting transcription of {len(window_bytes)} bytes...")
                        
                        text = await transcribe_window(window_bytes)
                        
                        print(f"[TRANSCRIBE #{transcription_count}] Result: '{text}' (length: {len(text)})")
                        
                        if text.strip():  # Only send non-empty text
                            await websocket.send_text(text)
                            print(f"[SENT #{transcription_count}] Sent to client: '{text}'")
                        else:
                            print(f"[SKIP #{transcription_count}] Empty transcription, not sending")
                    else:
                        audio_bytes = len(window_bytes) if window_bytes else 0
                        duration_sec = audio_bytes / (SAMPLE_RATE * 2) if audio_bytes > 0 else 0
                        print(f"[SKIP] Not enough new audio data for transcription ({audio_bytes} bytes = {duration_sec:.2f}s)")
                except Exception as transcribe_error:
                    print(f"[TRANSCRIBE ERROR] {transcribe_error}")
                    import traceback
                    traceback.print_exc()
                        
                last_emit = now
                
    except WebSocketDisconnect:
        print("PCM16 WebSocket disconnected")
    except Exception as e:
        print(f"PCM16 WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        await websocket.close()

# Non-streaming HTTP endpoint for Gradio sanity test
from fastapi import UploadFile, File
import tempfile
@app.post("/transcribe")
async def transcribe_file(file: UploadFile = File(...)):
    # Save uploaded file to a temporary file that faster-whisper can read
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file.flush()
            tmp_path = tmp_file.name
        
        # File is now closed, safe to use with faster-whisper
        segments, info = model.transcribe(
            tmp_path,
            language=LANG,
            task="transcribe",
            beam_size=1,
            vad_filter=False,
            word_timestamps=False,
            initial_prompt=None
        )
        text = "".join(s.text for s in segments)
        
        return {"text": text.strip()}
    
    finally:
        # Clean up the temporary file safely
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except (OSError, PermissionError):
                # If we can't delete it immediately, it will be cleaned up later
                pass

if __name__ == "__main__":
    # For local development - Railway uses hypercorn via Procfile
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
