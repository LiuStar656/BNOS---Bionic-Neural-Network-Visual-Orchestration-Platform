# Node Detail Panel Merge and Composite Node Config Window Fix

## Problem Description

### Problem 1: Composite Node Config Window Empty

When opening the composite node config window, the window content is empty with no UI elements.

**Root Cause**:
1. The `NodeDetailPanel._init_ui` method had an indentation error - the `try` block only contained the first two lines, causing most UI construction code to not execute
2. `CompositeNodeProvider` used the wrong attribute name `project_path`, while the main window actually uses `current_project_path`

### Problem 2: Composite Node Cannot Expand After Restart

Composite nodes can expand normally after creation, but fail to expand after restarting the project:
```
_expand_composite: internal node node_python_2 missing from canvas, removing from composite
_expand_composite: no internal nodes remaining for composite_c811a9f5
```

**Root Cause**: `save_layout` completely skipped internal child nodes of collapsed composite nodes when saving to `canvas_layout.json`, causing them to be unrecoverable after restart.

## Fixes

### Modified Files

**1. ui/dialogs/node_detail_panel.py**

- Fixed indentation error in `_init_ui` method, putting all UI construction code inside the `try` block
- Added exception handling and user notification, showing error message when initialization fails

**2. ui/dialogs/node_data_provider.py**

- Modified `CompositeNodeProvider.__init__` to use `current_project_path` instead of `project_path`

**3. ui/canvas/mixins/canvas_layout.py**

- Modified `save_layout`: Save all nodes (including composite internal nodes) with `is_internal` flag
- Modified `load_layout`: Use `is_internal` flag from layout file to identify internal nodes, keep them hidden after loading

**4. ui/dialogs/json_sync_editor.py (New)**

- Implemented bidirectional sync JSON editor with debounced save and external change detection

**5. ui/dialogs/log_viewer_widget.py (New)**

- Implemented log viewer with log file selection, polling update and clear functionality

**6. ui/dialogs/node_control_widget.py (New)**

- Implemented node control widget with start/stop buttons and status display
- Added anti-concurrency protection: `_operation_in_progress` flag prevents concurrent button clicks causing signal conflicts

**7. ui/canvas/mixins/canvas_node_manager.py**

- Added `_remove_from_composite_if_inside` method to sync update composite node internal list when deleting nodes

**8. ui/core/node/composite_node.py**

- Improved `_expand_composite` method to allow partial node missing and clean up invalid nodes

**9. ui/canvas/mixins/canvas_menus.py**

- Removed duplicate "Expand Node" option from regular node right-click menu, keeping only "Configure"

## Feature Improvements

### Window Merge

Merged "Expand Node" and "Node Config" windows into a unified **Node Detail Panel** with support for:
- **Config/Output/Logs** tabs (shared by regular and composite nodes)
- **Composite/Pipeline/DAG Status** exclusive tabs (composite nodes)
- **Node Info** panel showing node name, type, child count, path
- **Node Control** start/stop controls
- **Quick Actions** open folder, terminal, IDE

### Internationalization Support

Added complete i18n support for the node detail panel:
- New translation keys: `k_node_config`, `k_node_output`, `k_node_logs`, `k_composite`, `k_pipeline`, `k_dag_status`, etc.
- Updated `strings_cn.json` and `strings_en.json`

### Anti-Concurrency Protection

- Start/stop buttons added `_operation_in_progress` flag
- Clicking stop while starting is ignored, preventing signal conflicts

### Path Mapping Fix

Unified composite node path calculation using `CompositeNode` static methods

## Modified Files List

| File | Changes |
|------|---------|
| `ui/dialogs/node_detail_panel.py` | Window merge; fixed indentation error; added exception handling |
| `ui/dialogs/node_data_provider.py` | Fixed project path attribute name; new CompositeNodeProvider |
| `ui/dialogs/json_sync_editor.py` | New: Bidirectional sync JSON editor |
| `ui/dialogs/log_viewer_widget.py` | New: Log viewer widget |
| `ui/dialogs/node_control_widget.py` | New: Node control widget (with anti-concurrency protection) |
| `ui/canvas/mixins/canvas_layout.py` | Save/load includes internal nodes with `is_internal` flag |
| `ui/canvas/mixins/canvas_node_manager.py` | Sync update composite when deleting nodes |
| `ui/core/node/composite_node.py` | Fault-tolerant handling for missing nodes during expand |
| `ui/canvas/mixins/canvas_menus.py` | Removed duplicate "Expand Node" option |
| `ui/core/i18n/strings_cn.json` | Added node detail panel translations |
| `ui/core/i18n/strings_en.json` | Added node detail panel translations |
| `ui/core/i18n/translation_keys.py` | Added new translation key constants |