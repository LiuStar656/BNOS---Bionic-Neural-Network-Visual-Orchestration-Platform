# Debug Panel Removal and Performance Optimization

## 1. Debug Panel Removal

### Background

After multiple iterations on the debug panel (node selector, log breakpoints, session management, real-time log pipeline), we found its core functions overlap heavily with existing panels:
- Node start/stop → Node List panel and Properties panel already have full functionality
- Log viewing → `NodeLogSubPanel` in `NodeMonitorDock` is more complete (includes resource monitoring)
- Session table, Variables table → no data source, always empty

Only one unique feature: **log keyword highlighting**, insufficient to justify a standalone panel.

### Deleted Files

| File | Action |
|------|--------|
| `ui/panels/debug_panel.py` | Deleted |
| `ui/core/node_debugger.py` | Deleted (no consumers) |

### Reference Cleanup

| File | Cleanup |
|------|---------|
| `ui/core/application_context.py` | Removed `NodeDebugger` import, initialization, `debugger` property |
| `ui/main_window/panel.py` | Removed `show_debug_panel()` method and `debug_panel` branch in close callback |
| `ui/main_window/state.py` | Removed `debug_dock` from restore logic and persistence list |
| `ui/core/actions/builtin_view_actions.py` | Removed `view.debug_panel` Action |
| `ui/menu/menu_manager.py` | Removed debug panel menu item from Tools menu |
| `ui/core/strings_cn.json` | Removed 17 debug-only i18n keys |
| `ui/core/strings_en.json` | Removed 17 debug-only i18n keys |

---

## 2. Performance Panel Async Rework

### Problem

Opening the Performance panel caused noticeable UI freeze. Root cause: `psutil.process_iter()` called on the main thread — first-time process enumeration on Windows takes 1-3 seconds, freezing the entire UI.

### Fix

`StatsCollectorThread` in `PerformancePanel` now emits a `processes_ready` signal:
- Process list collection moved from main-thread `QTimer` to background thread
- Panel only receives data via `processes_ready.connect()` to update the table
- All `psutil` calls are now entirely on the background thread

### Modified Files

- `ui/panels/performance_panel.py`

---

## 3. Panel Lifecycle Dangling Pointer Guard

### Problem

After closing a panel, Qt destroys the C++ object but `self.xxx_panel` Python reference still points to a dead object. The original `hasattr + is None` check cannot detect dangling pointers, causing `Internal C++ object already deleted` crashes.

### Fix

`ui/main_window/panel.py` added `_is_panel_alive()` static method using `shiboken6.isValid()` to check C++ object liveness. All `show_*` methods and `toggle_node_list_panel` now use:

```python
if not self._is_panel_alive(getattr(self, 'xxx_panel', None)):
    # Rebuild panel
```

Also changed all panel attribute access in `_on_dock_panel_closed` to `getattr(self, 'xxx', None)` to prevent `AttributeError` from panels that were never opened.

### Modified Files

- `ui/main_window/panel.py`

---

## 4. Menu Check Mark Fix

### Problem

After restart, only "Node List" showed the correct check mark. Performance, debug, and preset library panels had no check marks.

### Root Cause

`is_checked_fn` was evaluated only once at menu construction time, before panels were created. Only `node_list` worked because it had an additional config fallback.

### Fix

All 6 Dock panel menu items now use unified `runtime visibility || config persistence` dual check:

| Panel | is_checked_fn |
|-------|--------------|
| `performance_panel` | `config.performance_dock` |
| `template_selector` | `config.preset_library_dock` |
| `node_monitor_dock` | runtime visible + config fallback |
| `resource_monitor` | runtime visible + config fallback |
| `node_list` | already working |

### Modified Files

- `ui/core/actions/builtin_view_actions.py`

---

## 5. Dock Tab Position Adjustment

Main window dock tab bar moved from bottom to top, consistent with `CanvasHost` style.

### Modified Files

- `ui/main_window/__main__.py`

---

## 6. Interaction Fixes

### Menu Reorganization

- Moved three Dock panel items (Node List, Node Monitor, Resource Monitor) from Edit menu to Tools menu
- Removed "(Dock)" text from i18n labels
- Added check marks for open panel menu items

### Modified Files

- `ui/menu/menu_manager.py`
- `ui/core/actions/builtin_view_actions.py`
- `ui/core/strings_cn.json`
- `ui/core/strings_en.json`
