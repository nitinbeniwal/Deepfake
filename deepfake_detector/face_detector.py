"""
face_detector.py — Multi-stage face detection pipeline.

Primary:  MTCNN (facenet-pytorch) — handles angles, occlusion, multiple faces.
Fallback: Haar cascade (bundled with opencv) — zero extra dependencies.

MTCNN is significantly more accurate than Haar for deepfake detection
because faces in manipulated videos are often at non-frontal angles.
"""
import cv2, os, numpy as np

# ── MTCNN (primary, best accuracy) ───────────────────────────────────────────
_mtcnn     = None
_mtcnn_ok  = None   # None=untested, True=loaded, False=failed

def _get_mtcnn():
    global _mtcnn, _mtcnn_ok
    if _mtcnn_ok is False:
        return None
    if _mtcnn is None:
        try:
            from facenet_pytorch import MTCNN
            _mtcnn = MTCNN(
                keep_all   = True,
                device     = "cpu",
                min_face_size = 20,
                thresholds = [0.6, 0.7, 0.7],
                post_process = False,
            )
            _mtcnn_ok = True
            print("Face detector: MTCNN ready")
        except Exception as e:
            print(f"Face detector: MTCNN unavailable ({e}) — using Haar cascade")
            _mtcnn_ok = False
    return _mtcnn


def _detect_mtcnn(img_bgr):
    """Returns list of (x, y, w, h) bounding boxes with confidence >= 0.90."""
    mtcnn = _get_mtcnn()
    if mtcnn is None:
        return []
    try:
        from PIL import Image
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil     = Image.fromarray(img_rgb)
        boxes, probs = mtcnn.detect(pil)
        if boxes is None:
            return []
        out = []
        for box, prob in zip(boxes, probs):
            if prob is not None and prob >= 0.90:
                x1, y1, x2, y2 = [int(c) for c in box]
                w, h = x2 - x1, y2 - y1
                if w > 0 and h > 0:
                    out.append((x1, y1, w, h))
        return out
    except Exception:
        return []


# ── Haar cascade (fallback) ───────────────────────────────────────────────────
_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
_cascade = None

def _get_cascade():
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(_CASCADE_PATH)
    return _cascade


def _detect_haar(img_bgr):
    gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = _get_cascade().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )
    return list(faces) if len(faces) > 0 else []


# ── Unified detection ─────────────────────────────────────────────────────────

def _detect_all(img_bgr):
    """Returns list of (x,y,w,h) boxes — MTCNN first, Haar fallback."""
    faces = _detect_mtcnn(img_bgr)
    if not faces:
        faces = _detect_haar(img_bgr)
    return faces


def _crop_and_save(img_bgr, bbox, save_path, pad=0.25):
    """Crop face with padding, resize to 224×224, save as JPEG."""
    x, y, w, h = bbox
    H, W = img_bgr.shape[:2]
    px, py = int(w * pad), int(h * pad)
    x1 = max(0, x - px);  y1 = max(0, y - py)
    x2 = min(W, x + w + px); y2 = min(H, y + h + py)
    face = img_bgr[y1:y2, x1:x2]
    if face.size == 0:
        return None
    face = cv2.resize(face, (224, 224))
    cv2.imwrite(save_path, face, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return save_path


def detect_face(image_path, output_folder):
    """Detect largest face, crop, save. Returns saved path or None."""
    os.makedirs(output_folder, exist_ok=True)
    img = cv2.imread(image_path)
    if img is None:
        return None
    faces = _detect_all(img)
    if not faces:
        return None
    bbox = max(faces, key=lambda f: f[2] * f[3])
    out  = os.path.join(output_folder, os.path.basename(image_path))
    return _crop_and_save(img, bbox, out)


def detect_faces_batch(image_paths, output_folder):
    """Batch face detection. Returns list[path|None] same order as input."""
    os.makedirs(output_folder, exist_ok=True)
    results = []
    for p in image_paths:
        img = cv2.imread(p)
        if img is None:
            results.append(None)
            continue
        faces = _detect_all(img)
        if not faces:
            results.append(None)
            continue
        bbox  = max(faces, key=lambda f: f[2] * f[3])
        out   = os.path.join(output_folder, os.path.basename(p))
        saved = _crop_and_save(img, bbox, out)
        results.append(saved)
    return results
