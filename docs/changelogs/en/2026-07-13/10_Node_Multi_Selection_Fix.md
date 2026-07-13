# Node Multi-Selection Fix

## Problem Description

The node multi-selection feature had the following issues:
- When Ctrl+clicking to select a second node, the selection ring of the first node would immediately disappear
- When directly Ctrl+clicking a node, the selection ring would also immediately jump out
- Multi-selection count was incorrect, unable to select more than 2 nodes

## Root Cause

Qt's `QGraphicsScene` default selection mode is `SingleSelection`, which automatically deselects other nodes when calling `setSelected(True)`, causing the multi-selection feature to fail.

## Fix Solution

Use a custom selection flag `_is_custom_selected` to completely bypass Qt's selection mode:

### Modified Files

**1. ui/canvas/items/node_components/rendering.py**

Check custom selection flag during rendering:
```python
is_selected = getattr(self._node, '_is_custom_selected', False) or self._node.isSelected()
border_color = QColor("#66b0ff") if is_selected else QColor(body_border)
```

**2. ui/canvas/mixins/canvas_selection.py**

- `on_node_selected`: Clear all custom selection states on normal click, select only current node
- `_toggle_node_selection`: Toggle custom selection state on Ctrl+click

**3. ui/canvas/canvas_view.py**

- `SelectedNodesList._sync`: Sync custom selection states to cache list
- `append/remove/clear`: Operate on custom selection flags

**4. ui/canvas/drawing/tools/selection_tool.py**

Clear all custom selection states on blank area click

## Selection Behavior After Fix

| Action | Behavior |
|--------|----------|
| Normal Click | Clear all selections, select current node |
| Ctrl+Click | Toggle current node selection state (supports multi-selection) |
| Blank Click | Clear all selections |
