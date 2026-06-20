"""
model_downloader.py — Downloads pretrained deepfake detector checkpoints.

Sources:
  DeepfakeBench v1.0.1 GitHub releases (public, no authentication required)
  Xception:        trained on FF++ (FaceForensics++) — face-swap specialist
  EfficientNet-B4: trained on FF++ — compression artifact specialist (97% AUC)

Called once at startup. Downloads run in background. Falls back to
ImageNet pretrained weights if download fails or Railway has no outbound access.
"""

import os, gc, logging, threading
import requests

logger = logging.getLogger(__name__)

_MODEL_DIR = os.path.dirname(os.path.abspath(__file__))

CHECKPOINTS = {
    "xception_deepfake.pt": {
        "url": "https://github.com/SCLBD/DeepfakeBench/releases/download/v1.0.1/xception_best.pth",
        "size_mb": 86,
        "desc": "Xception (FaceForensics++ trained)",
    },
    "efficientnet_b4_deepfake.pt": {
        "url": "https://github.com/SCLBD/DeepfakeBench/releases/download/v1.0.1/effnb4_best.pth",
        "size_mb": 75,
        "desc": "EfficientNet-B4 (FaceForensics++ trained, 97% AUC)",
    },
}


def _download(url: str, dest: str, size_mb: int, desc: str) -> bool:
    """Stream download with 1MB chunks. Returns True on success."""
    try:
        logger.info(f"[downloader] Starting: {desc} (~{size_mb}MB)")
        print(f"[downloader] Downloading {desc} (~{size_mb}MB) ...")
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, stream=True, timeout=300, headers=headers,
                         allow_redirects=True)
        r.raise_for_status()

        tmp = dest + ".tmp"
        total = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)

        if total < 1_000_000:
            raise ValueError(f"Downloaded file too small: {total} bytes (expected ~{size_mb}MB)")

        os.replace(tmp, dest)
        print(f"[downloader] {desc}: {total >> 20}MB saved to {os.path.basename(dest)}")
        return True

    except Exception as e:
        print(f"[downloader] FAILED {desc}: {e}")
        for path in (dest + ".tmp", dest):
            if os.path.exists(path):
                try: os.remove(path)
                except OSError: pass
        return False


def try_load_checkpoint(model, path: str) -> int:
    """
    Smart checkpoint loader with key-prefix remapping.

    DeepfakeBench wraps backbones in AbstractDetector, so state dict
    keys may have 'backbone.' prefix. This function tries multiple
    prefix strippings and picks the one with most matched keys.

    Returns: number of parameters successfully matched (0 = failed).
    """
    import torch

    try:
        raw = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as e:
        print(f"[loader] Cannot read {path}: {e}")
        return 0

    # Unwrap common wrapper keys
    for wrap_key in ("state_dict", "model", "net", "network"):
        if isinstance(raw, dict) and wrap_key in raw and isinstance(raw[wrap_key], dict):
            raw = raw[wrap_key]
            break

    if not isinstance(raw, dict):
        print(f"[loader] Unexpected checkpoint format: {type(raw)}")
        return 0

    best_matched = 0

    for prefix in ("", "backbone.", "module.", "model.", "encoder.", "net.", "block."):
        if prefix:
            candidate = {k[len(prefix):]: v
                         for k, v in raw.items() if k.startswith(prefix)}
        else:
            candidate = raw

        if not candidate:
            continue

        try:
            missing, unexpected = model.load_state_dict(candidate, strict=False)
            matched = len(candidate) - len(unexpected)
            if matched > best_matched:
                best_matched = matched
                print(f"[loader] prefix='{prefix}': {matched}/{len(candidate)} keys matched, "
                      f"{len(missing)} missing")
        except Exception:
            pass

    if best_matched > 0:
        print(f"[loader] Checkpoint loaded: {best_matched} parameters matched")
    else:
        print(f"[loader] No keys matched — check architecture compatibility")

    return best_matched


def ensure_checkpoints(blocking: bool = False):
    """
    Download missing checkpoints. Call at startup.

    blocking=False (default): runs in daemon thread, returns immediately.
    blocking=True: waits for all downloads to complete.
    """
    def _run():
        for filename, info in CHECKPOINTS.items():
            dest = os.path.join(_MODEL_DIR, filename)
            if os.path.exists(dest) and os.path.getsize(dest) > 1_000_000:
                print(f"[downloader] Already present: {filename}")
                continue
            _download(info["url"], dest, info["size_mb"], info["desc"])
            gc.collect()

    if blocking:
        _run()
    else:
        t = threading.Thread(target=_run, daemon=True, name="model-downloader")
        t.start()
        return t
