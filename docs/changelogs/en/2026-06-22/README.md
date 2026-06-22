# [2026-06-22] V2.0.19 - Vector Outline Filling for Edge Rendering, High DPI Support, Canvas Resolution Customization and Script Directory Refactoring

## Overview

**This update contains 4 sub-module changes**:

| # | Module | Description | Details |
|---|--------|-------------|---------|
| 01 | Edge Rendering Vector Outline Fill | QPainterPathStroker converts line path to closed outline, QBrush fill replaces QPen stroke | [->](01_Edge_Rendering.md) |
| 02 | High DPI Screen Adaptation | AA_EnableHighDpiScaling + AA_UseHighDpiPixmaps, SmoothPixmapTransform | [->](02_HighDPI_Support.md) |
| 03 | Canvas Resolution Settings | Rendering settings tab, 5 preset resolutions + custom size + antialiasing toggle | [->](03_Canvas_Resolution.md) |
| 04 | restart_helper Script Directory Refactoring | `restart_helper.py` moved from root to `scripts/`, related code paths and tech docs updated | [->](04_Script_Refactoring.md) |

---

## Change Statistics

| Type | Count | Files |
|------|-------|-------|
| **New** | 1 | `scripts/restart_helper.py` (moved from root, unchanged) |
| **Deleted** | 1 | `restart_helper.py` (old root location) |
| **Modified** | 9+1 | `ui/canvas/items/edge_item.py`, `bnos_console.py`, `ui/canvas/canvas_process.py`, `ui/canvas/canvas_view.py`, `ui/dialogs/settings_dialog.py`, `ui/core/app_config.py`, `ui/core/strings_cn.json`, `ui/core/strings_en.json`, `ui/canvas/mixins/canvas_connections.py`; plus 4 path references inside `docs/*.md` tech docs |

## Complete File Change List

| File | Change | Module |
|------|--------|--------|
| `ui/canvas/items/edge_item.py` | Refactored `paint()` - QPainterPathStroker outline fill, NoPen+QBrush, NoCache mode for EdgeItem/TempEdgeItem/EdgeArrowItem | 01_Edge / 02_HighDPI |
| `bnos_console.py` | `AA_EnableHighDpiScaling` + `AA_UseHighDpiPixmaps` (set BEFORE QApplication) | 02_HighDPI |
| `ui/canvas/canvas_process.py` | Same two attribute settings for subprocess canvas | 02_HighDPI |
| `ui/canvas/canvas_view.py` | NodeCanvas reads AppConfig("rendering") - canvas_width, canvas_height, antialiasing | 03_Resolution |
| `ui/dialogs/settings_dialog.py` | New "Rendering" tab - 5 preset buttons + custom W/H inputs + antialiasing checkbox + restart tip | 03_Resolution |
| `ui/core/app_config.py` | Default config adds `rendering: {canvas_width:5000, canvas_height:5000, antialiasing:true}` | 03_Resolution |
| `ui/core/strings_cn.json` | Added `settings.rendering.*`, `preset_1000/2000/5000/8000/10000`, `custom`, `width`, `height`, `px`, `antialiasing`, `restart_tip` | 03_Resolution |
| `ui/core/strings_en.json` | Same keys as above, English version | 03_Resolution |
| `ui/canvas/mixins/canvas_connections.py` | TempEdgeItem render strategy aligned with EdgeItem (NoCache, fill-based) | 01_Edge |
| `scripts/restart_helper.py` | Moved from root to `scripts/`; content and behavior unchanged | 04_Scripts |
| `bnos_console.py` | `restart_helper.py` path changed from same folder to `scripts/restart_helper.py` | 04_Scripts |
| `docs/BNOS_文件结构图.md` | New `scripts/` node in Mermaid graph; `restart_helper.py` re-parented to it | 04_Scripts |
| `docs/BNOS_架构图.md` | Flowchart label changed to `scripts/restart_helper.py` | 04_Scripts |
| `docs/BNOS_技术分析报告.md` | LOC table updated with new file path | 04_Scripts |
| `docs/BNOS_项目优化分析报告.md` | Root tree & section 7.4 references synchronized | 04_Scripts |