"""
device_utils.py — pick GPU automatically when available.

On a laptop/desktop with a CUDA GPU (and a CUDA build of torch) inference runs
on the GPU and is much faster. Everywhere else (CPU-only torch, no GPU, Railway)
it transparently falls back to CPU — no errors, no config needed.

Force CPU with DF_FORCE_CPU=1.
"""

import os
import functools


@functools.lru_cache(maxsize=1)
def has_cuda() -> bool:
    if os.environ.get("DF_FORCE_CPU", "0") == "1":
        return False
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def torch_device():
    """String for .to() / MTCNN: 'cuda' or 'cpu'."""
    return "cuda" if has_cuda() else "cpu"


def hf_device() -> int:
    """Device index for transformers.pipeline(device=...): 0 = first GPU, -1 = CPU."""
    return 0 if has_cuda() else -1


def describe() -> str:
    if not has_cuda():
        return "CPU"
    try:
        import torch
        return f"GPU ({torch.cuda.get_device_name(0)})"
    except Exception:
        return "GPU"
