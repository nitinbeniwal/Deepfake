import os
import threading
import time
from datetime import datetime

from crawler import crawl_page
from processor import process_content
from dashboard import app
from takedown import generate_legal_report

# ── Settings ──────────────────────────────
URLS_TO_MONITOR = [
    "https://www.bbc.com/news",
    "https://www.reuters.com",
    "https://www.ndtv.com",
]

SCAN_INTERVAL = 3600  # Every 1 hour
# ──────────────────────────────────────────

def run_scanner():
    print("🔍 Scanner started in background...")

    while True:
        print(f"\n{'='*50}")
        print(f"🔍 Scan started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")

        for url in URLS_TO_MONITOR:
            try:
                texts, videos = crawl_page(url)
                if texts:
                    process_content(url, texts[:5])
            except Exception as e:
                print(f"Error scanning {url}: {e}")

        print(f"\n✅ Scan complete! Next scan in {SCAN_INTERVAL//60} minutes...")
        time.sleep(SCAN_INTERVAL)

def run_dashboard():
    print("🌐 Dashboard starting...")
    print("Open browser and go to: http://127.0.0.1:5000")
    app.run(debug=False, use_reloader=False)

if __name__ == "__main__":

    print("="*50)
    print("🚀 DEEPFAKE DETECTION SYSTEM STARTING...")
    print("="*50)

    # Run scanner in background thread
    scanner_thread = threading.Thread(target=run_scanner)
    scanner_thread.daemon = True
    scanner_thread.start()

    # Small delay before dashboard starts
    time.sleep(2)

    # Run dashboard in main thread
    run_dashboard()