# Dock Window Re-Dock Bug Fix and Edge Detection Optimization

## 1. Issue Overview

### Bug 1: Dock Window Disappears When Re-Docked
- **Description**: When users drag the canvas dock out to become a floating window and then re-dock it back to the main window, the entire application UI disappears, but the process continues running.
- **Reproduction**: Drag canvas dock out → Drag back and dock → UI disappears

### Bug 2: Oversized Edge Resize Detection Area
- **Description**: The edge resize detection threshold (border) was set to 6 pixels, which was too large and caused users to accidentally trigger resize when operating near window edges.

## 2. Root Cause Analysis

### Bug 1 Root Cause

In `BnosDock._on_top_level_changed`, when transitioning from floating to docked state, the code incorrectly operated on `self.window()`:

```python
def _on_top_level_changed(self, floating):
    self._is_floating = floating
    if floating:
        QTimer.singleShot(0, self._apply_floating_style)
    else:
        w = self.window()  # ❌ Wrong: window() returns Qt's internal container window when QDockWidget is floating
        w.setWindowFlags(w.windowFlags() & ~Qt.WindowType.FramelessWindowHint)
        ...
```

When a QDockWidget is floating, Qt creates an internal container window, and `self.window()` returns this temporary container. When the dock is re-docked, this container window may be destroyed or become invalid, causing the window flags setting to fail and the entire UI to disappear.

### Bug 2 Root Cause

The `border = 6` threshold was too large on high-resolution screens, causing accidental resize triggers during normal operations near window edges.

## 3. Fix Solution

### Bug 1 Fix

Changed the operation target from `self.window()` to `self`:

```python
def _on_top_level_changed(self, floating):
    """Floating state change callback"""
    self._is_floating = floating
    if floating:
        QTimer.singleShot(0, self._apply_floating_style)
    else:
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.FramelessWindowHint)
        self._apply_docked_style()
        self.show()
```

This is consistent with `BnosDockWidget` (used for regular panels) and avoids operating on destroyed internal container windows.

### Bug 2 Fix

Reduced edge detection threshold from 6px to 4px:

**Modified files:**
- `ui/core/bnos_dock.py`: `border = 6` → `border = 4`
- `ui/core/dock_manager.py`: `border = 6` → `border = 4`

## 4. Impact Scope

| File | Changes |
| --- | --- |
| `ui/core/bnos_dock.py` | Changed operation target to `self` in `_on_top_level_changed`; border from 6 to 4 |
| `ui/core/dock_manager.py` | border from 6 to 4 |

## 5. Verification

- **Syntax Check**: `python _check_syntax.py` passed
- **Feature Verification Steps**:
  1. Start BNOS, open a project
  2. Drag canvas dock out to floating window
  3. Drag floating window back to main window → verify UI does not disappear
  4. Repeat steps 2-3 multiple times → verify stability
  5. Test edge resize on different screen resolutions → verify threshold is appropriate
