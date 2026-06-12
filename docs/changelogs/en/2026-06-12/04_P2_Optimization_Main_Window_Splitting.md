# P2 Level Optimization: Main Window Splitting

## Overview

Split the main window file (1519 lines) into three single-responsibility modules using Python Mixin pattern for responsibility separation.

## Optimization Content

### New Files

**`ui/main_window_state.py`** - State Management Module

Responsible for window state saving and restoration:
- `save_window_state()` - Save window state
- `restore_window_state()` - Restore window state
- `_restore_panel_state()` - Restore panel state (create Dock immediately)
- `_save_panel_visibility()` - Save panel visibility
- `auto_open_last_project()` - Auto-open last project

**`ui/main_window_lifecycle.py`** - Lifecycle Management Module

Responsible for window startup and shutdown flow orchestration:
- `_init_and_restore()` - Initialization and restore flow
- `closeEvent()` - Close event handling
- `moveEvent()` - Move event handling
- `resizeEvent()` - Resize event handling
- `_force_stop_all_nodes()` - Force stop all nodes

**`ui/main_window_actions.py`** - Business Actions Module

Responsible for various business operations:
- `_create_node_list_panel()` - Create node list panel
- `_create_resource_monitor()` - Create resource monitor panel
- `_create_node_monitor()` - Create node monitor panel
- `_show_message_box()` - Show message dialog
- `_handle_node_created()` - Handle node created event
- `_handle_node_deleted()` - Handle node deleted event
- `_handle_node_status_changed()` - Handle node status changed

### Modified Files

**`ui/main_window.py`**

- Import three Mixin classes: `MainWindowStateMixin`, `MainWindowLifecycleMixin`, `MainWindowActionsMixin`
- Main window class inherits these three Mixins to achieve responsibility separation

## Design Features

1. **Responsibility Separation**: Each module has a single responsibility, easy to maintain and test
2. **Mixin Pattern**: Use Python multiple inheritance for behavior reuse
3. **Progressive Splitting**: Keep original interfaces, no impact on existing calls
4. **Backward Compatible**: All methods maintain original signatures

## Verification Results

- ✅ GUI launches normally
- ✅ Auto-open last project
- ✅ Node list loads normally (3 nodes)
- ✅ All panel functions work correctly
- ✅ Window state saves and restores normally

## Benefits

- Main window file reduced from 1519 lines to only core window construction logic
- Clear code structure with well-defined responsibilities
- Easy for future feature extension and maintenance
- Improved code testability