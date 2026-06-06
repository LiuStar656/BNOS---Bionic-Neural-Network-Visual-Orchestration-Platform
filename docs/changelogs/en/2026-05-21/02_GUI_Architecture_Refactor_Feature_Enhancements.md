# 🔧 GUI Architecture Refactor & Feature Enhancements

## 🔧 GUI Architecture Refactor & Feature Enhancements (2026-05-21)

### Code Decoupling 📦

**10 new modules** created, eliminating code duplication:

| Module | Responsibility | Source |
|--------|---------------|--------|
| `ui/core/app_config.py` | Global config persistence | Extracted from main_window |
| `ui/core/theme.py` | Dark QSS stylesheet | Extracted from main_window |
| `ui/core/node_process.py` | Process start/stop/PID/health | New, eliminates 4 duplicates |
| `ui/canvas/canvas_colors.py` | Canvas color management Mixin | Extracted from canvas_view |
| `ui/canvas/canvas_layout.py` | Canvas layout persistence Mixin | Extracted from canvas_view |
| `ui/canvas/canvas_menus.py` | Canvas right-click menu Mixin | Extracted from canvas_view |

- `main_window.py`: 1491 → **935 lines** (-556)
- `canvas_view.py`: 1911 → **~1200 lines** (-680)
- Eliminated Toast 170-line duplicate, process management 180-line duplicate

### Process Health Detection 🩺

- **PID File Persistence**: `start_node_process` writes `.pid`, `stop_node_process` deletes it
- **Cross-Session Recovery**: GUI restart auto-scans `.pid` files, detects running processes, restores ● status
- **Periodic Health Check**: Polls running processes every 3s, crashed nodes auto-update to ○ stopped
- Fixed `subprocess.PIPE` buffer deadlock, switched to `DEVNULL`

### Selection System Unification 🖱️

- Removed `selected_node` standalone property
- Single-click / box-select / Ctrl+click all use unified `box_selected_nodes`
- Box-selected nodes auto-call `setSelected(True)`, support **group dragging**
- Fixed lambda closure late-binding causing right-click menu color failure

### Node Anti-Overlap 🧱

- Auto-detect and push away adjacent nodes during drag
- `setPos()` during layout loading also triggers anti-overlap

### Startup Script Fixes 🔨

`tools/rust_create_node.py` and `tools/python_create_node.py`:
- Support `--no-pause` flag (silent mode for GUI invocation)
- Use `start /b` / `nohup &` for background launch, no longer blocking
- Auto-write `.pid` file after launch
- Fixed Rust dual-file detection and auto-build logic

### Development Guidelines 📋

Added `开发维护准则.md` (10 coding standards + priority fix list) and `tools/Node_Generator_Guidelines_EN.md` (new language node standard template).

---