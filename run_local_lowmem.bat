@echo off
setlocal enabledelayedexpansion

echo ================================================
echo  Deepfake Detector - Low Memory Mode (under 8GB RAM)
echo  Sequential model loading - slower but stable
echo ================================================
echo.

cd /d "%~dp0deepfake_detector"

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Run setup_local.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

set LOW_MEM=1
set TRANSFORMERS_CACHE=%~dp0.model_cache\hf
set HF_HOME=%~dp0.model_cache\hf
set PORT=8000

if not exist "%~dp0.model_cache\hf" mkdir "%~dp0.model_cache\hf"

echo  LOW_MEM=1 active: models load one at a time (uses ~2GB peak RAM)
echo  Server: http://localhost:8000
echo.

python -m uvicorn api:app --host 0.0.0.0 --port 8000

pause
