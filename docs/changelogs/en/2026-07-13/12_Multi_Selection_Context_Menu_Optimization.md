# Multi-Selection Context Menu Optimization and Composite Node Support

## Problem Description

The multi-selection context menu had the following issues:
- When selecting composite nodes via box selection or Ctrl+click, the selection count did not include composite nodes
- Start/stop actions in the multi-selection context menu did not include composite nodes
- "Compress to composite" and "Batch remove" options were still shown when composite nodes were selected

## Fix Solution

### Modified Files

**1. ui/canvas/canvas_view.py**

Modify `SelectedNodesList._sync` method to also include composite nodes:
```python
from ui.canvas.items.composite_node_item import CompositeNodeItem
# Now check both NodeItem and CompositeNodeItem
if isinstance(item, (NodeItem, CompositeNodeItem))
```

**2. ui/canvas/mixins/canvas_menus.py**

Modify `_show_multi_node_menu` method to dynamically adjust menu options based on whether composite nodes are selected:
```python
has_composite = any(n.startswith("composite_") for n in node_list)

if not has_composite:
    # Show only when no composite nodes: batch remove, compress to composite
```

**3. ui/main_window/node.py**

Modify `start_selected_node_by_name` and `stop_selected_node_by_name` to handle composite nodes:
- Start: via startup queue
- Stop: via `composite_manager.stop_composite`

## Context Menu Behavior After Fix

| Condition | Displayed Options |
|-----------|-------------------|
| No composite nodes | Start, Stop, Batch Remove, Compress to Composite, Decompress (if applicable), Clear Listen Config, Clear Selection |
| With composite nodes | Start, Stop, Decompress (if applicable), Clear Listen Config, Clear Selection |

## New Menu Option

- Clear Selection: Used to clear all current selection states
