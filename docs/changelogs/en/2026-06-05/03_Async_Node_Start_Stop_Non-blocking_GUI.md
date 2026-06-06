# 🔧 Async Node Start/Stop, Non-blocking GUI

## 🔧 Async Node Start/Stop, Non-blocking GUI (2026-06-05)

### Problem Description

**GUI unresponsive when starting/stopping nodes**
- **Problem**: When starting or stopping nodes, the operation is synchronous and blocking, causing the entire GUI to become unresponsive
- **Impact**: Users cannot perform other operations during node start/stop, resulting in poor experience

### Fix Solution

**Async Start/Stop Mechanism**

1. **Single node operation async**
   - Immediately update UI status (show "Starting..." or "Stopping...")
   - Execute start/stop operation asynchronously in background
   - Update final status after operation completes

2. **Batch operation one by one**
   - One operation prompt "Starting/Stopping N nodes..."
   - Start/stop one node every 100ms
   - Display summary after all complete

### Technical Implementation

```python
def start_selected_node_by_name(self, node_name):
    """Start node (async)"""
    # Immediately show starting status
    self.node_list_panel.update_node_status(node_name, 'idle')
    self.show_toast("Starting node...", "info")
    
    # Execute start async
    QTimer.singleShot(10, lambda: self._start_node_async(node_name))

def _start_node_async(self, node_name):
    """Async start node (internal method)"""
    success, err = start_node_process(node_info)
    
    # Update UI in main thread
    def on_complete():
        if success:
            self.show_toast("Node started", "success")
        else:
            self.show_toast("Start failed: " + err, "error")
    
    QTimer.singleShot(10, on_complete)
```

### Modified Files

- `ui/main_window.py` - Added `_start_node_async`, `_stop_node_async` methods
- `ui/panels/node_list_panel.py` - Modified `batch_start_nodes`, `batch_stop_nodes` methods
- `ui/panels/node_list_dock.py` - Modified `batch_start_nodes`, `batch_stop_nodes` methods
- `ui/core/strings_cn.json` - Added "_k_node_starting", "_k_node_stopping" translations
- `ui/core/strings_en.json` - Added "_k_node_starting", "_k_node_stopping" translations

### Acceptance Criteria

✅ GUI can respond normally when starting nodes
✅ GUI can respond normally when stopping nodes
✅ GUI does not block during batch start/stop
✅ Display transition status prompts like "Starting...", "Stopping..."

---