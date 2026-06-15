# 【2026-06-15】V2.0.15 - Node Style Unification, Bug Fixes & Portable venv

---

## Update List

### 1. Node Style Unification & Anchor Coordinate Fixes

[View Details](./01_Node_Style_Unification_Anchor_Fixes_and_Lifecycle_Protection.md)

- **Style System Simplification**: Deleted rect.py / dot.py style files; unified entire system to panel mode (DetailedNodeStyle)
- **Anchor Position Unification**: Input/output anchor fallback positions changed to left/right edge midpoints (x=0/nw, y=h/2)
- **Coordinate System Fix**: Corrected the `setPos` double-offset bug (subtracting `size/2`) and the compensating `_find_nearest` `+half` bug, eliminating 8px visual offset
- **Inheritance Chain Fix**: DetailedNodeStyle now directly inherits NodeStyle base class, no longer depends on deleted RectNodeStyle
- **Process Lifecycle Protection**: Added RuntimeError guards for already-destroyed QProcess C++ objects during TerminalProcess destruction

---

### 2. dialog_utils.py pick Functions UnboundLocalError Fix

[View Details](./02_dialog_utils_pick_UnboundLocalError_Fix.md)

- **Root Cause**: In `pick_folder` / `pick_file` / `pick_save_file`, `go_up` / `sel_path` closures defined after `_create_nav_bar(..., go_up)` call — Python forward-reference triggers `UnboundLocalError`
- **Fix**: Move `go_up` / `sel_path` definitions before `_create_nav_bar` call; remove duplicate tail definitions
- **Impact Scope**: Open Project, Import Node, Export Node, Export Project all restored to normal operation

---

### 3. Async Project Open & Canvas Layout Loading Fix

[View Details](./03_Async_Project_Open_and_Canvas_Layout_Fix.md)

- **Async-ization**: `project_open()` changed to `QTimer.singleShot` two-phase loading — no longer blocks main thread; `project_refresh(async_mode=True)` aligns with node start/stop flow
- **Canvas Layout Fix**: Root cause of empty nodes when opening second project — `canvas_changed.emit()` signal in `canvas_host.py` fires before `load_layout()`, causing empty dict to write back to main window's `nodes_data`. Fixed order: `load_layout` → `update_canvas_data` → `canvas_changed.emit`
- **User Experience**: Large projects (50+ nodes) open with toast visible and responsive UI

---

### 4. Portable Virtual Environment for Python Nodes

[View Details](./04_Portable_Virtual_Environment_for_Python_Nodes.md)

- **De-Absolute-Path at Creation**: `python_create_node.py` creates venv with `--copies`; `start.json` no longer writes `python_exe` / `path` absolute paths — auto-inferred at runtime by `node_process.py` fallback
- **Auto-Repair on Import**: `_repair_portable_venv()` rewrites `pyvenv.cfg` `home` to point to target machine's Python; cleans legacy absolute paths in `start.json`
- **Packaging Optimization**: `packager.py` skips `__pycache__` and `.pyc` during compression — ~30-40% smaller packages
- **Result**: Python nodes exported as `.bnos` can be imported on other machines and **launched directly without re-running `pip install`**

---

## Key Updates

| Category | Details |
|----------|---------|
| **Style System** | Deleted rect.py / dot.py; unified to DetailedNodeStyle panel mode; anchor positions unified to left/right edge midpoints; fixed setPos 8px offset |
| **Bug Fixes** | dialog_utils three-function `UnboundLocalError`; second project open canvas layout loss; TerminalProcess QProcess destruction RuntimeError |
| **Async-ization** | project_open changed to QTimer.singleShot two-phase async loading — consistent with node start/stop async_mode |
| **Portable Nodes** | start.json de-absolute-pathed; `_repair_portable_venv` dynamically fixes `pyvenv.cfg` at import; bytecode cache skipped during packaging |
| **Code Quality** | canvas_host.py signal firing order corrected; packager.py zip compression skips bytecode cache; 169/169 compilation passes |

---

## Verification Results

- ✅ 169/169 Python source files compile successfully
- ✅ Open Project dialog: `pick_folder` normal, no `UnboundLocalError`
- ✅ Import/Export Node dialogs: `pick_file` / `pick_save_file` normal
- ✅ Opening two projects simultaneously: second project canvas layout loads correctly
- ✅ Large project opening: Main thread non-blocking, toast displays normally
- ✅ Python node cross-machine migration: No `pip install` needed after import, starts directly
- ✅ Node styles: Panel mode renders correctly, no 8px anchor offset
- ✅ Zero `PyQt6` / `pyqtSignal` / `pyqtSlot` references remaining in codebase
