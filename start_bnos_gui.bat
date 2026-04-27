@echo off
chcp 65001 >nul
echo ======================================
echo   BNOS Desktop Visual Node Platform
echo ======================================
echo.

REM Check virtual environment
if not exist "myenv_new\Scripts\activate.bat" (
    echo [INFO] Virtual environment not found, creating...
    python -m venv myenv_new
)

REM Activate virtual environment
call myenv_new\Scripts\activate.bat

REM Check dependencies
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    pip install pyqt6
)

echo [INFO] Starting BNOS Node Platform...
echo.

REM Run program
python bnos_gui.py

if errorlevel 1 (
    echo [ERROR] Program exited with error code: %errorlevel%
    pause
)
