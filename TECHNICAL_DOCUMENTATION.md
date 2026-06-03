# BNOS (Bionic Neural Network Visual Orchestration Platform)
## Technical Documentation

> 📖 中文版：[TECHNICAL_DOCUMENTATION_CN.md](TECHNICAL_DOCUMENTATION_CN.md)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Design](#2-architecture-design)
3. [Core Component Details](#3-core-component-details)
   - 3.1 Launch Layer Components
   - 3.2 Process Management Layer Components
   - 3.3 Project Management Layer Components
   - 3.4 UI Components
   - 3.5 Utility Components
4. [Data Flow](#4-data-flow)
5. [IPC Mechanism](#5-ipc-mechanism)
6. [Node Lifecycle Management](#6-node-lifecycle-management)

---

## 1. Project Overview

BNOS is a PyQt6-based neural network visual orchestration platform providing visual node orchestration, process management, real-time monitoring, and more.

### Core Features

| Module | Description |
|---------|------|
| Node Management | Node creation, start, stop, deletion |
| Canvas Orchestration | Visual node wiring and data flow orchestration |
| Process Monitoring | Real-time node process status and resource monitoring |
| Project Management | Project create, open, save, import/export |
| External Mounting | Mount external nodes into current project |

### Tech Stack

- **Framework**: PyQt6 (Qt6 bindings)
- **Language**: Python 3.8+
- **IPC**: QLocalSocket / QLocalServer
- **UI Styling**: QSS (Qt Style Sheets)

---

## 2. Architecture Design

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     BNOS Console                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Launch     │───▶│   UI Layer  │───▶│  Business   │        │
│  │  launcher   │    │ main_window │    │ node_process│        │
│  │ bnos_console│    │ canvas_view │    │ ipc         │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                │
│         ▼                  ▼                  ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Subprocess  │    │   Panels    │    │  Managers   │        │
│  │ canvas_proc │    │ node_list   │    │ polling     │        │
│  │ panel_proc  │    │ node_monitor│    │ project     │        │
│  │ core_proc   │    │ resource    │    │ registry    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Process Architecture

| Process Type | Description | Responsibility |
|---------|------|------|
| Main Process | BNOS Console | UI rendering, user interaction, process coordination |
| Canvas Process | canvas_process | Independent canvas rendering, node drawing |
| Panel Process | panel_process | Independent panel rendering, property editing |
| Core Process | core_process | Background business processing, no UI |

---

## 3. Core Component Details

### 3.1 Launch Layer Components

#### 3.1.1 launcher.py

**Responsibility**: Splash screen launcher, gracefully starts the entire application

**Core Functions**:

| Function | Purpose | Parameters | Returns |
|------|------|------|--------|
| `find_venv_python()` | Locate venv Python interpreter | None | `str` - Python path |
| `main()` | Main launch flow | None | None |
| `_fallback_launch()` | Fallback launch without tkinter | None | None |
| `_progress()` | Update progress file | `progress_file`: progress file path | None |

**Workflow**:
1. Display tkinter splash screen (ASCII Logo + progress bar)
2. Locate venv Python interpreter
3. Create temporary progress file
4. Launch main program `bnos_console.py --progress=<file>`
5. Poll progress file and update splash in real-time
6. Close splash when progress reaches 100%

---

#### 3.1.2 bnos_console.py

**Responsibility**: Application main entry, initializes Qt environment and main window

**Core Functions**:

| Function | Purpose | Parameters | Returns |
|------|------|------|--------|
| `_progress()` | Send progress to launcher | `progress_file`: file path, `pct`: percentage, `msg`: message | None |
| `main()` | Application entry point | None | None |

**Launch Flow**:
1. Parse CLI arguments (progress file path)
2. Initialize i18n
3. Initialize Qt application
4. Create main window
5. Load project
6. Enter event loop

---

### 3.2 Process Management Layer Components

#### 3.2.1 node_process.py

**Responsibility**: Node process lifecycle management (start/stop/monitor)

**Core Functions**:

| Function | Purpose | Parameters | Returns |
|------|------|------|--------|
| `start_node_process()` | Start node process | `node_info`: node info dict | `(bool, str)` - (success, error msg) |
| `stop_node_process()` | Stop node process | `node_info`: node info dict, `force`: force kill | `(bool, str)` |
| `detect_running_nodes()` | Detect background running nodes | `nodes_data`: node data | `list` - [(node_name, PID)] |
| `check_running_processes()` | Check node process status | `nodes_data`: node data | `list` - status change list |
| `_find_node_processes()` | Scan system for node processes | `node_path`: node path | `list` - PID list |
| `_kill_all_node_processes()` | Force kill all orphan processes | `node_path`: node path | None |
| `_write_pid()` | Write PID file | `node_path`: node path, `pid`: process ID | None |
| `_read_pid()` | Read PID file | `node_path`: node path | `int` - PID or None |

**Three-State Process Model**:

| State | Description | Detection Condition |
|------|------|----------|
| `running` | Running | listener running with main child process |
| `idle` | Idle | listener running but no main child process |
| `stopped` | Stopped | No Python process running |

**PID File Management**:
- Supports two formats: `.pid` (standard) and `node_python_<name>.pid` (named)
- Written on startup, deleted on stop
- Process scanning fallback handles missing PID files

---

#### 3.2.2 process_manager.py

**Responsibility**: Manage UI subprocess lifecycle (canvas, panel, core business)

**Core Classes**:

| Class | Purpose | Key Methods |
|------|------|----------|
| `ManagedProcess` | Managed subprocess | `start()`, `stop()`, `restart()`, `_check_health()` |
| `ProcessManager` | Process manager | `register()`, `start()`, `stop()`, `stop_all()` |

**Health Detection**:
- Checks process status every 2 seconds
- Auto-restart on crash (max 5 attempts)
- Crash signal notification support

---

#### 3.2.3 ipc.py

**Responsibility**: Cross-process communication (QLocalServer + QLocalSocket)

**Core Classes**:

| Class | Role | Key Methods |
|------|------|----------|
| `IPCServer` | Main process server | `start()`, `stop()`, `send()`, `broadcast()` |
| `IPCClient` | Subprocess client | `connect_to_server()`, `send()` |

**Action Constants**:

| Constant | Meaning |
|------|------|
| `A_ADD_NODE` | Add node to canvas |
| `A_REMOVE_NODE` | Remove node from canvas |
| `A_UPDATE_STATUS` | Update node status |
| `A_CREATE_EDGE` | Create edge |
| `A_REMOVE_EDGE` | Remove edge |
| `A_SYNC_DATA` | Sync data |
| `A_CLEAR_ALL` | Clear canvas |
| `A_WIN_SYNC` | Window geometry sync |

**Event Constants**:

| Constant | Meaning |
|------|------|
| `E_NODE_SELECTED` | Node selected |
| `E_NODE_DBLCLICKED` | Node double-clicked |
| `E_EDGE_CREATED` | Edge created |
| `E_EDGE_REMOVED` | Edge removed |

---

#### 3.2.4 polling_manager.py

**Responsibility**: Unified polling manager, centralized timer task scheduling

**Core Features**:
- Singleton pattern
- All tasks share one master timer
- Support different polling intervals
- Unified signal interface

**Default Polling Tasks**:

| Task Name | Interval(s) | Callback | Purpose |
|--------|----------|----------|------|
| `node_health` | 2 | `_poll_node_health()` | Node process health check |
| `global_logs` | 2 | `_poll_global_logs()` | Global log detection |
| `global_config` | 2 | `_poll_global_config()` | Global config detection |
| `node_logs` | 2 | `_poll_node_logs()` | Node log detection |
| `node_config` | 2 | `_poll_node_config()` | Node config detection |
| `node_output` | 2 | `_poll_node_output()` | Node output detection |
| `app_state` | 5 | `_poll_app_state()` | Application state detection |

**Signal Definitions**:

| Signal | Parameters | Trigger |
|------|------|----------|
| `node_status_changed` | `(node_name, new_status)` | Node status changed |
| `log_file_changed` | `(node_path, log_filename)` | Node log file changed |
| `global_log_changed` | `(log_file, content)` | Global log file changed |
| `config_file_changed` | `(node_path)` | Node config changed |
| `global_config_changed` | `(config_file)` | Global config changed |
| `output_json_changed` | `(node_path, content)` | Node output changed |
| `app_state_changed` | `(state)` | App state changed |

---

### 3.3 Project Management Layer Components

#### 3.3.1 project_manager.py

**Responsibility**: Project management (create/open/refresh, scan and load node data)

**Core Functions**:

| Function | Purpose | Parameters | Returns |
|------|------|------|--------|
| `project_new()` | Create new project | `main_window`: main window instance | None |
| `project_open()` | Open project | `main_window`: main window instance | None |
| `project_refresh()` | Refresh node list | `main_window`: main window instance | None |

**Project Structure**:
```
project_dir/
├── nodes/           # Node directory
│   ├── node1/       # Node folder
│   │   ├── config.json
│   │   ├── listener.py
│   │   └── ...
│   └── node2/
├── node_registry.json  # Node registry
└── canvas_layout.json  # Canvas layout
```

---

#### 3.3.2 node_registry.py

**Responsibility**: Node registry component, records node names and paths

**Core Class**: `NodeRegistry`

**Methods**:

| Method | Purpose | Parameters | Returns |
|------|------|------|--------|
| `load()` | Load registry from file | None | `bool` - load success |
| `save()` | Save registry to file | None | `bool` - save success |
| `register_node()` | Register or update node | `node_name`, `node_path`, `mount_root` | None |
| `unregister_node()` | Remove node | `node_name` | None |
| `sync_from_scan()` | Sync scan results | `scan_results`: {name: path} | None |
| `get_active_nodes()` | Get active nodes | None | `dict` - node info |
| `get_mounted_nodes()` | Get mounted nodes | None | `dict` - node info |

**Data Structure**:
```json
{
    "nodes": {
        "node_name": {
            "path": "/absolute/path",
            "last_seen": "2025-01-01T00:00:00",
            "status": "active",
            "mount_root": "/mount/path"
        }
    },
    "updated_at": "2025-01-01T00:00:00"
}
```

---

#### 3.3.3 external_node_manager.py

**Responsibility**: External node mount and unmount management

**Core Functions**:

| Function | Purpose | Parameters | Returns |
|------|------|------|--------|
| `mount_node()` | Mount external node | `main_window`: main window instance | None |
| `unmount_node()` | Unmount external node | `main_window`: main window instance, `node_name`: node name | None |

**Mount Features**:
- External nodes stored outside project directory
- Mount relationship recorded in registry
- Auto-create locked group (orange indicator)

---

#### 3.3.4 json_node_starter.py

**Responsibility**: Read and start nodes from JSON configuration files

**Core Class**: `JsonNodeStarter`

**Methods**:

| Method | Purpose | Parameters | Returns |
|------|------|------|--------|
| `load_config()` | Load JSON config | `config_path`: config file path | `(bool, str, list)` |
| `start_node()` | Start single node | `node_info`: node info | `(bool, str)` |
| `start_nodes_from_config()` | Start all nodes from config | `config_path`: config file path | `(dict, str)` |
| `start_nodes()` | Start multiple nodes | `nodes`: node list | `(dict, str)` |

**Config File Format**:
```json
{
    "nodes": [
        {
            "name": "node_name",
            "path": "/path/to/node",
            "config": {}
        }
    ]
}
```

---

### 3.4 UI Components

#### 3.4.1 main_window.py

**Responsibility**: Main window with complete UI layout and core functionality

**Core Features**:
- Photoshop-style layout (fixed center canvas + left/right dock panels)
- Custom title bar (frameless window)
- CanvasHost as central widget
- Multi-canvas Tab support

**Key Methods**:

| Method | Purpose |
|------|------|
| `init_ui()` | Initialize UI layout |
| `new_project()` | Create new project |
| `open_project()` | Open project |
| `refresh_nodes()` | Refresh node list |
| `start_selected_node()` | Start selected node |
| `stop_selected_node()` | Stop selected node |
| `show_toast()` | Show Toast notification |
| `closeEvent()` | Window close handler |

**Panel Management**:
- Node List Panel (floating/dock)
- Node Monitor Panel (floating/dock)
- Resource Monitor Panel (floating/dock)

---

#### 3.4.2 canvas_view.py

**Responsibility**: Node canvas (VueFlow-style infinite canvas)

**Core Features**:
- Infinite canvas support (5000x5000 pixels)
- Node dragging, anchor wiring, Bezier curves
- Zoom/pan (scroll wheel / touchpad / space+drag)
- Box selection mode
- Canvas center coordinate persistence

**Interaction Modes**:
- **Space Pan**: Hold Space to enter shortcut mode, then left-click to pan
- **Box Select**: Mouse drag to select multiple nodes
- **Wiring**: Drag from output anchor to input anchor

---

#### 3.4.3 canvas_host.py

**Responsibility**: Canvas host window, manages multiple canvas docks

**Core Features**:
- Blank buffer layer design (shown on startup)
- Each canvas independently maintains node data and connections
- Auto-sync data on canvas switch

**Methods**:

| Method | Purpose |
|------|------|
| `add_canvas_dock()` | Add new canvas dock |
| `get_active_canvas()` | Get currently active canvas |
| `sync_canvas_data_to_main_window()` | Sync canvas data to main window |
| `update_canvas_data_from_main_window()` | Update canvas data from main window |
| `save_all_layouts()` | Save all canvas layouts |

---

### 3.5 Utility Components

#### 3.5.1 app_config.py

**Responsibility**: Application config management, singleton pattern

**Managed Config Items**:

| Config Item | Description | Default |
|--------|------|--------|
| `window_geometry` | Window geometry info | `{x:100, y:100, width:1400, height:900}` |
| `splitter_sizes` | Splitter ratio | `[250, 1150]` |
| `last_project` | Last opened project | `None` |
| `language` | Language setting | `"cn"` |
| `panel_positions` | Panel positions | Per-panel coordinates |
| `panel_visibility` | Panel visibility | Per-panel state |

**Methods**:
- `load()` - Load config
- `save()` - Save config
- `get(key, default)` - Get config item
- `set(key, value)` - Set config item

---

#### 3.5.2 logger.py

**Responsibility**: Global logging configuration

**Features**:
- Dual output: console (INFO) + file (DEBUG)
- Log format: timestamp + level + message
- File retains full debug information

**Usage**:
```python
from ui.core.logger import logger
logger.info("Node started")
logger.debug("Debug info")
logger.warning("Warning message")
logger.error("Error message")
```

---

#### 3.5.3 shortcut_manager.py

**Responsibility**: Global keyboard shortcut management

**Default Shortcuts**:

| Shortcut | Function |
|--------|------|
| `Ctrl+N` | New project |
| `Ctrl+O` | Open project |
| `Ctrl+,` | Open settings |
| `Ctrl+R` | Restart application |
| `Ctrl+Q` | Quit application |
| `F5` | Refresh nodes |
| `Ctrl+Shift+O` | Mount external node |
| `Ctrl+Shift+S` | Start node |
| `Ctrl+Shift+X` | Stop node |
| `Ctrl+Shift+M` | Node monitor |
| `Ctrl+Shift+R` | Resource monitor |
| `Ctrl+T` | New canvas tab |

---

## 4. Data Flow

### Project Open Flow

```
User clicks "Open Project"
        │
        ▼
Select project directory
        │
        ▼
Validate project structure (nodes/ or canvas_layout.json)
        │
        ▼
Create canvas dock (via CanvasHost)
        │
        ▼
Scan nodes/ directory, load nodes
        │
        ▼
Sync node registry
        │
        ▼
Restore mounted nodes
        │
        ▼
Detect background running nodes
        │
        ▼
Update UI (canvas + panels)
```

### Node Start Flow

```
User clicks "Start Node"
        │
        ▼
Get selected node info
        │
        ▼
Check node status (not running/idle)
        │
        ▼
Clean up residual orphan processes
        │
        ▼
Read start.json config
        │
        ▼
Locate venv Python interpreter
        │
        ▼
Start listener.py process
        │
        ▼
Write PID file
        │
        ▼
Update node status to idle
        │
        ▼
Update UI display
```

---

## 5. IPC Mechanism

### IPC Architecture

```
Main Process (Server)
    │
    ├── Canvas Process (Client)
    │       └── Receives: add/remove nodes, update status, sync data
    │
    ├── Panel Process (Client)
    │       └── Receives: sync node list, property updates
    │
    └── Core Process (Client)
            └── Receives: background business processing
```

### Message Format

```json
{
    "action": "canvas.add_node",
    "params": {
        "node_name": "my_node",
        "info": {...}
    },
    "request_id": "a1b2c3d4"
}
```

---

## 6. Node Lifecycle Management

### Lifecycle State Diagram

```
         ┌──────────┐
         │  stopped │
         └────┬─────┘
              │ start()
              ▼
         ┌──────────┐
         │   idle   │◄───────────────┐
         └────┬─────┘                │
              │ task execution       │ task complete
              ▼                      │
         ┌──────────┐                │
         │ running  │────────────────┘
         └────┬─────┘
              │ stop() / crash
              ▼
         ┌──────────┐
         │  stopped │
         └──────────┘
```

### Status Detection Mechanism

| Detection Method | Priority | Description |
|----------|--------|------|
| Process Scan | Highest | Find Python processes via system commands |
| PID File | High | Read .pid file to get PID |
| Process Object | Low | Check subprocess.Popen object |

### Orphan Process Handling

When PID file is missing or process exits abnormally:
1. Scan system processes via `_find_node_processes()`
2. Find Python processes belonging to the node
3. Force kill via `_kill_all_node_processes()`
4. Update node status to `stopped`

---

## Appendix: File Structure & Line Counts

### Project Summary

| Area | Files | Total Lines |
|------|--------|--------|
| Root Directory | 17 | 6,240 |
| ui/ Directory | 77 | ~17,800 |
| tools/ Directory | 7 | ~2,435 |
| tests/ Directory | 3 | 100 |
| **Total** | **104** | **~26,575** |

### Root Directory Files

| File | Lines | Description |
|------|------|------|
| `launcher.py` | 251 | Splash launcher |
| `bnos_console.py` | 100 | Main entry point |
| `app_config.json` | 80 | App configuration |
| `canvas_layout.json` | 13 | Canvas layout |
| `color_settings.json` | 9 | Color settings |
| `build_bnos.spec` | 47 | PyInstaller packaging config |
| `start_bnos_console.bat` | 78 | Windows launcher |
| `start_bnos_console.sh` | 153 | Linux/macOS launcher |
| `start_bnos_console.vbs` | 16 | Silent launcher |
| `requirements.txt` | 16 | Python dependencies |
| `README.md` | 812 | English README |
| `README_CN.md` | 792 | Chinese README |
| `UPDATE_CN.md` | 1,798 | Chinese update log |
| `UPDATE_EN.md` | 844 | English update log |
| `TECHNICAL_DOCUMENTATION.md` | 832 | Technical documentation (EN) |
| `TECHNICAL_DOCUMENTATION_CN.md` | 835 | Technical documentation (CN) |
| `DEVELOPMENT_GUIDELINES.md` | 364 | Development guidelines |
| `CODE_ANALYSIS_REPORT.md` | 163 | Code analysis report |
| `下一步计划.md` | 24 | Next steps |

### ui/ Top Level

| File | Lines | Description |
|------|------|------|
| `__init__.py` | 4 | Module entry |
| `main_window.py` | 1,133 | Main window |
| `canvas_widget.py` | 15 | Canvas compat layer (Facade) |
| `app_config.json` | 19 | UI layer config |

### ui/canvas/ — Canvas Module

| File | Lines | Description |
|------|------|------|
| `__init__.py` | 17 | Canvas module entry |
| `canvas_view.py` | 935 | Canvas main view |
| `canvas_layout.py` | 393 | Layout persistence Mixin |
| `draw_layer.py` | 317 | Drawing layer manager |
| `graphic_items.py` | 299 | Graphic items (5 shapes) |
| `draw_toolbar.py` | 204 | Photoshop-style drawing toolbar |
| `canvas_colors.py` | 180 | Color management Mixin |
| `canvas_menus.py` | 170 | Right-click menu Mixin |
| `canvas_batch_ops.py` | 166 | Batch operations Mixin |
| `canvas_connections.py` | 162 | Wiring management Mixin |
| `canvas_process.py` | 116 | Canvas subprocess entry |
| `canvas_box_select.py` | 31 | Box selection Mixin |
| `CANVAS_SPLIT_REPORT.md` | 305 | Canvas split report |

### ui/canvas/items/ — Canvas Graphic Items

| File | Lines | Description |
|------|------|------|
| `edge_item.py` | 587 | Edge item (orthogonal lines + fold points) |
| `node_item.py` | 352 | Node container item |
| `node_style.py` | 314 | Node style system (rect/dot) |
| `anchor_item.py` | 76 | Anchor item (I/O port) |
| `__init__.py` | 15 | Graphic items module entry |

### ui/core/ — Core Business Module

| File | Lines | Description |
|------|------|------|
| `polling_manager.py` | 520 | Unified polling manager (singleton) |
| `canvas_host.py` | 484 | Canvas host window |
| `node_process.py` | 484 | Node process lifecycle management |
| `json_node_starter.py` | 329 | JSON config node launcher |
| `connection_inferrer.py` | 257 | Config fallback edge validation |
| `project_manager.py` | 233 | Project management |
| `node_registry.py` | 242 | Node registry |
| `file_operation_manager.py` | 216 | File operation manager |
| `packager.py` | 203 | Node/project pack & export |
| `import_export_manager.py` | 198 | Import/export manager |
| `strings_cn.json` | 540 | Chinese language pack |
| `strings_en.json` | 532 | English language pack |
| `dark_title_bar.py` | 171 | Custom dark title bar |
| `floating_panel.py` | 171 | Floating panel base class |
| `theme.py` | 68 | Dark QSS theme |
| `bnos_dock.py` | 166 | Dock component |
| `ipc.py` | 150 | IPC (QLocalSocket) |
| `dock_manager.py` | 142 | Dock manager |
| `node_creation_worker.py` | 134 | Async node creation worker |
| `process_manager.py` | 128 | UI subprocess manager |
| `external_node_manager.py` | 120 | External node mount manager |
| `splash_screen.py` | 112 | PyQt6 launch splash |
| `app_config.py` | 107 | App config manager |
| `window_state_manager.py` | 71 | Window state manager |
| `core_process.py` | 72 | Core business background process |
| `shortcut_manager.py` | 68 | Shortcut manager |
| `i18n.py` | 61 | i18n module |
| `logger.py` | 55 | Global logger module |

### ui/core/toast/ — Toast Notification

| File | Lines | Description |
|------|------|------|
| `toast_notification.py` | 238 | Toast notification component |

### ui/core/utils/ — Utility Functions

| File | Lines | Description |
|------|------|------|
| `dialog_utils.py` | 814 | Unified dialog component |
| `file_utils.py` | 74 | File utility functions |
| `log_viewer.py` | 33 | Log viewer utility |
| `__init__.py` | 1 | Empty file |

### ui/dialogs/ — Dialogs

| File | Lines | Description |
|------|------|------|
| `node_config_dialog.py` | 580 | Node config dialog |
| `color_settings_dialog.py` | 443 | Color settings dialog |
| `file_browser_dialog.py` | 347 | File browser dialog |
| `settings_dialog.py` | 306 | Settings dialog |
| `__init__.py` | 2 | Module entry |

### ui/panels/ — Panel Modules

| File | Lines | Description |
|------|------|------|
| `node_list_panel.py` | 1,099 | Node list floating panel |
| `node_list_dock.py` | 776 | Node list dock panel |
| `resource_monitor.py` | 508 | Resource monitor floating panel |
| `node_monitor.py` | 497 | Node monitor floating panel |
| `node_expand_panel.py` | 447 | Node expand panel |
| `resource_monitor_dock.py` | 412 | Resource monitor dock panel |
| `node_monitor_dock.py` | 371 | Node monitor dock panel |
| `node_group_manager.py` | 344 | Node group manager |
| `property_panel.py` | 301 | Property panel |
| `node_list_drag.py` | 262 | Node drag functionality |
| `node_list_context.py` | 248 | Right-click context menu |
| `panel_process.py` | 83 | Panel subprocess entry |

### ui/menu/ — Menu System

| File | Lines | Description |
|------|------|------|
| `menu_manager.py` | 220 | Menu bar manager |

### ui/creators/ — Node Creators

| File | Lines | Description |
|------|------|------|
| `node_creator_manager.py` | 268 | Multi-language node creation manager |

### ui/icons/ — Icon System

| File | Lines | Description |
|------|------|------|
| `codicon.py` | 708 | Codicon icon manager (597 icons) |
| `__init__.py` | 3 | Icon module entry |

### ui/docs/ — Documentation

| File | Lines | Description |
|------|------|------|
| `TOAST_MODULE_README.md` | 185 | Toast module documentation |

### tools/ — Node Generation Tools

| File | Lines | Description |
|------|------|------|
| `rust_create_node.py` | 1,155 | Rust node template generator |
| `python_create_node.py` | 144 | Python node template generator |
| `README_CN.md` | 480 | Tools Chinese README |
| `README.md` | 438 | Tools English README |
| `Node_Generator_Guidelines_EN.md` | 204 | New language node guidelines (EN) |
| `节点生成器开发准则.md` | 204 | New language node guidelines (CN) |

### tests/ — Tests

| File | Lines | Description |
|------|------|------|
| `test_panel_process.py` | 34 | Panel process test |
| `test_canvas_process.py` | 33 | Canvas process test |
| `test_core_process.py` | 33 | Core process test |
