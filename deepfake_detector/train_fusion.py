"""
train_fusion.py — fit the fusion head from labeled per-signal scores.

This is the meta-learner over the detector outputs (the "/btw" XGBoost idea),
trained the safe way: logistic regression first; XGBoost only reported as a
comparison, never shipped unless it BEATS logistic on a held-out split — and even
then we export linear-equivalent coefficients so the server stays dependency-free.

INPUT  (one of):
  --csv  path.csv   columns: visual,audio,temporal,frequency,forensic,metadata,label
                    label = 1 (fake) / 0 (real). Missing cells allowed (blank).
  --from-results    build the table from results/api_results.jsonl + a labels file
                    results/labels.jsonl  ({"filename":..., "label":0|1})

OUTPUT: fusion_model.json  (loaded automatically by fusion_head.py — restart not
needed, it hot-reloads on mtime change).

USAGE:
  python train_fusion.py --csv labeled_scores.csv
  python train_fusion.py --from-results

Needs >= ~200 labeled rows, both classes, to be worth anything. With less it
overfits — script warns and refuses below 40.
"""

import os, sys, json, argparse, csv as _csv, statistics
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

from fusion_head import FEATURES, _MODEL_PATH

_HERE = os.path.dirname(os.path.abspath(__file__))


def _rows_from_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            try:
                label = int(float(r["label"]))
            except (KeyError, ValueError, TypeError):
                continue
            feat = {}
            for k in FEATURES:
                v = r.get(k, "")
                feat[k] = float(v) if v not in ("", None) else None
            rows.append((feat, label))
    return rows


def _rows_from_results():
    res = os.path.join(_HERE, "results", "api_results.jsonl")
    lab = os.path.join(_HERE, "results", "labels.jsonl")
    if not (os.path.exists(res) and os.path.exists(lab)):
        print("Need results/api_results.jsonl AND results/labels.jsonl "
              "({'filename':..,'label':0|1}).")
        return []
    labels = {}
    with open(lab, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line); labels[d["filename"]] = int(d["label"])
            except Exception: pass
    rows = []
    with open(res, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            fn = d.get("filename")
            if fn not in labels:
                continue
            cs = d.get("component_scores") or {}
            feat = {k: (float(cs[k]) if cs.get(k) is not None else None) for k in FEATURES}
            rows.append((feat, labels[fn]))
    return rows


def _standardize(rows, fill):
    cols = {k: [] for k in FEATURES}
    for feat, _ in rows:
        for k in FEATURES:
            v = feat.get(k)
            cols[k].append(fill if v is None else v)
    mean = [statistics.mean(cols[k]) for k in FEATURES]
    std  = [statistics.pstdev(cols[k]) or 1.0 for k in FEATURES]
    X, y = [], []
    for feat, label in rows:
        X.append([(fill if feat.get(k) is None else feat[k]) for k in FEATURES])
        y.append(label)
    return X, y, mean, std


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--from-results", action="store_true")
    ap.add_argument("--fill", type=float, default=50.0, help="value for a missing signal")
    args = ap.parse_args()

    rows = _rows_from_csv(args.csv) if args.csv else (_rows_from_results() if args.from_results else [])
    if not rows:
        print("No labeled rows. Provide --csv or --from-results (with labels.jsonl)."); return
    n_fake = sum(1 for _, l in rows if l == 1)
    n_real = len(rows) - n_fake
    print(f"Loaded {len(rows)} rows  (fake {n_fake} / real {n_real})")
    if len(rows) < 40 or n_fake < 10 or n_real < 10:
        print("Too few labeled rows (need >=40 total, >=10 per class). Refusing — would overfit.")
        return

    try:
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, accuracy_score
    except ImportError:
        print("Install scikit-learn to train:  pip install scikit-learn numpy"); return

    X, y, mean, std = _standardize(rows, args.fill)
    X = np.array(X, float); y = np.array(y, int)
    Xs = (X - np.array(mean)) / np.array(std)

    Xtr, Xte, ytr, yte = train_test_split(Xs, y, test_size=0.2, random_state=42, stratify=y)
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(Xtr, ytr)
    prob = clf.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, prob) if len(set(yte)) > 1 else float("nan")
    acc = accuracy_score(yte, (prob >= 0.5).astype(int))
    print(f"Logistic  held-out AUC={auc:.3f}  acc={acc:.3f}")

    # Optional: compare XGBoost, but DO NOT ship it (keeps serve dependency-free).
    try:
        from xgboost import XGBClassifier
        xgb = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.1,
                            eval_metric="logloss")
        xgb.fit(Xtr, ytr)
        xp = xgb.predict_proba(Xte)[:, 1]
        xauc = roc_auc_score(yte, xp) if len(set(yte)) > 1 else float("nan")
        print(f"XGBoost   held-out AUC={xauc:.3f}  (comparison only)")
        if xauc - auc > 0.03:
            print("NOTE: XGBoost meaningfully beats logistic — you have enough data + "
                  "non-linear structure. Consider shipping a tree fusion (needs xgboost "
                  "at serve time); not done automatically.")
    except ImportError:
        pass

    model = {
        "type": "logistic",
        "features": FEATURES,
        "mean": list(map(float, mean)),
        "std": list(map(float, std)),
        "coef": list(map(float, clf.coef_[0])),
        "intercept": float(clf.intercept_[0]),
        "missing_fill": args.fill,
        "heldout_auc": None if auc != auc else round(float(auc), 4),
    }
    tmp = _MODEL_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(model, f, indent=2)
    os.replace(tmp, _MODEL_PATH)
    print(f"Saved fusion model -> {_MODEL_PATH}")
    print("Pipeline will use it automatically on the next analysis (hot-reload).")


if __name__ == "__main__":
    main()
