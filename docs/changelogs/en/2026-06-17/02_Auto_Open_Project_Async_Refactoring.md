# Auto-Open Project Async Refactoring (Unified timing with project_open)

---

## Problem Description

### Symptom
```
[23:52:23] INFO  (state.py): Auto-open last project: C:\Users\Lenovo\2
[23:52:24] INFO  (canvas_host.py): [CanvasHost] Check before canvas creation: parent_window=OK, nodes_data=0 nodes
[23:52:24] INFO  (canvas_layout.py): [load_layout] Read canvas_layout.json: 0 node positions
```

- **Key Issue**: `nodes_data=0 nodes`
- When `add_canvas_dock` is called, Worker is still scanning the disk in the background
- `load_layout` reads 0 nodes from `canvas_layout.json` (or node info is empty)
- User sees an empty canvas after restart

### User Feedback
> "After opening the app for the first time, the canvas layout doesn't load normally, but when I open other projects the second time, their canvas layouts load correctly"

---

## Root Cause Analysis

### Call Chain Comparison

```
# ============================================================
# Path A: User manually opens a project (project_open) — ✅ OK
# ============================================================

project_open(path)
  └─ Worker = ProjectLoadWorker(path)    ← Background thread starts disk scan
       └─ Worker.finished.connect(
           _on_finished(nodes_data, ...)
             │
             ├─ nodes_data.clear()       ← Populate data first
             ├─ for name, info: nodes_data[name] = info
             │
             └─ add_canvas_dock(...)     ← Then create canvas
                    └─ load_layout()     ← Read canvas_layout.json
                                             (nodes_data now populated)
```

```
# ============================================================
# Path B: Auto-open on startup (_auto_open_project) — ❌ Broken
# ============================================================

_auto_open_project(path)   ← Before fix
  ├─ project_refresh(self, async_mode=False)   ← Actually still async!
  │     └─ Worker = ProjectLoadWorker(path)   ← Worker running in background...
  │                                                 hasn't returned yet
  │
  └─ self._canvas_host.add_canvas_dock(...)     ← ← ← Immediately creates canvas!
          └─ load_layout()                          nodes_data = {} at this point
                 └─ canvas_layout.json reads 0 node positions
```

### Problem Source: `project_refresh`'s `async_mode` parameter is ignored

```python
# ui/core/project_manager.py
#
# Even passing async_mode=False, project_refresh still launches async Worker
# When Worker's finished signal fires, _auto_open_project already created the canvas
#
# Call timing (top to bottom):
#
#   t=0  _auto_open_project called
#   t=1  project_refresh(async_mode=False) launches Worker
#   t=2  add_canvas_dock() creates canvas
#   t=3  load_layout() reads canvas_layout.json → 0 nodes
#   t=4  Worker finishes scan, emits finished signal ← Too late!
```

### Why does the second project open normally?

```
# When opening the second project:
#   1. App already running
#   2. project_open() follows "correct Path A"
#   3. Worker.finished callback populates nodes_data first, then creates canvas
#   4. Canvas loads correctly
#
# Only "auto-open last project on startup" uses Path B (_auto_open_project)
# That's why "first app open fails, other projects after are OK"
```

---

## Fix Plan

### Core Principle
> **`_auto_open_project` uses the exact same async pattern as `project_open`**

### Changes

#### Change 1: Refactor `_auto_open_project` method

```python
# ui/main_window/state.py

def _auto_open_project(self, project_dir):
    """Internal method: auto-open specified project

    Uses the same async pattern as project_open: scans nodes in background first,
    then creates canvas and restores layout after scan completes.
    Ensures nodes_data is populated before add_canvas_dock is called.
    """
    # Validate project validity...

    # ✅ Key: reset state first + clean up old docks
    if hasattr(self, '_canvas_host') and self._canvas_host:
        self._canvas_host.remove_canvas_dock_by_path(project_dir)

    # ✅ Worker background scan (exactly like project_open)
    from ui.core.project_load_worker import ProjectLoadWorker
    worker = ProjectLoadWorker(project_dir, parent=self)

    # ✅ Worker callback: populate nodes_data first, then create canvas
    def _on_finished(nodes_data, mounted_nodes, running_nodes):
        # 1. Populate data first (consistent with project_open._on_finished)
        self.nodes_data.clear()
        for name, info in nodes_data.items():
            self.nodes_data[name] = info

        # 2. Then create canvas (nodes_data now populated)
        if hasattr(self, '_canvas_host'):
            self._canvas_host.add_canvas_dock(project_name, project_dir)

            # 3. Restore canvas state (splitter positions, etc.)
            from ui.core.window_state_manager import restore_canvas_host_state
            QTimer.singleShot(200, lambda: restore_canvas_host_state(self))

            # 4. Unified UI update
            from ui.core.project_manager import _apply_after_refresh
            _apply_after_refresh(self, running_nodes)

        # 5. Save project to config
        self.app_config.set("last_project", self.current_project_path)
        self.app_config.save()

        # 6. Refresh node list panel
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            if hasattr(self.node_list_panel, 'update_node_list'):
                self.node_list_panel.update_node_list(self.nodes_data)

    # ✅ Failure callback
    def _on_failed(err_msg):
        logger.error(f"[auto_open] Project scan failed: {err_msg}")
        self.show_toast(f"Failed to open project: {err_msg}", "error")

    # ✅ Connect signals and start
    worker.progress.connect(_on_progress)
    worker.finished.connect(_on_finished)
    worker.failed.connect(_on_failed)
    worker.start()
```

#### Change 2: `CanvasHost` adds `remove_canvas_dock_by_path`

```python
# ui/core/canvas_host.py

def remove_canvas_dock_by_path(self, project_path):
    """Remove canvas dock by project path

    Prevents dock residue when reopening the same project.
    """
    if not project_path:
        return

    normalized_path = os.path.normpath(os.path.abspath(project_path))
    docks_to_remove = []

    # Find all matching docks
    for dock in self._canvas_docks:
        content = dock.get_content_widget()
        if isinstance(content, NodeCanvas):
            canvas_data = self.get_canvas_data(content)
            canvas_project_path = canvas_data.get('project_path')
            if canvas_project_path:
                if os.path.normpath(os.path.abspath(canvas_project_path)) == normalized_path:
                    docks_to_remove.append(dock)

    # Safe removal
    for dock in docks_to_remove:
        try:
            self.removeDockWidget(dock)
            dock.setParent(None)
            dock.deleteLater()
            if dock in self._canvas_docks:
                self._canvas_docks.remove(dock)
            # Clean up references in canvas_data_map
            for key in list(self._canvas_data_map.keys()):
                try:
                    if key == dock or (hasattr(dock, 'get_content_widget') and
                                       key == dock.get_content_widget()):
                        del self._canvas_data_map[key]
                except Exception:
                    pass
            logger.info(f"[CanvasHost] Removed canvas dock: {project_path}")
        except Exception as e:
            logger.warning(f"[CanvasHost] Failed to remove canvas dock: {e}")
```

---

## Fixed Call Timing

```
# ============================================================
# Path B after fix: auto-open project on startup — ✅ OK
# ============================================================

_auto_open_project(path)   ← t=0
  │
  └─ remove_canvas_dock_by_path(path)   ← Clean old docks (if any)
  │
  └─ Worker = ProjectLoadWorker(path)
        │
        ├─ Worker background scan...   ← t=1 ~ t=3 (1000ms)
        │     └─ 6 nodes scanned
        │     └─ Node registry synced
        │
        └─ Worker.finished.emit(nodes_data, ...)   ← t=4 (back to main thread)
              │
              ├─ self.nodes_data.clear()
              ├─ for name, info: self.nodes_data[name] = info
              │
              ├─ add_canvas_dock(...)                ← t=4
              │     └─ load_layout()
              │         └─ canvas_layout.json reads M nodes ✓
              │
              ├─ restore_canvas_host_state(self)      ← t=4.2
              ├─ _apply_after_refresh(...)
              └─ node_list_panel.update_node_list(self.nodes_data)
```

---

## Log Comparison

### Before fix (broken)
```
[auto_open] Starting project scan: C:\Users\Lenovo\2
[CanvasHost] Check before canvas creation: parent_window=OK, nodes_data=0 nodes
[CanvasHost] Calling canvas.load_layout(C:\Users\Lenovo\2)
[load_layout] Read canvas_layout.json: 0 node positions
[load_layout] Node creation complete: restored from layout=0, canvas has=0 nodes
[project_load_worker.py] Project loaded, total 6 nodes, 0 running in background ← Too late!
```

### After fix (correct)
```
[auto_open] Starting project scan: C:\Users\Lenovo\2
[auto_open] Scan progress: 100% - Load complete
[auto_open] Worker finished, found 6 nodes
[auto_open] nodes_data populated (6 nodes), creating canvas
[CanvasHost] Check before canvas creation: parent_window=OK, nodes_data=6 nodes
[CanvasHost] Calling canvas.load_layout(C:\Users\Lenovo\2)
[load_layout] Read canvas_layout.json: 2 node positions, 0 edges
[load_layout] Restored from layout: python_node_1 (pos: 380, -140)
[load_layout] Restored from layout: node_rust_2 (pos: 0, 0)
[load_layout] Node creation complete: restored from layout=2, canvas has=2 nodes
[load_layout] Canvas node diagnosis:
  python_node_1: pos=(380,-140) visible=True z=2
  node_rust_2: pos=(0,0) visible=True z=2
```

---

## Modified Files List

| File | Method/Area | Change |
|------|-------------|--------|
| `ui/main_window/state.py` | `_auto_open_project` | Fully refactored to `ProjectLoadWorker` async pattern; `finished` callback populates `nodes_data` before creating canvas |
| `ui/core/canvas_host.py` | `remove_canvas_dock_by_path` | New method: cleans canvas docks by project path |
| `ui/core/canvas_host.py` | `_remove_blank_placeholder` | Added transparent central placeholder widget (see `01_Canvas_Layout_Loading_Fix.md`) |
| `ui/core/canvas_host.py` | `_create_canvas_dock` | Explicit `show()` / `raise_()` / `setFocus()` at end (see `01_Canvas_Layout_Loading_Fix.md`) |

---

## Verification Methods

### Test 1: First startup auto-open project
```
1. Ensure app_config.json last_project points to a valid project
2. Ensure project's canvas_layout.json contains node position information
3. Start application
4. Check logs: nodes_data=6 nodes (not 0)
5. Visual check: canvas shows nodes recorded in canvas_layout.json
```
**Expected**: ✅ Canvas loads nodes correctly

### Test 2: Project without canvas_layout.json
```
1. Delete project's canvas_layout.json
2. Restart application
3. Logs: canvas_layout.json doesn't exist, canvas starts empty
4. Canvas is empty but Node List Panel shows all project nodes
5. Drag 1 node from panel to canvas
6. 500ms later canvas_layout.json is created (see `03_Node_Add_Remove_Auto_Save_Trigger.md`)
7. Restart → node displays on canvas
```
**Expected**: ✅ Manually dragged node saved, restored after restart

### Test 3: Manual project open path (regression test)
```
1. Start application
2. Open another project via menu "Open Project"
3. Canvas displays that project's nodes correctly
```
**Expected**: ✅ Consistent with "correct Path A" behavior before fix

### Test 4: Reopen same project
```
1. Open project A
2. Open project A again
3. Canvas dock not duplicated
4. Canvas correctly shows project A's nodes
```
**Expected**: ✅ No duplicate docks, node layout correct

### Test 5: Syntax verification
```
python -c "import ast; ast.parse(open('ui/main_window/state.py').read()); print('OK')"
python -c "import ast; ast.parse(open('ui/core/canvas_host.py').read()); print('OK')"
```
**Expected**: ✅ Both files output OK

---

## Key Design Decisions

### Decision 1: `_auto_open_project` and `project_open` use the exact same pattern
- **Reason**: Two paths should behave consistently; avoid maintaining separate logic that drifts
- **Impact**: Slight code duplication, but logic is clear and easy to maintain
- **Rollback**: If decoupling is needed later, extract `_on_finished` callback as standalone function

### Decision 2: Add `remove_canvas_dock_by_path` instead of dedup check in dock creation
- **Reason**: Explicit cleanup is easier to understand and debug than implicit dedup; method name clearly expresses intent
- **Impact**: One more method, but reduced complexity of dock management
- **Rollback**: Can always remove this method and instead check inside `add_canvas_dock`

### Decision 3: Keep all subsequent UI updates in Worker callback (restore state, refresh panel, etc.)
- **Reason**: Must execute after Worker completes; otherwise you'd see the same "nodes_data not populated during state restore" class of issues
- **Impact**: Callback function is longer, but guarantees correct timing
- **Rollback**: If callback grows too large, split into multiple helper functions
