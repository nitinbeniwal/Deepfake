FROM python:3.11-slim

# System deps for OpenCV, ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create runtime dirs
RUN mkdir -p results reports extracted_frames detected_faces extracted_audio

EXPOSE 8000

# Default: API server (change CMD to run dashboard.py for Flask)
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
