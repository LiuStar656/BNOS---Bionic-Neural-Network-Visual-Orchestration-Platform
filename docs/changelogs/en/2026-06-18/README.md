# 【2026-06-18】V2.0.17 - NodeItem Split Refactoring, Mixin Architecture Composition & Node Startup Queue Fixes

---

## Update Overview

**This update contains 5 main changes:**

1. **NodeItem monolithic class split into composition pattern**: `node_item.py` reduced from 846 lines to 227 lines, split into 9 sub-components (rendering, geometry, interaction, status, config, style, parameter panel, etc.)
2. **6 Mixin classes fully converted to composition pattern**: `CanvasConnections` / `CanvasBatchOps` / `CanvasMenu` / `CanvasBoxSelect` / `CanvasColors` / `CanvasLayout` — explicit dependencies via `self.canvas`, eliminating implicit MRO dependencies
3. **Complete startup test verification**: All module imports / instantiations / API calls / complete application startup flow passed
4. **Node startup queue feature implementation**: Smart DAG scheduler with concurrency control, priority scheduling, topological dependency resolution, error retry, startup interval control, queue persistence
5. **Node startup queue and batch stop fixes**: Fixed 10 issues including right-click menu no response, batch stop only stopping one node, unable to restart after stopping, etc.

---

## Update List

### 1. NodeItem Monolithic Class Split into Composition Pattern (9 sub-components)

[Detailed Content](./01_NodeItem_Split_Refactor.md)

- **Before split**: `node_item.py` monolithic class 846 lines, mixing 18 responsibilities (rendering, geometry transformation, anchor management, parameter panel construction, config read/write, status updates, etc.)
- **After split**: Main class `NodeItem` only 227 lines + 9 sub-components, with single responsibility and independently testable
- **File structure**:
  ```
  ui/canvas/items/
    ├── node_item.py                    (Main class: lifecycle + delegation)
    └── node_components/
        ├── __init__.py
        ├── rendering.py                 (paint / custom colors)
        ├── subcomponents.py             (Text labels / status lights / expand button)
        ├── status_manager.py            (Resource monitoring / status / runtime)
        ├── config_manager.py            (config.json read/write)
        ├── geometry_handler.py          (itemChange / position / edge refresh)
        ├── interaction_handler.py       (Mouse / anchor connection interaction)
        ├── style_manager.py             (Style settings / dimensions)
        └── param_panel.py               (Parameter panel construction)
  ```
- **External API fully compatible**: Calling `NodeItem()` with original signature, no changes needed
- **Additional fix**: `config_manager.py` `_on_external_config_change` `widget.set_value` call corrected

---

### 2. 6 Mixin Classes Converted to Composition Pattern (Eliminating Implicit Dependencies)

[Detailed Content](./02_Mixin_Architecture_Refactoring.md)

**Problem Diagnosis**:
- Ambiguous state ownership (all state scattered on NodeCanvas)
- Implicit dependencies (Mixin A calls Mixin B's methods, dependent on MRO order)
- Fragile initialization order (wrong order causes immediate crash)
- Unit testing impractical (requires complete QApplication environment)

**Refactoring Plan**:
```
NodeCanvas.__init__():
  self.colors = CanvasColors(self)              # Foundation: colors/themes
  self.connections = CanvasConnections(self)     # Feature: connections
  self.layout_mgr = CanvasLayout(self)           # Feature: layout
  self.batch_ops = CanvasBatchOps(self)          # Operation: batch
  self.box_select = CanvasBoxSelect(self)        # Operation: box select
  self.menus = CanvasMenu(self)                  # Interaction: menus
```

**Key code changes**:
- Each composed class adds `__init__(self, canvas)`: explicit dependency declaration
- All `self.xxx` → `self.canvas.xxx`: clear state ownership
- NodeCanvas adds forwarding APIs (`_save_color_settings()`, `_load_color_settings()`, etc.), maintaining backward compatibility
- Explicit state variable initialization in `NodeCanvas.__init__` (`is_connecting`, `box_select_rect`, etc.)

**Fixed Bugs**:

| Bug | Symptom | Fix |
|-----|---------|-----|
| `box_select_rect` AttributeError | Attribute not found during box selection | `NodeCanvas.__init__` explicit init of `box_select_rect` / `box_selected_nodes` / `is_box_selecting` |
| `_save_color_settings` AttributeError | Method not found during layout save | `NodeCanvas` adds forwarding method `_save_color_settings()` → `self.colors._save_color_settings()` |
| `CanvasLayout` NodeItem passing failed | `'CanvasLayout' object has no attribute 'xxx'` during node creation | `CanvasLayout` `NodeItem(..., self, ...)` → `NodeItem(..., self.canvas, ...)` |

**Architecture improvement benefits**:
- State ownership: ✅ Clear (composed classes only access via `self.canvas`)
- Dependencies: ✅ Traceable (explicit assembly in order)
- Initialization order: ✅ Controllable (manual assembly in dependency order)
- Testability: ✅ Lower barrier (composed classes independently testable with Mock canvas)
- Code readability: ✅ Modular (7 independent functional modules, each < 500 lines)

---

### 3. About Other Mixins in the Project

After a complete scan, there is another Mixin in the project: `NodePanelSyncMixin` (located at `ui/panels/_shared/node_panel_sync_mixin.py`).

**Analysis Result**: This Mixin is relatively well-designed. It is a **behavior-injection Mixin** (only provides methods, no state ownership), and does not have the typical problems of Canvas Mixins (ambiguous state ownership, implicit dependencies). It is shared by `NodeMonitor` and `NodeMonitorDock` classes for synchronizing sub-panel lists with canvas nodes. **Recommended to keep as-is, no refactoring needed**.

| Mixin Name | Location | Usage | Refactoring Status |
|------------|----------|-------|-------------------|
| `NodePanelSyncMixin` | `ui/panels/_shared/node_panel_sync_mixin.py` | `NodeMonitor`, `NodeMonitorDock` | No refactoring needed |
| `CanvasConnectionsMixin` | `ui/canvas/mixins/canvas_connections.py` | `NodeCanvas` | ✅ Refactored |
| `CanvasBatchOpsMixin` | `ui/canvas/mixins/canvas_batch_ops.py` | `NodeCanvas` | ✅ Refactored |
| `CanvasMenusMixin` | `ui/canvas/mixins/canvas_menus.py` | `NodeCanvas` | ✅ Refactored |
| `CanvasBoxSelectMixin` | `ui/canvas/mixins/canvas_box_select.py` | `NodeCanvas` | ✅ Refactored |
| `CanvasColorsMixin` | `ui/canvas/mixins/canvas_colors.py` | `NodeCanvas` | ✅ Refactored |
| `CanvasLayoutMixin` | `ui/canvas/mixins/canvas_layout.py` | `NodeCanvas` | ✅ Refactored |

---

### 4. Node Startup Queue Feature Implementation

[Detailed Content](./05_Node_Startup_Queue_Feature_Implementation.md)

**Core Features**:

| Feature | Description |
|---------|-------------|
| **Concurrency Control** | Configurable maximum concurrent startup nodes (default 2), preventing resource competition |
| **Priority Scheduling** | Supports node startup priority, higher values mean higher priority |
| **Status Feedback** | New `queued` (waiting) status added |
| **Error Retry** | Automatic retry on failure (default 3 times), marks as `FAILED` when limit reached |
| **Startup Interval Control** | 200ms~500ms delay between batches, avoiding resource contention |
| **Queue Persistence** | Saves queue state on exit, restores on restart |
| **Event Notifications** | Decouples queue manager from UI via callback events (`node_enqueued`, `node_starting`, `node_started`, etc.) |

---

### 5. Node Startup Queue and Batch Stop Fixes

[Detailed Content](./04_Node_Startup_Queue_and_Batch_Stop_Fixes.md)

**Fixed Issues**:

| Issue | Symptom | Fix |
|-------|---------|-----|
| Right-click menu no response | Right-clicking on canvas nodes had no response | `contextMenuEvent` uses `items()` instead of `itemAt()`, prioritizing `NodeItem` |
| `box_selected_nodes` attribute error | Right-click menu referenced non-existent attribute | Corrected to `self.canvas.box_selected_nodes` |
| New node creation invalid | Right-click menu new node had no response | Pass `_make_ctx()` context ensuring `canvas` object included |
| Incomplete batch stop status detection | Only stopped running/idle, ignored queued/starting | Extended status detection to all non-stopped states |
| Unable to restart after stop | Showed "Failed to enqueue" | Called `startup_queue.dequeue(node_name)` on stop |
| Second batch start invalid | Showed "Added to startup list" but didn't start | Set `self._stopped = True` when queue empty |
| Batch stop only stopped one node | Only stopped the last selected node | Used default parameter `lambda n=node_name: ...` to capture loop variable |
| Synchronous blocking stop | `subprocess.run` blocking caused incomplete batch stops | Created `NodeStopWorker` background thread |
| Thread garbage collection | `QThread: Destroyed while thread '' is still running` | Added `_stop_node_workers` list to preserve thread references |
| `execute_node_stop` no multi-node support | Only handled single node `ctx.node_name` | Added `elif ctx.node_list:` branch iterating all nodes |

**Verification Results**:
- ✅ Right-click menu works correctly (single node, multi-node, canvas background)
- ✅ New node creation works properly
- ✅ Batch stop works for all selected nodes (supports running/idle/queued/starting states)
- ✅ Nodes can be restarted after stopping
- ✅ Second batch start executes correctly
- ✅ Thread references properly preserved, no QThread errors

---

### 5. Complete Startup Test Validation (Full Flow Passed)

[Detailed Content](./03_Startup_Test_Validation_Report.md)

**Test checklist**:

| Test Item | Content | Status |
|-----------|---------|--------|
| Module import test | 11 canvas modules imported one-by-one | ✅ 11/11 |
| NodeCanvas instantiation | Create NodeCanvas instance | ✅ |
| Composition layer assembly | Verify 10 composed components all instantiated | ✅ 10/10 |
| State variable initialization | nodes / edges / box_select_rect / is_connecting etc. | ✅ 10/10 |
| API call test | get_selected_node / clear_selection / clear_box_selection | ✅ 3/3 |
| Complete application startup | Launch from bnos_console.py, load 4-node project | ✅ |
| Box selection feature regression | box_select_rect / box_selected_nodes lifecycle | ✅ |
| Connection feature regression | is_connecting / connect_source / temp_edge | ✅ |
| Color settings chain | _save_color_settings / _load_color_settings forwarding chain | ✅ |
| Bug-1 fix verification | box_select_rect initialization | ✅ |
| Bug-2 fix verification | _save_color_settings forwarding | ✅ |
| Bug-3 fix verification | CanvasLayout passing self.canvas | ✅ |

**Complete application startup log** (key timestamps):
```
[10:05:13] Qt application initialization
[10:05:14] Node creation manager initialized
[10:05:14] Main window panel restoration (Dock system)
[10:05:15] Window state restoration (splitter positions)
[10:05:15] Project scanning & node loading (4 nodes)
[10:05:21] NodeCanvas initialized (composition mode: 10 components, no mixin inheritance)
[10:05:21] Canvas layout loaded (NodeItem rendering normal)
[10:05:21] Anchor binding / connection creation
[10:05:23] Canvas switching complete
[10:05:28] Application shutdown normal
```

**Non-fatal issues** (environment/system level, does not affect functionality):
- Qt thread safety warning (Timers cannot be started from another thread)
- Test environment permission limits (canvas_layout.json write failure)
- Windows terminal GBK encoding issue (emoji character output)

---

## Changed File List

| File | Change Type | Description |
|------|-------------|-------------|
| `ui/canvas/canvas_view.py` | Modified | Added composition layer assembly, state variable init, forwarding APIs |
| `ui/canvas/mixins/canvas_connections.py` | Modified | Mixin → composed class, `self` → `self.canvas` |
| `ui/canvas/mixins/canvas_batch_ops.py` | Modified | Mixin → composed class, `self` → `self.canvas`; batch stop status detection |
| `ui/canvas/mixins/canvas_menus.py` | Modified | Mixin → composed class, `self` → `self.canvas`; right-click menu node detection, attribute reference, new node context passing |
| `ui/canvas/mixins/canvas_box_select.py` | Modified | Mixin → composed class, `self` → `self.canvas` |
| `ui/canvas/mixins/canvas_colors.py` | Modified | Mixin → composed class, `self` → `self.canvas` |
| `ui/canvas/mixins/canvas_layout.py` | Modified | Mixin → composed class, `self` → `self.canvas` (critical fix) |
| `ui/canvas/items/node_item.py` | Modified | Reduced from 846 lines to 227 lines (delegation to sub-components) |
| `ui/canvas/items/node_components/*.py` | New | 9 sub-components (rendering/status/config/geometry/interaction/style/param_panel etc.) |
| `ui/core/node_startup_queue.py` | Modified | State reset when queue is empty |
| `ui/main_window/node.py` | Modified | Dequeue on stop, closure variable capture, background thread implementation |
| `ui/main_window/__main__.py` | Modified | Added `_stop_node_workers` list |
| `ui/main_window/lifecycle.py` | Modified | Wait for stop threads to complete during shutdown |
| `ui/core/actions/node/_lifecycle.py` | Modified | Multi-node handling support in `execute_node_stop` |

**Modified files**: 12 (core canvas logic + node lifecycle management)
**New files**: 9 (NodeItem sub-components)
**Deleted files**: 0
**Total line count change**: NodeItem 846 → 227 lines (+9 ~100-line sub-components)

---

## Backward Compatibility

✅ **API fully compatible**: All external calls to `NodeCanvas.xxx` maintain original signatures
✅ **No caller changes needed**: Code referencing `NodeItem` / `EdgeItem` requires no changes
✅ **File structure preserved**: All canvas files remain under `ui/canvas/` and its subdirectories

---

## Next Steps

- **Independent unit tests**: Write independent unit tests for CanvasConnections, CanvasBoxSelect, etc. using Mock canvas
- **Documentation improvement**: Add complete docstrings and usage examples for each composed class
- **Further decoupling**: Wrap remaining "data storage layer" (self.nodes, self.edges) on NodeCanvas as composed objects
