"""
pipeline.py — Strictly sequential multi-modal deepfake detection pipeline.

Each step runs one at a time. After each step:
  - Model is unloaded from RAM
  - Large objects deleted + gc.collect()
  - Only the scalar score is kept for final combination

Step order:
  0. Metadata         ffprobe — no ML, < 1s
  1. Frame/face ext.  OpenCV — no ML
  2. Visual           5 HF models, one at a time, each unloaded before next loads
  3. Audio            1 HF model, unloaded after (skipped in LOW_MEM)
  4. Temporal         numpy only
  5. Lip-sync         numpy + ffmpeg
  6. SPN              numpy only
  7. Forensic         numpy + PIL, no ML
  8. Meta-classifier  rule-based, no ML
  9. Combine          scalar scores only, instant

Verdict thresholds:
  >= 70 FAKE  >= 50 LIKELY FAKE  >= 35 UNCERTAIN  < 35 REAL
"""

import os, gc, shutil, threading
from datetime import datetime

_LOW_MEM = os.environ.get("LOW_MEM", "0") == "1"
_META_FAST_THRESHOLD = 55

W = {
    "visual":   0.40,
    "audio":    0.18,
    "temporal": 0.12,
    "lipsync":  0.10,
    "spn":      0.10,
    "forensic": 0.07,
    "metadata": 0.03,
}


def _verdict(s):
    if s is None: return "UNKNOWN"
    return "FAKE" if s >= 70 else "LIKELY FAKE" if s >= 50 else "UNCERTAIN" if s >= 35 else "REAL"


def _combine(cs):
    # When metadata is stripped (WhatsApp/re-encode), redistribute weight to forensic+temporal
    meta = cs.get("metadata") or 0
    wts  = dict(W)
    if meta < 5:
        wts["forensic"] = round(W["forensic"] + 0.02, 3)
        wts["temporal"] = round(W["temporal"] + 0.01, 3)
        wts["metadata"] = 0.0
    tw = ws = 0.0
    for k, wt in wts.items():
        s = cs.get(k)
        if s is not None:
            ws += s * wt
            tw += wt
    return round(ws / tw, 2) if tw else None


def _unload_hf(model_id):
    """Unload any model (HF or timm) from classifier cache and free RAM."""
    try:
        from classifier import _unload_model
        _unload_model(model_id)
    except Exception:
        pass
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def analyze_video(video_path, cleanup=True, on_stage=None):
    """
    Fully sequential pipeline.
    on_stage(stage_name, partial_scores_dict) is called after each step —
    use it to push progress to the job dict for live polling.

    Returns dict with final_score, verdict, confidence, component_scores, anomalies.
    """

    def step(name, partial=None):
        if on_stage:
            try:
                on_stage(name, partial or {})
            except Exception:
                pass

    wdir = os.path.abspath(f"_pipe_{os.getpid()}_{threading.get_ident()}")
    os.makedirs(wdir, exist_ok=True)
    fd = os.path.join(wdir, "faces")
    fc = os.path.join(wdir, "frames")
    os.makedirs(fd, exist_ok=True)
    os.makedirs(fc, exist_ok=True)

    cs         = {}   # signal name → scalar score (only thing kept between steps)
    components = {}   # full component dicts for API response
    anomalies  = []

    try:
        # ── Step 0: Metadata (ffprobe, no ML) ─────────────────────────────
        step("metadata")
        try:
            from metadata_analyzer import analyze_video_metadata
            meta = analyze_video_metadata(video_path)
        except Exception as e:
            meta = {"score": 0, "anomalies": [], "error": str(e)}
        cs["metadata"]     = meta.get("score", 0)
        components["metadata"] = meta
        anomalies += meta.get("anomalies", [])
        step("metadata_done", dict(cs))
        gc.collect()

        # Metadata fast-path: skip all ML instantly
        if cs["metadata"] >= _META_FAST_THRESHOLD:
            final = min(99, cs["metadata"] + 10)
            return {
                "final_score":      round(float(final), 2),
                "verdict":          _verdict(final),
                "confidence":       min(99, int(final)),
                "fast_path":        True,
                "fast_reason":      "metadata",
                "timestamp":        datetime.now().isoformat(),
                "video_path":       video_path,
                "components":       {"metadata": meta},
                "component_scores": cs,
                "anomalies":        anomalies,
            }

        # ── Step 1: Extract frames + faces (disk only, no ML) ─────────────
        step("extraction")
        face_paths  = []
        frame_paths = []
        try:
            from frame_extractor import extract_frames
            from face_detector   import detect_faces_batch
            extract_frames(video_path, fc)
            frame_paths = [os.path.join(fc, f) for f in sorted(os.listdir(fc))]
            saved      = detect_faces_batch(frame_paths, fd)
            face_paths = [p for p in saved if p]
        except Exception as e:
            components["extraction_error"] = str(e)
        step("extraction_done", dict(cs))
        gc.collect()

        # ── Step 2: Visual — 7 models sequentially (ViT × 5, Xception, EfficientNet-B4)
        step("visual")
        vis_score = None
        if face_paths:
            try:
                from classifier import _MODELS, _get_pipe, _score as _cls_score, _calibrate
                import statistics as _stats

                model_accum = {}  # model_id → (mean_score, weight)

                for model_id, weight, _stage in _MODELS:
                    # Build short label for live stage reporting
                    short = model_id.split("/")[-1] if "/" in model_id else model_id.split(":")[-1]
                    step(f"visual:{short}", dict(cs))
                    try:
                        from PIL import Image
                        pils = []
                        for p in face_paths:
                            try:
                                pils.append(Image.open(p).convert("RGB"))
                            except Exception:
                                pass

                        if pils:
                            pipe = _get_pipe(model_id)
                            if pipe is not None:
                                raw    = pipe(pils, batch_size=4)
                                scores = [_calibrate(_cls_score(r)) for r in raw]
                                valid  = [s for s in scores if s is not None]
                                if valid:
                                    model_accum[model_id] = (_stats.mean(valid), weight)
                        del pils
                    except Exception as ex:
                        short = model_id.split("/")[-1] if "/" in model_id else model_id
                        print(f"Visual model {short} error: {ex}")
                    finally:
                        _unload_hf(model_id)

                if model_accum:
                    tw = ws = 0.0
                    for mid, (sc, wt) in model_accum.items():
                        ws += sc * wt
                        tw += wt
                    if tw:
                        vis_score = round(ws / tw, 2)
                del model_accum
            except Exception as e:
                components["visual_error"] = str(e)

        cs["visual"] = vis_score
        components["visual"] = {"score": vis_score, "face_count": len(face_paths)}
        step("visual_done", dict(cs))
        gc.collect()

        # ── Step 3: Audio (skip in LOW_MEM — model is ~300MB) ────────────
        if not _LOW_MEM:
            step("audio")
            aud_score = None
            try:
                from audio_classifier import classify_audio
                aud_score = classify_audio(video_path)
                # Unload audio model from RAM
                import audio_classifier as _ac
                _ac._pipe = None
            except Exception as e:
                components["audio_error"] = str(e)
            cs["audio"] = aud_score
            components["audio"] = {"score": aud_score}
            step("audio_done", dict(cs))
            gc.collect()
        else:
            cs["audio"] = None
            components["audio"] = {"score": None, "skipped": "LOW_MEM"}

        # ── Step 4: Temporal consistency (numpy only) ─────────────────────
        step("temporal")
        try:
            from temporal_analyzer import temporal_consistency_score
            cs["temporal"] = temporal_consistency_score(face_paths)
        except Exception as e:
            cs["temporal"] = 0
            components["temporal_error"] = str(e)
        components["temporal"] = {"score": cs["temporal"]}
        step("temporal_done", dict(cs))
        gc.collect()

        # ── Step 5: Lip-sync (numpy + ffmpeg, no ML) ─────────────────────
        step("lipsync")
        try:
            from lipsync_analyzer import lipsync_score
            cs["lipsync"] = lipsync_score(face_paths, video_path)
        except Exception as e:
            cs["lipsync"] = 0
            components["lipsync_error"] = str(e)
        components["lipsync"] = {"score": cs["lipsync"]}
        step("lipsync_done", dict(cs))
        gc.collect()

        # ── Step 6: SPN / PRNU (numpy only) ──────────────────────────────
        step("spn")
        try:
            from spn_analyzer import spn_score
            cs["spn"] = spn_score(frame_paths)
        except Exception as e:
            cs["spn"] = 0
            components["spn_error"] = str(e)
        components["spn"] = {"score": cs["spn"]}
        step("spn_done", dict(cs))
        gc.collect()

        # ── Step 7: Forensic rules (numpy + PIL, no ML) ───────────────────
        step("forensic")
        foren = {"score": 0, "details": {}, "anomalies": []}
        if face_paths:
            try:
                from forensic_rules import run_all_forensic_rules
                foren    = run_all_forensic_rules(face_paths)
                anomalies += foren.get("anomalies", [])
            except Exception as e:
                components["forensic_error"] = str(e)
        cs["forensic"]     = foren.get("score", 0)
        components["forensic"] = foren
        step("forensic_done", dict(cs))
        gc.collect()

        # ── Step 8: Combine all scalar scores ────────────────────────────
        step("combining")
        final = _combine(cs)

        try:
            from meta_classifier import meta_classify
            dec = meta_classify(cs)
            if dec["score_override"] is not None:
                final = dec["score_override"]
            elif final is not None:
                final = min(99, final + dec["boost"])
            if final is not None:
                final = round(final * dec["confidence_adj"], 2)
                final = min(99, max(0, final))
            reason = dec.get("reason", "")
            if reason and reason != "standard weighted average":
                anomalies.append(f"Meta: {reason}")
        except Exception:
            pass

        step("done", dict(cs))

        return {
            "final_score":      round(float(final), 2) if final is not None else None,
            "verdict":          _verdict(final),
            "confidence":       min(99, int(final)) if final else 0,
            "fast_path":        False,
            "timestamp":        datetime.now().isoformat(),
            "video_path":       video_path,
            "components":       components,
            "component_scores": cs,
            "anomalies":        anomalies,
        }

    finally:
        if cleanup and os.path.exists(wdir):
            try:
                shutil.rmtree(wdir)
            except Exception:
                pass
        gc.collect()


def analyze_image(path):
    """Single-image pipeline (no audio/temporal/SPN/lipsync)."""
    from metadata_analyzer import analyze_image_metadata
    from forensic_rules    import run_all_forensic_rules
    from classifier        import classify_face

    meta  = analyze_image_metadata(path)
    foren = run_all_forensic_rules([path])
    try:
        vs = classify_face(path, verbose=False)
    except Exception:
        vs = None

    w = {"visual": 0.60, "forensic": 0.25, "metadata": 0.15}
    s = {"visual": vs, "forensic": foren.get("score", 0), "metadata": meta.get("score", 0)}
    tw = ws = 0.0
    for k, wt in w.items():
        if s[k] is not None:
            ws += s[k] * wt
            tw += wt
    final = round(ws / tw, 2) if tw else None
    return {
        "final_score": final,
        "verdict":     _verdict(final),
        "image_path":  path,
        "components":  {"visual": {"score": vs}, "metadata": meta, "forensic": foren},
        "anomalies":   meta.get("anomalies", []) + foren.get("anomalies", []),
    }
