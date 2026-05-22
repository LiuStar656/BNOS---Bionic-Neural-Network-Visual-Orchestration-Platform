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
set "VENV_DIR=myenv_new"
set "REQUIREMENTS=requirements.txt"
set "PYTHON=python"

:: ==================== CHECK PYTHON ====================
echo [INFO] Checking Python environment...
where %PYTHON% >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python and add to PATH.
    pause
    exit /b 1
)

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

:: ==================== ACTIVATE VENV ====================
echo [INFO] Activating virtual environment...
call "%VENV_DIR%\Scripts\activate.bat"

:: ==================== GO TO APP FOLDER ====================
cd /d "%APP_DIR%"

:: ==================== CHECK DEPENDENCIES ====================
echo [INFO] Checking dependencies from %REQUIREMENTS%...
if not exist "%REQUIREMENTS%" (
    echo [WARN] %REQUIREMENTS% not found. Installing base PyQt6...
    pip install pyqt6
    goto :start_gui
)
python -c "import pkg_resources; pkg_resources.require(open('%REQUIREMENTS%').readlines())" >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Missing dependencies. Installing from %REQUIREMENTS%...
    pip install -r %REQUIREMENTS%
) else (
    echo [OK] All dependencies satisfied. Skipping.
)

:start_gui

:: ==================== START APP ====================
echo.
echo ======================================
echo Starting BNOS Console...
echo ======================================
echo.

:: 启动 launcher (pythonw 完全无终端)
if exist %PYTHON%w.exe (
    start "" %PYTHON%w launcher.py
) else (
    start "" /b %PYTHON% launcher.py
)
exit /b 0