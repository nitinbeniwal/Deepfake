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

REM Upgrade pip
python -m pip install --upgrade pip --quiet

REM ---- STEP 1: Pin numpy 2.x FIRST ----
REM numpy 1.26.x has no prebuilt wheel for Python 3.13 and requires a C compiler.
REM Pre-installing numpy 2.x prevents pip from backtracking to 1.26 when
REM resolving other package dependencies (facenet-pytorch, grad-cam, etc.)
echo.
echo Step 1/3: Installing numpy 2.x (Python 3.13 compatible wheel)...
pip install "numpy>=2.0.0" --quiet
if errorlevel 1 (
    echo ERROR: numpy install failed.
    pause
    exit /b 1
)
echo numpy OK.

REM ---- STEP 2: Install facenet-pytorch without strict numpy constraint ----
echo.
echo Step 2/3: Installing facenet-pytorch...
pip install "facenet-pytorch>=2.5.3" --quiet
if errorlevel 1 (
    echo ERROR: facenet-pytorch install failed.
    pause
    exit /b 1
)
echo facenet-pytorch OK.

REM ---- STEP 3: Install all remaining requirements ----
echo.
echo Step 3/3: Installing remaining requirements (PyTorch, transformers, timm...)
echo This takes 3-8 minutes on first run (~2GB download).
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed.
    echo Common fixes:
    echo   - Check internet connection
    echo   - Run as Administrator
    echo   - Try: pip install -r requirements.txt --no-build-isolation
    pause
    exit /b 1
)

echo.
echo ================================================
echo  Setup complete!
echo.
echo  Run:      run_local.bat
echo  Then open: http://localhost:8000
echo ================================================
pause
