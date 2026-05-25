@echo off
setlocal enabledelayedexpansion
if not "%1"=="--no-pause" (
    cls
    chcp 65001 >nul
    echo ======================================
    echo        BNOS Node Starter (Windows)
    echo ======================================
    echo.
)
cd /d "%~dp0"

REM ==================== 环境检测与自愈 ====================
if not "%1"=="--no-pause" echo 🔍 检测虚拟环境状态...

if not exist "venv\Scripts\python.exe" (
    if not "%1"=="--no-pause" (
        echo ⚠️ 检测到虚拟环境缺失或损坏
        echo.
        echo 🔧 开始自动修复...
        echo.
    )
    
    if exist "..\..\tools\python_create_node.py" (
        python ..\..\tools\python_create_node.py --repair-only "%CD%"
        if errorlevel 1 (
            if not "%1"=="--no-pause" (
                echo.
                echo ❌ 自动修复失败
                echo 💡 请手动删除venv文件夹后重新创建节点
                pause
            )
            exit /b 1
        )
        if not "%1"=="--no-pause" (echo. && echo ✅ 虚拟环境重建成功)
    ) else (
        if not "%1"=="--no-pause" (
            echo ❌ 找不到python_create_node.py，无法自动修复
            echo 💡 请手动删除venv文件夹后重新创建节点
            pause
        )
        exit /b 1
    )
) else (
    if not "%1"=="--no-pause" echo ✅ 虚拟环境检测通过
)

REM ==================== 后台启动 + PID 记录 ====================
if not "%1"=="--no-pause" (
    echo.
    echo 🔧 后台启动监听程序...
    echo.
    start /b "" venv\Scripts\python.exe listener.py
) else (
    start /b "" venv\Scripts\python.exe listener.py >nul 2>&1
)

REM 写入 PID 文件供 GUI 检测
powershell -Command "$p=(Get-WmiObject Win32_Process -Filter "Name='python.exe' and CommandLine like '%%listener.py%%'" | Select-Object -First 1).ProcessId; if($p){{$p | Out-File -FilePath '.pid' -Encoding ASCII -NoNewline}}"

if not "%1"=="--no-pause" (
    echo ✅ 监听程序已在后台运行
    pause
)