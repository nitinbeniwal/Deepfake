"""
report.py — Printable forensic report for a cyber-cell case.

Renders a self-contained HTML page (no external assets) suitable for
browser "Print → Save as PDF". Includes case metadata, per-evidence
analysis verdicts, signal breakdown, and chain-of-custody hashes.
"""

import html
from datetime import datetime


def _esc(v):
    return html.escape(str(v if v is not None else ""))


def _verdict_color(verdict):
    return {
        "FAKE": "#c0392b", "LIKELY FAKE": "#e67e22",
        "UNCERTAIN": "#f1c40f", "REAL": "#27ae60",
    }.get(verdict, "#7f8c8d")


def _evidence_block(ev):
    res = ev.get("result") or {}
    verdict = res.get("verdict", "—")
    score = res.get("final_score")
    score_txt = f"{score:.1f}%" if isinstance(score, (int, float)) else "—"
    color = _verdict_color(verdict)

    comp = res.get("component_scores", {}) or {}
    rows = ""
    for k in ("visual", "audio", "temporal", "lipsync", "spn", "forensic", "metadata"):
        v = comp.get(k)
        vtxt = f"{v:.1f}%" if isinstance(v, (int, float)) else "n/a"
        rows += f"<tr><td>{_esc(k.title())}</td><td>{vtxt}</td></tr>"

    anomalies = res.get("anomalies", []) or []
    anom_html = "".join(f"<li>{_esc(a)}</li>" for a in anomalies) or "<li>None recorded</li>"

    return f"""
    <div class="evidence">
      <div class="ev-head">
        <div>
          <div class="ev-file">{_esc(ev.get('filename'))}</div>
          <div class="ev-meta">Evidence ID: {_esc(ev.get('evidence_id'))} &middot;
            Uploaded {_esc(ev.get('uploaded_at'))} by {_esc(ev.get('uploaded_by') or 'N/A')}</div>
        </div>
        <div class="verdict" style="background:{color}">{_esc(verdict)} &middot; {score_txt}</div>
      </div>
      <div class="ev-body">
        <div class="col">
          <h4>Signal Breakdown</h4>
          <table class="sig">{rows}</table>
        </div>
        <div class="col">
          <h4>Anomalies / Indicators</h4>
          <ul>{anom_html}</ul>
        </div>
      </div>
      <div class="custody">
        <strong>Chain of Custody</strong><br>
        SHA-256: <code>{_esc(ev.get('sha256'))}</code><br>
        Size: {_esc(ev.get('size_bytes'))} bytes &middot; Analysis status: {_esc(ev.get('status'))}
      </div>
    </div>
    """


def render_case_report(case: dict) -> str:
    ev_html = "".join(_evidence_block(e) for e in case.get("evidence", [])) \
        or "<p class='muted'>No evidence attached.</p>"

    fake_count = sum(1 for e in case.get("evidence", [])
                     if (e.get("result") or {}).get("verdict") in ("FAKE", "LIKELY FAKE"))
    total_ev = len(case.get("evidence", []))

    meta_rows = [
        ("Case Number", case.get("case_no")),
        ("Title", case.get("title")),
        ("Status", case.get("status")),
        ("Priority", case.get("priority")),
        ("Investigating Officer", case.get("officer_name")),
        ("Badge / ID", case.get("officer_badge")),
        ("Department / Unit", case.get("department")),
        ("Suspect", case.get("suspect")),
        ("Victim / Complainant", case.get("victim")),
        ("Source / URL", case.get("source_url")),
        ("Incident Date", case.get("incident_date")),
        ("Case Opened", case.get("created_at")),
    ]
    meta_html = "".join(
        f"<tr><th>{_esc(k)}</th><td>{_esc(v) or '—'}</td></tr>" for k, v in meta_rows)

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Forensic Report — {_esc(case.get('case_no') or case.get('case_id'))}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color:#1a1a1a; margin:0;
          padding:40px; max-width:900px; margin:auto; background:#fff; }}
  .banner {{ border-bottom:3px solid #1f3a5f; padding-bottom:16px; margin-bottom:24px; }}
  .banner h1 {{ margin:0; font-size:22px; color:#1f3a5f; letter-spacing:.5px; }}
  .banner .sub {{ color:#555; font-size:13px; margin-top:4px; }}
  .classified {{ float:right; border:2px solid #c0392b; color:#c0392b; font-weight:bold;
                 padding:4px 10px; font-size:12px; letter-spacing:1px; }}
  h2 {{ font-size:15px; color:#1f3a5f; border-bottom:1px solid #ddd; padding-bottom:6px;
        margin-top:32px; text-transform:uppercase; letter-spacing:.5px; }}
  table.meta {{ width:100%; border-collapse:collapse; }}
  table.meta th {{ text-align:left; width:200px; padding:6px 10px; background:#f4f6f9;
                   border:1px solid #e2e6ea; font-weight:600; vertical-align:top; }}
  table.meta td {{ padding:6px 10px; border:1px solid #e2e6ea; }}
  .summary {{ background:#f4f6f9; border-left:4px solid #1f3a5f; padding:14px 18px;
              margin:16px 0; font-size:14px; }}
  .evidence {{ border:1px solid #d7dde3; border-radius:6px; margin:16px 0; overflow:hidden; }}
  .ev-head {{ display:flex; justify-content:space-between; align-items:center;
              background:#f4f6f9; padding:12px 16px; }}
  .ev-file {{ font-weight:600; font-size:14px; }}
  .ev-meta {{ font-size:11px; color:#666; margin-top:2px; }}
  .verdict {{ color:#fff; font-weight:bold; padding:6px 14px; border-radius:4px;
              font-size:13px; white-space:nowrap; }}
  .ev-body {{ display:flex; gap:24px; padding:16px; }}
  .col {{ flex:1; }}
  .col h4 {{ margin:0 0 8px; font-size:12px; color:#1f3a5f; text-transform:uppercase; }}
  table.sig {{ width:100%; border-collapse:collapse; font-size:13px; }}
  table.sig td {{ padding:4px 8px; border-bottom:1px solid #eee; }}
  table.sig td:last-child {{ text-align:right; font-variant-numeric:tabular-nums; }}
  ul {{ margin:0; padding-left:18px; font-size:13px; }}
  .custody {{ background:#fffbe6; border-top:1px solid #f0e6b0; padding:10px 16px;
              font-size:11px; }}
  code {{ font-family:Consolas,monospace; word-break:break-all; }}
  .muted {{ color:#888; }}
  .footer {{ margin-top:40px; border-top:1px solid #ddd; padding-top:12px;
             font-size:11px; color:#777; }}
  .sign {{ margin-top:40px; display:flex; gap:60px; }}
  .sign div {{ flex:1; border-top:1px solid #333; padding-top:6px; font-size:12px; }}
  @media print {{ body {{ padding:0; }} .classified {{ -webkit-print-color-adjust:exact; }} }}
</style></head><body>
  <div class="banner">
    <div class="classified">CONFIDENTIAL</div>
    <h1>CYBER CRIME CELL — DEEPFAKE FORENSIC ANALYSIS REPORT</h1>
    <div class="sub">Generated {_esc(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))} &middot;
      Report ref: {_esc(case.get('case_id'))}</div>
  </div>

  <h2>Case Particulars</h2>
  <table class="meta">{meta_html}</table>

  <h2>Investigation Summary</h2>
  <div class="summary">
    {total_ev} item(s) of media evidence analysed.
    <strong>{fake_count}</strong> assessed as manipulated (FAKE / LIKELY FAKE).
    {_esc(case.get('notes') or '')}
  </div>

  <h2>Evidence Analysis</h2>
  {ev_html}

  <div class="sign">
    <div>Analysing Officer<br><br>{_esc(case.get('officer_name') or '')}</div>
    <div>Reviewed By<br><br></div>
  </div>

  <div class="footer">
    This report was produced by an automated multi-modal deepfake detection system
    (visual CNN/ViT ensemble, audio, temporal, sensor-noise and metadata analysis).
    Scores are probabilistic indicators and should be corroborated with additional
    forensic examination before evidentiary use.
  </div>
</body></html>"""
