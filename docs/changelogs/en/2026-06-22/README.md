# [2026-06-22] V2.0.19 - Vector Outline Filling for Edge Rendering, High DPI Support and Canvas Resolution Customization

## Overview

**This update contains 3 sub-module changes**:

| # | Module | Description | Details |
|---|--------|-------------|---------|
| 01 | Edge Rendering Vector Outline Fill | QPainterPathStroker converts line path to closed outline, QBrush fill replaces QPen stroke | [->](01_Edge_Rendering.md) |
| 02 | High DPI Screen Adaptation | AA_EnableHighDpiScaling + AA_UseHighDpiPixmaps, SmoothPixmapTransform | [->](02_HighDPI_Support.md) |
| 03 | Canvas Resolution Settings | Rendering settings tab, 5 preset resolutions + custom size + antialiasing toggle | [->](03_Canvas_Resolution.md) |

---

## Change Statistics

| Type | Count | Files |
|------|-------|-------|
| **New** | 0 | - |
| **Deleted** | 0 | - |
| **Modified** | 9 | `ui/canvas/items/edge_item.py`, `bnos_console.py`, `ui/canvas/canvas_process.py`, `ui/canvas/canvas_view.py`, `ui/dialogs/settings_dialog.py`, `ui/core/app_config.py`, `ui/core/strings_cn.json`, `ui/core/strings_en.json`, `ui/canvas/mixins/canvas_connections.py` |

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