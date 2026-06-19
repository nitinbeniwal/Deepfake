"""
Usage: python diagnose.py path/to/video.mp4 real|fake
"""
import sys, os, shutil, statistics
from frame_extractor import extract_frames
from face_detector   import detect_face
from classifier      import classify_face, reset_buffers

def diagnose_video(video_path, ground_truth):
    if ground_truth.lower() not in ("real","fake"):
        print("ground_truth must be real|fake"); return
    is_real = ground_truth.lower() == "real"
    F, FA = "diag_frames", "diag_faces"
    for d in (F, FA):
        if os.path.exists(d): shutil.rmtree(d)

    print(f"\nDIAGNOSE: {video_path}  (actually {ground_truth.upper()})\n{'='*60}")
    extract_frames(video_path, F)

    scores, face_paths = [], []
    for img in sorted(os.listdir(F)):
        saved = detect_face(os.path.join(F, img), FA)
        if saved:
            s = classify_face(saved)
            if s is not None:
                scores.append(s); face_paths.append((saved, s))

    if not scores:
        print("❌ No faces scored."); return

    med = statistics.median(scores)
    hi  = sum(1 for s in scores if s > 60)
    print(f"\nFrames: {len(scores)}  Median: {med:.1f}%  Hi>60%: {hi}")

    if is_real and med > 45:
        print(f"❌ FALSE POSITIVE — real video scored {med:.1f}%")
        print(f"   → Run Calibrate.py or set CALIBRATION_OFFSET={int(med)} in classifier.py")
    elif is_real:
        print(f"✅ Correctly real (median {med:.1f}%)")
    elif not is_real and med < 45:
        print(f"❌ FALSE NEGATIVE — fake scored {med:.1f}%")
        print("   → Deepfake may be high-quality; try lowering threshold or adding ensemble")
    else:
        print(f"✅ Correctly fake (median {med:.1f}%)")

    top5 = sorted(face_paths, key=lambda x: x[1], reverse=True)
    print("\nTop 5 fake frames:")
    for p, s in top5[:5]: print(f"  {os.path.basename(p):25s} {s:.1f}%")

    for d in (F, FA): shutil.rmtree(d)
    print("Cleaned up ✅")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python diagnose.py <video> <real|fake>"); sys.exit(1)
    if not os.path.exists(sys.argv[1]):
        print(f"Not found: {sys.argv[1]}"); sys.exit(1)
    diagnose_video(sys.argv[1], sys.argv[2])
