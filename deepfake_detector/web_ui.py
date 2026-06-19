DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sentinel — Deepfake Detection</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #0a0a0b;
  --surface:   #111113;
  --surface2:  #18181b;
  --surface3:  #1f1f23;
  --border:    #27272a;
  --border2:   #3f3f46;
  --text:      #fafafa;
  --text2:     #a1a1aa;
  --text3:     #71717a;
  --red:       #f87171;
  --red-bg:    rgba(248,113,113,.08);
  --red-border:rgba(248,113,113,.2);
  --green:     #4ade80;
  --green-bg:  rgba(74,222,128,.07);
  --green-border:rgba(74,222,128,.2);
  --amber:     #fbbf24;
  --amber-bg:  rgba(251,191,36,.07);
  --amber-border:rgba(251,191,36,.2);
  --blue:      #60a5fa;
  --blue-bg:   rgba(96,165,250,.08);
  --blue-border:rgba(96,165,250,.2);
  --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --mono: 'SF Mono','Fira Code','Cascadia Code','Consolas',monospace;
}

html, body { height: 100%; background: var(--bg); color: var(--text); font-family: var(--font); font-size: 13px; line-height: 1.5; -webkit-font-smoothing: antialiased; }

/* ── Top navigation ── */
.topnav {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}
.nav-left  { display: flex; align-items: center; gap: 24px; }
.nav-right { display: flex; align-items: center; gap: 16px; }

.wordmark {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: -.01em;
  color: var(--text);
  text-decoration: none;
}
.wordmark-icon {
  width: 22px;
  height: 22px;
  background: var(--red);
  border-radius: 4px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.wordmark-icon svg { width: 12px; height: 12px; fill: #fff; }

.nav-tabs { display: flex; gap: 2px; }
.tab-btn {
  padding: 5px 12px;
  border: none;
  background: none;
  cursor: pointer;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text3);
  transition: color .15s, background .15s;
}
.tab-btn:hover  { color: var(--text2); background: var(--surface3); }
.tab-btn.active { color: var(--text);  background: var(--surface3); }

.status-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text3);
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--green);
}
.clock-display { font-family: var(--mono); font-size: 11px; color: var(--text3); }
.nav-ext-link {
  font-size: 12px;
  color: var(--text3);
  text-decoration: none;
  padding: 4px 8px;
  border-radius: 5px;
  transition: color .15s, background .15s;
}
.nav-ext-link:hover { color: var(--text2); background: var(--surface3); }

/* ── Main layout ── */
main {
  max-width: 780px;
  margin: 0 auto;
  padding: 28px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ── Cards ── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.card-header {
  padding: 14px 18px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--text3);
}
.card-body { padding: 14px 18px 18px; }

/* ── Upload zone ── */
.upload-zone {
  position: relative;
  border: 1px dashed var(--border2);
  border-radius: 6px;
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color .15s, background .15s;
  background: var(--surface2);
}
.upload-zone:hover,
.upload-zone.drag-over { border-color: var(--blue); background: var(--blue-bg); }
.upload-zone input[type=file] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
  width: 100%;
  height: 100%;
}
.upload-icon { color: var(--text3); font-size: 22px; margin-bottom: 8px; }
.upload-label { font-size: 13px; font-weight: 500; color: var(--text2); margin-bottom: 4px; }
.upload-hint  { font-size: 11px; color: var(--text3); }

.file-row {
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
  padding: 8px 12px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 5px;
}
.file-name { font-family: var(--mono); font-size: 11px; color: var(--text2); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: 11px; color: var(--text3); flex-shrink: 0; }
.clear-btn { background: none; border: none; cursor: pointer; color: var(--text3); font-size: 15px; line-height: 1; padding: 0 4px; }
.clear-btn:hover { color: var(--text); }

.analyze-btn {
  display: block;
  width: 100%;
  margin-top: 12px;
  padding: 9px;
  border: none;
  border-radius: 6px;
  background: var(--red);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  letter-spacing: .01em;
  transition: opacity .15s;
}
.analyze-btn:hover   { opacity: .88; }
.analyze-btn:disabled { opacity: .3; cursor: not-allowed; }

/* ── Progress ── */
.prog-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 14px;
}
.spinner {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin-top: 1px;
  border: 1.5px solid var(--border2);
  border-top-color: var(--blue);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.prog-stage { font-size: 13px; font-weight: 500; color: var(--text); }
.prog-detail { font-size: 11px; color: var(--text3); margin-top: 2px; }
.prog-bar-track {
  height: 2px;
  background: var(--surface3);
  border-radius: 1px;
  overflow: hidden;
  margin-bottom: 12px;
}
.prog-bar-fill {
  height: 100%;
  background: var(--blue);
  border-radius: 1px;
  transition: width .5s;
}
.stage-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.stage-tag {
  font-size: 10px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 3px;
  border: 1px solid var(--border);
  color: var(--text3);
  background: var(--surface2);
  transition: all .2s;
}
.stage-tag.running { border-color: var(--blue-border); color: var(--blue); background: var(--blue-bg); }
.stage-tag.done    { border-color: var(--green-border); color: var(--green); background: var(--green-bg); }

/* ── Result ── */
.verdict-section {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
}
.verdict-label {
  font-size: 18px;
  font-weight: 600;
}
.verdict-fake    { color: var(--red); }
.verdict-likely  { color: var(--amber); }
.verdict-unc     { color: var(--amber); }
.verdict-real    { color: var(--green); }
.verdict-score   { font-family: var(--mono); font-size: 28px; font-weight: 600; }
.verdict-meta    { display: flex; flex-direction: column; gap: 2px; margin-left: auto; text-align: right; }
.verdict-file    { font-size: 11px; color: var(--text3); max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.verdict-ts      { font-size: 10px; color: var(--text3); }
.fast-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
  background: var(--blue-bg);
  color: var(--blue);
  border: 1px solid var(--blue-border);
}

/* ── Signal bars ── */
.sig-section { margin-bottom: 16px; }
.sig-section-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--text3);
  margin-bottom: 10px;
}
.sig-row {
  display: grid;
  grid-template-columns: 72px 1fr 38px 32px;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.sig-name   { font-size: 11px; font-weight: 500; color: var(--text2); }
.sig-track  { height: 4px; background: var(--surface3); border-radius: 2px; overflow: hidden; }
.sig-fill   { height: 100%; border-radius: 2px; transition: width .7s; }
.sig-fill-r { background: var(--red); }
.sig-fill-a { background: var(--amber); }
.sig-fill-g { background: var(--green); }
.sig-fill-n { background: var(--border2); }
.sig-pct    { font-family: var(--mono); font-size: 11px; text-align: right; }
.sig-wt     { font-size: 9px; color: var(--text3); text-align: right; }

/* ── Anomalies ── */
.anomaly-section {
  padding-top: 14px;
  border-top: 1px solid var(--border);
  margin-bottom: 14px;
}
.anomaly-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--text3);
  margin-bottom: 8px;
}
.anomaly-list { display: flex; flex-direction: column; gap: 4px; }
.anomaly-item {
  font-size: 11px;
  color: var(--amber);
  padding: 4px 8px;
  background: var(--amber-bg);
  border: 1px solid var(--amber-border);
  border-radius: 4px;
}

/* ── Feedback section ── */
.feedback-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.feedback-label { font-size: 11px; color: var(--text3); flex: 1; }
.feedback-btn {
  padding: 5px 12px;
  border-radius: 5px;
  border: 1px solid var(--border2);
  background: none;
  color: var(--text2);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all .15s;
}
.feedback-btn:hover { border-color: var(--red-border); color: var(--red); background: var(--red-bg); }

/* Feedback form (inline) */
.feedback-form {
  display: none;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  margin-top: 10px;
}
.feedback-form.open { display: flex; }
.feedback-form-label { font-size: 11px; font-weight: 500; color: var(--text2); }
.verdict-opts { display: flex; gap: 6px; flex-wrap: wrap; }
.verdict-opt {
  padding: 5px 12px;
  border-radius: 4px;
  border: 1px solid var(--border2);
  background: none;
  color: var(--text2);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all .12s;
}
.verdict-opt:hover          { background: var(--surface3); }
.verdict-opt.sel-fake       { border-color: var(--red-border); color: var(--red); background: var(--red-bg); }
.verdict-opt.sel-likely     { border-color: var(--amber-border); color: var(--amber); background: var(--amber-bg); }
.verdict-opt.sel-uncertain  { border-color: var(--amber-border); color: var(--amber); background: var(--amber-bg); }
.verdict-opt.sel-real       { border-color: var(--green-border); color: var(--green); background: var(--green-bg); }
.feedback-note {
  width: 100%;
  padding: 6px 10px;
  background: var(--surface3);
  border: 1px solid var(--border);
  border-radius: 4px;
  color: var(--text);
  font-family: var(--font);
  font-size: 12px;
  resize: none;
}
.feedback-note::placeholder { color: var(--text3); }
.feedback-submit {
  align-self: flex-start;
  padding: 5px 14px;
  border-radius: 5px;
  border: none;
  background: var(--surface3);
  color: var(--text2);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all .12s;
}
.feedback-submit:hover { background: var(--border2); color: var(--text); }
.feedback-thanks { font-size: 11px; color: var(--green); }

/* ── History table ── */
.tbl-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
thead th {
  padding: 8px 14px;
  text-align: left;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--text3);
  border-bottom: 1px solid var(--border);
  background: var(--surface2);
  white-space: nowrap;
}
tbody td {
  padding: 10px 14px;
  font-size: 11px;
  color: var(--text2);
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover td { background: var(--surface2); }
.mono { font-family: var(--mono); }

.verdict-chip {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .02em;
}
.vc-fake    { background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }
.vc-likely  { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.vc-unc     { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.vc-real    { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }

.empty-row td { text-align: center; color: var(--text3); padding: 32px 0; }

/* ── Error state ── */
.error-box {
  padding: 12px 14px;
  background: var(--red-bg);
  border: 1px solid var(--red-border);
  border-radius: 5px;
  font-size: 12px;
  color: var(--red);
}
.error-hint { font-size: 11px; color: var(--text3); margin-top: 4px; }

/* scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 2px; }
</style>
</head>
<body>

<!-- Top nav -->
<nav class="topnav">
  <div class="nav-left">
    <a class="wordmark" href="/">
      <div class="wordmark-icon">
        <svg viewBox="0 0 12 12"><path d="M6 1L1 4v4l5 3 5-3V4L6 1zm0 1.5L10 5v2.5L6 10 2 7.5V5l4-2.5z"/></svg>
      </div>
      Sentinel
    </a>
    <div class="nav-tabs">
      <button class="tab-btn active" id="tab-scan" onclick="switchTab('scan', this)">Scan</button>
      <button class="tab-btn" id="tab-history" onclick="switchTab('history', this)">History</button>
    </div>
  </div>
  <div class="nav-right">
    <div class="status-badge"><div class="status-dot"></div> Online</div>
    <div class="clock-display" id="clock">--:--:--</div>
    <a class="nav-ext-link" href="/docs" target="_blank">API</a>
    <a class="nav-ext-link" href="/health" target="_blank">Health</a>
  </div>
</nav>

<!-- Main -->
<main>

  <!-- ── SCAN PANEL ── -->
  <div id="panel-scan">

    <!-- Upload -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Analyze Video</span>
      </div>
      <div class="card-body">
        <div class="upload-zone" id="dropZone">
          <input type="file" id="fileInput" accept=".mp4,.avi,.mov,.mkv,.webm,.m4v">
          <div class="upload-icon">&#8679;</div>
          <div class="upload-label">Drop video here or click to browse</div>
          <div class="upload-hint">MP4 &middot; AVI &middot; MOV &middot; MKV &middot; WEBM &middot; M4V &mdash; max 500 MB</div>
        </div>
        <div class="file-row" id="fileRow">
          <span class="file-name" id="fileName"></span>
          <span class="file-size" id="fileSize"></span>
          <button class="clear-btn" onclick="clearFile()" title="Remove">&times;</button>
        </div>
        <button class="analyze-btn" id="analyzeBtn" disabled onclick="startAnalysis()">
          Analyze
        </button>
      </div>
    </div>

    <!-- Progress -->
    <div class="card" id="progressCard" style="display:none">
      <div class="card-body">
        <div class="prog-row">
          <div class="spinner"></div>
          <div>
            <div class="prog-stage" id="progStage">Uploading&hellip;</div>
            <div class="prog-detail" id="progDetail">Connecting to server</div>
          </div>
        </div>
        <div class="prog-bar-track">
          <div class="prog-bar-fill" id="progBar" style="width:0%"></div>
        </div>
        <div class="stage-row">
          <div class="stage-tag" id="st-meta">Metadata</div>
          <div class="stage-tag" id="st-visual">Visual (5 models)</div>
          <div class="stage-tag" id="st-audio">Audio</div>
          <div class="stage-tag" id="st-temporal">Temporal</div>
          <div class="stage-tag" id="st-lipsync">Lip-sync</div>
          <div class="stage-tag" id="st-spn">SPN</div>
          <div class="stage-tag" id="st-forensic">Forensic</div>
        </div>
      </div>
    </div>

    <!-- Result -->
    <div class="card" id="resultCard" style="display:none">
      <div class="card-header">
        <span class="card-title">Result</span>
      </div>
      <div class="card-body" id="resultBody"></div>
    </div>

  </div>

  <!-- ── HISTORY PANEL ── -->
  <div id="panel-history" style="display:none">
    <div class="card">
      <div class="card-header">
        <span class="card-title">Scan History</span>
        <button class="feedback-btn" onclick="loadHistory()">Refresh</button>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>File</th>
              <th>Verdict</th>
              <th>Score</th>
              <th>Visual</th>
              <th>Temporal</th>
              <th>SPN</th>
              <th>Fast</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody id="historyBody">
            <tr class="empty-row"><td colspan="8">Loading&hellip;</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

</main>

<script>
// ── Clock ──
setInterval(() => {
  document.getElementById('clock').textContent =
    new Date().toLocaleTimeString('en-US', {hour12:false});
}, 1000);

// ── Tab switching ──
function switchTab(name, btn) {
  document.getElementById('panel-scan').style.display    = name === 'scan'    ? '' : 'none';
  document.getElementById('panel-history').style.display = name === 'history' ? '' : 'none';
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (name === 'history') loadHistory();
}

// ── Drag and drop ──
const dz = document.getElementById('dropZone');
const fi = document.getElementById('fileInput');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag-over'); });
dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
dz.addEventListener('drop', e => {
  e.preventDefault();
  dz.classList.remove('drag-over');
  if (e.dataTransfer.files[0]) applyFile(e.dataTransfer.files[0]);
});
fi.addEventListener('change', () => { if (fi.files[0]) applyFile(fi.files[0]); });

const ALLOWED_EXT = ['.mp4','.avi','.mov','.mkv','.webm','.m4v'];
let _file = null, _lastResult = null;

function applyFile(f) {
  const ext = '.' + f.name.split('.').pop().toLowerCase();
  if (!ALLOWED_EXT.includes(ext)) {
    showInlineError('Unsupported file type. Allowed: ' + ALLOWED_EXT.join(', '));
    return;
  }
  _file = f;
  document.getElementById('fileRow').style.display = 'flex';
  document.getElementById('fileName').textContent = f.name;
  document.getElementById('fileSize').textContent = '(' + (f.size / 1024 / 1024).toFixed(1) + ' MB)';
  document.getElementById('analyzeBtn').disabled = false;
  hideResult();
}

function clearFile() {
  _file = null;
  fi.value = '';
  document.getElementById('fileRow').style.display = 'none';
  document.getElementById('analyzeBtn').disabled = true;
  hideResult();
}

function hideResult() {
  document.getElementById('progressCard').style.display = 'none';
  document.getElementById('resultCard').style.display   = 'none';
}

// ── Analysis flow ──
let _pollTimer = null, _simTimer = null, _pollCount = 0;
const MAX_POLLS = 150;

const STAGES = ['meta','visual','audio','temporal','lipsync','spn','forensic'];

// Map pipeline stage names → display label + which chip to activate
const STAGE_MAP = {
  'metadata':         {chip:'meta',     label:'Checking metadata'},
  'metadata_done':    {chip:'meta',     label:'Metadata done',     done:['meta']},
  'extraction':       {chip:'meta',     label:'Extracting frames'},
  'extraction_done':  {chip:'meta',     label:'Frames extracted',  done:['meta']},
  'visual':           {chip:'visual',   label:'Starting visual models'},
};
// visual:ModelName entries are dynamic — handled in pollJob
const VISUAL_DONE  = {chip:'visual',   label:'Visual analysis done', done:['meta','visual']};
const AUDIO_STAGE  = {chip:'audio',    label:'Analyzing audio'};
const AUDIO_DONE   = {chip:'audio',    label:'Audio done',           done:['meta','visual','audio']};
const TEMPORAL_S   = {chip:'temporal', label:'Temporal consistency check'};
const TEMPORAL_D   = {chip:'temporal', label:'Temporal done',        done:['meta','visual','audio','temporal']};
const LIPSYNC_S    = {chip:'lipsync',  label:'Lip-sync correlation'};
const LIPSYNC_D    = {chip:'lipsync',  label:'Lip-sync done',        done:['meta','visual','audio','temporal','lipsync']};
const SPN_S        = {chip:'spn',      label:'SPN noise fingerprint'};
const SPN_D        = {chip:'spn',      label:'SPN done',             done:['meta','visual','audio','temporal','lipsync','spn']};
const FORENSIC_S   = {chip:'forensic', label:'Forensic rules'};
const FORENSIC_D   = {chip:'forensic', label:'Forensic done',        done:['meta','visual','audio','temporal','lipsync','spn','forensic']};
const COMBINING    = {label:'Combining all signals…'};

function startAnalysis() {
  if (!_file) return;
  clearInterval(_pollTimer);
  clearInterval(_simTimer);
  _pollCount = 0;

  document.getElementById('progressCard').style.display = 'block';
  document.getElementById('resultCard').style.display   = 'none';
  document.getElementById('analyzeBtn').disabled = true;
  STAGES.forEach(s => document.getElementById('st-' + s).className = 'stage-tag');
  setProgress(0, 'Uploading file…', 'Please wait');

  const fd = new FormData();
  fd.append('file', _file);

  fetch('/analyze/video', {method:'POST', body:fd})
    .then(r => r.json())
    .then(data => {
      if (data.job_id) {
        _elapsed = 0;
        setProgress(4, 'Job accepted', 'ID: ' + data.job_id.slice(0,8) + '… polling every 4s');
        simulateProgress(); // slow bar movement fallback between polls
        _pollTimer = setInterval(() => pollJob(data.job_id), 4000);
      } else if (data.final_score !== undefined) {
        showResult(data);
      } else {
        showInlineError('Unexpected response from server.');
      }
    })
    .catch(e => showInlineError('Upload failed: ' + e));
}

// Fallback timer: just moves progress bar slowly so UI doesn't look frozen
function simulateProgress() {
  let elapsed = 0;
  const TOTAL = 300;
  _simTimer = setInterval(() => {
    elapsed++;
    const pct = Math.min(93, (elapsed / TOTAL) * 100);
    document.getElementById('progBar').style.width = pct + '%';
  }, 1000);
}

// Apply stage info from the real pipeline callback
let _elapsed = 0;
function applyStage(stage, partial) {
  _elapsed++;
  const label = stageLabel(stage);
  const chip  = stageChip(stage);
  const dones = stageDones(stage);

  if (label) setProgress(null, label, 'Elapsed: ~' + _elapsed + 's · auto-updating');
  if (chip)  document.getElementById('st-' + chip).className = 'stage-tag running';
  if (dones) dones.forEach(c => {
    document.getElementById('st-' + c).className = 'stage-tag done';
  });
}

function stageLabel(s) {
  if (!s) return null;
  if (s === 'metadata')        return 'Checking metadata…';
  if (s === 'extraction')      return 'Extracting frames and faces…';
  if (s === 'visual')          return 'Starting visual analysis…';
  if (s.startsWith('visual:')) return 'Visual model: ' + s.split(':')[1] + '…';
  if (s === 'visual_done')     return 'Visual analysis complete';
  if (s === 'audio')           return 'Analyzing audio…';
  if (s === 'audio_done')      return 'Audio analysis complete';
  if (s === 'temporal')        return 'Temporal consistency check…';
  if (s === 'temporal_done')   return 'Temporal analysis complete';
  if (s === 'lipsync')         return 'Lip-sync correlation…';
  if (s === 'lipsync_done')    return 'Lip-sync analysis complete';
  if (s === 'spn')             return 'SPN noise fingerprint…';
  if (s === 'spn_done')        return 'SPN analysis complete';
  if (s === 'forensic')        return 'Running forensic rules…';
  if (s === 'forensic_done')   return 'Forensic analysis complete';
  if (s === 'combining')       return 'Combining all signals…';
  if (s === 'done')            return 'Analysis complete';
  return s;
}

function stageChip(s) {
  if (!s) return null;
  if (s.startsWith('metadata'))  return 'meta';
  if (s.startsWith('visual'))    return 'visual';
  if (s.startsWith('audio'))     return 'audio';
  if (s.startsWith('temporal'))  return 'temporal';
  if (s.startsWith('lipsync'))   return 'lipsync';
  if (s.startsWith('spn'))       return 'spn';
  if (s.startsWith('forensic'))  return 'forensic';
  return null;
}

function stageDones(s) {
  if (s === 'metadata_done' || s === 'extraction_done') return ['meta'];
  if (s === 'visual_done')    return ['meta', 'visual'];
  if (s === 'audio_done')     return ['meta', 'visual', 'audio'];
  if (s === 'temporal_done')  return ['meta', 'visual', 'audio', 'temporal'];
  if (s === 'lipsync_done')   return ['meta', 'visual', 'audio', 'temporal', 'lipsync'];
  if (s === 'spn_done')       return ['meta', 'visual', 'audio', 'temporal', 'lipsync', 'spn'];
  if (s === 'forensic_done' || s === 'combining' || s === 'done')
    return ['meta', 'visual', 'audio', 'temporal', 'lipsync', 'spn', 'forensic'];
  return null;
}

function setProgress(pct, stage, detail) {
  document.getElementById('progStage').textContent  = stage;
  document.getElementById('progDetail').textContent = detail;
  document.getElementById('progBar').style.width    = pct + '%';
}

function pollJob(jobId) {
  _pollCount++;
  if (_pollCount > MAX_POLLS) {
    clearInterval(_pollTimer); clearInterval(_simTimer);
    showInlineError('Timeout (10 min). Server may have restarted. Try again.');
    return;
  }
  fetch('/jobs/' + jobId)
    .then(r => {
      if (r.status === 404) {
        clearInterval(_pollTimer); clearInterval(_simTimer);
        showInlineError('Server restarted mid-analysis (out of memory). Upload again.\nTip: ensure LOW_MEM=1 is set in Railway Variables.');
        return null;
      }
      return r.json();
    })
    .then(data => {
      if (!data) return;

      // Show real stage from server
      if (data.stage) applyStage(data.stage, data.partial_scores || {});

      if (data.status === 'done') {
        clearInterval(_pollTimer); clearInterval(_simTimer);
        STAGES.forEach(s => document.getElementById('st-' + s).className = 'stage-tag done');
        document.getElementById('progBar').style.width = '100%';
        setTimeout(() => showResult(data.result), 300);
      } else if (data.status === 'error') {
        clearInterval(_pollTimer); clearInterval(_simTimer);
        showInlineError('Analysis error: ' + (data.error || 'unknown'));
      }
    })
    .catch(() => {});
}

// ── Render result ──
function esc(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function vClass(v) {
  if (!v) return 'verdict-unc';
  const l = v.toLowerCase().replace(/\s/g,'');
  if (l === 'fake')   return 'verdict-fake';
  if (l.includes('likely')) return 'verdict-likely';
  if (l === 'real')   return 'verdict-real';
  return 'verdict-unc';
}
function barClass(v) { return v >= 70 ? 'sig-fill-r' : v >= 35 ? 'sig-fill-a' : 'sig-fill-g'; }
function pctColor(v) { return v >= 70 ? 'var(--red)' : v >= 35 ? 'var(--amber)' : 'var(--green)'; }
function chipClass(v) {
  if (!v) return 'vc-unc';
  const l = v.toLowerCase().replace(/\s/g,'');
  if (l === 'fake') return 'vc-fake';
  if (l.includes('likely')) return 'vc-likely';
  if (l === 'real') return 'vc-real';
  return 'vc-unc';
}

const SIGS = [
  {key:'visual',   label:'Visual',   wt:'40%'},
  {key:'audio',    label:'Audio',    wt:'18%'},
  {key:'temporal', label:'Temporal', wt:'12%'},
  {key:'lipsync',  label:'Lip-sync', wt:'10%'},
  {key:'spn',      label:'SPN',      wt:'10%'},
  {key:'forensic', label:'Forensic', wt:' 7%'},
  {key:'metadata', label:'Metadata', wt:' 3%'},
];

function showResult(r) {
  clearInterval(_pollTimer); clearInterval(_simTimer);
  document.getElementById('progressCard').style.display = 'none';
  document.getElementById('resultCard').style.display   = 'block';
  document.getElementById('analyzeBtn').disabled = false;

  _lastResult = r;
  const cs      = r.component_scores || {};
  const verdict = r.verdict || 'UNKNOWN';
  const score   = r.final_score != null ? parseFloat(r.final_score).toFixed(1) : '--';
  const sNum    = parseFloat(score) || 0;
  const vc      = vClass(verdict);
  const ts      = r.timestamp ? new Date(r.timestamp).toLocaleString() : '';
  const fn      = r.filename || r.video_path || '';

  const sigRows = SIGS.map(sig => {
    const raw = cs[sig.key];
    if (raw == null) return `
      <div class="sig-row">
        <div class="sig-name">${esc(sig.label)}</div>
        <div class="sig-track"><div class="sig-fill sig-fill-n" style="width:0%"></div></div>
        <div class="sig-pct" style="color:var(--text3)">N/A</div>
        <div class="sig-wt">${esc(sig.wt)}</div>
      </div>`;
    const v = Math.min(100, Math.round(parseFloat(raw)));
    return `
      <div class="sig-row">
        <div class="sig-name">${esc(sig.label)}</div>
        <div class="sig-track"><div class="sig-fill ${barClass(v)}" style="width:${v}%"></div></div>
        <div class="sig-pct" style="color:${pctColor(v)}">${v}%</div>
        <div class="sig-wt">${esc(sig.wt)}</div>
      </div>`;
  }).join('');

  const anom = (r.anomalies || []).filter(a => !a.startsWith('Meta:'));
  const anomHtml = anom.length ? `
    <div class="anomaly-section">
      <div class="anomaly-label">Anomalies detected</div>
      <div class="anomaly-list">
        ${anom.slice(0,8).map(a => `<div class="anomaly-item">${esc(a)}</div>`).join('')}
      </div>
    </div>` : '';

  const fastHtml = r.fast_path
    ? `<span class="fast-badge">Fast-path &middot; ${esc(r.fast_reason || 'metadata')}</span>` : '';

  document.getElementById('resultBody').innerHTML = `
    <div class="verdict-section">
      <div class="${vc} verdict-label">${esc(verdict)}</div>
      <div class="${vc} verdict-score">${score}%</div>
      <div class="verdict-meta">
        <div class="verdict-file" title="${esc(fn)}">${esc(fn)}</div>
        <div class="verdict-ts">${esc(ts)}</div>
        ${fastHtml}
      </div>
    </div>
    <div class="sig-section">
      <div class="sig-section-label">Signal breakdown</div>
      ${sigRows}
    </div>
    ${anomHtml}
    <div class="feedback-row">
      <span class="feedback-label">Result incorrect?</span>
      <button class="feedback-btn" onclick="toggleFeedback()">Mark as wrong</button>
    </div>
    <div class="feedback-form" id="feedbackForm">
      <div class="feedback-form-label">Correct verdict:</div>
      <div class="verdict-opts">
        <button class="verdict-opt" onclick="selectVerdict(this,'FAKE')">Fake</button>
        <button class="verdict-opt" onclick="selectVerdict(this,'LIKELY FAKE')">Likely Fake</button>
        <button class="verdict-opt" onclick="selectVerdict(this,'UNCERTAIN')">Uncertain</button>
        <button class="verdict-opt" onclick="selectVerdict(this,'REAL')">Real</button>
      </div>
      <textarea class="feedback-note" id="feedbackNote" rows="2"
        placeholder="Optional: why is this wrong? (e.g. WhatsApp compressed, metadata stripped)"></textarea>
      <button class="feedback-submit" onclick="submitFeedback()">Submit feedback</button>
      <span class="feedback-thanks" id="feedbackThanks" style="display:none">Feedback logged. Thank you.</span>
    </div>
  `;
  loadHistory();
}

// ── Feedback ──
let _selectedVerdict = null;

function toggleFeedback() {
  const f = document.getElementById('feedbackForm');
  f.classList.toggle('open');
}

function selectVerdict(btn, v) {
  _selectedVerdict = v;
  document.querySelectorAll('.verdict-opt').forEach(b => {
    b.className = 'verdict-opt';
  });
  const cls = v === 'FAKE' ? 'sel-fake'
            : v === 'LIKELY FAKE' ? 'sel-likely'
            : v === 'REAL' ? 'sel-real' : 'sel-uncertain';
  btn.classList.add(cls);
}

function submitFeedback() {
  if (!_selectedVerdict || !_lastResult) return;
  const note = document.getElementById('feedbackNote').value;
  fetch('/feedback', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({
      filename: _lastResult.filename || _lastResult.video_path || '',
      predicted_verdict: _lastResult.verdict || '',
      predicted_score: _lastResult.final_score || 0,
      correct_verdict: _selectedVerdict,
      component_scores: _lastResult.component_scores || {},
      notes: note,
    })
  })
  .then(r => r.json())
  .then(() => {
    document.getElementById('feedbackThanks').style.display = 'block';
    document.querySelector('.feedback-submit').style.display = 'none';
  })
  .catch(() => {});
}

function showInlineError(msg) {
  document.getElementById('progressCard').style.display = 'none';
  document.getElementById('resultCard').style.display   = 'block';
  document.getElementById('analyzeBtn').disabled = false;
  document.getElementById('resultBody').innerHTML = `
    <div class="error-box">
      ${esc(msg)}
      <div class="error-hint">Check /health or /docs for API status.</div>
    </div>`;
}

// ── History ──
function loadHistory() {
  fetch('/results?limit=25')
    .then(r => r.json())
    .then(d => renderHistory(d.results || []))
    .catch(() => {});
}

function renderHistory(rows) {
  const tb = document.getElementById('historyBody');
  if (!rows.length) {
    tb.innerHTML = '<tr class="empty-row"><td colspan="8">No scans yet</td></tr>';
    return;
  }
  tb.innerHTML = rows.map(r => {
    const v  = r.verdict || '–';
    const s  = r.final_score != null ? parseFloat(r.final_score).toFixed(1) : '–';
    const sn = parseFloat(s) || 0;
    const fn = (r.filename || r.video_path || '–').split(/[/\\]/).pop();
    const cs = r.component_scores || {};
    const vis  = cs.visual   != null ? Math.round(cs.visual) + '%'   : '–';
    const temp = cs.temporal != null ? Math.round(cs.temporal) + '%' : '–';
    const spn  = cs.spn      != null ? Math.round(cs.spn) + '%'      : '–';
    const ts   = r.timestamp ? new Date(r.timestamp).toLocaleString() : '–';
    return `<tr>
      <td class="mono" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(fn)}">${esc(fn)}</td>
      <td><span class="verdict-chip ${chipClass(v)}">${esc(v)}</span></td>
      <td class="mono" style="color:${pctColor(sn)};font-weight:600">${s}%</td>
      <td class="mono" style="color:var(--text3)">${esc(vis)}</td>
      <td class="mono" style="color:var(--text3)">${esc(temp)}</td>
      <td class="mono" style="color:var(--text3)">${esc(spn)}</td>
      <td style="color:var(--text3)">${r.fast_path ? 'Yes' : '–'}</td>
      <td style="color:var(--text3)">${esc(ts)}</td>
    </tr>`;
  }).join('');
}

loadHistory();
</script>
</body>
</html>"""
