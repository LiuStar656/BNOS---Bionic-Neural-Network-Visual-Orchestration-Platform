# 2026-06-10 Changelog

## 📋 Update Overview

This update completes Phase 10 (IDE Workspace Integration) and **Phase 12 (Adaptive Node View)**. Introduces the IDEScanner auto detector, 4 IDE Actions registered in the Action system, and a third node style "Detailed" — ComfyUI-style parameter controls rendered directly on the canvas.

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

### 2. 🎨 Adaptive Node View (ComfyUI-Style Detailed Mode)

**Feature Description**:
- New third node style "Detailed" — renders parameter editing controls directly on the canvas (like ComfyUI)
- 11 parameter types: string / text / password / int / float / bool / enum / file / directory / color / range
- Controls embedded via Qt-native `QGraphicsProxyWidget`, supporting keyboard interaction
- Parameter edits written back to `config.json` in real time with bidirectional data binding
- Style switching: Detailed ↔ Square ↔ Circle, any switch leaves no residual widgets
- Node dimensions exactly restored: Square 140×80, Circle 80×80
- Detailed mode dimensions auto-calculated from content (minimum width 240px)

**Modified Files** (8 files, ~450 lines of new code):
- **New** `ui/core/node_config_parser.py` (ParameterDef + parser)
- **New** `ui/canvas/parameter_widgets.py` (11 widget types + factory)
- Modified `ui/canvas/items/node_style.py` (DetailedNodeStyle + STYLES registration)
- Modified `ui/canvas/items/node_item.py` (_build_detailed_view + set_style refactor)
- Modified `ui/canvas/canvas_menus.py` (_switch_node_style simplified)
- Modified `ui/canvas/items/node_status_widget.py` (style reference de-caching)
- Modified i18n string files ("Detailed" / "Square" / "Circle")

**Key Bug Fixes**:
- Node creation size (140×80) vs style class default (140×120) mismatch → `_rect_default_width/height` stores original values
- NodeStatusWidget cached stale style reference → always reads `node_item._style`
- QComboBox dropdown wrong coordinates in ProxyWidget → `_ProxyAwareComboBox` overrides showPopup
- Proxy widgets remain after style switch → `_destroy_detailed()` unified cleanup

**Detailed Document**: [Adaptive Node View (ComfyUI-Style Detailed Mode)](./02_Detailed_Node_View_ComfyUI_Style.md)

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

---

**Date**: 2026-06-10
