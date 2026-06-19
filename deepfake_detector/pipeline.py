"""
pipeline.py — Multi-modal deepfake detection pipeline.

Fast-path: metadata checked first (< 0.5s).
  If metadata score >= 55 → skip expensive models, return early.

Full pipeline (parallel stages):
  Stage 1 (parallel): visual ensemble + audio
  Stage 2 (parallel): temporal + SPN + forensic + lipsync

Signal weights:
  visual    40%  — 3-model adaptive cascade + TTA
  audio     18%  — wav2vec2 deepfake audio model
  temporal  12%  — inter-frame face consistency
  lipsync   10%  — mouth motion vs audio energy correlation
  spn       10%  — sensor noise fingerprint (PRNU)
  forensic   7%  — FFT / compression / boundary / color
  metadata   3%  — codec / encoder / EXIF anomalies

Verdict thresholds:
  >= 70 → FAKE    >= 50 → LIKELY FAKE
  >= 35 → UNCERTAIN    < 35 → REAL
"""

import os, shutil, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

W = {
    "visual":   0.40,
    "audio":    0.18,
    "temporal": 0.12,
    "lipsync":  0.10,
    "spn":      0.10,
    "forensic": 0.07,
    "metadata": 0.03,
}
_META_FAST_THRESHOLD = 55


def _verdict(s):
    if s is None: return "UNKNOWN"
    return "FAKE" if s >= 70 else "LIKELY FAKE" if s >= 50 else "UNCERTAIN" if s >= 35 else "REAL"


# ── sub-tasks ─────────────────────────────────────────────────────────────────

def _meta(path):
    try:
        from metadata_analyzer import analyze_video_metadata
        return analyze_video_metadata(path)
    except Exception as e:
        return {"score": 0, "anomalies": [], "error": str(e)}


def _visual(video_path, wdir):
    from frame_extractor import extract_frames
    from face_detector   import detect_faces_batch
    from classifier      import classify_faces_batch
    from aggregator      import aggregate_results
    fd = f"{wdir}/faces"; fc = f"{wdir}/frames"
    os.makedirs(fd, exist_ok=True); os.makedirs(fc, exist_ok=True)
    try:
        extract_frames(video_path, fc)
        fps_all = [os.path.join(fc, f) for f in sorted(os.listdir(fc))]
        saved   = detect_faces_batch(fps_all, fd)
        faces   = [p for p in saved if p]
        if not faces:
            return {"score": None, "face_paths": [], "frame_paths": fps_all, "error": "No faces"}
        raw    = classify_faces_batch(faces, verbose=False)
        scores = [s for s in raw if s is not None]
        if not scores:
            return {"score": None, "face_paths": faces, "frame_paths": fps_all, "error": "No scores"}
        agg = aggregate_results(scores, debug=False)
        return {"score": agg["median_score"], "face_paths": faces, "frame_paths": fps_all,
                "frame_count": agg["frame_count"], "high_fake_pct": agg["high_fake_pct"]}
    except Exception as e:
        return {"score": None, "face_paths": [], "frame_paths": [], "error": str(e)}


def _audio(path):
    try:
        from audio_classifier import classify_audio
        return {"score": classify_audio(path)}
    except Exception as e:
        return {"score": None, "error": str(e)}


def _temporal(face_paths):
    try:
        from temporal_analyzer import temporal_consistency_score
        return {"score": temporal_consistency_score(face_paths)}
    except Exception as e:
        return {"score": 0, "error": str(e)}


def _lipsync(face_paths, video_path):
    try:
        from lipsync_analyzer import lipsync_score
        return {"score": lipsync_score(face_paths, video_path)}
    except Exception as e:
        return {"score": 0, "error": str(e)}


def _spn(frame_paths):
    try:
        from spn_analyzer import spn_score
        return {"score": spn_score(frame_paths)}
    except Exception as e:
        return {"score": 0, "error": str(e)}


def _forensic(face_paths):
    if not face_paths:
        return {"score": 0, "details": {}, "anomalies": []}
    try:
        from forensic_rules import run_all_forensic_rules
        return run_all_forensic_rules(face_paths)
    except Exception as e:
        return {"score": 0, "details": {}, "anomalies": [], "error": str(e)}


def _combine(component_scores):
    tw = ws = 0.0
    for k, wt in W.items():
        s = component_scores.get(k)
        if s is not None:
            ws += s * wt; tw += wt
    return round(ws / tw, 2) if tw else None


# ── public API ────────────────────────────────────────────────────────────────

def analyze_video(video_path, cleanup=True):
    """
    Full multi-modal pipeline.
    Returns dict: final_score, verdict, confidence, fast_path, component_scores,
                  components, anomalies, timestamp, video_path.
    """
    wdir = f"_pipe_{os.getpid()}_{threading.get_ident()}"
    os.makedirs(wdir, exist_ok=True)

    try:
        # ── Stage 0: fast metadata pre-check (< 0.5s) ─────────────────────
        metadata   = _meta(video_path)
        meta_score = metadata.get("score", 0)

        if meta_score >= _META_FAST_THRESHOLD:
            final = min(100, meta_score + 10)
            return {
                "final_score":      round(float(final), 2),
                "verdict":          _verdict(final),
                "confidence":       min(99, int(final)),
                "fast_path":        True,
                "fast_reason":      "metadata",
                "timestamp":        datetime.now().isoformat(),
                "video_path":       video_path,
                "components":       {"metadata": metadata},
                "component_scores": {"metadata": meta_score},
                "anomalies":        metadata.get("anomalies", []),
            }

        # ── Stage 1: parallel visual + audio ──────────────────────────────
        with ThreadPoolExecutor(max_workers=2) as ex:
            vis_f = ex.submit(_visual, video_path, wdir)
            aud_f = ex.submit(_audio,  video_path)
            vis   = vis_f.result()
            aud   = aud_f.result()

        face_paths  = vis.get("face_paths",  [])
        frame_paths = vis.get("frame_paths", [])

        # ── Stage 2: parallel temporal + lipsync + SPN + forensic ─────────
        with ThreadPoolExecutor(max_workers=4) as ex:
            temp_f  = ex.submit(_temporal, face_paths)
            lips_f  = ex.submit(_lipsync,  face_paths, video_path)
            spn_f   = ex.submit(_spn,      frame_paths)
            foren_f = ex.submit(_forensic, face_paths)
            temp    = temp_f.result()
            lips    = lips_f.result()
            spn     = spn_f.result()
            foren   = foren_f.result()

        cs = {
            "visual":   vis.get("score"),
            "audio":    aud.get("score"),
            "temporal": temp.get("score"),
            "lipsync":  lips.get("score"),
            "spn":      spn.get("score"),
            "forensic": foren.get("score", 0),
            "metadata": meta_score,
        }
        final     = _combine(cs)
        anomalies = metadata.get("anomalies", []) + foren.get("anomalies", [])

        # Multi-signal consensus boost: if 4+ signals all agree fake
        if final is not None:
            strong = sum(1 for s in cs.values() if s is not None and s >= 60)
            if strong >= 4:
                final = min(99, final + 5)

        return {
            "final_score":      final,
            "verdict":          _verdict(final),
            "confidence":       min(99, int(final)) if final else 0,
            "fast_path":        False,
            "timestamp":        datetime.now().isoformat(),
            "video_path":       video_path,
            "components":       {
                "visual": vis, "audio": aud, "temporal": temp,
                "lipsync": lips, "spn": spn,
                "metadata": metadata, "forensic": foren,
            },
            "component_scores": cs,
            "anomalies":        anomalies,
        }
    finally:
        if cleanup and os.path.exists(wdir):
            try: shutil.rmtree(wdir)
            except Exception: pass


def analyze_image(path):
    """Single-image pipeline (no audio/temporal/SPN/lipsync)."""
    from metadata_analyzer import analyze_image_metadata
    from forensic_rules    import run_all_forensic_rules
    from classifier        import classify_face

    meta  = analyze_image_metadata(path)
    foren = run_all_forensic_rules([path])
    try:    vs = classify_face(path, verbose=False)
    except Exception: vs = None

    w = {"visual": 0.60, "forensic": 0.25, "metadata": 0.15}
    s = {"visual": vs, "forensic": foren.get("score", 0), "metadata": meta.get("score", 0)}
    tw = ws = 0.0
    for k, wt in w.items():
        if s[k] is not None: ws += s[k] * wt; tw += wt
    final = round(ws / tw, 2) if tw else None
    return {
        "final_score": final, "verdict": _verdict(final), "image_path": path,
        "components":  {"visual": {"score": vs}, "metadata": meta, "forensic": foren},
        "anomalies":   meta.get("anomalies", []) + foren.get("anomalies", []),
    }
