import statistics

def aggregate_results(scores, debug=True):
    valid = [s for s in scores if s is not None]
    if not valid:
        print("⚠️  No faces scored.")
        return {"median_score": None, "verdict": "UNKNOWN - No faces detected",
                "confidence": 0, "frame_count": 0}

    med   = round(statistics.median(valid), 2)
    mean  = round(sum(valid) / len(valid), 2)
    std   = round(statistics.stdev(valid), 2) if len(valid) > 1 else 0
    hi    = sum(1 for s in valid if s > 60)
    hi_p  = round(hi / len(valid) * 100, 1)
    lo    = sum(1 for s in valid if s < 30)
    lo_p  = round(lo / len(valid) * 100, 1)
    mid   = len(valid) - hi - lo

    if debug:
        print(f"\n{'='*50}\nFRAME ANALYSIS  ({len(valid)} frames)\n{'='*50}")
        print(f"Median {med}%  Mean {mean}%  Std {std}%")
        print(f"Real <30% : {lo} ({lo_p}%)")
        print(f"Uncertain : {mid} ({round(mid/len(valid)*100,1)}%)")
        print(f"Fake >60% : {hi} ({hi_p}%)")

    if   med >= 70 and hi_p >= 50: verdict, conf = "🚨 LIKELY FAKE",                  min(99, int(med + hi_p/2))
    elif med >= 60 and hi_p >= 40: verdict, conf = "⚠️  LIKELY FAKE — review needed",  int(med)
    elif med >= 45 or  hi_p >= 35: verdict, conf = "❓ UNCERTAIN — review recommended", int(med)
    elif med < 30  and lo_p >= 60: verdict, conf = "✅ LOOKS REAL",                     100 - int(med)
    else:                          verdict, conf = "✅ LOOKS REAL",                     100 - int(med)

    if debug:
        print(f"\nVerdict: {verdict}  Confidence: {conf}%\n{'='*50}\n")

    return {"median_score": med, "mean_score": mean, "std_score": std,
            "verdict": verdict, "confidence": conf, "frame_count": len(valid),
            "high_fake_count": hi, "high_fake_pct": hi_p, "low_score_pct": lo_p,
            "details": {"real_frames": lo, "uncertain_frames": mid, "fake_frames": hi}}


def aggregate_multimodal(visual, audio=None, forensic=None, metadata=None,
                         temporal=None, lipsync=None, spn=None, debug=True):
    """Weighted combination matching pipeline.py 7-signal weights."""
    parts = [("visual",   visual,   0.40), ("audio",    audio,    0.18),
             ("temporal", temporal, 0.12), ("lipsync",  lipsync,  0.10),
             ("spn",      spn,      0.10), ("forensic", forensic, 0.07),
             ("metadata", metadata, 0.03)]
    tw = ws = 0.0
    for _, s, w in parts:
        if s is not None:
            ws += s * w; tw += w

    if not tw:
        return {"final_score": None, "verdict": "UNKNOWN", "confidence": 0}

    final = round(ws / tw, 2)
    if   final >= 70: verdict, conf = "🚨 LIKELY FAKE",   min(99, int(final))
    elif final >= 50: verdict, conf = "⚠️  LIKELY FAKE",  int(final)
    elif final >= 35: verdict, conf = "❓ UNCERTAIN",      int(final)
    else:             verdict, conf = "✅ LOOKS REAL",     100 - int(final)

    if debug:
        print(f"\nMULTI-MODAL: final={final}%  verdict={verdict}")
        for n, s, w in parts:
            print(f"  {n:10s}: {str(s)+'%':8s} (w={w:.0%})")

    return {"final_score": final, "verdict": verdict, "confidence": conf,
            "components": {n: s for n, s, _ in parts}}


def suggest_calibration_offset(baseline):
    if baseline < 20:
        print("✅ No calibration needed.")
        return {"offset": 0, "fake_threshold": 65, "uncertain_threshold": 45}
    off = int(baseline)
    print(f"⚠️  Baseline {baseline}% too high. Set CALIBRATION_OFFSET={off} in classifier.py")
    return {"offset": off, "fake_threshold": 55, "uncertain_threshold": 30}
