# BNOS (Bionic Neural Network Visual Orchestration Platform)
## Technical Documentation

> 📖 Chinese Version: [TECHNICAL_DOCUMENTATION_CN.md](TECHNICAL_DOCUMENTATION_CN.md)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Design](#2-architecture-design)
3. [Core Component Details](#3-core-component-details)
   - 3.1 Launch Layer
   - 3.2 Main Window Layer
   - 3.3 Canvas Layer
   - 3.4 Core Services Layer
   - 3.5 Panel Layer
   - 3.6 Project Management Layer
   - 3.7 Utility Layer
4. [Data Flow](#4-data-flow)
5. [IPC Mechanism](#5-ipc-mechanism)
6. [Node Lifecycle Management](#6-node-lifecycle-management)

---

## 1. Project Overview

BNOS is a PySide6-based neural network visual orchestration platform providing visual node orchestration, process management, real-time monitoring, and more.

### Core Features

| Module | Description |
|---------|------|
| Node Management | Node creation, start, stop, deletion |
| Canvas Orchestration | Visual node wiring and data flow orchestration |
| Process Monitoring | Real-time node process status and resource monitoring |
| Project Management | Project create, open, save, import/export |
| External Mounting | Mount external nodes into current project |
| Terminal Integration | Embedded PowerShell/CMD/Bash terminal dock |
| History Rollback | Photoshop-style undo/redo with command pattern |

### Tech Stack

- **Framework**: PySide6 (Qt6 bindings)
- **Language**: Python 3.12+
- **IPC**: QLocalSocket / QLocalServer
- **UI Styling**: QSS (Qt Style Sheets)
- **Architecture Pattern**: Mixin + Registry + Command + EventBus

---

## 2. Architecture Design

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     BNOS Console                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Launch     │───▶│   UI Layer  │───▶│  Business   │        │
│  │ bnos_console│    │ main_window │    │ node_process│        │
│  │             │    │ canvas_view │    │ ipc         │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│         │                  │                  │                │
│         ▼                  ▼                  ▼                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Terminal    │    │   Panels    │    │  Managers   │        │
│  │ terminal/   │    │ node_list   │    │ polling     │        │
│  │             │    │ node_monitor│    │ project     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

### Layered Architecture

| Layer | Components | Description |
|-------|-----------|-------------|
| **UI Layer** | `main_window/`, `canvas/`, `panels/`, `dialogs/` | User interface rendering and interaction |
| **Core Services** | `core/`, `menu/`, `icons/` | EventBus, DI, process management, actions |
| **Data Layer** | `nodes/`, `app_config.json`, `canvas_layout.json` | Persistent storage and runtime data |
| **Tool Layer** | `tools/` | Node template generators |

---

## 3. Core Component Details

### 3.1 Launch Layer

#### 3.1.1 bnos_console.py

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

### 3.2 Main Window Layer

#### 3.2.1 ui/main_window/__main__.py

**Responsibility**: Main window hub integrating 8 Mixin modules

**Mixin Modules**:

| File | Mixin Name | Responsibility |
|------|-----------|--------------|
| `state.py` | `MainWindowStateMixin` | Window state, node data, project path management |
| `lifecycle.py` | `MainWindowLifecycleMixin` | Initialization, shutdown orchestration, save/restore |
| `actions.py` | `MainWindowActionsMixin` | Action binding, toolbar, menu setup |
| `panel.py` | `MainWindowPanelMixin` | Floating panel and dock management |
| `ipc.py` | `MainWindowIPCMixin` | IPC server setup, secondary instance handling |
| `node.py` | `MainWindowNodeMixin` | Node control delegation (start/stop/restart) |
| `interaction.py` | `MainWindowInteractionMixin` | Keyboard shortcuts, drag-drop, window events |

**Architecture**: Each Mixin focuses on a single concern. The main class inherits all Mixins, keeping `__main__.py` under ~500 lines.

---

### 3.3 Canvas Layer

#### 3.3.1 Canvas Architecture

The canvas layer follows a **View + Mixins + Items** architecture:

```
ui/canvas/
├── canvas_view.py          # Main controller (QGraphicsView)
├── mixins/                 # Functional mixins
│   ├── canvas_layout.py       # Layout persistence
│   ├── canvas_connections.py  # Edge creation/management
│   ├── canvas_menus.py        # Right-click menus
│   ├── canvas_batch_ops.py    # Batch start/stop/clear
│   ├── canvas_box_select.py   # Box selection
│   ├── canvas_colors.py       # Color management
│   ├── canvas_event_handlers.py # Mouse/keyboard events
│   ├── canvas_node_manager.py # Node CRUD on canvas
│   ├── canvas_selection.py    # Selection logic
│   ├── canvas_background_renderer.py # Grid background
│   └── controllers.py         # Save/load controllers
├── items/                  # Graphics items
│   ├── node_item.py
│   ├── edge_item.py
│   ├── anchor_item.py
│   ├── anchor_manager.py
│   ├── node_status_widget.py
│   └── styles/             # Style registry
│       ├── _base.py
│       └── detailed.py
├── drawing/                # Drawing layer
│   ├── draw_layer.py
│   ├── draw_toolbar.py
│   └── graphic_items/      # Shape registry
│       ├── _base.py
│       ├── rect.py
│       ├── arrow.py
│       └── text.py
└── parameter_widgets/      # Parameter widget registry
    ├── _base.py
    ├── string.py
    ├── int_widget.py
    └── ... (11 types)
```

#### 3.3.2 canvas_view.py

**Class `NodeCanvas(QGraphicsView)`**: Main canvas container, inherits all canvas mixins.

**Key Attributes**:
- `self.nodes: dict[str, NodeItem]` → node name → node graphic item
- `self.edges: list[EdgeItem]` → all edges
- `self._save_timer: QTimer` → auto-save debounce timer (500ms)
- `self.canvas_width / canvas_height` → logical canvas dimensions

**Key Methods**:
- `save_layout(project_path)` → persists to `canvas_layout.json`
- `load_layout(project_path)` → restores from `canvas_layout.json`

#### 3.3.3 canvas_layout.py

**Save Flow**:
1. Traverse `self.nodes` → write x/y/width/height/style/custom_colors
2. Traverse `self.edges` → write source/target/source_port/target_port
3. Save view state (scale/scroll/center)
4. Atomic write to `<project>/canvas_layout.json`

**Load Flow**:
1. `_save_timer.stop()` — prevent save during load
2. Read `canvas_layout.json`
3. Traverse nodes → create/update NodeItem
4. Traverse edges → bind to specific ports via `AnchorManager`
5. `_validate_edge_anchor_binding()` — fix stale references
6. Restore view state

#### 3.3.4 Items Module

**NodeItem**: Container for node graphics, supports 3 styles via StyleRegistry
- **Rect**: Standard rectangular with full anchors
- **Dot**: Compact circular with z-layered architecture
- **Detailed**: ComfyUI-style with inline parameter widgets

**EdgeItem**: Orthogonal connections with draggable fold handles
- Long-press + drag to create fold waypoints
- Target/source port memory for anchor rebinding

**AnchorManager**: Manages input/output anchors per node
- Multi-port support (`input_ports` from `config.json`)
- Required ports prioritized as default connection points
- Edge migration on style switch

---

### 3.4 Core Services Layer

#### 3.4.1 event_bus.py

**EventBus Singleton**: Decoupled inter-module communication

```python
event_bus.publish("node.status_changed", node_name="node_1", status="running")
event_bus.subscribe("node.status_changed", on_status_changed)
```

**Common Events**:
- `node.created` / `node.removed` / `node.status_changed`
- `project.opened` / `project.closed`
- `config.modified` / `canvas.layout_saved`

#### 3.4.2 di.py

**DIContainer**: Service registration and resolution

```python
container.register("event_bus", event_bus)
container.register("process_manager", process_manager)
event_bus = container.resolve("event_bus")
```

#### 3.4.3 actions/

**Unified Action System**: ~80 actions across categories

| Category | Files | Examples |
|----------|-------|----------|
| Canvas | `builtin_canvas_actions.py` | zoom, fit_view, reset_view, toggle_draw |
| Node | `builtin_node_actions.py` + `node/` | start, stop, rename, delete, switch_style |
| Project | `builtin_project_actions.py` | new_project, open_project, refresh_nodes |
| View | `builtin_view_actions.py` | toggle_panel, toggle_theme |

**Node Actions Subpackage** (`actions/node/`):
- `_lifecycle.py`: start/stop/restart
- `_context_menu.py`: IDE open, terminal, explorer
- `_batch.py`: batch operations
- `_selection.py`: select/deselect
- `_group.py`: group/ungroup
- `_style.py`: style switching

#### 3.4.4 polling_manager.py

**Unified Polling Manager**: Centralized timer task scheduling

| Task Name | Interval(s) | Purpose |
|-----------|-------------|---------|
| `node_health` | 2 | Node process health check |
| `global_logs` | 2 | Global log detection |
| `global_config` | 2 | Global config detection |
| `node_logs` | 2 | Per-node log detection |
| `node_config` | 2 | Per-node config detection |
| `node_output` | 2 | Per-node output detection |
| `app_state` | 5 | Application state detection |

**Signals**: `node_status_changed`, `log_file_changed`, `config_file_changed`, `output_json_changed`

#### 3.4.5 process_manager.py & node_process.py

**ProcessManager**: UI subprocess lifecycle (canvas, panel, core)
- Health check every 2 seconds
- Auto-restart on crash (max 5 attempts)

**node_process.py**: Individual node process management
- Three-state model: `running` | `idle` | `stopped`
- PID file persistence (`.pid`)
- Orphan process scanning and cleanup
- Cross-session recovery

#### 3.4.6 terminal/

**Embedded Terminal Dock**:
- `terminal_process.py`: QProcess wrapper with ANSI stripping
- `terminal_widget.py`: QTextEdit + input with history
- `terminal_dock.py`: Multi-tab terminal dock (PowerShell/CMD/Bash)

**Features**: Real-time stdout/stderr, tabbed interface, working directory sync to active project

#### 3.4.7 commands/

**Command Pattern History System**:
- `base.py`: `Command` base class with `execute()` / `undo()`
- `history_manager.py`: Flat command list + `current_index` pointer
- `node_commands.py`: AddNodeCommand, RemoveNodeCommand, MoveNodeCommand
- `edge_commands.py`: AddEdgeCommand, RemoveEdgeCommand
- `compound_commands.py`: Multi-operation atomic commands

**Features**: Undo/redo/jump to any history state, precise anchor restoration

#### 3.4.8 toast/

**Toast Notification System**:
- `toast_notification.py`: Individual toast with fade animation
- `toast_queue_manager.py`: FIFO queue, max 3 visible, smart replacement

---

### 3.5 Panel Layer

| Panel | Files | Mode | Description |
|-------|-------|------|-------------|
| Node List | `node_list_panel.py` + `node_list_dock.py` | Floating + Dock | Tree view with groups, drag-drop, multi-select |
| Node Monitor | `node_monitor.py` + `node_monitor_dock.py` | Floating + Dock | Real-time log streaming per node |
| Resource Monitor | `resource_monitor.py` + `resource_monitor_dock.py` | Floating + Dock | System CPU/memory monitoring |
| History | `history_panel.py` | Floating | Visual command history with jump |
| Property | `property_panel.py` | Dialog | Config editor, color settings |
| Expand | `node_expand_panel.py` | Panel | output.json viewer/editor |
| Group Manager | `node_group_manager.py` | Dialog | Group CRUD and persistence |

**Shared Components** (`panels/_shared/`):
- `node_log_sub_panel.py`: Common log display widget
- `node_panel_sync_mixin.py`: Sync logic between panel and canvas
- `system_resource_collector.py`: System metrics collection

---

### 3.6 Project Management Layer

#### 3.6.1 project_manager.py

**Responsibility**: Project create/open/refresh

**Project Structure**:
```
project_dir/
├── nodes/              # Node directory
│   ├── node1/
│   │   ├── config.json
│   │   ├── main.py
│   │   └── ...
│   └── node2/
├── node_registry.json  # Node registry
└── canvas_layout.json  # Canvas layout
```

#### 3.6.2 node_registry.py

**NodeRegistry**: Persistent index of nodes with mount sources

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
    }
}
```

#### 3.6.3 external_node_manager.py

- Mount external nodes via reference (no file copy)
- Auto-create locked groups (🔒)
- Safe unmount preserves source files

#### 3.6.4 connection_inferrer.py

Infers edges from `config.json` `listen_upper_file` and `port_mappings`

---

### 3.7 Utility Layer

| Component | File | Description |
|-----------|------|-------------|
| Logger | `logger.py` | Global logger with rotation (console INFO + file DEBUG) |
| IDE Scanner | `ide_scanner.py` | 4-layer detection: cache → config → PATH → process/fs scan |
| Config Parser | `node_config_parser.py` | ParameterDef / InputPortDef / OutputPortDef parsing |
| Validators | `validators.py` | Node name and path validation |
| i18n | `i18n.py` | CN/EN string resources |
| Theme | `theme.py` | Dark QSS theme |
| Window State | `window_state_manager.py` | Geometry and splitter persistence |
| Shortcuts | `shortcut_manager.py` | Global keyboard shortcuts |

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
| ui/main_window/ | 9 | 1,997 |
| ui/canvas/ | 49 | 7,604 |
| ui/core/ | 69 | 11,816 |
| ui/panels/ | 19 | 5,078 |
| ui/dialogs/ | 5 | 1,555 |
| ui/creators/ | 1 | 268 |
| ui/menu/ | 1 | 109 |
| ui/icons/ | 2 | 711 |
| tools/ | 2 | 1,304 |
| tests/ | 9 | 504 |
| **ui/ Total** | **157** | **29,155** |

### Main Window Layer

| File | Lines | Description |
|------|------|-------------|
| `__main__.py` | ~500 | Main window hub (8 Mixins) |
| `state.py` | ~300 | State management |
| `lifecycle.py` | ~280 | Lifecycle and shutdown |
| `actions.py` | ~250 | Action bindings |
| `panel.py` | ~200 | Panel management |
| `ipc.py` | ~180 | IPC communication |
| `node.py` | ~160 | Node control delegation |
| `interaction.py` | ~127 | User interaction |

### Canvas Layer

| File | Lines | Description |
|------|------|-------------|
| `canvas_view.py` | ~935 | Canvas main view controller |
| `mixins/canvas_layout.py` | ~593 | Layout persistence |
| `mixins/canvas_connections.py` | ~280 | Connection management |
| `mixins/canvas_event_handlers.py` | ~400 | Event handling |
| `mixins/canvas_node_manager.py` | ~240 | Node CRUD |
| `items/edge_item.py` | ~650 | Edge item with orthogonal lines |
| `items/node_item.py` | ~400 | Node container |
| `items/anchor_manager.py` | ~350 | Anchor management |
| `drawing/draw_layer.py` | ~317 | Drawing layer |

### Core Services Layer

| File | Lines | Description |
|------|------|-------------|
| `polling_manager.py` | ~520 | Unified polling manager |
| `canvas_host.py` | ~550 | Canvas host and docking |
| `node_process.py` | ~484 | Node process lifecycle |
| `actions/action_factory.py` | ~300 | Action factory |
| `commands/history_manager.py` | ~250 | History rollback |
| `terminal/terminal_dock.py` | ~224 | Terminal dock |
| `terminal/terminal_process.py` | ~120 | Terminal process |
| `toast/toast_queue_manager.py` | ~180 | Toast queue |
| `event_bus.py` | ~80 | Event bus |
| `di.py` | ~60 | DI container |

---

*Last Updated: 2026-06-17*
