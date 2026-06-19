FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements first — cached layer, only re-runs when requirements.txt changes
COPY deepfake_detector/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY deepfake_detector/ .

# Runtime dirs
RUN mkdir -p results reports extracted_frames detected_faces extracted_audio

# HuggingFace model cache — mount as Railway volume for persistence
ENV TRANSFORMERS_CACHE=/cache/hf
ENV HF_HOME=/cache/hf
RUN mkdir -p /cache/hf

# Railway injects $PORT at runtime
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
