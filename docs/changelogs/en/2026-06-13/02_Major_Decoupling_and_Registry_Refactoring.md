# Major Decoupling and Registry-Based Refactoring

## Background

After months of accumulation, several modules developed heavily coupled monolithic files:

| File | Lines | Problem |
|------|-------|---------|
| `builtin_node_actions.py` | 613 | 23 actions crammed into one function |
| `parameter_widgets.py` | 570 | 10 widget classes + factory + constants in one file |
| `node_style.py` | 523 | 3 styles mixed in one file |
| `graphic_items.py` | 298 | 6 graphic classes + base + constants sharing one file |

Fixing bugs was painful: changing one style meant navigating a 500-line file; adding a parameter widget required finding a spot in 570 lines.

---

## Solution: Unified "Split + Registry" Pattern

All refactorings follow the same pattern: **one class per file → package `__init__.py` registry → backward-compatible redirect of old file**.

---

## 1. Node Style Decoupling

`node_style.py` (523 lines) → `items/styles/` package (5 files)

```
ui/canvas/items/styles/
├── __init__.py        # StyleRegistry + re-exports
├── _base.py           # NodeStyle base class
├── rect.py            # RectNodeStyle + Dark/Light variants
├── dot.py             # DotNodeStyle
└── detailed.py        # DetailedNodeStyle
```

**Key change**: `isinstance(style, DotNodeStyle)` → `self._style.style_key == "dot"` string comparison, decoupling concrete class import dependencies.

**StyleRegistry API**:
```python
StyleRegistry.get("dot")       → DotNodeStyle class
StyleRegistry.get("unknown")   → DarkRectNodeStyle (fallback)
StyleRegistry.keys()           → ["rect", "dot", "detailed"]
```

Adding a new style takes only two steps: create `newstyle.py` + add one line in the registry.

---

## 2. Parameter Widget Decoupling

`parameter_widgets.py` (570 lines) → `parameter_widgets/` package (14 files)

```
ui/canvas/parameter_widgets/
├── __init__.py         # WidgetRegistry + re-exports
├── _base.py            # ParameterWidget base + constants
├── _proxy_combo.py     # QGraphicsProxyWidget-compatible ComboBox
├── string.py / text.py / password.py / int_widget.py / float_widget.py
├── bool_widget.py / enum_widget.py / file_picker.py / dir_picker.py
├── color_widget.py / range_widget.py
```

**WidgetRegistry API**:
```python
WidgetRegistry.get("int")      → IntWidget class
WidgetRegistry.get("unknown")  → StringWidget (fallback)
WidgetRegistry.keys()          → 11 parameter types
```

Zero consumer changes — `from ui.canvas.parameter_widgets import ParameterWidget` auto-resolves to the package `__init__.py` after deleting the old `.py` file.

---

## 3. Drawing Graphics Decoupling

`graphic_items.py` (298 lines) → `graphic_items/` package (7 files)

```
ui/canvas/graphic_items/
├── __init__.py      # GraphicRegistry + re-exports
├── _base.py         # GraphicBase + constants (C_STROKE/C_FILL/C_TEXT/STROKE_W)
├── rect.py / round_rect.py / polygon.py / arrow.py / text.py
```

**GraphicRegistry API**:
```python
GraphicRegistry.get("arrow")      → ArrowGraphic class
GraphicRegistry.from_dict(d)      # Unified deserialization entry
```

`GraphicBase.from_dict()` retained, internally delegates to `GraphicRegistry.from_dict()`.

---

## 4. Built-in Action Decoupling

`builtin_node_actions.py` (613 lines) → `actions/node/` subpackage (9 files)

```
ui/core/actions/node/
├── __init__.py        # register_node_actions() aggregator
├── _lifecycle.py      # start/stop/config/refresh/mount/export (6 actions)
├── _context_menu.py   # add_to_canvas/open_folder/view_log/edit_config/rename/delete/unmount (7 actions)
├── _batch.py          # 5 batch_* actions
├── _selection.py      # select_all/deselect_all (2 actions)
├── _group.py          # 10 group.* actions
├── _ungrouped.py      # ungrouped.* (2 actions)
├── _ide.py            # open_vscode/open_trae_ide (2 actions)
└── _style.py          # change_style / 4 color actions (4 actions)
```

Each submodule exports a `register(main_window)` function; `__init__.py` iterates and calls them all. Adding an action only requires editing the relevant sub-file.

Backward compatibility: old file redirects via `from ui.core.actions.node import register_node_actions`; 3 consumers unchanged.

---

## 5. Shared Panel Module Extraction

Eliminated duplicate code for Node Log SubPanels and resource collection:

```
ui/panels/_shared/
├── node_log_sub_panel.py           # BaseNodeLogSubPanel
├── node_panel_sync_mixin.py        # SyncMixin (_sync_panels etc.)
└── system_resource_collector.py    # Shared collector singleton
```

- `NodeMonitor` / `NodeMonitorDock`: ~80-110 lines of duplicate code eliminated each
- `ResourceMonitor` / `ResourceMonitorDock`: 212 + 114 lines eliminated
- `shared_resource_collector` singleton resolves inconsistent psutil state between two panels

---

## 6. Bug Fixes (same period)

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Exit crash: `PollingManager` has no `stop_all` | Wrong method name in `application_context.py` | `stop_all`→`stop`, constructor→`instance()` |
| Exit crash: `ProcessManager` has no `terminate_all` | Same issue | `terminate_all`→`stop_all` |
| Dot circle remains in detailed mode | `DotNodeStyle` creates `_body` circle; `DetailedNodeStyle.apply()` missed hiding it | Added `_body.setVisible(False)` |
| Status widget incorrectly shown in dot/detailed modes | `update_status()` unconditionally creates widget | Added `status_show` guard |
| Small anchors lose connections after style switch | Edge migration only matched by old anchor `port_name` | Prioritize `_desired_target_port_name` matching |
| `config.json` params/ports overwritten by `start.json` | `start.json` lacks metadata fields; config entirely replaced | Re-read `config.json` from disk, overlay runtime fields |

---

## Impact Summary

| Metric | Value |
|--------|-------|
| Monolithic files before refactoring | 4 (523+570+613+298 = 2,004 lines) |
| Files after refactoring | 35 (max 187 lines each) |
| Consumer changes | 0-3 lines per file |
| Full project compilation | 145/145 **ALL OK** |
| New type/style registration | 2 steps (class file + one registry line) |
