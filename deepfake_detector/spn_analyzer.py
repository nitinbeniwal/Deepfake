"""
spn_analyzer.py — SPN/PRNU noise fingerprint analysis.

Every real camera sensor has a unique Photo Response Non-Uniformity (PRNU)
pattern embedded in the noise of every frame. AI-generated video has no
consistent physical sensor — inter-frame noise residuals don't correlate.

Real video : mean inter-frame noise correlation  ~0.08 - 0.25
AI video   : mean inter-frame noise correlation  ~0.00 - 0.04
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
    Needs at least 5 frames for a meaningful result.
    """
    residuals = []
    for p in frame_paths[:20]:
        img = cv2.imread(p)
        if img is not None:
            residuals.append(_noise_residual(img))

    if len(residuals) < 3:
        return 0.0

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
