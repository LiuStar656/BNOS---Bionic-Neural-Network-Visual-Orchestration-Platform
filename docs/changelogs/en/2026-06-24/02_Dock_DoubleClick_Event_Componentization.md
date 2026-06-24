# 02 Dock Double-Click Event Componentization

## Problem Overview

`BnosDock` (bnos_dock.py) and `BnosDockWidget` (dock_manager.py) each contained ~25 lines of duplicate `mouseDoubleClickEvent` code with identical logic (detect edge/title bar click → toggle float/dock), differing only in the embed callback (BnosDock needs to hide the title bar first).

## Root Cause

The double-click float/dock toggle logic was scattered across two QDockWidget subclasses without a shared abstraction. Any change to double-click behavior required modifying both files, increasing maintenance cost and risk of omission.

## Solution

1. **New `DockDoubleClickHandler` component** (in `ui/core/dock_position_manager.py`):
   - Standalone `QObject` subclass for unified double-click handling
   - `handle(event)` returns `True`/`False` to indicate whether the event was consumed
   - Constructor injects `title_widget_getter`, `is_title_bar_hidden`, `on_before_embed` callbacks to adapt to different Dock subclass needs
   - Tightly coupled with `DockPositionManager`: automatically calls `save_current_state_before_toggle()` + `restore_to_docked_position()` on embed

2. **`BnosDock` adaptation**:
   - `mouseDoubleClickEvent` reduced from ~25 lines to 4-line delegation
   - `_auto_embed_and_hide_title` → `_on_before_embed` callback, invoked by handler before embed

3. **`BnosDockWidget` adaptation**:
   - Same delegation pattern for `mouseDoubleClickEvent`
   - No `on_before_embed` needed (panel docks keep title bar when embedded)
   - Removed `_auto_embed` method

## Affected Files

| File | Change |
|------|--------|
| `ui/core/dock_position_manager.py` | New `DockDoubleClickHandler` class (~70 lines) |
| `ui/core/bnos_dock.py` | `mouseDoubleClickEvent` delegated; `_auto_embed_and_hide_title` → `_on_before_embed` |
| `ui/core/dock_manager.py` | `mouseDoubleClickEvent` delegated; removed `_auto_embed` |

## Verification

- Canvas Dock: Double-click title bar/edge → float ↔ embed (title bar hidden on embed)
- Panel Dock: Double-click title bar/edge → float ↔ embed (title bar retained on embed)
- Dock position restored accurately, unaffected by Qt cache
