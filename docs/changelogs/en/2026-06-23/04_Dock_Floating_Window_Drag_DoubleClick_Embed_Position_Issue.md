# Dock Floating Window Drag-Based Double-Click Embed Position Issue Analysis

## 1. Problem Overview

### Symptoms

| Operation | Result |
|-----------|--------|
| Docked → double-click title bar to float → **no drag** → double-click to embed | Correctly returns to original dock position |
| Docked → double-click title bar to float → **drag floating window** → double-click to embed | Docks at bottom-right corner of the floating window position first, then animates to correct position only after dragging another dock |
| Docked → drag out of main window to float → drag floating window → double-click to embed | Same as above: docks at bottom-right corner first |

### Affected Components

- `BnosDock` (canvas dock, `ui/core/bnos_dock.py`)
- `BnosDockWidget` (main window panel dock, `ui/core/dock_manager.py`)

---

## 2. Root Cause Analysis

### 2.1 Qt QDockWidget Native Limitation

Qt's `QDockWidget` maintains an **internal cache** of the "last docked area". Key behaviors:

1. **Floating window NOT dragged**: Qt preserves the internal dock cache, `setFloating(False)` places it directly in the original position — **works correctly**
2. **Floating window IS dragged**: Qt detects `moveEvent` on the floating window, clears the internal dock cache — **position info lost**

Once the cache is cleared, `setFloating(False)` can only guess the target area based on the floating window's current screen coordinates, defaulting to the bottom-right corner of whatever area it selects.

### 2.2 Previously Attempted But Unsuccessful Approaches

| Approach | Method | Failure Reason |
|----------|--------|----------------|
| Delayed restore | `QTimer.singleShot(100ms, restore)` | Qt layout already committed, timing race |
| Hide-then-restore | `hide()` → `removeDockWidget` → `addDockWidget` → `show()` | Queued layout requests from Qt override subsequent operations |
| setUpdatesEnabled to suppress animation | `setUpdatesEnabled(False)` → operations → `setUpdatesEnabled(True)` | The "bottom-right" layout request queued by `setFloating(False)` still executes when updates are re-enabled |
| processEvents to flush queue | Insert `processEvents()` between key steps | A single `processEvents()` is insufficient to fully drain Qt's internal queued events |
| eventFilter early save | Save dock area on mouse press | Area saved successfully but still overridden by Qt during restore |

### 2.3 Current Approach: `QDockWidget.setDockLocation()`

This is Qt's **native API**. Calling `setDockLocation(area)` before `setFloating(False)` tells Qt to use the specified area instead of guessing from the floating window position.

```python
# dock_position_manager.py - restore_to_docked_position()
area = self._original_dock_area
if area is None:
    area = self._get_persisted_docked_area()

self._dock_widget.setDockLocation(area)  # Tell Qt the target area
self._dock_widget.setFloating(False)      # Qt uses the specified area
```

### 2.4 Supporting Mechanism: JSON File Persistence

Created an independent `DockPositionManager` (`ui/core/dock_position_manager.py`):

```
.bnos/dock_positions.json
{
  "资源监测(Dock)": {
    "docked_area": 1,           // 1=Left, 2=Right, 4=Top, 8=Bottom
    "floating": {
      "x": 500, "y": 300,
      "width": 400, "height": 300
    }
  }
}
```

**Write Rules by Timing**:

| Timing | Content Written | Notes |
|--------|----------------|-------|
| `dockLocationChanged` signal | `docked_area` | Immediately persist when dragged to a new dock area |
| Floating window drag (500ms timer) | `floating` coordinates | Track floating window position in real-time |
| Before double-click toggle `save_current_state_before_toggle()` | Full current state | Write to JSON before toggling to prevent Qt cache clearing |

**Blocking mechanism**: During restore, `_block_persist = True` prevents the `dockLocationChanged` signal triggered by `setFloating(False)` from overwriting the correct value.

---

## 3. Key Files Involved

| File | Role |
|------|------|
| `ui/core/dock_position_manager.py` | **Core**: position persistence, signal listening, restore logic |
| `ui/core/bnos_dock.py` | Canvas dock wrapper, delegates to `DockPositionManager` on double-click |
| `ui/core/dock_manager.py` | Main window panel dock wrapper, also delegates to `DockPositionManager` |
| `ui/core/canvas_host.py` | Calls `save_original_dock_info` when creating canvas docks |
| `ui/dialogs/color_settings_dialog.py` | Color settings must affect both dock types |

---

## 4. Current Status: Still Unresolved

**The `setDockLocation()` approach has not yet been verified to solve the issue.**

The API documentation describes it as setting the dock's current dock location, but notes the value is only meaningful when the dock is inside a `QMainWindow`. The effect of calling `setDockLocation()` while the dock is floating lacks official clarity.

### Possible Next Steps

1. **Verify `setDockLocation()` behavior in floating state**: Use logging to confirm whether Qt's internal state is correct after the call
2. **Try `QDockWidget.DockWidgetFeature` approach**: Temporarily disable `DockWidgetFloatable` feature before embedding
3. **Try `QMainWindow.saveState()` / `restoreState()` approach**: Save layout snapshot when docked, restore when embedding
4. **Upgrade PySide6 version**: Check for related bug fixes
5. **Submit bug report to Qt/PySide6**: If confirmed to be a framework-level issue
