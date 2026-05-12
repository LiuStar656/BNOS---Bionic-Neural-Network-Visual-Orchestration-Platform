# 9

BNOS (Bionic Neural Network Operating System) Rust 节点

## 功能特性

- **高性能**: 基于 Rust 语言，比 Python 快 10-100 倍
- **内存安全**: 编译器保证内存安全，无数据竞争
- **自愈能力**: 自动检测环境并修复缺失的编译产物
- **灵活配置**: 通过 config.json 进行配置
- **持续监听**: 自动监控数据文件变化并处理

## 项目结构

```
9/
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
./target/release/9_listener

# 直接运行主程序（单次处理，需要传入 JSON 数据）
./target/release/9 '{"data": "your_input"}'
```

## 配置说明

编辑 `config.json` 文件：

```json
{
  "node_name": "9",
  "listen_upper_file": "../data/upper_data.json",
  "output_file": "./output.json",
  "filter": {},
  "output_type": ""
}
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
fn process(data: &serde_json::Value) -> Option<serde_json::Value> {
    // 在此实现你的业务逻辑
    // 例如：数据转换、计算、API 调用等
    
    // 示例：提取并处理数据
    let input = data.get("data")?;
    
    // 进行处理...
    let result = /* 你的处理逻辑 */;
    
    Some(result)
}
```

### 添加依赖

在 `Cargo.toml` 中添加依赖：

```toml
[dependencies]
serde = { version = "1.0", features = ["derive"] }
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
{
  "filter": {
    "type": "sensor_data",
    "priority": "high"
  }
}
```

只有当输入数据同时满足所有过滤条件时才会被处理。

## 日志

运行日志保存在 `logs/listener.log` 文件中。

查看日志：
```bash
# Linux/macOS
tail -f logs/listener.log

# Windows
type logs\listener.log
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
echo. > logs\listener.log
```

## 性能优化

发布模式已启用以下优化：
- 最高优化级别 (`opt-level = 3`)
- 链接时优化 (`lto = true`)
- 代码去重 (`codegen-units = 1`)
- 符号剥离 (`strip = true`)

## 许可证

本项目属于 BNOS 生态系统的一部分。
