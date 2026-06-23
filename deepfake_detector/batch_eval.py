"""Batch eval: run pipeline on dataset/{fake,real}, print scores vs ground truth."""
import os, glob, json, sys
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
from pipeline import analyze_video

DS = r"C:\Users\nbeni\OneDrive\Desktop\deepfake\dataset"

def run(label):
    out = []
    for p in sorted(glob.glob(os.path.join(DS, label, "*"))):
        if not p.lower().endswith((".mp4",".mov",".mkv",".webm",".avi",".m4v")):
            continue
        print(f"\n>>> [{label}] {os.path.basename(p)}", flush=True)
        try:
            r = analyze_video(p, cleanup=True)
            cs = r.get("component_scores", {})
            print(f"    FINAL {r.get('final_score')}  verdict {r.get('verdict')}", flush=True)
            print(f"    visual={cs.get('visual')} audio={cs.get('audio')} temporal={cs.get('temporal')} "
                  f"spn={cs.get('spn')} lipsync={cs.get('lipsync')} forensic={cs.get('forensic')} meta={cs.get('metadata')}", flush=True)
            out.append((label, os.path.basename(p), r.get("final_score"), r.get("verdict"), cs.get("visual")))
        except Exception as e:
            print(f"    ERROR {e}", flush=True)
            out.append((label, os.path.basename(p), None, "ERROR", None))
    return out

if __name__ == "__main__":
    res = run("fake") + run("real")
    print("\n\n================ SUMMARY ================", flush=True)
    for label, fn, score, verdict, vis in res:
        print(f"{label.upper():5s} | final={str(score):6s} | {verdict:12s} | visual={vis} | {fn[:40]}", flush=True)
