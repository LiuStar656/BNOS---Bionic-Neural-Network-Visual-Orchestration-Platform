# Node Add/Remove Auto-Save Trigger (Prevent losing manually dragged nodes after restart)

---

## Problem Description

### Symptom 1: Dragging nodes from Node List Panel to canvas doesn't save
```
1. User drags a node from Node List Panel to canvas (calls add_node_to_canvas)
2. Node displays correctly on canvas
3. Wait 500ms, check canvas_layout.json — node position not written!
4. Restart app — node not on canvas
```

### Symptom 2: Removing nodes from canvas doesn't save
```
1. User selects a node on canvas, press Delete or context menu remove
2. Node disappears from canvas
3. canvas_layout.json not updated
4. Restart app — node reappears on canvas (never truly removed)
```

### Symptom 3: Subprocess mode parameter mismatch
```
# Call in canvas_process.py
self.canvas.add_node_to_canvas(node_name, info)
                                       ↑
                                      2nd parameter

# But canvas_view.py definition accepts only 1 parameter
def add_node_to_canvas(self, node_name):
    ...

# Result: TypeError: add_node_to_canvas() takes 2 positional arguments but 3 were given
```

---

## Root Cause Analysis

### Root Cause 1: `add_node_to_canvas` doesn't call save logic

```python
# Before fix
def add_node_to_canvas(self, node_name):
    # ... create NodeItem
    node = NodeItem(node_name, language, status, x, y, 140, 80, self)
    self.scene.addItem(node)
    self.nodes[node_name] = node

    # Auto-record command (for history rollback)
    self._record_create_node(node_name)

    # ❌ Never triggers _save_timer!
    # ❌ canvas_layout.json never updated
```

- `_save_timer` is a `QTimer` that fires on node drag, zoom, etc.
- `_save_timer.start(500)` means "call _auto_save_layout() after 500ms"
- `_save_timer.stop()` is for debouncing (continuous operations only save once
- `add_node_to_canvas` just created the node and added it to scene but never told the system "there's a change needing save

### Root Cause 2: `remove_node_from_canvas` also doesn't call save logic

```python
# Before fix
def remove_node_from_canvas(self, node_name):
    if node_name not in self.nodes:
        return

    node = self.nodes[node_name]

    # Delete related edges
    edges_to_remove = [...]
    for edge in edges_to_remove:
        self.remove_edge(edge)

    # Remove node
    self.scene.removeItem(node)
    del self.nodes[node_name]

    # ❌ Never triggers _save_timer!
```

### Root Cause 3: Parameter mismatch (subprocess mode)

```python
# canvas_process.py - In subprocess mode, node info passed as parameter
def _on_node_added(self, node_name, node_info):
    self.canvas.add_node_to_canvas(node_name, node_info)

# canvas_view.py - But main process mode signature doesn't have this parameter
def add_node_to_canvas(self, node_name):
    # Needs to find node info from self.parent_window.nodes_data
```

- Subprocess mode (`canvas_process.py`) is an independent process receiving node info via IPC messages
- It can't access `self.parent_window.nodes_data` like main process can
- So it passes `node_info` directly when calling `add_node_to_canvas`
- But main process mode's `add_node_to_canvas` only accepts `node_name`

---

## Fix Plan

### Fix 1: `add_node_to_canvas` accepts optional `node_info` parameter and triggers save

```python
# ui/canvas/canvas_view.py

def add_node_to_canvas(self, node_name, node_info=None):
    """Add node to canvas

    Args:
        node_name: Node name
        node_info: Optional node info dict (passed directly in subprocess mode)
                   containing 'path', 'config', 'status' fields
    """
    if node_name in self.nodes:
        themed_message(self, t("k_title_info"), t("k_canvas_node_exists"), "info")
        return

    # Get node info (prefer passed node_info, otherwise read from parent_window)
    if node_info:
        # Subprocess mode: use passed node info directly
        language = self.detect_language(node_info.get('path', ''))
        status = node_info.get('status', 'stopped')
    elif self.parent_window and node_name in self.parent_window.nodes_data:
        # Main process mode: read from nodes_data
        parent_info = self.parent_window.nodes_data[node_name]
        language = self.detect_language(parent_info['path'])
        status = parent_info.get('status', 'stopped')
    else:
        # Fallback: use defaults
        language = "Python"
        status = "stopped"

    # Calculate position...
    # Create node...
    node = NodeItem(node_name, language, status, x, y, 140, 80, self)
    node.on_expand_requested = self.on_expand_requested
    self.scene.addItem(node)
    self.nodes[node_name] = node

    logger.info(f"Node {node_name} added to canvas (pos: {x}, {y})")

    # Auto-record command
    self._record_create_node(node_name)

    # ✅ Trigger auto-save layout (500ms debounce)
    if self.parent_window and self.parent_window.current_project_path:
        self._save_timer.stop()
        self._save_timer.start(500)
```

### Fix 2: `remove_node_from_canvas` triggers save

```python
# ui/canvas/canvas_view.py

def remove_node_from_canvas(self, node_name):
    """Remove node from canvas
    """
    if node_name not in self.nodes:
        return

    node = self.nodes[node_name]

    # Delete related edges
    edges_to_remove = [...]
    for edge in edges_to_remove:
        self.remove_edge(edge)

    # Remove node
    self.scene.removeItem(node)
    del self.nodes[node_name]

    logger.info(f"Node {node_name} removed from canvas")

    # ✅ Trigger auto-save layout (500ms debounce)
    if self.parent_window and self.parent_window.current_project_path:
        self._save_timer.stop()
        self._save_timer.start(500)
```

---

## Modified Files List

| File | Method | Change |
|------|--------|--------|
| `ui/canvas/canvas_view.py` | `add_node_to_canvas(self, node_name)` | Added optional `node_info=None` parameter; prefer passed node_info; triggers `_save_timer.start(500)` at end |
| `ui/canvas/canvas_view.py` | `remove_node_from_canvas(self, node_name)` | Triggers `_save_timer.start(500)` at end; adds operation logging |

---

## Auto-Save Mechanism Explanation

### How `_save_timer` works

```
User Operation              Timer State                    Actual Save
─────────────────────   ────────────────────────   ──────────────────

1. 1st node dragged        _save_timer.start(500)    ← Save after 500ms
                          (timer starts counting)
   |<----- 200ms ---->|

2. 2nd node dragged      _save_timer.stop()         ← Cancel previous timer
                          _save_timer.start(500)     ← Restart 500ms timer
   |<----- 150ms ---->|

3. Node position tweak    _save_timer.stop()
   (mouseMoveEvent)       _save_timer.start(500)   ← Restart 500ms timer
   |<--------- 600ms ------------>|

4. No operation (after 500ms)   Timer expires        _auto_save_layout()
                                                      → save_layout()
                                                      → canvas_layout.json written to disk
```

### Existing save trigger points (not modified this time)

```python
# Following operations already trigger save:
# - mouseMoveEvent(node)       ← On node drag
# - wheelEvent                ← On canvas zoom
# - keyPressEvent(Delete)     ← On keyboard delete
# - Node rename operations
# - closeEvent               ← On window close

# This time added:
# - add_node_to_canvas()     ← ✅ New save trigger
# - remove_node_from_canvas()  ← ✅ New save trigger
```

### `_auto_save_layout` implementation

```python
# (Existing code, shown here for reference)
def _auto_save_layout(self):
    """Auto-save canvas layout (debounced timer callback)"""
    try:
        if self.parent_window and self.parent_window.current_project_path:
            self.save_layout()
            logger.info("[auto_save] Canvas layout auto-saved")
    except Exception as e:
        logger.warning(f"Auto-save canvas layout failed: {e}")
```

---

## Verification Methods

### Test 1: Save after dragging node from Node List Panel

```
1. Start app, open a project (ensure Node List Panel visible)
2. Select 1 node in Node List Panel, double-click or use context menu "Add to Canvas"
3. Watch logs: add_node_to_canvas called
4. Wait 500ms (no other operations)
5. Check canvas_layout.json: should contain just-dragged node position info
6. Restart app
7. Verify: node displays on canvas
```
**Expected**: ✅ Node correctly saved, displays on canvas after restart

### Test 2: Continuous multi-node drag (debounce test)

```
1. Drag 3 nodes from list to canvas within 2 seconds
2. Wait 500ms
3. canvas_layout.json written only once (debounce working)
4. canvas_layout.json contains all 3 nodes
5. Restart → all 3 nodes on canvas
```
**Expected**: ✅ All 3 nodes correctly saved and restored

### Test 3: Remove node from canvas

```
1. Canvas has 3 nodes
2. Select 1 node → context menu "Remove from Canvas" or press Delete
3. Wait 500ms
4. canvas_layout.json updated (that node position info removed)
5. Restart → node not on canvas (but still in Node List Panel)
```
**Expected**: ✅ Node removed from canvas, canvas_layout.json synced

### Test 4: Subprocess mode parameter matching (regression test)

```
1. In subprocess mode, node info passed via IPC message
2. add_node_to_canvas(node_name, info) called
3. No TypeError thrown
4. Node correctly created and saved
```
**Expected**: ✅ No parameter mismatch error

### Test 5: Syntax verification

```
python -c "import ast; ast.parse(open('ui/canvas/canvas_view.py').read()); print('OK')"
```
**Expected**: ✅ File syntax correct

---

## Key Design Decisions

### Decision 1: Use optional parameter `node_info=None` instead of overloaded method
- **Reason**: Python doesn't support true method overloading; one default parameter supports both main process and subprocess modes with one signature
- **Impact**: Method signature slightly more complex, but only one method to maintain
- **Rollback**: If only one mode is ever needed, just remove the parameter

### Decision 2: Reuse `_save_timer` debounce mechanism instead of immediate save
- **Reason**: Consistent with node drag, zoom, etc. save pattern; only save once during continuous operations, reducing disk IO
- **Impact**: User waits 500ms after operation before actual write, but this matches existing behavior
- **Rollback**: For stronger "save now" semantics, could call `self.save_layout()` directly (but cautiously — could generate lots of disk writes)

### Decision 3: Distinguish `remove_node_from_canvas` vs `remove_node_with_cleanup`
- **`remove_node_from_canvas`**: Only removes node from canvas, node still in project (visible in Node List Panel) → only saves layout
- **`remove_node_with_cleanup`**: Deletes node from project, stops process, deletes files → saves layout + runs cleanup
- **Reason**: User has two different deletion intents; need clear distinction
- **Rollback**: If confusing for users, could add confirmation dialog
