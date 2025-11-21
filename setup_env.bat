@echo off
echo ========================================
echo DocSearch - Environment Setup
echo ========================================
echo.

echo Step 1: Creating Virtual Environment...
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo [!] Failed to create virtual environment.
    echo Please ensure Python is installed and in your PATH.
    pause
    exit /b 1
)
echo [OK] Virtual environment created.
echo.

echo Step 2: Upgrading pip...
venv\Scripts\python.exe -m pip install --upgrade pip
echo [OK] Pip upgraded.
echo.

echo Step 3: Installing Dependencies...
echo This may take a few minutes...
venv\Scripts\pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Installation encountered errors.
    echo This might be due to Windows Long Path limits.
    echo.
    echo Attempting to install core dependencies only...
    venv\Scripts\pip install Flask PyPDF2 pytesseract Pillow pdf2image Werkzeug gunicorn
    echo.
    echo [!] Core dependencies installed. Vector DB might be unavailable.
) else (
    echo [OK] All dependencies installed successfully!
)
echo.

echo Setup Complete!
echo.
pause
