"""
api.py — FastAPI REST API for the deepfake detection system.

Endpoints:
  GET  /health
  GET  /                     — web dashboard
  POST /analyze/video        — upload video → job_id (202, async)
  GET  /jobs/{job_id}        — poll job status / result
  POST /analyze/video/sync   — synchronous (for internal/LAN use only)
  POST /analyze/audio        — upload audio/video → audio-only score
  POST /analyze/text         — JSON body {text} → AI-text detection
  POST /analyze/url          — JSON body {url} → crawl + analyse
  GET  /results              — last N scan results
  POST /feedback             — submit correction for a result
  GET  /feedback/stats       — feedback summary

Run:
    uvicorn api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import json
import uuid
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
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

# ── async job store ──────────────────────────────────────────────────────────
# jobs: {job_id: {"status": "pending"|"running"|"done"|"error", "result": ...}}
_jobs: dict = {}
_jobs_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=2)


def _preload_models():
    """Warm up primary model on startup so first analysis doesn't cold-start."""
    try:
        from classifier import _get_pipe
        _get_pipe("prithivMLmods/Deep-Fake-Detector-v2-Model")
        print("Primary model preloaded OK")
    except Exception as e:
        print(f"Preload skipped: {e}")


@app.on_event("startup")
async def startup():
    threading.Thread(target=_preload_models, daemon=True).start()


def _log(result: dict):
    with open(os.path.join(RESULTS_DIR, "api_results.jsonl"), "a") as f:
        f.write(json.dumps(result) + "\n")


def _tmp(suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def _run_video_job(job_id: str, path: str, filename: str):
    with _jobs_lock:
        _jobs[job_id].update({"status": "running", "stage": "starting", "partial_scores": {}})

    def on_stage(stage: str, partial: dict):
        with _jobs_lock:
            _jobs[job_id]["stage"]          = stage
            _jobs[job_id]["partial_scores"] = partial

    try:
        from pipeline import analyze_video as _av
        result = _av(path, cleanup=True, on_stage=on_stage)
        result["filename"] = filename
        result["job_id"]   = job_id
        _log(result)
        with _jobs_lock:
            _jobs[job_id].update({"status": "done", "result": result, "stage": "done"})
    except Exception as e:
        with _jobs_lock:
            _jobs[job_id].update({"status": "error", "error": str(e), "stage": "error"})
    finally:
        if os.path.exists(path):
            try: os.remove(path)
            except OSError: pass


# ─── dashboard ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    from web_ui import DASHBOARD_HTML
    return DASHBOARD_HTML


# ─── health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    pending = sum(1 for j in _jobs.values() if j["status"] in ("pending", "running"))
    return {"status": "ok", "timestamp": datetime.now().isoformat(),
            "version": "2.0", "jobs_active": pending}


# ─── video (async) ───────────────────────────────────────────────────────────

@app.post("/analyze/video", status_code=202)
async def analyze_video(file: UploadFile = File(...)):
    """Submit video for async analysis. Returns job_id — poll GET /jobs/{job_id}."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _VIDEO_EXTS:
        raise HTTPException(400, f"Unsupported video type '{ext}'")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 500 MB)")

    path = _tmp(ext)
    with open(path, "wb") as f:
        f.write(data)
    del data

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "pending", "result": None,
                         "filename": file.filename,
                         "submitted": datetime.now().isoformat()}

    _executor.submit(_run_video_job, job_id, path, file.filename or "upload")
    return JSONResponse({"job_id": job_id, "status": "pending",
                         "poll_url": f"/jobs/{job_id}"}, status_code=202)


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Poll job status. status: pending | running | done | error."""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, f"Job {job_id} not found")
    return JSONResponse(job)


@app.post("/analyze/video/sync")
async def analyze_video_sync(file: UploadFile = File(...)):
    """Synchronous video analysis — use only when timeout is not a concern."""
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


# ─── feedback ─────────────────────────────────────────────────────────────────

class FeedbackReq(BaseModel):
    filename: str = ""
    predicted_verdict: str
    predicted_score: float
    correct_verdict: str
    component_scores: dict = {}
    notes: str = ""


@app.post("/feedback")
async def submit_feedback(req: FeedbackReq):
    """Submit a correction for a scan result. Stored for calibration review."""
    if req.correct_verdict not in {"FAKE", "LIKELY FAKE", "UNCERTAIN", "REAL"}:
        raise HTTPException(400, "correct_verdict must be FAKE, LIKELY FAKE, UNCERTAIN, or REAL")
    entry = {
        "id": str(uuid.uuid4()),
        "filename": req.filename,
        "predicted_verdict": req.predicted_verdict,
        "predicted_score": req.predicted_score,
        "correct_verdict": req.correct_verdict,
        "component_scores": req.component_scores,
        "notes": req.notes,
        "timestamp": datetime.now().isoformat(),
    }
    with open(os.path.join(RESULTS_DIR, "feedback.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")
    return JSONResponse({"status": "ok", "id": entry["id"]})


@app.get("/feedback/stats")
async def feedback_stats():
    """Summary of submitted corrections."""
    fpath = os.path.join(RESULTS_DIR, "feedback.jsonl")
    if not os.path.exists(fpath):
        return JSONResponse({"total": 0, "corrections": []})
    entries = []
    with open(fpath) as f:
        for line in f:
            line = line.strip()
            if line:
                try: entries.append(json.loads(line))
                except json.JSONDecodeError: pass
    wrong = [e for e in entries if e["predicted_verdict"] != e["correct_verdict"]]
    return JSONResponse({
        "total": len(entries),
        "corrections": len(wrong),
        "accuracy_rate": round(1 - len(wrong) / max(len(entries), 1), 3),
        "recent": entries[-10:][::-1],
    })


if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
