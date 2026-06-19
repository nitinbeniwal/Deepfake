import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import shutil
import statistics
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime

# Import our modules
from frame_extractor import extract_frames
from face_detector import detect_face
from classifier import classify_face
from aggregator import aggregate_results
from audio_classifier import classify_audio
from text_detector import detect_ai_text
from crawler import crawl_page
from processor import process_content
from takedown import generate_legal_report

# ── Colours ───────────────────────────────
BG    = "#1a1a2e"
CARD  = "#16213e"
RED   = "#e94560"
WHITE = "#ffffff"
GRAY  = "#a0a0a0"
GREEN = "#00b894"
# ──────────────────────────────────────────


class DeepfakeDetectorApp:

    def __init__(self, root):
        self.root = root
        self.root.title("🚨 Government Deepfake Detection System")
        self.root.geometry("1100x700")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        self.build_header()
        self.build_tabs()

    # ── Header ────────────────────────────
    def build_header(self):
        header = tk.Frame(self.root, bg=RED, pady=12)
        header.pack(fill="x")

        tk.Label(header,
                 text="🚨  GOVERNMENT DEEPFAKE DETECTION SYSTEM",
                 font=("Arial", 18, "bold"),
                 bg=RED, fg=WHITE).pack()

        tk.Label(header,
                 text="Powered by AI  |  For Official Use Only",
                 font=("Arial", 9),
                 bg=RED, fg=WHITE).pack()

    # ── Tabs ──────────────────────────────
    def build_tabs(self):
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TNotebook",
                        background=BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=CARD, foreground=WHITE,
                        padding=[15, 8], font=("Arial", 10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", RED)],
                  foreground=[("selected", WHITE)])

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_video   = tk.Frame(self.tabs, bg=BG)
        self.tab_audio   = tk.Frame(self.tabs, bg=BG)
        self.tab_text    = tk.Frame(self.tabs, bg=BG)
        self.tab_web     = tk.Frame(self.tabs, bg=BG)
        self.tab_reports = tk.Frame(self.tabs, bg=BG)
        self.tab_charts  = tk.Frame(self.tabs, bg=BG)

        self.tabs.add(self.tab_video,   text="📹  Video")
        self.tabs.add(self.tab_audio,   text="🎵  Audio")
        self.tabs.add(self.tab_text,    text="📝  Text")
        self.tabs.add(self.tab_web,     text="🌐  Website")
        self.tabs.add(self.tab_reports, text="📋  Reports")
        self.tabs.add(self.tab_charts,  text="📊  Charts")

        self.build_video_tab()
        self.build_audio_tab()
        self.build_text_tab()
        self.build_web_tab()
        self.build_reports_tab()
        self.build_charts_tab()

    # ── Helper: Card Frame ────────────────
    def make_card(self, parent, title):
        frame = tk.LabelFrame(parent, text=f"  {title}  ",
                              bg=CARD, fg=WHITE,
                              font=("Arial", 11, "bold"),
                              bd=1, relief="groove")
        frame.pack(fill="both", expand=True, padx=15, pady=10)
        return frame

    # ── Helper: Log Box ───────────────────
    def make_log(self, parent):
        log = scrolledtext.ScrolledText(parent, height=10,
                                        bg="#0f0f1a", fg=GREEN,
                                        font=("Courier", 10),
                                        insertbackground=WHITE)
        log.pack(fill="both", expand=True, padx=10, pady=5)
        return log

    def log(self, box, text):
        # Thread-safe: schedule on the Tkinter main loop
        self.root.after(0, self._log_safe, box, text)

    def _log_safe(self, box, text):
        box.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")
        box.see("end")

    # ── Helper: Result Label ──────────────
    def make_result(self, parent):
        lbl = tk.Label(parent, text="Awaiting scan...",
                       font=("Arial", 14, "bold"),
                       bg=CARD, fg=GRAY)
        lbl.pack(pady=8)
        return lbl

    # ── FIX 1: set_result is now INSIDE the class ─────────────────────────────
    # ── FIX 2: thresholds raised to match aggregator.py (85 / 65) ─────────────
    def set_result_safe(self, lbl, score):
        """Thread-safe wrapper around set_result."""
        self.root.after(0, self.set_result, lbl, score)

    def set_result(self, lbl, score):
        # Thresholds tuned for the Deep-Fake-Detector-v2 model, whose real
        # videos score ~10-15% and fakes score ~55%+. FAKE line sits at 45%,
        # in the gap between the two, so reals stay safe and fakes get flagged.
        if score >= 45:
            lbl.config(
                text=f"🚨  FAKE DETECTED  ({score}% fake score)", fg=RED)
        elif score >= 30:
            lbl.config(
                text=f"⚠️  UNCERTAIN  ({score}% — manual review)", fg="orange")
        else:
            lbl.config(
                text=f"✅  LOOKS REAL  ({score}% fake score)", fg=GREEN)

    # ══════════════════════════════════════
    # VIDEO TAB
    # ══════════════════════════════════════
    def build_video_tab(self):
        card = self.make_card(self.tab_video, "📹 Video Deepfake Scanner")

        tk.Label(card,
                 text="Select a video file to scan for face-swap deepfakes.",
                 bg=CARD, fg=GRAY, font=("Arial", 10)).pack(pady=5)

        self.video_path_var = tk.StringVar(value="No file selected")
        tk.Label(card, textvariable=self.video_path_var,
                 bg=CARD, fg=WHITE, font=("Arial", 9),
                 wraplength=700).pack()

        btn_frame = tk.Frame(card, bg=CARD)
        btn_frame.pack(pady=8)

        tk.Button(btn_frame, text="📂  Browse Video",
                  bg=CARD, fg=WHITE, font=("Arial", 10),
                  relief="groove", cursor="hand2",
                  command=self.browse_video).pack(side="left", padx=5)

        tk.Button(btn_frame, text="🔍  Scan Now",
                  bg=RED, fg=WHITE, font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2",
                  command=self.scan_video).pack(side="left", padx=5)

        tk.Button(btn_frame, text="🧪  Full Pipeline",
                  bg="#0070c0", fg=WHITE, font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2",
                  command=self.scan_video_pipeline).pack(side="left", padx=5)

        self.video_result = self.make_result(card)
        self.video_log    = self.make_log(card)

    def browse_video(self):
        path = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")])
        if path:
            self.video_path_var.set(path)

    def scan_video(self):
        path = self.video_path_var.get()
        if path == "No file selected":
            messagebox.showwarning("No File", "Please select a video file first!")
            return
        threading.Thread(target=self._scan_video_thread,
                         args=(path,), daemon=True).start()

    def _scan_video_thread(self, path):
        self.log(self.video_log, "Starting video scan...")
        self.video_result.config(text="Scanning...", fg=WHITE)
        try:
            # Step 0 — CLEAR leftover frames/faces from any previous scan.
            # Without this, a shorter video reuses the previous video's
            # leftover frames, contaminating the result. We delete the FILES
            # inside (not the folders) to avoid Windows "Access is denied"
            # errors when a folder handle is briefly locked.
            for folder in ("extracted_frames", "detected_faces"):
                os.makedirs(folder, exist_ok=True)
                for fn in os.listdir(folder):
                    fp = os.path.join(folder, fn)
                    try:
                        if os.path.isfile(fp):
                            os.remove(fp)
                    except OSError:
                        pass  # skip any file that's momentarily locked

            # Step 1 — extract frames (auto FPS, 1 frame / 2 sec)
            self.log(self.video_log, "Extracting frames...")
            extract_frames(path, "extracted_frames")   # every_n_frames=None → auto

            # Step 2 — detect & crop faces
            self.log(self.video_log, "Detecting faces...")
            face_paths = []
            for img in sorted(os.listdir("extracted_frames")):
                saved = detect_face(
                    os.path.join("extracted_frames", img), "detected_faces")
                if saved:                   # only keep frames where a face was found
                    face_paths.append(saved)

            if not face_paths:
                self.log(self.video_log, "⚠️  No faces found in any frame.")
                self.video_result.config(text="No faces detected", fg=GRAY)
                return

            # Step 3 — classify each face
            self.log(self.video_log,
                     f"Classifying {len(face_paths)} face frames...")
            scores = []
            for fp in face_paths:
                score = classify_face(fp)   # returns None if unparseable
                if score is not None:
                    scores.append(score)
                    self.log(self.video_log,
                             f"  {os.path.basename(fp)} → {score}% fake")

            # Step 4 — aggregate
            # Median alone misses fakes that only show in SOME frames (the deepfake
            # face appears in part of the clip). So we also measure how many frames
            # score high, and combine the two signals.
            if scores:
                median_score = round(statistics.median(scores), 2)
                mean_score   = round(sum(scores) / len(scores), 2)

                # Share of frames that look fake (>= 50%).
                high_count = sum(1 for s in scores if s >= 50)
                high_pct   = round(100 * high_count / len(scores), 1)

                # A "suspicion" score driven by the proportion of high frames.
                # If ~30%+ of frames are high, this rises toward FAKE territory.
                suspicion = round(min(100.0, high_pct * 2.5), 2)

                # Final score = whichever signal is stronger. A clean real video
                # has low median AND few high frames, so it stays low. A partial
                # fake has many high frames, so suspicion lifts it.
                final_score = max(median_score, suspicion)

                self.log(self.video_log,
                         f"Median: {median_score}%  |  Mean: {mean_score}%  |  "
                         f"High frames (>=50%): {high_count}/{len(scores)} "
                         f"({high_pct}%)  |  Final: {final_score}%")
                self.set_result_safe(self.video_result, final_score)
                self.save_result("Video", path, final_score)
                self.log(self.video_log, "✅ Scan complete!")
            else:
                self.log(self.video_log,
                         "⚠️  No scoreable frames — try a clearer video.")
                self.root.after(
                    0, self.video_result.config,
                    {"text": "Could not score any frames", "fg": GRAY})

        except Exception as e:
            self.log(self.video_log, f"❌ Error: {e}")
            self.root.after(
                0, self.video_result.config,
                {"text": "Error during scan", "fg": RED})

    def scan_video_pipeline(self):
        path = self.video_path_var.get()
        if path == "No file selected":
            messagebox.showwarning("No File", "Please select a video file first!")
            return
        threading.Thread(target=self._pipeline_thread,
                         args=(path,), daemon=True).start()

    def _pipeline_thread(self, path):
        self.log(self.video_log, "🧪 Full pipeline scan starting...")
        self.root.after(0, self.video_result.config,
                        {"text": "Pipeline running...", "fg": WHITE})
        try:
            from pipeline import analyze_video
            result = analyze_video(path, cleanup=True)

            score   = result.get("final_score")
            verdict = result.get("verdict", "UNKNOWN")
            comps   = result.get("component_scores", {})

            fp = result.get("fast_path", False)
            if fp:
                self.log(self.video_log,
                         f"FAST-PATH (metadata): {comps.get('metadata','?')}%")
            else:
                self.log(self.video_log,
                         f"Visual: {comps.get('visual','?')}%  "
                         f"Audio: {comps.get('audio','?')}%  "
                         f"Lip-sync: {comps.get('lipsync','?')}%  "
                         f"Temporal: {comps.get('temporal','?')}%  "
                         f"SPN: {comps.get('spn','?')}%  "
                         f"Forensic: {comps.get('forensic','?')}%  "
                         f"Metadata: {comps.get('metadata','?')}%")

            for anomaly in result.get("anomalies", []):
                self.log(self.video_log, f"  ⚠️  {anomaly}")

            self.log(self.video_log,
                     f"Pipeline final: {score}% → {verdict}")

            if score is not None:
                self.set_result_safe(self.video_result, score)
                self.save_result("Video-Pipeline", path, score)
            self.log(self.video_log, "✅ Pipeline complete!")
        except Exception as e:
            self.log(self.video_log, f"❌ Pipeline error: {e}")
            self.root.after(
                0, self.video_result.config,
                {"text": "Pipeline error", "fg": RED})

    # ══════════════════════════════════════
    # AUDIO TAB
    # ══════════════════════════════════════
    def build_audio_tab(self):
        card = self.make_card(self.tab_audio, "🎵 Audio Deepfake Scanner")

        tk.Label(card,
                 text="Select a video or audio file to scan for AI generated voice.",
                 bg=CARD, fg=GRAY, font=("Arial", 10)).pack(pady=5)

        self.audio_path_var = tk.StringVar(value="No file selected")
        tk.Label(card, textvariable=self.audio_path_var,
                 bg=CARD, fg=WHITE, font=("Arial", 9),
                 wraplength=700).pack()

        btn_frame = tk.Frame(card, bg=CARD)
        btn_frame.pack(pady=8)

        tk.Button(btn_frame, text="📂  Browse File",
                  bg=CARD, fg=WHITE, font=("Arial", 10),
                  relief="groove", cursor="hand2",
                  command=self.browse_audio).pack(side="left", padx=5)

        tk.Button(btn_frame, text="🔍  Scan Now",
                  bg=RED, fg=WHITE, font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2",
                  command=self.scan_audio).pack(side="left", padx=5)

        self.audio_result = self.make_result(card)
        self.audio_log    = self.make_log(card)

    def browse_audio(self):
        path = filedialog.askopenfilename(
            filetypes=[("Media files", "*.mp4 *.avi *.mov *.mp3 *.wav")])
        if path:
            self.audio_path_var.set(path)

    def scan_audio(self):
        path = self.audio_path_var.get()
        if path == "No file selected":
            messagebox.showwarning("No File", "Please select a file first!")
            return
        threading.Thread(target=self._scan_audio_thread,
                         args=(path,), daemon=True).start()

    def _scan_audio_thread(self, path):
        self.log(self.audio_log, "Starting audio scan...")
        self.audio_result.config(text="Scanning...", fg=WHITE)
        try:
            # The new classify_audio handles BOTH audio files and video files
            # (it extracts the audio track itself), and uses a real audio
            # deepfake model — no spectrogram/face-model hack.
            self.log(self.audio_log, "Analyzing audio with deepfake model...")
            score = classify_audio(path)

            self.set_result_safe(self.audio_result, score)
            self.log(self.audio_log, f"✅ Done! Score: {score}% fake")
            self.save_result("Audio", path, score)

        except Exception as e:
            self.log(self.audio_log, f"❌ Error: {e}")

    # ══════════════════════════════════════
    # TEXT TAB
    # ══════════════════════════════════════
    def build_text_tab(self):
        card = self.make_card(self.tab_text, "📝 Text Deepfake Scanner")

        tk.Label(card,
                 text="Paste any text below to check if it was AI generated.",
                 bg=CARD, fg=GRAY, font=("Arial", 10)).pack(pady=5)

        self.text_input = scrolledtext.ScrolledText(
            card, height=8, bg="#0f0f1a", fg=WHITE,
            font=("Arial", 11), insertbackground=WHITE)
        self.text_input.pack(fill="x", padx=10, pady=5)

        tk.Button(card, text="🔍  Analyse Text",
                  bg=RED, fg=WHITE, font=("Arial", 11, "bold"),
                  relief="flat", cursor="hand2",
                  command=self.scan_text).pack(pady=8)

        self.text_result = self.make_result(card)
        self.text_log    = self.make_log(card)

    def scan_text(self):
        text = self.text_input.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("No Text", "Please paste some text first!")
            return
        threading.Thread(target=self._scan_text_thread,
                         args=(text,), daemon=True).start()

    def _scan_text_thread(self, text):
        self.log(self.text_log, "Analysing text...")
        self.text_result.config(text="Analysing...", fg=WHITE)
        try:
            label, confidence = detect_ai_text(text)
            score = confidence if label == "Fake" else (100 - confidence)
            self.set_result_safe(self.text_result, score)
            self.log(self.text_log,
                     f"✅ Done! Verdict: {label} ({confidence}%)")
            self.save_result("Text", "Manual Input", score)
        except Exception as e:
            self.log(self.text_log, f"❌ Error: {e}")

    # ══════════════════════════════════════
    # WEBSITE TAB
    # ══════════════════════════════════════
    def build_web_tab(self):
        card = self.make_card(self.tab_web, "🌐 Website Scanner")

        tk.Label(card,
                 text="Enter a website URL to scan for deepfake content.",
                 bg=CARD, fg=GRAY, font=("Arial", 10)).pack(pady=5)

        url_frame = tk.Frame(card, bg=CARD)
        url_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(url_frame, text="URL:", bg=CARD, fg=WHITE,
                 font=("Arial", 10)).pack(side="left")

        self.url_var = tk.StringVar(value="https://")
        tk.Entry(url_frame, textvariable=self.url_var,
                 bg="#0f0f1a", fg=WHITE, font=("Arial", 11),
                 insertbackground=WHITE, width=60).pack(side="left", padx=10)

        tk.Button(card, text="🔍  Scan Website",
                  bg=RED, fg=WHITE, font=("Arial", 11, "bold"),
                  relief="flat", cursor="hand2",
                  command=self.scan_web).pack(pady=8)

        self.web_log = self.make_log(card)

    def scan_web(self):
        url = self.url_var.get().strip()
        if not url or url == "https://":
            messagebox.showwarning("No URL", "Please enter a website URL!")
            return
        threading.Thread(target=self._scan_web_thread,
                         args=(url,), daemon=True).start()

    def _scan_web_thread(self, url):
        self.log(self.web_log, f"Crawling: {url}")
        try:
            texts, videos = crawl_page(url)
            self.log(self.web_log,
                     f"Found {len(texts)} text blocks, {len(videos)} videos")

            if texts:
                results = process_content(url, texts[:5])
                for r in results:
                    self.log(self.web_log,
                             f"{r['verdict']} ({r['confidence']}%) → "
                             f"{r['text_preview'][:60]}...")

            self.log(self.web_log, "✅ Website scan complete!")

        except Exception as e:
            self.log(self.web_log, f"❌ Error: {e}")

    # ══════════════════════════════════════
    # REPORTS TAB
    # ══════════════════════════════════════
    def build_reports_tab(self):
        card = self.make_card(self.tab_reports, "📋 Scan Reports")

        btn_frame = tk.Frame(card, bg=CARD)
        btn_frame.pack(pady=8)

        tk.Button(btn_frame, text="🔄  Refresh",
                  bg=CARD, fg=WHITE, font=("Arial", 10),
                  relief="groove", cursor="hand2",
                  command=self.load_reports).pack(side="left", padx=5)

        tk.Button(btn_frame, text="📄  Generate PDF Report",
                  bg=RED, fg=WHITE, font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2",
                  command=self.generate_report).pack(side="left", padx=5)

        cols = ("Type", "Source", "Score", "Verdict", "Time")
        self.tree = ttk.Treeview(card, columns=cols,
                                  show="headings", height=15)

        style = ttk.Style()
        style.configure("Treeview",
                         background=CARD, foreground=WHITE,
                         fieldbackground=CARD, rowheight=28)
        style.configure("Treeview.Heading",
                         background=RED, foreground=WHITE,
                         font=("Arial", 10, "bold"))

        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=160)

        self.tree.pack(fill="both", expand=True, padx=10, pady=5)
        self.load_reports()

    def load_reports(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        path = "results/scan_results.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                self.tree.insert("", "end", values=(
                    row.get("type", "Text"),
                    str(row.get("url", ""))[:40],
                    f"{row.get('confidence', 0)}%",
                    row.get("verdict", ""),
                    row.get("scanned_at", "")
                ))

    def generate_report(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection",
                                   "Please select a row from the table first!")
            return
        values = self.tree.item(selected[0])['values']
        url    = values[1]
        score  = float(str(values[2]).replace("%", ""))
        path   = generate_legal_report(url, score)
        messagebox.showinfo("Report Generated", f"PDF saved to:\n{path}")

    # ══════════════════════════════════════
    # CHARTS TAB
    # ══════════════════════════════════════
    def build_charts_tab(self):
        card = self.make_card(self.tab_charts, "📊 Detection Statistics")

        tk.Button(card, text="🔄  Refresh Charts",
                  bg=RED, fg=WHITE, font=("Arial", 10, "bold"),
                  relief="flat", cursor="hand2",
                  command=self.load_charts).pack(pady=8)

        self.chart_frame = tk.Frame(card, bg=CARD)
        self.chart_frame.pack(fill="both", expand=True)
        self.load_charts()

    def load_charts(self):
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        path = "results/scan_results.csv"
        if not os.path.exists(path):
            tk.Label(self.chart_frame,
                     text="No scan data yet.\nRun some scans first!",
                     bg=CARD, fg=GRAY,
                     font=("Arial", 13)).pack(expand=True)
            return

        df = pd.read_csv(path)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4))
        fig.patch.set_facecolor(CARD)

        # Pie chart
        counts = df['verdict'].value_counts()
        colors = [RED if v == 'Fake' else GREEN for v in counts.index]
        ax1.pie(counts, labels=counts.index, colors=colors,
                autopct='%1.1f%%', textprops={'color': WHITE})
        ax1.set_title("Real vs Fake", color=WHITE, fontsize=13)
        ax1.set_facecolor(CARD)

        # Bar chart
        if 'confidence' in df.columns:
            numeric_conf = pd.to_numeric(
                df['confidence'], errors='coerce').dropna()
            if len(numeric_conf) > 0:
                numeric_conf.plot(kind='bar', ax=ax2,
                                  color=RED, edgecolor=CARD)
                ax2.set_title("Confidence per Scan", color=WHITE, fontsize=13)
                ax2.set_facecolor(CARD)
                ax2.tick_params(colors=WHITE)
            else:
                ax2.text(0.5, 0.5, 'No data yet',
                         color=WHITE, ha='center', va='center',
                         transform=ax2.transAxes, fontsize=13)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ── Save result to CSV ────────────────
    # FIX 4: verdict threshold raised to match aggregator.py (85)
    def save_result(self, scan_type, source, score):
        os.makedirs("results", exist_ok=True)
        # Match the verdict thresholds used in set_result (45 / 30).
        verdict = "Fake" if score >= 45 else ("Uncertain" if score >= 30 else "Real")
        df = pd.DataFrame([{
            "type":       scan_type,
            "url":        source,
            "confidence": score,
            "verdict":    verdict,
            "scanned_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        path = "results/scan_results.csv"
        if os.path.exists(path):
            df.to_csv(path, mode='a', header=False, index=False)
        else:
            df.to_csv(path, index=False)


# ── Run the app ───────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app  = DeepfakeDetectorApp(root)
    root.mainloop()