import os, json, subprocess
from datetime import datetime
from pathlib import Path

_AI_TAGS = (
    # deepfake tools
    "fakeapp","deepfacelab","facefusion","roop","simswap","wav2lip","sadtalker",
    # commercial AI video
    "synthesia","heygen","runway","pika","sora","kling","veo","gemini","bard",
    "invideo","descript","kapwing","pictory","lumen5",
    # image generators
    "dall-e","midjourney","stable-diffusion","firefly","imagen","flux","ideogram",
    "adobe firefly","canva",
    # generic AI signals
    "google deepmind","openai","anthropic","meta ai",
)

# Confirmed AI platform encoders (very high confidence)
_AI_PLATFORM_ENCODERS = ("google","goog","youtube","veo","openai","tiktok","bytedance","meta-ai")
# FFmpeg version ranges common in AI tool pipelines (moderate confidence)
_AI_ENCODERS = ("lavf58","lavf59","lavf60","lavf61")

_SIGS = {
    b'\x00\x00\x00\x18ftyp': 'mp4', b'\x00\x00\x00\x1cftyp': 'mp4',
    b'\x1a\x45\xdf\xa3': 'mkv', b'RIFF': 'avi',
    b'\xff\xd8\xff': 'jpeg', b'\x89PNG': 'png',
}
_AI_SIZES = {(512,512),(768,768),(1024,1024),(512,768),(768,512),(576,1024),(1024,576)}

def _sig(path):
    ext = Path(path).suffix.lower().lstrip(".")
    try:
        with open(path,"rb") as f: h = f.read(16)
    except OSError: return True, "unreadable"
    det = next((t for s,t in _SIGS.items() if h[:len(s)]==s), None)
    if not det: return True, "unknown"
    ok = {"mp4":{"mp4","m4v"},"mkv":{"mkv"},"avi":{"avi"},
          "jpeg":{"jpg","jpeg"},"png":{"png"}}.get(det,set())
    return ext in ok, f"ext={ext} magic={det}" if ext not in ok else det

def _cv2_probe(path):
    """Minimal stream info via OpenCV when ffprobe is unavailable."""
    try:
        import cv2
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return None
        fps  = cap.get(cv2.CAP_PROP_FPS)
        nfr  = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        w    = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h    = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if not (w and h):
            return None
        dur = nfr / fps if fps > 0 else 0
        return {
            "streams": [{"codec_type": "video", "width": w, "height": h,
                         "avg_frame_rate": f"{int(round(fps))}/1",
                         "nb_frames": str(int(nfr))}],
            "format":  {"duration": str(round(dur, 2)),
                        "size": str(os.path.getsize(path)),
                        "tags": {}},
        }
    except Exception:
        return None


def _ffprobe(path):
    try:
        import imageio_ffmpeg
        fp = os.path.join(os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()),
                          "ffprobe.exe" if os.name=="nt" else "ffprobe")
        if not os.path.exists(fp): fp = "ffprobe"
        r = subprocess.run([fp,"-v","quiet","-print_format","json",
                            "-show_streams","-show_format",path],
                           capture_output=True, timeout=30)
        if r.returncode == 0:
            return json.loads(r.stdout)
    except Exception:
        pass
    return _cv2_probe(path)

def analyze_video_metadata(path):
    anom, score, meta = [], 0, {}
    ok, sig = _sig(path)
    if not ok: anom.append(f"Signature mismatch: {sig}"); score += 20

    probe = _ffprobe(path)
    if probe:
        fmt, streams = probe.get("format",{}), probe.get("streams",[])
        enc = fmt.get("tags",{}).get("encoder","") or fmt.get("tags",{}).get("Encoder","")
        meta["encoder"] = enc
        if enc:
            el = enc.lower()
            if any(a in el for a in _AI_TAGS):
                anom.append(f"AI platform encoder: {enc}"); score += 50
            elif any(a in el for a in _AI_PLATFORM_ENCODERS):
                # Google/YouTube/Veo encoder = near-certain AI platform output
                anom.append(f"AI platform encoder (Google/Veo): {enc}"); score += 50
            elif any(a in el for a in _AI_ENCODERS):
                anom.append(f"AI-associated encoder version: {enc}"); score += 20
            elif "lavf" in el or "lavc" in el:
                anom.append(f"FFmpeg re-encode (common in AI tools): {enc}"); score += 10
        if not fmt.get("tags",{}).get("creation_time"):
            anom.append("No creation_time (stripped)"); score += 15

        vids = [s for s in streams if s.get("codec_type")=="video"]
        auds = [s for s in streams if s.get("codec_type")=="audio"]
        if vids and not auds: anom.append("No audio stream"); score += 10
        if len(vids) > 1:    anom.append(f"Multiple video streams: {len(vids)}"); score += 10

        for v in vids:
            meta["video_codec"] = v.get("codec_name","")
            w,h = int(v.get("width",0)), int(v.get("height",0))
            br  = int(v.get("bit_rate",0) or fmt.get("bit_rate",0) or 0)
            meta.update({"resolution":f"{w}x{h}","bitrate":br})
            if w and h:
                if (w,h) in _AI_SIZES: anom.append(f"AI-canvas resolution: {w}x{h}"); score += 20
                if br:
                    px = w*h
                    if br < px*0.001 or br > px*0.06: anom.append(f"Unusual bitrate {br//1000}kbps for {w}x{h}"); score += 10
            fps_s = v.get("avg_frame_rate","0/1")
            try:
                n,d = map(int,fps_s.split("/")); fps = n/d if d else 0
                meta["fps"] = round(fps,2)
                if 0 < fps < 10 or fps > 60: anom.append(f"Unusual FPS: {fps:.1f}"); score += 5
            except Exception: pass

        for a in auds:
            sr = int(a.get("sample_rate",0) or 0)
            meta["audio_sample_rate"] = sr
            if sr and sr not in {8000,11025,16000,22050,44100,48000}:
                anom.append(f"Non-standard sample rate: {sr}Hz"); score += 5
    else:
        anom.append("ffprobe unavailable")

    return {"score": min(100,score), "anomalies": anom, "metadata": meta, "suspicious": score >= 25}

def analyze_image_metadata(path):
    from PIL import Image
    anom, score, meta = [], 0, {}
    ok, sig = _sig(path)
    if not ok: anom.append(f"Signature mismatch: {sig}"); score += 15

    try:
        img = Image.open(path)
        meta.update({"format": img.format, "size": f"{img.width}x{img.height}"})
        if (img.width, img.height) in _AI_SIZES:
            anom.append(f"Common AI size: {img.width}x{img.height}"); score += 10
        raw = img._getexif() if hasattr(img,"_getexif") else None
        if raw is None:
            anom.append("No EXIF (AI-generated or stripped)"); score += 10
        else:
            from PIL.ExifTags import TAGS
            exif = {TAGS.get(k,k):v for k,v in raw.items()}
            sw = str(exif.get("Software","")).lower()
            if sw and any(a in sw for a in _AI_TAGS):
                anom.append(f"AI in EXIF Software: {sw}"); score += 40
            dt_o, dt_m = exif.get("DateTimeOriginal",""), exif.get("DateTime","")
            if dt_o and dt_m and dt_o != dt_m:
                try:
                    diff = abs((datetime.strptime(dt_m,"%Y:%m:%d %H:%M:%S") -
                                datetime.strptime(dt_o,"%Y:%m:%d %H:%M:%S")).days)
                    if diff > 30: anom.append(f"Modified {diff}d after capture"); score += 8
                except Exception: pass
    except Exception as e:
        anom.append(f"Metadata error: {e}")

    return {"score": min(100,score), "anomalies": anom, "metadata": meta, "suspicious": score >= 20}
