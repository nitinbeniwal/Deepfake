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
import sys
import json
import uuid
import tempfile
import threading

# Windows consoles default to cp1252 — any non-ASCII in a print() (e.g. arrows,
# emoji) raises UnicodeEncodeError mid-analysis, which the pipeline catches as an
# extraction error and silently drops the visual signal. Force UTF-8 with
# replacement so logging can never abort detection.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
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
LOGS_DIR    = "logs"
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

_ERROR_LOG  = os.path.join(LOGS_DIR, "errors.jsonl")
_EVENT_LOG  = os.path.join(LOGS_DIR, "events.jsonl")
_SERVER_START = datetime.now().isoformat()

def _log_event(event: str, data: dict):
    """Append a structured event to the event log (non-blocking)."""
    try:
        row = {"ts": datetime.now().isoformat(), "event": event, **data}
        with open(_EVENT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass

def _log_error(job_id: str, filename: str, stage: str, error: str, tb: str = ""):
    """Append a structured error record."""
    try:
        row = {
            "ts": datetime.now().isoformat(),
            "job_id": job_id,
            "filename": filename,
            "stage": stage,
            "error": error,
            "traceback": tb,
        }
        with open(_ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass

_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}
_AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma", ".opus", ".amr"}
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif", ".heic", ".heif", ".gif"}
_ALL_EXTS   = _VIDEO_EXTS | _AUDIO_EXTS | _IMAGE_EXTS

def _media_type(ext: str) -> str:
    e = ext.lower()
    if e in _VIDEO_EXTS: return "video"
    if e in _AUDIO_EXTS: return "audio"
    if e in _IMAGE_EXTS: return "image"
    return "unknown"

# ── async job store ──────────────────────────────────────────────────────────
# jobs: {job_id: {"status": "pending"|"running"|"done"|"error", "result": ...}}
_jobs: dict = {}
_jobs_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=2)


def _preload_models():
    """Warm up primary model on startup so first analysis doesn't cold-start."""
    try:
        from device_utils import describe
        print(f"Compute device: {describe()}")
    except Exception:
        pass
    try:
        from classifier import _get_pipe
        _get_pipe("prithivMLmods/Deep-Fake-Detector-v2-Model")
        print("Primary model preloaded OK")
    except Exception as e:
        print(f"Preload skipped: {e}")


@app.on_event("startup")
async def startup():
    # Download DeepfakeBench checkpoints (Xception + EfficientNet-B4) in background
    try:
        from model_downloader import ensure_checkpoints
        ensure_checkpoints(blocking=False)
    except Exception as e:
        print(f"Checkpoint downloader skipped: {e}")
    threading.Thread(target=_preload_models, daemon=True).start()


def _log(result: dict):
    with open(os.path.join(RESULTS_DIR, "api_results.jsonl"), "a") as f:
        f.write(json.dumps(result) + "\n")


def _tmp(suffix):
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def _finish_job(job_id, path, result, case_id, evidence_id):
    """Common completion handler for all media job types."""
    _log(result)
    filename = result.get("filename", "")
    _log_event("job_done", {"job_id": job_id, "filename": filename,
                            "verdict": result.get("verdict"), "score": result.get("final_score")})
    with _jobs_lock:
        _jobs[job_id].update({"status": "done", "result": result, "stage": "done",
                               "finished": datetime.now().isoformat()})
    if case_id and evidence_id:
        try:
            from case_store import set_evidence
            set_evidence(case_id, evidence_id, status="done", result=result)
        except Exception:
            pass
    if os.path.exists(path):
        try: os.remove(path)
        except OSError: pass


def _fail_job(job_id, path, error, case_id, evidence_id, stage="unknown", tb=""):
    import traceback as _tb
    tb_str = tb or _tb.format_exc()
    with _jobs_lock:
        info = _jobs.get(job_id, {})
        filename = info.get("filename", "")
        _jobs[job_id].update({"status": "error", "error": str(error),
                               "stage": stage, "traceback": tb_str,
                               "finished": datetime.now().isoformat()})
    _log_error(job_id, filename, stage, str(error), tb_str)
    _log_event("job_error", {"job_id": job_id, "filename": filename,
                              "stage": stage, "error": str(error)})
    if case_id and evidence_id:
        try:
            from case_store import set_evidence
            set_evidence(case_id, evidence_id, status="error",
                         result={"error": str(error), "stage": stage})
        except Exception:
            pass
    if os.path.exists(path):
        try: os.remove(path)
        except OSError: pass


def _run_image_job(job_id: str, path: str, filename: str,
                   case_id: str = None, evidence_id: str = None):
    with _jobs_lock:
        _jobs[job_id].update({"status": "running", "stage": "starting", "partial_scores": {}})
    if case_id and evidence_id:
        try:
            from case_store import set_evidence
            set_evidence(case_id, evidence_id, status="running", job_id=job_id)
        except Exception:
            pass

    def on_stage(stage: str, partial: dict):
        with _jobs_lock:
            _jobs[job_id]["stage"]          = stage
            _jobs[job_id]["partial_scores"] = partial

    try:
        from pipeline import analyze_image as _ai
        result = _ai(path, cleanup=True, on_stage=on_stage)
        result["filename"] = filename
        result["job_id"]   = job_id
        _finish_job(job_id, path, result, case_id, evidence_id)
    except Exception as e:
        import traceback as _tb
        with _jobs_lock:
            stage = _jobs.get(job_id, {}).get("stage", "unknown")
        _fail_job(job_id, path, e, case_id, evidence_id, stage=stage, tb=_tb.format_exc())


def _run_audio_job(job_id: str, path: str, filename: str,
                   case_id: str = None, evidence_id: str = None):
    with _jobs_lock:
        _jobs[job_id].update({"status": "running", "stage": "starting", "partial_scores": {}})
    if case_id and evidence_id:
        try:
            from case_store import set_evidence
            set_evidence(case_id, evidence_id, status="running", job_id=job_id)
        except Exception:
            pass

    def on_stage(stage: str, partial: dict):
        with _jobs_lock:
            _jobs[job_id]["stage"]          = stage
            _jobs[job_id]["partial_scores"] = partial

    try:
        from pipeline import analyze_audio as _aa
        result = _aa(path, cleanup=True, on_stage=on_stage)
        result["filename"] = filename
        result["job_id"]   = job_id
        _finish_job(job_id, path, result, case_id, evidence_id)
    except Exception as e:
        import traceback as _tb
        with _jobs_lock:
            stage = _jobs.get(job_id, {}).get("stage", "unknown")
        _fail_job(job_id, path, e, case_id, evidence_id, stage=stage, tb=_tb.format_exc())


def _run_video_job(job_id: str, path: str, filename: str,
                   case_id: str = None, evidence_id: str = None, focus: str = "full"):
    with _jobs_lock:
        _jobs[job_id].update({"status": "running", "stage": "starting", "partial_scores": {}})

    if case_id and evidence_id:
        try:
            from case_store import set_evidence
            set_evidence(case_id, evidence_id, status="running", job_id=job_id)
        except Exception:
            pass

    def on_stage(stage: str, partial: dict):
        with _jobs_lock:
            _jobs[job_id]["stage"]          = stage
            _jobs[job_id]["partial_scores"] = partial

    try:
        from pipeline import analyze_video as _av
        result = _av(path, cleanup=True, on_stage=on_stage, focus=focus)
        result["filename"] = filename
        result["job_id"]   = job_id
        _finish_job(job_id, path, result, case_id, evidence_id)
    except Exception as e:
        import traceback as _tb
        with _jobs_lock:
            stage = _jobs.get(job_id, {}).get("stage", "unknown")
        _fail_job(job_id, path, e, case_id, evidence_id, stage=stage, tb=_tb.format_exc())


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
async def analyze_video(file: UploadFile = File(...), focus: str = Query("full")):
    """Submit any media file for async analysis. Returns job_id — poll GET /jobs/{job_id}.

    Accepts: video (mp4/avi/mov/mkv/webm/m4v), image (jpg/png/webp/bmp/gif/heic),
             audio (mp3/wav/m4a/flac/ogg/aac/opus).
    focus: full | visual | audio | quick — applies to video only."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALL_EXTS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. "
                            f"Supported: video={sorted(_VIDEO_EXTS)}, "
                            f"image={sorted(_IMAGE_EXTS)}, audio={sorted(_AUDIO_EXTS)}")

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
                         "filename": file.filename, "focus": focus,
                         "submitted": datetime.now().isoformat()}

    mtype = _media_type(ext)
    if mtype == "image":
        _executor.submit(_run_image_job, job_id, path, file.filename or "upload", None, None)
    elif mtype == "audio":
        _executor.submit(_run_audio_job, job_id, path, file.filename or "upload", None, None)
    else:
        _executor.submit(_run_video_job, job_id, path, file.filename or "upload", None, None, focus)

    return JSONResponse({"job_id": job_id, "status": "pending", "media_type": mtype,
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
        from calibration import verdict as _verdict
        verdict = _verdict(score)
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
    fpath = os.path.join(RESULTS_DIR, "feedback.jsonl")
    with open(fpath, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Feed the correction back into calibration so the next upload scores better.
    # Re-reads ALL feedback and recomputes the visual offset (EMA + clamped).
    calib = None
    try:
        rows = []
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try: rows.append(json.loads(line))
                    except json.JSONDecodeError: pass
        from calibration import record_feedback
        calib = record_feedback(rows)
        _log_event("calibration_update",
                   {"visual_offset": calib.get("visual_offset"),
                    "n_feedback": calib.get("n_feedback")})
    except Exception as e:
        _log_event("calibration_error", {"error": str(e)})

    return JSONResponse({"status": "ok", "id": entry["id"],
                         "calibration": calib})


@app.post("/analyze/gradcam")
async def analyze_gradcam(
    file: UploadFile = File(...),
    model_type: str = "xception",
):
    """
    Generate Grad-CAM forensic heatmap for a face image.
    Shows which facial regions triggered the FAKE classification.
    Use for evidence documentation in law enforcement reports.

    model_type: "xception" (default) or "efficientnet_b4"
    Returns: fake_probability + base64 PNG heatmap overlay.
    """
    if model_type not in ("xception", "efficientnet_b4"):
        raise HTTPException(400, "model_type must be 'xception' or 'efficientnet_b4'")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
        raise HTTPException(400, f"Unsupported image type '{ext}'")

    path = _tmp(ext)
    try:
        data = await file.read()
        if len(data) > 20 * 1024 * 1024:
            raise HTTPException(413, "Image too large (max 20MB)")
        with open(path, "wb") as f:
            f.write(data)
        del data

        from gradcam_engine import gradcam_for_image
        result = gradcam_for_image(path, model_type=model_type)
        if "error" in result:
            raise HTTPException(503, result["error"])
        result["filename"] = file.filename
        result["timestamp"] = datetime.now().isoformat()
        return JSONResponse(result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Grad-CAM failed: {e}")
    finally:
        if os.path.exists(path):
            try: os.remove(path)
            except OSError: pass


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
    calib = None
    try:
        from calibration import _load
        calib = _load()
    except Exception:
        pass
    return JSONResponse({
        "total": len(entries),
        "corrections": len(wrong),
        "accuracy_rate": round(1 - len(wrong) / max(len(entries), 1), 3),
        "calibration": calib,
        "recent": entries[-10:][::-1],
    })


# ─── cases (cyber-cell case management) ───────────────────────────────────────

class CaseReq(BaseModel):
    case_no: str = ""
    title: str = ""
    officer_name: str = ""
    officer_badge: str = ""
    department: str = ""
    suspect: str = ""
    victim: str = ""
    source_url: str = ""
    incident_date: str = ""
    priority: str = "MEDIUM"
    notes: str = ""


class CaseUpdateReq(BaseModel):
    status: str = None
    notes: str = None
    priority: str = None
    suspect: str = None
    victim: str = None
    title: str = None
    officer_name: str = None
    officer_badge: str = None
    department: str = None
    source_url: str = None
    incident_date: str = None
    case_no: str = None


@app.get("/cases")
async def cases_list():
    from case_store import list_cases
    return JSONResponse({"cases": list_cases()})


@app.post("/cases", status_code=201)
async def cases_create(req: CaseReq):
    from case_store import create_case
    case = create_case(req.dict())
    return JSONResponse(case, status_code=201)


@app.get("/cases/{case_id}")
async def cases_get(case_id: str):
    from case_store import get_case
    case = get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return JSONResponse(case)


@app.patch("/cases/{case_id}")
async def cases_update(case_id: str, req: CaseUpdateReq):
    from case_store import update_case
    case = update_case(case_id, {k: v for k, v in req.dict().items() if v is not None})
    if not case:
        raise HTTPException(404, "Case not found")
    return JSONResponse(case)


@app.post("/cases/{case_id}/evidence", status_code=202)
async def cases_add_evidence(case_id: str, file: UploadFile = File(...),
                             uploaded_by: str = Query(""), focus: str = Query("full")):
    """Attach a video to a case (with chain-of-custody) and start analysis."""
    from case_store import get_case, add_evidence
    if not get_case(case_id):
        raise HTTPException(404, "Case not found")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALL_EXTS:
        raise HTTPException(400, f"Unsupported file type '{ext}'")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 500 MB)")

    path = _tmp(ext)
    with open(path, "wb") as f:
        f.write(data)
    del data

    ev = add_evidence(case_id, filename=file.filename or "upload",
                      file_path=path, uploaded_by=uploaded_by)

    job_id = str(uuid.uuid4())
    mtype  = _media_type(ext)
    with _jobs_lock:
        _jobs[job_id] = {"status": "pending", "result": None,
                         "filename": file.filename, "case_id": case_id,
                         "evidence_id": ev["evidence_id"], "focus": focus,
                         "media_type": mtype,
                         "submitted": datetime.now().isoformat()}

    if mtype == "image":
        _executor.submit(_run_image_job, job_id, path, file.filename or "upload",
                         case_id, ev["evidence_id"])
    elif mtype == "audio":
        _executor.submit(_run_audio_job, job_id, path, file.filename or "upload",
                         case_id, ev["evidence_id"])
    else:
        _executor.submit(_run_video_job, job_id, path, file.filename or "upload",
                         case_id, ev["evidence_id"], focus)

    return JSONResponse({"job_id": job_id, "evidence_id": ev["evidence_id"],
                         "sha256": ev["sha256"], "media_type": mtype,
                         "poll_url": f"/jobs/{job_id}"},
                        status_code=202)


@app.get("/cases/{case_id}/report", response_class=HTMLResponse)
async def cases_report(case_id: str):
    """Printable forensic report for a case (browser print → PDF)."""
    from case_store import get_case
    from report import render_case_report
    case = get_case(case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return HTMLResponse(render_case_report(case))


# ─── admin panel ─────────────────────────────────────────────────────────────

@app.get("/admin/jobs")
async def admin_jobs(limit: int = Query(100, ge=1, le=1000)):
    """All jobs sorted newest-first with full detail (status, stage, error, traceback)."""
    with _jobs_lock:
        jobs_snap = dict(_jobs)
    rows = []
    for jid, j in jobs_snap.items():
        rows.append({
            "job_id":    jid,
            "filename":  j.get("filename", ""),
            "status":    j.get("status", ""),
            "stage":     j.get("stage", ""),
            "error":     j.get("error", ""),
            "traceback": j.get("traceback", ""),
            "submitted": j.get("submitted", ""),
            "finished":  j.get("finished", ""),
            "media_type": j.get("media_type") or j.get("result", {}).get("media_type", ""),
            "verdict":   j.get("result", {}).get("verdict", "") if j.get("result") else "",
        })
    rows.sort(key=lambda r: r["submitted"], reverse=True)
    return JSONResponse({"jobs": rows[:limit], "total": len(rows)})


@app.get("/admin/logs")
async def admin_logs(
    log_type: str = Query("errors", regex="^(errors|events)$"),
    limit: int = Query(100, ge=1, le=1000),
):
    """Return last N entries from errors.jsonl or events.jsonl."""
    fpath = _ERROR_LOG if log_type == "errors" else _EVENT_LOG
    if not os.path.exists(fpath):
        return JSONResponse({"log_type": log_type, "entries": [], "total": 0})
    rows = []
    with open(fpath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    rows.reverse()
    return JSONResponse({"log_type": log_type, "entries": rows[:limit], "total": len(rows)})


@app.get("/admin/stats")
async def admin_stats():
    """System stats: uptime, job counts, memory, disk."""
    with _jobs_lock:
        all_jobs = list(_jobs.values())
    counts = {"pending": 0, "running": 0, "done": 0, "error": 0}
    for j in all_jobs:
        s = j.get("status", "")
        if s in counts:
            counts[s] += 1

    mem_mb = None
    try:
        import psutil
        proc = psutil.Process()
        mem_mb = round(proc.memory_info().rss / 1024 / 1024, 1)
        disk = psutil.disk_usage(".")
        disk_info = {"total_gb": round(disk.total / 1e9, 1),
                     "used_gb": round(disk.used / 1e9, 1),
                     "free_gb": round(disk.free / 1e9, 1)}
    except Exception:
        disk_info = {}

    now = datetime.now()
    start = datetime.fromisoformat(_SERVER_START)
    uptime_s = int((now - start).total_seconds())
    hours, rem = divmod(uptime_s, 3600)
    mins, secs = divmod(rem, 60)

    error_log_size = 0
    event_log_size = 0
    if os.path.exists(_ERROR_LOG):
        error_log_size = os.path.getsize(_ERROR_LOG)
    if os.path.exists(_EVENT_LOG):
        event_log_size = os.path.getsize(_EVENT_LOG)

    return JSONResponse({
        "server_start":   _SERVER_START,
        "uptime":         f"{hours}h {mins}m {secs}s",
        "uptime_seconds": uptime_s,
        "jobs":           counts,
        "total_jobs":     len(all_jobs),
        "memory_mb":      mem_mb,
        "disk":           disk_info,
        "error_log_bytes": error_log_size,
        "event_log_bytes": event_log_size,
        "timestamp":      now.isoformat(),
    })


if __name__ == "__main__":
    import uvicorn, os
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
