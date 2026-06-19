"""
face_detector.py — Face detection using OpenCV (no extra dependencies).
Uses Haar cascade (bundled with opencv-python) with a DNN fallback when
the OpenCV DNN face model is available.
"""
import cv2, os, numpy as np

# Haar cascade — always available inside opencv-python package
_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml"
_cascade = None

def _get_cascade():
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(_CASCADE_PATH)
    return _cascade


def _detect_bbox(img_bgr):
    """Return (x,y,w,h) of largest face, or None."""
    gray  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    faces = _get_cascade().detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
    )
    if len(faces) == 0:
        return None
    # Largest face by area
    return max(faces, key=lambda f: f[2] * f[3])


def _crop_and_save(img_bgr, bbox, save_path, pad=0.25):
    """Crop face with padding and save as JPEG."""
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
    """Detect largest face, crop, save. Returns save path or None."""
    os.makedirs(output_folder, exist_ok=True)
    img = cv2.imread(image_path)
    if img is None:
        return None
    bbox = _detect_bbox(img)
    if bbox is None:
        print(f"  No face: {os.path.basename(image_path)}")
        return None
    out = os.path.join(output_folder, os.path.basename(image_path))
    result = _crop_and_save(img, bbox, out)
    if result:
        print(f"  Face ✅ {os.path.basename(image_path)}")
    return result


def detect_faces_batch(image_paths, output_folder):
    """Batch face detection. Returns list[path|None] same order as input."""
    os.makedirs(output_folder, exist_ok=True)
    results = []
    for p in image_paths:
        img = cv2.imread(p)
        if img is None:
            results.append(None); continue
        bbox = _detect_bbox(img)
        if bbox is None:
            print(f"  No face: {os.path.basename(p)}")
            results.append(None); continue
        out  = os.path.join(output_folder, os.path.basename(p))
        saved = _crop_and_save(img, bbox, out)
        if saved:
            print(f"  Face ✅ {os.path.basename(p)}")
        results.append(saved)
    return results
