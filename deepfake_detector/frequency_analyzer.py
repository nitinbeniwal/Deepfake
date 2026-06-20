"""
frequency_analyzer.py — Texture and spectral analysis for deepfake detection.

Deepfake faces, even after WhatsApp/social-media compression, retain detectable
artifacts in their local texture statistics and high-frequency spectral content:

1. Over-smooth skin: AI face generation models smooth out natural skin micro-texture.
   Real faces have richer local standard deviation (local_std ~12-25).
   AI faces tend to be either over-smooth (<8) or unnaturally sharp.

2. Spectral slope: real camera images follow a steep ~1/f² power spectrum.
   GAN/diffusion faces have flatter spectrum (slope closer to -1 than -2.5).

3. Inter-face spectral variance: in a real video every frame of the same person
   has consistent spectral properties. Deepfakes that composite faces from a
   different source often show frame-to-frame spectral inconsistency.

Returns None when signal is unreliable (< 3 face crops available).
"""

import cv2
import numpy as np


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _load_gray(path, size=224):
    img = cv2.imread(path)
    if img is None:
        return None
    gray = cv2.cvtColor(cv2.resize(img, (size, size)), cv2.COLOR_BGR2GRAY)
    return gray.astype(np.float32)


def _local_std(gray_float, ksize=16):
    """Mean of local standard deviations in non-overlapping ksize×ksize patches."""
    h, w = gray_float.shape
    stds = []
    for y in range(0, h - ksize + 1, ksize):
        for x in range(0, w - ksize + 1, ksize):
            patch = gray_float[y:y+ksize, x:x+ksize]
            stds.append(float(np.std(patch)))
    return float(np.mean(stds)) if stds else None


def _spectral_slope(gray_float):
    """
    Estimate the power-law exponent β of the radial power spectrum (P ∝ f^-β).
    Real images:  β ≈ 2.0–3.5 (steep roll-off)
    AI/GAN faces: β ≈ 1.0–2.0 (flatter spectrum)
    Returns the slope (negative float), or None on failure.
    """
    f = np.fft.fft2(gray_float / 255.0)
    fshift = np.fft.fftshift(f)
    power = np.abs(fshift) ** 2 + 1e-10

    h, w = power.shape
    cy, cx = h // 2, w // 2
    y, x = np.mgrid[0:h, 0:w]
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2).astype(int)
    r = np.clip(r, 1, min(cy, cx) - 1)

    tbin = np.bincount(r.ravel(), power.ravel())
    nr   = np.bincount(r.ravel())
    with np.errstate(divide='ignore', invalid='ignore'):
        radial = np.where(nr > 0, tbin / nr, 1e-10)

    n = len(radial)
    use = max(1, n // 8)  # use low-to-mid frequency range only
    freqs = np.arange(1, use + 1, dtype=np.float32)
    psd   = radial[1:use + 1]

    if np.any(psd <= 0) or len(freqs) < 4:
        return None

    try:
        coef = np.polyfit(np.log(freqs), np.log(psd), 1)
        return float(coef[0])
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────

def frequency_score(face_paths):
    """
    Score 0–100 (higher = more likely deepfake/AI-generated).
    Returns None when < 3 usable face crops are available.
    """
    local_stds = []
    slopes     = []

    for p in face_paths[:15]:
        gray = _load_gray(p)
        if gray is None:
            continue

        ls = _local_std(gray)
        if ls is not None:
            local_stds.append(ls)

        sl = _spectral_slope(gray)
        if sl is not None:
            slopes.append(sl)

    if len(local_stds) < 3:
        return None

    score = 0.0

    # ── Feature 1: skin texture smoothness ────────────────────
    # Over-smooth skin (AI faces): local_std < 8 → strong fake signal
    # Real faces: local_std typically 12–25
    mean_std = float(np.mean(local_stds))
    if mean_std < 6.0:
        score += 35
    elif mean_std < 9.0:
        score += 20
    elif mean_std < 12.0:
        score += 8
    elif mean_std > 40.0:   # unnaturally noisy (some GAN artifacts)
        score += 12

    # ── Feature 2: spectral slope ─────────────────────────────
    # Flatter spectrum (slope > -2.0) = AI generation signal
    # Very steep (< -3.5) = over-processed / HDR → mild signal
    if slopes:
        mean_slope = float(np.mean(slopes))
        if mean_slope > -1.3:
            score += 40
        elif mean_slope > -1.8:
            score += 25
        elif mean_slope > -2.2:
            score += 10
        elif mean_slope < -3.8:
            score += 8   # over-smooth / sharpened

    # ── Feature 3: frame-to-frame spectral consistency ────────
    # Deepfake compositing from different source: higher variance
    if len(slopes) >= 4:
        slope_std = float(np.std(slopes))
        if slope_std > 0.6:
            score += 18
        elif slope_std > 0.35:
            score += 8

    return round(min(100.0, score), 1)
