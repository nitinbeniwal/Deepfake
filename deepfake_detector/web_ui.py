DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SENTINEL — Deepfake Detection Platform</title>
<style>
:root{
  --bg:#090c13;--bg2:#0e1219;--bg3:#141a26;--bg4:#1a2233;
  --border:#1c2535;--border2:#243048;
  --cyan:#00d4ff;--red:#ff2d55;--orange:#ff6b35;
  --green:#00e676;--yellow:#ffca28;
  --muted:#3d5166;--text:#dde4ef;--text2:#8899aa;
  --font:system-ui,-apple-system,'Segoe UI',sans-serif;
  --mono:'JetBrains Mono','Fira Code','Courier New',monospace;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--text);font-family:var(--font);font-size:14px;line-height:1.5}

/* Layout */
.app{display:grid;grid-template-rows:52px 1fr;height:100vh}
.body{display:grid;grid-template-columns:210px 1fr;overflow:hidden}

/* Header */
header{
  display:flex;align-items:center;justify-content:space-between;
  padding:0 20px;background:var(--bg2);border-bottom:1px solid var(--border);z-index:10
}
.brand{display:flex;align-items:center;gap:10px}
.brand-logo{
  width:28px;height:28px;border-radius:6px;
  background:linear-gradient(135deg,var(--red),var(--orange));
  display:grid;place-items:center;font-size:13px;font-weight:900;color:#fff
}
.brand-name{font-size:14px;font-weight:700;letter-spacing:2px}
.brand-sub{font-size:9px;letter-spacing:1px;color:var(--text2)}
.header-right{display:flex;align-items:center;gap:16px}
.online-pill{
  display:flex;align-items:center;gap:5px;padding:3px 10px;border-radius:20px;
  background:rgba(0,230,118,.08);border:1px solid rgba(0,230,118,.25);
  font-size:10px;font-weight:700;color:var(--green);letter-spacing:1px
}
.online-dot{width:5px;height:5px;border-radius:50%;background:var(--green);animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.clock{font-family:var(--mono);font-size:11px;color:var(--text2)}

/* Sidebar */
nav{
  background:var(--bg2);border-right:1px solid var(--border);
  padding:12px 8px;display:flex;flex-direction:column;gap:1px;overflow-y:auto
}
.nav-label{font-size:9px;font-weight:700;letter-spacing:1.5px;color:var(--muted);padding:10px 8px 4px;text-transform:uppercase}
.nav-link{
  display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:7px;
  text-decoration:none;color:var(--text2);font-size:12px;font-weight:500;cursor:pointer;
  border:none;background:none;width:100%;text-align:left;transition:all .12s
}
.nav-link:hover{background:var(--bg3);color:var(--text)}
.nav-link.active{background:var(--bg3);color:var(--cyan);border-left:2px solid var(--cyan)}
.nav-icon{font-size:13px;width:16px;text-align:center}
nav hr{border:none;border-top:1px solid var(--border);margin:8px 0}
.nav-footer{margin-top:auto;padding:10px 8px;font-size:10px;color:var(--muted)}

/* Main */
main{overflow-y:auto;padding:22px}
.section-title{
  font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
  color:var(--text2);margin-bottom:16px;display:flex;align-items:center;gap:8px
}
.section-title::after{content:'';flex:1;height:1px;background:var(--border)}

/* Upload card */
.card{
  background:var(--bg2);border:1px solid var(--border);
  border-radius:12px;padding:20px;margin-bottom:18px
}
.drop-zone{
  border:2px dashed var(--border2);border-radius:10px;padding:44px 20px;
  text-align:center;cursor:pointer;transition:all .2s;background:var(--bg3);
  position:relative;user-select:none
}
.drop-zone:hover,.drop-zone.over{border-color:var(--cyan);background:rgba(0,212,255,.04)}
.drop-zone input[type=file]{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}
.drop-icon{font-size:32px;margin-bottom:10px;opacity:.4}
.drop-title{font-size:15px;font-weight:600;color:var(--text);margin-bottom:4px}
.drop-sub{font-size:11px;color:var(--muted)}
.file-badge{
  display:none;margin-top:12px;padding:8px 14px;border-radius:8px;
  background:var(--bg4);border:1px solid var(--border2);
  font-family:var(--mono);font-size:12px;color:var(--cyan);
  display:none;align-items:center;gap:8px
}
.scan-btn{
  display:flex;align-items:center;justify-content:center;gap:8px;
  margin-top:14px;padding:11px 28px;border-radius:8px;border:none;
  background:linear-gradient(135deg,var(--red),var(--orange));
  color:#fff;font-size:13px;font-weight:700;cursor:pointer;
  letter-spacing:.5px;transition:opacity .15s;width:100%
}
.scan-btn:hover{opacity:.88}
.scan-btn:disabled{opacity:.3;cursor:not-allowed}

/* Progress */
.progress-card{display:none}
.prog-header{display:flex;align-items:flex-start;gap:12px;margin-bottom:16px}
.spinner{
  width:20px;height:20px;flex-shrink:0;margin-top:2px;
  border:2px solid var(--border2);border-top-color:var(--cyan);
  border-radius:50%;animation:spin .8s linear infinite
}
@keyframes spin{to{transform:rotate(360deg)}}
.prog-title{font-size:13px;font-weight:600;color:var(--text)}
.prog-sub{font-size:11px;color:var(--text2);margin-top:2px}
.prog-bar-wrap{height:4px;background:var(--bg3);border-radius:2px;overflow:hidden;margin-bottom:14px}
.prog-bar{height:100%;background:linear-gradient(90deg,var(--cyan),var(--green));border-radius:2px;transition:width .6s}
.stage-chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{
  font-size:10px;padding:3px 10px;border-radius:10px;font-weight:600;letter-spacing:.3px;
  border:1px solid var(--border);color:var(--muted);transition:all .3s
}
.chip.active{border-color:var(--cyan);color:var(--cyan);background:rgba(0,212,255,.08)}
.chip.done{border-color:var(--green);color:var(--green);background:rgba(0,230,118,.07)}

/* Results */
.results-card{display:none}
.verdict-row{
  display:flex;align-items:center;flex-wrap:wrap;gap:16px;
  padding-bottom:18px;margin-bottom:18px;border-bottom:1px solid var(--border)
}
.verdict-badge{
  font-size:20px;font-weight:900;letter-spacing:1px;padding:8px 20px;
  border-radius:8px;text-transform:uppercase
}
.v-fake{background:rgba(255,45,85,.15);color:var(--red);border:1px solid rgba(255,45,85,.4)}
.v-likely{background:rgba(255,107,53,.12);color:var(--orange);border:1px solid rgba(255,107,53,.35)}
.v-uncertain{background:rgba(255,202,40,.1);color:var(--yellow);border:1px solid rgba(255,202,40,.35)}
.v-real{background:rgba(0,230,118,.08);color:var(--green);border:1px solid rgba(0,230,118,.3)}
.score-big{font-family:var(--mono);font-size:38px;font-weight:800}
.verdict-meta{display:flex;flex-direction:column;gap:4px}
.verdict-file{font-size:12px;color:var(--text2);max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fast-tag{
  display:inline-block;padding:2px 8px;border-radius:4px;
  font-size:9px;font-weight:700;letter-spacing:1px;
  background:rgba(0,212,255,.08);color:var(--cyan);border:1px solid rgba(0,212,255,.3)
}

/* Signal bars */
.sig-grid{display:flex;flex-direction:column;gap:11px;margin-bottom:16px}
.sig-row{display:grid;grid-template-columns:82px 1fr 46px 36px;align-items:center;gap:10px}
.sig-name{font-size:10px;font-weight:700;letter-spacing:.5px;text-transform:uppercase;color:var(--text2)}
.sig-bar-bg{background:var(--bg3);border-radius:3px;height:7px;overflow:hidden}
.sig-bar{height:100%;border-radius:3px;transition:width .7s}
.bar-r{background:linear-gradient(90deg,#c0102e,var(--red))}
.bar-o{background:linear-gradient(90deg,var(--orange),var(--yellow))}
.bar-g{background:linear-gradient(90deg,#00b248,var(--green))}
.sig-pct{font-family:var(--mono);font-size:12px;font-weight:700;text-align:right}
.sig-wt{font-size:9px;color:var(--muted);text-align:right}

/* Anomalies */
.anomalies-section{padding-top:14px;border-top:1px solid var(--border);margin-top:14px}
.anomaly-pill{
  display:inline-flex;align-items:center;gap:4px;margin:3px;
  padding:3px 10px;border-radius:10px;font-size:10px;font-weight:600;
  background:rgba(255,202,40,.07);color:var(--yellow);border:1px solid rgba(255,202,40,.25)
}

/* History */
.hist-card{background:var(--bg2);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.hist-header{
  display:flex;align-items:center;justify-content:space-between;
  padding:12px 16px;border-bottom:1px solid var(--border)
}
.hist-title{font-size:12px;font-weight:700;letter-spacing:.5px}
table{width:100%;border-collapse:collapse}
th{
  padding:8px 14px;text-align:left;font-size:9px;font-weight:700;
  letter-spacing:1px;text-transform:uppercase;color:var(--muted);
  border-bottom:1px solid var(--border);background:var(--bg)
}
td{padding:10px 14px;font-size:11px;color:var(--text2);border-bottom:1px solid var(--border);vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:var(--bg3)}
.pill{
  display:inline-block;padding:2px 8px;border-radius:9px;
  font-size:10px;font-weight:700;font-family:var(--mono)
}
.p-fake{background:rgba(255,45,85,.1);color:var(--red);border:1px solid rgba(255,45,85,.3)}
.p-likely{background:rgba(255,107,53,.1);color:var(--orange);border:1px solid rgba(255,107,53,.3)}
.p-unc{background:rgba(255,202,40,.08);color:var(--yellow);border:1px solid rgba(255,202,40,.25)}
.p-real{background:rgba(0,230,118,.08);color:var(--green);border:1px solid rgba(0,230,118,.25)}
.empty{padding:36px;text-align:center;color:var(--muted);font-size:12px}

::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:3px}
</style>
</head>
<body>
<div class="app">

<!-- Header -->
<header>
  <div class="brand">
    <div class="brand-logo">S</div>
    <div>
      <div class="brand-name">SENTINEL</div>
      <div class="brand-sub">DEEPFAKE INTELLIGENCE PLATFORM</div>
    </div>
  </div>
  <div class="header-right">
    <div class="online-pill"><div class="online-dot"></div>ONLINE</div>
    <div class="clock" id="clock">--:--:--</div>
  </div>
</header>

<div class="body">

<!-- Sidebar -->
<nav>
  <div class="nav-label">Detection</div>
  <button class="nav-link active" id="navScan" onclick="navSwitch('scan',this)">
    <span class="nav-icon">&#9651;</span>Scan Target
  </button>
  <button class="nav-link" id="navHistory" onclick="navSwitch('history',this)">
    <span class="nav-icon">&#9670;</span>Scan History
  </button>
  <hr>
  <div class="nav-label">System</div>
  <a class="nav-link" href="/docs" target="_blank">
    <span class="nav-icon">&#8862;</span>API Docs
  </a>
  <a class="nav-link" href="/health" target="_blank">
    <span class="nav-icon">&#9829;</span>Health Check
  </a>
  <div class="nav-footer">
    v2.0 &middot; 7-Signal Pipeline<br>
    5-Model Visual Ensemble
  </div>
</nav>

<!-- Main Content -->
<main>

  <!-- SCAN PANEL -->
  <div id="scanPanel">
    <div class="section-title">Scan Target</div>

    <!-- Upload -->
    <div class="card">
      <div class="drop-zone" id="dropZone">
        <input type="file" id="fileInput" accept=".mp4,.avi,.mov,.mkv,.webm,.m4v">
        <div class="drop-icon">&#8679;</div>
        <div class="drop-title">Drop video here or click to browse</div>
        <div class="drop-sub">MP4 &nbsp;&middot;&nbsp; AVI &nbsp;&middot;&nbsp; MOV &nbsp;&middot;&nbsp; MKV &nbsp;&middot;&nbsp; WEBM &nbsp;&middot;&nbsp; M4V &nbsp;&middot;&nbsp; Max 500 MB</div>
      </div>
      <div class="file-badge" id="fileBadge">
        <span>&#9654;</span><span id="fileNameText"></span>
      </div>
      <button class="scan-btn" id="scanBtn" disabled onclick="startScan()">
        &#9654;&nbsp;&nbsp;ANALYZE VIDEO
      </button>
    </div>

    <!-- Progress -->
    <div class="card progress-card" id="progressCard">
      <div class="prog-header">
        <div class="spinner"></div>
        <div>
          <div class="prog-title" id="progTitle">Submitting file&hellip;</div>
          <div class="prog-sub" id="progSub">Please wait &mdash; analysis runs in background</div>
        </div>
      </div>
      <div class="prog-bar-wrap">
        <div class="prog-bar" id="progBar" style="width:0%"></div>
      </div>
      <div class="stage-chips">
        <div class="chip" id="ch-meta">Metadata</div>
        <div class="chip" id="ch-visual">Visual Models</div>
        <div class="chip" id="ch-audio">Audio</div>
        <div class="chip" id="ch-temporal">Temporal</div>
        <div class="chip" id="ch-lipsync">Lip-sync</div>
        <div class="chip" id="ch-spn">SPN</div>
        <div class="chip" id="ch-forensic">Forensic</div>
      </div>
    </div>

    <!-- Results -->
    <div class="card results-card" id="resultsCard">
      <div id="resultsInner"></div>
    </div>
  </div>

  <!-- HISTORY PANEL -->
  <div id="historyPanel" style="display:none">
    <div class="section-title">Scan History</div>
    <div class="hist-card">
      <div class="hist-header">
        <div class="hist-title">RECENT SCANS</div>
        <button class="nav-link" style="width:auto;padding:4px 10px;font-size:11px" onclick="loadHistory()">&#8635; Refresh</button>
      </div>
      <div id="histTable"><div class="empty">Loading&hellip;</div></div>
    </div>
  </div>

</main>
</div>
</div>

<script>
// Clock
setInterval(() => {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-US', {hour12:false});
}, 1000);

// Nav switching
function navSwitch(panel, btn) {
  document.getElementById('scanPanel').style.display    = panel === 'scan'    ? '' : 'none';
  document.getElementById('historyPanel').style.display = panel === 'history' ? '' : 'none';
  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  btn.classList.add('active');
  if (panel === 'history') loadHistory();
}

// Drag and drop
const dz   = document.getElementById('dropZone');
const fi   = document.getElementById('fileInput');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('over'); });
dz.addEventListener('dragleave', () => dz.classList.remove('over'));
dz.addEventListener('drop', e => {
  e.preventDefault(); dz.classList.remove('over');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});
fi.addEventListener('change', () => { if (fi.files[0]) setFile(fi.files[0]); });

const ALLOWED = ['.mp4','.avi','.mov','.mkv','.webm','.m4v'];
let _file = null;

function setFile(f) {
  const ext = '.' + f.name.split('.').pop().toLowerCase();
  if (!ALLOWED.includes(ext)) {
    alert('Unsupported type. Allowed: ' + ALLOWED.join(', '));
    return;
  }
  _file = f;
  const badge = document.getElementById('fileBadge');
  badge.style.display = 'flex';
  document.getElementById('fileNameText').textContent =
    f.name + '  (' + (f.size/1024/1024).toFixed(1) + ' MB)';
  document.getElementById('scanBtn').disabled = false;
  document.getElementById('resultsCard').style.display = 'none';
  document.getElementById('progressCard').style.display = 'none';
}

// Scan flow
let _poll = null, _sim = null;

function startScan() {
  if (!_file) return;
  clearInterval(_poll); clearInterval(_sim);

  document.getElementById('progressCard').style.display = 'block';
  document.getElementById('resultsCard').style.display  = 'none';
  document.getElementById('scanBtn').disabled = true;

  ['meta','visual','audio','temporal','lipsync','spn','forensic'].forEach(s => {
    document.getElementById('ch-' + s).className = 'chip';
  });
  setProgress(0, 'Uploading file…', 'Connecting to server');

  const fd = new FormData();
  fd.append('file', _file);

  fetch('/analyze/video', {method:'POST', body:fd})
    .then(r => r.json())
    .then(data => {
      if (data.job_id) {
        setProgress(4, 'Job queued — ID: ' + data.job_id.slice(0,8) + '…',
                    'Analysis running in background · auto-updating');
        simulateProgress();
        _poll = setInterval(() => pollJob(data.job_id), 4000);
      } else if (data.final_score !== undefined) {
        showResult(data);
      } else {
        showError('Server error: ' + JSON.stringify(data));
      }
    })
    .catch(e => showError('Upload failed: ' + e));
}

// Stage timing (cumulative seconds)
const STAGES = ['meta','visual','audio','temporal','lipsync','spn','forensic'];
const STAGE_NAMES = [
  'Checking metadata (< 1s)',
  'Running 5-model visual ensemble…',
  'Analyzing audio track…',
  'Temporal consistency analysis…',
  'Lip-sync correlation…',
  'SPN noise fingerprint…',
  'Forensic rules (ELA, frequency…)',
];
const STAGE_AT = [0, 3, 35, 55, 70, 90, 115]; // seconds when each stage activates

function simulateProgress() {
  let t = 0;
  const TOTAL = 150;
  _sim = setInterval(() => {
    t++;
    const pct = Math.min(92, (t / TOTAL) * 100);
    document.getElementById('progBar').style.width = pct + '%';
    // Activate chips
    STAGES.forEach((s, i) => {
      const el = document.getElementById('ch-' + s);
      const next = STAGE_AT[i + 1] ?? TOTAL;
      if (t >= STAGE_AT[i] && t < next) el.className = 'chip active';
      else if (t >= next)               el.className = 'chip done';
    });
    // Update title to current stage
    const cur = STAGES.findLastIndex((_, i) => t >= STAGE_AT[i]);
    if (cur >= 0) setProgress(pct, STAGE_NAMES[cur], 'Elapsed: ' + t + 's · auto-polling every 4s');
  }, 1000);
}

function setProgress(pct, title, sub) {
  document.getElementById('progTitle').textContent = title;
  document.getElementById('progSub').textContent   = sub;
  document.getElementById('progBar').style.width   = pct + '%';
}

function pollJob(jobId) {
  fetch('/jobs/' + jobId).then(r => r.json()).then(data => {
    if (data.status === 'done') {
      clearInterval(_poll); clearInterval(_sim);
      STAGES.forEach(s => document.getElementById('ch-' + s).className = 'chip done');
      document.getElementById('progBar').style.width = '100%';
      setTimeout(() => showResult(data.result), 400);
    } else if (data.status === 'error') {
      clearInterval(_poll); clearInterval(_sim);
      showError(data.error || 'Analysis failed');
    }
  }).catch(() => {});
}

// Helpers
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function barCls(v) { return v >= 70 ? 'bar-r' : v >= 35 ? 'bar-o' : 'bar-g'; }
function barCol(v) { return v >= 70 ? 'var(--red)' : v >= 35 ? 'var(--yellow)' : 'var(--green)'; }
function vCls(v) {
  if (!v) return 'v-uncertain';
  const l = v.toLowerCase().replace(/\s/g,'');
  if (l === 'fake') return 'v-fake';
  if (l.includes('likely')) return 'v-likely';
  if (l === 'real') return 'v-real';
  return 'v-uncertain';
}
function pCls(v) {
  if (!v) return 'p-unc';
  const l = v.toLowerCase().replace(/\s/g,'');
  if (l === 'fake') return 'p-fake';
  if (l.includes('likely')) return 'p-likely';
  if (l === 'real') return 'p-real';
  return 'p-unc';
}

// Signal definitions
const SIGS = [
  {key:'visual',   label:'Visual',   wt:'40%', desc:'5-model ViT ensemble'},
  {key:'audio',    label:'Audio',    wt:'18%', desc:'Deepfake audio classifier'},
  {key:'temporal', label:'Temporal', wt:'12%', desc:'Inter-frame consistency'},
  {key:'lipsync',  label:'Lip-sync', wt:'10%', desc:'Mouth motion vs audio'},
  {key:'spn',      label:'SPN',      wt:'10%', desc:'Sensor noise fingerprint'},
  {key:'forensic', label:'Forensic', wt:' 7%', desc:'8 forensic rules'},
  {key:'metadata', label:'Metadata', wt:' 3%', desc:'Codec / encoder anomalies'},
];

function showResult(r) {
  clearInterval(_poll); clearInterval(_sim);
  document.getElementById('progressCard').style.display = 'none';
  document.getElementById('resultsCard').style.display  = 'block';
  document.getElementById('scanBtn').disabled = false;

  const cs      = r.component_scores || {};
  const verdict = r.verdict || 'UNKNOWN';
  const score   = r.final_score != null ? parseFloat(r.final_score).toFixed(1) : '--';
  const sNum    = parseFloat(score) || 0;
  const vc      = vCls(verdict);

  const sigRows = SIGS.map(sig => {
    const raw = cs[sig.key];
    if (raw == null) return `
      <div class="sig-row">
        <div class="sig-name" title="${esc(sig.desc)}">${esc(sig.label)}</div>
        <div class="sig-bar-bg"><div class="sig-bar" style="width:0%"></div></div>
        <div class="sig-pct" style="color:var(--muted)">N/A</div>
        <div class="sig-wt">${esc(sig.wt)}</div>
      </div>`;
    const v = Math.min(100, Math.round(parseFloat(raw)));
    return `
      <div class="sig-row">
        <div class="sig-name" title="${esc(sig.desc)}">${esc(sig.label)}</div>
        <div class="sig-bar-bg"><div class="sig-bar ${barCls(v)}" style="width:${v}%"></div></div>
        <div class="sig-pct" style="color:${barCol(v)}">${v}%</div>
        <div class="sig-wt">${esc(sig.wt)}</div>
      </div>`;
  }).join('');

  const anom = (r.anomalies || []).slice(0, 10);
  const anomHtml = anom.length
    ? `<div class="anomalies-section">
        <div style="font-size:9px;font-weight:700;letter-spacing:1px;color:var(--muted);margin-bottom:6px">ANOMALIES FLAGGED</div>
        ${anom.map(a => `<span class="anomaly-pill">&#9873; ${esc(a)}</span>`).join('')}
       </div>` : '';

  const fastTag = r.fast_path
    ? `<span class="fast-tag">FAST-PATH &middot; ${esc(r.fast_reason || 'metadata')}</span>` : '';

  const ts = r.timestamp ? new Date(r.timestamp).toLocaleString() : '';

  document.getElementById('resultsInner').innerHTML = `
    <div class="verdict-row">
      <div class="verdict-badge ${vc}">${esc(verdict)}</div>
      <div class="score-big" style="color:${barCol(sNum)}">${score}%</div>
      <div class="verdict-meta">
        <div class="verdict-file" title="${esc(r.filename||r.video_path||'')}">${esc(r.filename||r.video_path||'')}</div>
        ${fastTag}
        <div style="font-size:10px;color:var(--muted)">${esc(ts)}</div>
      </div>
    </div>
    <div style="font-size:9px;font-weight:700;letter-spacing:1px;color:var(--muted);margin-bottom:12px">SIGNAL BREAKDOWN &nbsp;<span style="color:var(--border2)">(hover signal name for description)</span></div>
    <div class="sig-grid">${sigRows}</div>
    ${anomHtml}
  `;

  loadHistory();
}

function showError(msg) {
  document.getElementById('progressCard').style.display = 'none';
  document.getElementById('resultsCard').style.display  = 'block';
  document.getElementById('scanBtn').disabled = false;
  document.getElementById('resultsInner').innerHTML =
    `<div style="padding:16px;color:var(--red);font-size:13px">
      &#9888; ${esc(msg)}<br>
      <span style="font-size:11px;color:var(--muted)">Check /health or /docs for details.</span>
    </div>`;
}

// History
function loadHistory() {
  fetch('/results?limit=25').then(r => r.json()).then(d => renderHistory(d.results || [])).catch(()=>{});
}

function renderHistory(rows) {
  const el = document.getElementById('histTable');
  if (!rows.length) { el.innerHTML = '<div class="empty">No scans yet &mdash; upload a video to start</div>'; return; }
  el.innerHTML = `<table>
    <thead><tr><th>File</th><th>Verdict</th><th>Score</th><th>Visual</th><th>Audio</th><th>Fast</th><th>Timestamp</th></tr></thead>
    <tbody>
    ${rows.map(r => {
      const v  = r.verdict || '–';
      const s  = r.final_score != null ? parseFloat(r.final_score).toFixed(1) : '–';
      const sn = parseFloat(s) || 0;
      const fn = (r.filename || r.video_path || '–').split(/[/\\]/).pop();
      const cs = r.component_scores || {};
      const vis = cs.visual   != null ? Math.round(cs.visual)   + '%' : '–';
      const aud = cs.audio    != null ? Math.round(cs.audio)    + '%' : '–';
      const ts  = r.timestamp ? new Date(r.timestamp).toLocaleString() : '–';
      return `<tr>
        <td style="font-family:var(--mono);max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(fn)}">${esc(fn)}</td>
        <td><span class="pill ${pCls(v)}">${esc(v)}</span></td>
        <td style="font-family:var(--mono);color:${barCol(sn)};font-weight:700">${s}%</td>
        <td style="font-family:var(--mono);font-size:11px;color:var(--text2)">${esc(vis)}</td>
        <td style="font-family:var(--mono);font-size:11px;color:var(--text2)">${esc(aud)}</td>
        <td style="font-size:10px;color:var(--muted)">${r.fast_path ? 'YES' : '–'}</td>
        <td style="font-size:10px;color:var(--muted)">${esc(ts)}</td>
      </tr>`;
    }).join('')}
    </tbody></table>`;
}

loadHistory();
</script>
</body>
</html>"""
