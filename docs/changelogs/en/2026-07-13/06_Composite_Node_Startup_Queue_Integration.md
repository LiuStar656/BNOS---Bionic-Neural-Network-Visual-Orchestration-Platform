# 06 Composite Node Startup Queue Integration

## Problem Description

Composite nodes were not going through the startup queue, causing:
1. No startup notification (toast)
2. Status not updated
3. Unable to benefit from queue features like concurrency control and retry mechanism

## Fix Solution

### 6.1 NodeStartWorker Auto Type Detection

**File**: `ui/core/node/node_startup_queue.py`

`NodeStartWorker.run()` automatically selects startup method based on `composite_` prefix.

**Code Change**:
```python
def run(self):
    node_name = self._item.node_name
    if node_name.startswith("composite_"):
        self._start_composite(node_name)
    else:
        self._start_regular_node(node_name)
```

### 6.2 New Composite Startup Method

**File**: `ui/core/node/node_startup_queue.py`

Added `_start_composite()` method to start composite nodes via `CompositeNodeManager`.

**Code Change**:
```python
def _start_composite(self, comp_id: str):
    from ui.core.node.composite_node import CompositeNode
    ...
    mgr = getattr(main_window.canvas, "_composite_manager", None)
    runtime = mgr.get_runtime(comp_id) or "inprocess"
    if runtime == "inprocess":
        success, err = mgr.start_inprocess(comp_id)
    else:
        success, err = mgr.start_process_mode(comp_id)
    self.finished.emit(success, err)
```

### 6.3 Context Menu Start via Queue

**File**: `ui/canvas/mixins/canvas_menus.py`

`_composite_start()` changed to call `startup_queue.enqueue()`.

**Code Change**:
```python
def _composite_start(self, mgr, comp_id):
    from ui.core.node.node_startup_queue import startup_queue
    startup_queue.enqueue(comp_id)
    self.show_toast(t("_k_node_starting").format(name=comp_id), "info")
```

### 6.4 Node List Start via Queue

**File**: `ui/panels/node_list_context.py`

`_start_composite_group()` changed to call `startup_queue.enqueue()`.

### 6.5 Main Window Event Handling for Composite

**File**: `ui/main_window/node.py`

Updated `_on_queue_node_starting`, `_on_queue_node_started`, `_on_queue_node_failed`, added `_update_composite_status()` method.

### 6.6 CompositeNodeItem update_status Method

**File**: `ui/canvas/items/composite_node_item.py`

Added `update_status()` method to update status and apply style.

**Code Change**:
```python
def update_status(self, status):
    self.status = status
    if hasattr(self, '_style'):
        self._style.apply_status(self, status)
```

## Modified Files

| File | Change |
|------|--------|
| `ui/core/node/node_startup_queue.py` | Added `_start_composite()`; `run()` auto-detects node type |
| `ui/canvas/mixins/canvas_menus.py` | `_composite_start()` via startup queue |
| `ui/panels/node_list_context.py` | `_start_composite_group()` via startup queue |
| `ui/main_window/node.py` | Event handling for composite nodes; `_update_composite_status()` |
| `ui/canvas/items/composite_node_item.py` | Added `update_status()` method |

## Verification

After fix:
- ✅ Composite nodes enqueued on startup
- ✅ Startup notification toast shown
- ✅ Node list group color updated (starting → running)
- ✅ Canvas node status style updated

---

**Last Updated**: 2026-07-13
