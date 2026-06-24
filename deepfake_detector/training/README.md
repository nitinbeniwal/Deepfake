# Training harness

Everything to fine-tune the detector on your GPU laptop. You only RUN files —
no setup beyond putting your tokens in `creds.env`.

## What it does
1. **download_datasets.py** — pulls curated Kaggle/HF datasets into `datasets/`.
2. **prepare_dataset.py** — sorts them into `dataset/real/` and `dataset/fake/`.
3. **train_finetune.py** (repo root) — fine-tunes Xception → `xception_deepfake.pt`.
4. **score_dataset.py** — runs the pipeline over labeled clips → `fusion_train.csv`.
5. **train_fusion.py** (repo root) — trains the fusion head → `fusion_model.json`.

The app auto-loads both new files on the next server start. Nothing here is
committed: `datasets/`, `dataset/`, `creds.env`, and the CSVs are all gitignored.

## One-time setup on the laptop
```
git clone https://github.com/nitinbeniwal/Deepfake
cd Deepfake
setup_local.bat                      # builds venv + installs deps (one time)
```
Then **install a CUDA build of torch** so the GTX 1650 is used (huge speedup):
```
deepfake_detector\venv\Scripts\python -m pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision --upgrade
```

## Tokens
```
cd deepfake_detector\training
copy creds.env.example creds.env
notepad creds.env                    # paste your Kaggle / HF tokens
```
(Kaggle: easiest is to drop `kaggle.json` at `%USERPROFILE%\.kaggle\kaggle.json`
instead of filling KAGGLE_USERNAME/KEY.)

## Run the whole thing
```
run_all.bat
```
That downloads → sorts → fine-tunes → scores → trains fusion, end to end.

## Or run steps manually
```
cd deepfake_detector\training
python download_datasets.py
python prepare_dataset.py
cd ..
python train_finetune.py --data training\dataset --epochs 15
python training\score_dataset.py --limit 400
python train_fusion.py --csv training\fusion_train.csv
```

## Add your OWN phone clips (recommended — best accuracy)
Drop real clips into `training/dataset/real/` and fakes into
`training/dataset/fake/` before running `train_finetune.py`. In-domain data beats
any public dataset for your use case.

## Datasets pulled (edit `DATASETS` in download_datasets.py to change)
| name | source | notes |
|---|---|---|
| faceforensicspp | Kaggle | FaceForensics++ — gold standard face-swap |
| deepfakefusion | Kaggle | 399k real/fake faces |
| cropped | Kaggle | pre-cropped faces, fast |
| stylegan3 | Kaggle | GAN faces |
| df2026 | Kaggle | recent |
| df2026_images_hf | HF | recent AI images |
| ddl | ModelScope | **OFF by default** — 1.8M, 88 techniques, huge |

Turn DDL on only with lots of disk/time (it's the best for AI-generation like
Gemini/Veo, but it's enormous).

## After training
Restart the server (`run_local.bat`). It loads `xception_deepfake.pt` and
`fusion_model.json` automatically — verdict now uses your fine-tuned model + the
learned fusion instead of the off-the-shelf weighted average.
