"""
classifier.py — 7-model deepfake detection ensemble.

Visual pipeline (sequential, one model at a time, each unloaded before next):

  HuggingFace ViT models (transformer-based, face-swap specialists):
    1. prithivMLmods/Deep-Fake-Detector-v2-Model      weight 0.12  stage 1
    2. dima806/deepfake_vs_real_image_detection         weight 0.10  stage 2
    3. Wvolf/ViT-Deepfake-Detection                    weight 0.08  stage 2
    4. prithivMLmods/Deepfake-Detection-Exp-02-Model   weight 0.07  stage 3
    5. haywoodsloan/autotrain-deepfake-detection        weight 0.05  stage 3

  CNN specialists (timm, compression-artifact experts):
    6. Xception          weight 0.33  stage 3  (FaceForensics++ architecture)
    7. EfficientNet-B4   weight 0.25  stage 3  (DeepfakeBench top performer)

Fine-tune checkpoints: drop xception_deepfake.pt / efficientnet_b4_deepfake.pt
next to this file. Without them, CNN models use ImageNet pretrained backbone
(neutral ~50% output) until you supply trained weights from DF40/FF++.

Stage cascade (normal mode only, not LOW_MEM):
  Stage 1 → screens all frames with primary ViT.
  Stage 2 → uncertain frames → TTA + secondary ViTs.
  Stage 3 → still uncertain → specialist ViTs + CNN models.
"""

import gc, os, threading, statistics
from concurrent.futures import ThreadPoolExecutor, as_completed

CALIBRATION_OFFSET = 0
_LOW_MEM = os.environ.get("LOW_MEM", "0") == "1"

UNCERTAIN_LO, UNCERTAIN_HI   = 20, 80
STILL_UNCERTAIN_LO, STILL_HI = 35, 65

# Sentinels for timm-based CNN models (not loadable via HF pipeline)
_XCEPTION_ID     = "timm:xception_deepfake"
_EFFICIENTNET_ID = "timm:efficientnet_b4_deepfake"

_MODELS = [
    # (model_id, weight, stage)   — weights sum to 1.0
    # HuggingFace face-deepfake specialists (all verified to exist on HF Hub)
    ("prithivMLmods/Deep-Fake-Detector-v2-Model",      0.12, 1),  # FaceForensics++ trained
    ("dima806/deepfake_vs_real_image_detection",        0.10, 2),  # 189K image dataset
    ("Wvolf/ViT_Deepfake_Detection",                   0.10, 2),  # ViT deepfake specialist
    ("prithivMLmods/deepfake-detector-model-v1",       0.08, 3),  # high-download v1 model
    ("umm-maybe/AI-image-detector",                    0.05, 3),  # AI-generated image detector
    # CNN specialists — highest weights, loaded last (require downloaded checkpoints)
    (_XCEPTION_ID,                                      0.33, 3),  # FaceForensics++ 97% AUC
    (_EFFICIENTNET_ID,                                  0.22, 3),  # DeepfakeBench top performer
]

_FAKE = ("fake","deepfake","spoof","synthetic","artificial","generated",
         "ai","manipulat","forg","altered","tamper")
_REAL = ("real","genuine","authentic","human","live","bonafide",
         "natural","original","unaltered")

_pipes: dict = {}
_lock = threading.Lock()

def reset_buffers(): return None


# ── Xception (timm) ───────────────────────────────────────────────────────────

_xception_instance = None
_xception_lock     = threading.Lock()
_xception_ckpt_valid = None  # None=unknown, True=valid, False=no keys matched
_XCEPTION_CKPT     = os.path.join(os.path.dirname(__file__), "xception_deepfake.pt")


class _XceptionWrapper:
    """
    Xception CNN via timm. Mimics HF pipeline __call__ interface.
    Designed for FaceForensics++ deepfake detection (299×299 input).

    Only runs when a valid DeepfakeBench checkpoint is available.
    Without matched weights, ImageNet pretrained outputs ~50% neutral — excluded
    from the ensemble to avoid diluting real signals.
    """

    def __init__(self):
        import timm
        from torchvision import transforms
        print("Loading: xception (timm) ...")
        self.model = timm.create_model("xception", pretrained=True, num_classes=2)
        self._valid = False

        if os.path.exists(_XCEPTION_CKPT):
            from model_downloader import try_load_checkpoint
            matched = try_load_checkpoint(self.model, _XCEPTION_CKPT)
            if matched > 0:
                self._valid = True
                print(f"Xception: DeepfakeBench checkpoint loaded ({matched} params matched)")
            else:
                print("Xception: no keys matched — excluded from ensemble (ImageNet = random ~50%)")
        else:
            print("Xception: checkpoint not downloaded — excluded until weights available")

        if self._valid:
            self.model.eval()
        self.transform = transforms.Compose([
            transforms.Resize((299, 299)),
            transforms.ToTensor(),
            transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
        ])

    def __call__(self, images, batch_size=4):
        import torch
        results = []
        for i in range(0, len(images), batch_size):
            batch   = images[i : i + batch_size]
            tensors = torch.stack([self.transform(img) for img in batch])
            with torch.no_grad():
                probs = torch.softmax(self.model(tensors), dim=1)
            for p in probs:
                results.append([
                    {"label": "FAKE", "score": float(p[1])},
                    {"label": "REAL", "score": float(p[0])},
                ])
        return results


def _get_xception():
    global _xception_instance, _xception_ckpt_valid
    if _xception_ckpt_valid is False:
        return None  # already determined: no valid checkpoint
    if _xception_instance is None:
        with _xception_lock:
            if _xception_instance is None:
                try:
                    inst = _XceptionWrapper()
                    _xception_ckpt_valid = inst._valid
                    if inst._valid:
                        _xception_instance = inst
                        print("Loaded:  xception OK")
                    else:
                        print("SKIP:    xception — no valid checkpoint")
                except Exception as e:
                    _xception_ckpt_valid = False
                    print(f"SKIP:    xception — {e}")
    return _xception_instance


def _unload_xception():
    global _xception_instance
    with _xception_lock:
        _xception_instance = None
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


# ── EfficientNet-B4 (timm) ────────────────────────────────────────────────────

_efficientnet_instance = None
_efficientnet_lock     = threading.Lock()
_efficientnet_ckpt_valid = None  # None=unknown, True=valid, False=no keys matched
_EFFICIENTNET_CKPT     = os.path.join(os.path.dirname(__file__), "efficientnet_b4_deepfake.pt")


class _EfficientNetWrapper:
    """
    EfficientNet-B4 CNN via timm. Mimics HF pipeline __call__ interface.
    DeepfakeBench top performer on FF++ (97% AUC). 380×380 input.

    Only runs when a valid DeepfakeBench checkpoint is available.
    Without matched weights, ImageNet pretrained outputs ~50% neutral — excluded
    from the ensemble to avoid diluting real signals.
    """

    def __init__(self):
        import timm
        from torchvision import transforms
        print("Loading: efficientnet_b4 (timm) ...")
        self.model = timm.create_model("efficientnet_b4", pretrained=True, num_classes=2)
        self._valid = False

        if os.path.exists(_EFFICIENTNET_CKPT):
            from model_downloader import try_load_checkpoint
            matched = try_load_checkpoint(self.model, _EFFICIENTNET_CKPT)
            if matched > 0:
                self._valid = True
                print(f"EfficientNet-B4: DeepfakeBench checkpoint loaded ({matched} params matched)")
            else:
                print("EfficientNet-B4: no keys matched — excluded from ensemble (ImageNet = random ~50%)")
        else:
            print("EfficientNet-B4: checkpoint not downloaded — excluded until weights available")

        if self._valid:
            self.model.eval()
        self.transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __call__(self, images, batch_size=4):
        import torch
        results = []
        for i in range(0, len(images), batch_size):
            batch   = images[i : i + batch_size]
            tensors = torch.stack([self.transform(img) for img in batch])
            with torch.no_grad():
                probs = torch.softmax(self.model(tensors), dim=1)
            for p in probs:
                results.append([
                    {"label": "FAKE", "score": float(p[1])},
                    {"label": "REAL", "score": float(p[0])},
                ])
        return results


def _get_efficientnet():
    global _efficientnet_instance, _efficientnet_ckpt_valid
    if _efficientnet_ckpt_valid is False:
        return None  # already determined: no valid checkpoint
    if _efficientnet_instance is None:
        with _efficientnet_lock:
            if _efficientnet_instance is None:
                try:
                    inst = _EfficientNetWrapper()
                    _efficientnet_ckpt_valid = inst._valid
                    if inst._valid:
                        _efficientnet_instance = inst
                        print("Loaded:  efficientnet_b4 OK")
                    else:
                        print("SKIP:    efficientnet_b4 — no valid checkpoint")
                except Exception as e:
                    _efficientnet_ckpt_valid = False
                    print(f"SKIP:    efficientnet_b4 — {e}")
    return _efficientnet_instance


def _unload_efficientnet():
    global _efficientnet_instance
    with _efficientnet_lock:
        _efficientnet_instance = None
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


# ── Unified model loader / unloader ──────────────────────────────────────────

def _get_pipe(model_id):
    """Load and return model by ID. Handles both HF pipeline and timm sentinels."""
    if model_id == _XCEPTION_ID:
        return _get_xception()
    if model_id == _EFFICIENTNET_ID:
        return _get_efficientnet()
    if model_id not in _pipes:
        with _lock:
            if model_id not in _pipes:
                from transformers import pipeline
                short = model_id.split("/")[-1]
                print(f"Loading: {short} ...")
                try:
                    _pipes[model_id] = pipeline("image-classification", model=model_id)
                    print(f"Loaded:  {short} OK")
                except Exception as e:
                    print(f"SKIP:    {short} — {e}")
                    _pipes[model_id] = None
    return _pipes.get(model_id)


def _unload_model(model_id):
    """Unload any model type from memory."""
    if model_id == _XCEPTION_ID:
        _unload_xception()
        return
    if model_id == _EFFICIENTNET_ID:
        _unload_efficientnet()
        return
    _pipes.pop(model_id, None)
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


# ── Score helpers ─────────────────────────────────────────────────────────────

def _score(results):
    fp = rp = None
    for r in results:
        lbl  = r["label"].strip().lower()
        is_f = any(t in lbl for t in _FAKE) or lbl in ("label_1", "1")
        is_r = any(t in lbl for t in _REAL) or lbl in ("label_0", "0")
        if is_f and not is_r:
            fp = max(fp, r["score"]) if fp else r["score"]
        elif is_r and not is_f:
            rp = max(rp, r["score"]) if rp else r["score"]
    if fp: return fp * 100
    if rp: return (1 - rp) * 100
    top = max(results, key=lambda r: r["score"])
    return ((1 - top["score"]) if any(t in top["label"].lower() for t in _REAL) else top["score"]) * 100


def _calibrate(s):
    if s is None: return None
    return round(max(0.0, min(100.0, s - CALIBRATION_OFFSET)), 2)


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


# ── Model runners ─────────────────────────────────────────────────────────────

def _run_model(model_id, pil_images, batch_size=8):
    pipe = _get_pipe(model_id)
    if pipe is None:
        return [None] * len(pil_images)
    try:
        results = pipe(pil_images, batch_size=batch_size)
        return [_score(r) for r in results]
    except Exception as e:
        short = model_id.split("/")[-1] if "/" in model_id else model_id
        print(f"Model {short} error: {e}")
        return [None] * len(pil_images)


def _run_and_unload(model_id, pil_images, batch_size=4):
    """Load → run → unload. Used in sequential / LOW_MEM mode."""
    pipe = _get_pipe(model_id)
    if pipe is None:
        return [None] * len(pil_images)
    try:
        results = pipe(pil_images, batch_size=batch_size)
        return [_score(r) for r in results]
    except Exception as e:
        short = model_id.split("/")[-1] if "/" in model_id else model_id
        print(f"Model {short} error: {e}")
        return [None] * len(pil_images)
    finally:
        _unload_model(model_id)


def _classify_sequential(valid, orig_idxs, image_paths):
    """All 7 models, one at a time, each unloaded before next. Safe on 512MB RAM."""
    final = [None] * len(image_paths)
    model_results = {}

    for model_id, weight, _stage in _MODELS:
        short = model_id.split("/")[-1] if "/" in model_id else model_id
        print(f"[sequential] {short} ...")
        scores = _run_and_unload(model_id, valid, batch_size=4)
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


# ── Public API ────────────────────────────────────────────────────────────────

def classify_faces_batch(image_paths, verbose=False):
    """
    LOW_MEM mode: all 7 models sequential, each unloaded before next.
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

    if _LOW_MEM:
        return _classify_sequential(valid, orig_idxs, image_paths)

    primary_id = _MODELS[0][0]

    # Stage 1: primary ViT on all images
    raw1           = _run_model(primary_id, valid)
    primary_scores = [_calibrate(s) for s in raw1]

    clear_idxs = [i for i, s in enumerate(primary_scores)
                  if s is not None and (s < UNCERTAIN_LO or s > UNCERTAIN_HI)]
    unc_idxs   = [i for i, s in enumerate(primary_scores)
                  if s is None or UNCERTAIN_LO <= s <= UNCERTAIN_HI]

    for i in clear_idxs:
        final[orig_idxs[i]] = primary_scores[i]

    if not unc_idxs:
        return final

    # Stage 2: uncertain → TTA + secondary ViTs
    unc_imgs     = [valid[i] for i in unc_idxs]
    unc_orig_idx = [orig_idxs[i] for i in unc_idxs]
    aug_batch, aug_map = [], []
    for idx, img in enumerate(unc_imgs):
        for aug in _tta(img):
            aug_batch.append(aug)
            aug_map.append(idx)

    img_scores = defaultdict(lambda: defaultdict(list))

    for aug_idx, s in enumerate(_run_model(primary_id, aug_batch)):
        if s is not None:
            img_scores[aug_map[aug_idx]][primary_id].append(s)

    stage2_hf = [(mid, w) for mid, w, stage in _MODELS if stage == 2]
    with ThreadPoolExecutor(max_workers=max(1, len(stage2_hf))) as ex:
        futs = {ex.submit(_run_model, mid, aug_batch): mid for mid, w in stage2_hf}
        for fut in as_completed(futs):
            mid = futs[fut]
            for aug_idx, s in enumerate(fut.result()):
                if s is not None:
                    img_scores[aug_map[aug_idx]][mid].append(s)

    stage2_results = []
    for local_idx in range(len(unc_imgs)):
        tw = ws = 0.0
        for mid, w, _ in _MODELS[:3]:
            augs = img_scores[local_idx].get(mid, [])
            if augs:
                ws += statistics.mean(augs) * w
                tw += w
        stage2_results.append(_calibrate(ws / tw) if tw else None)

    # Stage 3: still uncertain → specialist ViTs + CNN models (sequential for CNNs)
    still_unc = [i for i, s in enumerate(stage2_results)
                 if s is None or STILL_UNCERTAIN_LO <= s <= STILL_HI]

    if still_unc:
        su_imgs = [unc_imgs[i] for i in still_unc]
        su_aug, su_map = [], []
        for idx, img in enumerate(su_imgs):
            for aug in _tta(img):
                su_aug.append(aug)
                su_map.append(idx)

        spec_scores = defaultdict(lambda: defaultdict(list))

        # HF stage-3 models in parallel
        stage3_hf = [(mid, w) for mid, w, stage in _MODELS
                     if stage == 3 and mid not in (_XCEPTION_ID, _EFFICIENTNET_ID)]
        with ThreadPoolExecutor(max_workers=max(1, len(stage3_hf))) as ex:
            futs = {ex.submit(_run_model, mid, su_aug): mid for mid, w in stage3_hf}
            for fut in as_completed(futs):
                mid = futs[fut]
                for aug_idx, s in enumerate(fut.result()):
                    if s is not None:
                        spec_scores[su_map[aug_idx]][mid].append(s)

        # CNN models sequential (heavy — load/run/unload one at a time)
        for cnn_id in (_XCEPTION_ID, _EFFICIENTNET_ID):
            cnn_scores = _run_and_unload(cnn_id, su_imgs, batch_size=4)
            for local_idx, s in enumerate(cnn_scores):
                if s is not None:
                    spec_scores[local_idx][cnn_id].append(s)

        for su_local, local_idx in enumerate(still_unc):
            tw = ws = 0.0
            for mid, w, _ in _MODELS:
                src  = img_scores[local_idx] if mid in img_scores[local_idx] else spec_scores[su_local]
                augs = src.get(mid, [])
                if augs:
                    ws += statistics.mean(augs) * w
                    tw += w
            if tw:
                stage2_results[local_idx] = _calibrate(ws / tw)

    for local_idx in range(len(unc_imgs)):
        s = stage2_results[local_idx]
        final[unc_orig_idx[local_idx]] = s
        if verbose and s is not None:
            print(f"  [ensemble] frame → {s:.1f}%")

    return final


def classify_face(image_path, verbose=True):
    scores = classify_faces_batch([image_path], verbose=verbose)
    return scores[0]


classify_face_v2 = classify_face
