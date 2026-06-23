"""Generate report.pdf -- Cyber Cell Deepfake Detection System submission report."""

from fpdf import FPDF
from datetime import date

TODAY = date.today().strftime("%d %B %Y")

class PDF(FPDF):
    def header(self):
        self.set_fill_color(15, 27, 45)       # navy
        self.rect(0, 0, 210, 16, 'F')
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(201, 209, 217)
        self.set_xy(10, 4)
        self.cell(0, 8, "CYBER CELL  |  FORENSICS DIVISION  |  DEEPFAKE DETECTION UNIT", ln=0, align="L")
        self.set_xy(0, 4)
        self.cell(200, 8, f"CONFIDENTIAL   {TODAY}", ln=0, align="R")
        self.set_text_color(0, 0, 0)
        self.ln(10)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, f"Page {self.page_no()} | Cyber Cell Deepfake Detection -- Confidential", align="C")

    def section(self, title, number=""):
        self.ln(4)
        self.set_fill_color(240, 242, 245)
        self.set_draw_color(225, 228, 232)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(13, 17, 23)
        tag = f"{number}  " if number else ""
        self.cell(0, 9, f"  {tag}{title}", ln=True, fill=True, border="B")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def subsection(self, title):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(9, 105, 218)
        self.cell(0, 7, f"  {title}", ln=True)
        self.set_text_color(30, 30, 30)
        self.ln(1)

    def body(self, text, indent=8):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(45, 50, 60)
        self.set_left_margin(indent)
        self.set_right_margin(15)
        self.multi_cell(0, 5.5, text)
        self.set_left_margin(10)
        self.set_right_margin(10)
        self.ln(1)

    def bullet(self, text, indent=12, symbol="-"):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(45, 50, 60)
        x0 = self.get_x()
        self.set_x(indent)
        self.multi_cell(0, 5.5, f"{symbol}  {text}", border=0)
        self.set_x(x0)
        self.ln(0.5)

    def kv(self, key, value, indent=14):
        self.set_font("Helvetica", "B", 9.5)
        self.set_text_color(80, 90, 100)
        self.set_x(indent)
        self.cell(52, 6, key + ":", ln=0)
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(20, 20, 30)
        self.multi_cell(0, 6, value)

    def tag(self, label, r, g, b):
        """Inline colored tag."""
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.cell(len(label)*2 + 8, 5.5, f"  {label}  ", fill=True, border=0)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(255, 255, 255)

    def divider(self):
        self.set_draw_color(220, 224, 230)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def target_row(self, label, current, target, status):
        self.set_font("Helvetica", "B", 9.5)
        self.set_x(14)
        self.set_text_color(40, 40, 60)
        self.cell(60, 7, label, ln=0)
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(100, 100, 120)
        self.cell(40, 7, current, ln=0)
        self.set_font("Helvetica", "B", 9.5)
        if "75" in target or "20" in target:
            self.set_text_color(9, 105, 218)
        self.cell(40, 7, target, ln=0)
        clr = (26, 127, 55) if status == "TARGET" else (207, 34, 46)
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*clr)
        self.set_text_color(255, 255, 255)
        self.cell(30, 5.5, f"  {status}  ", fill=True, ln=True)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(255, 255, 255)


pdf = PDF()
pdf.set_margins(10, 10, 10)
pdf.set_auto_page_break(auto=True, margin=18)
pdf.add_page()

# ??? COVER BLOCK ???????????????????????????????????????????????????????????????
pdf.set_fill_color(15, 27, 45)
pdf.rect(0, 16, 210, 54, 'F')

pdf.set_xy(10, 22)
pdf.set_font("Helvetica", "B", 22)
pdf.set_text_color(255, 255, 255)
pdf.cell(0, 12, "DEEPFAKE DETECTION SYSTEM", ln=True)

pdf.set_x(10)
pdf.set_font("Helvetica", "", 13)
pdf.set_text_color(180, 200, 230)
pdf.cell(0, 8, "Technical Report & Accuracy Improvement Roadmap", ln=True)

pdf.set_x(10)
pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(140, 160, 190)
pdf.cell(0, 6, f"Cyber Cell -- Forensics Division     |     Prepared: {TODAY}", ln=True)

pdf.ln(20)
pdf.set_text_color(0, 0, 0)

# ??? 1. EXECUTIVE SUMMARY ?????????????????????????????????????????????????????
pdf.section("EXECUTIVE SUMMARY", "1.")
pdf.body(
    "The Cyber Cell Forensics Division has developed an AI-powered deepfake detection system capable of "
    "analysing video evidence for signs of synthetic manipulation across multiple signals: visual face "
    "authenticity, audio voice cloning, temporal consistency, forensic artifacts, and metadata anomalies. "
    "This report outlines the current system status, accuracy targets, fine-tuning requirements, data "
    "collection needs, and the technical roadmap to achieve deployment-grade accuracy."
)

# ??? 2. SYSTEM OVERVIEW ???????????????????????????????????????????????????????
pdf.section("SYSTEM OVERVIEW", "2.")
pdf.body("The system runs locally on Cyber Cell hardware. It provides a web-based dashboard for case management, "
         "evidence upload, forensic scanning, and chain-of-custody reporting.")

pdf.subsection("Detection Pipeline (7 Signals)")
signals = [
    ("Visual AI (weight 58%)", "5 deep learning models (Xception, EfficientNet-B4, ViT, CLIP) analyse face regions frame-by-frame for synthesis artifacts."),
    ("Audio (17%)", "Transformer-based classifier detects voice cloning and synthesis in the audio track."),
    ("Temporal (12%)", "Frame-to-frame consistency analysis detects unnatural motion patterns and blinking anomalies."),
    ("Forensic Rules (8%)", "Edge artifacts, colour banding, frequency anomalies, and JPEG re-compression artifacts."),
    ("Metadata (5%)", "FFprobe-based creation timestamp, codec, and GPS data analysis."),
    ("Lip-sync (0% -- pending calibration)", "Cross-modal audio-visual alignment. Currently disabled: inverted on WhatsApp-compressed video."),
    ("SPN / Sensor Noise (0% -- pending calibration)", "Camera fingerprint analysis. Currently disabled: inverted on compressed video."),
]
for name, desc in signals:
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_x(14)
    pdf.set_text_color(9, 105, 218)
    pdf.cell(0, 6, name, ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(60, 70, 80)
    pdf.set_x(22)
    pdf.multi_cell(0, 5, desc)
    pdf.ln(0.5)
pdf.set_text_color(0, 0, 0)

# ??? 3. CURRENT ACCURACY STATUS ???????????????????????????????????????????????
pdf.section("CURRENT ACCURACY STATUS", "3.")
pdf.body(
    "Evaluation conducted on 4 in-domain videos (3 fake, 1 real) -- all WhatsApp-compressed. "
    "Results show that pre-trained off-the-shelf models do NOT reliably separate real vs. fake on "
    "compressed/re-encoded video. Fine-tuning on domain-specific data is mandatory."
)

pdf.set_font("Helvetica", "B", 9)
pdf.set_x(14)
pdf.set_fill_color(240, 242, 245)
pdf.set_text_color(80, 90, 100)
pdf.cell(60, 7, "Metric", fill=True, border="B", ln=0)
pdf.cell(40, 7, "Current (off-shelf)", fill=True, border="B", ln=0)
pdf.cell(40, 7, "Target", fill=True, border="B", ln=0)
pdf.cell(30, 7, "Status", fill=True, border="B", ln=True)
pdf.set_text_color(0,0,0)

pdf.target_row("Fake video score", "52-67%  (too low)", ">= 75%", "PENDING")
pdf.target_row("Real video score", "54%  (too high)", "<= 20%", "PENDING")
pdf.target_row("Fake recall (detection rate)", "~60% estimated", ">= 75%", "PENDING")
pdf.target_row("False positive on real video", "~40% estimated", "<= 20%", "PENDING")
pdf.ln(3)

pdf.body(
    "Root cause: both CNN checkpoints (Xception, EfficientNet-B4) were trained on FaceForensics++ "
    "high-quality video (C23 compression). WhatsApp re-encodes at very low bitrate, destroying the "
    "artifact signature these models were trained to find. The model has never seen this compression "
    "profile, so it guesses randomly -- real video scores 54%, indistinguishable from fake."
)

# ??? 4. ACCURACY IMPROVEMENT ROADMAP ?????????????????????????????????????????
pdf.section("ACCURACY IMPROVEMENT ROADMAP", "4.")

pdf.subsection("Step 1 -- Domain-Specific Fine-Tuning (Highest Priority)")
pdf.body(
    "The pre-trained models must be re-trained (fine-tuned) on video from the exact domain of interest: "
    "WhatsApp-compressed, Indian-language, face-swap and voice-clone style deepfakes. "
    "This is the single most impactful action and is estimated to move fake recall from ~60% to >=75% "
    "and reduce false positives on real video from ~40% to <=20%."
)
pdf.bullet("Fine-tune Xception classifier (primary visual model) on domain data.")
pdf.bullet("Fine-tune EfficientNet-B4 classifier (secondary visual model) on same data.")
pdf.bullet("Combine both models via soft-vote ensemble -- typically adds 4-8% accuracy over single model.")
pdf.bullet("Apply JPEG/video compression augmentation during training to mimic WhatsApp re-encoding.")
pdf.bullet("Estimated training time: 2-4 hours per model on free GPU (Kaggle T4).")
pdf.bullet("Total time to first fine-tuned checkpoint: 1-2 days (data prep + training + validation).")

pdf.subsection("Step 2 -- Data Harness Construction")
pdf.body(
    "A data harness is required to standardise, label, and feed video samples into the fine-tuning "
    "pipeline. Without a harness, manual preparation of each video is impractical at scale."
)
pdf.bullet("Harness function: ingest raw video files (MP4/MOV), extract face crops at 299x299px, "
           "apply compression augmentation, write labelled train/val splits.")
pdf.bullet("Labels required: binary (0 = REAL, 1 = FAKE) per video clip.")
pdf.bullet("Harness already partially implemented in train_finetune.py. "
           "Needs extension for batch ingestion of large corpora (1000+ clips).")
pdf.bullet("Chain-of-custody: each video hashed (SHA-256) at ingestion for evidentiary integrity.")

pdf.subsection("Step 3 -- Re-enable Disabled Signals (SPN + Lip-Sync)")
pdf.body(
    "Two signals -- Sensor Pattern Noise (SPN) and Lip-Sync -- are currently disabled (weight = 0) "
    "because they inverted on compressed video during evaluation (real video scored higher than fake). "
    "After fine-tuning on compressed-domain data, these must be re-evaluated and re-enabled with "
    "calibrated weights. Re-enabling both adds ~13% additional signal weight to the pipeline."
)

pdf.subsection("Step 4 -- Active Learning Loop")
pdf.body(
    "Every false verdict corrected by the operator via the 'Mark as wrong' button in the dashboard "
    "is logged. These corrections should be accumulated and used as additional training data in "
    "monthly fine-tuning cycles. This allows the model to continuously improve on cases it gets wrong."
)
pdf.bullet("Feedback stored in: feedback_log.json (auto-created by API).")
pdf.bullet("Target: retrain quarterly or after every 100 corrected verdicts.")

pdf.subsection("Step 5 -- Threshold Calibration")
pdf.body(
    "After fine-tuning, the scoring thresholds (currently: >=75 FAKE, >=55 LIKELY FAKE, >=30 "
    "INCONCLUSIVE, <30 REAL) must be recalibrated on a held-out validation set to achieve the "
    "target operating point."
)

# ??? 5. DATA REQUIREMENTS ?????????????????????????????????????????????????????
pdf.add_page()
pdf.section("DATA REQUIREMENTS", "5.")

pdf.subsection("5.1  Real Video Data -- REQUIRED FROM CYBER CELL")
pdf.body(
    "This is the primary bottleneck. Off-the-shelf models have abundant public fake data but lack "
    "in-domain real video. The Cyber Cell must provide labeled genuine video samples from the "
    "same domain as the fakes being investigated."
)
reqs = [
    ("Minimum quantity", "200 genuine video clips (>= 10 seconds each)"),
    ("Recommended quantity", "500+ clips for reliable >=75% / <=20% accuracy"),
    ("Format", "MP4 or MOV, any resolution >= 480p"),
    ("Source", "WhatsApp-forwarded genuine videos, complainant-provided originals, "
               "CCTV footage with visible faces"),
    ("Language/ethnicity", "Must match target population (Indian faces, Indian language audio)"),
    ("Compression", "Include WhatsApp-forwarded (re-compressed) versions -- the model must learn "
                    "to pass these as REAL"),
    ("Privacy", "Face data must be handled per DPDP Act 2023 guidelines. "
                "Training data should be anonymised or consent-obtained."),
    ("Labelling", "Videos placed in dataset/real/ folder. No other action required -- "
                  "the pipeline labels automatically by folder."),
]
for k, v in reqs:
    pdf.kv(k, v)
    pdf.ln(1)

pdf.subsection("5.2  Fake Video Data -- Available from Public Datasets")
pdf.body(
    "Sufficient public deepfake datasets exist for the fake class. The following have been "
    "identified and integrated into the training pipeline:"
)

datasets = [
    ("FaceForensics++ C23", "gradientvoyager/faceforensics-c23-extracted-faces-100k",
     "~100,000 pre-cropped face images", "Gold standard benchmark. 4 manipulation types: "
     "Deepfakes, Face2Face, FaceSwap, NeuralTextures. C23 compression mimics real-world quality."),
    ("Deepfake and Real Images", "manjilkarki/deepfake-and-real-images",
     "~190,000 face crops", "Large-scale dataset. Already face-cropped at 299x299px. "
     "Fast to train on. Includes real class which can supplement Step 5.1 data."),
    ("DFD -- Deep Fake Detection", "sanikatiwarekar/deep-fake-detection-dfd-entire-original-dataset",
     "~24 GB raw video", "Google/FaceForensics DFD corpus. Raw video -- face extraction required. "
     "High quality source material."),
    ("Deepfake vs Real 60K", "prithivsakthiur/deepfake-vs-real-60k",
     "60,000 images", "Recent 2025 dataset. Good diversity of generation methods."),
    ("StyleGAN3 Faces", "troykueh/real-vs-fake-faces-stylegan3",
     "10,000 images", "AI-generated faces using latest StyleGAN3. Useful for AI-image detection."),
    ("DFDC Faces Sample", "itamargr/dfdc-faces-of-the-train-sample",
     "~3.9 GB faces", "Facebook DFDC competition dataset. High variety of actors and scenarios."),
]

for name, ref, size, desc in datasets:
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_x(14)
    pdf.set_text_color(13, 17, 23)
    pdf.cell(0, 6, name, ln=True)
    pdf.set_font("Helvetica", "I", 8.5)
    pdf.set_text_color(100, 110, 130)
    pdf.set_x(20)
    pdf.cell(0, 5, f"Kaggle: {ref}   |   Size: {size}", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(55, 65, 80)
    pdf.set_x(20)
    pdf.multi_cell(0, 5, desc)
    pdf.ln(2)
pdf.set_text_color(0, 0, 0)

# ??? 6. TRAINING REQUIREMENTS ?????????????????????????????????????????????????
pdf.section("TRAINING INFRASTRUCTURE & REQUIREMENTS", "6.")
pdf.body(
    "Fine-tuning requires GPU compute. The following infrastructure has been identified:"
)
infra = [
    ("Free GPU (current)", "Kaggle Notebooks -- T4 GPU, 30 hrs/week free. "
     "Training job submitted via Kaggle API from Cyber Cell CLI. "
     "Expected training time: 1-2 hrs per model per run."),
    ("Local GPU (available)", "NVIDIA GTX 1650 (4 GB VRAM) on operator laptop. "
     "Suitable for small runs and validation. Slower than cloud T4."),
    ("Cloud GPU (recommended for scale)", "Google Colab Pro or Kaggle Pro ($9-20/month). "
     "Enables 2x T4 GPUs and longer runtimes for large dataset training."),
    ("Storage required", "~50 GB for combined datasets + face cache + model checkpoints."),
    ("Python environment", "Already configured. Dependencies: PyTorch, timm, torchvision, "
     "facenet-pytorch, opencv, fpdf2, fastapi, uvicorn."),
]
for k, v in infra:
    pdf.kv(k, v)
    pdf.ln(2)

# ??? 7. TIMELINE ??????????????????????????????????????????????????????????????
pdf.section("ESTIMATED TIMELINE TO TARGET ACCURACY", "7.")

timeline = [
    ("Week 1", "Data collection",
     "Cyber Cell provides >=200 real video clips. "
     "Ingest into dataset/real/. Run data harness to extract face crops. "
     "Validate data quality and label integrity."),
    ("Week 1-2", "First fine-tuning run",
     "Train Xception on combined data (real: Cyber Cell clips, fake: FF++ + manjilkarki). "
     "Evaluate fake_recall and real_spec on held-out test set. "
     "Expected result after first run: fake ~65-72%, real ~25-35%."),
    ("Week 2-3", "Second iteration",
     "Augment training with additional compression levels. "
     "Add EfficientNet-B4 fine-tuning. Combine via ensemble. "
     "Expected result: fake >=72%, real <=25%."),
    ("Week 3-4", "Calibration & signal re-enable",
     "Threshold calibration on validation set. "
     "Re-test SPN and lip-sync on fine-tuned model. "
     "Re-enable with calibrated weights if behaviour is correct. "
     "Expected result: fake >=75%, real <=20% -- TARGET ACHIEVED."),
    ("Month 2+", "Production & active learning",
     "Deploy calibrated model. "
     "Accumulate operator feedback corrections. "
     "Quarterly fine-tuning cycles to maintain accuracy as deepfake methods evolve."),
]

for period, phase, desc in timeline:
    pdf.set_fill_color(240, 242, 245)
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(9, 105, 218)
    pdf.cell(28, 7, period, fill=True, ln=0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(13, 17, 23)
    pdf.cell(50, 7, f"  {phase}", fill=True, ln=0)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(55, 65, 80)
    pdf.set_fill_color(248, 249, 251)
    pdf.multi_cell(0, 7, f"  {desc}", fill=True)
    pdf.ln(2)
pdf.set_text_color(0, 0, 0)

# ??? 8. WHAT WE NEED FROM CYBER CELL ?????????????????????????????????????????
pdf.add_page()
pdf.section("IMMEDIATE REQUIREMENTS FROM CYBER CELL", "8.")
pdf.body("To begin fine-tuning and achieve target accuracy, the following are required:")

needs = [
    "Real video corpus: minimum 200 WhatsApp-compressed genuine video clips with visible faces. "
     "Format: MP4/MOV in dataset/real/ folder on training machine.",
    "Subject diversity: include different genders, ages, and lighting conditions to prevent "
     "the model from learning demographic shortcuts instead of manipulation artifacts.",
    "Case-derived test set: 20-30 real + 20-30 fake videos from actual cases (without PII), "
     "held out for final accuracy evaluation. These must NOT be used in training.",
    "Approval for Kaggle API training: the system already has Kaggle API access configured "
     "(account: nishubeniwal). Confirm this is acceptable for submitting training notebooks "
     "to Kaggle's free GPU infrastructure.",
    "Timeline commitment: the operator must be available during Week 1 to validate that "
     "collected real video is genuinely authentic and correctly labelled.",
]
for n in needs:
    pdf.bullet(n)

# ??? 9. TECHNICAL SPECIFICATIONS ?????????????????????????????????????????????
pdf.section("TECHNICAL SPECIFICATIONS", "9.")

specs = [
    ("Primary model", "Xception (pretrained ImageNet ? fine-tuned on deepfake domain)"),
    ("Secondary model", "EfficientNet-B4 (pretrained ? fine-tuned, ensemble with Xception)"),
    ("Input resolution", "299 × 299 px face crops (MTCNN face detection)"),
    ("Training framework", "PyTorch + timm + torchvision"),
    ("Augmentation", "RandomHorizontalFlip, JPEG re-compression (Q=25-80), ColorJitter, Rotation"),
    ("Loss function", "CrossEntropyLoss with class weights (handles imbalanced datasets)"),
    ("Optimiser", "AdamW, lr=1e-4, weight_decay=1e-4, CosineAnnealing scheduler, 15 epochs"),
    ("Evaluation metrics", "Fake recall (TP rate on fake class), Real specificity (TN rate on real class)"),
    ("Target thresholds", "Fake score >= 75 ? FAKE  |  Real score <= 20 ? REAL"),
    ("Checkpoint format", "Native timm state_dict ? xception_deepfake.pt (auto-loaded by classifier)"),
    ("API", "FastAPI + uvicorn, REST endpoints: /analyze/video, /cases, /jobs, /feedback, /results"),
    ("Dashboard", "Pure HTML/JS, no external dependencies, light theme, localhost:8000"),
]
for k, v in specs:
    pdf.kv(k, v)
    pdf.ln(1.5)

# ??? 10. CONCLUSION ???????????????????????????????????????????????????????????
pdf.section("CONCLUSION", "10.")
pdf.body(
    "The Cyber Cell Deepfake Detection System is operational and provides a full forensic workflow -- "
    "from evidence ingestion to chain-of-custody reporting. The current accuracy limitation is "
    "well-understood and solvable: off-the-shelf models fail on compressed video because they were "
    "not trained on that domain. Fine-tuning on even 200 real + 200 fake in-domain clips is expected "
    "to achieve the 75% / 20% target within 3-4 weeks."
)
pdf.body(
    "The primary dependency is real video data from the Cyber Cell. Fake data from six high-quality "
    "public datasets (100,000-190,000 samples) is already integrated into the training pipeline. "
    "GPU compute is available free of charge via Kaggle, and the training pipeline is fully automated "
    "-- submitting a new training run requires a single CLI command."
)
pdf.body(
    "Once target accuracy is achieved, the model will be retrained quarterly using operator feedback "
    "to maintain performance as deepfake generation techniques evolve."
)

# ??? FINAL STAMP ??????????????????????????????????????????????????????????????
pdf.ln(4)
pdf.set_fill_color(15, 27, 45)
pdf.rect(10, pdf.get_y(), 190, 18, 'F')
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(201, 209, 217)
pdf.set_xy(14, pdf.get_y() + 4)
pdf.cell(130, 6, "Cyber Cell  |  Forensics Division  |  Deepfake Detection Unit", ln=0)
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(140, 160, 190)
pdf.cell(0, 6, TODAY, ln=True, align="R")

out = r"C:\Users\nbeni\OneDrive\Desktop\deepfake\deepfake\Deepfake\report.pdf"
pdf.output(out)
print("PDF written:", out)
