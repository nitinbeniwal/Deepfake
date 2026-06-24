"""
classifier.py — 9-model deepfake detection ensemble (7 HF + 2 timm CNN).
Two families: face-swap specialists (FF++ ViTs/CNNs) + AI-generation detectors
(diffusion/GAN, for fully-synthetic Gemini/Veo/SDXL frames). See _MODELS below.

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

import calibration as _calib

# Subtracted from every visual model score. Learned from operator feedback and
# stored in calibration.json — refresh_calibration() reloads it at the start of
# each analysis so corrections take effect on the next upload (no restart).
CALIBRATION_OFFSET = _calib.get_visual_offset()


def refresh_calibration():
    global CALIBRATION_OFFSET
    CALIBRATION_OFFSET = _calib.get_visual_offset()


_LOW_MEM = os.environ.get("LOW_MEM", "0") == "1"

UNCERTAIN_LO, UNCERTAIN_HI   = 20, 80
STILL_UNCERTAIN_LO, STILL_HI = 35, 65

# Sentinels for timm-based CNN models (not loadable via HF pipeline)
_XCEPTION_ID     = "timm:xception_deepfake"
_EFFICIENTNET_ID = "timm:efficientnet_b4_deepfake"

_MODELS = [
    # (model_id, weight, stage)   — relative weights (runtime normalizes by total)
    # Full ensemble = union of both prior model sets (all verified loading on HF).
    # Two families, on purpose:
    #   FACE-SWAP specialists (FF++-trained ViTs + CNNs) — catch DeepFaceLab/Roop/
    #     FaceFusion/Wav2Lip type manipulations.
    #   AI-GENERATION detectors (diffusion/GAN) — catch fully synthetic frames
    #     (Gemini/Veo/SDXL/Midjourney), which the FF++ models miss. These carry
    #     real weight now because that was the gap (Gemini video scored low).
    # The fusion head (train_fusion.py), once trained, learns the true weighting.
    # ── Face-swap / deepfake specialists (ViT) ──
    ("prithivMLmods/Deep-Fake-Detector-v2-Model",      0.13, 1),   # strongest FF++ ViT
    ("dima806/deepfake_vs_real_image_detection",        0.08, 2),
    ("Wvolf/ViT_Deepfake_Detection",                   0.07, 2),
    ("prithivMLmods/Deep-Fake-Detector-Model",         0.06, 3),
    ("prithivMLmods/deepfake-detector-model-v1",       0.06, 3),   # re-added (was on remote)
    # ── AI-generation detectors (diffusion / GAN — catch Gemini/Veo/SDXL) ──
    ("umm-maybe/AI-image-detector",                    0.05, 2),   # re-added; AI-gen images/video
    ("Organika/sdxl-detector",                          0.05, 3),  # diffusion-image detector (Gemini/SD)
    # ── CNN specialists — FF++ trained, highest weight, run last ──
    (_XCEPTION_ID,                                      0.30, 3),
    (_EFFICIENTNET_ID,                                  0.20, 3),
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
_XCEPTION_CKPT     = os.path.join(os.path.dirname(__file__), "xception_deepfake.pt")


class _XceptionWrapper:
    """
    Xception CNN via timm, loaded with DeepfakeBench FF++ weights.
    Mimics HF pipeline __call__ interface. 299×299 input.

    DeepfakeBench checkpoint (xception_best.pth) layout:
      backbone.*          → timm legacy_xception backbone   (matches after prefix strip)
      backbone.last_linear → classifier head Linear(2048, 2) (timm calls it 'fc')
      backbone.adjust_channel → unused feature-adapter, dropped

    IMPORTANT: if the classifier head fails to load we RAISE, so the caller
    skips this model entirely instead of injecting a random-head (noise) score.
    Label convention: softmax index 1 = FAKE, index 0 = REAL (DeepfakeBench).
    """

    def __init__(self):
        import timm, torch
        from torchvision import transforms
        print("Loading: xception (DeepfakeBench FF++) ...")
        self.model = timm.create_model("xception", pretrained=False, num_classes=2)

        if not os.path.exists(_XCEPTION_CKPT):
            raise FileNotFoundError("xception_deepfake.pt not present")

        raw = torch.load(_XCEPTION_CKPT, map_location="cpu", weights_only=False)
        if isinstance(raw, dict) and "state_dict" in raw and isinstance(raw["state_dict"], dict):
            raw = raw["state_dict"]

        # Two accepted formats:
        #  (a) DeepfakeBench: keys prefixed 'backbone.', head named 'last_linear'
        #  (b) Native timm fine-tune (our train_finetune.py output): plain timm keys
        if any(k.startswith("backbone.") for k in raw):
            sd = {}
            for k, v in raw.items():
                if not k.startswith("backbone."):
                    continue
                kk = k[len("backbone."):]
                if kk.startswith("adjust_channel"):    # DeepfakeBench adapter — unused at inference
                    continue
                if kk.startswith("last_linear"):        # head → timm 'fc'
                    kk = "fc" + kk[len("last_linear"):]
                sd[kk] = v
        else:
            sd = dict(raw)                              # native timm state_dict

        missing, unexpected = self.model.load_state_dict(sd, strict=False)
        head_ok = "fc.weight" not in missing and "fc.bias" not in missing
        backbone_ok = len(sd) - len(unexpected) > 100
        if not (head_ok and backbone_ok):
            raise RuntimeError(
                f"Xception checkpoint incomplete (head_ok={head_ok}, "
                f"matched={len(sd) - len(unexpected)}/{len(sd)}) — refusing to run with random head")
        print(f"Xception: FF++ weights loaded ({len(sd) - len(unexpected)}/{len(sd)} keys, head OK)")

        from device_utils import torch_device
        self.device = torch_device()
        self.model.eval().to(self.device)
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
            tensors = torch.stack([self.transform(img) for img in batch]).to(self.device)
            with torch.no_grad():
                probs = torch.softmax(self.model(tensors), dim=1).cpu()
            for p in probs:
                results.append([
                    {"label": "FAKE", "score": float(p[1])},
                    {"label": "REAL", "score": float(p[0])},
                ])
        return results


def _get_xception():
    global _xception_instance
    if _xception_instance is None:
        with _xception_lock:
            if _xception_instance is None:
                try:
                    _xception_instance = _XceptionWrapper()
                    print("Loaded:  xception OK")
                except Exception as e:
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
_EFFICIENTNET_CKPT     = os.path.join(os.path.dirname(__file__), "efficientnet_b4_deepfake.pt")


class _EfficientNetWrapper:
    """
    EfficientNet-B4 with DeepfakeBench FF++ weights, via the lukemelas
    `efficientnet_pytorch` lib (the arch DeepfakeBench actually trained on).
    Mimics HF pipeline __call__ interface. 380×380 input.

    DeepfakeBench checkpoint (effnb4_best.pth) layout:
      backbone.efficientnet.*  → EfficientNet feature extractor (no _fc)
      backbone.last_layer      → classifier head Linear(1792, 2)

    Uses extract_features → global avg pool → last_layer. RAISES if the head
    cannot be built, so the caller skips it rather than scoring with noise.
    Label convention: softmax index 1 = FAKE, index 0 = REAL.
    """

    def __init__(self):
        import torch
        import torch.nn as nn
        from efficientnet_pytorch import EfficientNet
        from torchvision import transforms
        print("Loading: efficientnet_b4 (DeepfakeBench FF++) ...")

        if not os.path.exists(_EFFICIENTNET_CKPT):
            raise FileNotFoundError("efficientnet_b4_deepfake.pt not present")

        self.net = EfficientNet.from_name("efficientnet-b4")
        raw = torch.load(_EFFICIENTNET_CKPT, map_location="cpu", weights_only=False)
        if isinstance(raw, dict) and "state_dict" in raw and isinstance(raw["state_dict"], dict):
            raw = raw["state_dict"]

        pref = "backbone.efficientnet."
        sd = {k[len(pref):]: v for k, v in raw.items() if k.startswith(pref)}
        missing, unexpected = self.net.load_state_dict(sd, strict=False)
        backbone_ok = len(sd) - len(unexpected) > 300
        if not backbone_ok:
            raise RuntimeError(f"EffB4 backbone load failed ({len(sd) - len(unexpected)}/{len(sd)})")

        hw, hb = raw.get("backbone.last_layer.weight"), raw.get("backbone.last_layer.bias")
        if hw is None or hb is None:
            raise RuntimeError("EffB4 classifier head (last_layer) missing — refusing random head")
        self.head = nn.Linear(hw.shape[1], hw.shape[0])
        self.head.load_state_dict({"weight": hw, "bias": hb})
        print(f"EfficientNet-B4: FF++ weights loaded ({len(sd) - len(unexpected)}/{len(sd)} keys, head OK)")

        from device_utils import torch_device
        self.device = torch_device()
        self.net.eval().to(self.device)
        self.head.eval().to(self.device)
        self.transform = transforms.Compose([
            transforms.Resize((380, 380)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ])

    def __call__(self, images, batch_size=4):
        import torch
        import torch.nn.functional as F
        results = []
        for i in range(0, len(images), batch_size):
            batch   = images[i : i + batch_size]
            tensors = torch.stack([self.transform(img) for img in batch]).to(self.device)
            with torch.no_grad():
                feat  = self.net.extract_features(tensors)
                feat  = F.adaptive_avg_pool2d(feat, 1).flatten(1)
                probs = torch.softmax(self.head(feat), dim=1).cpu()
            for p in probs:
                results.append([
                    {"label": "FAKE", "score": float(p[1])},
                    {"label": "REAL", "score": float(p[0])},
                ])
        return results


def _get_efficientnet():
    global _efficientnet_instance
    if _efficientnet_instance is None:
        with _efficientnet_lock:
            if _efficientnet_instance is None:
                try:
                    _efficientnet_instance = _EfficientNetWrapper()
                    print("Loaded:  efficientnet_b4 OK")
                except Exception as e:
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
                from device_utils import hf_device
                short = model_id.split("/")[-1]
                print(f"Loading: {short} ...")
                try:
                    _pipes[model_id] = pipeline("image-classification", model=model_id,
                                                device=hf_device())
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
