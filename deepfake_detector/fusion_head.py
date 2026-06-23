"""
fusion_head.py — learned fusion over the per-signal scores.

Replaces the hand-tuned weighted average in pipeline._combine() with a model
LEARNED from labeled data (logistic regression by default, XGBoost optional).
This is the "/btw" fusion idea, done the honest way:

  - Inference here is pure-numpy (logistic) — no sklearn/xgboost needed to RUN,
    only to TRAIN (train_fusion.py). Keeps the server light.
  - If no trained model file exists, fuse() returns None and the pipeline falls
    back to the existing weighted average. So shipping this changes NOTHING until
    you actually train it on real labeled clips. No new runtime errors.

State file: fusion_model.json (next to this module), written by train_fusion.py:
  {
    "type": "logistic",
    "features": ["visual","audio","temporal","frequency","forensic","metadata"],
    "mean":   [...],   # standardization (per feature)
    "std":    [...],
    "coef":   [...],   # logistic weights
    "intercept": 0.0,
    "missing_fill": 50.0   # value used when a signal is absent
  }
"""

import os, json, threading, math

_HERE = os.path.dirname(os.path.abspath(__file__))
_MODEL_PATH = os.path.join(_HERE, "fusion_model.json")
_lock = threading.Lock()

# Canonical feature order. train_fusion.py MUST use the same list.
FEATURES = ["visual", "audio", "temporal", "frequency", "forensic", "metadata"]

_cache = {"mtime": None, "model": None}


def _load():
    """Load + cache the fusion model, reloading when the file changes."""
    try:
        mtime = os.path.getmtime(_MODEL_PATH)
    except OSError:
        _cache["mtime"], _cache["model"] = None, None
        return None
    if _cache["mtime"] == mtime and _cache["model"] is not None:
        return _cache["model"]
    with _lock:
        try:
            with open(_MODEL_PATH, encoding="utf-8") as f:
                m = json.load(f)
        except Exception:
            m = None
        _cache["mtime"], _cache["model"] = mtime, m
        return m


def is_trained() -> bool:
    return _load() is not None


def _vec(component_scores: dict, model: dict):
    fill = model.get("missing_fill", 50.0)
    feats = model.get("features", FEATURES)
    return [float(component_scores.get(k) if component_scores.get(k) is not None else fill)
            for k in feats]


def fuse(component_scores: dict):
    """
    Return a fused fake-probability score 0-100, or None if no model is trained
    (caller then falls back to the weighted average).

    Only "logistic" is supported for in-process inference. An XGBoost model
    trained by train_fusion.py is exported AS logistic-equivalent coefficients
    only when linear; otherwise train_fusion.py refuses and keeps logistic, so
    this stays dependency-free at serve time.
    """
    model = _load()
    if not model or model.get("type") != "logistic":
        return None
    try:
        x = _vec(component_scores, model)
        mean = model["mean"]; std = model["std"]; coef = model["coef"]
        b = model.get("intercept", 0.0)
        z = b
        for xi, mi, si, ci in zip(x, mean, std, coef):
            si = si if si and abs(si) > 1e-9 else 1.0
            z += ci * ((xi - mi) / si)
        prob = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))
        return round(prob * 100.0, 2)
    except Exception:
        return None
