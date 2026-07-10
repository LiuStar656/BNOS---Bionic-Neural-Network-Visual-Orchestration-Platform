# Project File Lock & Bug Fixes

## Overview

Introduced project-level file locking to prevent multiple BNOS instances from opening the same project simultaneously, preventing data corruption. Fixed multiple runtime bugs discovered during development.

## Core Changes

### 1. Project File Lock

Modified `ui/core/project_manager.py`:

- **Write lock file**: On project open, write `.bnos_project.lock` in project root containing PID and timestamp
- **PID liveness detection**: `_is_pid_alive()` uses Windows API `OpenProcess` + `GetExitCodeProcess` to double-confirm whether the process is truly running
- **Expired lock cleanup**: `remove_project_lock()` cleans up lock file on project close
- **Conflict notification**: Popup "Project is open by another BNOS instance (PID:xxxxx)" when lock detected

Modified `ui/core/canvas_host.py`:

- `remove_canvas_dock_by_path()` auto-cleans lock file on canvas close

### 2. Bug Fixes

#### GROUP_PREFIX AttributeError
- **File**: `ui/core/composite_node.py`
- **Root Cause**: Module-level constants `GROUP_PREFIX` / `GROUP_COLOR` not promoted to class attributes, other modules accessing via `CompositeNode.GROUP_PREFIX` -> `AttributeError`
- **Fix**: Set both constants as `CompositeNode` class attributes

#### blockSignals Not Restored Breaking Double-Click/Right-Click
- **File**: `ui/panels/node_list_dock.py`
- **Root Cause**: `blockSignals(True)` was called but never restored to `False` in `update_node_list`, permanently blocking `itemDoubleClicked` and `customContextMenuRequested` signals
- **Fix**: Add `blockSignals(False)` after tree build completion

#### clear_box_selection Method Name Error
- **File**: `ui/canvas/mixins/canvas_batch_ops.py`
- **Root Cause**: 4 calls to `clear_box_selection()`, actual method name is `clear_selection()`
- **Fix**: Unified to `clear_selection()`

#### node_list_context UnboundLocalError
- **File**: `ui/panels/node_list_context.py`
- **Root Cause**: Lazy import of `CompositeNode` inside `if not mgr:` block, used in three decompress/start/stop methods outside the block
- **Fix**: Promoted to module-level import

#### status_manager C++ Object Deleted RuntimeError
- **File**: `ui/canvas/items/node_components/status_manager.py`
- **Root Cause**: Resource monitoring signal still fires after node deletion, `QGraphicsTextItem` C++ object already destroyed
- **Fix**: Added `scene() is None` liveness check in `_on_status_updated`

#### app_config Type Check Breaking last_project
- **File**: `ui/core/app_config.py`
- **Root Cause**: S16 type validation rejected `str` values set after `None` sentinel
- **Fix**: `None` sentinel skips type validation
