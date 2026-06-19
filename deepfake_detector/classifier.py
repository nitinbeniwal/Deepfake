"""
classifier.py — Adaptive 3-model ensemble with TTA.

Cascade approach for speed:
  1. Run primary model on all frames.
  2. If score clearly real (<20) or clearly fake (>80) → done.
  3. If uncertain (20-80) → add secondary + tertiary models + TTA.

Models (weighted):
  primary   prithivMLmods/Deep-Fake-Detector-v2-Model  0.40
  secondary dima806/deepfake_vs_real_image_detection    0.35
  tertiary  Wvolf/ViT-Deepfake-Detection                0.25
"""

import threading, statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

CALIBRATION_OFFSET = 0
UNCERTAIN_LO, UNCERTAIN_HI = 20, 80   # range that triggers ensemble

_MODELS = [
    ("prithivMLmods/Deep-Fake-Detector-v2-Model", 0.40),
    ("dima806/deepfake_vs_real_image_detection",   0.35),
    ("Wvolf/ViT-Deepfake-Detection",               0.25),
]
_FAKE = ("fake","deepfake","spoof","synthetic","artificial","generated","ai","manipulat","forg")
_REAL = ("real","genuine","authentic","human","live","bonafide","natural","original")

_pipes: dict = {}
_lock = threading.Lock()

def reset_buffers(): return None


def _get_pipe(model_id):
    if model_id not in _pipes:
        with _lock:
            if model_id not in _pipes:
                from transformers import pipeline
                print(f"Loading: {model_id} ...")
                _pipes[model_id] = pipeline("image-classification", model=model_id)
                print(f"Loaded: {model_id.split('/')[-1]} OK")
    return _pipes[model_id]


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
    return ((1-top["score"]) if any(t in top["label"].lower() for t in _REAL) else top["score"])*100


def _tta(img):
    """4 augmented variants for TTA."""
    from PIL import Image, ImageEnhance
    return [
        img,
        img.transpose(Image.FLIP_LEFT_RIGHT),
        ImageEnhance.Brightness(img).enhance(0.9),
        ImageEnhance.Brightness(img).enhance(1.1),
    ]


def _run_model(model_id, pil_images, batch_size=8):
    """Run one model on list of PIL images. Returns list[float|None]."""
    try:
        pipe = _get_pipe(model_id)
        results = pipe(pil_images, batch_size=batch_size)
        return [_score(r) for r in results]
    except Exception as e:
        print(f"Model {model_id.split('/')[-1]} error: {e}")
        return [None]*len(pil_images)


def _calibrate(s):
    return round(max(0.0, min(100.0, s - CALIBRATION_OFFSET)), 2)


def classify_faces_batch(image_paths, verbose=False):
    """
    Adaptive ensemble. Returns list[float|None] same order as image_paths.
    - Uncertain frames get TTA + secondary/tertiary models.
    - Clear frames (very high or very low) use primary only.
    """
    from PIL import Image
    from collections import defaultdict

    # Load images
    valid, orig_idxs = [], []
    for i, p in enumerate(image_paths):
        try: valid.append(Image.open(p).convert("RGB")); orig_idxs.append(i)
        except Exception: pass

    final = [None]*len(image_paths)
    if not valid: return final

    # --- Stage 1: primary model on all images ---
    primary_id, primary_w = _MODELS[0]
    raw1 = _run_model(primary_id, valid)
    primary_scores = [_calibrate(s) if s is not None else None for s in raw1]

    # Split: clear vs uncertain
    clear_idxs = [i for i, s in enumerate(primary_scores)
                  if s is not None and (s < UNCERTAIN_LO or s > UNCERTAIN_HI)]
    unc_idxs   = [i for i, s in enumerate(primary_scores)
                  if s is None or UNCERTAIN_LO <= s <= UNCERTAIN_HI]

    # Clear → use primary score directly
    for i in clear_idxs:
        final[orig_idxs[i]] = primary_scores[i]
        if verbose: print(f"  [primary] {image_paths[orig_idxs[i]].split('/')[-1]} → {primary_scores[i]:.1f}%")

    if not unc_idxs:
        return final

    # --- Stage 2: uncertain frames → TTA + secondary + tertiary ---
    unc_imgs     = [valid[i] for i in unc_idxs]
    unc_orig_idx = [orig_idxs[i] for i in unc_idxs]

    # Build TTA batch
    aug_batch, aug_map = [], []
    for idx, img in enumerate(unc_imgs):
        for aug in _tta(img):
            aug_batch.append(aug); aug_map.append(idx)

    # Per image per model: list of augmented scores
    img_model_scores = defaultdict(lambda: defaultdict(list))

    # Primary TTA scores (re-run primary on uncertain with TTA)
    primary_tta = _run_model(primary_id, aug_batch)
    for aug_idx, s in enumerate(primary_tta):
        if s is not None:
            img_model_scores[aug_map[aug_idx]][primary_id].append(s)

    # Secondary + tertiary in parallel
    secondary_models = _MODELS[1:]
    with ThreadPoolExecutor(max_workers=len(secondary_models)) as ex:
        futs = {ex.submit(_run_model, mid, aug_batch): (mid, w)
                for mid, w in secondary_models}
        for fut in as_completed(futs):
            mid, _ = futs[fut]
            for aug_idx, s in enumerate(fut.result()):
                if s is not None:
                    img_model_scores[aug_map[aug_idx]][mid].append(s)

    # Weighted ensemble per uncertain image
    for local_idx in range(len(unc_imgs)):
        ws, tw = 0.0, 0.0
        for mid, w in _MODELS:
            augs = img_model_scores[local_idx].get(mid, [])
            if augs:
                ws += statistics.mean(augs) * w; tw += w
        if tw:
            s = _calibrate(ws / tw)
            final[unc_orig_idx[local_idx]] = s
            if verbose:
                print(f"  [ensemble+TTA] {image_paths[unc_orig_idx[local_idx]].split('/')[-1]} → {s:.1f}%")

    return final


def classify_face(image_path, verbose=True):
    """Single image. Uses ensemble for uncertain scores."""
    scores = classify_faces_batch([image_path], verbose=verbose)
    return scores[0]


classify_face_v2 = classify_face
