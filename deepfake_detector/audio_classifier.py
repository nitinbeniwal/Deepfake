import os, statistics

AUDIO_MODEL = "Hemgg/Deepfake-audio-detection"
_FAKE = ("fake","deepfake","spoof","synthetic","artificial","generated","ai","aivoice","label_1")
_REAL = ("real","genuine","authentic","human","bonafide","live","natural","label_0")
VIDEO_EXTS = {".mp4",".avi",".mov",".mkv",".webm",".m4v"}

_pipe, _lock = None, None

def _get_pipe():
    global _pipe, _lock
    import threading
    if _lock is None: _lock = threading.Lock()
    if _pipe is None:
        with _lock:
            if _pipe is None:
                from transformers import pipeline
                print(f"Loading audio model: {AUDIO_MODEL} ...")
                _pipe = pipeline("audio-classification", model=AUDIO_MODEL)
                print("Audio model loaded ✅")
    return _pipe

def _score(results):
    fp = rp = None
    for r in results:
        lbl = r["label"].strip().lower()
        if any(t in lbl for t in _FAKE) and not any(t in lbl for t in _REAL):
            fp = max(fp, r["score"]) if fp else r["score"]
        elif any(t in lbl for t in _REAL) and not any(t in lbl for t in _FAKE):
            rp = max(rp, r["score"]) if rp else r["score"]
    if fp: return round(fp * 100, 2)
    if rp: return round((1 - rp) * 100, 2)
    top = max(results, key=lambda r: r["score"])
    return round(((1-top["score"]) if any(t in top["label"].lower() for t in _REAL) else top["score"]) * 100, 2)

def _to_wav(path):
    if os.path.splitext(path)[1].lower() not in VIDEO_EXTS:
        return path
    import subprocess, imageio_ffmpeg
    out = path + ".extracted.wav"
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-i", path,
                        "-vn", "-ac","1","-ar","16000","-y", out], capture_output=True)
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError("Audio extraction failed")
    return out

def classify_audio(path):
    import librosa
    wav = _to_wav(path)
    cleanup = wav != path
    try:
        y, sr = librosa.load(wav, sr=16000, mono=True)
        dur, pipe, W = len(y)/sr, _get_pipe(), 4.0
        if dur <= W:
            return round(statistics.median([_score(pipe({"array": y, "sampling_rate": sr}))]), 2)
        scores, start = [], 0.0
        while start < dur:
            chunk = y[int(start*sr):int(min(dur, start+W)*sr)]
            if len(chunk) < sr * 0.5: break
            scores.append(_score(pipe({"array": chunk, "sampling_rate": sr})))
            start += W
        return round(statistics.median(scores), 2) if scores else 0.0
    finally:
        if cleanup and os.path.exists(wav):
            try: os.remove(wav)
            except OSError: pass
