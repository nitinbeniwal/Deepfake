"""
download_datasets.py — pull the curated deepfake datasets onto the training box.

Reads credentials from environment (loaded by run_all.bat from creds.env) or from
~/.kaggle/kaggle.json. Downloads into  training/datasets/<name>/ .

Toggle datasets with the ENABLED dict below. Kaggle sets need the Kaggle token;
HF sets need HF_TOKEN for speed (public ones work without). The big ModelScope
DDL set is OFF by default (it is huge — turn on only with lots of disk + time).

USAGE:  python download_datasets.py            # downloads all ENABLED
        python download_datasets.py --only faceforensicspp deepfakefusion
"""

import os, sys, subprocess, argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEST = os.path.join(_HERE, "datasets")

# name -> (source, identifier, enabled)
#   source "kaggle" : Kaggle dataset slug
#   source "hf"     : HuggingFace dataset repo id
#   source "modelscope": ModelScope dataset id
DATASETS = {
    # ── Kaggle (need Kaggle token) ──
    "faceforensicspp":   ("kaggle", "khan1803115/faceforensic",                      True),
    "deepfakefusion":    ("kaggle", "ajaysonicu/deepfakefusion-399k-realfake-faces", True),
    "cropped":           ("kaggle", "ucimachinelearning/deep-fake-detection-cropped-dataset", True),
    "stylegan3":         ("kaggle", "troykueh/real-vs-fake-faces-stylegan3",         True),
    "df2026":            ("kaggle", "chuneeb/deepfake-detection-dataset-2026",       True),
    "generic1":          ("kaggle", "prince7489/deepfake-detection-dataset",         False),
    # ── HuggingFace (HF_TOKEN optional) ──
    "df2026_images_hf":  ("hf",     "TacoGido/deepfake-detection-2026-images",       True),
    "frameviews_hf":     ("hf",     "gonnerthetooner/deepfake-frame-views-balanced-fusion-v1", False),
    # ── ModelScope (huge — DDL 1.8M, 88 techniques) ──
    "ddl":               ("modelscope", "DDLteam/DDL_dataset",                       False),
}


def _kaggle(slug, dest):
    os.makedirs(dest, exist_ok=True)
    print(f"[kaggle] {slug} -> {dest}")
    # kaggle reads ~/.kaggle/kaggle.json or KAGGLE_USERNAME/KAGGLE_KEY env automatically
    r = subprocess.run([sys.executable, "-m", "kaggle", "datasets", "download",
                        "-d", slug, "-p", dest, "--unzip"], capture_output=False)
    return r.returncode == 0


def _hf(repo, dest):
    os.makedirs(dest, exist_ok=True)
    print(f"[hf] {repo} -> {dest}")
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=repo, repo_type="dataset", local_dir=dest,
                          token=os.environ.get("HF_TOKEN") or None,
                          local_dir_use_symlinks=False)
        return True
    except Exception as e:
        print(f"[hf] FAILED {repo}: {e}")
        return False


def _modelscope(ds_id, dest):
    os.makedirs(dest, exist_ok=True)
    print(f"[modelscope] {ds_id} -> {dest}  (large!)")
    try:
        from modelscope.msdatasets import MsDataset
        MsDataset.load(ds_id, cache_dir=dest)
        return True
    except Exception as e:
        print(f"[modelscope] FAILED {ds_id}: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="download only these names")
    args = ap.parse_args()

    os.makedirs(_DEST, exist_ok=True)
    todo = []
    for name, (src, ident, enabled) in DATASETS.items():
        if args.only:
            if name in args.only: todo.append((name, src, ident))
        elif enabled:
            todo.append((name, src, ident))

    if not todo:
        print("Nothing selected. Enable datasets in DATASETS or pass --only <name>."); return

    print(f"Downloading {len(todo)} dataset(s) into {_DEST}\n")
    ok = fail = 0
    for name, src, ident in todo:
        dest = os.path.join(_DEST, name)
        success = (_kaggle(ident, dest) if src == "kaggle" else
                   _hf(ident, dest)     if src == "hf" else
                   _modelscope(ident, dest))
        if success: ok += 1; print(f"  OK   {name}\n")
        else:       fail += 1; print(f"  FAIL {name}\n")

    print(f"Done. {ok} ok, {fail} failed.")
    print("Next:  python prepare_dataset.py   (sorts everything into dataset/real and dataset/fake)")


if __name__ == "__main__":
    main()
