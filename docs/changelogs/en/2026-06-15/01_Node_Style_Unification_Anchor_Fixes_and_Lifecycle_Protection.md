# Node Style Unification, Anchor Coordinate Fixes & Process Lifecycle Protection

## Overview

Today's update focuses on three areas:
1. **Node Style System Simplification**: Completely removed rectangular/dot styles, unified entire system to panel mode (DetailedNodeStyle)
2. **Anchor Coordinate Fixes**: Anchors repositioned to left/right edge midpoints, with setPos/_find_nearest double-offset bug fixed
3. **Process Lifecycle Protection**: Fixed RuntimeError from already-destroyed QProcess C++ objects during TerminalProcess destruction

---

## 1. Node Style System Simplification

### Motivation

The original three node styles (panel/rectangular/dot) caused maintenance complexity and inconsistent UX. Panel mode already integrates all core capabilities (parameter inline display, status lights, CPU/MEM usage, language labels), making the other styles redundant.

### Changes

| Action | File | Details |
|------|------|------|
| **Delete** | `ui/canvas/items/styles/rect.py` | RectNodeStyle, DarkRectNodeStyle, LightRectNodeStyle |
| **Delete** | `ui/canvas/items/styles/dot.py` | DotNodeStyle |
| **Rewrite** | `ui/canvas/items/styles/detailed.py` | Now inherits `NodeStyle` base class directly (previously inherited RectNodeStyle) |
| **Simplify** | `ui/canvas/items/styles/__init__.py` | StyleRegistry only registers `"detailed"` → `DetailedNodeStyle` |
| **Rewrite** | `ui/canvas/items/node_item.py` | `set_style` simplified to DetailedNodeStyle only; `paint`/`shape`/`mousePressEvent` removed is_dot checks; constructor defaults to DetailedNodeStyle |
| **Update** | `ui/canvas/canvas_layout.py` | Default style `"rect"` → `"detailed"` |
| **Simplify** | `ui/canvas/items/node_style.py` | Compatibility layer only exports DetailedNodeStyle + StyleRegistry |

---

## 2. Anchor Coordinate Fix: Left/Right Edge Midpoints

### Motivation

Input/output anchor fallback positions were previously at top-left and bottom-right corners respectively, which was inconsistent and hard to locate. Unified to left edge midpoint (x=0, y=h/2) and right edge midpoint (x=nw, y=h/2).

### Coordinate System Fix (Root Cause Bug)

**Problem**: `_make_anchor()` creates `AnchorItem(-size/2, -size/2, size, size)` whose local ellipse center is at `(0,0)`, so after `setPos(px, py)` the visual center is at `(px, py)`. However, the old code subtracted an extra `size/2` in all `setPos` calls:

```python
# Old code (bug)
anchor.setPos(center_x - size/2, center_y - size/2)  # visual center offset by size/2
```

Meanwhile `_find_nearest` added `half` back as compensation:

```python
# Old code (compensating bug)
center_x = anchor.pos().x() + half  # compensates the extra -size/2 above
```

The two bugs cancelled each other out for hit detection, but the visual position was always offset by 8px.

**Fix**: Removed the `-size/2` from all `setPos` calls and the `+half` from `_find_nearest`, making coordinates what-you-see-is-what-you-get.

### Changed Files

| File | Change |
|------|--------|
| `ui/canvas/items/anchor_manager.py:228` | Main input anchor fallback: `(ANCHOR_HALF+8, ANCHOR_HALF+4)` → `(0, nh/2)` |
| `ui/canvas/items/anchor_manager.py:288` | Main output anchor fallback: `(nw, nh - ANCHOR_HALF)` → `(nw, nh/2)` |
| `ui/canvas/items/anchor_manager.py:228,254,288` | Three `setPos(cx - size/2, cy - size/2)` → `setPos(cx, cy)` |
| `ui/canvas/items/anchor_manager.py:643` | `_find_nearest` removed `+half` compensation |
| `ui/canvas/items/node_item.py:687-689` | `__output__` row anchor: `(final_w - ANCHOR_SIZE/2, final_h - ANCHOR_HALF)` → `(final_w, final_h/2)` |

---

## 3. Process Lifecycle Protection

### Problem

`TerminalProcess.__del__()` → `stop()` → `self.process.state()` could access a `QProcess` C++ object already freed by Qt's parent widget destruction chain during program exit, throwing:

```
RuntimeError: libshiboken: Internal C++ object (PySide6.QtCore.QProcess) already deleted.
```

### Fix

Added `try/except RuntimeError` guards in both `stop()` and `__del__()` of `terminal_process.py`, silently returning when the C++ object has already been destroyed.

---

## Affected File Summary

| File | Action |
|------|------|
| `ui/canvas/items/styles/rect.py` | Deleted |
| `ui/canvas/items/styles/dot.py` | Deleted |
| `ui/canvas/items/styles/__init__.py` | Simplified |
| `ui/canvas/items/styles/detailed.py` | Inheritance chain rewritten |
| `ui/canvas/items/styles/_base.py` | Unchanged (provides base class) |
| `ui/canvas/items/node_item.py` | set_style/paint/shape/constructor simplified |
| `ui/canvas/items/node_style.py` | Compatibility layer simplified |
| `ui/canvas/canvas_layout.py` | Default style changed to detailed |
| `ui/canvas/canvas_menus.py` | Style switching logic simplified |
| `ui/canvas/items/anchor_manager.py` | Anchor fallback positions + setPos/_find_nearest fixes |
| `ui/core/terminal/terminal_process.py` | RuntimeError protection |
