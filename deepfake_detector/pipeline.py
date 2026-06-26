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

# Keep the 7 visual models resident in RAM between uploads. Reloading every model
# from disk on every analysis was the main reason a second upload still took ~2
# min. With warm models only the FIRST upload pays the load cost. Disabled under
# LOW_MEM (e.g. 512MB Railway) where all 7 resident would OOM — there we keep the
# load/unload-each-model behaviour. Override with KEEP_MODELS_WARM=0.
_KEEP_WARM = (not _LOW_MEM) and os.environ.get("KEEP_MODELS_WARM", "1") != "0"

# Visual (FF++ CNNs + ViTs) is the trusted signal. SPN and LIP-SYNC are DISABLED
# (weight 0): on compressed video (WhatsApp/re-encode) they invert — measured on
# labeled clips, real footage scored spn=80 / lipsync=92 while fakes scored ~0,
# i.e. they fire on the genuine clip. They still run for display but do not affect
# the score. Temporal is the only heuristic that separated correctly, kept small.
W = {
    "visual":    0.62,   # the only trusted signal — give it the most share
    "audio":     0.06,   # cut: voice-clone model flags reel MUSIC/processed audio as fake
    "temporal":  0.08,   # cut: fires high on compressed REAL video (inversion)
    "lipsync":   0.00,   # disabled — inverted on compressed video
    "spn":       0.00,   # disabled — inverted on compressed video
    "frequency": 0.05,   # texture + spectral analysis (numpy, no ML)
    "forensic":  0.08,
    "metadata":  0.02,   # cut: WhatsApp strips metadata on ALL clips → false suspicion
}

# ── Focus modes ───────────────────────────────────────────────────────────────
# The operator can preview the clip and tell us where the manipulation is.
# Focusing skips the expensive signals that don't matter (huge CPU saving) and
# up-weights the signal that does (cleaner verdict, fewer false highs from noisy
# heuristics). Metadata always runs — it is < 1s and free.
#
#   full    everything (default)
#   visual  face / face-swap — visual models + face forensics, skip audio model
#   audio   voice clone — audio model only, skip all frame/face work
#   quick   fast triage — visual models only, skip slow heuristics
FOCUS_STEPS = {
    "full":   {"visual", "audio", "temporal", "lipsync", "spn", "frequency", "forensic"},
    "visual": {"visual", "temporal", "spn", "frequency", "forensic"},
    "audio":  {"audio"},
    "quick":  {"visual"},
}
# Multiplier applied to the focused signal's weight so the operator's hint
# steers (but never fully silences) the verdict.
FOCUS_BOOST = {
    "full":   {},
    "visual": {"visual": 1.6},
    "audio":  {"audio": 1.0},
    "quick":  {"visual": 1.0},
}


def _normalize_focus(focus):
    f = (focus or "full").strip().lower()
    return f if f in FOCUS_STEPS else "full"


def _agg_frames(scores):
    """
    Aggregate per-frame fake scores for one model.

    Plain mean dilutes localized manipulation (deepfakes often corrupt only a
    subset of frames). We blend the overall mean with the mean of the top 40%
    of frames — emphasizing fake evidence while staying robust to single
    outliers (which would cause false positives on real video).
    """
    if not scores:
        return None
    s = sorted(scores, reverse=True)
    k = max(1, int(len(s) * 0.4))
    top_mean = sum(s[:k]) / k
    mean = sum(s) / len(s)
    return round(0.45 * mean + 0.55 * top_mean, 2)


def _verdict(s):
    # Single source of truth for verdict bands lives in calibration.py so the
    # video / image / audio pipelines (and the audio endpoint) never drift apart.
    from calibration import verdict as _v
    return _v(s)


def _combine(cs, focus="full"):
    # When metadata is stripped (WhatsApp/re-encode), redistribute weight to forensic+temporal
    meta = cs.get("metadata") or 0
    wts  = dict(W)
    if meta < 5:
        wts["forensic"] = round(W["forensic"] + 0.02, 3)
        wts["temporal"] = round(W["temporal"] + 0.01, 3)
        wts["metadata"] = 0.0
    # Apply focus boost to the signal the operator flagged.
    for k, mult in FOCUS_BOOST.get(_normalize_focus(focus), {}).items():
        if k in wts:
            wts[k] = round(wts[k] * mult, 4)
    tw = ws = 0.0
    for k, wt in wts.items():
        s = cs.get(k)
        if s is not None:
            ws += s * wt
            tw += wt
    return round(ws / tw, 2) if tw else None


def _unload_hf(model_id):
    """Unload a model from classifier cache and free RAM.

    No-op when _KEEP_WARM: the model stays cached in classifier._pipes (or the
    timm wrapper globals) so the next upload reuses it instead of reloading.
    """
    if _KEEP_WARM:
        return
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


def analyze_video(video_path, cleanup=True, on_stage=None, focus="full"):
    """
    Fully sequential pipeline.
    on_stage(stage_name, partial_scores_dict) is called after each step —
    use it to push progress to the job dict for live polling.

    focus: "full" | "visual" | "audio" | "quick" — restricts which signals run
    so the operator can speed up and sharpen analysis when they already know
    where the manipulation is (see FOCUS_STEPS).

    Returns dict with final_score, verdict, confidence, component_scores, anomalies.
    """
    focus  = _normalize_focus(focus)
    try:
        from classifier import refresh_calibration
        refresh_calibration()   # pick up any feedback-learned offset
    except Exception:
        pass
    steps_on = FOCUS_STEPS[focus]
    need_faces = bool(steps_on & {"visual", "temporal", "lipsync", "spn", "frequency", "forensic"})

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
        face_paths  = []
        frame_paths = []
        if need_faces:
            step("extraction")
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
        vis_score = None
        if "visual" in steps_on and face_paths:
            step("visual")
            try:
                from classifier import _MODELS, _get_pipe, _score as _cls_score, _calibrate

                model_accum = {}  # model_id → (agg_score, weight)

                # Model identities are not exposed to the UI — only "Model N".
                for _i, (model_id, weight, _stage) in enumerate(_MODELS, 1):
                    step(f"visual:Model {_i}", dict(cs))
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
                                    model_accum[model_id] = (_agg_frames(valid), weight)
                        del pils
                    except Exception as ex:
                        print(f"Visual Model {_i} error: {ex}")
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

        if "visual" in steps_on:
            cs["visual"] = vis_score
            components["visual"] = {"score": vis_score, "face_count": len(face_paths)}
            step("visual_done", dict(cs))
        gc.collect()

        # ── Step 3: Audio (skip in LOW_MEM — model is ~300MB) ────────────
        if "audio" in steps_on and not _LOW_MEM:
            step("audio")
            aud_score = None
            try:
                from audio_classifier import classify_audio
                aud_score = classify_audio(video_path)
                if not _KEEP_WARM:
                    # Unload audio model from RAM
                    import audio_classifier as _ac
                    _ac._pipe = None
            except Exception as e:
                components["audio_error"] = str(e)
            cs["audio"] = aud_score
            components["audio"] = {"score": aud_score}
            step("audio_done", dict(cs))
            gc.collect()
        elif _LOW_MEM and "audio" in steps_on:
            cs["audio"] = None
            components["audio"] = {"score": None, "skipped": "LOW_MEM"}

        # ── Step 4: Temporal consistency (numpy only) ─────────────────────
        if "temporal" in steps_on:
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
        if "lipsync" in steps_on:
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
        if "spn" in steps_on:
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

        # ── Step 6b: Frequency / texture analysis (numpy + cv2, no ML) ────
        if "frequency" in steps_on:
            step("frequency")
            try:
                from frequency_analyzer import frequency_score
                cs["frequency"] = frequency_score(face_paths)
            except Exception as e:
                cs["frequency"] = None
                components["frequency_error"] = str(e)
            components["frequency"] = {"score": cs["frequency"]}
            step("frequency_done", dict(cs))
            gc.collect()

        # ── Step 7: Forensic rules (numpy + PIL, no ML) ───────────────────
        if "forensic" in steps_on:
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
        # Learned fusion head takes over IF it has been trained on labeled data
        # (fusion_model.json present); otherwise fall back to the weighted average.
        fused = None
        try:
            from fusion_head import fuse as _fuse
            fused = _fuse(cs)
        except Exception:
            fused = None
        if fused is not None:
            final = fused
            components["fusion"] = {"score": fused, "source": "learned"}
        else:
            final = _combine(cs, focus)
            components["fusion"] = {"score": final, "source": "weighted_average"}

        try:
            from meta_classifier import meta_classify
            # Exclude disabled (inverted-on-compression) signals from meta rules too,
            # otherwise the SPN/temporal "physical override" re-introduces false fakes.
            cs_meta = {k: v for k, v in cs.items() if W.get(k, 0) > 0}
            dec = meta_classify(cs_meta)
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
            "focus":            focus,
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


def analyze_image(path, cleanup=True, on_stage=None):
    """
    Single-image pipeline: face detection → visual models → forensic rules → EXIF.
    Audio / temporal / lipsync / SPN skipped (no video stream).
    on_stage(stage, partial) mirrors analyze_video for UI progress.
    """
    import threading
    from datetime import datetime
    from PIL import Image as _PIL, ExifTags as _EXIF

    def step(name, partial=None):
        if on_stage:
            try: on_stage(name, partial or {})
            except Exception: pass

    try:
        from classifier import refresh_calibration
        refresh_calibration()
    except Exception:
        pass

    wdir = os.path.abspath(f"_pipe_{os.getpid()}_{threading.get_ident()}_img")
    fd   = os.path.join(wdir, "faces")
    os.makedirs(fd, exist_ok=True)
    cs = {}; components = {}; anomalies = []

    try:
        # ── Step 0: EXIF metadata ────────────────────────────────────────────
        step("metadata")
        try:
            exif_data = {}; anom_meta = []
            img = _PIL.open(path).convert("RGB")
            try:
                raw_exif = img._getexif() or {}
                for tag_id, val in raw_exif.items():
                    tag = _EXIF.TAGS.get(tag_id, str(tag_id))
                    exif_data[str(tag)] = str(val)[:120]
            except Exception:
                pass
            if os.path.splitext(path)[1].lower() in ('.jpg', '.jpeg') and not exif_data:
                anom_meta.append("No EXIF in JPEG — possible AI-generated or re-saved image")
            if "Software" in exif_data and any(k in exif_data["Software"].lower()
                                               for k in ("midjourney","stable diffusion","dalle","firefly")):
                anom_meta.append(f"AI generator signature in EXIF Software: {exif_data['Software']}")
            meta = {"score": 25 if anom_meta else 5, "anomalies": anom_meta, "exif": exif_data}
        except Exception as e:
            meta = {"score": 0, "anomalies": [], "error": str(e)}
        cs["metadata"] = meta.get("score", 0)
        components["metadata"] = meta
        anomalies += meta.get("anomalies", [])
        step("metadata_done", dict(cs))
        gc.collect()

        # ── Step 1: Face detection ───────────────────────────────────────────
        step("extraction")
        face_paths = []
        try:
            from face_detector import detect_face
            fp = detect_face(path, fd)
            if fp:
                face_paths = [fp]
        except Exception as e:
            components["extraction_error"] = str(e)
        if not face_paths:
            # No face detected — use full image resized as proxy
            try:
                fp2 = os.path.join(fd, "full.jpg")
                _PIL.open(path).convert("RGB").resize((299, 299)).save(fp2)
                face_paths = [fp2]
            except Exception:
                pass
        step("extraction_done", dict(cs))
        gc.collect()

        # ── Step 2: Visual models (same as video pipeline) ───────────────────
        step("visual")
        vis_score = None
        if face_paths:
            try:
                from classifier import _MODELS, _get_pipe, _score as _cls_score, _calibrate
                model_accum = {}
                for _i, (model_id, weight, _s) in enumerate(_MODELS, 1):
                    step(f"visual:Model {_i}", dict(cs))
                    try:
                        pils = []
                        for p in face_paths:
                            try: pils.append(_PIL.open(p).convert("RGB"))
                            except Exception: pass
                        if pils:
                            pipe = _get_pipe(model_id)
                            if pipe is not None:
                                raw    = pipe(pils, batch_size=4)
                                scores = [_calibrate(_cls_score(r)) for r in raw]
                                valid  = [s for s in scores if s is not None]
                                if valid:
                                    model_accum[model_id] = (_agg_frames(valid), weight)
                        del pils
                    except Exception as ex:
                        print(f"Visual Model {_i} error: {ex}")
                    finally:
                        _unload_hf(model_id)
                if model_accum:
                    tw = ws = 0.0
                    for _, (sc, wt) in model_accum.items():
                        ws += sc * wt; tw += wt
                    if tw: vis_score = round(ws / tw, 2)
                del model_accum
            except Exception as e:
                components["visual_error"] = str(e)
        cs["visual"] = vis_score
        components["visual"] = {"score": vis_score, "face_count": len(face_paths)}
        step("visual_done", dict(cs))
        gc.collect()

        # ── Step 3: Forensic rules ───────────────────────────────────────────
        step("forensic")
        foren = {"score": 0, "details": {}, "anomalies": []}
        if face_paths:
            try:
                from forensic_rules import run_all_forensic_rules
                foren = run_all_forensic_rules(face_paths)
                anomalies += foren.get("anomalies", [])
            except Exception as e:
                components["forensic_error"] = str(e)
        cs["forensic"] = foren.get("score", 0)
        components["forensic"] = foren
        step("forensic_done", dict(cs))
        gc.collect()

        # ── Step 4: Combine ──────────────────────────────────────────────────
        step("combining")
        w_img = {"visual": 0.72, "forensic": 0.20, "metadata": 0.08}
        tw = ws = 0.0
        for k, wt in w_img.items():
            s = cs.get(k)
            if s is not None:
                ws += s * wt; tw += wt
        final = round(ws / tw, 2) if tw else None
        step("done", dict(cs))

        return {
            "final_score":      round(float(final), 2) if final is not None else None,
            "verdict":          _verdict(final),
            "confidence":       min(99, int(final)) if final else 0,
            "fast_path":        False,
            "focus":            "image",
            "media_type":       "image",
            "timestamp":        datetime.now().isoformat(),
            "video_path":       path,
            "components":       components,
            "component_scores": cs,
            "anomalies":        anomalies,
        }
    finally:
        if cleanup and os.path.exists(wdir):
            try: shutil.rmtree(wdir)
            except Exception: pass
        gc.collect()


def analyze_audio(path, cleanup=True, on_stage=None):
    """
    Audio-only pipeline: voice clone / TTS detection.
    Visual / temporal / forensic skipped (no video frames).
    """
    from datetime import datetime

    def step(name, partial=None):
        if on_stage:
            try: on_stage(name, partial or {})
            except Exception: pass

    cs = {}; components = {}; anomalies = []

    try:
        # ── Step 0: Metadata (ffprobe / mutagen) ────────────────────────────
        step("metadata")
        try:
            from metadata_analyzer import analyze_video_metadata
            meta = analyze_video_metadata(path)
        except Exception as e:
            meta = {"score": 0, "anomalies": [], "error": str(e)}
        cs["metadata"] = meta.get("score", 0)
        components["metadata"] = meta
        anomalies += meta.get("anomalies", [])
        step("metadata_done", dict(cs))

        # ── Step 1: Audio classifier (voice clone / TTS) ────────────────────
        step("audio")
        aud_score = None
        try:
            from audio_classifier import classify_audio
            aud_score = classify_audio(path)
            if not _KEEP_WARM:
                import audio_classifier as _ac
                _ac._pipe = None
        except Exception as e:
            components["audio_error"] = str(e)
        cs["audio"] = aud_score
        components["audio"] = {"score": aud_score}
        step("audio_done", dict(cs))
        gc.collect()

        # ── Step 2: Combine ──────────────────────────────────────────────────
        step("combining")
        w_aud = {"audio": 0.90, "metadata": 0.10}
        tw = ws = 0.0
        for k, wt in w_aud.items():
            s = cs.get(k)
            if s is not None:
                ws += s * wt; tw += wt
        final = round(ws / tw, 2) if tw else None
        step("done", dict(cs))

        return {
            "final_score":      round(float(final), 2) if final is not None else None,
            "verdict":          _verdict(final),
            "confidence":       min(99, int(final)) if final else 0,
            "fast_path":        False,
            "focus":            "audio",
            "media_type":       "audio",
            "timestamp":        datetime.now().isoformat(),
            "video_path":       path,
            "components":       components,
            "component_scores": cs,
            "anomalies":        anomalies,
        }
    finally:
        gc.collect()
