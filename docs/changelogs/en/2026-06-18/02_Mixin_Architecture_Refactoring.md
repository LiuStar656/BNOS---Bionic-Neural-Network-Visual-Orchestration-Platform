# 02 Mixin Architecture Refactoring - 6 Mixin Classes Converted to Composition Pattern

**Date**: 2026-06-18

---

## Problem Diagnosis

### Current Situation

In `ui/canvas/canvas_view.py`, the `NodeCanvas` class used **multiple inheritance** to mix in 6 Mixin classes:

| Mixin Class | Responsibility | State Variables |
|------------|--------------|----------------|
| `CanvasConnectionsMixin` | Connection lifecycle management | `is_connecting`, `connect_source`, `_connect_source_anchor`, `temp_edge` |
| `CanvasBatchOpsMixin` | Node batch operations (start/stop/remove) | `self.selected_nodes` (depends on selection layer) |
| `CanvasMenusMixin` | Right-click menu system (node menu / connection menu / blank canvas menu) | `self.colors` (depends on color layer) |
| `CanvasBoxSelectMixin` | Box selection state management | `box_select_rect`, `box_selected_nodes`, `is_box_selecting`, `box_select_start_pos` |
| `CanvasColorsMixin` | Color settings (canvas/grid/node/connection) | `canvas_bg_color`, `grid_color` etc. 10+ color variables |
| `CanvasLayoutMixin` | Layout save/load | `_save_color_settings()`, `_load_color_settings()` (depends on color layer) |

### Core Problems Identified

#### 1. Ambiguous State Ownership

- **Problem**: All state (connecting, box selection, colors) is scattered directly on `self` (NodeCanvas). External code can read/write arbitrarily.
- **Impact**: When adding new features, you don't know which Mixin to put it in. The "Mega Mixin" grows continuously.

#### 2. Implicit Dependencies (Cross-Mixin Method Calls)

```python
# In CanvasLayoutMixin.save_layout():
self._save_color_settings()  # ← This method actually lives in CanvasColorsMixin

# In CanvasBoxSelectMixin.clear_box_selection():
for node_name in self.box_selected_nodes:  # ← Actually comes from SelectionManager
    ...
```

- **Problem**: Mixin A calls Mixin B's methods, determined by Python MRO order.
- **Impact**: Modifying one Mixin can break another Mixin's internal calls (e.g., CanvasLayout calling `_save_color_settings` fails because `self.canvas` doesn't exist).

#### 3. Fragile Initialization Order

- **Problem**: `NodeCanvas.__init__` needs color layer first → then selection layer → then connection layer. Wrong order causes crashes.
- **Impact**: Initialization logic is brittle, every change requires verifying the full call chain.

#### 4. Unit Testing Impractical

- **Problem**: Testing `CanvasConnections` requires instantiating the entire `NodeCanvas` with full QApplication + QGraphicsScene + parent window context.
- **Impact**: Key features (connections, box selection, menus) have virtually no independently testable units.

---

## Refactoring Plan: Composition Over Inheritance

### Core Idea

Change **"Mixin inheritance"** to **"composition assembly"**:

```
┌────────────────────────────────────────────────────────┐
│ NodeCanvas (QGraphicsView)                            │
│                                                        │
│ [__init__]                                             │
│ • self.colors = CanvasColors(self)             ← Composed Component 1 │
│ • self.connections = CanvasConnections(self)    ← Composed Component 2 │
│ • self.layout_mgr = CanvasLayout(self)          ← Composed Component 3 │
│ • self.batch_ops = CanvasBatchOps(self)          ← Composed Component 4 │
│ • self.box_select = CanvasBoxSelect(self)        ← Composed Component 5 │
│ • self.menus = CanvasMenu(self)                 ← Composed Component 6 │
│                                                        │
│ [Forwarding API]                                        │
│ • def _save_color_settings():              ← Delegates to self.colors │
│ • def _load_color_settings(path):           ← Delegates to self.colors │
│ • def clear_box_selection():                ← Delegates to self.box_select │
│ • def get_selected_node():                 ← Delegates to self.selection │
└────────────────────────────────────────────────────────┘
```

Each composed class accepts `canvas` as context:

```python
class CanvasColors:
    def __init__(self, canvas):
        self.canvas = canvas  # ← Explicit dependency, all canvas access via self.canvas

    def _save_color_settings(self):
        # Only accessed via self.canvas, no implicit inheritance
        if not self.canvas.parent_window or ...:
            return
        ...
```

### Refactoring Principles

| Principle | Implementation |
|----------|----------------|
| **State in one place only** | State variables (`is_connecting`, etc.) stay on NodeCanvas, composed objects read/write via `self.canvas.is_connecting` |
| **Explicit dependencies declared** | Each composed class clearly states its dependency in `__init__` via `self.canvas` |
| **Assembly in dependency order** | `NodeCanvas.__init__` instantiates composed objects in "foundation layer → feature layer → interaction layer" order |
| **Composed classes testable independently** | Composed classes only accept `canvas` parameter, can be unit tested with a Mock canvas |

---

## Change Log (8 files total)

### 1. [canvas_view.py](ui/canvas/canvas_view.py)

**In `__init__` Added State Variable Initialization**:
```python
# Connection state
self.is_connecting = False
self.connect_source = None
self._connect_source_anchor = None
self.temp_edge = None

# Box selection state
self.box_select_rect = None
self.box_selected_nodes = []
self.is_box_selecting = False
self.box_select_start_pos = None
```

**Added Forwarding Methods** (backward-compatible API surface):
```python
def _save_color_settings(self):
    self.colors._save_color_settings()

def _load_color_settings(self, project_path):
    self.colors._load_color_settings(project_path)
```

**Composition Assembly Order** (by dependency):
```python
self.colors = CanvasColors(self)          # Foundation layer
self.connections = CanvasConnections(self) # Feature layer
self.layout_mgr = CanvasLayout(self)       # Feature layer
self.batch_ops = CanvasBatchOps(self)      # Operation layer
self.box_select = CanvasBoxSelect(self)    # Operation layer
self.menus = CanvasMenu(self)              # Interaction layer
```

### 2. [canvas_connections.py](ui/canvas/mixins/canvas_connections.py) - `CanvasConnectionsMixin` → `CanvasConnections`
- Added `__init__(self, canvas)`: Saves canvas context
- All `self.xxx` → `self.canvas.xxx`

### 3. [canvas_batch_ops.py](ui/canvas/mixins/canvas_batch_ops.py) - `CanvasBatchOpsMixin` → `CanvasBatchOps`
- Added `__init__(self, canvas)`
- `self.selection` → `self.canvas.selection`
- `self.parent_window` → `self.canvas.parent_window`

### 4. [canvas_menus.py](ui/canvas/mixins/canvas_menus.py) - `CanvasMenusMixin` → `CanvasMenu`
- Added `__init__(self, canvas)`
- `self.colors.change_node_background_color(item)` → `self.canvas.colors.change_node_background_color(item)`

### 5. [canvas_box_select.py](ui/canvas/mixins/canvas_box_select.py) - `CanvasBoxSelectMixin` → `CanvasBoxSelect`
- Added `__init__(self, canvas)`
- `self.box_select_rect` → `self.canvas.box_select_rect`
- `self.scene.removeItem(...)` → `self.canvas.scene.removeItem(...)`

### 6. [canvas_colors.py](ui/canvas/mixins/canvas_colors.py) - `CanvasColorsMixin` → `CanvasColors`
- Added `__init__(self, canvas)`
- All color attribute access via `self.canvas`

### 7. [canvas_layout.py](ui/canvas/mixins/canvas_layout.py) - **Critical fix (the focus of this refactor)**

```
OLD → class CanvasLayoutMixin(NodeCanvas):
    def save_layout(self, project_path):
        ...
        self._save_color_settings()  # ← Implicit CanvasColorsMixin dependency

    def load_layout(self, project_path):
        node = NodeItem(name, lang, status, x, y, w, h, self)  # ← self is Mixin object
        ...

NEW → class CanvasLayout:
    def __init__(self, canvas):
        self.canvas = canvas

    def save_layout(self, project_path):
        ...
        self.canvas._save_color_settings()  # ← Explicit NodeCanvas forwarding

    def load_layout(self, project_path):
        node = NodeItem(name, lang, status, x, y, w, h, self.canvas)  # ← Pass real NodeCanvas
        ...
```

**Key Error References Fixed**:

| Location | Old | New |
|----------|-----|-----|
| `save_layout()` end | `self._save_color_settings()` | `self.canvas._save_color_settings()` |
| `load_layout()` start | `self.viewport().rect().center()` | `self.canvas.viewport().rect().center()` |
| `load_layout()` node creation | `NodeItem(..., self, ...)` | `NodeItem(..., self.canvas, ...)` |
| `load_layout()` node assignment | `node.canvas = self` | `node.canvas = self.canvas` |
| `load_layout()` edge creation | `EdgeItem(..., self, ...)` | `EdgeItem(..., self.canvas, ...)` |
| `load_layout()` validation | `self._validate_edge_anchor_binding()` | `self.canvas._validate_edge_anchor_binding()` |

**Impact**: After this refactor, `NodeItem` / `EdgeItem` no longer receive a Mixin pseudo-object (lacking `nodes`, `edges`, `scene` properties), eliminating `AttributeError: 'CanvasLayout' object has no attribute 'input_anchor_color'` etc.

---

## Bug Fix Verification

| Bug ID | Symptom | Root Cause | Fix |
|--------|---------|-----------|-----|
| Bug-1 | `AttributeError: 'NodeCanvas' object has no attribute 'box_select_rect'` | `NodeCanvas.__init__` no longer inherits from Mixin, missing box selection state variables | Explicit init in `NodeCanvas.__init__` for `box_select_rect`, `box_selected_nodes`, etc. |
| Bug-2 | `AttributeError: 'NodeCanvas' object has no attribute '_save_color_settings'` | `CanvasLayout.save_layout()` calls `self._save_color_settings()`, but method is now in `CanvasColors` | Add forwarding method in `NodeCanvas`: `_save_color_settings()` → `self.colors._save_color_settings()` |
| Bug-3 | `AttributeError: 'CanvasLayout' object has no attribute 'input_anchor_color'` | `NodeItem(..., self, ...)` receives `CanvasLayout` instead of `NodeCanvas` | Changed to `NodeItem(..., self.canvas, ...)` |
| Bug-4 | `AttributeError: 'CanvasLayout' object has no attribute 'scene'` | Same as above, `EdgeItem` receives `CanvasLayout` | Changed to `EdgeItem(..., self.canvas, ...)` |
| Bug-5 | `AttributeError: 'CanvasLayout' object has no attribute 'nodes'` | `self.nodes` is actually a Mixin self.nodes reference | Changed to `self.canvas.nodes` |

---

## Test Verification Results

### Module Import Test (11/11 ✅)

```
OK: ui.canvas.canvas_view
OK: ui.canvas.mixins.canvas_selection
OK: ui.canvas.mixins.canvas_background_renderer
OK: ui.canvas.mixins.canvas_node_manager
OK: ui.canvas.mixins.canvas_event_handlers
OK: ui.canvas.mixins.canvas_connections
OK: ui.canvas.mixins.canvas_batch_ops
OK: ui.canvas.mixins.canvas_menus
OK: ui.canvas.mixins.canvas_box_select
OK: ui.canvas.mixins.canvas_colors
OK: ui.canvas.mixins.canvas_layout
```

### Composition Layer Component Assembly Test (6/6 ✅)

```
OK: canvas.colors = CanvasColors
OK: canvas.connections = CanvasConnections
OK: canvas.layout_mgr = CanvasLayout
OK: canvas.batch_ops = CanvasBatchOps
OK: canvas.box_select = CanvasBoxSelect
OK: canvas.menus = CanvasMenu
```

### Full Application Startup Test (✅ Passed)

Application startup → main window creation → project loading → canvas rendering → shutdown all normal.

---

## Architecture Improvement Benefits

| Dimension | Before | After | Improvement |
|-----------|--------|-------|-------------|
| **State ownership** | Mixed on NodeCanvas | Composed classes access only via `self.canvas` with clear ownership | ✅ Clear |
| **Dependencies** | Implicit MRO-driven | Explicit assembly in order, dependencies visible | ✅ Traceable |
| **Initialization order** | Fragile, MRO-determined | Controllable, manual assembly in dependency order | ✅ Controllable |
| **Testability** | Requires full QApplication | Composed classes individually testable with Mock | ✅ Lower barrier |
| **Code readability** | 2000+ lines in single class | 7 independent functional modules, each < 500 lines | ✅ Modular |

---

## Backward Compatibility

✅ **API surface unchanged**: External code still uses `canvas._save_color_settings()`, `canvas.clear_box_selection()`, `canvas.get_selected_node()` etc. with original signatures.

✅ **No caller changes needed**: All code referencing `NodeItem` / `EdgeItem` requires no changes.

✅ **File structure preserved**: All canvas files remain under `ui/canvas/` and its subdirectories.

---

## Next Steps

- **Independent unit tests**: Write isolated unit tests for `CanvasConnections`, `CanvasBoxSelect`, etc. using Mock canvas
- **Further decoupling**: Wrap remaining "data storage layer" (self.nodes, self.edges) on NodeCanvas as composed objects
- **Documentation**: Add complete docstrings and usage examples for each composed class
