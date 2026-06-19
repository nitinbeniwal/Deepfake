"""
classifier.py — Adaptive 5-model ensemble with TTA.

3-stage cascade for maximum accuracy with controlled speed:
  Stage 1: Primary model fast-screens all frames.
  Stage 2: Uncertain frames (20-80%) → TTA + 2 secondary models in parallel.
  Stage 3: Still uncertain after Stage 2 → run 2 specialist models.

Models (weighted):
  primary    prithivMLmods/Deep-Fake-Detector-v2-Model     0.30
  secondary1 dima806/deepfake_vs_real_image_detection       0.25
  secondary2 Wvolf/ViT-Deepfake-Detection                  0.20
  specialist1 prithivMLmods/Deepfake-Detection-Exp-02-Model 0.15
  specialist2 haywoodsloan/autotrain-deepfake-detection     0.10

Specialist models only activate for genuinely uncertain frames.
This adds accuracy without proportional latency increase.
"""

import os, threading, statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

CALIBRATION_OFFSET = 0
_LOW_MEM = os.environ.get("LOW_MEM", "0") == "1"  # Railway free tier: 1 model only
UNCERTAIN_LO, UNCERTAIN_HI   = 20, 80   # triggers Stage 2
STILL_UNCERTAIN_LO, STILL_HI = 35, 65   # triggers Stage 3 (tighter band)

_MODELS = [
    # (model_id, weight, stage)
    ("prithivMLmods/Deep-Fake-Detector-v2-Model",      0.30, 1),
    ("dima806/deepfake_vs_real_image_detection",        0.25, 2),
    ("Wvolf/ViT-Deepfake-Detection",                   0.20, 2),
    ("prithivMLmods/Deepfake-Detection-Exp-02-Model",  0.15, 3),
    ("haywoodsloan/autotrain-deepfake-detection",       0.10, 3),
]

_FAKE = ("fake","deepfake","spoof","synthetic","artificial","generated",
         "ai","manipulat","forg","altered","tamper")
_REAL = ("real","genuine","authentic","human","live","bonafide",
         "natural","original","unaltered")

_pipes: dict = {}
_lock = threading.Lock()

def reset_buffers(): return None


def _get_pipe(model_id):
    if model_id not in _pipes:
        with _lock:
            if model_id not in _pipes:
                from transformers import pipeline
                print(f"Loading: {model_id.split('/')[-1]} ...")
                try:
                    _pipes[model_id] = pipeline("image-classification", model=model_id)
                    print(f"Loaded:  {model_id.split('/')[-1]} OK")
                except Exception as e:
                    print(f"SKIP:    {model_id.split('/')[-1]} — {e}")
                    _pipes[model_id] = None
    return _pipes.get(model_id)


def _score(results):
    fp = rp = None
    for r in results:
        lbl = r["label"].strip().lower()
        is_f = any(t in lbl for t in _FAKE) or lbl in ("label_1","1")
        is_r = any(t in lbl for t in _REAL) or lbl in ("label_0","0")
        if is_f and not is_r: fp = max(fp, r["score"]) if fp else r["score"]
        elif is_r and not is_f: rp = max(rp, r["score"]) if rp else r["score"]
    if fp: return fp * 100
    if rp: return (1 - rp) * 100
    top = max(results, key=lambda r: r["score"])
    return ((1 - top["score"]) if any(t in top["label"].lower() for t in _REAL) else top["score"]) * 100


def _tta(img):
    from PIL import Image, ImageEnhance
    return [
        img,
        img.transpose(Image.FLIP_LEFT_RIGHT),
        ImageEnhance.Brightness(img).enhance(0.85),
        ImageEnhance.Brightness(img).enhance(1.15),
        img.rotate(3),
        img.rotate(-3),
    ]


def _run_model(model_id, pil_images, batch_size=8):
    pipe = _get_pipe(model_id)
    if pipe is None:
        return [None] * len(pil_images)
    try:
        results = pipe(pil_images, batch_size=batch_size)
        return [_score(r) for r in results]
    except Exception as e:
        print(f"Model {model_id.split('/')[-1]} error: {e}")
        return [None] * len(pil_images)


def _run_and_unload(model_id, pil_images, batch_size=8):
    """Load, run, immediately unload model to free RAM. For sequential LOW_MEM mode."""
    import gc
    pipe = _get_pipe(model_id)
    if pipe is None:
        return [None] * len(pil_images)
    try:
        results = pipe(pil_images, batch_size=batch_size)
        return [_score(r) for r in results]
    except Exception as e:
        print(f"Model {model_id.split('/')[-1]} error: {e}")
        return [None] * len(pil_images)
    finally:
        _pipes.pop(model_id, None)
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


def _classify_sequential(valid, orig_idxs, image_paths):
    """All 5 models, one at a time. Unloads each before loading next. Safe on 512MB RAM."""
    import gc
    final = [None] * len(image_paths)
    model_results = {}  # model_id -> list[float|None] for valid images

    for model_id, weight, stage in _MODELS:
        print(f"[sequential] {model_id.split('/')[-1]} ...")
        scores = _run_and_unload(model_id, valid)
        model_results[model_id] = [_calibrate(s) for s in scores]
        gc.collect()

    for i, orig_i in enumerate(orig_idxs):
        tw = ws = 0.0
        for model_id, weight, _ in _MODELS:
            s = model_results.get(model_id, [None] * len(valid))
            if i < len(s) and s[i] is not None:
                ws += s[i] * weight
                tw += weight
        if tw:
            final[orig_i] = _calibrate(ws / tw)

    return final


def _calibrate(s):
    if s is None: return None
    return round(max(0.0, min(100.0, s - CALIBRATION_OFFSET)), 2)


def _weighted_mean(score_map):
    """score_map: {model_id: [scores]}. Returns per-image weighted mean."""
    valid_models = [(mid, w, stage) for mid, w, stage in _MODELS
                    if mid in score_map and score_map[mid]]
    if not valid_models:
        return None
    tw = ws = 0.0
    for mid, w, _ in valid_models:
        s = score_map[mid]
        if s is not None:
            ws += statistics.mean(s if isinstance(s, list) else [s]) * w
            tw += w
    return round(ws / tw, 2) if tw else None


def classify_faces_batch(image_paths, verbose=False):
    """
    In LOW_MEM mode: all 5 models run sequentially, each unloaded before next loads.
    Normal mode: 3-stage adaptive cascade with TTA.
    Returns list[float|None] same order as image_paths.
    """
    from PIL import Image
    from collections import defaultdict

    valid, orig_idxs = [], []
    for i, p in enumerate(image_paths):
        try:
            valid.append(Image.open(p).convert("RGB"))
            orig_idxs.append(i)
        except Exception:
            pass

    final = [None] * len(image_paths)
    if not valid:
        return final

    # Sequential mode: all 5 models, one at a time, safe on 512MB
    if _LOW_MEM:
        return _classify_sequential(valid, orig_idxs, image_paths)

    primary_id = _MODELS[0][0]

    # ── Stage 1: primary on all images ─────────────────────────────────────
    raw1 = _run_model(primary_id, valid)
    primary_scores = [_calibrate(s) for s in raw1]

    clear_idxs = [i for i, s in enumerate(primary_scores)
                  if s is not None and (s < UNCERTAIN_LO or s > UNCERTAIN_HI)]
    unc_idxs   = [i for i, s in enumerate(primary_scores)
                  if s is None or UNCERTAIN_LO <= s <= UNCERTAIN_HI]

    for i in clear_idxs:
        final[orig_idxs[i]] = primary_scores[i]

    if not unc_idxs:
        return final

    # ── Stage 2: uncertain → TTA + secondary models ─────────────────────────
    unc_imgs     = [valid[i] for i in unc_idxs]
    unc_orig_idx = [orig_idxs[i] for i in unc_idxs]

    aug_batch, aug_map = [], []
    for idx, img in enumerate(unc_imgs):
        for aug in _tta(img):
            aug_batch.append(aug)
            aug_map.append(idx)

    img_scores = defaultdict(lambda: defaultdict(list))

    # Primary TTA on uncertain
    for aug_idx, s in enumerate(_run_model(primary_id, aug_batch)):
        if s is not None:
            img_scores[aug_map[aug_idx]][primary_id].append(s)

    # Stage-2 models in parallel
    stage2_models = [(mid, w) for mid, w, stage in _MODELS if stage == 2]
    with ThreadPoolExecutor(max_workers=len(stage2_models)) as ex:
        futs = {ex.submit(_run_model, mid, aug_batch): (mid, w)
                for mid, w in stage2_models}
        for fut in as_completed(futs):
            mid, _ = futs[fut]
            for aug_idx, s in enumerate(fut.result()):
                if s is not None:
                    img_scores[aug_map[aug_idx]][mid].append(s)

    # Compute Stage 2 scores
    stage2_results = []
    for local_idx in range(len(unc_imgs)):
        tw = ws = 0.0
        for mid, w, _ in _MODELS[:3]:
            augs = img_scores[local_idx].get(mid, [])
            if augs:
                ws += statistics.mean(augs) * w
                tw += w
        stage2_results.append(_calibrate(ws / tw) if tw else None)

    # ── Stage 3: still uncertain after Stage 2 → specialist models ──────────
    still_unc = [i for i, s in enumerate(stage2_results)
                 if s is None or STILL_UNCERTAIN_LO <= s <= STILL_HI]

    if still_unc:
        su_imgs     = [unc_imgs[i] for i in still_unc]
        su_aug, su_map = [], []
        for idx, img in enumerate(su_imgs):
            for aug in _tta(img):
                su_aug.append(aug)
                su_map.append(idx)

        stage3_models = [(mid, w) for mid, w, stage in _MODELS if stage == 3]
        spec_scores = defaultdict(lambda: defaultdict(list))

        with ThreadPoolExecutor(max_workers=len(stage3_models)) as ex:
            futs = {ex.submit(_run_model, mid, su_aug): (mid, w)
                    for mid, w in stage3_models}
            for fut in as_completed(futs):
                mid, _ = futs[fut]
                for aug_idx, s in enumerate(fut.result()):
                    if s is not None:
                        spec_scores[su_map[aug_idx]][mid].append(s)

        for su_local, local_idx in enumerate(still_unc):
            # Combine all 5 models for final uncertain score
            tw = ws = 0.0
            for mid, w, _ in _MODELS:
                src = img_scores[local_idx] if _ < 3 else spec_scores[su_local]
                augs = src.get(mid, []) if isinstance(src, dict) else []
                if augs:
                    ws += statistics.mean(augs) * w
                    tw += w
            if tw:
                stage2_results[local_idx] = _calibrate(ws / tw)

    # Write Stage 2/3 results
    for local_idx in range(len(unc_imgs)):
        s = stage2_results[local_idx]
        final[unc_orig_idx[local_idx]] = s
        if verbose and s is not None:
            print(f"  [ensemble] {image_paths[unc_orig_idx[local_idx]].split('/')[-1]} → {s:.1f}%")

    return final


def classify_face(image_path, verbose=True):
    scores = classify_faces_batch([image_path], verbose=verbose)
    return scores[0]


classify_face_v2 = classify_face
