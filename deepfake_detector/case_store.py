"""
case_store.py — Persistent case file store for cyber-cell deepfake investigations.

Each case is a JSON file under cases/<case_id>.json holding:
  - case metadata (case number, officer, department, suspect/victim, dates, notes)
  - status (OPEN / UNDER REVIEW / CLOSED)
  - evidence list: each uploaded media item with chain-of-custody
    (sha256 hash, uploaded_by, timestamp) and its analysis result.

No external DB — flat JSON files, safe for a single-node local deployment and
trivially auditable / backed up by copying the folder.
"""

import os, json, uuid, hashlib, threading
from datetime import datetime

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases")
os.makedirs(_DIR, exist_ok=True)
_lock = threading.Lock()

STATUSES = ("OPEN", "UNDER REVIEW", "CLOSED")


def _path(case_id):
    return os.path.join(_DIR, f"{case_id}.json")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def create_case(data: dict) -> dict:
    case_id = uuid.uuid4().hex[:12]
    now = datetime.now().isoformat()
    case = {
        "case_id":       case_id,
        "case_no":       data.get("case_no", "").strip(),
        "title":         data.get("title", "").strip(),
        "officer_name":  data.get("officer_name", "").strip(),
        "officer_badge": data.get("officer_badge", "").strip(),
        "department":    data.get("department", "").strip(),
        "suspect":       data.get("suspect", "").strip(),
        "victim":        data.get("victim", "").strip(),
        "source_url":    data.get("source_url", "").strip(),
        "incident_date": data.get("incident_date", "").strip(),
        "priority":      data.get("priority", "MEDIUM").strip().upper() or "MEDIUM",
        "notes":         data.get("notes", "").strip(),
        "status":        "OPEN",
        "created_at":    now,
        "updated_at":    now,
        "evidence":      [],
    }
    with _lock:
        with open(_path(case_id), "w", encoding="utf-8") as f:
            json.dump(case, f, indent=2)
    return case


def get_case(case_id: str):
    p = _path(case_id)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _save(case: dict):
    case["updated_at"] = datetime.now().isoformat()
    with _lock:
        with open(_path(case["case_id"]), "w", encoding="utf-8") as f:
            json.dump(case, f, indent=2)


def list_cases() -> list:
    out = []
    for fn in os.listdir(_DIR):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(_DIR, fn), encoding="utf-8") as f:
                    c = json.load(f)
                out.append({
                    "case_id":   c["case_id"],
                    "case_no":   c.get("case_no", ""),
                    "title":     c.get("title", ""),
                    "status":    c.get("status", "OPEN"),
                    "priority":  c.get("priority", "MEDIUM"),
                    "officer_name": c.get("officer_name", ""),
                    "evidence_count": len(c.get("evidence", [])),
                    "created_at": c.get("created_at", ""),
                    "updated_at": c.get("updated_at", ""),
                })
            except Exception:
                pass
    out.sort(key=lambda c: c.get("updated_at", ""), reverse=True)
    return out


def update_case(case_id: str, fields: dict):
    case = get_case(case_id)
    if not case:
        return None
    for k in ("status", "notes", "priority", "suspect", "victim", "title",
              "officer_name", "officer_badge", "department", "source_url",
              "incident_date", "case_no"):
        if k in fields and fields[k] is not None:
            case[k] = fields[k]
    if case.get("status") not in STATUSES:
        case["status"] = "OPEN"
    _save(case)
    return case


def add_evidence(case_id: str, *, filename: str, file_path: str,
                 uploaded_by: str = "") -> dict:
    """Register an uploaded media item with chain-of-custody before analysis."""
    case = get_case(case_id)
    if not case:
        return None
    ev = {
        "evidence_id": uuid.uuid4().hex[:10],
        "filename":    filename,
        "sha256":      sha256_file(file_path),
        "size_bytes":  os.path.getsize(file_path),
        "uploaded_by": uploaded_by,
        "uploaded_at": datetime.now().isoformat(),
        "status":      "pending",     # pending | running | done | error
        "job_id":      None,
        "result":      None,
    }
    case["evidence"].append(ev)
    _save(case)
    return ev


def set_evidence(case_id: str, evidence_id: str, **fields):
    case = get_case(case_id)
    if not case:
        return None
    for ev in case["evidence"]:
        if ev["evidence_id"] == evidence_id:
            ev.update(fields)
            _save(case)
            return ev
    return None
