# Canvas Module Directory Reorganization (Composition Layer + mixins + drawing Subdirectories)

---

## Background

The `ui/canvas/` root directory had accumulated 13 Python files with overlapping responsibilities, without any directory-level categorization:

- `canvas_view.py` / `canvas_process.py` (entry / main class)
- `canvas_connections.py` / `canvas_box_select.py` / `canvas_batch_ops.py` / `canvas_menus.py` / `canvas_layout.py` / `canvas_colors.py` (Mixin layer)
- `canvas_selection.py` / `canvas_background_renderer.py` / `canvas_node_manager.py` / `canvas_event_handlers.py` (composition layer, previously split out of NodeCanvas)
- `controllers.py` (controller layer)
- `draw_layer.py` / `draw_toolbar.py` + `graphic_items/` (drawing layer)

**Issues**:
1. Too many files at the root level — newcomers cannot quickly recognize the layering of responsibilities
2. Mixin / composition layer / drawing layer / rendering items were four different things with no directory separation
3. Import paths like `from ui.canvas.canvas_layout import ...` had misleading "one file at root" semantics

---

## Target Structure

```
ui/canvas/
├── __init__.py          ← entry + backward-compat shim (sys.modules aliases)
├── canvas_view.py       ← NodeCanvas main class (composite assembler + Qt virtual method forwarding)
├── canvas_process.py    ← subprocess entry (IPC registration)
│
├── mixins/              ← logic layer (the 11 files previously scattered at root)
│   ├── canvas_connections.py
│   ├── canvas_box_select.py
│   ├── canvas_batch_ops.py
│   ├── canvas_menus.py
│   ├── canvas_layout.py
│   ├── canvas_colors.py
│   ├── canvas_selection.py
│   ├── canvas_background_renderer.py
│   ├── canvas_node_manager.py
│   ├── canvas_event_handlers.py
│   └── controllers.py   ← 7 Canvas controllers (CanvasConnectionController etc.)
│
├── drawing/             ← drawing layer
│   ├── draw_layer.py
│   ├── draw_toolbar.py
│   └── graphic_items/
│       ├── __init__.py
│       ├── _base.py
│       ├── arrow.py
│       ├── polygon.py
│       ├── rect.py
│       ├── round_rect.py
│       └── text.py
│
├── items/               ← pure UI rendering (NodeItem / EdgeItem / AnchorItem / node styles)
│   └── styles/
│
└── parameter_widgets/   ← parameter editing controls (unchanged)
```

**The root directory now holds only 3 Python files** (`__init__.py` / `canvas_view.py` / `canvas_process.py`), clean and obvious.

---

## Implementation Plan

### 1. File Moves

| Old path | New path | Notes |
|----------|----------|-------|
| `ui/canvas/canvas_connections.py` | `ui/canvas/mixins/canvas_connections.py` | Connection Mixin |
| `ui/canvas/canvas_box_select.py` | `ui/canvas/mixins/canvas_box_select.py` | Box-select Mixin |
| `ui/canvas/canvas_batch_ops.py` | `ui/canvas/mixins/canvas_batch_ops.py` | Batch-ops Mixin |
| `ui/canvas/canvas_menus.py` | `ui/canvas/mixins/canvas_menus.py` | Context-menu Mixin |
| `ui/canvas/canvas_layout.py` | `ui/canvas/mixins/canvas_layout.py` | Layout persistence Mixin |
| `ui/canvas/canvas_colors.py` | `ui/canvas/mixins/canvas_colors.py` | Color settings Mixin |
| `ui/canvas/canvas_selection.py` | `ui/canvas/mixins/canvas_selection.py` | Selection + command recording (composition) |
| `ui/canvas/canvas_background_renderer.py` | `ui/canvas/mixins/canvas_background_renderer.py` | Background + grid (composition) |
| `ui/canvas/canvas_node_manager.py` | `ui/canvas/mixins/canvas_node_manager.py` | Node CRUD (composition) |
| `ui/canvas/canvas_event_handlers.py` | `ui/canvas/mixins/canvas_event_handlers.py` | Mouse/keyboard events (composition) |
| `ui/canvas/controllers.py` | `ui/canvas/mixins/controllers.py` | 7 feature-dimension controllers |
| `ui/canvas/draw_layer.py` | `ui/canvas/drawing/draw_layer.py` | Drawing layer entry |
| `ui/canvas/draw_toolbar.py` | `ui/canvas/drawing/draw_toolbar.py` | Drawing toolbar UI |
| `ui/canvas/graphic_items/` | `ui/canvas/drawing/graphic_items/` | Drawing primitive collection (whole dir) |

### 2. Import Rewrites inside canvas_view.py

All Mixin / composition / drawing layer imports inside `NodeCanvas.__init__` were rewritten to the new paths:

```python
# OLD
from ui.canvas.canvas_colors import CanvasColorsMixin
from ui.canvas.canvas_layout import CanvasLayoutMixin
from ui.canvas.draw_layer import DrawLayer
from ui.canvas.canvas_selection import SelectionManager
from ui.canvas.canvas_background_renderer import BackgroundRenderer
from ui.canvas.canvas_node_manager import NodeManager
from ui.canvas.canvas_event_handlers import EventHandlers
# ...
from ui.canvas.controllers import CanvasConnectionController  # inside _init_controllers

# NEW
from ui.canvas.mixins.canvas_colors import CanvasColorsMixin
from ui.canvas.mixins.canvas_layout import CanvasLayoutMixin
from ui.canvas.mixins.canvas_connections import CanvasConnectionsMixin
from ui.canvas.mixins.canvas_box_select import CanvasBoxSelectMixin
from ui.canvas.mixins.canvas_batch_ops import CanvasBatchOpsMixin
from ui.canvas.drawing.draw_layer import DrawLayer
from ui.canvas.mixins.canvas_selection import SelectionManager
from ui.canvas.mixins.canvas_background_renderer import BackgroundRenderer
from ui.canvas.mixins.canvas_node_manager import NodeManager
from ui.canvas.mixins.canvas_event_handlers import EventHandlers
# ...
from ui.canvas.mixins.controllers import CanvasConnectionController
```

### 3. Backward-Compatibility Shim (the core piece)

To avoid breaking any existing direct references to `ui.canvas.canvas_xxx` / `ui.canvas.draw_layer` / `ui.canvas.graphic_items`, a `sys.modules` alias block was injected into `ui/canvas/__init__.py`:

```python
# ui/canvas/__init__.py
import sys

# Register sys.modules aliases so that:
#   from ui.canvas.canvas_layout import CanvasLayoutMixin  (old path)
# resolves identically to:
#   from ui.canvas.mixins.canvas_layout import CanvasLayoutMixin  (new path)
_COMPAT_MAP = {
    # mixins / composition
    "ui.canvas.canvas_connections":      "ui.canvas.mixins.canvas_connections",
    "ui.canvas.canvas_box_select":       "ui.canvas.mixins.canvas_box_select",
    "ui.canvas.canvas_batch_ops":        "ui.canvas.mixins.canvas_batch_ops",
    "ui.canvas.canvas_menus":            "ui.canvas.mixins.canvas_menus",
    "ui.canvas.canvas_layout":           "ui.canvas.mixins.canvas_layout",
    "ui.canvas.canvas_colors":           "ui.canvas.mixins.canvas_colors",
    "ui.canvas.canvas_selection":        "ui.canvas.mixins.canvas_selection",
    "ui.canvas.canvas_background_renderer": "ui.canvas.mixins.canvas_background_renderer",
    "ui.canvas.canvas_node_manager":     "ui.canvas.mixins.canvas_node_manager",
    "ui.canvas.canvas_event_handlers":   "ui.canvas.mixins.canvas_event_handlers",
    # controllers
    "ui.canvas.controllers":             "ui.canvas.mixins.controllers",
    # drawing
    "ui.canvas.draw_layer":              "ui.canvas.drawing.draw_layer",
    "ui.canvas.draw_toolbar":            "ui.canvas.drawing.draw_toolbar",
    "ui.canvas.graphic_items":           "ui.canvas.drawing.graphic_items",
}

for alias, real in _COMPAT_MAP.items():
    try:
        mod = __import__(real, fromlist=["_"])
        sys.modules.setdefault(alias, mod)
    except Exception:
        pass
```

**Key properties**:
- `sys.modules.setdefault` — registers only if the alias isn't already registered, skips otherwise
- Module is first truly imported, *then* aliased, so `alias is real` (both names refer to the **same** module object — no "same file imported twice" issue)
- After `import ui.canvas.canvas_layout as mod_old` and `import ui.canvas.mixins.canvas_layout as mod_new`, `mod_old is mod_new` evaluates to `True`

**References into `items/` remain untouched** — those files already lived in a subdirectory, requiring no shim.

### 4. Header-docstring in canvas_view.py

Updated the architectural description at the top of `canvas_view.py` to reflect the new `ui/canvas/` layout, as a living document.

---

## File Change Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `ui/canvas/__init__.py` | Heavily modified | New `sys.modules` alias registration; retains NodeCanvas export |
| `ui/canvas/canvas_view.py` | Partially modified | Header description + all import paths point to the new subdirs |
| `ui/canvas/mixins/` (11 files) | New | Physically moved from the root; no logic changes |
| `ui/canvas/drawing/` (3 files + graphic_items/) | New | Physically moved from the root |
| 13 old files at root (11 .py files + draw_layer.py + draw_toolbar.py + graphic_items/) | Deleted | Removed once relocation was verified |

**No business logic was modified** — only physical file relocation, import-path rewriting, and the compatibility shim in `__init__.py`.

---

## Verification

### Test 1 — Python import check (standalone script)
```python
import sys
sys.path.insert(0, ".")

# New paths
from ui.canvas.canvas_view import NodeCanvas
from ui.canvas.mixins.canvas_layout import CanvasLayoutMixin
from ui.canvas.mixins.canvas_connections import CanvasConnectionsMixin
from ui.canvas.mixins.canvas_selection import SelectionManager
from ui.canvas.mixins.canvas_background_renderer import BackgroundRenderer
from ui.canvas.mixins.canvas_node_manager import NodeManager
from ui.canvas.mixins.canvas_event_handlers import EventHandlers
from ui.canvas.mixins.controllers import CanvasConnectionController
from ui.canvas.drawing.draw_layer import DrawLayer
from ui.canvas.drawing.draw_toolbar import DrawToolbar
from ui.canvas.drawing.graphic_items import GraphicBase
print("[OK] all new-path imports")

# Old paths (backward-compat check)
from ui.canvas.canvas_layout import CanvasLayoutMixin as CL2
from ui.canvas.canvas_menus import CanvasMenusMixin
from ui.canvas.canvas_connections import CanvasConnectionsMixin
from ui.canvas.draw_layer import DrawLayer as DL2
from ui.canvas.controllers import CanvasConnectionController as CCC2
from ui.canvas.canvas_selection import SelectionManager as SM2
from ui.canvas.graphic_items import GraphicBase as GB2
print("[OK] all old-path imports (backward-compatible)")

# Module-alias identity check
import ui.canvas.canvas_layout as mod_old
import ui.canvas.mixins.canvas_layout as mod_new
assert mod_old is mod_new, "module alias mismatch!"
print("[OK] old/new paths resolve to the same module object")
```
**Expected**: ✅ Three `[OK]` lines, zero `ImportError`

### Test 2 — Application start-up (full launch path)
```bash
python bnos_console.py
```
**Expected**: ✅ Normal start; confirm key log lines:
```
[canvas_view.py] Canvas controller composite layer activated (7 controllers, delegation pattern)
[canvas_view.py] NodeCanvas initialized (composition: selection/background/node/event)
[canvas_layout.py] [load_layout] canvas_layout.json read: N node positions
[canvas_layout.py] [load_layout] scene refreshed, viewport refreshed
[canvas_host.py]  CanvasHost: canvas Dock created (top dock)
```
✅ No `ImportError: cannot import name 'xxx' from 'ui.canvas.xxx'`

### Test 3 — Hands-on sub-system verification
- Drag a new node from the node list → `NodeManager.add_node_to_canvas` → node appears → `canvas_layout.json` saved after 500 ms
- Drag a node around → canvas scrolls smoothly and node redraws (`BackgroundRenderer` / `EventHandlers` work)
- Ctrl+click multi-select → `SelectionManager.on_node_selected` works; selection highlight is correct
- Right-click menu → `CanvasMenusMixin` works
- Draw an edge → `CanvasConnectionsMixin` + `CanvasConnectionController` work
- Switch between two project canvas tabs → separate layouts load correctly

### Test 4 — AST syntax check
```bash
python -c "import ast; [ast.parse(open(f).read()) for f in ['ui/canvas/__init__.py','ui/canvas/canvas_view.py','ui/canvas/canvas_process.py','ui/canvas/mixins/canvas_layout.py','ui/canvas/mixins/controllers.py','ui/canvas/drawing/draw_layer.py']]; print('OK')"
```
**Expected**: ✅ prints `OK`

---

## Key Design Decisions

### Decision 1 — Keep a backward-compat shim (sys.modules aliases)
- **Why**: Other project files (and hypothetical future third-party code) may `from ui.canvas.canvas_layout import ...`. A hard cut-off breaks all of those references.
- **Impact**: Zero functional impact; adds a single `__import__` per alias at module-load time — cost is negligible
- **Rollback**: If one day we're certain nothing external depends on the old paths, just delete the `_COMPAT_MAP` block

### Decision 2 — Keep `canvas_view.py` and `canvas_process.py` at the root
- **Why**: They are the "entry files" of the whole `ui.canvas` module; placing them at the root makes the semantics clearer. Additionally `ui/main_window/ipc.py` registers `ui/canvas/canvas_process.py` as an IPC subprocess path — leaving it there avoids unnecessary changes.
- **Rollback**: Moving them into a subdirectory like `ui/canvas/app/` is a possible future refactor; we simply chose not to do it now.

### Decision 3 — Place `controllers.py` inside `mixins/` rather than giving it its own directory
- **Why**: The 7 classes in `controllers.py` (`CanvasConnectionController` etc.) are essentially "a different take on Mixins" — functional-dimensioned compositors. They are small (≈100 lines), and a standalone `ui/canvas/controllers/` directory would fragment the layout. Grouping with `mixins/` keeps search paths tight.
- **Rollback**: If `controllers.py` grows beyond ≈500 lines, it's trivial to split it into its own directory (just update the alias path in `__init__.py` and move the file).

### Decision 4 — Move the entire `graphic_items/` directory into `drawing/`
- **Why**: `graphic_items` are the drawing layer's primitives (arrows / rectangles / circles / polygons / text), sitting at the same abstraction level as `draw_layer.py` and `draw_toolbar.py`. They belong together.
- **Rollback**: None.

---

## Backward-Compatibility Matrix

| Old import style | Still works | Notes |
|------------------|-------------|-------|
| `from ui.canvas.canvas_view import NodeCanvas` | ✅ | unchanged location |
| `from ui.canvas.canvas_process import ...` | ✅ | unchanged location |
| `from ui.canvas.items.node_item import NodeItem` | ✅ | `items/` subdir kept as-is |
| `from ui.canvas.canvas_layout import CanvasLayoutMixin` | ✅ | sys.modules alias |
| `from ui.canvas.canvas_menus import CanvasMenusMixin` | ✅ | sys.modules alias |
| `from ui.canvas.canvas_connections import CanvasConnectionsMixin` | ✅ | sys.modules alias |
| `from ui.canvas.canvas_colors import CanvasColorsMixin` | ✅ | sys.modules alias |
| `from ui.canvas.canvas_selection import SelectionManager` | ✅ | sys.modules alias |
| `from ui.canvas.canvas_background_renderer import BackgroundRenderer` | ✅ | sys.modules alias |
| `from ui.canvas.canvas_node_manager import NodeManager` | ✅ | sys.modules alias |
| `from ui.canvas.canvas_event_handlers import EventHandlers` | ✅ | sys.modules alias |
| `from ui.canvas.controllers import CanvasConnectionController` | ✅ | sys.modules alias |
| `from ui.canvas.draw_layer import DrawLayer` | ✅ | sys.modules alias |
| `from ui.canvas.draw_toolbar import DrawToolbar` | ✅ | sys.modules alias |
| `from ui.canvas.graphic_items import GraphicBase` | ✅ | sys.modules alias |
| `import ui.canvas.canvas_layout` | ✅ | returns the same module object as `ui.canvas.mixins.canvas_layout` |

---

## Change-Size & Risk Assessment

| Dimension | Value | Notes |
|-----------|-------|-------|
| New directories | 2 | `ui/canvas/mixins/`, `ui/canvas/drawing/` |
| Files moved | 14 | 11 mixins/controllers + 2 drawing files + graphic_items/ |
| Files deleted (at root) | 13 | the 11 .py files above + draw_layer.py + draw_toolbar.py |
| Business-logic changes | 0 | purely physical relocation + import rewrites + compatibility shim |
| Risk level | Very low | Pure directory reorganization; every call site kept working via `sys.modules` aliases |
| Rollback procedure | Copy the moved files back to the root and delete the `_COMPAT_MAP` block in `__init__.py` |

---

## Recommendations for Future Development

1. **Place new canvas modules by responsibility** — logic classes → `mixins/`; drawing-related code → `drawing/`; rendering items → `items/`; new parameter controls → `parameter_widgets/`
2. **New code should prefer the new paths**: `from ui.canvas.mixins.canvas_xxx import ...` / `from ui.canvas.drawing.xxx import ...`; old paths are kept for compatibility only
3. **Optional next-round improvements**:
   - If `controllers.py` grows past ≈500 lines, split it into its own `ui/canvas/controllers/` directory (one file per class)
   - The Mixin inheritance in `canvas_view.py` could be rewritten into composition style (matching `selection` / `background` / `node_manager` / `events`) to eliminate multiple inheritance — this needs an impact study first
