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
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created
)

REM Activate virtual environment
call myenv_new\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

REM Upgrade pip
python -m pip install --upgrade pip >nul 2>&1

REM Check dependencies
echo [INFO] Checking dependencies...
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo [INFO] PyQt6 not found, installing dependencies...
    pip install pyqt6
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed
) else (
    echo [SUCCESS] All dependencies are ready
)

echo.
echo [INFO] Starting BNOS Node Platform...
echo.

REM Run program
python bnos_gui.py

if errorlevel 1 (
    echo.
    echo [ERROR] Program exited with error code: %errorlevel%
    pause
)
