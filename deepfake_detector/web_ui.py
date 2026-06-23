DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cyber Cell — Deepfake Forensic Unit</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:          #f0f2f5;
  --surface:     #ffffff;
  --surface2:    #f7f8fa;
  --surface3:    #eef0f3;
  --border:      #e1e4e8;
  --border2:     #c9cdd4;
  --text:        #0d1117;
  --text2:       #3d444d;
  --text3:       #848d97;
  --nav-bg:      #0f1b2d;
  --nav-border:  #1c2f4a;
  --nav-text:    #c9d1d9;
  --nav-text2:   #8b949e;
  --red:         #cf222e;
  --red-bg:      rgba(207,34,46,.07);
  --red-border:  rgba(207,34,46,.22);
  --green:       #1a7f37;
  --green-bg:    rgba(26,127,55,.07);
  --green-border:rgba(26,127,55,.22);
  --amber:       #9a6700;
  --amber-bg:    rgba(154,103,0,.07);
  --amber-border:rgba(154,103,0,.22);
  --blue:        #0969da;
  --blue-bg:     rgba(9,105,218,.07);
  --blue-border: rgba(9,105,218,.22);
  --shadow-sm:   0 1px 3px rgba(0,0,0,.08), 0 1px 2px rgba(0,0,0,.06);
  --shadow:      0 2px 8px rgba(0,0,0,.08), 0 1px 4px rgba(0,0,0,.06);
  --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --mono: 'SF Mono','Fira Code','Cascadia Code','Consolas',monospace;
}

html, body { height: 100%; background: var(--bg); color: var(--text); font-family: var(--font); font-size: 13px; line-height: 1.5; -webkit-font-smoothing: antialiased; }

/* ── Top navigation (dark navy — authority feel) ── */
.topnav {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--nav-bg);
  border-bottom: 1px solid var(--nav-border);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 8px rgba(0,0,0,.25);
}
.nav-left  { display: flex; align-items: center; gap: 28px; }
.nav-right { display: flex; align-items: center; gap: 16px; }

.wordmark {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: -.01em;
  color: #ffffff;
  text-decoration: none;
}
.wordmark-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 6px;
  background: rgba(255,255,255,.07);
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 6px;
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
.wordmark-sub { font-size: 9px; font-weight: 500; color: var(--nav-text2); letter-spacing: .08em; text-transform: uppercase; display: block; line-height: 1; margin-top: 1px; }

.nav-tabs { display: flex; gap: 2px; }
.tab-btn {
  padding: 6px 14px;
  border: none;
  background: none;
  cursor: pointer;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--nav-text2);
  transition: color .15s, background .15s;
}
.tab-btn:hover  { color: var(--nav-text); background: rgba(255,255,255,.08); }
.tab-btn.active { color: #ffffff; background: rgba(255,255,255,.12); }

.status-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--nav-text2);
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3fb950;
  box-shadow: 0 0 5px #3fb950;
}
.clock-display { font-family: var(--mono); font-size: 11px; color: var(--nav-text2); letter-spacing: .04em; }
.nav-ext-link {
  font-size: 11px;
  color: var(--nav-text2);
  text-decoration: none;
  padding: 4px 8px;
  border-radius: 5px;
  transition: color .15s, background .15s;
}
.nav-ext-link:hover { color: var(--nav-text); background: rgba(255,255,255,.08); }

/* ── Stats bar ── */
.stats-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 14px;
}
.stat-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: var(--shadow-sm);
}
.stat-val { font-size: 26px; font-weight: 700; color: var(--text); line-height: 1; }
.stat-label { font-size: 11px; color: var(--text3); margin-top: 4px; font-weight: 500; }
.stat-delta { font-size: 10px; margin-top: 2px; }

/* ── Main layout ── */
main {
  max-width: 860px;
  margin: 0 auto;
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ── Cards ── */
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
.card-header {
  padding: 14px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  background: var(--surface2);
}
.card-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--text2);
}
.card-body { padding: 16px 18px 18px; }

/* ── Upload zone ── */
.upload-zone {
  position: relative;
  border: 2px dashed var(--border2);
  border-radius: 8px;
  padding: 36px 20px;
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
.upload-icon { font-size: 28px; margin-bottom: 10px; line-height: 1; }
.upload-label { font-size: 14px; font-weight: 600; color: var(--text2); margin-bottom: 4px; }
.upload-hint  { font-size: 11px; color: var(--text3); }

.file-row {
  display: none;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
  padding: 10px 14px;
  background: var(--blue-bg);
  border: 1px solid var(--blue-border);
  border-radius: 7px;
}
.file-name { font-family: var(--mono); font-size: 11px; color: var(--text2); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { font-size: 11px; color: var(--text3); flex-shrink: 0; }
.clear-btn { background: none; border: none; cursor: pointer; color: var(--text3); font-size: 16px; line-height: 1; padding: 0 4px; }
.clear-btn:hover { color: var(--red); }

.analyze-btn {
  display: block;
  width: 100%;
  margin-top: 14px;
  padding: 10px;
  border: none;
  border-radius: 7px;
  background: var(--nav-bg);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  letter-spacing: .02em;
  transition: opacity .15s, transform .1s;
  box-shadow: 0 2px 6px rgba(0,0,0,.2);
}
.analyze-btn:hover:not(:disabled)   { opacity: .88; transform: translateY(-1px); }
.analyze-btn:active:not(:disabled)  { transform: translateY(0); }
.analyze-btn:disabled { opacity: .35; cursor: not-allowed; }

/* ── Progress ── */
.kp-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 4px; }
.kp-stage-now { font-size: 14px; font-weight: 600; color: var(--text); }
.kp-pct { font-family: var(--mono); font-size: 24px; font-weight: 700; color: var(--blue); }
.prog-detail { font-size: 11px; color: var(--text3); margin-bottom: 4px; }
.kp-bar-track { height: 6px; background: var(--surface3); border-radius: 3px; overflow: hidden; margin: 10px 0 16px; border: 1px solid var(--border); }
.kp-bar-fill {
  height: 100%; border-radius: 3px; width: 0%;
  background: linear-gradient(90deg, var(--blue), #6366f1);
  transition: width .6s cubic-bezier(.4,0,.2,1);
  box-shadow: 0 0 10px rgba(9,105,218,.4);
}
.kp-list { display: flex; flex-direction: column; gap: 3px; }
.kp-step {
  display: flex; align-items: center; gap: 10px; padding: 7px 10px;
  border-radius: 7px; transition: background .2s; opacity: .45;
}
.kp-step.active { opacity: 1; background: var(--blue-bg); border: 1px solid var(--blue-border); }
.kp-step.done   { opacity: 1; }
.kp-dot {
  width: 20px; height: 20px; border-radius: 50%; flex-shrink: 0;
  border: 2px solid var(--border2); display: grid; place-items: center;
  font-size: 10px; transition: all .25s; background: var(--surface2);
}
.kp-step.active .kp-dot {
  border-color: var(--blue); background: var(--blue-bg);
  animation: kp-pulse 1.2s ease-in-out infinite;
}
.kp-step.done .kp-dot { border-color: var(--green); background: var(--green); color: #fff; }
.kp-step.done .kp-dot::after { content: '\2713'; font-weight: 700; font-size: 10px; }
@keyframes kp-pulse { 0%,100%{ box-shadow:0 0 0 0 rgba(9,105,218,.3);} 50%{ box-shadow:0 0 0 5px rgba(9,105,218,0);} }
.kp-name { font-size: 12px; color: var(--text2); flex: 1; font-weight: 500; }
.kp-step.active .kp-name { color: var(--text); font-weight: 600; }
.kp-sub { font-size: 10px; color: var(--text3); font-family: var(--mono); }
.kp-spin {
  width: 12px; height: 12px; border: 2px solid var(--border2);
  border-top-color: var(--blue); border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Result ── */
.verdict-banner {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 18px;
  padding: 16px 18px;
  border-radius: 8px;
  border: 1px solid var(--border);
}
.verdict-banner.vb-fake    { background: var(--red-bg); border-color: var(--red-border); }
.verdict-banner.vb-likely  { background: var(--amber-bg); border-color: var(--amber-border); }
.verdict-banner.vb-unc     { background: var(--amber-bg); border-color: var(--amber-border); }
.verdict-banner.vb-real    { background: var(--green-bg); border-color: var(--green-border); }

.verdict-icon { font-size: 28px; flex-shrink: 0; line-height: 1; }
.verdict-info { flex: 1; }
.verdict-label { font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.verdict-label.verdict-fake    { color: var(--red); }
.verdict-label.verdict-likely  { color: var(--amber); }
.verdict-label.verdict-unc     { color: var(--amber); }
.verdict-label.verdict-real    { color: var(--green); }
.verdict-score   { font-family: var(--mono); font-size: 32px; font-weight: 700; line-height: 1; margin-top: 2px; }
.verdict-meta    { text-align: right; }
.verdict-file    { font-size: 11px; color: var(--text3); max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.verdict-ts      { font-size: 10px; color: var(--text3); }
.fast-badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: .05em;
  text-transform: uppercase;
  background: var(--blue-bg);
  color: var(--blue);
  border: 1px solid var(--blue-border);
  margin-top: 4px;
}

/* ── Signal bars ── */
.sig-section { margin-bottom: 16px; }
.sig-section-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--text3);
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
}
.sig-row {
  display: grid;
  grid-template-columns: 76px 1fr 40px 34px;
  align-items: center;
  gap: 10px;
  margin-bottom: 9px;
}
.sig-name   { font-size: 11px; font-weight: 600; color: var(--text2); }
.sig-track  { height: 5px; background: var(--surface3); border-radius: 3px; overflow: hidden; border: 1px solid var(--border); }
.sig-fill   { height: 100%; border-radius: 3px; transition: width .7s; }
.sig-fill-r { background: linear-gradient(90deg, #dc2626, #ef4444); }
.sig-fill-a { background: linear-gradient(90deg, #b45309, #d97706); }
.sig-fill-g { background: linear-gradient(90deg, #15803d, #22c55e); }
.sig-fill-n { background: var(--border2); }
.sig-pct    { font-family: var(--mono); font-size: 11px; font-weight: 600; text-align: right; }
.sig-wt     { font-size: 9px; color: var(--text3); text-align: right; }

/* ── Anomalies ── */
.anomaly-section {
  padding-top: 14px;
  border-top: 1px solid var(--border);
  margin-bottom: 14px;
}
.anomaly-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--text3);
  margin-bottom: 8px;
}
.anomaly-list { display: flex; flex-direction: column; gap: 5px; }
.anomaly-item {
  font-size: 11px;
  color: var(--amber);
  padding: 5px 10px;
  background: var(--amber-bg);
  border: 1px solid var(--amber-border);
  border-radius: 5px;
  font-weight: 500;
}

/* ── Feedback ── */
.feedback-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}
.feedback-label { font-size: 11px; color: var(--text3); flex: 1; }
.feedback-btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid var(--border2);
  background: var(--surface);
  color: var(--text2);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s;
  box-shadow: var(--shadow-sm);
}
.feedback-btn:hover { border-color: var(--blue-border); color: var(--blue); background: var(--blue-bg); }

.feedback-form {
  display: none;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 8px;
  margin-top: 10px;
}
.feedback-form.open { display: flex; }
.feedback-form-label { font-size: 11px; font-weight: 600; color: var(--text2); }
.verdict-opts { display: flex; gap: 6px; flex-wrap: wrap; }
.verdict-opt {
  padding: 6px 14px;
  border-radius: 5px;
  border: 1px solid var(--border2);
  background: var(--surface);
  color: var(--text2);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all .12s;
  box-shadow: var(--shadow-sm);
}
.verdict-opt:hover          { background: var(--surface3); }
.verdict-opt.sel-fake       { border-color: var(--red-border); color: var(--red); background: var(--red-bg); }
.verdict-opt.sel-likely     { border-color: var(--amber-border); color: var(--amber); background: var(--amber-bg); }
.verdict-opt.sel-uncertain  { border-color: var(--amber-border); color: var(--amber); background: var(--amber-bg); }
.verdict-opt.sel-real       { border-color: var(--green-border); color: var(--green); background: var(--green-bg); }
.feedback-note {
  width: 100%;
  padding: 7px 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
  color: var(--text);
  font-family: var(--font);
  font-size: 12px;
  resize: none;
}
.feedback-note::placeholder { color: var(--text3); }
.feedback-note:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px var(--blue-bg); }
.feedback-submit {
  align-self: flex-start;
  padding: 6px 16px;
  border-radius: 6px;
  border: 1px solid var(--border2);
  background: var(--surface);
  color: var(--text2);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all .12s;
  box-shadow: var(--shadow-sm);
}
.feedback-submit:hover { background: var(--nav-bg); color: #fff; border-color: var(--nav-bg); }
.feedback-thanks { font-size: 11px; color: var(--green); font-weight: 600; }

/* ── History table ── */
.tbl-wrap { overflow-x: auto; }
.search-bar {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface2);
}
.search-input {
  width: 100%;
  padding: 7px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-family: var(--font);
  font-size: 12px;
  transition: border-color .15s;
}
.search-input:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px var(--blue-bg); }
.search-input::placeholder { color: var(--text3); }
table { width: 100%; border-collapse: collapse; }
thead th {
  padding: 9px 14px;
  text-align: left;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  color: var(--text3);
  border-bottom: 1px solid var(--border);
  background: var(--surface2);
  white-space: nowrap;
}
tbody td {
  padding: 10px 14px;
  font-size: 12px;
  color: var(--text2);
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover td { background: var(--blue-bg); cursor: pointer; }
.mono { font-family: var(--mono); }

.verdict-chip {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .03em;
}
.vc-fake    { background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }
.vc-likely  { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.vc-unc     { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.vc-real    { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }

.empty-row td { text-align: center; color: var(--text3); padding: 40px 0; font-size: 12px; }

/* ── Error ── */
.error-box {
  padding: 14px 16px;
  background: var(--red-bg);
  border: 1px solid var(--red-border);
  border-radius: 7px;
  font-size: 12px;
  color: var(--red);
  font-weight: 500;
}
.error-hint { font-size: 11px; color: var(--text3); margin-top: 4px; font-weight: 400; }

/* ── Forms ── */
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 16px; }
label { display: flex; flex-direction: column; gap: 4px; font-size: 11px; color: var(--text3); font-weight: 600; letter-spacing: .02em; text-transform: uppercase; }
label.full { margin-top: 10px; grid-column: 1 / -1; }
input, select, textarea {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-family: var(--font);
  font-size: 12px;
  padding: 8px 10px;
  transition: border-color .15s;
  text-transform: none;
  font-weight: 400;
  letter-spacing: 0;
}
input:focus, select:focus, textarea:focus { outline: none; border-color: var(--blue); box-shadow: 0 0 0 3px var(--blue-bg); }
textarea { resize: vertical; }

/* ── Case detail ── */
.case-hd { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 4px; }
.case-hd h2 { font-size: 17px; font-weight: 700; color: var(--text); }
.case-sub { font-size: 11px; color: var(--text3); margin-top: 3px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 20px; margin-top: 10px; }
.meta-item { font-size: 12px; color: var(--text2); }
.meta-item span { color: var(--text3); display: block; font-size: 10px; text-transform: uppercase; letter-spacing: .06em; font-weight: 700; margin-bottom: 1px; }
.pri-chip, .status-chip { display: inline-block; padding: 2px 9px; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: .03em; }
.pri-LOW    { background: var(--green-bg); color: var(--green); border: 1px solid var(--green-border); }
.pri-MEDIUM { background: var(--blue-bg); color: var(--blue); border: 1px solid var(--blue-border); }
.pri-HIGH   { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.pri-CRITICAL { background: var(--red-bg); color: var(--red); border: 1px solid var(--red-border); }
.status-OPEN { background: var(--blue-bg); color: var(--blue); border: 1px solid var(--blue-border); }
.status-chip[data-s="UNDER REVIEW"] { background: var(--amber-bg); color: var(--amber); border: 1px solid var(--amber-border); }
.status-chip[data-s="CLOSED"] { background: var(--surface3); color: var(--text3); border: 1px solid var(--border2); }
.ev-card { border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; margin-bottom: 9px; background: var(--surface2); box-shadow: var(--shadow-sm); }
.ev-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.ev-fn { font-family: var(--mono); font-size: 11px; color: var(--text2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
.ev-hash { font-family: var(--mono); font-size: 9px; color: var(--text3); margin-top: 3px; word-break: break-all; }
.link-btn { color: var(--blue); text-decoration: none; font-size: 11px; font-weight: 600; }
.link-btn:hover { text-decoration: underline; }
.action-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

/* ── Focus selector ── */
.focus-group { margin-top: 16px; }
.focus-label { font-size: 11px; color: var(--text3); margin-bottom: 8px; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.focus-pills { display: flex; gap: 8px; flex-wrap: wrap; }
.focus-pill {
  flex: 1; min-width: 72px; padding: 10px 8px; border-radius: 8px;
  border: 1px solid var(--border2); background: var(--surface2);
  color: var(--text2); font-size: 11px; font-weight: 500; cursor: pointer;
  transition: all .15s; text-align: center; box-shadow: var(--shadow-sm);
}
.focus-pill .fp-title { display: block; font-weight: 700; font-size: 12px; }
.focus-pill .fp-sub   { display: block; font-size: 9px; color: var(--text3); margin-top: 2px; }
.focus-pill:hover { border-color: var(--blue-border); background: var(--blue-bg); }
.focus-pill.active { border-color: var(--blue); background: var(--blue-bg); color: var(--blue); box-shadow: 0 0 0 3px rgba(9,105,218,.1); }
.focus-pill.active .fp-sub { color: var(--blue); opacity: .75; }

/* ── Divider ── */
hr.section-div { border: none; border-top: 1px solid var(--border); margin: 14px 0; }

/* ── Action btn variants ── */
.btn-primary {
  padding: 7px 18px; border-radius: 6px; border: none;
  background: var(--nav-bg); color: #fff; font-size: 12px; font-weight: 700;
  cursor: pointer; transition: all .15s; box-shadow: var(--shadow-sm);
}
.btn-primary:hover { opacity: .88; }
.btn-ghost {
  padding: 7px 14px; border-radius: 6px; border: 1px solid var(--border2);
  background: var(--surface); color: var(--text2); font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all .15s; box-shadow: var(--shadow-sm);
}
.btn-ghost:hover { background: var(--surface3); border-color: var(--border2); }
.btn-danger {
  padding: 7px 14px; border-radius: 6px; border: 1px solid var(--red-border);
  background: var(--red-bg); color: var(--red); font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all .15s;
}
.btn-danger:hover { background: var(--red); color: #fff; }

/* ── Admin panel ── */
.admin-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; margin-bottom: 14px; }
.admin-stat { background:var(--surface); border:1px solid var(--border); border-radius:10px; padding:14px 16px; box-shadow:var(--shadow-sm); }
.admin-stat .stat-val { font-size:22px; font-weight:700; }
.admin-stat .stat-label { font-size:11px; color:var(--text3); margin-top:4px; font-weight:500; }
.admin-refresh-bar { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.admin-refresh-note { font-size:11px; color:var(--text3); }
.tag-pending  { background:var(--blue-bg);  color:var(--blue);  border:1px solid var(--blue-border);  padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700; }
.tag-running  { background:var(--amber-bg); color:var(--amber); border:1px solid var(--amber-border); padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700; }
.tag-done     { background:var(--green-bg); color:var(--green); border:1px solid var(--green-border); padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700; }
.tag-error    { background:var(--red-bg);   color:var(--red);   border:1px solid var(--red-border);   padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700; }
.tb-error { font-family:var(--mono); font-size:10px; color:var(--red); max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; cursor:pointer; }
.tb-expand { white-space:pre-wrap; word-break:break-all; max-height:200px; overflow-y:auto; }
.log-stage { font-family:var(--mono); font-size:10px; color:var(--amber); }

/* scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--surface2); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text3); }
  /* disclaimer modal */
  #dfDisclaimer { position:fixed; inset:0; background:rgba(0,0,0,.6); z-index:9999;
    display:none; align-items:center; justify-content:center; }
  #dfDisclaimer.show { display:flex; }
  #dfDisclaimer .dlg { background:var(--card,#fff); color:var(--text,#111); max-width:440px;
    width:90%; border-radius:14px; padding:24px 26px; box-shadow:0 20px 60px rgba(0,0,0,.4);
    border:1px solid var(--border,#e5e7eb); }
  #dfDisclaimer h3 { margin:0 0 10px; font-size:17px; }
  #dfDisclaimer p { margin:0 0 12px; font-size:13px; line-height:1.5; color:var(--text2,#555); }
  #dfDisclaimer .gpu { font-weight:600; color:var(--text,#111); }
  #dfDisclaimer button { margin-top:6px; width:100%; padding:11px; border:none; border-radius:9px;
    background:var(--nav-bg,#111); color:#fff; font-weight:600; font-size:14px; cursor:pointer; }
</style>
</head>
<body>

<!-- Analysis time disclaimer -->
<div id="dfDisclaimer">
  <div class="dlg">
    <h3>⏳ Analysis may take a while</h3>
    <p>This tool runs several detection models on each upload. On a CPU-only
       machine a single video can take <strong>one to two minutes or more</strong>
       to produce a fake score and verdict.</p>
    <p class="gpu">For faster analysis, run it on a machine with a dedicated GPU —
       the models use the GPU automatically when one is available.</p>
    <p id="dfDevLine" style="font-size:12px;opacity:.8"></p>
    <button onclick="document.getElementById('dfDisclaimer').classList.remove('show')">Got it</button>
  </div>
</div>
<script>
  (function(){
    try { document.getElementById('dfDisclaimer').classList.add('show'); } catch(e){}
    // show the active compute device if the API exposes it
    fetch('/admin/stats').then(r=>r.json()).then(d=>{
      var el=document.getElementById('dfDevLine'); if(el && d && d.device) el.textContent='Current device: '+d.device;
    }).catch(function(){});
  })();
</script>

<!-- Top nav -->
<nav class="topnav">
  <div class="nav-left">
    <a class="wordmark" href="/">
      <div class="wordmark-badge">
        <div class="wordmark-icon">
          <svg viewBox="0 0 12 12"><path d="M6 1L1 4v4l5 3 5-3V4L6 1zm0 1.5L10 5v2.5L6 10 2 7.5V5l4-2.5z"/></svg>
        </div>
        <div>
          <span>Cyber Cell</span>
          <span class="wordmark-sub">Forensics Division</span>
        </div>
      </div>
    </a>
    <div class="nav-tabs">
      <button class="tab-btn active" id="tab-cases" onclick="switchTab('cases', this)">Cases</button>
      <button class="tab-btn" id="tab-scan" onclick="switchTab('scan', this)">Quick Scan</button>
      <button class="tab-btn" id="tab-history" onclick="switchTab('history', this)">History</button>
      <button class="tab-btn" id="tab-admin" onclick="switchTab('admin', this)">Admin</button>
    </div>
  </div>
  <div class="nav-right">
    <div class="status-badge"><div class="status-dot"></div>&nbsp;Online</div>
    <div class="clock-display" id="clock">--:--:--</div>
    <a class="nav-ext-link" href="/docs" target="_blank">API</a>
    <a class="nav-ext-link" href="/health" target="_blank">Health</a>
  </div>
</nav>

<!-- Main -->
<main>

  <!-- ── CASES PANEL ── -->
  <div id="panel-cases">

    <!-- Stats bar -->
    <div class="stats-bar" id="statsBar">
      <div class="stat-card">
        <div class="stat-val" id="st-total">—</div>
        <div class="stat-label">Total Cases</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:var(--blue)" id="st-open">—</div>
        <div class="stat-label">Open</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:var(--red)" id="st-critical">—</div>
        <div class="stat-label">Critical Priority</div>
      </div>
      <div class="stat-card">
        <div class="stat-val" style="color:var(--green)" id="st-closed">—</div>
        <div class="stat-label">Closed</div>
      </div>
    </div>

    <!-- Registry -->
    <div id="caseRegistry">
      <div class="card">
        <div class="card-header">
          <span class="card-title">Case Registry</span>
          <div class="action-row">
            <button class="btn-primary" onclick="showNewCaseForm()">+ New Case</button>
          </div>
        </div>
        <div class="search-bar">
          <input class="search-input" id="caseSearch" placeholder="Search by case no., title, officer…" oninput="filterCases()" />
        </div>
        <div class="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Case No.</th><th>Title</th><th>Priority</th>
                <th>Status</th><th>Officer</th><th>Evidence</th><th>Updated</th>
              </tr>
            </thead>
            <tbody id="caseListBody">
              <tr class="empty-row"><td colspan="7">Loading&hellip;</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- New case form -->
    <div id="newCaseCard" class="card" style="display:none">
      <div class="card-header">
        <span class="card-title">Register New Case</span>
        <button class="btn-ghost" onclick="showRegistry()">&larr; Back</button>
      </div>
      <div class="card-body">
        <div class="form-grid">
          <label>Case Number<input id="nc_case_no" placeholder="e.g. CYB/2026/0142"></label>
          <label>Title<input id="nc_title" placeholder="Short case title"></label>
          <label>Investigating Officer<input id="nc_officer_name" placeholder="Full name"></label>
          <label>Badge / ID<input id="nc_officer_badge" placeholder="Badge no."></label>
          <label>Department / Unit<input id="nc_department" placeholder="e.g. Cyber Crime Cell"></label>
          <label>Priority
            <select id="nc_priority">
              <option>LOW</option><option selected>MEDIUM</option><option>HIGH</option><option>CRITICAL</option>
            </select>
          </label>
          <label>Suspect<input id="nc_suspect" placeholder="If known"></label>
          <label>Victim / Complainant<input id="nc_victim" placeholder="If known"></label>
          <label>Source / URL<input id="nc_source_url" placeholder="Origin of media (URL or platform)"></label>
          <label>Incident Date<input id="nc_incident_date" type="date"></label>
          <label class="full">Notes / Description
            <textarea id="nc_notes" rows="3" placeholder="Case background, complaint summary, digital evidence received…"></textarea>
          </label>
        </div>
        <div style="display:flex;gap:8px;margin-top:16px">
          <button class="btn-primary" onclick="createCase()">Create Case</button>
          <button class="btn-ghost" onclick="showRegistry()">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Case detail -->
    <div id="caseDetail" style="display:none"></div>
  </div>

  <!-- ── SCAN PANEL ── -->
  <div id="panel-scan" style="display:none">
    <div class="card">
      <div class="card-header">
        <span class="card-title">Analyze Video</span>
      </div>
      <div class="card-body">
        <div class="upload-zone" id="dropZone">
          <input type="file" id="fileInput" accept=".mp4,.avi,.mov,.mkv,.webm,.m4v,.jpg,.jpeg,.png,.bmp,.webp,.gif,.heic,.tiff,.mp3,.wav,.m4a,.flac,.ogg,.aac,.opus,.amr">
          <div class="upload-icon" id="dropIcon">📁</div>
          <div class="upload-label">Drop any media file or click to browse</div>
          <div class="upload-hint">
            <strong>Video:</strong> MP4 AVI MOV MKV WEBM &nbsp;|&nbsp;
            <strong>Image:</strong> JPG PNG WEBP BMP GIF HEIC &nbsp;|&nbsp;
            <strong>Audio:</strong> MP3 WAV M4A FLAC OGG AAC &mdash; max 500 MB
          </div>
        </div>
        <div class="file-row" id="fileRow">
          <span class="file-name" id="fileName"></span>
          <span class="file-size" id="fileSize"></span>
          <button class="clear-btn" onclick="clearFile()" title="Remove">&times;</button>
        </div>
        <div class="focus-group" id="scanFocus">
          <div class="focus-label">Focus analysis on:</div>
          <div class="focus-pills">
            <button class="focus-pill active" data-focus="full"   onclick="pickFocus('scan',this)"><span class="fp-title">Full</span><span class="fp-sub">all signals</span></button>
            <button class="focus-pill"        data-focus="visual" onclick="pickFocus('scan',this)"><span class="fp-title">Face</span><span class="fp-sub">visual + forensic</span></button>
            <button class="focus-pill"        data-focus="audio"  onclick="pickFocus('scan',this)"><span class="fp-title">Audio</span><span class="fp-sub">voice clone</span></button>
            <button class="focus-pill"        data-focus="quick"  onclick="pickFocus('scan',this)"><span class="fp-title">Quick</span><span class="fp-sub">fast triage</span></button>
          </div>
        </div>
        <button class="analyze-btn" id="analyzeBtn" disabled onclick="startAnalysis()">
          Run Forensic Analysis
        </button>
      </div>
    </div>

    <!-- Progress -->
    <div class="card" id="progressCard" style="display:none">
      <div class="card-header"><span class="card-title">Analysis Progress</span></div>
      <div class="card-body">
        <div class="kp-head">
          <div class="kp-stage-now" id="progStage">Uploading&hellip;</div>
          <div class="kp-pct" id="kpPct">0%</div>
        </div>
        <div class="prog-detail" id="progDetail">Connecting to server</div>
        <div class="kp-bar-track"><div class="kp-bar-fill" id="progBar"></div></div>
        <div class="kp-list" id="kpList"></div>
      </div>
    </div>

    <!-- Result -->
    <div class="card" id="resultCard" style="display:none">
      <div class="card-header">
        <span class="card-title">Forensic Result</span>
        <button class="btn-ghost" onclick="clearFile()" style="font-size:11px">Scan another</button>
      </div>
      <div class="card-body" id="resultBody"></div>
    </div>
  </div>

  <!-- ── HISTORY PANEL ── -->
  <div id="panel-history" style="display:none">
    <div class="card">
      <div class="card-header">
        <span class="card-title">Scan History</span>
        <button class="btn-ghost" onclick="loadHistory()">&#x21BB; Refresh</button>
      </div>
      <div class="search-bar">
        <input class="search-input" id="histSearch" placeholder="Search history…" oninput="filterHistory()" />
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>File</th><th>Verdict</th><th>Score</th>
              <th>Visual</th><th>Temporal</th><th>SPN</th><th>Fast</th><th>Time</th>
            </tr>
          </thead>
          <tbody id="historyBody">
            <tr class="empty-row"><td colspan="8">Loading&hellip;</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ── ADMIN PANEL ── -->
  <div id="panel-admin" style="display:none">

    <!-- System stats -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">System Status</span>
        <div class="admin-refresh-bar">
          <span class="admin-refresh-note" id="adminRefreshNote">Auto-refresh every 5s</span>
          <button class="btn-ghost" onclick="loadAdmin()">&#x21BB; Refresh now</button>
        </div>
      </div>
      <div class="card-body">
        <div class="admin-grid" id="adminStats">
          <div class="admin-stat"><div class="stat-val" id="adm-uptime">—</div><div class="stat-label">Uptime</div></div>
          <div class="admin-stat"><div class="stat-val" style="color:var(--blue)" id="adm-active">—</div><div class="stat-label">Active Jobs</div></div>
          <div class="admin-stat"><div class="stat-val" style="color:var(--red)" id="adm-errors">—</div><div class="stat-label">Errored Jobs</div></div>
          <div class="admin-stat"><div class="stat-val" style="color:var(--text3)" id="adm-mem">—</div><div class="stat-label">Memory (MB)</div></div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;font-size:11px;color:var(--text3)">
          <div>Pending: <strong id="adm-pending">—</strong></div>
          <div>Running: <strong id="adm-running">—</strong></div>
          <div>Done: <strong id="adm-done">—</strong></div>
          <div>Total: <strong id="adm-total">—</strong></div>
        </div>
      </div>
    </div>

    <!-- Active / recent jobs -->
    <div class="card">
      <div class="card-header"><span class="card-title">Active &amp; Recent Jobs</span></div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>Job ID</th><th>File</th><th>Type</th><th>Status</th>
              <th>Stage</th><th>Error</th><th>Submitted</th><th>Finished</th>
            </tr>
          </thead>
          <tbody id="adminJobsBody">
            <tr class="empty-row"><td colspan="8">Loading…</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Error log -->
    <div class="card">
      <div class="card-header">
        <span class="card-title">Error Log</span>
        <button class="btn-ghost" onclick="loadAdminLogs()" style="font-size:11px">&#x21BB; Reload</button>
      </div>
      <div class="tbl-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th><th>Job ID</th><th>File</th>
              <th>Stage</th><th>Root Cause</th><th>Traceback</th>
            </tr>
          </thead>
          <tbody id="adminLogsBody">
            <tr class="empty-row"><td colspan="6">Loading…</td></tr>
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
let _adminTimer = null;
function switchTab(name, btn) {
  ['cases','scan','history','admin'].forEach(p => {
    document.getElementById('panel-'+p).style.display = name === p ? '' : 'none';
  });
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  if (name === 'history') loadHistory();
  if (name === 'cases')   { showRegistry(); loadCases(); }
  if (name === 'admin')   { loadAdmin(); startAdminAutoRefresh(); }
  else                    { stopAdminAutoRefresh(); }
}
function startAdminAutoRefresh() {
  stopAdminAutoRefresh();
  _adminTimer = setInterval(loadAdmin, 5000);
}
function stopAdminAutoRefresh() {
  if (_adminTimer) { clearInterval(_adminTimer); _adminTimer = null; }
}

// ── Drag and drop ──
const dz = document.getElementById('dropZone');
const fi = document.getElementById('fileInput');
dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('drag-over'); });
dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
dz.addEventListener('drop', e => {
  e.preventDefault(); dz.classList.remove('drag-over');
  if (e.dataTransfer.files[0]) applyFile(e.dataTransfer.files[0]);
});
fi.addEventListener('change', () => { if (fi.files[0]) applyFile(fi.files[0]); });

const VIDEO_EXT = new Set(['.mp4','.avi','.mov','.mkv','.webm','.m4v']);
const IMAGE_EXT = new Set(['.jpg','.jpeg','.png','.bmp','.webp','.gif','.heic','.heif','.tiff','.tif']);
const AUDIO_EXT = new Set(['.mp3','.wav','.m4a','.flac','.ogg','.aac','.opus','.amr','.wma']);
const ALLOWED_EXT = new Set([...VIDEO_EXT, ...IMAGE_EXT, ...AUDIO_EXT]);
const FILE_ICON = {video:'🎬', image:'🖼️', audio:'🎵'};

function mediaType(ext) {
  if (VIDEO_EXT.has(ext)) return 'video';
  if (IMAGE_EXT.has(ext)) return 'image';
  if (AUDIO_EXT.has(ext)) return 'audio';
  return null;
}

let _file = null, _lastResult = null;

function applyFile(f) {
  const ext = '.' + f.name.split('.').pop().toLowerCase();
  const mt = mediaType(ext);
  if (!mt) { showInlineError('Unsupported file type: ' + ext + '. Allowed: video, image (JPG/PNG/WEBP), audio (MP3/WAV/M4A).'); return; }
  _file = f;
  document.getElementById('fileRow').style.display = 'flex';
  document.getElementById('fileName').textContent  = f.name;
  document.getElementById('fileSize').textContent  = '(' + (f.size/1024/1024).toFixed(1) + ' MB)';
  document.getElementById('analyzeBtn').disabled   = false;
  document.getElementById('dropIcon').textContent  = FILE_ICON[mt] || '📁';
  // Show/hide focus pills — not meaningful for image or audio-only
  document.getElementById('scanFocus').style.display = mt === 'video' ? '' : 'none';
  hideResult();
}
function clearFile() {
  _file = null; fi.value = '';
  document.getElementById('fileRow').style.display = 'none';
  document.getElementById('analyzeBtn').disabled   = true;
  hideResult();
}
function hideResult() {
  document.getElementById('progressCard').style.display = 'none';
  document.getElementById('resultCard').style.display   = 'none';
}

// ── Focus selector ──
const _focus = {scan:'full', ev:'full'};
function pickFocus(panel, btn) {
  _focus[panel] = btn.getAttribute('data-focus');
  btn.parentElement.querySelectorAll('.focus-pill').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}

// ── Keypoint progress ──
let _pollTimer = null, _creepTimer = null, _pollCount = 0;
const MAX_POLLS = 600;  // 600 × 2s = 20 min — enough for CPU-only 5-model video
const KP_DEFS = {
  full:   ['metadata','extraction','visual','audio','temporal','lipsync','spn','forensic','combining'],
  visual: ['metadata','extraction','visual','temporal','spn','forensic','combining'],
  audio:  ['metadata','audio','combining'],
  quick:  ['metadata','extraction','visual','combining'],
  image:  ['metadata','extraction','visual','forensic','combining'],
};
const KP_LABEL = {
  metadata:'Metadata check', extraction:'Frames & face detection', visual:'Visual AI models',
  audio:'Audio / voice analysis', temporal:'Temporal consistency', lipsync:'Lip-sync',
  spn:'Sensor noise (SPN)', forensic:'Forensic rules', combining:'Combining verdict',
};
let _kpList = [], _kpDone = {}, _kpTarget = 0, _kpCur = 0, _elapsed = 0;

function kpFromStage(s) {
  if (!s) return null;
  if (s.startsWith('visual')) return 'visual';
  return s.replace('_done','');
}
function renderKeypoints(focus) {
  _kpList = (KP_DEFS[focus] || KP_DEFS.full).slice(); _kpDone = {};
  const host = document.getElementById('kpList');
  host.innerHTML = _kpList.map(id => `
    <div class="kp-step" id="kp-${id}">
      <div class="kp-dot"></div>
      <div class="kp-name">${esc(KP_LABEL[id]||id)}</div>
      <div class="kp-sub" id="kpsub-${id}"></div>
    </div>`).join('');
}
function setProgress(pct, stage, detail) {
  if (stage  != null) document.getElementById('progStage').textContent  = stage;
  if (detail != null) document.getElementById('progDetail').textContent = detail;
  if (pct    != null) { _kpTarget = pct; startCreep(); }
}
function startCreep() {
  if (_creepTimer) return;
  _creepTimer = setInterval(() => {
    if (_kpCur < _kpTarget) {
      _kpCur = Math.min(_kpTarget, _kpCur + Math.max(0.2, (_kpTarget - _kpCur)*0.08));
      document.getElementById('progBar').style.width   = _kpCur + '%';
      document.getElementById('kpPct').textContent = Math.round(_kpCur) + '%';
    }
  }, 60);
}
function applyStage(stage) {
  _elapsed++;
  const kp = kpFromStage(stage); if (!kp) return;
  const idx = _kpList.indexOf(kp); if (idx < 0) return;
  for (let i = 0; i < idx; i++) markDone(_kpList[i]);
  const isDone = stage.endsWith('_done') || stage === 'done';
  const el = document.getElementById('kp-'+kp);
  if (isDone) {
    markDone(kp);
    setProgress(((idx+1)/_kpList.length)*100, null, 'Elapsed ~'+_elapsed+'s · '+KP_LABEL[kp]+' done');
  } else {
    if (el && !_kpDone[kp]) { el.className = 'kp-step active'; el.querySelector('.kp-dot').innerHTML = '<div class="kp-spin"></div>'; }
    let lbl = KP_LABEL[kp];
    if (stage.startsWith('visual:')) { const m = stage.split(':')[1]; document.getElementById('kpsub-visual').textContent = m; lbl = 'Running '+m; }
    document.getElementById('progStage').textContent = lbl;
    setProgress(((idx+0.5)/_kpList.length)*100, null, 'Elapsed ~'+_elapsed+'s · analyzing');
  }
}
function markDone(id) {
  if (_kpDone[id]) return; _kpDone[id] = true;
  const el = document.getElementById('kp-'+id);
  if (el) { el.className = 'kp-step done'; el.querySelector('.kp-dot').innerHTML = ''; }
}

function startAnalysis() {
  if (!_file) return;
  clearInterval(_pollTimer); clearInterval(_creepTimer); _creepTimer = null;
  _pollCount = 0; _kpCur = 0; _kpTarget = 0; _elapsed = 0;
  const ext = '.' + _file.name.split('.').pop().toLowerCase();
  const mt  = mediaType(ext) || 'video';
  // For image/audio, override focus so the right keypoints show
  const focusKey = mt === 'image' ? 'image' : mt === 'audio' ? 'audio' : _focus.scan;
  document.getElementById('progressCard').style.display = 'block';
  document.getElementById('resultCard').style.display   = 'none';
  document.getElementById('analyzeBtn').disabled = true;
  renderKeypoints(focusKey);
  document.getElementById('progBar').style.width  = '0%';
  document.getElementById('kpPct').textContent = '0%';
  setProgress(3, 'Uploading ' + mt + '…', mt === 'image' ? 'Image forensic analysis' : mt === 'audio' ? 'Voice/audio analysis' : 'Focus: '+_focus.scan);
  const fd = new FormData(); fd.append('file', _file);
  fetch('/analyze/video?focus='+encodeURIComponent(_focus.scan), {method:'POST', body:fd})
    .then(r => r.json())
    .then(data => {
      if (data.job_id) { setProgress(6,'Queued','Job '+data.job_id.slice(0,8)+'… live updates'); _pollTimer = setInterval(() => pollJob(data.job_id), 2000); }
      else if (data.final_score !== undefined) showResult(data);
      else showInlineError('Unexpected response from server.');
    })
    .catch(e => showInlineError('Upload failed: '+e));
}
function pollJob(jobId) {
  _pollCount++;
  if (_pollCount > MAX_POLLS) { clearInterval(_pollTimer); clearInterval(_creepTimer); _creepTimer = null; showInlineError('Timeout. Try again.'); return; }
  fetch('/jobs/'+jobId)
    .then(r => { if (r.status===404) { clearInterval(_pollTimer); clearInterval(_creepTimer); _creepTimer = null; showInlineError('Server restarted. Upload again.'); return null; } return r.json(); })
    .then(data => {
      if (!data) return;
      if (data.stage) applyStage(data.stage);
      if (data.status === 'done') {
        clearInterval(_pollTimer); clearInterval(_creepTimer); _creepTimer = null;
        _kpList.forEach(markDone); _kpCur = 100;
        document.getElementById('progBar').style.width  = '100%';
        document.getElementById('kpPct').textContent = '100%';
        setTimeout(() => showResult(data.result), 350);
      } else if (data.status === 'error') {
        clearInterval(_pollTimer); clearInterval(_creepTimer); _creepTimer = null;
        showInlineError('Analysis error: '+(data.error||'unknown'));
      }
    }).catch(() => {});
}

// ── Render result ──
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function vClass(v) {
  if (!v) return 'verdict-unc';
  const l = v.toLowerCase().replace(/\s/g,'');
  if (l==='fake') return 'verdict-fake';
  if (l.includes('likely')) return 'verdict-likely';
  if (l==='real') return 'verdict-real';
  return 'verdict-unc';
}
function vbClass(v) {
  if (!v) return 'vb-unc';
  const l = v.toLowerCase().replace(/\s/g,'');
  if (l==='fake') return 'vb-fake';
  if (l.includes('likely')) return 'vb-likely';
  if (l==='real') return 'vb-real';
  return 'vb-unc';
}
function vIcon(v) {
  if (!v) return '❓';
  const l = v.toLowerCase().replace(/\s/g,'');
  if (l==='fake') return '🚨';
  if (l.includes('likely')) return '⚠️';
  if (l==='real') return '✅';
  return '❓';
}
function barClass(v) { return v>=70 ? 'sig-fill-r' : v>=35 ? 'sig-fill-a' : 'sig-fill-g'; }
function pctColor(v) { return v>=70 ? 'var(--red)' : v>=35 ? 'var(--amber)' : 'var(--green)'; }
function chipClass(v) {
  if (!v) return 'vc-unc';
  const l = v.toLowerCase().replace(/\s/g,'');
  if (l==='fake') return 'vc-fake';
  if (l.includes('likely')) return 'vc-likely';
  if (l==='real') return 'vc-real';
  return 'vc-unc';
}
const SIGS = [
  {key:'visual',   label:'Visual',   wt:'58%'},
  {key:'audio',    label:'Audio',    wt:'17%'},
  {key:'temporal', label:'Temporal', wt:'12%'},
  {key:'forensic', label:'Forensic', wt:' 8%'},
  {key:'lipsync',  label:'Lip-sync', wt:' 0%'},
  {key:'spn',      label:'SPN',      wt:' 0%'},
  {key:'metadata', label:'Metadata', wt:' 5%'},
];

function showResult(r) {
  clearInterval(_pollTimer);
  document.getElementById('progressCard').style.display = 'none';
  document.getElementById('resultCard').style.display   = 'block';
  document.getElementById('analyzeBtn').disabled = false;
  _lastResult = r;
  const cs      = r.component_scores || {};
  const verdict = r.verdict || 'UNKNOWN';
  const score   = r.final_score!=null ? parseFloat(r.final_score).toFixed(1) : '--';
  const sNum    = parseFloat(score)||0;
  const vc      = vClass(verdict);
  const ts      = r.timestamp ? new Date(r.timestamp).toLocaleString() : '';
  const fn      = r.filename || r.video_path || '';

  const sigRows = SIGS.map(sig => {
    const raw = cs[sig.key];
    if (raw==null) return `
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
        <div class="sig-pct" style="color:${pctColor(v)};font-weight:700">${v}%</div>
        <div class="sig-wt">${esc(sig.wt)}</div>
      </div>`;
  }).join('');

  const anom    = (r.anomalies||[]).filter(a => !a.startsWith('Meta:'));
  const anomHtml = anom.length ? `
    <div class="anomaly-section">
      <div class="anomaly-label">Anomalies detected (${anom.length})</div>
      <div class="anomaly-list">
        ${anom.slice(0,8).map(a => `<div class="anomaly-item">⚠ ${esc(a)}</div>`).join('')}
      </div>
    </div>` : '';

  const fastHtml = r.fast_path
    ? `<span class="fast-badge">Fast-path &middot; ${esc(r.fast_reason||'metadata')}</span>` : '';

  document.getElementById('resultBody').innerHTML = `
    <div class="verdict-banner ${vbClass(verdict)}">
      <div class="verdict-icon">${vIcon(verdict)}</div>
      <div class="verdict-info">
        <div class="${vc} verdict-label">${esc(verdict)}</div>
        <div class="${vc} verdict-score">${score}%</div>
      </div>
      <div class="verdict-meta">
        <div class="verdict-file" title="${esc(fn)}">${esc(fn)}</div>
        <div class="verdict-ts">${esc(ts)}</div>
        ${fastHtml}
      </div>
    </div>
    <div class="sig-section">
      <div class="sig-section-label">Signal Breakdown</div>
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
      <span class="feedback-thanks" id="feedbackThanks" style="display:none">✓ Feedback logged. Thank you.</span>
    </div>
  `;
  loadHistory();
}

// ── Feedback ──
let _selectedVerdict = null;
function toggleFeedback() { document.getElementById('feedbackForm').classList.toggle('open'); }
function selectVerdict(btn, v) {
  _selectedVerdict = v;
  document.querySelectorAll('.verdict-opt').forEach(b => b.className = 'verdict-opt');
  const cls = v==='FAKE' ? 'sel-fake' : v==='LIKELY FAKE' ? 'sel-likely' : v==='REAL' ? 'sel-real' : 'sel-uncertain';
  btn.classList.add(cls);
}
function submitFeedback() {
  if (!_selectedVerdict || !_lastResult) return;
  const note = document.getElementById('feedbackNote').value;
  fetch('/feedback', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      filename: _lastResult.filename||_lastResult.video_path||'',
      predicted_verdict: _lastResult.verdict||'',
      predicted_score: _lastResult.final_score||0,
      correct_verdict: _selectedVerdict,
      component_scores: _lastResult.component_scores||{},
      notes: note,
    })})
    .then(r => r.json())
    .then(() => {
      document.getElementById('feedbackThanks').style.display = 'block';
      document.querySelector('.feedback-submit').style.display = 'none';
    }).catch(() => {});
}
function showInlineError(msg) {
  document.getElementById('progressCard').style.display = 'none';
  document.getElementById('resultCard').style.display   = 'block';
  document.getElementById('analyzeBtn').disabled = false;
  document.getElementById('resultBody').innerHTML = `
    <div class="error-box">
      🔴 ${esc(msg)}
      <div class="error-hint">Check /health or /docs for API status.</div>
    </div>`;
}

// ── History ──
let _historyRows = [];
function loadHistory() {
  fetch('/results?limit=50')
    .then(r => r.json())
    .then(d => { _historyRows = d.results||[]; renderHistory(_historyRows); })
    .catch(() => {});
}
function filterHistory() {
  const q = document.getElementById('histSearch').value.toLowerCase();
  renderHistory(q ? _historyRows.filter(r => JSON.stringify(r).toLowerCase().includes(q)) : _historyRows);
}
function renderHistory(rows) {
  const tb = document.getElementById('historyBody');
  if (!rows.length) { tb.innerHTML = '<tr class="empty-row"><td colspan="8">No scans yet</td></tr>'; return; }
  tb.innerHTML = rows.map(r => {
    const v  = r.verdict||'–'; const s = r.final_score!=null ? parseFloat(r.final_score).toFixed(1) : '–';
    const sn = parseFloat(s)||0;
    const fn = (r.filename||r.video_path||'–').split(/[/\\]/).pop();
    const cs = r.component_scores||{};
    const vis  = cs.visual   !=null ? Math.round(cs.visual)+'%'   : '–';
    const temp = cs.temporal !=null ? Math.round(cs.temporal)+'%' : '–';
    const spn  = cs.spn      !=null ? Math.round(cs.spn)+'%'      : '–';
    const ts   = r.timestamp ? new Date(r.timestamp).toLocaleString() : '–';
    return `<tr>
      <td class="mono" style="max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(fn)}">${esc(fn)}</td>
      <td><span class="verdict-chip ${chipClass(v)}">${esc(v)}</span></td>
      <td class="mono" style="color:${pctColor(sn)};font-weight:700">${s}%</td>
      <td class="mono" style="color:var(--text3)">${esc(vis)}</td>
      <td class="mono" style="color:var(--text3)">${esc(temp)}</td>
      <td class="mono" style="color:var(--text3)">${esc(spn)}</td>
      <td style="color:var(--text3)">${r.fast_path ? '⚡ Yes':'–'}</td>
      <td style="color:var(--text3);white-space:nowrap">${esc(ts)}</td>
    </tr>`;
  }).join('');
}

// ══════════════════════════════════════════════════════════════════
//  CASE MANAGEMENT
// ══════════════════════════════════════════════════════════════════
let _activeCase = null, _allCases = [];

function showRegistry() {
  document.getElementById('caseRegistry').style.display = '';
  document.getElementById('newCaseCard').style.display  = 'none';
  document.getElementById('caseDetail').style.display   = 'none';
}
function showNewCaseForm() {
  document.getElementById('caseRegistry').style.display = 'none';
  document.getElementById('newCaseCard').style.display  = '';
  document.getElementById('caseDetail').style.display   = 'none';
}

function loadCases() {
  fetch('/cases')
    .then(r => r.json())
    .then(d => { _allCases = d.cases||[]; renderCaseList(_allCases); updateStats(_allCases); })
    .catch(() => {});
}
function filterCases() {
  const q = document.getElementById('caseSearch').value.toLowerCase();
  renderCaseList(q ? _allCases.filter(c => JSON.stringify(c).toLowerCase().includes(q)) : _allCases);
}
function updateStats(cases) {
  document.getElementById('st-total').textContent    = cases.length;
  document.getElementById('st-open').textContent     = cases.filter(c => c.status==='OPEN').length;
  document.getElementById('st-critical').textContent = cases.filter(c => (c.priority||'').toUpperCase()==='CRITICAL').length;
  document.getElementById('st-closed').textContent   = cases.filter(c => c.status==='CLOSED').length;
}
function renderCaseList(cases) {
  const tb = document.getElementById('caseListBody');
  if (!cases.length) { tb.innerHTML = '<tr class="empty-row"><td colspan="7">No cases yet — click + New Case to register one</td></tr>'; return; }
  tb.innerHTML = cases.map(c => {
    const upd = c.updated_at ? new Date(c.updated_at).toLocaleString() : '–';
    const pri = (c.priority||'MEDIUM').toUpperCase();
    return `<tr onclick="openCase('${esc(c.case_id)}')">
      <td class="mono" style="font-weight:600">${esc(c.case_no||'–')}</td>
      <td style="font-weight:500">${esc(c.title||'(untitled)')}</td>
      <td><span class="pri-chip pri-${esc(pri)}">${esc(pri)}</span></td>
      <td><span class="status-chip status-OPEN" data-s="${esc(c.status)}">${esc(c.status)}</span></td>
      <td style="color:var(--text2)">${esc(c.officer_name||'–')}</td>
      <td class="mono" style="color:var(--text3);font-weight:600">${c.evidence_count}</td>
      <td style="color:var(--text3);white-space:nowrap">${esc(upd)}</td>
    </tr>`;
  }).join('');
}
function val(id) { return document.getElementById(id).value.trim(); }
function createCase() {
  const body = {
    case_no: val('nc_case_no'), title: val('nc_title'),
    officer_name: val('nc_officer_name'), officer_badge: val('nc_officer_badge'),
    department: val('nc_department'), priority: val('nc_priority'),
    suspect: val('nc_suspect'), victim: val('nc_victim'),
    source_url: val('nc_source_url'), incident_date: val('nc_incident_date'),
    notes: val('nc_notes'),
  };
  fetch('/cases', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
    .then(r => r.json())
    .then(c => {
      ['nc_case_no','nc_title','nc_officer_name','nc_officer_badge','nc_department',
       'nc_suspect','nc_victim','nc_source_url','nc_incident_date','nc_notes']
        .forEach(id => document.getElementById(id).value = '');
      loadCases(); openCase(c.case_id);
    })
    .catch(e => alert('Create failed: '+e));
}
function openCase(caseId) {
  fetch('/cases/'+caseId)
    .then(r => r.json())
    .then(c => { _activeCase = c; renderCaseDetail(c); })
    .catch(() => {});
}
function renderCaseDetail(c) {
  document.getElementById('caseRegistry').style.display = 'none';
  document.getElementById('newCaseCard').style.display  = 'none';
  const d = document.getElementById('caseDetail'); d.style.display = '';
  const pri = (c.priority||'MEDIUM').toUpperCase();
  const meta = [
    ['Investigating Officer', c.officer_name],['Badge / ID', c.officer_badge],
    ['Department', c.department],['Suspect', c.suspect],
    ['Victim / Complainant', c.victim],['Incident Date', c.incident_date],
    ['Source / URL', c.source_url],['Opened', c.created_at ? new Date(c.created_at).toLocaleString() : ''],
  ].map(([k,v]) => `<div class="meta-item"><span>${esc(k)}</span>${esc(v||'–')}</div>`).join('');
  const ev = (c.evidence||[]).map(e => evidenceCard(e)).join('') ||
    '<p style="color:var(--text3);font-size:12px;padding:8px 0">No evidence attached yet.</p>';

  d.innerHTML = `
    <div class="card">
      <div class="card-header">
        <div>
          <div style="font-size:16px;font-weight:700;color:var(--text)">${esc(c.title||'(untitled case)')}</div>
          <div class="case-sub">
            <span class="mono" style="font-weight:600">${esc(c.case_no||c.case_id)}</span>
            &middot; <span class="pri-chip pri-${esc(pri)}">${esc(pri)}</span>
            &middot; <span class="status-chip status-OPEN" data-s="${esc(c.status)}">${esc(c.status)}</span>
          </div>
        </div>
        <div class="action-row">
          <select id="cd_status" onchange="changeStatus('${esc(c.case_id)}', this.value)"
            style="font-size:11px;padding:5px 8px;border-radius:5px">
            <option ${c.status==='OPEN'?'selected':''}>OPEN</option>
            <option ${c.status==='UNDER REVIEW'?'selected':''}>UNDER REVIEW</option>
            <option ${c.status==='CLOSED'?'selected':''}>CLOSED</option>
          </select>
          <a class="btn-ghost" href="/cases/${esc(c.case_id)}/report" target="_blank" style="font-size:11px;text-decoration:none;padding:6px 12px">📄 Report</a>
          <button class="btn-ghost" onclick="showRegistry();loadCases()" style="font-size:11px">&larr; Back</button>
        </div>
      </div>
      <div class="card-body">
        <div class="meta-grid">${meta}</div>
        ${c.notes ? `<hr class="section-div"><div style="font-size:12px;color:var(--text2)"><span style="color:var(--text3);font-size:10px;text-transform:uppercase;font-weight:700;letter-spacing:.06em">Notes</span><br><br>${esc(c.notes)}</div>` : ''}
      </div>
    </div>

    <div class="card">
      <div class="card-header"><span class="card-title">Add Evidence</span></div>
      <div class="card-body">
        <div class="upload-zone" id="evDrop">
          <input type="file" id="evFileInput" accept=".mp4,.avi,.mov,.mkv,.webm,.m4v,.jpg,.jpeg,.png,.bmp,.webp,.gif,.heic,.tiff,.mp3,.wav,.m4a,.flac,.ogg,.aac,.opus,.amr">
          <div class="upload-icon">🎬</div>
          <div class="upload-label">Drop evidence file or click to browse</div>
          <div class="upload-hint">Video &middot; Photo &middot; Audio &mdash; SHA-256 hash recorded for chain-of-custody &middot; max 500 MB</div>
        </div>
        <div class="focus-group" id="evFocus">
          <div class="focus-label">Focus analysis on:</div>
          <div class="focus-pills">
            <button class="focus-pill active" data-focus="full"   onclick="pickFocus('ev',this)"><span class="fp-title">Full</span><span class="fp-sub">all signals</span></button>
            <button class="focus-pill"        data-focus="visual" onclick="pickFocus('ev',this)"><span class="fp-title">Face</span><span class="fp-sub">visual + forensic</span></button>
            <button class="focus-pill"        data-focus="audio"  onclick="pickFocus('ev',this)"><span class="fp-title">Audio</span><span class="fp-sub">voice clone</span></button>
            <button class="focus-pill"        data-focus="quick"  onclick="pickFocus('ev',this)"><span class="fp-title">Quick</span><span class="fp-sub">fast triage</span></button>
          </div>
        </div>
        <div id="evProgress" style="display:none;margin-top:14px">
          <div class="kp-head"><div class="kp-stage-now" id="evStage">Uploading…</div>
            <div class="kp-pct" id="evPct">0%</div></div>
          <div class="prog-detail" id="evDetail"></div>
          <div class="kp-bar-track"><div class="kp-bar-fill" id="evBar"></div></div>
          <div class="kp-list" id="evKpList"></div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">Evidence &amp; Findings (${(c.evidence||[]).length})</span>
      </div>
      <div class="card-body" id="evList">${ev}</div>
    </div>
  `;

  _focus.ev = 'full';
  const efi = document.getElementById('evFileInput');
  efi.addEventListener('change', () => { if (efi.files[0]) uploadEvidence(c.case_id, efi.files[0]); });
}

function evidenceCard(e) {
  const r = e.result||{};
  const v = r.verdict||(e.status==='done'?'–':e.status);
  const s = r.final_score!=null ? parseFloat(r.final_score).toFixed(1)+'%' : '';
  const sn = parseFloat(r.final_score)||0;
  const up = e.uploaded_at ? new Date(e.uploaded_at).toLocaleString() : '';
  let verdictHtml = '';
  if (e.status==='done') {
    verdictHtml = `<span class="verdict-chip ${chipClass(v)}">${esc(v)}</span>
      <span class="mono" style="color:${pctColor(sn)};font-weight:700;margin-left:6px">${s}</span>`;
  } else if (e.status==='running'||e.status==='pending') {
    verdictHtml = `<span style="color:var(--blue);font-size:11px;font-weight:600">Analyzing…</span>`;
  } else if (e.status==='error') {
    verdictHtml = `<span style="color:var(--red);font-size:11px;font-weight:600">Error</span>`;
  }
  return `<div class="ev-card">
    <div class="ev-top">
      <div style="min-width:0">
        <div class="ev-fn">🎞 ${esc(e.filename)}</div>
        <div class="ev-hash">SHA-256: ${esc(e.sha256||'')}</div>
      </div>
      <div style="white-space:nowrap;text-align:right;flex-shrink:0">
        ${verdictHtml}
        <div style="font-size:10px;color:var(--text3);margin-top:4px">${esc(up)} &middot; ${esc(e.uploaded_by||'')}</div>
      </div>
    </div>
  </div>`;
}

// Evidence-panel keypoint state
let _evKp=[], _evDone={}, _evTarget=0, _evCur=0, _evCreep=null;
function evRenderKp(focus) {
  _evKp=(KP_DEFS[focus]||KP_DEFS.full).slice(); _evDone={};
  document.getElementById('evKpList').innerHTML = _evKp.map(id => `
    <div class="kp-step" id="evkp-${id}"><div class="kp-dot"></div>
    <div class="kp-name">${esc(KP_LABEL[id]||id)}</div>
    <div class="kp-sub" id="evkpsub-${id}"></div></div>`).join('');
}
function evCreepStart() {
  if (_evCreep) return;
  _evCreep = setInterval(() => {
    if (_evCur < _evTarget) {
      _evCur = Math.min(_evTarget, _evCur + Math.max(0.2, (_evTarget-_evCur)*0.08));
      document.getElementById('evBar').style.width = _evCur+'%';
      document.getElementById('evPct').textContent = Math.round(_evCur)+'%';
    }
  }, 60);
}
function evMarkDone(id) {
  if (_evDone[id]) return; _evDone[id]=true;
  const el = document.getElementById('evkp-'+id);
  if (el) { el.className='kp-step done'; el.querySelector('.kp-dot').innerHTML=''; }
}
function evApplyStage(stage) {
  const kp = kpFromStage(stage); if (!kp) return;
  const idx = _evKp.indexOf(kp); if (idx<0) return;
  for (let i=0;i<idx;i++) evMarkDone(_evKp[i]);
  const el = document.getElementById('evkp-'+kp);
  if (stage.endsWith('_done')||stage==='done') {
    evMarkDone(kp); _evTarget=((idx+1)/_evKp.length)*100; evCreepStart();
    document.getElementById('evStage').textContent = KP_LABEL[kp]+' done';
  } else {
    if (el&&!_evDone[kp]) { el.className='kp-step active'; el.querySelector('.kp-dot').innerHTML='<div class="kp-spin"></div>'; }
    let lbl=KP_LABEL[kp];
    if (stage.startsWith('visual:')) { const m=stage.split(':')[1]; document.getElementById('evkpsub-visual').textContent=m; lbl='Running '+m; }
    document.getElementById('evStage').textContent=lbl;
    _evTarget=((idx+0.5)/_evKp.length)*100; evCreepStart();
  }
}

function uploadEvidence(caseId, file) {
  const officer = (_activeCase&&_activeCase.officer_name)||'';
  const focus = _focus.ev;
  clearInterval(_evPoll); clearInterval(_evCreep); _evCreep=null;
  _evCur=0; _evTarget=3;
  const fd = new FormData(); fd.append('file', file);
  document.getElementById('evProgress').style.display='block';
  document.getElementById('evBar').style.width='0%';
  document.getElementById('evPct').textContent='0%';
  document.getElementById('evStage').textContent='Uploading evidence…';
  document.getElementById('evDetail').textContent=file.name+' · focus: '+focus;
  evRenderKp(focus); evCreepStart();
  fetch('/cases/'+caseId+'/evidence?uploaded_by='+encodeURIComponent(officer)+'&focus='+encodeURIComponent(focus), {method:'POST', body:fd})
    .then(r => r.json())
    .then(data => {
      if (data.job_id) {
        document.getElementById('evDetail').textContent = 'Hash '+(data.sha256||'').slice(0,16)+'… · chain-of-custody recorded';
        pollEvidence(data.job_id, caseId);
      } else { alert('Upload failed'); }
    }).catch(e => alert('Upload failed: '+e));
}

let _evPoll = null;
function pollEvidence(jobId, caseId) {
  clearInterval(_evPoll); let n=0;
  _evPoll = setInterval(() => {
    n++; if (n>250) { clearInterval(_evPoll); return; }
    fetch('/jobs/'+jobId).then(r => r.ok ? r.json() : null).then(j => {
      if (!j) return;
      if (j.stage) evApplyStage(j.stage);
      if (j.status==='done'||j.status==='error') {
        clearInterval(_evPoll); clearInterval(_evCreep); _evCreep=null;
        _evKp.forEach(evMarkDone);
        document.getElementById('evBar').style.width='100%';
        document.getElementById('evPct').textContent='100%';
        setTimeout(() => openCase(caseId), 600);
      }
    }).catch(() => {});
  }, 2000);
}

function changeStatus(caseId, status) {
  fetch('/cases/'+caseId, {method:'PATCH', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({status})}).then(() => loadCases()).catch(() => {});
}

// ══════════════════════════════════════════════════════════════════
//  ADMIN PANEL
// ══════════════════════════════════════════════════════════════════
function loadAdmin() {
  loadAdminStats();
  loadAdminJobs();
  loadAdminLogs();
}

function loadAdminStats() {
  fetch('/admin/stats')
    .then(r => r.json())
    .then(d => {
      document.getElementById('adm-uptime').textContent  = d.uptime  || '—';
      document.getElementById('adm-mem').textContent     = d.memory_mb != null ? d.memory_mb : '—';
      document.getElementById('adm-active').textContent  = (d.jobs.pending||0) + (d.jobs.running||0);
      document.getElementById('adm-errors').textContent  = d.jobs.error  || 0;
      document.getElementById('adm-pending').textContent = d.jobs.pending || 0;
      document.getElementById('adm-running').textContent = d.jobs.running || 0;
      document.getElementById('adm-done').textContent    = d.jobs.done    || 0;
      document.getElementById('adm-total').textContent   = d.total_jobs   || 0;
      document.getElementById('adminRefreshNote').textContent =
        'Last refresh: ' + new Date().toLocaleTimeString() + '  · auto every 5s';
    }).catch(() => {});
}

function loadAdminJobs() {
  fetch('/admin/jobs?limit=50')
    .then(r => r.json())
    .then(d => {
      const tb = document.getElementById('adminJobsBody');
      const rows = d.jobs || [];
      if (!rows.length) { tb.innerHTML = '<tr class="empty-row"><td colspan="8">No jobs yet</td></tr>'; return; }
      tb.innerHTML = rows.map(j => {
        const st   = j.status || '';
        const tag  = `<span class="tag-${st}">${esc(st.toUpperCase())}</span>`;
        const err  = j.error ? `<span class="tb-error" title="${esc(j.traceback||j.error)}" onclick="this.classList.toggle('tb-expand')">${esc(j.error.slice(0,60))}${j.error.length>60?'…':''}</span>` : '—';
        const sub  = j.submitted ? new Date(j.submitted).toLocaleTimeString() : '—';
        const fin  = j.finished  ? new Date(j.finished).toLocaleTimeString()  : '—';
        const fn   = (j.filename||'—').split(/[/\\]/).pop();
        return `<tr>
          <td class="mono" style="font-size:10px;color:var(--text3)">${esc((j.job_id||'').slice(0,8))}</td>
          <td class="mono" style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(j.filename)}">${esc(fn)}</td>
          <td style="color:var(--text3);font-size:11px">${esc(j.media_type||'—')}</td>
          <td>${tag}</td>
          <td class="log-stage">${esc(j.stage||'—')}</td>
          <td>${err}</td>
          <td style="color:var(--text3);white-space:nowrap;font-size:11px">${esc(sub)}</td>
          <td style="color:var(--text3);white-space:nowrap;font-size:11px">${esc(fin)}</td>
        </tr>`;
      }).join('');
    }).catch(() => {});
}

function loadAdminLogs() {
  fetch('/admin/logs?log_type=errors&limit=50')
    .then(r => r.json())
    .then(d => {
      const tb = document.getElementById('adminLogsBody');
      const rows = d.entries || [];
      if (!rows.length) { tb.innerHTML = '<tr class="empty-row"><td colspan="6">No errors logged yet</td></tr>'; return; }
      tb.innerHTML = rows.map(e => {
        const ts  = e.ts ? new Date(e.ts).toLocaleString() : '—';
        const fn  = (e.filename||'—').split(/[/\\]/).pop();
        const tb2 = e.traceback
          ? `<span class="tb-error" onclick="this.classList.toggle('tb-expand')" title="Click to expand">${esc((e.traceback||'').split('\\n').pop().slice(0,60))}…</span>`
          : '—';
        return `<tr>
          <td style="white-space:nowrap;font-size:11px;color:var(--text3)">${esc(ts)}</td>
          <td class="mono" style="font-size:10px;color:var(--text3)">${esc((e.job_id||'').slice(0,8))}</td>
          <td class="mono" style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(fn)}</td>
          <td class="log-stage">${esc(e.stage||'—')}</td>
          <td style="color:var(--red);font-size:11px;max-width:220px">${esc((e.error||'').slice(0,120))}</td>
          <td>${tb2}</td>
        </tr>`;
      }).join('');
    }).catch(() => {});
}

loadHistory();
loadCases();
</script>
</body>
</html>"""
