"""
spn_analyzer.py — SPN/PRNU noise fingerprint analysis.

Every real camera sensor has a unique Photo Response Non-Uniformity (PRNU)
pattern embedded in the noise of every frame. AI-generated video has no
consistent physical sensor — inter-frame noise residuals don't correlate.

Real video : mean inter-frame noise correlation  ~0.08 - 0.25
AI video   : mean inter-frame noise correlation  ~0.00 - 0.04

WhatsApp / social-media re-encoded video: heavy DCT block quantization wipes
out the PRNU signal entirely. Residual variance < 2.0 is a reliable indicator
of this condition — we return None so the signal is excluded from the
weighted average rather than dragging the fake-score toward 0.
"""

import cv2, numpy as np


def _noise_residual(img_bgr, size=(256, 256)):
    """Extract high-frequency noise via Gaussian subtraction."""
    gray    = cv2.resize(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY), size).astype(np.float32)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    return (gray - blurred).flatten()


def spn_score(frame_paths):
    """
    Score 0-100 (higher = more likely AI-generated).
    Returns None when signal is unreliable (< 3 frames or heavy compression).
    """
    residuals, variances = [], []
    for p in frame_paths[:20]:
        img = cv2.imread(p)
        if img is not None:
            r = _noise_residual(img)
            residuals.append(r)
            variances.append(float(np.var(r)))

    if len(residuals) < 3:
        return None  # insufficient frames — no signal

    # Heavily compressed video (WhatsApp, Telegram, social-media re-encode) has
    # quantization that destroys the sensor PRNU pattern.  Residual variance < 2.0
    # means the "noise" is uniform DCT block artifacts — not usable for PRNU.
    mean_var = float(np.mean(variances))
    if mean_var < 2.0:
        return None  # compression destroyed PRNU — exclude from ensemble

    # Compute all pairwise correlations (upper-triangle only)
    mat   = np.corrcoef(residuals)
    idx   = np.triu_indices_from(mat, k=1)
    pairs = mat[idx]
    mean_corr = float(np.mean(pairs))

    # Mapping:
    # real camera corr >= 0.08 → score near 0
    # AI-generated corr <= 0.02 → score near 80-100
    if mean_corr >= 0.08:      score = 0.0
    elif mean_corr >= 0.04:    score = (0.08 - mean_corr) / 0.04 * 40
    elif mean_corr >= 0.00:    score = 40 + (0.04 - mean_corr) / 0.04 * 40
    else:                       score = min(100, 80 + abs(mean_corr) * 200)

    return round(float(score), 1)
