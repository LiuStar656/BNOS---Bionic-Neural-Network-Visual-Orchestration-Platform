@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=utf-8
setlocal enabledelayedexpansion

cls
echo ======================================
echo   BNOS Console - Visual Node Orchestration
echo ======================================
echo.

:: ==================== CONFIG ====================
set "VENV_DIR=venv"
set "REQUIREMENTS=requirements.txt"
set "PYTHON=python"

:: ==================== CHECK PYTHON ====================
echo [INFO] Checking Python environment...
where %PYTHON% >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.12+ and add to PATH.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('%PYTHON% --version 2^>^&1') do set PYTHON_VERSION=%%v
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if %PY_MAJOR% lss 3 (
    echo [ERROR] Python version must be 3.12 or higher.
    echo [INFO] Detected: %PYTHON_VERSION%
    pause
    exit /b 1
)
if %PY_MAJOR% equ 3 if %PY_MINOR% lss 12 (
    echo [ERROR] Python version must be 3.12 or higher.
    echo [INFO] Detected: %PYTHON_VERSION%
    pause
    exit /b 1
)
echo [OK] Python 3.12+ detected
echo.

:: ==================== CREATE VENV IF NOT EXISTS ====================
echo [INFO] Checking virtual environment: %VENV_DIR%
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [WARN] Virtual environment not found. Creating new one...
    %PYTHON% -m venv %VENV_DIR%
    
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created.
)
echo.

:: ==================== ACTIVATE VENV ====================
echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

:: ==================== UPGRADE PIP ====================
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] pip upgraded
) else (
    echo [WARN] Failed to upgrade pip, continuing...
)
echo.

:: ==================== CHECK DEPENDENCIES ====================
echo [INFO] Checking dependencies from %REQUIREMENTS%...
if not exist "%REQUIREMENTS%" (
    echo [WARN] %REQUIREMENTS% not found. Installing base dependencies...
    pip install pyside6 psutil
    goto :start_gui
)
python -c "import pkg_resources; pkg_resources.require(open('%REQUIREMENTS%').readlines())" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Missing dependencies. Installing from %REQUIREMENTS%...
    pip install -r %REQUIREMENTS%
) else (
    echo [OK] All dependencies satisfied. Skipping.
)
echo.

:start_gui

:: ==================== START APP ====================
echo ======================================
echo Starting BNOS Console...
echo ======================================
echo.

python bnos_console.py

exit /b %errorlevel%