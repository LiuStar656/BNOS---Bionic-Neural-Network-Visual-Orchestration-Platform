# 06 Code Standardization Overhaul

## Overview

Comprehensive code standardization for the entire BNOS project (227 Python files), establishing automated quality gates and eliminating legacy inconsistencies alongside real bugs.

---

## 1. Toolchain Setup (Greenfield)

| Tool | Config | Purpose |
|------|--------|---------|
| **Ruff** | `pyproject.toml` | Replaces flake8 + black + isort, 200+ rules auto-check & auto-fix |
| **Pre-commit** | `.pre-commit-config.yaml` | Auto-runs ruff check + format on `git commit` |
| **EditorConfig** | `.editorconfig` | Unified indent (4 spaces), line endings (LF), UTF-8 encoding |
| **Pylance** | `pyrightconfig.json` | Real-time IDE type checking with precise Mixin/Qt false-positive suppression |

---

## 2. Real Bug Fixes (8 bugs)

Issues discovered during standardization that would cause runtime crashes or logic errors:

| File | Bug | Impact |
|------|-----|--------|
| `ui/core/actions/composite_actions.py` | `execute_fn=decompress` referencing undefined variable | `NameError` crash |
| `ui/core/node/external_node_manager.py` | 2× `except Exception:` lambda referencing uncaught `e` | Double crash in exception handler |
| `ui/core/system/ipc.py` | 3× closure loop variable capture | All callbacks use last iteration value |
| `ui/main_window/state.py` | Duplicate `_restore_terminal_dock` definition | First implementation is dead code |
| `ui/core/utils/changelog_viewer.py` | Missing `logger` import | `NameError` |
| `ui/panels/performance_panel.py` | Missing `polling_manager` import | `ImportError` |
| `ui/canvas/mixins/canvas_node_manager.py` | Wrong `NodeConfigDialog` import path | `ImportError` |
| `ui/panels/node_list_ops.py` / `node_expand_panel.py` | Same (3 locations) | `ImportError` |

---

## 3. Import & Logger Unification

### Logger Unification

| Before (4 styles) | After |
|---|---|
| `logging.getLogger(__name__)` |  |
| `logging.getLogger("BNOS")` | `from ui.core.logger import logger` |
| `from ui.core.logger import get_logger; logger = get_logger(__name__)` |  |
| Direct `from ui.core.logger import logger` |  |

Files fixed: `i18n.py`, `translation_keys.py`, `core_process.py`, `project_manager.py`

### print() → logger.info()

| File | Fixes |
|------|-------|
| `ui/core/services/core_process.py` | 2 occurrences |
| `tests/*.py` | T201 exclusion (test output) |
| `tools/*.py` | T201 exclusion (CLI tools) |

---

## 4. Python 3.12 Modernization

### `from __future__ import annotations` Global Coverage

- **219 files** added, fully covered
- Enables `str | None` syntax replacing `Optional[str]`

### `# type: ignore` Eliminated

- `ui/core/actions/action_registry.py`: 8 → **0**
- `pyrightconfig.json`: 5 new precise suppressions for Mixin pattern false positives

### os.path → pathlib.Path

| Phase | os.path count | Files affected |
|------|---------------|----------------|
| Before | 691 | 72 files |
| After | 156 | 42 files |
| **Reduction** | **-77%** | |

Coverage includes: core utilities (`dialog_utils.py`, `packager.py`, `file_utils.py`, `polling_manager.py`), node system (`node_process.py`, `composite_node.py`, `ide_scanner.py`, etc.), project management, canvas mixins, dialogs/panels, entry points — **25+ files** total.

---

## 5. Dead Code Removal

| File | Cleanup |
|------|---------|
| `tools/python_create_node.py` | 4× `if/else: pass` blocks, `except Exception: pass` → `except OSError:` |
| `tools/rust_create_node.py` | `if check_rust_installed(): pass else: pass` → actual check with warning |
| `scripts/restart_helper.py` | Useless `if/else: pass` removed |
| `ui/core/node/json_node_starter.py` | Removed unreachable `isinstance(dict)` check |

---

## 6. Runtime Error Fixes

| File | Fix |
|------|-----|
| `ui/core/config/app_config.py` | `config_file` compatible with both `str` and `Path` (defensive `Path()` wrapping) |
| `ui/core/node/composite_node.py` | `save()` filters `_morphed_edges` before serialization (contains non-serializable Qt `EdgeItem`) |
| `ui/main_window/interaction.py` | Added `is not None` guard on `_resize_start_pos` |

---

## 7. Final Verification

```
ruff check    → All checks passed!
pytest        → 172 passed, 0 failed
py_compile    → 227 files, 0 errors
Pylance       → 0 diagnostics
pre-commit    → Installed, auto-triggers on git commit
```

---

## Modified File List

| Category | Count | Key Files |
|----------|-------|-----------|
| New Config Files | 4 | `pyproject.toml`(updated), `.editorconfig`, `.pre-commit-config.yaml`, `pyrightconfig.json` |
| Core Utilities | 6 | `dialog_utils.py`, `packager.py`, `file_utils.py`, `changelog_viewer.py`, `polling_manager.py`, `app_config.py` |
| Node System | 8 | `node_process.py`, `composite_node.py`, `composite_env.py`, `ide_scanner.py`, `node_registry.py`, `json_node_starter.py`, `composite_orchestrator.py`, `language_detector.py` |
| Canvas Module | 6 | `canvas_node_manager.py`, `canvas_connections.py`, `canvas_layout.py`, `canvas_batch_ops.py`, `canvas_colors.py`, `canvas_view.py` |
| Project Management | 3 | `project_manager.py`, `import_export_manager.py`, `file_operation_manager.py` |
| Dialogs/Panels | 8 | `preset_library_dialog.py`, `node_config_dialog.py`, `file_browser_dialog.py`, `property_panel.py`, `node_list_ops.py`, `node_expand_panel.py`, `node_list_panel.py`, `node_monitor.py`, etc. |
| Entry/Launch | 3 | `launcher.py`, `bnos_console.py`, `__main__.py` |
| Action System | 2 | `action_registry.py`, `_template.py` |
| Mixin Layer | 2 | `state.py`, `interaction.py` |
| Services/System | 3 | `core_process.py`, `process_manager.py`, `history_manager.py` |
| i18n | 2 | `i18n.py`, `translation_keys.py` |
| Tool Scripts | 3 | `python_create_node.py`, `rust_create_node.py`, `restart_helper.py` |
| Tests | 5 | `test_app_config.py`, `test_translation_keys.py`, `test_core_process.py`, `test_canvas_process.py`, `test_terminal_feature.py`, etc. |
| Other | 7 | `config_manager.py`, `composite_factory.py`, `connection_inferrer.py`, `validators.py`, `dock/canvas_host.py`, `icons/codicon.py`, `external_node_manager.py`, etc. |

---

**Last Updated**: 2026-07-12
