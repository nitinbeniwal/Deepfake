from flask import Flask, render_template_string, request, redirect, url_for
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

RESULTS_FILE = "results/scan_results.csv"
APPROVED_FILE = "results/approved_removals.csv"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Deepfake Detection Dashboard</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #f0f0f0; }
        h1 { color: #cc0000; }
        .card { background: white; padding: 20px; margin: 10px 0;
                border-radius: 8px; border-left: 5px solid #cc0000; }
        .score-high { color: red; font-weight: bold; }
        .score-low { color: green; font-weight: bold; }
        .btn-approve { background: #cc0000; color: white;
                       padding: 8px 16px; border: none;
                       border-radius: 4px; cursor: pointer; }
        .btn-reject { background: #666; color: white;
                      padding: 8px 16px; border: none;
                      border-radius: 4px; cursor: pointer; }
        .stats { background: #cc0000; color: white;
                 padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <h1>🚨 Deepfake Detection Dashboard</h1>

    <div class="stats">
        <b>Total Flagged Items: {{ total }}</b> &nbsp;|&nbsp;
        <b>Approved Removals: {{ approved }}</b>
    </div>

    {% for item in items %}
    <div class="card">
        <p><b>URL:</b> {{ item.url }}</p>
        <p><b>Text Preview:</b> {{ item.text_preview }}</p>
        <p><b>Verdict:</b> {{ item.verdict }}</p>
        <p><b>Confidence:</b>
            <span class="{{ 'score-high' if item.confidence > 70 else 'score-low' }}">
                {{ item.confidence }}%
            </span>
        </p>
        <p><b>Scanned at:</b> {{ item.scanned_at }}</p>

        <form method="POST" action="/review">
            <input type="hidden" name="url" value="{{ item.url }}">
            <input type="hidden" name="verdict" value="{{ item.verdict }}">
            <input type="hidden" name="confidence" value="{{ item.confidence }}">
            <button class="btn-approve" name="action" value="approve">
                ✅ Approve Removal
            </button>
            &nbsp;
            <button class="btn-reject" name="action" value="reject">
                ❌ Reject
            </button>
        </form>
    </div>
    {% endfor %}

    {% if not items %}
    <div class="card">
        <p>✅ No flagged items found. System is clean!</p>
    </div>
    {% endif %}

</body>
</html>
"""

@app.route("/")
def index():
    items = []
    total = 0
    approved = 0

    if os.path.exists(RESULTS_FILE):
        df = pd.read_csv(RESULTS_FILE)
        # Show only fake items
        flagged = df[df['verdict'] == 'Fake']
        items = flagged.to_dict('records')
        total = len(items)

    if os.path.exists(APPROVED_FILE):
        approved_df = pd.read_csv(APPROVED_FILE)
        approved = len(approved_df)

    return render_template_string(HTML_TEMPLATE,
                                  items=items,
                                  total=total,
                                  approved=approved)

@app.route("/review", methods=["POST"])
def review():
    action = request.form.get("action")
    url = request.form.get("url")
    verdict = request.form.get("verdict")
    confidence = request.form.get("confidence")

    if action == "approve":
        os.makedirs("results", exist_ok=True)
        df = pd.DataFrame([{
            "url": url,
            "verdict": verdict,
            "confidence": confidence,
            "action": "APPROVED FOR REMOVAL",
            "reviewed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])

        if os.path.exists(APPROVED_FILE):
            df.to_csv(APPROVED_FILE, mode='a', header=False, index=False)
        else:
            df.to_csv(APPROVED_FILE, index=False)

        print(f"✅ Approved removal for: {url}")

    return redirect(url_for("index"))

if __name__ == "__main__":
    print("🚀 Starting Dashboard...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True)