# 【2026-06-20】V2.0.18 - Floating Panel System, Preset Library Refactoring, Translation & UI Unification

## Overview

**This update contains 6 sub-module changes**:

| # | Module | Description | Details |
|---|--------|-------------|---------|
| 01 | Performance Panel Fix | ChartCanvas custom paint, QPainter import fix, drag pause | [→](01_Performance_Panel_Fix.md) |
| 02 | Debug Panel Translation | 17 CN/EN translation key completion | [→](02_Debug_Panel_Translation.md) |
| 03 | Preset Library Refactoring | Skeleton template → full .bnos package, PresetLibraryDialog | [→](03_Preset_Library_Refactoring.md) |
| 04 | IPC Core Process Expansion | node.stop_all, node.detect_running commands | [→](04_IPC_Core_Process.md) |
| 05 | Polling Manager Dynamic Freq | CPU-load-adaptive 1s/2s/4s intervals | [→](05_Polling_Manager.md) |
| 06 | Translation Key Revision | 3 mismatch fixes, 29 new keys, 17 deprecated keys removed | [→](06_Translation_Key_Revision.md) |

---

## Change Statistics

| Type | Count | Files |
|------|-------|-------|
| **New** | 4 | `preset_library_dialog.py`, `node_templates/`, `docs/changelogs/cn/2026-06-20/*`, `docs/changelogs/en/2026-06-20/*` |
| **Deleted** | 2 | `template_selector_dialog.py`, `node_template_manager.py` |
| **Modified** | 14 | `performance_panel.py`, `debug_panel.py`, `_template.py`, `canvas_menus.py`, `panel.py`, `application_context.py`, `builtin_view_actions.py`, `core_process.py`, `polling_manager.py`, `floating_panel.py`, `import_export_manager.py`, `packager.py`, `strings_cn.json`, `strings_en.json` |

## Complete File Change List

| File | Change | Module |
|------|--------|--------|
| `ui/panels/performance_panel.py` | Added `ChartCanvas`, fixed imports, overrode drag hooks | 01_Perf |
| `ui/panels/debug_panel.py` | i18n key reference update | 02_Debug |
| `ui/dialogs/preset_library_dialog.py` | **New** — Preset library dialog | 03_Preset |
| `ui/dialogs/template_selector_dialog.py` | **Deleted** | 03_Preset |
| `ui/core/node_template_manager.py` | **Deleted** | 03_Preset |
| `ui/core/actions/node/_template.py` | Rewritten — save uses Packager, registers 2 Actions | 03_Preset |
| `ui/core/actions/node/__init__.py` | Registered `_template` module | 03_Preset |
| `ui/canvas/mixins/canvas_menus.py` | Added "Save as Preset" to right-click menu | 03_Preset |
| `ui/main_window/panel.py` | Updated import to `PresetLibraryDialog` | 03_Preset |
| `ui/core/application_context.py` | Removed template manager references | 03_Preset |
| `ui/core/floating_panel.py` | Added `themed_input_dialog()` | 03_Preset |
| `ui/core/import_export_manager.py` | Added `_repair_portable_venv()` | 03_Preset |
| `ui/core/packager.py` | Added `compress_directory` / `extract_package` / `validate` | 03_Preset |
| `ui/core/core_process.py` | Added `stop_all` / `detect_running` command dispatch | 04_IPC |
| `ui/core/polling_manager.py` | Dynamic frequency adjustment mechanism | 05_Polling |
| `ui/core/actions/builtin_view_actions.py` | i18n key update | 06_i18n |
| `ui/core/strings_cn.json` | +29 keys, -17 keys, mismatch fixes | 06_i18n |
| `ui/core/strings_en.json` | +29 keys, -17 keys, mismatch fixes | 06_i18n |
