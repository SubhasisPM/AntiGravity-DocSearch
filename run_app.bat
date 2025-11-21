@echo off
echo ========================================
echo DocSearch - Application Launcher
echo ========================================
echo.

echo Checking for Python...
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Python found!
    goto :start
)

py --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Python Launcher found!
    set PYTHON_CMD=py
    goto :start_py
)

echo [!] Python not found in PATH.
echo.
echo Please install Python from: https://www.python.org/downloads/
echo IMPORTANT: Check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:start
echo Starting DocSearch Server...
echo.
echo Open your browser to: http://localhost:5000
echo.
venv\Scripts\python.exe app.py
pause
exit /b

:start_py
echo Starting DocSearch Server...
echo.
echo Open your browser to: http://localhost:5000
echo.
venv\Scripts\python.exe app.py
pause
exit /b
