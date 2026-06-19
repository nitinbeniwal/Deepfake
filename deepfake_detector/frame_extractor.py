import cv2, os
from concurrent.futures import ThreadPoolExecutor

def extract_frames(video_path, output_folder, every_n_frames=None, max_frames=60):
    try:
        from classifier import reset_buffers; reset_buffers()
    except Exception:
        pass

    os.makedirs(output_folder, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = every_n_frames or max(1, int(fps))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video: {fps:.1f}fps  {total/fps:.1f}s  →  1 frame/s (max {max_frames})")

    pending, fi, si = [], 0, 0
    while si < max_frames:
        ok, frame = cap.read()
        if not ok: break
        if fi % step == 0:
            pending.append((os.path.join(output_folder, f"frame_{si:04d}.jpg"), frame.copy()))
            si += 1
        fi += 1
    cap.release()

    def _write(item):
        cv2.imwrite(item[0], item[1], [cv2.IMWRITE_JPEG_QUALITY, 85])

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(_write, pending))

    print(f"Extracted {si} frames ✅")
    return si
