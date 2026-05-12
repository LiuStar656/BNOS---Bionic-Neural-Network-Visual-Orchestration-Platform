#!/bin/bash

cd "$(dirname "$0")"

echo "======================================"
echo "        BNOS Rust Node Starter"
echo "======================================"
echo ""

# ==================== 环境检测与自愈 ====================
echo "🔍 检测 Rust 环境和编译产物..."

if [ ! -f "target/release/9" ]; then
    echo "⚠️ 检测到编译产物缺失"
    echo ""
    echo "🔧 开始自动构建..."
    echo ""
    
    # 检查 Rust 是否安装
    if ! command -v rustc &> /dev/null; then
        echo "❌ Rust 未安装"
        echo "💡 请先安装 Rust: https://rustup.rs/"
        exit 1
    fi
    
    # 构建项目
    cargo build --release
    if [ $? -ne 0 ]; then
        echo ""
        echo "❌ 构建失败"
        exit 1
    fi
    echo ""
    echo "✅ 构建成功"
else
    echo "✅ 编译产物检测通过"
fi

echo ""
echo "✅ 启动监听程序..."
echo ""
./target/release/9_listener
