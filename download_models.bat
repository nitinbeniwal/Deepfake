@echo off
setlocal enabledelayedexpansion

echo ================================================
echo  Deepfake Detector - Download CNN Checkpoints
echo  Xception + EfficientNet-B4 (DeepfakeBench)
echo ================================================
echo.

cd /d "%~dp0deepfake_detector"

if not exist "venv313\Scripts\activate.bat" (
    echo ERROR: Run setup_local.bat first.
    pause
    exit /b 1
)

call venv313\Scripts\activate.bat

echo Downloading Xception (~86MB) and EfficientNet-B4 (~75MB)...
echo This may take 2-5 minutes on a normal connection.
echo.

python -c "
import sys
sys.path.insert(0, '.')
from model_downloader import ensure_checkpoints
print('Starting downloads...')
ensure_checkpoints(blocking=True)
print('Done.')
"

echo.
echo ================================================
echo  Checkpoint download complete.
echo  Restart the server (run_local.bat) to use them.
echo ================================================
pause
