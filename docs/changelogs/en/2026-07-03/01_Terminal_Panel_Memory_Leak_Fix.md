# Terminal Panel Memory Leak Fix

## Problem

Users suspected that terminal processes were not being stopped when the terminal panel was closed, causing `powershell.exe` processes to persist in the background and resulting in memory leaks.

## Root Cause Analysis

Three paths leading to terminal process leaks were identified through code tracing:

### Path 1: `hide()` does not trigger `closeEvent`

`toggle_terminal()` uses `hide()`/`show()` to toggle visibility, which does not trigger `closeEvent`. Therefore, `stop_all_terminals()` in `TerminalDock.closeEvent()` was never executed.

```python
def toggle_terminal(self):
    if self._terminal_dock.isVisible():
        self._terminal_dock.hide()  # does not trigger closeEvent
    else:
        self._terminal_dock.show()
```

### Path 2: `_remove_dock()` bypasses `closeEvent`

`_remove_dock()` directly calls `deleteLater()`, bypassing `closeEvent`, leaving terminal processes uncleaned when the panel is closed.

```python
def _remove_dock(self, dock, edge):
    self._main_window.removeDockWidget(dock)
    dock.deleteLater()  # does not trigger closeEvent
```

### Path 3: Cleanup logic does not handle `QProcess`

`_stop_content_timers()` only cleans `QTimer` and `QThread`, **not `QProcess`**. Moreover, `TerminalProcess` is a `QObject` with a nested `QProcess`, so `findChildren` cannot locate the nested `QProcess` by default.

## Fix

Added two layers of protection in `_stop_content_timers()`:

### 1. `QProcess` Cleanup

Iterates through all `QProcess` children with a three-level termination chain:
- `terminate()`: graceful termination
- `kill()`: force kill (after 3 second timeout)
- `taskkill /F /T`: system-level fallback (after another timeout)

### 2. `TerminalWidget` Explicit Cleanup

Imports and calls `TerminalWidget.close_terminal()` to ensure nested `TerminalProcess` instances are properly stopped.

## Modified Files

| File | Change |
|------|--------|
| `ui/core/dock_manager.py` | Added `QProcess` and `TerminalWidget` cleanup logic in `_stop_content_timers()` |
