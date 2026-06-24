@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  run_all.bat  — one-click training pipeline (run on the GPU laptop)
REM  download datasets -> sort -> fine-tune CNN -> score -> train fusion
REM ============================================================
cd /d "%~dp0"

REM ---- 1. credentials ----
if not exist "creds.env" (
    echo ERROR: creds.env not found.
    echo   copy creds.env.example to creds.env and fill in your tokens.
    pause & exit /b 1
)
echo Loading credentials from creds.env ...
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("creds.env") do (
    if not "%%a"=="" set "%%a=%%b"
)

REM ---- 2. activate the detector venv (created by setup_local.bat) ----
if not exist "..\venv\Scripts\activate.bat" (
    echo ERROR: ..\venv not found. Run setup_local.bat in the repo root first.
    pause & exit /b 1
)
call "..\venv\Scripts\activate.bat"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

REM ---- 3. GPU check (training is painfully slow on CPU) ----
python -c "import torch;print('CUDA available:',torch.cuda.is_available(), '|', (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only'))"
echo If that says 'CPU only' on your GTX 1650, install a CUDA build of torch:
echo    pip install --index-url https://download.pytorch.org/whl/cu121 torch torchvision --upgrade
echo (training still runs on CPU, just much slower)
echo.

REM ---- 4. training deps for downloading ----
echo Installing dataset-download tools (kaggle, huggingface_hub, modelscope) ...
pip install kaggle huggingface_hub modelscope --quiet

REM ---- 5. download ----
echo.
echo === STEP 1/4: downloading datasets ===
python download_datasets.py || (echo download failed & pause & exit /b 1)

REM ---- 6. sort into dataset/real and dataset/fake ----
echo.
echo === STEP 2/4: sorting into real/fake ===
python prepare_dataset.py || (echo prepare failed & pause & exit /b 1)

REM ---- 7. fine-tune the CNN (overwrites xception_deepfake.pt) ----
echo.
echo === STEP 3/4: fine-tuning Xception on your data ===
cd ..
python train_finetune.py --data training\dataset --epochs 15 || (echo finetune failed & pause & exit /b 1)

REM ---- 8. score for fusion + train the fusion head ----
echo.
echo === STEP 4/4: scoring clips + training fusion head ===
python training\score_dataset.py --limit 400 || (echo scoring failed & pause & exit /b 1)
python train_fusion.py --csv training\fusion_train.csv || (echo fusion train failed & pause & exit /b 1)

echo.
echo ============================================================
echo  DONE. New weights: xception_deepfake.pt + fusion_model.json
echo  Restart the server (run_local.bat) to use them.
echo ============================================================
pause
