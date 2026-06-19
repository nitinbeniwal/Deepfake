import pandas as pd, os
from datetime import datetime
from text_detector import detect_ai_text

def process_content(url, texts, output_folder="results"):
    os.makedirs(output_folder, exist_ok=True)
    print(f"\nProcessing {len(texts)} blocks from {url}")
    results = []
    for i, text in enumerate(texts):
        print(f"  [{i+1}/{len(texts)}]", end=" ")
        label, conf = detect_ai_text(text)
        results.append({"url": url, "text_preview": text[:100]+"...",
                         "verdict": label, "confidence": conf,
                         "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    path = os.path.join(output_folder, "scan_results.csv")
    df = pd.DataFrame(results)
    df.to_csv(path, mode="a", header=not os.path.exists(path), index=False)
    print(f"Saved → {path} ✅")
    return results
