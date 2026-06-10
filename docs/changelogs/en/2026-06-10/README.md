# 2026-06-10 Changelog

## 📋 Update Overview

This update completes Phase 10 (IDE Workspace Integration), **Phase 12 (Adaptive Node View)**, and **Multi-Anchor System Refinement with Edge Persistence**. Introduces the IDEScanner auto detector, 4 IDE Actions registered in the Action system, a third node style "Panel" (ComfyUI-style controls on canvas), plus anchor differentiation, port mapping fixes, edge persistence, and batch cleanup improvements.

---

## ✨ Update Contents

### 1. 🚀 IDE Auto Detection & Right-Click Menu Action Integration

**Feature Description**:
- New `IDEScanner` auto scanner (214 lines), cross-platform VSCode / Trae IDE detection
- Four-layer detection chain: Memory cache → app_config → PATH → Env var/Process scan → Filesystem
- 4 IDE Actions registered in Action system, canvas right-click menus fully ActionFactory-driven
- Node config dialog IDE buttons unified to `ide_scanner.add_buttons_to_layout()`
- Environment variable derivation + process scanning covers non-standard Trae install paths (e.g., `F:\Trae CN\`)

**Modified Files** (8 files):
- New `ui/core/ide_scanner.py`
- Modified `ui/core/actions/builtin_node_actions.py`, `builtin_canvas_actions.py`
- Refactored `ui/canvas/canvas_menus.py`, `ui/dialogs/node_config_dialog.py`
- Configured `ui/main_window.py`, i18n string files

**Detailed Document**: [IDE Auto Detection & Action Integration](./01_IDE_Auto_Detection_and_Action_Integration.md)

---

### 2. 🎨 Adaptive Node View (ComfyUI-Style Panel Mode)

**Feature Description**:
- New third node style "Panel" — renders parameter editing controls directly on the canvas (like ComfyUI)
- 11 parameter types: string / text / password / int / float / bool / enum / file / directory / color / range
- Controls embedded via Qt-native `QGraphicsProxyWidget`, supporting keyboard interaction
- Parameter edits written back to `config.json` in real time with bidirectional data binding
- Style switching: Panel ↔ Block ↔ Node, any switch leaves no residual widgets
- Node dimensions exactly restored: Block 140×80, Node 80×80
- Panel mode dimensions auto-calculated from content (minimum width 240px)

**Modified Files** (8 files, ~450 lines of new code):
- **New** `ui/core/node_config_parser.py` (ParameterDef + parser)
- **New** `ui/canvas/parameter_widgets.py` (11 widget types + factory)
- Modified `ui/canvas/items/node_style.py` (DetailedNodeStyle + STYLES registration)
- Modified `ui/canvas/items/node_item.py` (_build_detailed_view + set_style refactor)
- Modified `ui/canvas/canvas_menus.py` (_switch_node_style simplified)
- Modified `ui/canvas/items/node_status_widget.py` (style reference de-caching)
- Modified i18n string files ("Panel" / "Block" / "Node")

---

### 3. 📝 Node Style Naming Enhancement

**Feature Description**:
- Node style names upgraded from descriptive names to more professional geometric + functional style naming
- Improved product design feel and brand consistency

**Naming Changes**:

| Old Name | New Name | Design Concept |
|----------|----------|----------------|
| Square | Block | Classic block flowchart style |
| Circle | Node | Dot node, emphasizing connection relationships |
| Detailed | Panel | Expanded control panel |

**Modified Files**:
- `ui/core/strings_cn.json`
- `ui/core/strings_en.json`

---

### 4. 🔌 Multi-Input Ports Support (Panel Mode)

**Feature Description**:
- Supports defining multiple input ports via `config.json` (`input_ports` field)
- Each port can define name, label, data type, required status, and description
- Automatically creates multiple input anchors in Panel mode, evenly distributed on the left side of the node
- Supports port type validation and default port selection
- Backward compatible: nodes without multi-port definition use default single anchor

**Configuration Example** (`config.json`):
```json
{
  "input_ports": [
    {"name": "input_sensor", "label": "Sensor Data", "type": "sensor", "required": true},
    {"name": "input_logs", "label": "Log Data", "type": "log"},
    {"name": "input_config", "label": "Config", "type": "json"}
  ],
  "parameters": [...]
}
```

**Input Port Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique port identifier |
| `label` | string | Display name |
| `type` | string | Data type (for compatibility validation) |
| `required` | bool | Whether connection is required |
| `description` | string | Port description (optional) |

**Modified Files**:
- `ui/core/node_config_parser.py` (Added `InputPortDef` class and parsing methods)
- `ui/canvas/items/node_item.py` (Added multi-anchor container and build methods)
- `ui/canvas/items/node_style.py` (Panel mode calls multi-anchor building)
- `ui/canvas/items/edge_item.py` (Supports multi-port connection logic)

**Key Bug Fixes**:
- Node creation size (140×80) vs style class default (140×120) mismatch → `_rect_default_width/height` stores original values
- NodeStatusWidget cached stale style reference → always reads `node_item._style`
- QComboBox dropdown wrong coordinates in ProxyWidget → `_ProxyAwareComboBox` overrides showPopup
- Proxy widgets remain after style switch → `_destroy_detailed()` unified cleanup

**Detailed Document**: [Adaptive Node View (ComfyUI-Style Panel Mode)](./02_Detailed_Node_View_ComfyUI_Style.md)

---

### 5. 🔧 Multi-Anchor System Refinement & Edge Persistence

**Feature Description**:
- Anchor differentiation: main input anchor (`listen_upper_file`) 16px centered on left edge; additional input port anchors 10px, tight against label left side
- Port mapping fix: `port_name="default"` writes to `listen_upper_file` instead of `port_mappings["default"]`
- Edge z-layer boost: EdgeItem z-value 0 → 20, ensuring edges always render on top
- Persistence fix: `canvas_layout.json` saves `source_port` / `target_port`, restoring correct anchor binding after restart
- Batch cleanup: `clear_canvas` and `batch_clear_listen_config` now properly handle `port_mappings`

**Modified Files** (8 files):
- Modified `ui/canvas/items/anchor_item.py` (dual-size anchor support)
- Modified `ui/canvas/items/anchor_manager.py` (size param, dynamic distance calc)
- Modified `ui/canvas/items/node_item.py` (small anchor coordinate calc)
- Modified `ui/canvas/items/edge_item.py` (z-value boost)
- Modified `ui/canvas/canvas_connections.py` (port mapping dispatch)
- Modified `ui/canvas/canvas_layout.py` (persistence + binding validation)
- Modified `ui/canvas/canvas_view.py` (clear_canvas fix)
- Modified `ui/canvas/canvas_batch_ops.py` (batch cleanup enhancement)

**Detailed Document**: [Multi-Anchor System Refinement & Edge Persistence](./03_Multi_Anchor_Refinement_and_Edge_Persistence.md)

---

## 🎯 Overview

| Feature | Status |
|---------|--------|
| IDEScanner Auto Scanner | ✅ Completed |
| IDE Action Registration (4) | ✅ Completed |
| Canvas Right-Click Menu Action-Driven | ✅ Completed |
| Node Config Dialog Button Unification | ✅ Completed |
| Trae Non-Standard Path Fix | ✅ Completed |
| Phase 10 IDE Workspace Integration | ✅ Completed |
| **Phase 12 Detailed Node View** | ✅ Completed |
| Parameter JSON Standard Format | ✅ Completed |
| 11 Parameter Widget Types | ✅ Completed |
| Qt ProxyWidget Embedding on Canvas | ✅ Completed |
| Bidirectional Data Binding (real-time config.json write-back) | ✅ Completed |
| Style Switching Without Size Distortion | ✅ Completed |
| Style Switching Without Widget Residues | ✅ Completed |
| Main / Sub Anchor Size Differentiation (16px / 10px) | ✅ Completed |
| Port Mapping Dispatch (default → listen_upper_file) | ✅ Completed |
| Edge Z-Layer Boost (z=20) | ✅ Completed |
| Edge Port Info Persistence (no loss on restart) | ✅ Completed |
| Batch Clear port_mappings Support | ✅ Completed |

---

**Date**: 2026-06-10
