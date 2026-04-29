@echo off
cls
echo ======================================
echo        BNOS Node Starter (Windows)
echo ======================================
echo.
cd /d "%~dp0"
chmp 65001 >nul
if not exist "venv\Scripts\python.exe" (
    echo ❌ 虚拟环境不存在！
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
echo ✅ 启动监听程序...
echo.
venv\Scripts\python.exe listener.py
echo.
echo ❌ 程序已退出
pause
