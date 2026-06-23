@echo off
setlocal enabledelayedexpansion

echo ================================================
echo  Deepfake Detector - Starting Local Server
echo ================================================
echo.

cd /d "%~dp0deepfake_detector"

REM Check venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo Run setup_local.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

REM Set environment variables for local run
set LOW_MEM=0
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set TRANSFORMERS_CACHE=%~dp0.model_cache\hf
set HF_HOME=%~dp0.model_cache\hf
set PORT=8000

REM Create cache dir
if not exist "%~dp0.model_cache\hf" mkdir "%~dp0.model_cache\hf"

echo.
echo  Server:   http://localhost:8000
echo  API docs: http://localhost:8000/docs
echo.
echo  First run: HuggingFace models download automatically (~2GB total)
echo  Models cached after first run - subsequent starts are instant.
echo.
echo  Press Ctrl+C to stop the server.
echo.

python -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload

pause
