# 04 Node Running State Protection

## Problem Description

Performing rename or delete operations on running nodes may cause data loss, process exceptions, or resource leaks.

## Fix Solution

### 4.1 Rename Protection

**File**: `ui/panels/node_list_panel.py`

Check node status before renaming. If the node is in `running` or `starting` state, show a toast warning and reject the operation.

**Code Change**:
```python
from ui.core.node.node_process import check_node_not_running

ok, msg = check_node_not_running(old_name, self.nodes_data)
if not ok:
    if self.parent_window:
        self.parent_window.show_toast(msg, "warning")
    return
```

### 4.2 Delete Protection

**File**: `ui/panels/node_list_panel.py`

Check for running nodes among selected nodes before deletion. If any are running, show a confirmation dialog informing the user that deletion will stop these nodes.

**Code Change**:
```python
running = [
    n for n in selected_nodes
    if self.nodes_data.get(n, {}).get("status") in ("running", "starting")
]
if running:
    names = "、".join(running)
    reply = themed_message(
        self,
        "确认删除",
        f"以下 {len(running)} 个节点正在运行中：\n{names}\n\n"
        f"删除将同时停止这些节点。是否继续？",
        "warning2",
    )
    if reply != MSG_ACCEPT:
        return
```

### 4.3 Utility Check Function

**File**: `ui/core/node/node_process.py`

Added `check_node_not_running()` function providing unified running state detection logic.

**Code Change**:
```python
def check_node_not_running(node_name: str, nodes_data: dict) -> tuple[bool, str]:
    node_info = nodes_data.get(node_name, {})
    status = node_info.get("status", "unknown")
    if status in ("running", "starting"):
        return False, f"节点「{node_name}」正在运行中，请先停止后再操作"
    return True, ""
```

## Modified Files

| File | Change |
|------|--------|
| `ui/panels/node_list_panel.py` | Running state check before rename; confirmation dialog for deleting running nodes |
| `ui/core/node/node_process.py` | Added `check_node_not_running()` utility function |

## Verification

After fix:
- ✅ Running nodes cannot be renamed, warning toast shown
- ✅ Confirmation dialog lists all running nodes when deleting
- ✅ User can choose to continue (stop nodes) or cancel

---

**Last Updated**: 2026-07-13
