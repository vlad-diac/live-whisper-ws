import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database URL from Railway environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine
if DATABASE_URL:
    # Railway provides postgres:// but SQLAlchemy needs postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    engine = create_engine(DATABASE_URL)
else:
    # Fallback for local development
    engine = create_engine("sqlite:///./whisper_app.db")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class TranscriptionSession(Base):
    __tablename__ = "transcription_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_token = Column(String, index=True)

class TranscriptionResult(Base):
    __tablename__ = "transcription_results"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    text = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    audio_duration = Column(Integer)  # in milliseconds
    confidence = Column(String)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)
