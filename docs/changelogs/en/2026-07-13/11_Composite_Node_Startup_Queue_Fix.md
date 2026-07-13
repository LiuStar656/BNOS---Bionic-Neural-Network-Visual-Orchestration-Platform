# Composite Node Startup Queue Integration Fix

## Problem Description

Composite node startup had the following issues:
- Right-click menu startup for composite nodes did not go through the startup queue
- No startup toast notification was displayed
- Status was not updated after startup (node list group color, canvas node status)

## Root Cause

The `_composite_start` and `_start_composite_group` methods directly called `mgr.start_inprocess()` without going through the startup queue, resulting in no startup notifications and status updates.

## Fix Solution

### Modified Files

**1. ui/canvas/mixins/canvas_menus.py**

Change `_composite_start` to start via startup queue:
```python
startup_queue.enqueue(comp_id)
# Get main window and show startup notification
app = QApplication.instance()
main_window = app.activeWindow()
main_window.show_toast(t("_k_node_starting").format(name=comp_id), "info")
```

**2. ui/panels/node_list_context.py**

Change `_start_composite_group` to start via startup queue

**3. ui/main_window/node.py**

Update event handlers, add `_update_composite_status` method to handle composite node status updates:
- Update node list group color (starting → running)
- Update canvas node status style

**4. ui/canvas/items/composite_node_item.py**

Add `update_status` method for updating composite node runtime status display

**5. ui/main_window/node.py**

Modify `start_selected_node_by_name` and `stop_selected_node_by_name` to handle composite nodes:
- Start: via startup queue
- Stop: via `composite_manager.stop_composite`

## Behavior After Fix

- ✅ Composite nodes are added to startup queue when starting
- ✅ Startup toast notification is displayed
- ✅ Node list group color is updated
- ✅ Canvas node status style is updated
- ✅ Start/stop actions can act on composite nodes
