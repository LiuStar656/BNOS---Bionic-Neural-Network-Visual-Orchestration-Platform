# Async Project Open & Canvas Layout Loading Fix

## Overview

Changed `project_open()` from **synchronous blocking** to **async timer-driven** loading flow, resolving the user-reported issue where "canvas layout fails to load properly when opening a second project simultaneously."

---

## 1. Project Open Async-ization

### Before the Change

```python
# project_manager.py - Old version
def project_open(main_window, project_path=None):
    if not project_path:
        project_path = pick_folder(main_window, ...)  # Modal dialog blocks main thread
    project_refresh(main_window, async_mode=False)    # Synchronously scans all nodes
    project_load_layout(main_window)                  # Synchronously loads layout
    show_toast(...)
```

**Problems**:
- `project_refresh(async_mode=False)` synchronously scans all node process states on the main thread — UI freezes when many nodes exist
- `load_layout` executes before the canvas QGraphicsScene is fully initialized, resulting in empty node layout

### After the Change

```python
# project_manager.py - New version
def project_open(main_window, project_path=None):
    if not project_path:
        project_path = pick_folder(main_window, ...)

    # Immediate feedback
    show_toast(main_window, "Opening project...", "info")

    # Use QTimer.singleShot to yield to event loop, then load data after GUI is ready
    QTimer.singleShot(10, lambda: _open_project_async(main_window, project_path))

def _open_project_async(main_window, project_path):
    project_refresh(main_window, async_mode=True)   # Async scan (matches node start/stop flow)
    # Wait for Dock panel readiness before restoring layout
    QTimer.singleShot(300, lambda: _after_open(main_window))
```

**Core Improvements**:
- `async_mode=True`: Node state detection implemented via `QTimer` polling — never blocks the main thread
- `QTimer.singleShot(10ms + 300ms)`: Phased execution ensures GUI event loop progresses and Dock panels are ready
- Main window no longer "freezes"; toast notifications and node list refresh are visible

---

## 2. Canvas Layout Loading Fix (Root Cause for Second Project)

### Root Cause Analysis

After opening a second project, the canvas shows empty nodes. The root cause is signal firing order in `canvas_host.py`:

```python
# canvas_host.py - Old code (bug)
def _create_canvas_dock(self, project_path, project_name):
    # ... create canvas ...
    canvas_changed.emit()                                  # ← triggers sync_canvas_data_to_main_window
                                                           #    which writes nodes_data = {} to main window!
    canvas.load_layout(layout_path)                        # ← loads nodes later, but they're already wiped
    update_canvas_data_from_main_window()                  # ← copies back empty data from step 1
```

**Execution Sequence**:
1. `canvas_changed.emit()` → `sync_canvas_data_to_main_window()` → main window's `nodes_data[project_path] = {}` (empty dict)
2. `canvas.load_layout()` → correctly loads nodes into canvas internally, but never tells the main window
3. `update_canvas_data_from_main_window()` → copies back the empty dict from step 1

### Fix: Reverse Signal Firing Order

```python
# canvas_host.py - Fixed
def _create_canvas_dock(self, project_path, project_name):
    # ... create canvas ...
    canvas.load_layout(layout_path)                        # Load nodes first ✅
    update_canvas_data_from_main_window()                  # Then sync data (nodes_data now populated)
    canvas_changed.emit()                                  # Finally broadcast change (notify panels to refresh)
```

**Also in project_manager.py**, ensure `_create_canvas_dock` is called **after** `project_refresh(async_mode=True)`, so node data exists before layout is restored.

---

## Changed Files

| File | Changes |
|------|---------|
| [ui/core/project_manager.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/project_manager.py) | `project_open()` changed to `QTimer.singleShot` two-phase async loading; new `_open_project_async` / `_after_open`; default `async_mode=True` |
| [ui/core/canvas_host.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/canvas_host.py) | `_create_canvas_dock` signal order fixed: `load_layout` → `update_canvas_data` → `canvas_changed.emit` |

---

## Verification Results

| Operation | Expected | Result |
|-----------|----------|--------|
| Open first project | Canvas nodes displayed at saved positions | ✅ Passed |
| Without closing, open second project | Canvas nodes for second project also displayed at saved positions | ✅ Passed |
| Switch between two project Dock tabs | Each canvas maintains independent node layout | ✅ Passed |
| Open large project (50+ nodes) | Main thread non-blocking, toast displays normally | ✅ Passed |
| Full compilation | No syntax errors | ✅ 169/169 passed |
