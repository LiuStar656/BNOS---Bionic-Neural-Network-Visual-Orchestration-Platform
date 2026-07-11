# Core Directory Reorganization

## Overview

45 modules in `ui/core/` were split into 7 categorized subdirectories, eliminating root-level file clutter. Three bugs introduced during the reorganization (encoding corruption and UnboundLocalError) were also fixed.

## Key Changes

### 1. Directory Categories

| Subdir | Description | File Count |
|--------|-------------|------------|
| `node/` | Node management: composite nodes, process control, config parsing, registry, startup queue, IDE scanning | 13 |
| `dock/` | Dock system: main dock, panel management, floating panels, CanvasHost, position persistence | 7 |
| `system/` | Infrastructure: DI container, EventBus, IPC, thread pool, polling, shortcuts, update scheduler, window state | 8 |
| `services/` | App services: application context, lifecycle management, core process, shutdown orchestration | 5 |
| `project/` | Project management: project loading, import/export, file operations | 4 |
| `config/` | Configuration: app config, theme, state, validators | 4 |
| `i18n/` | Internationalization: translation engine, key registry, CN/EN JSON strings | 4 |

**Kept at root**: `logger.py` (80 references, too costly to move), `packager.py`, `dark_title_bar.py`, `splash_screen.py`

### 2. Backward Compatibility

- `from ui.core.i18n import t` — **unchanged**, `i18n/__init__.py` transparently proxies all public APIs
- 150+ external import paths updated to new subdirectory paths
- 3 string path references corrected (`core_process.py` registration path)

### 3. Bug Fixes

**Encoding corruption fix**: Batch file editing by Task agents during reorganization introduced encoding corruption in `node_config_dialog.py` and `lifecycle.py`, replacing Chinese characters with `�?` replacement characters, causing `SyntaxError: invalid character`. Both files have been rewritten with English comments.

**UnboundLocalError fix**: In [canvas_event_handlers.py](file:///f:/Bionic Neural Network Program Operating System/ui/canvas/mixins/canvas_event_handlers.py), `AnchorItem` was only imported locally inside the connection mode code block, but the Alt+box-select code path also referenced this variable, causing `UnboundLocalError`. It has been promoted to a top-level import alongside `NodeItem` and `EdgeItem`.

### Migration Statistics

| Fix Type | Count |
|----------|-------|
| Import path updates | 150+ occurrences |
| String path references | 3 occurrences |
| Encoding corruption fixes | 2 files |
| Top-level import promotion | 1 occurrence |

## Files Affected

| File | Change Type |
|------|-------------|
| `ui/core/node/` (14 files) | New subdirectory, 13 modules moved in |
| `ui/core/dock/` (8 files) | New subdirectory, 7 modules moved in |
| `ui/core/system/` (9 files) | New subdirectory, 8 modules moved in |
| `ui/core/services/` (6 files) | New subdirectory, 5 modules moved in |
| `ui/core/project/` (5 files) | New subdirectory, 4 modules moved in |
| `ui/core/config/` (5 files) | New subdirectory, 4 modules moved in |
| `ui/core/i18n/` (5 files) | New subdirectory, 4 modules moved + `__init__.py` transparent proxy |
| `ui/core/i18n/__init__.py` | New — transparent proxy for backward-compatible `from ui.core.i18n import t` |
| `ui/dialogs/node_config_dialog.py` | Fix — encoding corruption, full rewrite |
| `ui/main_window/lifecycle.py` | Fix — encoding corruption, full rewrite |
| `ui/canvas/mixins/canvas_event_handlers.py` | Fix — AnchorItem local import promoted to top-level |
| 37 external reference files | Modified — import path updates |
