"""
api.py — FastAPI REST API for the deepfake detection system.

Endpoints:
  GET  /health
  POST /analyze/video   — upload video → full pipeline result
  POST /analyze/audio   — upload audio/video → audio-only score
  POST /analyze/text    — JSON body {text} → AI-text detection
  POST /analyze/url     — JSON body {url} → crawl + analyse
  GET  /results         — last N scan results

Run:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import json
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="Deepfake Detection API",
    description="Multi-modal deepfake detection — video, audio, text, web.",
    version="2.0.0",
)

MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
_AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}


def _log(result: dict):
    with open(os.path.join(RESULTS_DIR, "api_results.jsonl"), "a") as f:
        f.write(json.dumps(result) + "\n")


def _tmp(suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


# ─── health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat(), "version": "2.0"}


# ─── video ───────────────────────────────────────────────────────────────────

@app.post("/analyze/video")
async def analyze_video(file: UploadFile = File(...)):
    """Full pipeline: visual + audio + metadata + forensic rules."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _VIDEO_EXTS:
        raise HTTPException(400, f"Unsupported video type '{ext}'")

    path = _tmp(ext)
    try:
        data = await file.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "File too large (max 500 MB)")
        with open(path, "wb") as f:
            f.write(data)
        del data
        from pipeline import analyze_video as _av
        result = _av(path, cleanup=True)
        result["filename"] = file.filename
        _log(result)
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}")
    finally:
        if os.path.exists(path):
            try: os.remove(path)
            except OSError: pass


# ─── audio ───────────────────────────────────────────────────────────────────

@app.post("/analyze/audio")
async def analyze_audio(file: UploadFile = File(...)):
    """Audio-only deepfake score."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (_VIDEO_EXTS | _AUDIO_EXTS):
        raise HTTPException(400, f"Unsupported file type '{ext}'")

    path = _tmp(ext)
    try:
        with open(path, "wb") as f:
            f.write(await file.read())
        from audio_classifier import classify_audio
        score = classify_audio(path)
        verdict = "FAKE" if score >= 50 else ("UNCERTAIN" if score >= 35 else "REAL")
        result = {"score": score, "verdict": verdict,
                  "filename": file.filename,
                  "timestamp": datetime.now().isoformat()}
        _log(result)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(500, f"Audio analysis failed: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)


# ─── text ────────────────────────────────────────────────────────────────────

class TextReq(BaseModel):
    text: str


@app.post("/analyze/text")
async def analyze_text(req: TextReq):
    """Detect AI-generated text."""
    if not req.text.strip():
        raise HTTPException(400, "text cannot be empty")
    try:
        from text_detector import detect_ai_text
        label, confidence = detect_ai_text(req.text)
        result = {"label": label, "confidence": confidence,
                  "timestamp": datetime.now().isoformat()}
        _log(result)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(500, f"Text analysis failed: {e}")


# ─── url ─────────────────────────────────────────────────────────────────────

class URLReq(BaseModel):
    url: str
    max_texts: int = 5


@app.post("/analyze/url")
async def analyze_url(req: URLReq):
    """Crawl a URL and analyse text blocks for AI content."""
    if not req.url.startswith(("http://", "https://")):
        raise HTTPException(400, "URL must start with http:// or https://")
    try:
        from crawler   import crawl_page
        from processor import process_content
        texts, videos = crawl_page(req.url)
        results = process_content(req.url, texts[: req.max_texts]) if texts else []
        out = {
            "url": req.url,
            "texts_found": len(texts),
            "videos_found": len(videos),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
        _log(out)
        return JSONResponse(out)
    except Exception as e:
        raise HTTPException(500, f"URL analysis failed: {e}")


# ─── results ─────────────────────────────────────────────────────────────────

@app.get("/results")
async def get_results(limit: int = Query(50, ge=1, le=500)):
    """Return the most recent scan results."""
    log = os.path.join(RESULTS_DIR, "api_results.jsonl")
    if not os.path.exists(log):
        return JSONResponse({"results": [], "total": 0})

    lines = []
    with open(log) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    lines.reverse()
    return JSONResponse({"results": lines[:limit], "total": len(lines)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
