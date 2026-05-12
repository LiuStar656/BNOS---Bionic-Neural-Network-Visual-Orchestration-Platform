@echo off
cls
chcp 65001 >nul
echo ======================================
echo        BNOS Rust Node Starter
echo ======================================
echo.
cd /d "%%~dp0"

REM ==================== 环境检测与自愈 ====================
echo 🔍 检测 Rust 环境和编译产物...

if not exist "target\release\9.exe" (
    echo ⚠️ 检测到编译产物缺失
    echo.
    echo 🔧 开始自动构建...
    echo.
    
    REM 检查 Rust 是否安装
    where rustc >nul 2>&1
    if errorlevel 1 (
        echo ❌ Rust 未安装
        echo 💡 请先安装 Rust: https://rustup.rs/
        pause
        exit /b 1
    )
    
    REM 构建项目
    cargo build --release
    if errorlevel 1 (
        echo.
        echo ❌ 构建失败
        pause
        exit /b 1
    )
    echo.
    echo ✅ 构建成功
) else (
    echo ✅ 编译产物检测通过
)

echo.
echo ✅ 启动监听程序...
echo.
target\release\9_listener.exe
echo.
echo ❌ 程序已退出
pause
