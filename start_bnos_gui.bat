@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONLEGACYWINDOWSSTDIO=utf-8
setlocal enabledelayedexpansion

cls
echo ======================================
echo   BNOS Desktop Visual Node Platform
echo ======================================
echo.

:: ==================== CONFIG ====================
set "VENV_DIR=myenv_new"
set "REQUIREMENTS=requirements_gui.txt"
set "PYTHON=python"
set "MAIN_FILE=bnos_gui.py"
set "GUI_DIR=."

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

:: ==================== GO TO GUI FOLDER ====================
cd /d "%GUI_DIR%"

:: ==================== CHECK DEPENDENCIES ====================
echo [INFO] Verifying dependencies...
if exist "%REQUIREMENTS%" (
    echo [INFO] Installing dependencies from %REQUIREMENTS%...
    pip install -r %REQUIREMENTS%
) else (
    echo [WARN] %REQUIREMENTS% not found. Installing base PyQt6...
    pip install pyqt6
)

:: ==================== START GUI ====================
echo.
echo ======================================
echo Starting BNOS GUI Application...
echo ======================================
echo.

%PYTHON% "%MAIN_FILE%"

:: ==================== EXIT ====================
echo.
echo [INFO] Application exited.
pause
exit /b %errorlevel%