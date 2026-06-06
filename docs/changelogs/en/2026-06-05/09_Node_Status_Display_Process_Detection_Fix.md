# 🔧 Node Status Display & Process Detection Fix

## 🔧 Node Status Display & Process Detection Fix (2026-06-05)

### Fixed Issues

**1. Node list status requires manual refresh to display**
- **Problem**: Status indicator in node list does not update properly when node status changes
- **Cause**: Status check only evaluates `status == 'running'`, ignoring 'idle' status (running but no active task)
- **Fix**: Change status check logic to `status in ('running', 'idle')`
- **Modified Files**:
  - `ui/panels/node_list_dock.py`
  - `ui/panels/node_list_panel.py`

**2. Circular node text layout becomes square style after refresh**
- **Problem**: After refreshing nodes, text position on circular nodes changes to square node layout
- **Cause**: `update_display` method hardcodes text positions (15px and h-18px), overriding positions set by circular node style
- **Fix**: Refactor `update_display` method, remove hardcoded text position settings, call `self._style.apply(self)` to reapply style when node name or language changes
- **Modified File**: `ui/canvas/items/node_item.py`

**3. Node unexpectedly exits after GUI restart**
- **Problem**: When exiting GUI with "don't stop nodes" option, nodes continue running in background. After restarting GUI, nodes show "running" first, then exit unexpectedly after a few seconds
- **Cause**: Logic flaw in `check_running_processes()` function. When process scan (PowerShell command) fails, even if recorded PID is still alive, node is incorrectly marked as `stopped` and PID file is deleted
- **Fix**: When process scan fails but PID is still alive, preserve node status instead of forcing it to `stopped`
- **Modified File**: `ui/core/node_process.py`

### Technical Implementation Details

**Node List Status Fix**:
```python
# Before
if status == 'running':
    item.setText(0, f"● {node_name}")
    item.setForeground(0, QColor("green"))

# After
if status in ('running', 'idle'):
    item.setText(0, f"● {node_name}")
    item.setForeground(0, QColor("green"))
```

**Circular Node Text Position Fix**:
```python
# Before
def update_display(self, node_name=None, language=None, status=None):
    w = self.rect().width()
    h = self.rect().height()
    if node_name:
        self.name_text.setPos((w - name_rect.width()) / 2, 15)  # Hardcoded position
    if language:
        self.lang_text.setPos((w - lang_rect.width()) / 2, h - 18)  # Hardcoded position

# After
def update_display(self, node_name=None, language=None, status=None):
    # Only update content, position is determined by style
    if node_name:
        self.name_text.setPlainText(node_name)
    if language:
        self.lang_text.setPlainText(language)
    # Reapply style to update text position
    if node_name or language:
        self._style.apply(self)
```

**Process Detection Logic Fix**:
```python
# Before
if pid is not None and _is_pid_alive(pid):
    pass  # Continue to logic below, mark as stopped

# After
if pid is not None and _is_pid_alive(pid):
    # Process is still running, but process scan didn't find it (may be permission or environment issue)
    # Preserve current status, don't force mark as stopped
    logger.warning("Node %s PID=%d is alive, but process scan found no matching process", name, pid)
    continue  # ← Key fix: preserve node status
```

### Acceptance Criteria

✅ Node status indicator turns green (●) after startup, no manual refresh needed  
✅ Node status indicator turns gray (○) after stopping  
✅ Circular nodes maintain correct text layout and style after refresh  
✅ When exiting GUI with "don't stop nodes", nodes continue running in background  
✅ After restarting GUI, background nodes are correctly detected  
✅ Node status remains "running" or "idle", not incorrectly marked as "stopped"  
✅ PID file is not incorrectly deleted  

---