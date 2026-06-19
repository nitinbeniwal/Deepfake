"""
test_accuracy.py  —  Batch test your detector on multiple videos
================================================================
Tests your detector on a dataset and identifies patterns in errors.

Usage:
    python test_accuracy.py \
        --real-dir path/to/real_videos/ \
        --fake-dir path/to/fake_videos/ \
        --output results.csv
"""

import os
import csv
import statistics
import argparse
import shutil
from datetime import datetime

from frame_extractor import extract_frames
from face_detector import detect_face
from classifier import classify_face, reset_buffers

def test_single_video(video_path, output_folder="test_temp"):
    """
    Tests a single video and returns the median fake score.
    
    Returns:
        dict with: median_score, frame_count, verdict, details
    """
    
    # Create temp folders
    frames_folder = os.path.join(output_folder, "frames")
    faces_folder = os.path.join(output_folder, "faces")
    
    for folder in (frames_folder, faces_folder):
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder)
    
    try:
        # Extract frames
        reset_buffers()
        extract_frames(video_path, frames_folder)
        
        # Detect and classify faces
        scores = []
        for img in sorted(os.listdir(frames_folder)):
            img_path = os.path.join(frames_folder, img)
            saved = detect_face(img_path, faces_folder)
            if saved:
                score = classify_face(saved, verbose=False)
                if score is not None:
                    scores.append(score)
        
        if not scores:
            return {
                "median_score": None,
                "frame_count": 0,
                "error": "No faces detected"
            }
        
        median = statistics.median(scores)
        high_fake = sum(1 for s in scores if s > 60)
        high_pct = (high_fake / len(scores)) * 100
        
        # Determine verdict using aggregator_v2 logic
        if median >= 70 and high_pct >= 50:
            verdict = "FAKE"
        elif median >= 60 and high_pct >= 40:
            verdict = "LIKELY FAKE"
        elif median >= 45 or high_pct >= 35:
            verdict = "UNCERTAIN"
        elif median < 30 and (len(scores) - high_fake) / len(scores) >= 0.6:
            verdict = "REAL"
        else:
            verdict = "REAL"
        
        return {
            "median_score": round(median, 2),
            "mean_score": round(sum(scores) / len(scores), 2),
            "frame_count": len(scores),
            "high_fake_count": high_fake,
            "high_fake_pct": round(high_pct, 1),
            "verdict": verdict,
            "min_score": round(min(scores), 2),
            "max_score": round(max(scores), 2)
        }
    
    except Exception as e:
        return {
            "median_score": None,
            "frame_count": 0,
            "error": str(e)
        }
    
    finally:
        # Cleanup
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)


def test_directory(video_dir, ground_truth, output_csv=None):
    """
    Tests all videos in a directory.
    
    Args:
        video_dir: path to directory with videos
        ground_truth: "real" or "fake"
        output_csv: optional file to save results
    
    Returns:
        list of test results
    """
    
    videos = [f for f in os.listdir(video_dir) 
              if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]
    
    if not videos:
        print(f"No videos found in {video_dir}")
        return []
    
    print(f"\n{'='*70}")
    print(f"Testing {len(videos)} {ground_truth} videos...")
    print(f"{'='*70}\n")
    
    results = []
    correct = 0
    incorrect = 0
    
    for i, video in enumerate(videos, 1):
        video_path = os.path.join(video_dir, video)
        print(f"[{i:2d}/{len(videos)}] {video:50s}", end=" ", flush=True)
        
        result = test_single_video(video_path)
        result['filename'] = video
        result['ground_truth'] = ground_truth
        
        if result['median_score'] is None:
            print(f"⚠️  ERROR: {result.get('error', 'Unknown')}")
            result['correct'] = False
            incorrect += 1
        else:
            # Check if verdict matches ground truth
            verdict = result['verdict'].lower()
            is_correct = (
                ('real' in ground_truth.lower() and 'real' in verdict) or
                ('fake' in ground_truth.lower() and 'fake' in verdict)
            )
            
            result['correct'] = is_correct
            
            if is_correct:
                print(f"✅ {result['verdict']:15s} (score: {result['median_score']:.1f}%)")
                correct += 1
            else:
                print(f"❌ {result['verdict']:15s} (score: {result['median_score']:.1f}%)")
                incorrect += 1
        
        results.append(result)
    
    # Summary
    total = correct + incorrect
    accuracy = (correct / total * 100) if total > 0 else 0
    
    print(f"\n{'='*70}")
    print(f"RESULTS FOR {ground_truth.upper()} VIDEOS")
    print(f"{'='*70}")
    print(f"Total videos   : {len(videos)}")
    print(f"Correct        : {correct}")
    print(f"Incorrect      : {incorrect}")
    print(f"Accuracy       : {accuracy:.1f}%")
    
    # Analyze scores
    valid_scores = [r['median_score'] for r in results 
                    if r['median_score'] is not None]
    if valid_scores:
        print(f"\nScore statistics:")
        print(f"  Median : {statistics.median(valid_scores):.1f}%")
        print(f"  Mean   : {sum(valid_scores)/len(valid_scores):.1f}%")
        print(f"  Min    : {min(valid_scores):.1f}%")
        print(f"  Max    : {max(valid_scores):.1f}%")
    
    print(f"{'='*70}\n")
    
    # Save to CSV if requested
    if output_csv:
        write_header = not os.path.exists(output_csv) or os.path.getsize(output_csv) == 0
        with open(output_csv, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            if write_header:
                writer.writeheader()
            writer.writerows(results)
        
        print(f"Results saved to {output_csv}")
    
    return results


def analyze_errors(results):
    """
    Analyzes common patterns in errors.
    """
    
    real_videos = [r for r in results if r['ground_truth'] == 'real']
    fake_videos = [r for r in results if r['ground_truth'] == 'fake']
    
    real_errors = [r for r in real_videos if not r.get('correct', False)]
    fake_errors = [r for r in fake_videos if not r.get('correct', False)]
    
    print("\n" + "="*70)
    print("ERROR ANALYSIS")
    print("="*70)
    
    if real_errors:
        print(f"\n🔴 FALSE POSITIVES (Real videos marked as Fake):")
        print(f"   Count: {len(real_errors)}")
        print(f"   Median score of errors: {statistics.median([r['median_score'] for r in real_errors if r['median_score']]):.1f}%")
        print(f"   These videos are scoring too high as fake")
        print(f"\n   Recommendations:")
        print(f"   1. Run Calibrate.py on similar videos")
        print(f"   2. Lower FAKE threshold from 65% to ~50%")
        print(f"   3. Check if codec/quality differs from deployment videos")
    
    if fake_errors:
        print(f"\n🟢 FALSE NEGATIVES (Fake videos marked as Real):")
        print(f"   Count: {len(fake_errors)}")
        error_scores = [r['median_score'] for r in fake_errors if r['median_score']]
        if error_scores:
            print(f"   Median score of errors: {statistics.median(error_scores):.1f}%")
        print(f"   These deepfakes are too similar to real videos")
        print(f"\n   Recommendations:")
        print(f"   1. Deepfakes may be very high quality")
        print(f"   2. Lower FAKE threshold to 40-45%")
        print(f"   3. Or add AI-based classifier for hybrid detection")
    
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch test deepfake detector")
    parser.add_argument("--real-dir", required=True, help="Directory with real videos")
    parser.add_argument("--fake-dir", required=True, help="Directory with fake videos")
    parser.add_argument("--output", default="accuracy_results.csv", 
                       help="Output CSV file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.real_dir):
        print(f"Error: {args.real_dir} not found")
        exit(1)
    
    if not os.path.exists(args.fake_dir):
        print(f"Error: {args.fake_dir} not found")
        exit(1)
    
    # Start fresh CSV
    if os.path.exists(args.output):
        os.remove(args.output)
    open(args.output, 'a').close()  # Create empty file
    
    # Test real videos
    real_results = test_directory(args.real_dir, "real", args.output)
    
    # Test fake videos
    fake_results = test_directory(args.fake_dir, "fake", args.output)
    
    # Analysis
    all_results = real_results + fake_results
    analyze_errors(all_results)
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    correct = sum(1 for r in all_results if r.get('correct', False))
    total = len(all_results)
    print(f"Overall accuracy: {correct}/{total} = {correct/total*100:.1f}%")
    print(f"Results saved to: {args.output}")
    print("="*70 + "\n")