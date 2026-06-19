"""
Usage: python Calibrate.py path/to/known_real_video.mp4
"""
import sys, os, statistics, shutil
from frame_extractor import extract_frames
from face_detector   import detect_face
from classifier      import classify_face

def calibrate(video_path):
    F, FA = "cal_frames", "cal_faces"
    for d in (F, FA):
        if os.path.exists(d): shutil.rmtree(d)

    print(f"\nCALIBRATION: {video_path}\n{'='*50}")
    extract_frames(video_path, F)

    scores = []
    for img in sorted(os.listdir(F)):
        saved = detect_face(os.path.join(F, img), FA)
        if saved:
            s = classify_face(saved)
            if s is not None:
                scores.append(s); print(f"  {os.path.basename(saved):30s} → {s:.2f}%")

    if not scores:
        print("⚠️  No faces scored.")
        return

    med = round(statistics.median(scores), 2)
    print(f"\n{'='*50}\nMedian: {med}%  Mean: {round(sum(scores)/len(scores),2)}%")

    if med < 30:
        print("✅ No calibration needed (CALIBRATION_OFFSET = 0)")
    else:
        print(f"⚠️  Set CALIBRATION_OFFSET = {int(med)} in classifier.py")
        print(f"   Then use FAKE threshold >= {min(95, int(med)+40)}")

    for d in (F, FA): shutil.rmtree(d)
    print("Cleaned up ✅")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python Calibrate.py <video>"); sys.exit(1)
    calibrate(sys.argv[1])
