# IDE Auto Detection & Right-Click Menu Action Integration

## 📋 Update Overview

This update completes Phase 10: IDE Workspace Integration. A new `IDEScanner` module auto-detects locally installed VSCode / Trae IDE and provides unified opening logic. All IDE function keys are registered through the Action system, with canvas right-click menus and node config dialogs calling them uniformly.

---

## 🎯 Core Features

### 1. IDEScanner Auto Scanner

**New `ui/core/ide_scanner.py` (214 lines)**

- Cross-platform IDE detection (Windows / Linux / macOS)
- Four-layer detection chain: **Memory cache → app_config persistence → PATH command → Environment variable / Process scan → Filesystem scan**
- Environment variable derivation: reverse-derives Trae install root from `TRAE_SANDBOX_CLI_PATH`
- Process scanning: PowerShell `Get-Process` to locate running IDE process paths
- Covers non-standard install locations (e.g., `F:\Trae CN\` on custom drives)
- Global singleton `ide_scanner`, caches results to `app_config.json`

**Public API**:

| Method | Description |
|------|------|
| `find_vscode()` | Locate VSCode executable path |
| `find_trae_ide()` | Locate Trae IDE executable path |
| `open_vscode_workspace(node_name, node_path)` | Generate `.code-workspace` and open in VSCode |
| `open_in_vscode(workspace_path)` | Open path in VSCode |
| `open_in_trae(workspace_path)` | Open path in Trae IDE |
| `open_in_ide(workspace_path, ide_type)` | Unified IDE open entry point |
| `add_buttons_to_layout(layout, node_name, node_path)` | Add open buttons to dialog layout |

---

### 2. IDE Action Registration

**Extended `builtin_node_actions.py`** — 2 new node Actions:

| Action ID | Name | Logic |
|-----------|------|-------|
| `node.open_vscode` | Open in VSCode | Generate `.code-workspace` → open node directory |
| `node.open_trae_ide` | Open in Trae IDE | Call `ide_scanner.open_in_trae()` |

**Extended `builtin_canvas_actions.py`** — 2 new canvas Actions:

| Action ID | Name | Logic |
|-----------|------|-------|
| `workspace.open_vscode` | Open in VSCode | Open project root in VSCode |
| `workspace.open_trae_ide` | Open in Trae IDE | Open project root in Trae IDE |

All IDE Actions pass path info via `ActionContext(extra={...})`, fully integrated with the existing Action system.

---

### 3. Right-Click Menu Action-Driven

**Refactored `ui/canvas/canvas_menus.py`**

- Single node menu: IDE entries generated via `ActionFactory.create_action("node.open_vscode", ...)`
- Blank canvas menu: IDE entries generated via `ActionFactory.create_action("workspace.open_vscode", ...)`
- Removed 35 lines of hardcoded QAction code (`_open_in_ide()` / `_open_workspace_in_ide()`)

**Refactored `ui/dialogs/node_config_dialog.py`**

- Removed 66 lines of duplicate IDE detection/opening code
- Unified to `ide_scanner.add_buttons_to_layout()` for dialog buttons

---

### 4. I18n Support

| Key | Chinese | English |
|-----|---------|---------|
| `k_open_vscode` | 打开VSCode | Open in VSCode |
| `_k_open_trae` | 打开 Trae IDE | Open in Trae IDE |

---

## 📁 Modified Files Summary

### New Files

| File | Lines | Description |
|------|-------|-------------|
| `ui/core/ide_scanner.py` | 214 | IDE auto scanner (detection + opening logic) |

### Modified Files

| File | Change | Description |
|------|--------|-------------|
| `ui/core/actions/builtin_node_actions.py` | +15 lines | Added `node.open_vscode` / `node.open_trae_ide` |
| `ui/core/actions/builtin_canvas_actions.py` | +30 lines | Added `workspace.open_vscode` / `workspace.open_trae_ide` |
| `ui/canvas/canvas_menus.py` | -35 lines | Removed hardcoded QAction, unified to ActionFactory |
| `ui/dialogs/node_config_dialog.py` | -66 lines | Removed duplicate IDE code, unified to IDEScanner |
| `ui/main_window.py` | +2 lines | Injected `app_config` into IDEScanner |
| `ui/core/strings_cn.json` | +1 line | `_k_open_trae` |
| `ui/core/strings_en.json` | +1 line | `_k_open_trae` |

---

## 🏗️ Architecture

```
                    ┌──────────────────────────┐
                    │      ActionRegistry       │
                    │  node.open_vscode         │
                    │  node.open_trae_ide       │
                    │  workspace.open_vscode    │
                    │  workspace.open_trae_ide  │
                    └─────┬──────────┬──────────┘
                          │          │
              ┌───────────┘          └───────────┐
              ▼                                  ▼
┌──────────────────────┐            ┌──────────────────────┐
│  canvas_menus.py     │            │  node_config_dialog  │
│  ActionFactory       │            │  add_buttons_to_     │
│  .create_action()    │            │  layout()            │
└──────────┬───────────┘            └──────────┬───────────┘
           │                                   │
           └───────────────┬───────────────────┘
                           ▼
              ┌──────────────────────────┐
              │       IDEScanner          │
              │  ┌────────────────────┐   │
              │  │ Memory cache       │   │
              │  │ app_config persist │   │
              │  │ PATH command       │   │
              │  │ Env var derivation │   │
              │  │ Process scan       │   │
              │  │ Filesystem scan    │   │
              │  └────────────────────┘   │
              │  .code-workspace gen      │
              │  subprocess.Popen launch  │
              └──────────────────────────┘
```

- **IDEScanner** only handles detection + opening, no menu building
- **Action System** handles right-click menu entries (unified convention)
- **Dialog buttons** retain `add_buttons_to_layout()` as an independent UI scenario

---

## ⚠️ Notes

- Trae detection uses `_find_from_runtime()` before filesystem scan, covering non-standard paths
- Process scanning requires PowerShell `Get-Process`, available on Windows 7+
- `_find_from_runtime()` only active on Windows; Linux/macOS use filesystem scan
- Generated `.code-workspace` files auto-configure Python interpreter path (venv)

---

**Date**: 2026-06-10
**Author**: Trae AI
