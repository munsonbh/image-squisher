@echo off
REM Setup script for image-squisher (Windows)

echo ==========================================
echo Image Squisher - Setup (Windows)
echo ==========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8 or higher.
    echo Download from: https://www.python.org/downloads/
    exit /b 1
)

echo Checking Python version...
python --version
echo.

REM Create venv if it doesn't exist
echo Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
    echo [OK] Created virtual environment
) else (
    echo [OK] Virtual environment already exists
)

REM Activate venv
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

REM Install core dependencies
echo.
echo Installing Python dependencies...
python -m pip install "Pillow>=10.0.0" --quiet
echo [OK] Installed Pillow

REM Note: pillow-heif is macOS-only, skip on Windows
echo [INFO] pillow-heif skipped (macOS only - HEIC support not available on Windows)

REM Check for optional dependencies
echo.
echo Checking optional dependencies...

REM Check for JPEG XL (cjxl.exe)
where cjxl.exe >nul 2>&1
if errorlevel 1 (
    echo [WARN] JPEG XL not found (optional)
    echo   Download from: https://github.com/libjxl/libjxl/releases
) else (
    echo [OK] JPEG XL support available
)

echo.
echo ==========================================
echo Setup complete!
echo ==========================================
echo.
echo Next steps:
echo   1. Activate the virtual environment:
echo      venv\Scripts\activate
echo.
echo   2. (Optional) Install JPEG XL support:
echo      Download from: https://github.com/libjxl/libjxl/releases
echo.
echo   3. Run the script:
echo      python main.py C:\path\to\your\images
echo.

