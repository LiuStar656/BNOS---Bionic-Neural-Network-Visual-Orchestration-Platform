# 05 Selection Dual-Source Sync Fix & Composite Node Double-Click Config

## Issue 1 — Old Node Selection Highlight Persists After Clicking Another Node

1. Click Node A on canvas → A gets blue selection border
2. Click Node B on canvas → B gets blue selection border **but A's blue border never disappears**
3. Expected behavior: "plain click = single select"; only **Ctrl + click** = multi-select

## Root Cause — Selection Visual Depends on "Dual-Source OR", but Clear-Action Only Writes Single-Source

At line 39 in [node_components/rendering.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/items/node_components/rendering.py#L39), the selection-border visual predicate is:

```python
is_selected = getattr(self._node, "_is_custom_selected", False) or self._node.isSelected()
```

If **either** source is True, node renders as selected:

| Source | What | Written by |
|--------|------|------------|
| `_is_custom_selected` (custom flag) | Raw boolean flag added early in the project to bypass Qt's `SingleSelection` mode and allow true multi-select across `NodeItem`s | `SelectionManager.on_node_selected` / `_toggle_node_selection` |
| `isSelected()` (Qt-native QGraphicsItem selection) | Standard selection state inherited from `QGraphicsRectItem`, written by `QGraphicsScene.selectionChanged` / user rubber-band box-select / `setSelected()` calls | Qt Scene + partial business code (box-select clear, `SelectedNodesList` write APIs, etc.) |

But the old `SelectionManager.on_node_selected` (click to switch single-selection) only cleared `_is_custom_selected`, **never synchronously cleared Qt-native `setSelected(False)`**:

```python
# ❌ OLD: only cleared custom flag; A was still True in Qt scene.selectedItems()
for n in self.canvas.nodes.values():
    if getattr(n, "_is_custom_selected", False):
        n._is_custom_selected = False  # cleared only THIS one
        n.update()
# Render layer: False OR True == True → A still shows selected highlight!
```

Same inconsistency existed across **5 write entry points** in the selection system:
1. `SelectionManager.on_node_selected` (plain click, single select)
2. `SelectionManager._toggle_node_selection` (Ctrl+click, multi toggle)
3. `SelectedNodesList.append / remove / clear` (selection list write APIs)
4. `CanvasBoxSelect.clear_box_selection` (post-box-select state clear)

Entries 1, 3, 4 are all "clear all previous selection" semantics, but only wiped one of the two sources → visual residue.

## Fix Strategy — End-to-End Dual-Write / Dual-Clear

Rule: **Any place that writes `_is_custom_selected` MUST simultaneously call `setSelected()`. The two are always identical.**

### Fix 1 — SelectionManager single-select entry (canvas_selection.py `on_node_selected`)

```python
# ✅ NEW: predicate checks both OR arms; dual-write on clear; scene.clearSelection() as safety net
for n in self.canvas.nodes.values():
    if getattr(n, "_is_custom_selected", False) or n.isSelected():
        n._is_custom_selected = False
        n.setSelected(False)
        n.update()
self.canvas.scene.clearSelection()  # Qt-scene safety net (rubber-band / drag external selections)
node._is_custom_selected = True
node.setSelected(True)
node.update()
```

### Fix 2 — SelectionManager multi-toggle entry (canvas_selection.py `_toggle_node_selection`)

```python
# ✅ NEW: dual-source predicate, identical toggle
if getattr(node, "_is_custom_selected", False) or node.isSelected():
    node._is_custom_selected = False
    node.setSelected(False)
else:
    node._is_custom_selected = True
    node.setSelected(True)
node.update()
```

### Fix 3 — SelectedNodesList three write APIs (canvas_view.py)

```python
def append(self, name):
    node = self._canvas.nodes[name]
    node._is_custom_selected = True
    node.setSelected(True)   # ✅ ADDED
    node.update()

def remove(self, name):
    node = self._canvas.nodes[name]
    node._is_custom_selected = False
    node.setSelected(False)  # ✅ ADDED
    node.update()

def clear(self):
    self._canvas.scene.clearSelection()
    for item in self._canvas.nodes.values():
        item._is_custom_selected = False
        item.setSelected(False)  # ✅ ADDED (redundant with scene.clearSelection but consistent)
        item.update()
```

### Fix 4 — CanvasBoxSelect box-selection clear (canvas_box_select.py `clear_box_selection`)

```python
for _node_name, node in self.canvas.nodes.items():
    node.setPen(QPen(QColor(self.canvas.node_border_color), 2))
    node._is_custom_selected = False  # ✅ ADDED
    node.setSelected(False)
    node.update()                     # ✅ ADDED: repaint
```

### Fix Verification

| Operation | Old Behavior | New Behavior |
|-----------|-------------|-------------|
| Click A → Click B | Both A, B show selection border ❌ | Only B shows selection border ✅ |
| Ctrl+Click A → Ctrl+Click B | Both A, B selected ✅ | Both A, B selected ✅ |
| Ctrl+Click A (on) → Ctrl+Click A again | A deselected ✅ | A deselected ✅ |
| Rubber-band multi-select → Click blank canvas | Box-select highlight residue ❌ (some paths) | All cleared ✅ |
| Call `box_selected_nodes.clear()` programmatically | Qt-native selection residue ❌ | Both sources fully cleared ✅ |

---

## Issue 2 — Double-Clicking Composite Node Does Nothing

Regular nodes (`NodeItem`) double-click to open the configuration detail panel, but composite nodes (`CompositeNodeItem`) double-click produced no response. Users needed a fast way on the canvas to inspect/edit composite ports, internal nodes, routing, etc. Previously the only path was the multi-step "Node List → Right Click → Configure".

## Root Cause

- **Regular Node**: `NodeItem` has a complete mouse event chain (`mouseDoubleClickEvent` → `expand_requested` → open panel)
- **Composite Node**: `CompositeNodeItem` inherits `QGraphicsRectItem`; early revisions did not override `mouseDoubleClickEvent` (nor even `mousePressEvent` — context menus were dispatched at canvas-level via `EventHandlers`). Double-click fell through to Qt's default empty no-op.

Also need to verify whether the detail panel even supports composite nodes.

## Fix

### Step A — Complete the CompositeNodeItem mouse event chain (composite_node_item.py)

Added both `mousePressEvent` (incidentally brings three functions into alignment: plain-click select / Ctrl multi-select / right-click context menu) and `mouseDoubleClickEvent` (new feature):

```python
def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.RightButton:
        self.contextMenuEvent(event)    # Right-click: composite-specific context menu
        event.accept()
        return
    if event.button() != Qt.MouseButton.LeftButton:
        super().mousePressEvent(event)
        return
    # Connecting mode: input anchor hit → finish connection
    if self.canvas and self.canvas.is_connecting:
        input_anchor = self.find_nearest_input_anchor(event.pos(), 60)
        if input_anchor:
            self.canvas.complete_connection_to_input(self, input_anchor)
            event.accept()
            return
    # Ctrl + click → multi toggle
    if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and self.canvas:
        self.canvas._toggle_node_selection(self.node_name)
        event.accept()
        return
    # Plain click → clear others, single-select this
    if self.canvas:
        self.canvas.on_node_selected(self)
    super().mousePressEvent(event)

def mouseDoubleClickEvent(self, event):
    if event.button() != Qt.MouseButton.LeftButton:
        return super().mouseDoubleClickEvent(event)
    if not self.canvas:
        return super().mouseDoubleClickEvent(event)
    try:
        self.canvas.open_node_config(self.comp_id)   # Core: open configuration panel
        logger.info("[%s] Double-click opened composite node config page", self.comp_id)
    except Exception as e:
        logger.warning("[%s] Double-click open config failed: %s", self.comp_id, e)
    event.accept()
```

### Step B — Verify NodeDetailPanel supports composites (node_detail_panel.py `create_for_node`)

Panel already has dual-provider architecture, auto-detects by prefix:

```python
def create_for_node(node_name, parent_window):
    if node_name.startswith("composite_"):
        provider = CompositeNodeProvider(node_name, parent_window)  # ✅ loads node_clusters.json / composite.json
    else:
        provider = RegularNodeProvider(...)
    return NodeDetailPanel(provider, parent_window)
```

Tab assembly in `CompositeNodeProvider` verified: the previous session already removed the duplicate "Composite Config" Tab (avoiding the same composite.json opening twice). Current structure:
- Overview Tab (composite info, port list, internal node list)
- Cluster Config Tab (node_clusters.json, includes `_port_routing` routing table editor)
- Composite Structure Tab (composite.json live JSON editor)

### Interaction Behavior Summary (CompositeNodeItem)

| Interaction | Response |
|-------------|----------|
| Left-click (no modifier) | Clear all other canvas selections → single-select highlight on this composite |
| Ctrl + left-click | Toggle composite selection state (add/remove from multi-set) |
| Left double-click | Open composite detail config panel (3 tabs: Overview / Cluster Config / Composite Structure) |
| Right-click | Pop up composite-specific menu (Expand/Collapse, Decompress, Runtime Mode, Start/Stop) |
| Drag header area | Move composite position + auto-update connected edge paths |
| Drag output anchor | Start connection (identical behavior to regular NodeItem) |
| Connecting-mode drag onto input region | Input anchor hit → finish connection to this composite port |

---

## Files Changed

| File | Changes |
|------|---------|
| `ui/canvas/mixins/canvas_selection.py` | `on_node_selected` dual-writes `_is_custom_selected=False` + `setSelected(False)` when clearing; appends `scene.clearSelection()` safety net; `setSelected(True)` on newly selected node; `_toggle_node_selection` dual-source predicate + dual-write |
| `ui/canvas/canvas_view.py` | `SelectedNodesList.append / remove / clear` three write APIs now sync `setSelected()` |
| `ui/canvas/mixins/canvas_box_select.py` | `clear_box_selection` syncs `_is_custom_selected=False` + calls `update()` to repaint |
| `ui/canvas/items/composite_node_item.py` | Added `mousePressEvent` (full semantics: single-select / Ctrl multi-select / right-click menu / connection anchor hit); Added `mouseDoubleClickEvent` (calls `canvas.open_node_config(comp_id)` to open composite config panel; full try/except + success/warning logs) |

---

**Last Updated**: 2026-07-15
