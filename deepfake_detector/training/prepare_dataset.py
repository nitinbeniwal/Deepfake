"""
prepare_dataset.py — sort everything under training/datasets/ into a single
training/dataset/{real,fake}/ tree that train_finetune.py understands.

Each Kaggle/HF dataset uses different folder names for its two classes. This
script walks every downloaded folder and routes files by the label keyword in
their path. Files land in dataset/real or dataset/fake via hardlink (cheap, no
extra disk) or copy fallback.

Heuristic label keywords (case-insensitive, matched on any path component):
  REAL : real, genuine, authentic, original, live, pristine, 0_real, class_0
  FAKE : fake, deepfake, manipulat, synthet, generat, gan, swap, forg, 1_fake, class_1

Anything that matches neither is reported and skipped (you can move it by hand).
Run AFTER download_datasets.py.
"""

import os, sys, shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC  = os.path.join(_HERE, "datasets")
_DST  = os.path.join(_HERE, "dataset")

_MEDIA = (".jpg", ".jpeg", ".png", ".bmp", ".webp",
          ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")

_REAL_KW = ("real", "genuine", "authentic", "original", "live", "pristine")
_FAKE_KW = ("fake", "deepfake", "manipulat", "synthet", "generat", "gan", "swap", "forg")


def _label_for(path_lower):
    # check fake first (some paths contain both 'real' and 'fake' e.g. 'real-vs-fake')
    parts = path_lower.replace("\\", "/").split("/")
    for p in parts:
        if any(k in p for k in _FAKE_KW): return "fake"
    for p in parts:
        if any(k in p for k in _REAL_KW): return "real"
    # explicit 0/1 class folders
    for p in parts:
        if p in ("1", "class_1", "1_fake"): return "fake"
        if p in ("0", "class_0", "0_real"): return "real"
    return None


def _place(src_file, dst_dir, idx):
    os.makedirs(dst_dir, exist_ok=True)
    ext = os.path.splitext(src_file)[1].lower()
    dst = os.path.join(dst_dir, f"{idx:08d}{ext}")
    try:
        os.link(src_file, dst)          # hardlink — no extra disk
    except OSError:
        try: shutil.copy2(src_file, dst)
        except OSError: return False
    return True


def main():
    if not os.path.isdir(_SRC):
        print(f"No {_SRC} — run download_datasets.py first."); return
    real_dir = os.path.join(_DST, "real")
    fake_dir = os.path.join(_DST, "fake")
    counts = {"real": 0, "fake": 0, "skipped": 0}
    idx = 0

    for root, _dirs, files in os.walk(_SRC):
        for fn in files:
            if os.path.splitext(fn)[1].lower() not in _MEDIA:
                continue
            full = os.path.join(root, fn)
            label = _label_for(full.lower())
            if label is None:
                counts["skipped"] += 1
                continue
            if _place(full, real_dir if label == "real" else fake_dir, idx):
                counts[label] += 1; idx += 1

    print(f"\nReady at {_DST}")
    print(f"  real    : {counts['real']}")
    print(f"  fake    : {counts['fake']}")
    print(f"  skipped : {counts['skipped']}  (label not detected in path — move by hand if needed)")
    if counts["real"] < 50 or counts["fake"] < 50:
        print("\nWARNING: very few per class. Check that datasets downloaded and that their\n"
              "folder names contain real/fake keywords. You can also drop your OWN phone\n"
              "clips into dataset/real and dataset/fake directly.")
    print("\nNext:  cd ..  &&  python train_finetune.py --data training/dataset --epochs 15")


if __name__ == "__main__":
    main()
