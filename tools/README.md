# Tools 文件夹

本文件夹包含 BNOS 平台的节点生成器工具。

## 文件说明

- **python_create_node.py**: Python 节点模板生成器
  - 自动创建节点目录结构
  - 配置虚拟环境（venv）
  - 生成标准的 packet.py 和 config.json
  - 支持自愈功能，可修复损坏的虚拟环境

- **rust_create_node.py**: Rust 节点模板生成器
  - 生成完整的 Rust 项目结构
  - 包含 Cargo.toml 配置文件
  - 提供 main.rs 和 packet.rs 模板
  - 自动生成平台特定的启动脚本

## 使用方法

### 通过 GUI 使用
在 BNOS GUI 中创建节点时，系统会自动调用这些生成器。

### 命令行使用

```bash
# 创建 Python 节点
python tools/python_create_node.py my_node_name

# 创建 Rust 节点
python tools/rust_create_node.py my_node_name

# 仅修复 Python 节点的虚拟环境
python tools/python_create_node.py --repair-only ./node_python_my_node
```

## 注意事项

- 节点生成器会在项目根目录下创建 `node_<language>_<name>` 格式的节点文件夹
- Python 节点会自动配置独立的虚拟环境
- Rust 节点需要预先安装 Rust 工具链（rustc 和 cargo）
