"""
meta_classifier.py — Layer 3: Decision over all signal scores.

Takes the component_scores dict from pipeline.py and applies
calibrated rules to produce a final confidence adjustment.

Catches cases where weighted average under-reports:
  - Multiple signals weakly agree → boost
  - Single signal extremely high → trust it
  - Conflicting signals → reduce confidence
  - Metadata fast-path confirms AI tool → hard boost
"""


def meta_classify(component_scores: dict) -> dict:
    """
    Returns:
      score_override: float|None  — if set, replaces pipeline weighted average
      boost:          float       — additive adjustment to apply
      confidence_adj: float       — multiply final confidence by this (0.5-1.2)
      reason:         str
    """
    cs = {k: v for k, v in component_scores.items() if v is not None}
    if not cs:
        return {"score_override": None, "boost": 0, "confidence_adj": 1.0, "reason": "no signals"}

    scores = list(cs.values())
    n_total     = len(scores)
    n_high      = sum(1 for s in scores if s >= 60)
    n_very_high = sum(1 for s in scores if s >= 75)
    n_low       = sum(1 for s in scores if s <= 25)
    mean_s      = sum(scores) / n_total
    max_s       = max(scores)
    min_s       = min(scores)

    visual   = cs.get("visual",   0) or 0
    audio    = cs.get("audio",    0) or 0
    metadata = cs.get("metadata", 0) or 0
    lipsync  = cs.get("lipsync",  0) or 0
    temporal = cs.get("temporal", 0) or 0
    spn      = cs.get("spn",      0) or 0
    forensic = cs.get("forensic", 0) or 0

    boost = 0.0
    confidence_adj = 1.0
    score_override = None
    reasons = []

    # Rule 1: Strong consensus — 4+ signals all agree fake
    if n_very_high >= 4:
        boost += 8
        confidence_adj = 1.15
        reasons.append(f"strong consensus ({n_very_high} signals ≥75%)")

    elif n_high >= 4:
        boost += 5
        confidence_adj = 1.10
        reasons.append(f"consensus ({n_high} signals ≥60%)")

    # Rule 2: Visual model very confident → anchor result
    if visual >= 85:
        score_override = min(99, visual + 5)
        confidence_adj = 1.20
        reasons.append(f"visual anchor ({visual:.0f}%)")

    # Rule 3: Metadata detected AI tool (hard signal)
    if metadata >= 55:
        score_override = min(99, metadata + 12)
        confidence_adj = 1.30
        reasons.append(f"metadata AI tool ({metadata:.0f}%)")

    # Rule 4: Audio + lipsync both high → voice+face faked together
    if audio >= 65 and lipsync >= 65:
        boost += 6
        reasons.append("audio+lipsync sync mismatch")

    # Rule 5: Conflicting signals → reduce confidence
    if max_s > 70 and min_s < 20 and n_total >= 4:
        confidence_adj = min(confidence_adj, 0.85)
        reasons.append("conflicting signals")

    # Rule 6: All signals low → high real confidence
    if n_low >= max(3, n_total - 1) and mean_s < 25:
        score_override = max(0, mean_s - 5)
        confidence_adj = 1.20
        reasons.append(f"high real consensus ({n_low} signals ≤25%)")

    # Rule 7: SPN + temporal both high → physical inconsistency
    if spn >= 60 and temporal >= 60:
        boost += 5
        reasons.append("physical noise+temporal mismatch")

    return {
        "score_override": score_override,
        "boost":          round(boost, 1),
        "confidence_adj": round(confidence_adj, 2),
        "reason":         "; ".join(reasons) if reasons else "standard weighted average",
    }
