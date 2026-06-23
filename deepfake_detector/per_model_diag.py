"""Per-model diagnostic: each visual model's mean score per video. Reveals which
models actually separate real vs fake on this dataset."""
import os, glob, sys, shutil, statistics
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

from frame_extractor import extract_frames
from face_detector import detect_faces_batch
from classifier import _MODELS, _get_pipe, _score, _calibrate, _unload_model
from PIL import Image

DS = r"C:\Users\nbeni\OneDrive\Desktop\deepfake\dataset"

def faces_for(video):
    wd = "_diag_tmp"
    if os.path.exists(wd): shutil.rmtree(wd)
    os.makedirs(wd+"/fr", exist_ok=True)
    extract_frames(video, wd+"/fr")
    fr = [os.path.join(wd+"/fr", f) for f in sorted(os.listdir(wd+"/fr"))]
    saved = detect_faces_batch(fr, wd+"/fc")
    return [p for p in saved if p], wd

vids = [("fake", p) for p in sorted(glob.glob(os.path.join(DS,"fake","*.mp4")))] + \
       [("real", p) for p in sorted(glob.glob(os.path.join(DS,"real","*.mp4")))]

# table[model] = list of (label, mean_score)
table = {mid: [] for mid,_,_ in _MODELS}
for label, v in vids:
    faces, wd = faces_for(v)
    pils = [Image.open(p).convert("RGB") for p in faces]
    print(f"\n[{label}] {os.path.basename(v)} — {len(pils)} faces", flush=True)
    for mid, w, _ in _MODELS:
        short = mid.split("/")[-1] if "/" in mid else mid
        try:
            pipe = _get_pipe(mid)
            if pipe is None:
                table[mid].append((label, None)); print(f"   {short:45s} DEAD", flush=True); continue
            raw = pipe(pils, batch_size=4)
            sc = [_calibrate(_score(r)) for r in raw]
            sc = [x for x in sc if x is not None]
            m = round(statistics.mean(sc),1) if sc else None
            table[mid].append((label, m))
            print(f"   {short:45s} {m}", flush=True)
        except Exception as e:
            table[mid].append((label, None)); print(f"   {short:45s} ERR {e}", flush=True)
        finally:
            _unload_model(mid)
    shutil.rmtree(wd, ignore_errors=True)

print("\n\n===== SEPARATION (mean fake vs mean real; want fake>>real) =====", flush=True)
for mid,_,_ in _MODELS:
    short = mid.split("/")[-1] if "/" in mid else mid
    fakes = [s for l,s in table[mid] if l=="fake" and s is not None]
    reals = [s for l,s in table[mid] if l=="real" and s is not None]
    if not fakes or not reals:
        print(f"{short:45s} insufficient/dead"); continue
    mf, mr = statistics.mean(fakes), statistics.mean(reals)
    print(f"{short:45s} fake_avg={mf:5.1f}  real_avg={mr:5.1f}  sep={mf-mr:+5.1f}", flush=True)
