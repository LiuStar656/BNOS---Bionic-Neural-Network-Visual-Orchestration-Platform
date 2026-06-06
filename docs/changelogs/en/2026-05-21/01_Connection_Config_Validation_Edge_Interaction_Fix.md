# 🔗 Connection Config Validation + Edge Interaction Fixes

## 🔗 Connection Config Validation + Edge Interaction Fixes (2026-05-21)

### Config.json Fallback Validation 🔍

**New component**: `ui/core/connection_inferrer.py`

`canvas_layout.json` loading now silently cross-validates against each node's `config.json`:

- **Inference**: Parses `listen_upper_file` from every node's `config.json`, extracting upstream node names from paths
- **Path Compatibility**: Supports absolute (`F:/project/nodes/A/output.json`), relative (`../A/output.json`), and Windows paths
- **Auto-Repair**: Edges in config but missing on canvas → auto-added (log: `[Config兜底] 补充缺失连线`)
- **Suspicious Edges**: Edges on canvas but missing from config → logged as warning, NOT auto-removed (safety-first)
- **Fully Silent**: Validation runs transparently; all logs tagged with `[Config兜底]`

**Affected files**: `ui/core/connection_inferrer.py`(new), `ui/canvas/canvas_layout.py`(modified)

### Edge Selection & Deletion Fixes 🔧

**Modified files**: `ui/canvas/items/edge_item.py`, `ui/canvas/canvas_menus.py`

- **Selection enabled**: `EdgeItem` sets `ItemIsSelectable` flag, left-click selects with +4px highlight
- **Wider hit area**: `shape()` returns 8px stroke path for easier clicking on Bezier curves
- **Arrow as child**: Arrow reparented as EdgeItem child `QGraphicsPolygonItem(self)`, mouse events disabled, clicks pass through
- **Right-click menu**: Canvas `contextMenuEvent` now detects `EdgeItem` → [Delete Edge] [Change Edge Color] [Clear Selection]
- **Dead code removed**: Eliminated broken `scene.items()` search for `NodeCanvas` (it's a `QGraphicsView`, not a scene item)
- **Emoji cleanup**: Edge right-click menu emoji removed

---