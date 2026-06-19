# 04_IPC Core Process Command Expansion

**Date**: 2026-06-20

## Background

`CoreProcessApp` (`ui/core/core_process.py`) is the IPC communication bridge between the main process and core business process in BNOS architecture. Before this update, its `_on_message` command dispatch dictionary supported limited commands, lacking batch node operations and running state awareness.

## Changes

### New Commands

Added two new commands to the `_on_message` dispatch dictionary:

```python
def _on_message(self, msg):
    action = msg.get("action")
    params = msg.get("params", {})

    command_map = {
        # ... existing commands ...
        "node.stop_all": self._handle_stop_all_nodes,
        "node.detect_running": self._handle_detect_running_nodes,
    }
```

### `node.stop_all` — Batch Stop All Nodes

```python
def _handle_stop_all_nodes(self, params=None):
    """Iterate all registered running nodes and stop each one"""
    stopped = []
    from ui.core.node_process import stop_node_process
    for node_name, node_info in self._nodes.items():
        if node_info.get("running", False):
            stop_node_process(node_name, node_info.get("path", ""))
            stopped.append(node_name)
    return {"stopped": stopped, "count": len(stopped)}
```

**Design notes**:
- Only processes nodes in `running` state
- Calls `stop_node_process` individually for clean shutdown
- Returns full list and count of stopped nodes

### `node.detect_running` — Running State Detection

```python
def _handle_detect_running_nodes(self, params=None):
    """Scan all nodes, return currently running node list"""
    running = [name for name, info in self._nodes.items()
               if info.get("running", False)]
    return {"running": running, "count": len(running)}
```

## Use Cases

| Command | Trigger Scenario |
|---------|-----------------|
| `node.stop_all` | Project close, batch stop, ShutdownOrchestrator graceful exit |
| `node.detect_running` | Startup auto-recovery, status panel refresh, cross-session PID detection |

## Impact

- **Modified**: `ui/core/core_process.py`
- **New methods**: `_handle_stop_all_nodes()`, `_handle_detect_running_nodes()`
- **Backward compatible**: ✅ Only extends dispatch, no impact on existing commands
