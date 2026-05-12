#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BNOS Rust 节点一键生成脚本（增强版）
用于快速创建新的 Rust 节点项目模板，包含完整的自愈机制和环境管理

使用方法:
    python generate_node.py <node_name>
    python generate_node.py --repair-only <node_dir>
    
参数:
    node_name: 节点名称（必填），将自动生成 node_rust_<node_name> 目录
    --repair-only: 修复模式，仅检测并修复指定节点的编译产物

示例:
    python generate_node.py my_node        # 生成 node_rust_my_node 目录
    python generate_node.py data_processor # 生成 node_rust_data_processor 目录
    python generate_node.py --repair-only ./node_rust_my_node
"""

import os
import sys
import json
import subprocess
import shutil
from pathlib import Path


def check_rust_installed() -> bool:
    """检查 Rust 工具链是否已安装"""
    try:
        result = subprocess.run(
            ["rustc", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_cargo_installed() -> bool:
    """检查 Cargo 是否已安装"""
    try:
        result = subprocess.run(
            ["cargo", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def build_project(node_dir: str) -> bool:
    """构建 Rust 项目"""
    print("[BUILD] 开始构建项目（release 模式）...")
    try:
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=node_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            print("[SUCCESS] 项目构建成功")
            return True
        else:
            print(f"[ERROR] 项目构建失败:")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("[ERROR] 构建超时（超过5分钟）")
        return False
    except Exception as e:
        print(f"[ERROR] 构建异常: {e}")
        return False


def auto_repair_build(node_dir: str) -> bool:
    """
    自动检测并修复编译产物（自愈逻辑）
    在节点启动时调用，检测二进制文件是否缺失/损坏，自动重建
    """
    # 读取配置获取节点名称
    config_path = os.path.join(node_dir, "config.json")
    if not os.path.exists(config_path):
        print("[ERROR] 配置文件不存在")
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    node_name = config.get("node_name", os.path.basename(node_dir))
    
    # 检测1: target/release 目录是否存在
    release_dir = os.path.join(node_dir, "target", "release")
    if not os.path.exists(release_dir):
        print("[WARN] 检测到编译产物缺失，开始自动重建...")
        return build_project(node_dir)
    
    # 检测2: 主程序二进制文件是否存在
    if os.name == "nt":
        main_exe = os.path.join(release_dir, f"{node_name}.exe")
        listener_exe = os.path.join(release_dir, f"{node_name}_listener.exe")
    else:
        main_exe = os.path.join(release_dir, node_name)
        listener_exe = os.path.join(release_dir, f"{node_name}_listener")
    
    if not os.path.exists(main_exe) or not os.path.exists(listener_exe):
        print("[WARN] 检测到二进制文件缺失，开始自动重建...")
        return build_project(node_dir)
    
    # 检测3: 尝试运行二进制文件，检查是否真正可用
    try:
        result = subprocess.run(
            [main_exe, "--help"] if os.name != "nt" else [main_exe],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=node_dir
        )
        # 即使返回非0，只要能运行就说明文件没损坏
        print("[OK] 编译产物检测通过")
        return True
    except Exception:
        print("[WARN] 检测到编译产物损坏，开始自动重建...")
        # 清理损坏的编译产物
        try:
            shutil.rmtree(release_dir, ignore_errors=True)
            print("[OK] 已清理损坏的编译产物")
        except Exception as e:
            print(f"[WARN] 清理失败: {e}")
        return build_project(node_dir)


def create_cargo_toml(node_name: str) -> str:
    """生成 Cargo.toml 文件内容"""
    return f'''[package]
name = "{node_name}"
version = "0.1.0"
edition = "2021"
authors = ["BNOS Developer"]
description = "BNOS Rust Node - {node_name}"

[[bin]]
name = "{node_name}"
path = "src/main.rs"

[[bin]]
name = "{node_name}_listener"
path = "src/listener.rs"

[dependencies]
serde = {{ version = "1.0", features = ["derive"] }}
serde_json = "1.0"
chrono = "0.4"

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
strip = true
'''


def create_main_rs(node_name: str) -> str:
    """生成 src/main.rs 文件内容"""
    return f'''mod packet;

use std::env;
use std::fs;
use packet::OutputPacket;

fn main() {{
    // 获取当前可执行文件所在目录
    let exe_path = env::current_exe().expect("Failed to get executable path");
    let node_dir = exe_path.parent().expect("Failed to get parent directory");
    
    // 读取配置文件
    let config_path = node_dir.join("config.json");
    let config_str = fs::read_to_string(&config_path)
        .unwrap_or_else(|e| {{
            eprintln!("Failed to read config file: {{}}", e);
            std::process::exit(1);
        }});
    
    let config: serde_json::Value = serde_json::from_str(&config_str)
        .unwrap_or_else(|e| {{
            eprintln!("Failed to parse config: {{}}", e);
            std::process::exit(1);
        }});

    // 从命令行参数获取输入数据
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {{
        let error_packet = OutputPacket::error("no input");
        println!("{{}}", serde_json::to_string(&error_packet).unwrap());
        std::process::exit(1);
    }}

    let input_str = &args[1];
    
    // 解析输入数据
    let input_data: serde_json::Value = match serde_json::from_str(input_str) {{
        Ok(data) => data,
        Err(e) => {{
            let error_packet = OutputPacket::error(&format!("Invalid JSON input: {{}}", e));
            println!("{{}}", serde_json::to_string(&error_packet).unwrap());
            std::process::exit(1);
        }}
    }};

    // 调用处理函数
    let result = process(&input_data);

    // 构建输出数据包
    let output_type = config["output_type"].as_str().unwrap_or("");
    
    // 如果需要添加 type 字段
    if !output_type.is_empty() {{
        let mut output_json = serde_json::to_value(OutputPacket::success(result)).unwrap();
        if let Some(obj) = output_json.as_object_mut() {{
            obj.insert("type".to_string(), serde_json::Value::String(output_type.to_string()));
        }}
        println!("{{}}", serde_json::to_string(&output_json).unwrap());
    }} else {{
        println!("{{}}", serde_json::to_string(&OutputPacket::success(result)).unwrap());
    }}
}}

/// 节点核心处理逻辑
/// 
/// # 参数
/// * `data` - 输入的 JSON 数据
/// 
/// # 返回
/// 处理后的数据（Option<serde_json::Value>）
/// 
/// # 示例
/// ```rust
/// // 在此实现你的业务逻辑
/// fn process(data: &serde_json::Value) -> Option<serde_json::Value> {{
///     // 提取数据字段
///     let input = data.get("data")?;
///     
///     // 进行处理...
///     // 例如：数据转换、计算、API 调用等
///     
///     Some(processed_result)
/// }}
/// ```
fn process(data: &serde_json::Value) -> Option<serde_json::Value> {{
    // TODO: 在此实现你的业务逻辑
    // 默认返回输入数据中的 data 字段
    data.get("data").cloned()
}}
'''


def create_listener_rs(node_name: str) -> str:
    """生成 src/listener.rs 文件内容（增强版自愈逻辑）"""
    return '''use std::env;
use std::fs;
use std::path::Path;
use std::process::Command;
use std::thread;
use std::time::Duration;
use chrono::Local;

fn main() {
    println!("Starting {} listener...", env!("CARGO_PKG_NAME"));
    
    // 自愈机制：检查环境
    if !check_and_fix_environment() {
        eprintln!("Environment check failed!");
        std::process::exit(1);
    }
    
    // 读取配置
    let config = read_config();
    
    // 监听并处理数据（循环监听）
    listen_loop(&config);
}

/// 检查并修复环境
fn check_and_fix_environment() -> bool {
    println!("Checking environment...");
    
    // 检查 Rust 工具链
    if !check_rust_installed() {
        eprintln!("Error: Rust is not installed. Please install Rust from https://rustup.rs/");
        return false;
    }
    
    // 检查 Cargo
    if !check_cargo_installed() {
        eprintln!("Error: Cargo is not installed.");
        return false;
    }
    
    // 检查编译产物
    let exe_name = if cfg!(target_os = "windows") {
        format!("{}.exe", env!("CARGO_PKG_NAME"))
    } else {
        env!("CARGO_PKG_NAME").to_string()
    };
    
    if !Path::new(&exe_name).exists() {
        println!("Binary not found, building...");
        if !build_project() {
            eprintln!("Build failed!");
            return false;
        }
    }
    
    println!("Environment check passed.");
    true
}

/// 检查 Rust 是否已安装
fn check_rust_installed() -> bool {
    Command::new("rustc")
        .arg("--version")
        .output()
        .is_ok()
}

/// 检查 Cargo 是否已安装
fn check_cargo_installed() -> bool {
    Command::new("cargo")
        .arg("--version")
        .output()
        .is_ok()
}

/// 构建项目
fn build_project() -> bool {
    println!("Building project in release mode...");
    let status = Command::new("cargo")
        .args(&["build", "--release"])
        .status();
    
    match status {
        Ok(status) => {
            if status.success() {
                println!("Build completed successfully.");
                true
            } else {
                eprintln!("Build failed with status: {:?}", status);
                false
            }
        }
        Err(e) => {
            eprintln!("Failed to execute cargo build: {}", e);
            false
        }
    }
}

/// 读取配置文件
fn read_config() -> serde_json::Value {
    let config_path = "config.json";
    let config_str = fs::read_to_string(config_path)
        .unwrap_or_else(|e| {
            eprintln!("Failed to read config file: {}", e);
            std::process::exit(1);
        });
    
    serde_json::from_str(&config_str)
        .unwrap_or_else(|e| {
            eprintln!("Failed to parse config: {}", e);
            std::process::exit(1);
        })
}

/// 循环监听并处理数据
fn listen_loop(config: &serde_json::Value) {
    let upper_file = config["listen_upper_file"]
        .as_str()
        .unwrap_or("../data/upper_data.json");
    
    let output_file = config["output_file"]
        .as_str()
        .unwrap_or("./output.json");
    
    let node_name = config["node_name"]
        .as_str()
        .unwrap_or("unknown");
    
    let process_flag = format!("_processed_{}", node_name);
    
    println!("Listening to: {}", upper_file);
    println!("Output to: {}", output_file);
    println!("Process flag: {}", process_flag);
    
    log_message(&format!("Node started: {}", node_name));
    log_message(&format!("Listening: {}", upper_file));
    
    loop {
        // 检查输入文件是否存在
        if !Path::new(upper_file).exists() {
            thread::sleep(Duration::from_millis(200));
            continue;
        }
        
        // 读取输入数据
        let data_str = match fs::read_to_string(upper_file) {
            Ok(s) => s,
            Err(e) => {
                log_message(&format!("Error reading input file: {}", e));
                thread::sleep(Duration::from_millis(200));
                continue;
            }
        };
        
        // 解析 JSON
        let mut data: serde_json::Value = match serde_json::from_str(&data_str) {
            Ok(d) => d,
            Err(e) => {
                log_message(&format!("JSON parse error: {}", e));
                thread::sleep(Duration::from_secs(1));
                continue;
            }
        };
        
        // 检查是否已处理
        if let Some(flag) = data.get(&process_flag) {
            if flag.as_bool().unwrap_or(false) {
                thread::sleep(Duration::from_millis(200));
                continue;
            }
        }
        
        // 应用过滤器
        if let Some(filter) = config.get("filter") {
            if !apply_filter(&data, filter) {
                thread::sleep(Duration::from_millis(200));
                continue;
            }
        }
        
        log_message("Processing data...");
        
        // 调用主程序处理
        let exe_name = if cfg!(target_os = "windows") {
            format!("{}.exe", env!("CARGO_PKG_NAME"))
        } else {
            env!("CARGO_PKG_NAME").to_string()
        };
        
        let input_json = serde_json::to_string(&data).unwrap_or_else(|_| "{}".to_string());
        
        let output = Command::new(&exe_name)
            .arg(&input_json)
            .output();
        
        match output {
            Ok(out) => {
                if out.status.success() {
                    let result = String::from_utf8_lossy(&out.stdout);
                    
                    // 写入输出文件
                    if let Err(e) = fs::write(output_file, result.as_ref()) {
                        log_message(&format!("Error writing output: {}", e));
                    } else {
                        log_message("Processing completed successfully");
                        
                        // 标记为已处理
                        if let Some(obj) = data.as_object_mut() {
                            obj.insert(process_flag.clone(), serde_json::Value::Bool(true));
                        }
                        
                        // 更新输入文件
                        if let Ok(updated_json) = serde_json::to_string_pretty(&data) {
                            let _ = fs::write(upper_file, updated_json);
                        }
                    }
                } else {
                    let error = String::from_utf8_lossy(&out.stderr);
                    log_message(&format!("Processing failed: {}", error));
                }
            }
            Err(e) => {
                log_message(&format!("Failed to execute {}: {}", exe_name, e));
            }
        }
        
        thread::sleep(Duration::from_millis(200));
    }
}

/// 应用过滤器
fn apply_filter(data: &serde_json::Value, filter: &serde_json::Value) -> bool {
    // TODO: 实现过滤逻辑
    // 根据 filter 配置决定是否处理该数据
    if let Some(obj) = filter.as_object() {
        for (key, value) in obj {
            if let Some(data_value) = data.get(key) {
                if data_value != value {
                    return false;
                }
            } else {
                return false;
            }
        }
    }
    true
}

/// 记录日志
fn log_message(message: &str) {
    let timestamp = Local::now().format("%Y-%m-%d %H:%M:%S");
    let log_line = format!("[{}] {}", timestamp, message);
    println!("{}", log_line);
    
    // 写入日志文件
    let log_dir = "logs";
    if !Path::new(log_dir).exists() {
        let _ = fs::create_dir_all(log_dir);
    }
    
    let log_file = Path::new(log_dir).join("listener.log");
    if let Ok(mut file) = fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_file)
    {
        use std::io::Write;
        let _ = writeln!(file, "{}", log_line);
    }
}
'''


def create_packet_rs() -> str:
    """生成 src/packet.rs 文件内容"""
    return '''use serde::{Deserialize, Serialize};

/// 输出数据包结构
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutputPacket {
    pub code: i32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl OutputPacket {
    /// 创建成功响应
    pub fn success(data: Option<serde_json::Value>) -> Self {
        Self {
            code: 0,
            data,
            error: None,
        }
    }

    /// 创建错误响应
    pub fn error(msg: &str) -> Self {
        Self {
            code: -1,
            data: None,
            error: Some(msg.to_string()),
        }
    }
}
'''


def create_config_json(node_name: str) -> str:
    """生成 config.json 文件内容"""
    config = {
        "node_name": node_name,
        "listen_upper_file": "../data/upper_data.json",
        "output_file": "./output.json",
        "filter": {},
        "output_type": ""
    }
    return json.dumps(config, indent=2, ensure_ascii=False)


def create_start_bat(node_name: str) -> str:
    """生成 start.bat 文件内容（增强版）"""
    return f'''@echo off
cls
chcp 65001 >nul
echo ======================================
echo        BNOS Rust Node Starter
echo ======================================
echo.
cd /d "%%~dp0"

REM ==================== 环境检测与自愈 ====================
echo 🔍 检测 Rust 环境和编译产物...

if not exist "target\\release\\{node_name}.exe" (
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
target\\release\\{node_name}_listener.exe
echo.
echo ❌ 程序已退出
pause
'''


def create_start_sh(node_name: str) -> str:
    """生成 start.sh 文件内容（增强版）"""
    return f'''#!/bin/bash

cd "$(dirname "$0")"

echo "======================================"
echo "        BNOS Rust Node Starter"
echo "======================================"
echo ""

# ==================== 环境检测与自愈 ====================
echo "🔍 检测 Rust 环境和编译产物..."

if [ ! -f "target/release/{node_name}" ]; then
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
./target/release/{node_name}_listener
'''


def create_gitignore() -> str:
    """生成 .gitignore 文件内容"""
    return '''# Rust
/target/
**/*.rs.bk
Cargo.lock

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Environment
.env

# Build artifacts
*.pdb
*.dll
'''


def create_readme(node_name: str) -> str:
    """生成 README.md 文件内容"""
    return f'''# {node_name}

BNOS (Bionic Neural Network Operating System) Rust 节点

## 功能特性

- **高性能**: 基于 Rust 语言，比 Python 快 10-100 倍
- **内存安全**: 编译器保证内存安全，无数据竞争
- **自愈能力**: 自动检测环境并修复缺失的编译产物
- **灵活配置**: 通过 config.json 进行配置
- **持续监听**: 自动监控数据文件变化并处理

## 项目结构

```
{node_name}/
├── src/
│   ├── main.rs          # 主处理程序
│   ├── listener.rs      # 监听器和自愈逻辑
│   └── packet.rs        # 数据包定义
├── Cargo.toml           # Rust 项目配置
├── config.json          # 节点配置
├── start.bat            # Windows 启动脚本
├── start.sh             # Linux/macOS 启动脚本
├── .gitignore           # Git 忽略配置
└── README.md            # 项目说明
```

## 快速开始

### 前置要求

- Rust 工具链 (rustc, cargo)
- 验证安装: 
  ```bash
  rustc --version
  cargo --version
  ```

### 构建项目

```bash
# 开发模式
cargo build

# 发布模式（推荐生产环境使用）
cargo build --release
```

### 运行节点

#### Windows
```bash
start.bat
```

#### Linux/macOS
```bash
chmod +x start.sh
./start.sh
```

### 手动运行

```bash
# 运行监听器（持续监听模式）
./target/release/{node_name}_listener

# 直接运行主程序（单次处理，需要传入 JSON 数据）
./target/release/{node_name} \'{{"data": "your_input"}}\'
```

## 配置说明

编辑 `config.json` 文件：

```json
{{
  "node_name": "{node_name}",
  "listen_upper_file": "../data/upper_data.json",
  "output_file": "./output.json",
  "filter": {{}},
  "output_type": ""
}}
```

- `node_name`: 节点名称
- `listen_upper_file`: 监听的上级数据文件路径
- `output_file`: 输出文件路径
- `filter`: 过滤规则（键值对匹配）
- `output_type`: 输出数据类型标识

## 开发指南

### 实现业务逻辑

在 `src/main.rs` 中修改 `process` 函数：

```rust
fn process(data: &serde_json::Value) -> Option<serde_json::Value> {{
    // 在此实现你的业务逻辑
    // 例如：数据转换、计算、API 调用等
    
    // 示例：提取并处理数据
    let input = data.get("data")?;
    
    // 进行处理...
    let result = /* 你的处理逻辑 */;
    
    Some(result)
}}
```

### 添加依赖

在 `Cargo.toml` 中添加依赖：

```toml
[dependencies]
serde = {{ version = "1.0", features = ["derive"] }}
serde_json = "1.0"
chrono = "0.4"
# 添加其他依赖...
```

然后运行：
```bash
cargo build
```

### 自定义过滤器

在 `config.json` 中设置过滤规则：

```json
{{
  "filter": {{
    "type": "sensor_data",
    "priority": "high"
  }}
}}
```

只有当输入数据同时满足所有过滤条件时才会被处理。

## 日志

运行日志保存在 `logs/listener.log` 文件中。

查看日志：
```bash
# Linux/macOS
tail -f logs/listener.log

# Windows
type logs\\listener.log
```

## 自愈机制

本节点具备自动修复能力：

1. **环境检测**: 启动时检查 Rust 工具链和编译产物
2. **自动构建**: 发现缺失时自动执行 `cargo build --release`
3. **持续运行**: 监听器会持续监控数据文件变化
4. **错误恢复**: 遇到错误时记录日志并继续运行

## 故障排除

### 编译失败

查看详细错误信息：
```bash
cargo build --verbose
```

常见原因：
- Rust 版本过旧：运行 `rustup update`
- 依赖下载失败：配置国内镜像源
- 代码语法错误：检查错误提示

### 清理构建

```bash
cargo clean
```

### 更新依赖

```bash
cargo update
```

### 日志文件过大

定期清理日志：
```bash
# Linux/macOS
echo "" > logs/listener.log

# Windows
echo. > logs\\listener.log
```

## 性能优化

发布模式已启用以下优化：
- 最高优化级别 (`opt-level = 3`)
- 链接时优化 (`lto = true`)
- 代码去重 (`codegen-units = 1`)
- 符号剥离 (`strip = true`)

## 许可证

本项目属于 BNOS 生态系统的一部分。
'''


def generate_node(node_name: str, output_dir: str = None):
    """生成完整的 Rust 节点项目"""
    
    # 强制使用默认输出目录格式：node_rust_<节点名称>
    output_dir = os.path.join(os.getcwd(), f"node_rust_{node_name}")
    
    print(f"\n{'='*60}")
    print(f"正在生成 Rust 节点项目: {node_name}")
    print(f"输出目录: {output_dir}")
    print(f"{'='*60}\n")
    
    # 创建目录结构
    src_dir = os.path.join(output_dir, "src")
    logs_dir = os.path.join(output_dir, "logs")
    
    os.makedirs(src_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    
    # 生成文件列表
    files = {
        "Cargo.toml": create_cargo_toml(node_name),
        "src/main.rs": create_main_rs(node_name),
        "src/listener.rs": create_listener_rs(node_name),
        "src/packet.rs": create_packet_rs(),
        "config.json": create_config_json(node_name),
        "start.bat": create_start_bat(node_name),
        "start.sh": create_start_sh(node_name),
        ".gitignore": create_gitignore(),
        "README.md": create_readme(node_name),
    }
    
    # 写入文件
    for filename, content in files.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] 创建文件: {filename}")
    
    # 为 start.sh 添加执行权限（在非 Windows 系统上）
    if sys.platform != 'win32':
        start_sh_path = os.path.join(output_dir, "start.sh")
        os.chmod(start_sh_path, 0o755)
        print(f"  [OK] 设置执行权限: start.sh")
    
    print(f"\n{'='*60}")
    print(f"[SUCCESS] 节点项目 '{node_name}' 生成成功！")
    print(f"{'='*60}\n")
    print(f"下一步操作:")
    print(f"  1. 进入项目目录: cd {output_dir}")
    
    # 检查 Rust 环境
    if check_rust_installed():
        print(f"  2. Rust 环境已就绪 [OK]")
        print(f"  3. 构建项目: cargo build --release")
    else:
        print(f"  2. [WARN] 未检测到 Rust 环境")
        print(f"     请先安装 Rust: https://rustup.rs/")
        print(f"  3. 安装后运行: cargo build --release")
    
    print(f"  4. 编辑 src/main.rs 实现你的业务逻辑")
    print(f"  5. 修改 config.json 配置节点参数")
    print(f"  6. 运行节点: {'start.bat' if sys.platform == 'win32' else './start.sh'}")
    print()


def repair_only_mode(node_dir: str):
    """仅修复模式：检测并修复指定节点的编译产物"""
    print(f"\n{'='*60}")
    print(f"[REPAIR] 开始修复节点: {node_dir}")
    print(f"{'='*60}\n")
    
    if not os.path.exists(node_dir):
        print(f"[ERROR] 节点目录不存在: {node_dir}")
        sys.exit(1)
    
    # 检测并修复编译产物
    success = auto_repair_build(node_dir)
    
    if success:
        print(f"\n[SUCCESS] 节点修复完成")
        sys.exit(0)
    else:
        print(f"\n[ERROR] 节点修复失败")
        sys.exit(1)


def main():
    """主函数"""
    # 支持 --repair-only 模式
    if len(sys.argv) >= 3 and sys.argv[1] == "--repair-only":
        node_dir = sys.argv[2]
        repair_only_mode(node_dir)
        return
    
    # 正常创建节点模式
    if len(sys.argv) < 2:
        print("="*60)
        print("    BNOS Rust 节点生成器（增强版）")
        print("="*60)
        print()
        print("用法: python generate_node.py <node_name>")
        print("      python generate_node.py --repair-only <node_dir>")
        print()
        print("示例:")
        print("  python generate_node.py my_node")
        print("  python generate_node.py --repair-only ./node_rust_my_node")
        print()
        
        # 交互式输入
        name = input("输入节点名称: ").strip()
        if not name:
            print("❌ 名称不能为空")
            sys.exit(1)
        
        # 验证节点名称
        if not name.replace('_', '').replace('-', '').isalnum():
            print("错误: 节点名称只能包含字母、数字、下划线和连字符")
            sys.exit(1)
        
        try:
            generate_node(name)
        except Exception as e:
            print(f"错误: 生成节点项目时出错 - {e}")
            sys.exit(1)
        
        input("\n按回车退出...")
    else:
        node_name = sys.argv[1]
        
        # 验证节点名称
        if not node_name.replace('_', '').replace('-', '').isalnum():
            print("错误: 节点名称只能包含字母、数字、下划线和连字符")
            sys.exit(1)
        
        try:
            generate_node(node_name)
        except Exception as e:
            print(f"错误: 生成节点项目时出错 - {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
