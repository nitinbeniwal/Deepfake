"""
temporal_analyzer.py — Frame-to-frame consistency analysis.

Real videos: face embeddings change smoothly (same physical face).
Deepfakes: each frame generated independently → higher variance.

Uses simple pixel-level embeddings (no extra models needed) and
optional torchvision ResNet features for higher accuracy.
"""

import cv2, numpy as np, os


def _pixel_embedding(img_bgr, size=48):
    """Fast pixel-level embedding: resize + flatten + normalize."""
    r = cv2.resize(img_bgr, (size, size)).astype(np.float32)
    r = (r - r.mean()) / (r.std() + 1e-8)
    return r.flatten()


def _cosine_dist(a, b):
    n = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)
    return 1.0 - float(n)


def temporal_consistency_score(face_paths, use_resnet=False):
    """
    Score 0-100 (higher = more inconsistent = more likely fake).

    Real face: inter-frame cosine distance std  ~0.02-0.06
    Deepfake : inter-frame cosine distance std  ~0.08-0.20
    """
    imgs = []
    for p in face_paths[:20]:
        img = cv2.imread(p)
        if img is not None:
            imgs.append(img)

    if len(imgs) < 3:
        return 0.0

    if use_resnet:
        embeds = _resnet_embeddings(imgs)
    else:
        embeds = [_pixel_embedding(img) for img in imgs]

    dists = [_cosine_dist(embeds[i], embeds[i+1]) for i in range(len(embeds)-1)]
    if not dists:
        return 0.0

    mean_d = float(np.mean(dists))
    std_d  = float(np.std(dists))

    # Thresholds from empirical observation:
    # Real: std ~ 0.02-0.06, Fake: std ~ 0.08-0.20
    # Sigmoid-like mapping
    if std_d < 0.05:   score = 0.0
    elif std_d < 0.08: score = (std_d - 0.05) / 0.03 * 30
    elif std_d < 0.15: score = 30 + (std_d - 0.08) / 0.07 * 50
    else:              score = min(100, 80 + (std_d - 0.15) * 200)

    # Also penalise sudden large jumps (max/mean ratio)
    max_d = max(dists)
    if mean_d > 0 and max_d / (mean_d + 1e-8) > 4:
        score = min(100, score + 15)

    return round(float(score), 1)


def _resnet_embeddings(imgs_bgr):
    """Use torchvision MobileNetV3 (fast, already installed) for embeddings."""
    try:
        import torch, torchvision.models as models, torchvision.transforms as T
        global _feat_model, _transform
        if not hasattr(_resnet_embeddings, '_model'):
            weights = models.MobileNet_V3_Small_Weights.DEFAULT
            m = models.mobilenet_v3_small(weights=weights)
            m.classifier = torch.nn.Identity()
            m.eval()
            _resnet_embeddings._model = m
            _resnet_embeddings._tf = weights.transforms()

        tf = _resnet_embeddings._tf
        tensors = []
        for img in imgs_bgr:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            from PIL import Image
            pil = Image.fromarray(rgb)
            tensors.append(tf(pil))

        with torch.no_grad():
            batch = torch.stack(tensors)
            feats = _resnet_embeddings._model(batch).numpy()
        return [feats[i] for i in range(len(feats))]
    except Exception:
        # Fallback to pixel embeddings
        return [_pixel_embedding(img) for img in imgs_bgr]
