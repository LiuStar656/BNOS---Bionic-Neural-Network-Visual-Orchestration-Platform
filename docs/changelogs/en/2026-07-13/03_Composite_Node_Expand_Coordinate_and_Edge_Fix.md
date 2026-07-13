# 03 Composite Node Expand Coordinate and Edge Fix

## Problem Description

Two issues occurred after expanding composite nodes:
1. **Child node position offset**: Expanded child nodes moved to incorrect positions, not where the composite node was
2. **Edge loss**: External node edges connected to the composite node remained at their original positions, not reconnecting to the expanded child nodes

## Root Cause Analysis

### Issue 1: Coordinate Offset

The expand function used a saved stale `canvas_position` instead of the composite node's current actual position. When the composite node was moved before expanding, child nodes would be positioned at the old location.

**Before fix**:
```python
comp_pos = comp.get("canvas_position", {"x": 0, "y": 0})
```

**After fix**:
```python
comp_pos = {
    "x": comp_item.pos().x(),
    "y": comp_item.pos().y(),
}
```

### Issue 2: Edge Mapping Failure

The composite node's default input anchor name is `"default"`, but `_identify_ports` uses `"data"` for the main input port name. This caused `_morph_composite_to_internal_edges` to fail finding the corresponding internal node.

**Fix**: Added `"data"` → `"default"` port name mapping.

### Issue 3: Layout Loading Restores Old Coordinates

`canvas_layout.json` saved all node coordinates, including composite node's internal child nodes. When loading layout, child nodes were restored to old positions, inconsistent with the composite node's current position.

**Fix**: Skip internal nodes of collapsed composites during save and load.

## Fix Details

### 3.1 Expand Coordinate Fix

**File**: `ui/core/node/composite_node.py`

Retrieve current position directly from `comp_item.pos()` instead of using saved `canvas_position`.

### 3.2 Port Name Mapping

**File**: `ui/core/node/composite_node.py`

Added `"data"` → `"default"` port name mapping in `_morph_composite_to_internal_edges` to ensure the default input anchor correctly finds the internal node.

### 3.3 Layout Save/Load Filtering

**File**: `ui/canvas/mixins/canvas_layout.py`

- Save layout: Skip internal nodes of collapsed composite nodes, only save composite node coordinates
- Load layout: Skip internal nodes of collapsed composite nodes, don't restore old positions

### 3.4 Execution Order Adjustment

**File**: `ui/core/node/composite_node.py`

Moved `_morph_composite_to_internal_edges` to execute after child node positioning, ensuring newly created edge endpoints use correct child node positions.

## Modified Files

| File | Change |
|------|--------|
| `ui/core/node/composite_node.py` | Use current position on expand; add port name mapping; adjust execution order |
| `ui/canvas/mixins/canvas_layout.py` | Skip internal nodes of collapsed composites during save/load |

## Verification

After fix:
- ✅ Child nodes correctly positioned at composite node's current location when expanding
- ✅ External node edges correctly connect to expanded child nodes
- ✅ After collapsing, moving, and re-expanding, child node positions are correct
- ✅ After saving/loading layout, composite node expands to correct position

---

**Last Updated**: 2026-07-13
