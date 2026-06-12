# P2 Level Optimization: ApplicationContext Aggregate Global State

## Overview

Created the `ApplicationContext` singleton class to unify all global state holders and provide a unified service access entry.

## Optimization Content

### New Files

**`ui/core/application_context.py`**

Created the `ApplicationContext` singleton class aggregating the following services:

| Service Name | Property Name | Description |
|--------------|---------------|-------------|
| AppConfig | `config` | Configuration service |
| EventBus | `event_bus` | Event bus |
| PollingManager | `polling` | Polling manager |
| NodeControlService | `node_control` | Node control service |
| ProcessManager | `process_manager` | Process manager |
| PanelManager | `panel_manager` | Panel manager |
| DockManager | `dock_manager` | Dock manager |
| ToastQueueManager | `toast_manager` | Toast manager |
| ShortcutManager | `shortcut_manager` | Shortcut manager |
| FileOperationManager | `file_operation` | File operation manager |
| ImportExportManager | `import_export` | Import/export manager |

### Modified Files

**`bnos_console.py`**

- Call `ApplicationContext.initialize()` after Qt initialization
- Call `ApplicationContext.initialize_ui_services(window)` after main window creation
- Call `ApplicationContext.shutdown()` before application exit

## Design Features

1. **Lazy Initialization**: Services dependent on main window (e.g., PanelManager, DockManager) are initialized lazily after main window creation
2. **Unified Entry**: All modules access services through `ApplicationContext()` singleton
3. **Lifecycle Management**: Provides `initialize()` and `shutdown()` methods to manage service lifecycle

## Usage

```python
from ui.core.application_context import ApplicationContext

ctx = ApplicationContext()
ctx.config.save()
ctx.node_control.start_node(node_id)
```

## Verification Results

- ✅ GUI launches normally
- ✅ All services initialized correctly
- ✅ Project loads normally

## Benefits

- Reduce scattered global variables
- Improve code maintainability
- Facilitate dependency injection and testing