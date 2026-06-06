# 🔧 Node Config Dialog Stays Open After Start

## 🔧 Node Config Dialog Stays Open After Start (2026-06-05)

### Fixed Issue

**Node config dialog closes automatically after starting node**
- **Problem**: After clicking "Start Node" button, the config dialog closes automatically, requiring user to reopen it for subsequent operations
- **Cause**: Missing status persistence and update mechanism
- **Fix**: Added status display label, subscribed to status change signal, ensured dialog stays open

### Feature Improvements

**Real-time Status Display**
- Added status display label in node info card
- Subscribed to `polling_manager.node_status_changed` signal
- Real-time status update (running/idle/stopped)

**Dialog Stays Open**
- Dialog stays open after starting node, updates status display
- Dialog stays open after stopping node, updates status display
- User can continue operating in the dialog

### Modified Files

- `ui/dialogs/node_config_dialog.py` - Added status display and signal subscription

### Technical Implementation

```python
# Subscribe to status change signal
polling_manager.node_status_changed.connect(self._on_node_status_changed)

# Status display update
def _update_status_display(self):
    status = node_data.get('status', 'unknown')
    if status == 'running':
        self._status_label.setText("状态: ● 运行中")
        self._status_label.setStyleSheet("color: #FF4444;")
    elif status == 'idle':
        self._status_label.setText("状态: ● 空闲")
        self._status_label.setStyleSheet("color: #44FF44;")
    else:
        self._status_label.setText("状态: ○ 已停止")
        self._status_label.setStyleSheet("color: gray;")

# Update status after starting node (dialog stays open)
def start_node(self):
    self.parent_window.start_selected_node_by_name(self.node_name)
    self._update_status_display()  # Update status, don't close dialog
```

### Acceptance Criteria

✅ After clicking "Start Node", config dialog stays open
✅ Dialog shows node status update (status indicator changes)
✅ User can continue operating in the dialog (stop node, view logs, etc.)
✅ User can manually close dialog by clicking close button
✅ When start fails, dialog stays open and shows error message

---