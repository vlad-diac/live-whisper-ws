# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing and build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for building the frontend
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy Python requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend package files and install Node dependencies
COPY whisper-fe/package*.json ./whisper-fe/
WORKDIR /app/whisper-fe
RUN npm ci --only=production

# Copy frontend source code and build
COPY whisper-fe/ ./
RUN npm run build

# Go back to app directory and copy Python source
WORKDIR /app
COPY server.py .

# Create directory for static files
RUN mkdir -p static

# Copy built frontend to static directory
RUN cp -r whisper-fe/dist/* static/

# Expose port (Railway will set PORT environment variable)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MODEL_NAME=small.en
ENV COMPUTE_TYPE=int8

# Command to run the application
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
