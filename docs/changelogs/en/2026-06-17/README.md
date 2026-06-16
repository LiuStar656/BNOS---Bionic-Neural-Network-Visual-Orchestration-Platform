# [2026-06-17] V2.0.16 - Canvas Layout Loading Fix, Auto-Open Project Async Refactoring and Node Add/Remove Persistence

---

## Update Summary

**3 core issues resolved in this update**:
1. **Canvas nodes not showing on first app launch** - timing issue: `load_layout()` executes before `nodes_data` is populated
2. **Nodes dragged to canvas not being saved** - `add_node_to_canvas` and `remove_node_from_canvas` did not trigger auto-save
3. **Null reference crashes** - `_terminal_dock` accessed before initialization, `NodeListDockPanel` missing `refresh()` method

---

## Update List

### 1. Canvas Layout Loading Fix (try/finally protection + Scene/Viewport force refresh)

[Detailed content](./01_Canvas_Layout_Loading_Fix.md)

- **`load_layout` lifecycle protection**: Wrap all loading logic with `try/finally` to ensure `setUpdatesEnabled(True)` is always called, regardless of exceptions
- **Force Scene/Viewport refresh**: In `finally` block, call `self.scene.update(self.scene.sceneRect())` + `self.viewport().update()` to ensure newly added nodes/edges render immediately
- **Detailed diagnostic logging**: After loading completes, output node count, position, size, visibility, and z-value for easier rendering layer debugging
- **Logic correction**: Removed logic that auto-created canvas nodes from `nodes_data` - canvas nodes should only come from `canvas_layout.json` (user manually dragged/positioned)

---

### 2. Auto-Open Project Async Refactoring (Same timing as project_open)

[Detailed content](./02_Auto_Open_Project_Async_Refactoring.md)

- **Root cause diagnosis**: Previously `_auto_open_project` called `project_refresh(async_mode=False)` then **immediately** created the canvas, but Worker scanned disk in the background → `nodes_data` was still empty → `canvas_layout.json` read 0 node positions
- **Async refactoring**: Changed to use the exact same `ProjectLoadWorker` pattern as `project_open` — Worker background scan → `finished` signal returns to main thread → populate `nodes_data` → create canvas → `load_layout` → restore state
- **New method `remove_canvas_dock_by_path`**: `CanvasHost` now supports removing canvas docks by project path to prevent residual docks when reopening the same project
- **Correct call chain**: `Worker.scan → nodes_data populated → add_canvas_dock → load_layout → restore_state`

---

### 3. Node Add/Remove Auto-Save Trigger (Prevent losing manually dragged nodes after restart)

[Detailed content](./03_Node_Add_Remove_Auto_Save_Trigger.md)

- **`add_node_to_canvas` extension**: Added optional parameter `node_info` (passed directly in subprocess mode), resolving `TypeError` caused by parameter mismatch in `canvas_process.py.add_node_to_canvas(node_name, info)`
- **Save trigger**: After adding a node to canvas, execute `_save_timer.stop()` / `_save_timer.start(500)` to trigger debounced auto-save to `canvas_layout.json`
- **Node removal save**: `remove_node_from_canvas` also triggers `_save_timer` debounced save after completion
- **Operation logging**: Node operations logged for tracking canvas changes

---

### 4. Terminal Dock and Node Panel Null Reference Fix (Eliminate all AttributeErrors)

[Detailed content](./04_Terminal_Dock_And_Node_Panel_Null_Reference_Fix.md)

- **`_terminal_dock` uninitialized protection**: `_update_terminal_on_canvas_change` now first checks `hasattr(self, '_terminal_dock')`, returns early if not initialized (before first canvas is created)
- **`NodeListDockPanel.refresh()` added**: Convenience method to reload node list from `self.parent_window.nodes_data`, ensuring panel refresh after `_auto_open_project` works correctly

---

## Main Updates

| Category | Update Content |
|----------|----------------|
| **Canvas Loading** | `load_layout` try/finally protection; scene/viewport force refresh; detailed diagnostic logs; nodes only from `canvas_layout.json` |
| **Async/Concurrency** | `_auto_open_project` changed to `ProjectLoadWorker` signal pattern; `CanvasHost.remove_canvas_dock_by_path()` new method |
| **Persistence** | `add_node_to_canvas` / `remove_node_from_canvas` now trigger `_save_timer.start(500)` debounced save |
| **Bug Fixes** | `CanvasHost._terminal_dock` uninitialized protection; `NodeListDockPanel` missing `refresh()` method; `add_node_to_canvas` parameter mismatch |
| **Code Quality** | All modified files verified with `ast.parse` syntax check; no new `AttributeError`s |

---

## Modified Files List

| File | Changes |
|------|---------|
| `ui/canvas/canvas_layout.py` | `load_layout` adds try/finally; scene/viewport force refresh; diagnostic logs; removed nodes_data auto-create logic |
| `ui/core/canvas_host.py` | `_remove_blank_placeholder` adds transparent central widget; canvas dock explicit show; new `remove_canvas_dock_by_path`; `_update_terminal_on_canvas_change` null reference protection |
| `ui/main_window/state.py` | `_auto_open_project` fully refactored to `ProjectLoadWorker` async mode; `node_list_panel.refresh()` replaced with `update_node_list()` |
| `ui/canvas/canvas_view.py` | `add_node_to_canvas` accepts optional `node_info` parameter; triggers `_save_timer` after node add/remove |
| `ui/panels/node_list_dock.py` | New `refresh()` convenience method |

---

## Verification Results

- ✅ `ast.parse` syntax verification: all 5 modified files pass
- ✅ Auto-open project on launch: canvas nodes display correctly (no longer empty)
- ✅ Drag node from panel to canvas: `canvas_layout.json` auto-updates after 500ms
- ✅ Remove node from canvas: `canvas_layout.json` sync-updated; node not on canvas after restart (but still in node list panel)
- ✅ `_terminal_dock` null reference: no `AttributeError`
- ✅ `NodeListDockPanel.refresh()` call: executes correctly; node list re-renders from `nodes_data`
- ✅ Multiple project switching: each tab displays own canvas nodes correctly
- ✅ No `QProcess: Destroyed while process is still running` new errors (historical warnings addressed separately later)
