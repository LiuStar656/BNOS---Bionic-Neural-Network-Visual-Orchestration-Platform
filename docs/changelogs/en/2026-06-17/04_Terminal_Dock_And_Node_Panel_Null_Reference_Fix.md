# Terminal Dock and Node Panel Null Reference Fix (Eliminate all AttributeErrors)

---

## Problem 1: `_terminal_dock` accessed before initialization

### Symptom

```
Traceback (most recent call last):
  File "ui/core/canvas_host.py", line 633, in _update_terminal_on_canvas_change
    if hasattr(self._terminal_dock, 'sync_to_canvas'):
               ^^^^^^^^^^^^^^^^^^^
AttributeError: 'CanvasHost' object has no attribute '_terminal_dock'. Did you mean: '_init_terminal_dock'?
```

### Root Cause Analysis

#### CanvasHost terminal dock initialization timing

```
# CanvasHost initialization flow
# ───────────────────────────────────────────────────────

  t=0  __init__()
        ├─ Create blank buffer layer _blank_placeholder
        ├─ Set style
        │
        │   At this point: self._terminal_dock DOESN'T EXIST!
        │
        └─ Wait for external call...

  t=1  add_canvas_dock(project_name, project_path)  ← First canvas created
        └─ _create_canvas_dock()
             ├─ Create canvas (NodeCanvas)
             ├─ Create canvas_dock (QDockWidget)
             ├─ canvas_dock.setWidget(canvas)
             └─ ✅ len(self._canvas_docks) == 1 → call _init_terminal_dock()
                    └─ self._terminal_dock = TerminalDock(...)
                          ↑
                       Only initialized AFTER "first canvas created"
```

#### `_update_terminal_on_canvas_change` call timing

```
# Canvas switching flow
# ───────────────────────────────────────────────────────

  When user switches canvas tab or a new canvas is created:

  canvas_changed.emit(canvas)   ← Signal fires
       └─ _update_terminal_on_canvas_change(canvas)   ← This method called
              │
              └─ hasattr(self._terminal_dock, 'sync_to_canvas')
                     ↑
                 ❌ If this is the first canvas, and _init_terminal_dock()
                    hasn't finished executing yet → self._terminal_dock doesn't exist!
```

#### Trigger condition

1. App starts auto-opening a project
2. First canvas dock being created → `_canvas_docks` becomes `[dock]`
3. After creation `canvas_changed` signal fires → calls `_update_terminal_on_canvas_change`
4. **But**: `_init_terminal_dock()` might not have finished (depends on Qt signal queue ordering)
5. → `self._terminal_dock` attribute doesn't exist → `AttributeError`

**Simpler explanation**: `_update_terminal_on_canvas_change` tries to access an attribute that hasn't been created yet.

### Fix Plan

#### Fix 1-1: Check attribute existence in `_update_terminal_on_canvas_change`

```python
# ui/core/canvas_host.py

def _update_terminal_on_canvas_change(self, canvas):
    """Update terminal when canvas changes"""
    # ✅ Check terminal was initialized first
    # (_terminal_dock only initialized after first canvas created)
    if not hasattr(self, '_terminal_dock') or self._terminal_dock is None:
        return

    if hasattr(self._terminal_dock, 'sync_to_canvas'):
        self._terminal_dock.sync_to_canvas()
```

#### Fix 1-2 (optional): Pre-initialize in `CanvasHost.__init__`

```python
# ui/core/canvas_host.py

def __init__(self, parent=None):
    super().__init__(parent)
    self._parent_window = parent

    # Pre-initialize (ensures hasattr check always returns True)
    self._terminal_dock = None   # ← Optional preventative init

    # ... rest of init
```

**Note**: This fix uses Fix 1-1 only; Fix 1-2 is available as extra insurance.

---

## Problem 2: `NodeListDockPanel` has no `refresh()` method

### Symptom

```
Traceback (most recent call last):
  File "ui/main_window/state.py", line 310, in _on_finished
    self.node_list_panel.refresh()
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NodeListDockPanel' object has no attribute 'refresh'
```

### Root Cause Analysis

#### NodeListDockPanel's actual refresh method

```python
# ui/panels/node_list_dock.py

class NodeListDockPanel(QWidget, NodeListOperationsMixin, ...):
    """Node list panel (Dock version)"""

    def update_node_list(self, nodes_data):
        """Update node list (tree structure, supports grouping)"""
        # ✅ This IS the actual "refresh" method!
        # - Clear node_tree
        # - Add nodes by group
        # - Update path display
        self.nodes_data = nodes_data
        # ...
        self.path_label.setText(...)

    # ❌ No refresh() method exists!
```

#### Who's calling `refresh()`?

```python
# ui/main_window/state.py - _auto_open_project's _on_finished callback

def _on_finished(nodes_data, ...):
    ...
    # 6. Sync node list panel display
    if hasattr(self, 'node_list_panel') and self.node_list_panel:
        self.node_list_panel.refresh()   # ❌ This method doesn't exist!
```

**Problem**: While refactoring `_auto_open_project`, I added "refresh node list panel" logic but mistakenly called a non-existent method `refresh()`.

**Why wasn't this a problem before?**: Because previously `_auto_open_project` used the synchronous path (`project_refresh(async_mode=False)`) and never explicitly called panel refresh.

### Fix Plan

#### Fix 2-1: Add `NodeListDockPanel.refresh()` convenience method

```python
# ui/panels/node_list_dock.py

class NodeListDockPanel(...):
    # ...

    def refresh(self):
        """Convenience refresh method: reload node list from parent_window.nodes_data

        This method makes NodeListDockPanel's interface consistent with common
        refresh semantics, while also supporting external triggers
        (e.g., from _auto_open_project's callback).
        """
        if self.parent_window and hasattr(self.parent_window, 'nodes_data'):
            self.update_node_list(self.parent_window.nodes_data)
```

#### Fix 2-2: Double-check at call site

```python
# ui/main_window/state.py - _on_finished callback

# 6. Sync node list panel display
if hasattr(self, 'node_list_panel') and self.node_list_panel:
    # ✅ NodeListDockPanel uses update_node_list(nodes_data) to refresh display
    if hasattr(self.node_list_panel, 'update_node_list'):
        self.node_list_panel.update_node_list(self.nodes_data)
    # Or alternatively use the newly added refresh()
    # self.node_list_panel.refresh()
```

**Note**: This fix implements both 2-1 and 2-2 for double insurance.

---

## Modified Files List

| File | Method/Area | Change |
|------|-------------|--------|
| `ui/core/canvas_host.py` | `_update_terminal_on_canvas_change` | Checks `hasattr(self, '_terminal_dock')` first, early return if not initialized |
| `ui/panels/node_list_dock.py` | `NodeListDockPanel` | Added `refresh()` convenience method |
| `ui/main_window/state.py` | `_on_finished` callback | Uses `update_node_list(self.nodes_data)` instead of non-existent `refresh()` |

---

## Verification Methods

### Test 1: `_terminal_dock` uninitialized protection

```
1. Ensure app_config.json last_project points to a valid project
2. Start the application
3. Watch console: no AttributeError: 'CanvasHost' object has no attribute '_terminal_dock'
4. Terminal dock normal (if configured to show terminal)
```
**Expected**: ✅ No crash

### Test 2: `_update_terminal_on_canvas_change` works correctly when switching canvases

```
1. Open 2 projects
2. Switch canvas tabs
3. Watch console: no AttributeError
4. Terminal (if shown) syncs to current project working directory
```
**Expected**: ✅ Switching works

### Test 3: `NodeListDockPanel.refresh()` call works

```
1. Start app (auto-open project)
2. Watch console: no AttributeError: 'NodeListDockPanel' object has no attribute 'refresh'
3. Node List Panel shows all project nodes
```
**Expected**: ✅ Panel displays correctly

### Test 4: Syntax verification

```
python -c "import ast; ast.parse(open('ui/core/canvas_host.py').read()); print('OK')"
python -c "import ast; ast.parse(open('ui/panels/node_list_dock.py').read()); print('OK')"
```
**Expected**: ✅ Both files output OK

### Test 5: Functional test (full path)

```
1. Drag node from list to canvas
2. Remove node from canvas
3. Switch multiple projects
4. Close app → restart
5. Throughout whole process no AttributeError
```
**Expected**: ✅ No crashes during entire flow

---

## Key Design Decisions

### Decision 1: Check `hasattr` in `_update_terminal_on_canvas_change` vs. pre-initialize
- **Reason**: Explicit check is clearer than implicit initialization; caller immediately understands "why nothing happened" (via code comments)
- **Impact**: If subsequent callers access `_terminal_dock`, same check needed (but that's fine — this is the standard defensive programming pattern)
- **Rollback**: Could instead set `self._terminal_dock = None` in `__init__`, then check `if self._terminal_dock is not None`

### Decision 2: Add `refresh()` convenience method (rather than hard-code `update_node_list` call at site)
- **Reason**: `refresh()` is a more generic interface name; other code may use it too; keeps `update_node_list` as underlying implementation
- **Impact**: One more convenience method, but code is cleaner; future changes only need modify `refresh()` implementation
- **Rollback**: If only the call site needs it, could delete `refresh()` method

### Decision 3: Double insurance (both Fix 2-1 + Fix 2-2)
- **Reason**: Even if `refresh()` exists in state.py, adding `hasattr` check prevents similar issues when `NodeListDockPanel` is refactored in the future
- **Impact**: Slightly more code, but much better tolerance for future refactoring
- **Rollback**: If considered redundant, remove the `hasattr` check at the call site
