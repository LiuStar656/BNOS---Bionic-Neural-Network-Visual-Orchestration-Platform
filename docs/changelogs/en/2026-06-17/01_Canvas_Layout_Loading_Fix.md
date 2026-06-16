# Canvas Layout Loading Fix (try/finally protection + Scene/Viewport force refresh)

---

## Problem Description

### Symptom 1: Canvas has nodes but they don't display
- Nodes were read from `canvas_layout.json` by `load_layout` and added to `QGraphicsScene` via `NodeItem`
- But nodes are not visible in the UI
- After reopening a second project, the canvas displays normally

### Symptom 2: Nodes/edges don't render immediately after changes
- Dragging nodes, adding/removing edges require a click/zoom to trigger a refresh
- `QGraphicsView`'s `setUpdatesEnabled(False)` was never restored to `True` under exceptional conditions

### Symptom 3: Scene doesn't display after nodes/edges are loaded
- `canvas_layout.json` exists and contains node position information
- Node count, positions, and sizes are shown correctly in logs
- But the render layer is empty — `QGraphicsScene` never triggers `paintEvent`

---

## Root Cause Analysis

### Root Cause 1: `setUpdatesEnabled(False)` has no `finally` protection

```python
# Before fix
self.setUpdatesEnabled(False)
# ... loading logic (may throw exceptions)
self.setUpdatesEnabled(True)   # If an exception is thrown mid-way, this line never executes
```

- If any step in `load_layout` throws an exception (e.g., malformed `canvas_layout.json`, `NodeItem` construction failure)
- `setUpdatesEnabled(True)` is never called
- `QGraphicsView` is left in "updates disabled" state, **never to redraw**

### Root Cause 2: Missing `QGraphicsScene.update()` force scene refresh

```python
# Before: Only called update() after NodeItem was added to scene
node = NodeItem(...)
self.scene.addItem(node)
# Scene may cache render results; newly added items don't immediately trigger paintEvent
```

- `QGraphicsScene.addItem()` only inserts items into the index
- Need to explicitly call `scene.update(sceneRect)` to notify the render layer of new content
- This is especially important for batch-loading scenarios with many nodes in `canvas_layout.json`

### Root Cause 3: `viewport()` caching issue

- `QGraphicsView`'s viewport (`QWidget`) has independent update mechanisms
- Even if `scene.update()` fires, without a viewport redraw the visuals may still be empty
- Need additional call to `self.viewport().update()`

### Root Cause 4: Canvas dock never explicitly displayed

- After `CanvasHost` removes `_blank_placeholder`, `centralWidget` is set to `None`
- Qt's `QDockWidget` needs a **valid central widget** to dock and render correctly
- Even if the dock was created and added to the layout, without a central widget rendering can fail

---

## Fix Plan

### Fix 1: `load_layout` adds `try/finally` protection

```python
# ui/canvas/canvas_layout.py

try:
    self.setUpdatesEnabled(False)
    # ... all loading logic:
    # 1. Read canvas_layout.json
    # 2. Create NodeItem
    # 3. Create edges
    # 4. Restore view state (zoom/scroll)
except json.JSONDecodeError:
    logger.warning("canvas_layout.json format error")
except Exception as e:
    logger.exception(f"load_layout unexpected exception: {e}")
finally:
    # Success or failure, updates must be restored
    self.setUpdatesEnabled(True)
    # Force scene refresh (ensure newly added nodes render immediately)
    if hasattr(self, 'scene') and self.scene is not None:
        self.scene.update(self.scene.sceneRect())
    # Force viewport redraw
    if hasattr(self, 'viewport') and callable(self.viewport):
        self.viewport().update()
```

### Fix 2: `CanvasHost._remove_blank_placeholder` adds transparent central placeholder widget

```python
# ui/core/canvas_host.py

# Problem: With centralWidget = None, dock widgets can't dock correctly
# Fix: Create a transparent QWidget as central placeholder
central_placeholder = QWidget(self)
central_placeholder.setStyleSheet("background: transparent;")
central_placeholder.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
central_placeholder.setObjectName("canvas_host_central_placeholder")
self.setCentralWidget(central_placeholder)
```

### Fix 3: Canvas dock explicit activation

```python
# ui/core/canvas_host.py - end of _create_canvas_dock method

# Explicitly show canvas dock and canvas widget
canvas_dock.show()
canvas_dock.raise_()
canvas.show()
canvas.raise_()
canvas.setFocus()
```

### Fix 4: Remove logic that "auto-creates nodes from nodes_data"

```python
# The previous logic was wrong:
# It iterated parent_window.nodes_data and auto-created NodeItem + arranged on canvas
# for nodes not in canvas_layout.json

# Correct behavior: canvas nodes only come from canvas_layout.json (user manually dragged/positioned)
# Other project nodes only appear in the Node List Panel, not automatically on the canvas

# Removed:
# - Collecting nodes requiring auto-arrange logic
# - start_x/start_y auto-arrange calculation
# - NodeItem creation and addition
# - auto_arranged_count counting
```

### Fix 5: Add detailed diagnostic logging

```python
# ui/canvas/canvas_layout.py - in load_layout finally block

logger.info(
    f"[load_layout] canvas node diagnosis:\n"
    f"  Total nodes: {len(self.nodes)}\n"
    f"  Total edges: {len(self.edges)}\n"
    f"  sceneRect: {self.scene.sceneRect()}"
)

# Output each node's position and visibility (first 5 only, avoid log spam)
for i, (name, node) in enumerate(list(self.nodes.items())[:5]):
    pos = node.pos()
    rect = node.rect() if hasattr(node, 'rect') else '(n/a)'
    visible = node.isVisible() if hasattr(node, 'isVisible') else True
    z = node.zValue() if hasattr(node, 'zValue') else 0
    logger.info(
        f"  [{i+1}] {name}: pos=({pos.x():.0f},{pos.y():.0f}) "
        f"visible={visible} z={z}"
    )
if len(self.nodes) > 5:
    logger.info(f"  ... plus {len(self.nodes) - 5} more nodes")
```

---

## Modified Files List

| File | Method/Area | Change |
|------|-------------|--------|
| `ui/canvas/canvas_layout.py` | `load_layout` docstring | Updated: nodes only restored from `canvas_layout.json` |
| `ui/canvas/canvas_layout.py` | `load_layout` try/except | Wrapped in `try/finally` to protect all loading logic |
| `ui/canvas/canvas_layout.py` | `load_layout` finally | `setUpdatesEnabled(True)` + `scene.update(sceneRect)` + `viewport().update()` |
| `ui/canvas/canvas_layout.py` | `load_layout` finally | Detailed diagnostic logs (node positions, visibility) |
| `ui/canvas/canvas_layout.py` | `load_layout` body | Removed logic that "auto-creates nodes from nodes_data" |
| `ui/core/canvas_host.py` | `_remove_blank_placeholder` | Added transparent central placeholder widget (replacing `centralWidget = None`) |
| `ui/core/canvas_host.py` | `_create_canvas_dock` | Explicit `show()` / `raise_()` / `setFocus()` at end |

---

## Verification Methods

### Prerequisites
1. Have a valid project (`canvas_layout.json` contains node position information)
2. Delete the project's `canvas_layout.json` (or keep a version with content, test both)

### Test 1: With canvas_layout.json
```
1. Start the application (automatically opens the project)
2. Check log output:
   [auto_open] Worker finished, found 6 nodes
   [auto_open] nodes_data populated (6 nodes), creating canvas
   [load_layout] Read canvas_layout.json: 2 node positions
   [load_layout] Restored from layout: python_node_1 (pos: 380, -140)
   ...
   [load_layout] Canvas node diagnosis:
     python_node_1: pos=(380,-140) visible=True z=2
3. Visual check: canvas should show 2 nodes, positions match canvas_layout.json
4. Drag any node to new position → wait 500ms → canvas_layout.json updated
5. Restart app → node is restored at new position
```
**Expected**: ✅ Nodes display correctly, positions correct, saved and restored after move

### Test 2: Without canvas_layout.json
```
1. Delete project's canvas_layout.json
2. Start the application
3. Logs show:
   [load_layout] canvas_layout.json does not exist, canvas starts empty (please drag nodes from Node List Panel)
4. Canvas is empty; Node List Panel shows all project nodes
5. Drag 2 nodes from list to canvas
6. Wait 500ms → canvas_layout.json is created and written with node positions
7. Restart → canvas has those 2 nodes
```
**Expected**: ✅ Starts empty, manually dragged nodes saved, restored after restart

### Test 3: Multi-project switching
```
1. Open project A (canvas_layout.json has nodes)
2. Open project B (canvas_layout.json has different nodes)
3. Switch A/B canvas tabs
4. Each tab displays its own nodes
```
**Expected**: ✅ Nodes displayed correctly during switching, no cross-interference

### Test 4: Syntax verification
```
python -c "import ast; ast.parse(open('ui/canvas/canvas_layout.py').read()); print('OK')"
python -c "import ast; ast.parse(open('ui/core/canvas_host.py').read()); print('OK')"
```
**Expected**: ✅ Both files output OK

---

## Key Design Decisions

### Decision 1: Canvas nodes come only from canvas_layout.json
- **Reason**: The canvas is the user's "visual workspace"; only manually dragged/positioned nodes should appear there
- **Impact**: All project nodes are shown in the "Node List Panel"; only user-selected nodes appear on the canvas
- **Rollback**: If "show all nodes automatically on canvas" is needed later, re-add NodeItem creation logic from `nodes_data` in `load_layout`

### Decision 2: Use try/finally instead of try/except for setUpdatesEnabled
- **Reason**: `setUpdatesEnabled(True)` must be called in **all cases** (including exceptions)
- **Impact**: No functional impact, just improved code robustness
- **Rollback**: Remove try/finally to return to old behavior

### Decision 3: Refresh both scene and viewport in finally block
- **Reason**: Qt's render layer has multiple levels of caching (scene's BSP tree, viewport pixel buffer)
- **Impact**: May cause slight extra rendering overhead, but completely acceptable vs. the critical "empty canvas" problem
- **Rollback**: If performance testing shows excessive refreshes, keep only `scene.update(sceneRect())`
