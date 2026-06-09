# 2026-06-10 Changelog

## 📋 Update Overview

This update completes Phase 10: IDE Workspace Integration, and fixes Trae IDE detection for non-standard install paths.

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

## 🎯 Overview

| Feature | Status |
|---------|--------|
| IDEScanner Auto Scanner | ✅ Completed |
| IDE Action Registration (4) | ✅ Completed |
| Canvas Right-Click Menu Action-Driven | ✅ Completed |
| Node Config Dialog Button Unification | ✅ Completed |
| Trae Non-Standard Path Fix | ✅ Completed |
| Phase 10 IDE Workspace Integration | ✅ Completed |

---

**Date**: 2026-06-10
