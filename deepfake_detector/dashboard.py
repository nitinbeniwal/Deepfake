"""
dashboard.py — SOC-style Flask web dashboard for deepfake detection.
Run: python dashboard.py  →  http://localhost:5000
"""
from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import pandas as pd
import os, json
from datetime import datetime

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB upload limit

RESULTS_FILE  = "results/scan_results.csv"
APPROVED_FILE = "results/approved_removals.csv"
API_BASE      = os.environ.get("API_BASE", "http://localhost:8000")

# ── SOC Dashboard HTML ────────────────────────────────────────────────────────
TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="30">
<title>SENTINEL — Deepfake Detection Platform</title>
<style>
  :root {
    --bg:      #0a0d14;
    --bg2:     #0f1420;
    --bg3:     #161c2d;
    --border:  #1e2a3a;
    --cyan:    #00d4ff;
    --red:     #ff2d55;
    --green:   #00e676;
    --yellow:  #ffca28;
    --muted:   #4a5568;
    --text:    #e2e8f0;
    --text2:   #94a3b8;
    --font:    'Inter', 'Segoe UI', system-ui, sans-serif;
    --mono:    'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; background: var(--bg); color: var(--text); font-family: var(--font); font-size: 14px; }

  /* ── Layout ── */
  .layout { display: grid; grid-template-rows: 56px 1fr; min-height: 100vh; }
  .main   { display: grid; grid-template-columns: 220px 1fr; overflow: hidden; }

  /* ── Top Bar ── */
  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 24px; background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }
  .topbar-brand { display: flex; align-items: center; gap: 10px; }
  .topbar-brand .logo {
    width: 28px; height: 28px; border-radius: 6px;
    background: linear-gradient(135deg, var(--red) 0%, #ff6b35 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; font-weight: 900; color: #fff;
  }
  .topbar-brand span { font-size: 15px; font-weight: 700; letter-spacing: 2px; color: var(--text); }
  .topbar-brand sub  { font-size: 9px; letter-spacing: 1px; color: var(--text2); }
  .topbar-right { display: flex; align-items: center; gap: 16px; }
  .status-pill {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 12px; border-radius: 20px;
    background: rgba(0, 230, 118, 0.1); border: 1px solid rgba(0, 230, 118, 0.3);
    font-size: 11px; font-weight: 600; color: var(--green); letter-spacing: 1px;
  }
  .status-pill .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--green); animation: pulse 2s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .topbar-time { font-family: var(--mono); font-size: 12px; color: var(--text2); }

  /* ── Sidebar ── */
  .sidebar {
    background: var(--bg2); border-right: 1px solid var(--border);
    padding: 20px 0; display: flex; flex-direction: column;
  }
  .nav-section { padding: 0 12px; margin-bottom: 4px; }
  .nav-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px; color: var(--muted); padding: 12px 8px 6px; }
  .nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 9px 12px; border-radius: 8px; cursor: pointer;
    text-decoration: none; color: var(--text2); font-size: 13px; font-weight: 500;
    transition: all .15s;
  }
  .nav-item:hover, .nav-item.active {
    background: var(--bg3); color: var(--text);
  }
  .nav-item.active { border-left: 2px solid var(--cyan); color: var(--cyan); }
  .nav-icon { font-size: 15px; width: 20px; text-align: center; }
  .sidebar-footer {
    margin-top: auto; padding: 16px 20px;
    border-top: 1px solid var(--border);
    font-size: 11px; color: var(--muted);
  }

  /* ── Content ── */
  .content { padding: 24px; overflow-y: auto; }
  .page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
  .page-title { font-size: 20px; font-weight: 700; color: var(--text); }
  .page-subtitle { font-size: 12px; color: var(--text2); margin-top: 2px; }
  .refresh-btn {
    display: flex; align-items: center; gap: 6px;
    padding: 8px 16px; border-radius: 8px; border: 1px solid var(--border);
    background: var(--bg3); color: var(--text2); cursor: pointer;
    font-size: 12px; text-decoration: none; transition: all .15s;
  }
  .refresh-btn:hover { border-color: var(--cyan); color: var(--cyan); }

  /* ── Stats Grid ── */
  .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
  .stat-card {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 12px; padding: 20px;
  }
  .stat-card.danger  { border-color: rgba(255, 45, 85, 0.3);  background: rgba(255, 45, 85, 0.05);  }
  .stat-card.safe    { border-color: rgba(0, 230, 118, 0.3); background: rgba(0, 230, 118, 0.05); }
  .stat-card.warn    { border-color: rgba(255, 202, 40, 0.3); background: rgba(255, 202, 40, 0.05); }
  .stat-card.info    { border-color: rgba(0, 212, 255, 0.3);  background: rgba(0, 212, 255, 0.05);  }
  .stat-label { font-size: 11px; font-weight: 600; letter-spacing: 1px; color: var(--text2); text-transform: uppercase; }
  .stat-value { font-size: 32px; font-weight: 800; font-family: var(--mono); margin: 8px 0 4px; }
  .stat-card.danger .stat-value  { color: var(--red);    }
  .stat-card.safe   .stat-value  { color: var(--green);  }
  .stat-card.warn   .stat-value  { color: var(--yellow); }
  .stat-card.info   .stat-value  { color: var(--cyan);   }
  .stat-sub { font-size: 11px; color: var(--muted); }

  /* ── Panel ── */
  .panel {
    background: var(--bg2); border: 1px solid var(--border);
    border-radius: 12px; margin-bottom: 20px; overflow: hidden;
  }
  .panel-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 14px 20px; border-bottom: 1px solid var(--border);
  }
  .panel-title { font-size: 13px; font-weight: 700; color: var(--text); letter-spacing: .5px; }
  .panel-badge {
    font-size: 10px; font-weight: 700; padding: 3px 8px;
    border-radius: 12px; background: rgba(255,45,85,.15); color: var(--red);
    border: 1px solid rgba(255,45,85,.3);
  }

  /* ── Table ── */
  .data-table { width: 100%; border-collapse: collapse; }
  .data-table th {
    padding: 10px 16px; text-align: left; font-size: 10px;
    font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    color: var(--muted); border-bottom: 1px solid var(--border);
    background: var(--bg);
  }
  .data-table td {
    padding: 12px 16px; font-size: 12px; color: var(--text2);
    border-bottom: 1px solid var(--border);
    vertical-align: middle;
  }
  .data-table tr:last-child td { border-bottom: none; }
  .data-table tr:hover td { background: var(--bg3); }
  .data-table .mono { font-family: var(--mono); }

  /* ── Score Badge ── */
  .score-badge {
    display: inline-flex; align-items: center; gap: 4px;
    padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 700; font-family: var(--mono);
  }
  .score-fake     { background: rgba(255,45,85,.15);  color: var(--red);    border: 1px solid rgba(255,45,85,.3);  }
  .score-real     { background: rgba(0,230,118,.12);  color: var(--green);  border: 1px solid rgba(0,230,118,.3);  }
  .score-warn     { background: rgba(255,202,40,.12); color: var(--yellow); border: 1px solid rgba(255,202,40,.3); }

  /* ── Verdict Tag ── */
  .verdict-tag {
    display: inline-block; padding: 3px 8px; border-radius: 4px;
    font-size: 10px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase;
  }
  .v-fake { background: rgba(255,45,85,.15); color: var(--red); }
  .v-real { background: rgba(0,230,118,.1);  color: var(--green); }
  .v-unc  { background: rgba(255,202,40,.1); color: var(--yellow); }

  /* ── Action Btns ── */
  .action-btn {
    padding: 5px 12px; border-radius: 6px; border: 1px solid; cursor: pointer;
    font-size: 11px; font-weight: 600; transition: all .15s; background: transparent;
  }
  .action-approve { border-color: rgba(255,45,85,.4); color: var(--red); }
  .action-approve:hover { background: rgba(255,45,85,.1); }
  .action-reject  { border-color: var(--border); color: var(--muted); }
  .action-reject:hover  { background: var(--bg3); color: var(--text2); }

  /* ── Upload Panel ── */
  .upload-form {
    display: grid; grid-template-columns: 1fr auto; gap: 12px; align-items: center;
    padding: 20px;
  }
  .upload-row { display: flex; gap: 12px; align-items: center; }
  .file-input-wrap {
    flex: 1; border: 1px dashed var(--border); border-radius: 8px;
    padding: 12px 16px; background: var(--bg);
    display: flex; align-items: center; gap: 10px;
    color: var(--text2); font-size: 12px; cursor: pointer;
    transition: border-color .15s;
  }
  .file-input-wrap:hover { border-color: var(--cyan); color: var(--cyan); }
  .file-input-wrap input { position: absolute; opacity: 0; cursor: pointer; }
  .scan-btn {
    padding: 10px 24px; border-radius: 8px; border: none; cursor: pointer;
    background: linear-gradient(135deg, var(--red) 0%, #ff6b35 100%);
    color: #fff; font-size: 13px; font-weight: 700; letter-spacing: .5px;
    transition: opacity .15s;
  }
  .scan-btn:hover { opacity: .85; }

  /* ── Threat Bar ── */
  .threat-bar-wrap { padding: 16px 20px; }
  .threat-label { font-size: 11px; color: var(--text2); margin-bottom: 6px; display: flex; justify-content: space-between; }
  .threat-bar { height: 6px; background: var(--bg); border-radius: 3px; overflow: hidden; }
  .threat-fill { height: 100%; border-radius: 3px; transition: width .5s; }
  .threat-low  { background: linear-gradient(90deg, var(--green), #00bcd4); }
  .threat-mid  { background: linear-gradient(90deg, var(--yellow), #ff9800); }
  .threat-high { background: linear-gradient(90deg, var(--red), #ff6b35); }

  /* ── Empty State ── */
  .empty-state { padding: 48px; text-align: center; color: var(--muted); }
  .empty-icon { font-size: 40px; margin-bottom: 12px; opacity: .4; }
  .empty-text { font-size: 13px; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--muted); }
</style>
</head>
<body>
<div class="layout">

  <!-- Top Bar -->
  <header class="topbar">
    <div class="topbar-brand">
      <div class="logo">S</div>
      <div>
        <span>SENTINEL</span><br>
        <sub>DEEPFAKE INTELLIGENCE PLATFORM</sub>
      </div>
    </div>
    <div class="topbar-right">
      <div class="status-pill">
        <div class="dot"></div> SYSTEM ONLINE
      </div>
      <div class="topbar-time" id="clock">{{ now }}</div>
    </div>
  </header>

  <div class="main">

    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="nav-section">
        <div class="nav-label">Operations</div>
        <a class="nav-item active" href="/">
          <span class="nav-icon">◼</span> Dashboard
        </a>
        <a class="nav-item" href="/results">
          <span class="nav-icon">◈</span> Scan Results
        </a>
      </div>
      <div class="nav-section">
        <div class="nav-label">Detection</div>
        <a class="nav-item" href="#upload">
          <span class="nav-icon">▲</span> Scan Target
        </a>
        <a class="nav-item" href="/review_queue">
          <span class="nav-icon">◉</span> Review Queue
          {% if flagged_count > 0 %}
          <span class="panel-badge" style="margin-left:auto">{{ flagged_count }}</span>
          {% endif %}
        </a>
      </div>
      <div class="nav-section">
        <div class="nav-label">System</div>
        <a class="nav-item" href="{{ api_base | e }}/docs" target="_blank">
          <span class="nav-icon">&#8862;</span> API Docs
        </a>
        <a class="nav-item" href="{{ api_base | e }}/health" target="_blank">
          <span class="nav-icon">&#9825;</span> Health Check
        </a>
      </div>
      <div class="sidebar-footer">
        v2.0 · 7-Signal Ensemble<br>
        Auto-refresh: 30s
      </div>
    </aside>

    <!-- Content -->
    <main class="content">
      <div class="page-header">
        <div>
          <div class="page-title">Threat Overview</div>
          <div class="page-subtitle">Real-time deepfake detection · {{ total_scans }} total scans</div>
        </div>
        <a class="refresh-btn" href="/">↻ Refresh</a>
      </div>

      <!-- Stats -->
      <div class="stats-grid">
        <div class="stat-card danger">
          <div class="stat-label">Fake Detected</div>
          <div class="stat-value">{{ fake_count }}</div>
          <div class="stat-sub">{{ fake_pct }}% of all scans</div>
        </div>
        <div class="stat-card safe">
          <div class="stat-label">Verified Real</div>
          <div class="stat-value">{{ real_count }}</div>
          <div class="stat-sub">{{ real_pct }}% of all scans</div>
        </div>
        <div class="stat-card warn">
          <div class="stat-label">Uncertain</div>
          <div class="stat-value">{{ unc_count }}</div>
          <div class="stat-sub">Requires manual review</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">Total Scans</div>
          <div class="stat-value">{{ total_scans }}</div>
          <div class="stat-sub">Approved removals: {{ approved }}</div>
        </div>
      </div>

      <!-- Threat level -->
      {% if total_scans > 0 %}
      <div class="panel" style="margin-bottom:20px">
        <div class="panel-header">
          <div class="panel-title">THREAT LEVEL</div>
          <span style="font-size:11px;color:var(--text2)">Based on fake detection rate</span>
        </div>
        <div class="threat-bar-wrap">
          <div class="threat-label">
            <span>{{ threat_label }}</span>
            <span style="font-family:var(--mono)">{{ fake_pct }}%</span>
          </div>
          <div class="threat-bar">
            <div class="threat-fill {{ threat_class }}" style="width:{{ fake_pct }}%"></div>
          </div>
        </div>
      </div>
      {% endif %}

      <!-- Recent Scans -->
      <div class="panel">
        <div class="panel-header">
          <div class="panel-title">RECENT DETECTIONS</div>
          {% if fake_count > 0 %}
          <span class="panel-badge">{{ fake_count }} FLAGGED</span>
          {% endif %}
        </div>
        {% if items %}
        <table class="data-table">
          <thead>
            <tr>
              <th>Source</th>
              <th>Type</th>
              <th>Score</th>
              <th>Verdict</th>
              <th>Timestamp</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {% for item in items %}
            <tr>
              <td class="mono" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
                  title="{{ item.url | e }}">{{ item.url | e | truncate(40) }}</td>
              <td><span style="font-size:10px;letter-spacing:.5px;color:var(--text2)">{{ item.type | e | upper }}</span></td>
              <td>
                {% set s = item.confidence | float %}
                {% if s >= 60 %}
                  <span class="score-badge score-fake">{{ s }}%</span>
                {% elif s >= 35 %}
                  <span class="score-badge score-warn">{{ s }}%</span>
                {% else %}
                  <span class="score-badge score-real">{{ s }}%</span>
                {% endif %}
              </td>
              <td>
                {% if item.verdict == 'Fake' %}
                  <span class="verdict-tag v-fake">FAKE</span>
                {% elif item.verdict == 'Real' %}
                  <span class="verdict-tag v-real">REAL</span>
                {% else %}
                  <span class="verdict-tag v-unc">UNCERTAIN</span>
                {% endif %}
              </td>
              <td class="mono" style="font-size:11px;color:var(--muted)">{{ item.scanned_at | e }}</td>
              <td>
                {% if item.verdict == 'Fake' %}
                <form method="POST" action="/review" style="display:inline">
                  <input type="hidden" name="url"        value="{{ item.url | e }}">
                  <input type="hidden" name="verdict"    value="{{ item.verdict | e }}">
                  <input type="hidden" name="confidence" value="{{ item.confidence | e }}">
                  <button class="action-btn action-approve" name="action" value="approve">Flag</button>
                </form>
                {% endif %}
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
        {% else %}
        <div class="empty-state">
          <div class="empty-icon">◎</div>
          <div class="empty-text">No scan data yet — run a scan to populate this feed</div>
        </div>
        {% endif %}
      </div>

      <!-- Upload / Quick Scan -->
      <div class="panel" id="upload">
        <div class="panel-header">
          <div class="panel-title">QUICK SCAN</div>
          <span style="font-size:11px;color:var(--text2)">Upload video · async analysis · auto-polls result</span>
        </div>
        <div style="padding:20px">
          <div style="display:flex;gap:12px;align-items:center">
            <label style="flex:1;display:flex;align-items:center;gap:10px;
                          border:1px dashed var(--border);border-radius:8px;
                          padding:12px 16px;cursor:pointer;color:var(--text2);font-size:12px;
                          background:var(--bg);transition:border-color .15s" id="fileLabel">
              <span>&#128193;</span>
              <span id="fileLabelText">Choose video file (MP4, AVI, MOV, MKV)…</span>
              <input type="file" id="videoFile" accept="video/*"
                     style="position:absolute;opacity:0;width:1px"
                     onchange="document.getElementById('fileLabelText').textContent=this.files[0]?.name||'Choose file…'">
            </label>
            <button class="scan-btn" onclick="submitScan()">&#9654; ANALYZE</button>
          </div>
          <!-- Status panel -->
          <div id="scanStatus" style="display:none;margin-top:14px;padding:14px;
               background:var(--bg);border:1px solid var(--border);border-radius:8px;
               font-family:var(--mono);font-size:12px;">
            <div id="statusText" style="color:var(--cyan)">Submitting…</div>
            <div id="resultBox" style="display:none;margin-top:12px"></div>
          </div>
          <p style="margin-top:10px;font-size:11px;color:var(--muted)">
            Analysis runs async (models load on first use — may take 1-3 min). Poll interval: 5s.
          </p>
        </div>
      </div>

    </main>
  </div>
</div>

<script>
  // Live clock
  function tick() {
    const el = document.getElementById('clock');
    if (el) el.textContent = new Date().toLocaleTimeString('en-US', {hour12: false});
  }
  tick(); setInterval(tick, 1000);

  // Async scan
  const API_BASE = '{{ api_base | e }}';
  let _pollTimer = null;

  function submitScan() {
    const fi = document.getElementById('videoFile');
    if (!fi.files.length) { alert('Select a video file first.'); return; }
    const fd = new FormData();
    fd.append('file', fi.files[0]);
    document.getElementById('scanStatus').style.display = 'block';
    document.getElementById('statusText').textContent = 'Submitting to ' + API_BASE + '…';
    document.getElementById('resultBox').style.display = 'none';

    fetch(API_BASE + '/analyze/video', {method:'POST', body:fd})
      .then(r => r.json())
      .then(data => {
        if (data.job_id) {
          document.getElementById('statusText').textContent =
            'Job submitted: ' + data.job_id + ' · polling every 5s…';
          _pollTimer = setInterval(() => pollJob(data.job_id), 5000);
        } else {
          showResult(data);
        }
      })
      .catch(e => {
        document.getElementById('statusText').style.color = 'var(--red)';
        document.getElementById('statusText').textContent = 'Submit failed: ' + e;
      });
  }

  function pollJob(jobId) {
    fetch(API_BASE + '/jobs/' + jobId)
      .then(r => r.json())
      .then(data => {
        const s = data.status;
        document.getElementById('statusText').textContent =
          'Job ' + jobId.slice(0,8) + '… · Status: ' + s.toUpperCase();
        if (s === 'done') {
          clearInterval(_pollTimer);
          showResult(data.result);
        } else if (s === 'error') {
          clearInterval(_pollTimer);
          document.getElementById('statusText').style.color = 'var(--red)';
          document.getElementById('statusText').textContent = 'Error: ' + (data.error || 'unknown');
        }
      })
      .catch(() => {});
  }

  function showResult(r) {
    const verdict = r.verdict || 'UNKNOWN';
    const score   = r.final_score != null ? r.final_score.toFixed(1) : '–';
    const color   = verdict === 'FAKE' ? 'var(--red)' :
                    verdict === 'REAL' ? 'var(--green)' : 'var(--yellow)';
    const box = document.getElementById('resultBox');
    box.style.display = 'block';
    box.innerHTML = `
      <div style="display:flex;gap:16px;align-items:center;margin-bottom:10px">
        <span style="font-size:22px;font-weight:900;color:${color}">${verdict}</span>
        <span style="font-size:18px;color:${color}">${score}%</span>
        ${r.fast_path ? '<span style="font-size:10px;color:var(--muted);background:var(--bg3);padding:2px 6px;border-radius:4px">FAST-PATH</span>' : ''}
      </div>
      <div style="color:var(--text2);margin-bottom:8px">${r.filename || ''}</div>
      ${renderComponents(r.component_scores)}
      ${(r.anomalies||[]).length ? '<div style="margin-top:8px;color:var(--muted);font-size:11px">' +
        r.anomalies.slice(0,5).map(a=>'⚑ '+a).join('<br>') + '</div>' : ''}`;
    document.getElementById('statusText').textContent = 'Analysis complete.';
    document.getElementById('statusText').style.color = 'var(--green)';
  }

  function renderComponents(cs) {
    if (!cs) return '';
    const order = ['visual','audio','temporal','lipsync','spn','forensic','metadata'];
    return '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px">' +
      order.filter(k => cs[k] != null).map(k => {
        const v = cs[k].toFixed(0);
        const c = v >= 70 ? 'var(--red)' : v >= 35 ? 'var(--yellow)' : 'var(--green)';
        return `<span style="padding:2px 8px;border-radius:4px;border:1px solid ${c};
                color:${c};font-size:10px;text-transform:uppercase">${k} ${v}%</span>`;
      }).join('') + '</div>';
  }
</script>
</body>
</html>"""

# ── Routes ───────────────────────────────────────────────────────────────────

def _load_results():
    if not os.path.exists(RESULTS_FILE):
        return pd.DataFrame()
    try:
        return pd.read_csv(RESULTS_FILE)
    except Exception:
        return pd.DataFrame()


@app.route("/")
def index():
    df = _load_results()
    items, total_scans = [], 0
    fake_count = real_count = unc_count = approved = 0

    if not df.empty:
        total_scans = len(df)
        fake_count  = int((df.get("verdict","") == "Fake").sum())
        real_count  = int((df.get("verdict","") == "Real").sum())
        unc_count   = total_scans - fake_count - real_count
        items = df.sort_values("scanned_at", ascending=False).head(50).to_dict("records")

    if os.path.exists(APPROVED_FILE):
        try: approved = len(pd.read_csv(APPROVED_FILE))
        except Exception: pass

    fake_pct = round(100 * fake_count / total_scans, 1) if total_scans else 0
    real_pct = round(100 * real_count / total_scans, 1) if total_scans else 0
    threat_class  = "threat-high" if fake_pct >= 50 else ("threat-mid" if fake_pct >= 25 else "threat-low")
    threat_label  = "CRITICAL" if fake_pct >= 50 else ("ELEVATED" if fake_pct >= 25 else "LOW")

    return render_template_string(
        TEMPLATE,
        items=items, total_scans=total_scans,
        fake_count=fake_count, real_count=real_count,
        unc_count=unc_count, approved=approved,
        fake_pct=fake_pct, real_pct=real_pct,
        flagged_count=fake_count,
        threat_class=threat_class, threat_label=threat_label,
        now=datetime.now().strftime("%H:%M:%S UTC"),
        api_base=API_BASE,
    )


@app.route("/review_queue")
def review_queue():
    df = _load_results()
    if df.empty:
        return redirect(url_for("index"))
    flagged = df[df.get("verdict","") == "Fake"] if "verdict" in df else pd.DataFrame()
    return render_template_string(
        TEMPLATE,
        items=flagged.sort_values("scanned_at", ascending=False).to_dict("records") if not flagged.empty else [],
        total_scans=len(df), fake_count=len(flagged),
        real_count=int((df.get("verdict","") == "Real").sum()),
        unc_count=len(df) - len(flagged) - int((df.get("verdict","") == "Real").sum()),
        approved=0, fake_pct=0, real_pct=0, flagged_count=len(flagged),
        threat_class="threat-high", threat_label="REVIEW QUEUE",
        now=datetime.now().strftime("%H:%M:%S UTC"),
        api_base=API_BASE,
    )


@app.route("/results")
def results_json():
    df = _load_results()
    return jsonify(df.to_dict("records") if not df.empty else [])


@app.route("/review", methods=["POST"])
def review():
    action     = request.form.get("action", "")
    url        = request.form.get("url", "")
    verdict    = request.form.get("verdict", "")
    confidence = request.form.get("confidence", "")

    if action == "approve" and url:
        os.makedirs("results", exist_ok=True)
        row = pd.DataFrame([{
            "url": url, "verdict": verdict, "confidence": confidence,
            "action": "FLAGGED_FOR_REMOVAL",
            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }])
        mode, header = ("a", False) if os.path.exists(APPROVED_FILE) else ("w", True)
        row.to_csv(APPROVED_FILE, mode=mode, header=header, index=False)

    return redirect(url_for("index"))


if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)
    print("SENTINEL dashboard → http://localhost:5000")
    app.run(debug=False, host="0.0.0.0", port=5000)
