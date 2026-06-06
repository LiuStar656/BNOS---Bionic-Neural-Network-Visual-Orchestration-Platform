# 🐍 JSON 启动虚拟环境支持

## 🐍 JSON 启动虚拟环境支持 (2026-06-05)

### 已修复的问题

**JSON 启动无法启动虚拟环境**
- **问题**：通过 JSON 配置启动 Python 节点时，无法正确激活虚拟环境，导致节点启动失败
- **原因**：`python_create_node.py` 生成的 `start.json` 缺少虚拟环境路径配置
- **修复**：在 `start.json` 中添加 `python_exe` 字段，启动器优先使用该配置

### 功能改进

**虚拟环境路径配置**
- 修改 `python_create_node.py`，先创建虚拟环境再生成 `start.json`
- 在 `start.json` 中添加 `python_exe` 字段，记录虚拟环境 Python 解释器的绝对路径

**启动器配置读取**
- 修改 `_python_exe_for_node()` 函数，支持从 `start_config` 参数读取配置
- 优先使用 `start.json` 中配置的路径，未配置时回退到默认路径

**虚拟环境验证**
- 新增 `_validate_venv()` 函数，验证 Python 解释器的有效性
- 检查文件存在性、执行权限、版本兼容性
- 启动前验证，失败时提供明确错误信息

### 修改的文件

- `tools/python_create_node.py` - 在 start.json 中添加 python_exe 字段
- `ui/core/node_process.py` - 支持从 start.json 读取 venv 配置，添加验证机制

### 技术实现

```python
# python_create_node.py - 在 start.json 中添加 python_exe
start_content = {
    "nodes": [
        {
            "name": f"node_python_{node_name}",
            "path": full_node_dir,
            "python_exe": python_exe_path,  # 新增字段
            "config": {...}
        }
    ]
}

# node_process.py - 优先从 start.json 读取配置
def _python_exe_for_node(node_path, start_config=None, node_name=None):
    # 优先从 start_config 中读取 python_exe 配置
    if start_config and 'nodes' in start_config:
        for n in start_config['nodes']:
            if n.get('name') == node_name or n.get('path') == node_path:
                if 'python_exe' in n and n['python_exe']:
                    return os.path.normpath(n['python_exe'])
    # 回退到默认路径
    return os.path.join(node_path, "venv", "Scripts" if os.name == 'nt' else "bin", "python.exe")
```

### 验收标准

✅ `python_create_node.py` 生成的 `start.json` 包含 `python_exe` 字段  
✅ 通过 JSON 配置启动 Python 节点时，能正确激活虚拟环境  
✅ 启动失败时显示清晰的错误信息（如 venv 缺失、Python 版本不兼容）  
✅ 跨平台支持（Windows 10/11、Linux、macOS）

---