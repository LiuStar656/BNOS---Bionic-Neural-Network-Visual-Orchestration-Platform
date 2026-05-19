@echo off
REM Set UTF-8 encoding to prevent garbled text
chcp 65001 >nul

echo ======================================
echo   BNOS Desktop Visual Node Platform
echo ======================================
echo.

REM ==================== Step 1: Check Python Installation ====================
echo [INFO] Checking Python installation...
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

python --version
echo [SUCCESS] Python detected
echo.

REM ==================== Step 2: Check and Create Virtual Environment ====================
echo [INFO] Checking virtual environment...

if not exist "myenv_new\Scripts\activate.bat" (
    echo [WARN] Virtual environment not found
    echo.
    echo [INFO] Creating virtual environment (myenv_new)...
    python -m venv myenv_new
    
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment
        echo.
        echo Possible reasons:
        echo 1. Python is not properly installed
        echo 2. Insufficient disk space
        echo 3. No write permission in current directory
        echo.
        pause
        exit /b 1
    )
    
    echo [SUCCESS] Virtual environment created successfully
) else (
    echo [SUCCESS] Virtual environment found
)
echo.

REM ==================== Step 3: Activate Virtual Environment ====================
echo [INFO] Activating virtual environment...
call myenv_new\Scripts\activate.bat

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to activate virtual environment
    echo.
    echo Please try:
    echo 1. Delete the myenv_new folder
    echo 2. Run this script again
    echo.
    pause
    exit /b 1
)

echo [SUCCESS] Virtual environment activated
echo.

REM ==================== Step 4: Upgrade pip ====================
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

if errorlevel 1 (
    echo [WARN] Failed to upgrade pip, but will continue
) else (
    echo [SUCCESS] pip upgraded
)
echo.

REM ==================== Step 5: Check and Install Dependencies ====================
echo [INFO] Checking dependencies...

REM Check if requirements file exists
if not exist "requirements_gui.txt" (
    echo [WARN] requirements_gui.txt not found
    echo.
    echo [INFO] Will attempt to install basic dependencies...
    set INSTALL_CMD=pip install pyqt6
) else (
    echo [INFO] Found requirements_gui.txt
    echo.
    set INSTALL_CMD=pip install -r requirements_gui.txt
)

REM Quick check if key dependency is installed
python -c "import PyQt6" 2>nul
if errorlevel 1 (
    echo [WARN] Key dependencies not found
    echo.
    echo [INFO] Installing dependencies (this may take a few minutes)...
    echo.
    
    %INSTALL_CMD%
    
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install dependencies
        echo.
        echo Please try:
        echo 1. Check your internet connection
        echo 2. Try running: pip install pyqt6 manually
        echo 3. See README.md for manual installation instructions
        echo.
        pause
        exit /b 1
    )
    
    echo.
    echo [SUCCESS] Dependencies installed successfully
) else (
    echo [SUCCESS] All dependencies are ready
)
echo.

REM ==================== Step 6: Start Application ====================
echo ======================================
echo Starting BNOS Node Platform...
echo ======================================
echo.

python bnos_gui.py

set EXIT_CODE=%errorlevel%

if %EXIT_CODE% neq 0 (
    echo.
    echo ======================================
    echo [ERROR] Program exited with error code: %EXIT_CODE%
    echo ======================================
    echo.
    echo Common issues:
    echo 1. Missing display server (Linux)
    echo 2. PyQt6 installation incomplete
    echo 3. Permission denied
    echo.
    echo Check the error messages above for details
    pause
)

exit /b %EXIT_CODE%
