FROM python:3.11-slim

# System deps: OpenCV headless + ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Runtime directories
RUN mkdir -p results reports extracted_frames detected_faces extracted_audio

# HuggingFace model cache dir — mount as Railway volume for persistence
ENV TRANSFORMERS_CACHE=/cache/hf
ENV HF_HOME=/cache/hf
RUN mkdir -p /cache/hf

EXPOSE ${PORT:-8000}

# Railway injects $PORT — fall back to 8000 locally
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
