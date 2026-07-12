# 12 Orthogonal Edge Snapping

## Overview

New orthogonal edge snapping feature: when dragging edge waypoints, auto-snap to the nearest right-angle intersection, making segments horizontal or vertical. Supports menu toggle and Shift to temporarily disable.

---

## I. Interaction

| Action | Effect |
|------|------|
| Drag waypoint | **Auto-snap** to nearest orthogonal intersection |
| Shift + drag | Temporarily disable snapping (free drag) |
| Right-click canvas → Ortho Snap: ON/OFF | Global toggle |

---

## II. Snap Algorithm

```
Dragging waypoint wp, adjacent points are prev and next:

Candidate 1: (prev.x, next.y)  →  prev→wp vertical, wp→next horizontal
Candidate 2: (next.x, prev.y)  →  prev→wp horizontal, wp→next vertical

Choose candidate closest to mouse. No snap beyond 20px threshold.
```

Visual effect on canvas:

```
┌───────┐     → Free drag (no snap)
│  A    │
│       │───┐
└───────┘   │
            │  ← Drag here → auto-snap
┌───────┐   │
│  B    │───┘
└───────┘
```

---

## III. Changes

| File | Change |
|------|------|
| `edge_item.py` | `_snap_orthogonal()` static method + `SNAP_THRESHOLD = 20` + `mouseMoveEvent` snap |
| `canvas_view.py` | `edge_snap_enabled = True` canvas-level toggle |
| `canvas_menus.py` | `_toggle_edge_snap()` + right-click menu item |
| i18n 3 files | +2 keys (ON/OFF status text) |

Total: ~80 lines, 4 files.
