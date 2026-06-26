"""
calibration.py — single source of truth for the score offset + verdict bands.

Two problems this fixes:

  1. Verdict thresholds were hard-coded in three places with three different
     scales (pipeline FAKE>=85, docstring >=70, audio endpoint >=50). Now every
     caller uses verdict()/get_thresholds() here.

  2. The visual models are uncalibrated — on compressed/real footage they sit
     ~50, so genuine clips read INCONCLUSIVE instead of REAL. CALIBRATION_OFFSET
     was a hard 0 that nobody ever changed. Now the offset lives in
     calibration.json and is learned from operator feedback (see
     record_feedback) so corrections actually move future scores.

State file: calibration.json (next to this module). Safe defaults if absent.
"""

import os, json, threading, statistics
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_STATE_PATH = os.path.join(_HERE, "calibration.json")
_lock = threading.Lock()

# Offset is SUBTRACTED from each visual model score (0..100). Positive offset
# pushes scores down (use when real footage reads too high). Bounded so a noisy
# feedback batch can never flip the whole system.
_OFFSET_MIN, _OFFSET_MAX = -20.0, 50.0

_DEFAULTS = {
    "visual_offset": 0.0,
    "thresholds": {"fake": 85, "likely": 72, "inconclusive": 30},
    "n_feedback": 0,
    "updated": None,
}


def _load() -> dict:
    try:
        with open(_STATE_PATH, encoding="utf-8") as f:
            d = json.load(f)
        # merge over defaults so missing keys never crash callers
        out = dict(_DEFAULTS)
        out.update({k: d[k] for k in d if k in _DEFAULTS})
        out["thresholds"] = {**_DEFAULTS["thresholds"], **(d.get("thresholds") or {})}
        return out
    except Exception:
        return dict(_DEFAULTS)


def _save(d: dict):
    try:
        tmp = _STATE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2)
        os.replace(tmp, _STATE_PATH)
    except Exception:
        pass


def get_visual_offset() -> float:
    return float(_load().get("visual_offset", 0.0))


def get_thresholds() -> dict:
    return _load()["thresholds"]


def verdict(score) -> str:
    """Single verdict mapping used by every pipeline (video/image/audio)."""
    if score is None:
        return "UNKNOWN"
    t = get_thresholds()
    return ("FAKE"         if score >= t["fake"] else
            "LIKELY FAKE"  if score >= t["likely"] else
            "INCONCLUSIVE" if score >= t["inconclusive"] else
            "REAL")


# ── Feedback-driven calibration ───────────────────────────────────────────────

# Map free-text correct_verdict to a target band: True = should read REAL.
_REAL_LABELS = {"REAL"}
_FAKE_LABELS = {"FAKE", "LIKELY FAKE"}


def _visual_of(entry: dict):
    """Best available per-item visual score from a feedback row."""
    cs = entry.get("component_scores") or {}
    v = cs.get("visual")
    if v is None:
        v = entry.get("predicted_score")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def record_feedback(feedback_rows: list) -> dict:
    """
    Recompute the visual offset from ALL feedback collected so far.

    Goal: push genuine (correct_verdict == REAL) clips below the REAL band.
    We take the median pre-offset visual score of REAL-labelled items and set
    the offset so that median lands a margin below the inconclusive threshold.
    EMA-blended with the current offset and clamped, so one odd correction can't
    swing the system. FAKE-labelled items act as a guard: we never push the
    offset so high that their median would drop below the fake line.

    Returns the new calibration state.
    """
    with _lock:
        state = _load()
        thr = state["thresholds"]
        cur = float(state.get("visual_offset", 0.0))

        real_v = [v for e in feedback_rows
                  if (e.get("correct_verdict") in _REAL_LABELS)
                  for v in [_visual_of(e)] if v is not None]
        fake_v = [v for e in feedback_rows
                  if (e.get("correct_verdict") in _FAKE_LABELS)
                  for v in [_visual_of(e)] if v is not None]

        target = cur
        if real_v:
            med_real = statistics.median(real_v)
            margin = 8.0                      # land this far below the REAL band
            # offset must satisfy: med_real - offset <= inconclusive - margin
            desired = med_real - (thr["inconclusive"] - margin)
            if fake_v:
                # ...but keep fake median above the LIKELY line by >= margin
                med_fake = statistics.median(fake_v)
                ceiling = med_fake - (thr["likely"] + margin)
                desired = min(desired, ceiling)
            target = desired

        target = max(_OFFSET_MIN, min(_OFFSET_MAX, target))
        # Confidence-weighted move: with few samples we barely budge; the offset
        # only approaches the target once enough corrections agree. K=5 → 1
        # sample moves ~17% of the way, 5 samples ~50%, 20 samples ~80%.
        n = max(len(real_v), len(fake_v))
        K = 5.0
        alpha = n / (n + K)
        new_offset = round((1 - alpha) * cur + alpha * target, 2)

        state["visual_offset"] = new_offset
        state["n_feedback"] = len(feedback_rows)
        state["updated"] = datetime.now().isoformat()
        _save(state)
        return state
