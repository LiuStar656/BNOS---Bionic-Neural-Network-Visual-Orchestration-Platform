# 🔄 Standalone Launcher + 3-State Indicators + Ctrl+D Delete + Color Fixes

## 🔄 Standalone Launcher + 3-State Indicators + Ctrl+D Delete + Color Fixes (2026-05-23)

### Standalone tkinter Launcher

Replaced embedded PySide6 splash with `launcher.py` (251 lines):
- Pure tkinter, zero dependencies on venv, packable as standalone EXE
- Splash appears instantly → background spawns venv pythonw → real-time progress file polling
- Smooth progress bar animation, precisely synced with main program loading
- Auto-close 0.2s after 100%. `.vbs` zero-window launcher
- Missing venv: shows install guide on splash then exits

### 3-State Status Indicator

| Color | State | Detection |
|-------|-------|-----------|
| Gray `#888` | Stopped | listener PID absent |
| Green `#44FF44` | Idle | listener alive, no main child |
| Red `#FF4444` | Running | listener + main child active |

Uses `psutil` process tree detection, zero node code changes. Health check polls every 3s, UI fully adapted for 3-state model.

### Ctrl+D Unified Delete Shortcut

`Ctrl+D` context-aware:
- Node list focused → batch delete nodes/groups
- Canvas box-selected nodes → remove from canvas
- Canvas selected graphics → delete

Right-click delete removed (conflicted with context menu).

### Color Settings Fixes

- **Canvas background**: `drawBackground` directly `painter.fillRect` using `canvas_bg_color`; `resetCachedContent` + `repaint` for instant update
- **Color dialog**: BNOS dark theme Frameless window, draggable, visible border
- **Key name alignment**: `choose_color`'s `canvas_bg` now matches `collect_settings`'s `temp_canvas_bg_color`

### Shortcut Manager

New `ui/core/shortcut_manager.py`: 11 shortcuts centrally defined + persisted to `app_config.json` + settings panel visual editor + double-click capture.

### Language Switching Fixed

Fixed Python `from import LANG` value-copy bug (added `get_lang()`) + restart via `exit(42)` exit code + `AppConfig` supports new key persistence.

### Affected Files

`launcher.py`(new), `node_process.py`, `node_style.py`, `canvas_colors.py`, `canvas_view.py`, `shortcut_manager.py`(new), `color_settings_dialog.py`, `settings_dialog.py`, `menu_manager.py`, `main_window.py`, `i18n.py`, `app_config.py`, `start_bnos_console.vbs`(new), startup scripts

---