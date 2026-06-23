# Architecture

Flat module layout (every module imports siblings directly, e.g.
`from classifier import ...`). Run commands from inside `deepfake_detector/`.
Modules are grouped below by role — the files are flat on disk on purpose so the
existing imports and the Railway/Docker entrypoint keep working.

## Entry points
| File          | Role                                                        |
|---------------|-------------------------------------------------------------|
| `api.py`      | FastAPI server — REST + dashboard. **Canonical entrypoint.** |
| `web_ui.py`   | Dashboard HTML/JS served by `api.py`                        |
| `main.py` / `gui.py` / `dashboard.py` | Older/standalone entrypoints — not used by the server |

Run: `uvicorn api:app --host 0.0.0.0 --port 8000`

## Core scoring
| File                | Role                                                    |
|---------------------|---------------------------------------------------------|
| `pipeline.py`       | Sequential multi-modal pipeline (video/image/audio)     |
| `classifier.py`     | 7-model visual ensemble (ViT ×5 + Xception + EffNet-B4) |
| `aggregator.py`     | Per-frame / per-signal aggregation helpers              |
| `meta_classifier.py`| Rule layer over component scores                         |
| `calibration.py`    | **Single source** of verdict bands + feedback-learned offset |

## Signals (one analysis step each)
`audio_classifier.py` `temporal_analyzer.py` `lipsync_analyzer.py`
`spn_analyzer.py` `forensic_rules.py` `metadata_analyzer.py`
`face_detector.py` `frame_extractor.py`

> `lipsync` and `spn` are weight-0 (they invert on compressed video) — they run
> for display only and are stripped before `meta_classifier` sees them.

## Models / forensics
`model_downloader.py` (fetches FF++ checkpoints at startup) · `gradcam_engine.py`

## Case management (cyber-cell)
`case_store.py` · `report.py` · `takedown.py`

## Training / eval (manual, offline — NOT run on upload)
`train_finetune.py` · `Calibrate.py` · `batch_eval.py` · `per_model_diag.py`
· `diagnose.py` · `test.py` · `test_accuracy.py`

## Misc tools
`crawler.py` · `processor.py` · `text_detector.py` · `audio_classifier.py`

---

## How scoring works (and recent fixes)

1. **Verdict bands** are defined once in `calibration.json`
   (`fake≥85, likely≥72, inconclusive≥30, real<30`). Video, image and audio all
   call `calibration.verdict()` — previously each had its own thresholds.

2. **Calibration offset** is subtracted from visual scores. It is **learned from
   feedback**: every `POST /feedback` recomputes it (`calibration.record_feedback`)
   so genuine clips that read too high are pushed toward REAL on the next upload.
   The move is confidence-weighted (few corrections → small move) and clamped
   `[-20, +40]`. No retraining happens on upload — only this offset adapts.

3. **Models stay warm** between uploads (`_KEEP_WARM` in `pipeline.py`) unless
   `LOW_MEM=1`. Only the first upload pays the model-load cost.

## Things still worth doing
- Fine-tune `xception_deepfake.pt` on your own compressed clips
  (`train_finetune.py`) — the off-the-shelf FF++ weights don't separate
  WhatsApp-recompressed real vs fake well; the feedback offset only shifts the
  band, it can't add discrimination the models lack.
- Verify the HF model IDs in `classifier._MODELS` all load (some can 404 and get
  silently skipped, which shifts the renormalized score).
