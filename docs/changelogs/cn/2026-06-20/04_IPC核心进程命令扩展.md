# 04_IPC 核心进程命令扩展

**日期**: 2026-06-20

## 背景

`CoreProcessApp`（`ui/core/core_process.py`）是 BNOS 架构中主进程与核心业务进程间的 IPC 通信桥梁。在本次更新前，其 `_on_message` 方法的命令分发字典支持有限的命令，缺少批量节点操作和运行状态感知能力。

## 变更内容

### 新增命令

在 `_on_message` 的命令分发字典中新增两条命令：

```python
def _on_message(self, msg):
    action = msg.get("action")
    params = msg.get("params", {})

    command_map = {
        # ... 已有命令 ...
        "node.stop_all": self._handle_stop_all_nodes,        # 新增
        "node.detect_running": self._handle_detect_running_nodes,  # 新增
    }
```

### `node.stop_all` — 批量停止所有节点

```python
def _handle_stop_all_nodes(self, params=None):
    """遍历所有 registered running 节点并逐个停止"""
    stopped = []
    from ui.core.node_process import stop_node_process
    for node_name, node_info in self._nodes.items():
        if node_info.get("running", False):
            stop_node_process(node_name, node_info.get("path", ""))
            stopped.append(node_name)
    return {"stopped": stopped, "count": len(stopped)}
```

**设计要点**：
- 仅处理 `running` 状态的节点
- 逐个调用 `stop_node_process`，确保每个节点被正确清理
- 返回被停止节点的完整列表和计数

### `node.detect_running` — 运行态检测

```python
def _handle_detect_running_nodes(self, params=None):
    """扫描所有节点，返回当前正在运行的节点列表"""
    running = [name for name, info in self._nodes.items()
               if info.get("running", False)]
    return {"running": running, "count": len(running)}
```

## 使用场景

| 命令 | 触发场景 |
|------|---------|
| `node.stop_all` | 项目关闭、批量停止、ShutdownOrchestrator 优雅退出 |
| `node.detect_running` | 启动自动恢复、状态面板刷新、跨会话 PID 检测 |

## 影响范围

- **修改文件**: `ui/core/core_process.py`
- **新增方法**: `_handle_stop_all_nodes()`, `_handle_detect_running_nodes()`
- **向后兼容**: ✅ 仅扩展命令字典，不影响已有命令
