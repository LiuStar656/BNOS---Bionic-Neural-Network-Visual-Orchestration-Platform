# Multi-Anchor System Refinement & Edge Persistence

## 📋 Update Overview

This update refines the multi-anchor input system in Panel mode, addressing anchor positioning, port mapping distribution, edge persistence, and batch cleanup. The main input anchor (`listen_upper_file`) is now clearly differentiated from additional input ports (`input_port`) in size, position, and config write target. Edge port bindings survive application restart.

---

## 🎯 Core Changes

### 1. Anchor Differentiation

**Two anchor types**:

| Anchor | Size | Position | config Write Field |
|--------|------|----------|-------------------|
| `listen_upper_file` (main input) | 16px | Left edge, vertically centered | `listen_upper_file` |
| `input_port` (additional input) | 10px | Tight against label left (x=21) | `port_mappings[port_name]` |

**Layout comparison**:

```
Before (all same size at left edge):
  [● 16px]  listen_upper_file
  [● 16px]  prompt
  [● 16px]  context

After (size differentiated, small anchors near labels):
  [● 16px]  listen_upper_file  (centered on left edge)
  [○ 10px]  prompt             (2px from label left)
  [○ 10px]  context            (2px from label left)
```

**Modified files**:
- `ui/canvas/items/anchor_item.py`: Added `ANCHOR_SIZE_SMALL=10`, `ANCHOR_HALF_SMALL=5`; constructor accepts `size` param; hover effects adapt to actual size
- `ui/canvas/items/node_item.py`: `_param_row_positions` uses `(center_x, center_y, size)` triples; small anchor x = `ANCHOR_ZONE_WIDTH + LEFT_INNER_PADDING - ANCHOR_SIZE_SMALL/2 - 2 = 21`
- `ui/canvas/items/anchor_manager.py`: `_make_anchor` accepts `size`; `_find_nearest` computes center from actual size; `build_from_config` differentiates default (16px) from port anchors (10px)

---

### 2. config.json Port Mapping Correction

**Problem**: Connections to the `listen_upper_file` anchor were written to `port_mappings["default"]`, while the main `listen_upper_file` field remained empty or kept its template value.

**Fix**: Added port name dispatch in `canvas_connections.py`:

```python
# port_name == "default" or None → read/write listen_upper_file
# port_name == "prompt"/"context"... → read/write port_mappings[port_name]
if port_name and port_name != "default":
    target_config['port_mappings'][port_name] = source_output_path
else:
    target_config['listen_upper_file'] = source_output_path
```

**Modified files**: `ui/canvas/canvas_connections.py` (`create_edge` L132-143, `remove_edge` L204-219)

---

### 3. Edge Z-Layer Boost

**Problem**: Edges at z-value 0 were occluded by nodes (z=2) and anchors (z=10).

**Fix**: EdgeItem z-value raised from 0 to 20, now the topmost canvas layer.

**Layer hierarchy**: `Nodes(z=2) < Anchors(z=10) < Edges(z=20)`

**Modified files**: `ui/canvas/items/edge_item.py` (L65)

---

### 4. Edge Persistence Fix

**Problem**: After restart, all edges re-bound to the default `listen_upper_file` anchor, losing connections to port-specific anchors (e.g., `prompt`, `context`).

**Root cause**:
1. `save_layout` didn't save port names
2. `load_layout` created EdgeItem without port info
3. `_validate_edge_anchor_binding` used an `or` condition, so one missing anchor caused the other to be overwritten too

**Fix**:

| Location | Change |
|----------|--------|
| `save_layout` | Added `source_port` / `target_port` to edge dict |
| `load_layout` | Restore bindings via `anchor_manager.get_input/output()` using port names |
| `_validate_edge_anchor_binding` | `if not a or not b` → per-anchor `if not a` / `if not b` |

**Persistence format change**:
```json
// Before
{"source": "node_rust_1", "target": "node_python_1"}

// After
{"source": "node_rust_1", "target": "node_python_1", "target_port": "prompt"}
```

**Modified files**: `ui/canvas/canvas_layout.py`

---

### 5. Batch Cleanup Enhancement

**Problem**: `clear_canvas` called `edge.remove_from_scene()` directly, bypassing config cleanup; `batch_clear_listen_config` only cleared `listen_upper_file` without touching `port_mappings`.

**Fix**:

| Method | Change |
|--------|--------|
| `clear_canvas` | `edge.remove_from_scene()` → `self.remove_edge(edge)`, full config cleanup path |
| `batch_clear_listen_config` | Clears `listen_upper_file` + `port_mappings` + `out_connections` simultaneously |

**Modified files**:
- `ui/canvas/canvas_view.py` (L964-968)
- `ui/canvas/canvas_batch_ops.py` (L123-154)

---

## 📂 File Change Summary

| File | Action | Description |
|------|--------|-------------|
| `ui/canvas/items/anchor_item.py` | Modified | Dual-size anchors (16px/10px), hover effect adaptation |
| `ui/canvas/items/anchor_manager.py` | Modified | `_make_anchor` size param; `_find_nearest` dynamic calc; default vs port anchor distinction |
| `ui/canvas/items/node_item.py` | Modified | `_param_row_positions` triples; small anchor x=21 tight against label |
| `ui/canvas/items/edge_item.py` | Modified | z-value 0 → 20 |
| `ui/canvas/canvas_connections.py` | Modified | port_name="default" → writes `listen_upper_file` |
| `ui/canvas/canvas_layout.py` | Modified | Persist source_port/target_port; restore port bindings on load; per-anchor validation |
| `ui/canvas/canvas_view.py` | Modified | `clear_canvas` uses `remove_edge` for full cleanup |
| `ui/canvas/canvas_batch_ops.py` | Modified | Batch clear includes `port_mappings` + `out_connections` |

---

## 🐛 Fixed Issues

| Issue | Status |
|-------|--------|
| `listen_upper_file` connection written to `port_mappings["default"]` | ✅ Fixed |
| Edges occluded by nodes and anchors | ✅ Fixed |
| Small anchor edges lost on restart, re-bind to main anchor | ✅ Fixed |
| `clear_canvas` not clearing port mappings in config | ✅ Fixed |
| `batch_clear_listen_config` not clearing `port_mappings` | ✅ Fixed |
| Small anchors same size as main anchor (16px), no visual distinction | ✅ Fixed |
| Small anchors positioned on border, not intuitive | ✅ Fixed |

---

## ✅ Acceptance Criteria

| Item | Status |
|------|--------|
| Main anchor 16px centered on left edge; port anchors 10px tight against label left | ✅ |
| Main anchor connections write to `listen_upper_file` | ✅ |
| Port anchor connections write to `port_mappings[port_name]` | ✅ |
| Removing edges clears corresponding `port_mappings` entries in config.json | ✅ |
| Port bindings survive application restart | ✅ |
| Clearing canvas removes all port info from config.json | ✅ |
| All files pass PyLance diagnostics with zero errors | ✅ |

---

**Date**: 2026-06-10
