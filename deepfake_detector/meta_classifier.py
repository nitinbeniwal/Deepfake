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

    # NOTE: pipeline strips disabled signals (lipsync, spn — weight 0, inverted on
    # compressed video) before calling meta_classify, so rules depending on them
    # could never fire. Those rules were removed. Only live signals are read here.
    visual    = cs.get("visual",    0) or 0
    audio     = cs.get("audio",     0) or 0
    metadata  = cs.get("metadata",  0) or 0
    temporal  = cs.get("temporal",  0) or 0
    forensic  = cs.get("forensic",  0) or 0
    frequency = cs.get("frequency", 0) or 0

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

    # Rule 4: Temporal flicker strongly high → physical inconsistency boost.
    # Temporal is the one heuristic kept live (weight 0.12); a strong reading
    # nudges the verdict up but never overrides the visual models alone.
    if temporal >= 80 and score_override is None:
        boost += 8
        reasons.append(f"temporal inconsistency ({temporal:.0f}%)")

    # Rule 5: Conflicting signals → reduce confidence (no clear consensus).
    if (max_s > 70 and min_s < 20 and n_total >= 4 and score_override is None):
        confidence_adj = min(confidence_adj, 0.85)
        reasons.append("conflicting signals")

    # Rule 6: All signals low → high real confidence
    if n_low >= max(3, n_total - 1) and mean_s < 25:
        score_override = max(0, mean_s - 5)
        confidence_adj = 1.20
        reasons.append(f"high real consensus ({n_low} signals ≤25%)")

    # Rule 7: Frequency / texture anomaly → mild boost (numpy spectral signal).
    if frequency >= 60 and score_override is None:
        boost += 10
        confidence_adj = max(confidence_adj, 1.08)
        reasons.append(f"frequency/texture anomaly ({frequency:.0f}%)")
    elif frequency >= 40 and score_override is None:
        boost += 5
        reasons.append(f"mild texture anomaly ({frequency:.0f}%)")

    return {
        "score_override": score_override,
        "boost":          round(boost, 1),
        "confidence_adj": round(confidence_adj, 2),
        "reason":         "; ".join(reasons) if reasons else "standard weighted average",
    }
