# 03 Dock Double-Click Event Disabled

## Problem Overview

Double-clicking the Dock title bar to toggle float/dock has bugs and has been temporarily disabled.

## Root Cause

Initially used `event.ignore()` to try blocking double-click events, but `ignore()` only marks the event as "unhandled" and propagates it upward to Qt's Dock system, which still triggers the float/dock toggle internally.

## Solution

**Dual Interception** mechanism:

1. **Event filter layer**: `self.installEventFilter(self)` intercepts `QEvent.MouseButtonDblClick` at the earliest dispatch stage, returning `True` to consume the event and prevent propagation to Qt internals
2. **mouseDoubleClickEvent layer**: Changed to `event.accept()` as a fallback to ensure the event is consumed

Additionally:
- `DockDoubleClickHandler` implementation cleared, class definition retained with `[Disabled]` marker
- Handler initialization removed from both Dock classes
- `BnosDock._on_before_embed` commented out and preserved for future restoration

## Affected Files

| File | Change |
|------|--------|
| `ui/core/dock_position_manager.py` | `DockDoubleClickHandler` class cleared and marked disabled |
| `ui/core/bnos_dock.py` | Added `QEvent` import; installed `eventFilter` to intercept double-clicks; `mouseDoubleClickEvent` → `accept()`; removed handler init; commented out `_on_before_embed` |
| `ui/core/dock_manager.py` | Same as above |

## Verification

- Double-click Dock title bar → no response (no float/dock toggle)
- Double-click Dock edge area → no response
- Dragging title bar still works normally for float/dock
