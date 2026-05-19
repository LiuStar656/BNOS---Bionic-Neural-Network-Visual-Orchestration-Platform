@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ======================================
echo   BNOS Desktop Visual Node Platform
echo ======================================
echo.

:: ==================== 配置区域（你不用改）====================
set "VENV_DIR=myenv_new"
set "REQUIREMENTS=requirements_gui.txt"
set "PYTHON_CMD=python"
set "PIP_CMD=!VENV_DIR!\Scripts\pip.exe"
set "ACTIVATE_CMD=!VENV_DIR!\Scripts\activate.bat"
set "MAIN_SCRIPT=bnos_gui.py"

:: ==================== 检查Python ====================
echo [INFO] 检查 Python 环境...
where !PYTHON_CMD! >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python，请安装并添加到PATH
    pause
    exit /b 1
)

:: ==================== 检查虚拟环境 ====================
echo [INFO] 检查虚拟环境：!VENV_DIR!
if not exist "!ACTIVATE_CMD!" (
    echo [WARN] 虚拟环境不存在，正在自动创建...
    !PYTHON_CMD! -m venv !VENV_DIR!
    
    if errorlevel 1 (
        echo [ERROR] 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo [SUCCESS] 虚拟环境创建完成
)

:: ==================== 激活虚拟环境 ====================
echo [INFO] 激活虚拟环境...
call "!ACTIVATE_CMD!"

:: ==================== 升级pip ====================
echo [INFO] 升级 pip...
!PYTHON_CMD! -m pip install --upgrade pip >nul 2>&1

:: ==================== 安装依赖 ====================
echo [INFO] 检查项目依赖...
if exist "!REQUIREMENTS!" (
    echo [INFO] 正在安装依赖：!REQUIREMENTS!
    !PIP_CMD! install -r !REQUIREMENTS!
) else (
    echo [INFO] 安装基础依赖 PyQt6
    !PIP_CMD! install pyqt6
)

:: ==================== 启动程序 ====================
echo.
echo ======================================
echo 启动 BNOS GUI 主程序...
echo ======================================
echo.

!PYTHON_CMD! "!MAIN_SCRIPT!"

echo.
echo [INFO] 程序已退出
pause
exit /b %errorlevel%