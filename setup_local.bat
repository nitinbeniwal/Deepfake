@echo off
setlocal enabledelayedexpansion

echo ================================================
echo  Deepfake Detector - Local Setup (Windows)
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Python found: %PYVER%

REM Go to deepfake_detector subfolder (where all .py files live)
cd /d "%~dp0deepfake_detector"

REM Create virtual environment if not exists
if not exist "venv\" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create venv
        pause
        exit /b 1
    )
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip silently
python -m pip install --upgrade pip --quiet

REM Install requirements
echo.
echo Installing requirements (this takes 3-5 minutes on first run)...
echo (Downloading PyTorch, transformers, timm, facenet-pytorch...)
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. Check internet connection.
    pause
    exit /b 1
)

echo.
echo ================================================
echo  Setup complete!
echo  Run:  run_local.bat   to start the server
echo  Then open:  http://localhost:8000
echo ================================================
pause
