# Node Startup Queue and Batch Stop Fixes

---

## Update Overview

This update fixes multiple issues related to node startup queue and batch stop functionality, ensuring stability and correctness of node lifecycle management.

---

## Fixes

### 1. Right-click Menu Node Detection Fix

**Problem**: Right-clicking on canvas nodes had no response

**Fix**: Modified `contextMenuEvent` method to use `items()` instead of `itemAt()` to get all overlapping items, prioritizing `NodeItem` first, then `EdgeItem`

**File**: `ui/canvas/mixins/canvas_menus.py`

---

### 2. `box_selected_nodes` Attribute Reference Fix

**Problem**: Right-click menu referenced non-existent attribute `self.canvas.selection.box_selected_nodes`

**Fix**: Changed to correct path `self.canvas.box_selected_nodes`

**Files**: `ui/canvas/mixins/canvas_menus.py`, `ui/canvas/mixins/canvas_batch_ops.py`

---

### 3. New Node Feature Fix

**Problem**: New node creation in right-click menu had no response

**Fix**: Pass `self._make_ctx()` context for new node actions, ensuring `context.extra` contains `canvas` object

**File**: `ui/canvas/mixins/canvas_menus.py`

---

### 4. Batch Stop Node Status Detection Fix

**Problem**: Batch stop only stopped nodes in `running` and `idle` states, ignoring `queued` and `starting` states

**Fix**: Extended status detection to include all non-`stopped` states

**File**: `ui/canvas/mixins/canvas_batch_ops.py`

---

### 5. Unable to Restart After Stop Fix

**Problem**: After stopping a node, restarting showed "加入队列失败" (Failed to enqueue)

**Fix**: Remove node from startup queue when stopping (`startup_queue.dequeue(node_name)`)

**File**: `ui/main_window/node.py`

---

### 6. Startup Queue Scheduler State Reset Fix

**Problem**: Second batch start showed "已加入启动列表" (Added to startup list) but didn't actually start

**Fix**: Set `self._stopped = True` when queue is empty, ensuring scheduler restarts on next `enqueue` call

**File**: `ui/core/node_startup_queue.py`

---

### 7. Batch Stop Closure Variable Capture Fix

**Problem**: Batch stop only stopped the last selected node

**Fix**: Use default parameter value to capture loop variable `lambda n=node_name: ...`

**File**: `ui/main_window/node.py`

---

### 8. Batch Stop Background Thread Implementation

**Problem**: `stop_node_process` used synchronous `subprocess.run`, blocking the GUI and causing incomplete batch stops

**Fix**: Created `NodeStopWorker` background thread to execute stop operations asynchronously

**File**: `ui/main_window/node.py`

---

### 9. Thread Reference Preservation Fix

**Problem**: `NodeStopWorker` threads were garbage collected after creation

**Fix**: Added `_stop_node_workers` list to preserve thread references

**Files**: `ui/main_window/__main__.py`, `ui/main_window/node.py`, `ui/main_window/lifecycle.py`

---

### 10. `execute_node_stop` Multi-node Handling Fix

**Problem**: `execute_node_stop` function in ActionRegistry only handled single node case, ignoring `ctx.node_list`

**Fix**: Added `elif ctx.node_list:` branch to iterate over all nodes and call `stop_selected_node_by_name`

**File**: `ui/core/actions/node/_lifecycle.py`

---

## Changed File List

| File | Change Type | Description |
|------|-------------|-------------|
| `ui/canvas/mixins/canvas_menus.py` | Modified | Right-click menu node detection, attribute reference, new node context passing |
| `ui/canvas/mixins/canvas_batch_ops.py` | Modified | `box_selected_nodes` attribute reference, batch stop status detection |
| `ui/core/node_startup_queue.py` | Modified | State reset when queue is empty |
| `ui/main_window/node.py` | Modified | Dequeue on stop, closure variable capture, background thread implementation |
| `ui/main_window/__main__.py` | Modified | Added `_stop_node_workers` list |
| `ui/main_window/lifecycle.py` | Modified | Wait for stop threads to complete during shutdown |
| `ui/core/actions/node/_lifecycle.py` | Modified | Multi-node handling support in `execute_node_stop` |

---

## Verification Results

✅ Right-click menu works correctly (single node, multi-node, canvas background)
✅ New node creation works properly
✅ Batch stop works for all selected nodes (supports running/idle/queued/starting states)
✅ Nodes can be restarted after stopping
✅ Second batch start executes correctly
✅ Thread references properly preserved, no `QThread: Destroyed while thread '' is still running` errors