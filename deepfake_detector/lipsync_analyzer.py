"""
lipsync_analyzer.py — Lip-sync consistency check.

Real video: mouth motion correlates with speech audio energy.
Deepfake (face-swap): face generated independently from audio → low correlation.

Method:
  1. Crop mouth ROI from each face frame (bottom 40% of face)
  2. Optical flow magnitude between consecutive frames → mouth motion signal
  3. Extract audio via ffmpeg, compute per-frame RMS → speech energy signal
  4. Pearson correlation of the two aligned signals
  5. Low/negative correlation → likely fake

Score 0-100 (higher = more likely fake).
Returns 0 if not enough data (no audio track, < 5 frames, silent video).
"""

import os, subprocess
import cv2
import numpy as np


def _mouth_roi(img_bgr):
    h, w = img_bgr.shape[:2]
    return img_bgr[int(h * 0.55):h, int(w * 0.15):int(w * 0.85)]


def _optical_flow_mag(prev_bgr, curr_bgr):
    p = cv2.cvtColor(prev_bgr, cv2.COLOR_BGR2GRAY)
    c = cv2.cvtColor(curr_bgr, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(p, c, None,
                                        pyr_scale=0.5, levels=3,
                                        winsize=13, iterations=3,
                                        poly_n=5, poly_sigma=1.1, flags=0)
    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
    return float(np.mean(mag))


def _audio_rms_per_frame(video_path, n_frames):
    """Extract mono 16kHz audio and split into n_frames chunks → RMS array."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg = "ffmpeg"

    cmd = [ffmpeg, "-i", video_path,
           "-f", "f32le", "-ac", "1", "-ar", "16000",
           "-vn", "pipe:1", "-loglevel", "quiet"]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=30)
        if r.returncode != 0 or not r.stdout:
            return None
    except Exception:
        return None

    raw = np.frombuffer(r.stdout, dtype=np.float32)
    if len(raw) == 0:
        return None

    chunk = max(1, len(raw) // n_frames)
    rms = []
    for i in range(n_frames):
        seg = raw[i * chunk:(i + 1) * chunk]
        rms.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    return np.array(rms, dtype=np.float32)


def lipsync_score(face_paths, video_path=None):
    """
    Score 0-100 (higher = more likely fake/out-of-sync).

    Correlation thresholds (empirical):
      corr >= 0.30  → real-range       → score ~  0
      corr  ~ 0.15  → borderline       → score ~ 35
      corr ~  0.00  → no sync          → score ~ 70
      corr < 0.00   → anti-correlated  → score ~ 100
    """
    imgs = []
    for p in face_paths[:30]:
        img = cv2.imread(p)
        if img is not None:
            imgs.append(img)

    if len(imgs) < 5:
        return 0.0

    # Mouth ROI motion signal (n-1 values)
    mouths = [_mouth_roi(img) for img in imgs]
    motion = np.array([
        _optical_flow_mag(mouths[i], mouths[i + 1])
        for i in range(len(mouths) - 1)
    ])

    if video_path is None or not os.path.exists(video_path):
        return 0.0

    energy = _audio_rms_per_frame(video_path, len(motion))
    if energy is None or len(energy) < len(motion):
        return 0.0

    energy = energy[:len(motion)]

    # Can't score if either signal is flat (silent / no mouth movement)
    if motion.std() < 1e-6 or energy.std() < 1e-6:
        return 0.0

    corr = float(np.corrcoef(motion, energy)[0, 1])

    if corr >= 0.30:    score = 0.0
    elif corr >= 0.15:  score = (0.30 - corr) / 0.15 * 35
    elif corr >= 0.00:  score = 35 + (0.15 - corr) / 0.15 * 35
    else:               score = min(100.0, 70 + abs(corr) * 100)

    return round(float(score), 1)
