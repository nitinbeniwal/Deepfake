"""
score_dataset.py — run the full detection pipeline over labeled media and write a
CSV of per-signal scores + label, for train_fusion.py.

Reads training/dataset/{real,fake}, runs analyze_image / analyze_video on each
file, and writes training/fusion_train.csv with columns:
    visual,audio,temporal,frequency,forensic,metadata,label

label = 1 (fake) / 0 (real).

This is the slow step (it runs every model on every file). Use --limit to cap how
many per class so you get a fusion model without scoring the whole dataset.

USAGE:  python score_dataset.py --limit 400
"""

import os, sys, csv, argparse, random

_HERE   = os.path.dirname(os.path.abspath(__file__))
_PARENT = os.path.dirname(_HERE)
sys.path.insert(0, _PARENT)   # import the detector modules
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

_DATASET = os.path.join(_HERE, "dataset")
_OUT     = os.path.join(_HERE, "fusion_train.csv")

_IMG = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
_VID = (".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v")

from fusion_head import FEATURES


def _gather(label_dir, limit):
    files = []
    for root, _d, fs in os.walk(label_dir):
        for fn in fs:
            if os.path.splitext(fn)[1].lower() in (_IMG + _VID):
                files.append(os.path.join(root, fn))
    random.shuffle(files)
    return files[:limit] if limit else files


def _score_one(path):
    from pipeline import analyze_image, analyze_video
    ext = os.path.splitext(path)[1].lower()
    try:
        res = analyze_image(path) if ext in _IMG else analyze_video(path, cleanup=True)
        return res.get("component_scores", {})
    except Exception as e:
        print(f"  skip {os.path.basename(path)}: {e}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=400, help="max files per class (0 = all)")
    args = ap.parse_args()

    real = _gather(os.path.join(_DATASET, "real"), args.limit)
    fake = _gather(os.path.join(_DATASET, "fake"), args.limit)
    if not real or not fake:
        print(f"Need both classes in {_DATASET}. real={len(real)} fake={len(fake)}"); return
    print(f"Scoring {len(real)} real + {len(fake)} fake ...")

    rows = 0
    with open(_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(FEATURES + ["label"])
        for label, files in ((0, real), (1, fake)):
            for i, p in enumerate(files, 1):
                cs = _score_one(p)
                if cs is None:
                    continue
                w.writerow([cs.get(k, "") if cs.get(k) is not None else "" for k in FEATURES] + [label])
                rows += 1
                if i % 25 == 0:
                    print(f"  {'fake' if label else 'real'}: {i}/{len(files)}")

    print(f"\nWrote {rows} rows -> {_OUT}")
    print("Next:  cd ..  &&  python train_fusion.py --csv training/fusion_train.csv")


if __name__ == "__main__":
    main()
