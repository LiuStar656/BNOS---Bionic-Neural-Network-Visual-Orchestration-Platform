# BNOS Console — Bionic Neural Network Visual Orchestration Platform

🌍 **Language Selection**: [中文](README_CN.md) | **English**

<div align="center">

```
 █████╗     ███╗  ██╗     █████╗     ██████╗
 ██╔══██╗   ████╗ ██║    ██╔══██╗   ██╔════╝
 ██████╔╝   ██╔██╗██║    ██║  ██║   ╚█████╗
 ██╔══██╗   ██║╚████║    ██║  ██║    ╚═══██╗
 ██████╔╝   ██║ ╚███║    ╚█████╔╝   ██████╔╝
 ╚═════╝    ╚═╝  ╚══╝     ╚════╝    ╚═════╝
          B N O S   C O N S O L E
```

![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge&logo=python)
![Rust](https://img.shields.io/badge/Rust-Supported-orange?style=for-the-badge&logo=rust)
![PyQt6](https://img.shields.io/badge/PyQt6-Latest-green?style=for-the-badge&logo=qt)
![License](https://img.shields.io/badge/License-MIT-red?style=for-the-badge)

**A Pure Desktop Bionic Visual Orchestration Platform**

[Quick Start](#-quick-start) • [Features](#-core-features) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>


---

> 📋 **See [UPDATE_EN.md](UPDATE_EN.md) for recent changes**

---

## 📖 Overview

**BNOS (Bionic Neural Network Program Operating System)** is a desktop-based visual orchestration platform built with **PyQt6**, designed for the BNOS Bionic Neural Network Node System. It provides graphical configuration, drag-and-drop neural circuit construction, and real-time monitoring capabilities.

**Multi-Language Support**: The platform supports nodes implemented in **Python, Rust, Node.js, Go, Java, C++, and Ruby**, enabling developers to leverage the strengths of different programming languages within a single neural network architecture. Each node runs in an isolated environment with native performance characteristics.

### 🎯 Problem Statement

Traditional distributed neuron systems face these challenges:

1. **Complex Configuration**: Manual JSON editing is error-prone and path mapping is tedious
2. **Unclear Relationships**: Hard to visualize data flow and dependencies between neurons
3. **Difficult Monitoring**: No real-time visibility into neuron status, logs, and errors
4. **Environment Chaos**: Dependency conflicts across multiple independent runtime environments

**BNOS Solution**: Visual canvas, automatic path configuration, real-time monitoring, and one-click lifecycle management.

### 🔍 BNOS vs Low-Code Platforms

While BNOS may appear similar to low-code platforms at first glance, there are fundamental differences in philosophy, architecture, and use cases:

| Aspect | **BNOS Platform** | **Traditional Low-Code Platforms** |
|--------|-------------------|------------------------------------|
| **Core Philosophy** | Code-first with visual orchestration | Visual-first with limited code extension |
| **Node Implementation** | Full programming language support (Python, Rust, Go, Java, etc.) with complete IDE integration | Pre-built components with restricted customization |
| **Execution Model** | Each node runs as an independent process with isolated environment | Centralized runtime engine managing all components |
| **Extensibility** | Unlimited - write any logic in any supported language | Limited to platform-provided plugins or scripts |
| **Performance** | Native performance per node (compiled languages like Rust achieve 10-100x speedup) | Constrained by platform's interpretation layer |
| **Dependency Management** | Per-node virtual environments prevent conflicts | Shared dependencies may cause version conflicts |
| **Debugging** | Standard debugging tools (VSCode, terminal, logs) per node | Platform-specific debuggers with limited capabilities |
| **Portability** | Nodes are standalone applications, easily migratable | Tightly coupled to platform, difficult to extract |
| **Learning Curve** | Requires programming knowledge but offers full control | Easier to start but hits ceiling quickly |
| **Use Cases** | Complex AI agents, distributed systems, research experiments | Simple workflows, business automation, rapid prototyping |
| **Data Flow** | File-based communication (JSON) with attention mechanism filtering | Proprietary messaging protocols |
| **Deployment** | Each node can be deployed independently | Must deploy entire platform |

#### Key Advantages of BNOS:

✅ **True Programming Power**: Not limited by visual abstractions - write complex algorithms, integrate any library, implement custom protocols  
✅ **Language Flexibility**: Mix Python for ML, Rust for performance-critical paths, Go for concurrency - all in one network  
✅ **Independent Evolution**: Each node evolves independently, no platform upgrade required  
✅ **Research-Friendly**: Perfect for experimenting with neural architectures, attention mechanisms, emergent behaviors  
✅ **Production-Ready**: Nodes are standard applications that can run anywhere, not locked into a platform  

#### When to Choose Low-Code:

- Rapid prototyping without coding skills
- Simple business workflows (approval processes, form handling)
- Non-technical users need to build automations
- Standard CRUD operations with predefined connectors

#### When to Choose BNOS:

- Building complex AI agent systems
- Research on neural networks and emergent behaviors
- Performance-critical distributed processing
- Need for full control over implementation details
- Long-term maintainability and portability requirements

**In Summary**: BNOS is a **visual orchestration layer for real code**, not a replacement for programming. It combines the clarity of visual design with the power of traditional development, making it ideal for sophisticated neural network applications where low-code platforms fall short.


---

## 🔗 Node Internal Mechanism Documentation

For developers who want to understand the detailed technical implementation of BNOS nodes, we provide a comprehensive external documentation repository covering:

- **Node Communication Mechanism**: File-based JSON communication protocol and data flow
- **Attention Filtering System**: How nodes filter and process incoming data using attention rules
- **Virtual Environment Isolation**: Per-node environment management and dependency isolation strategies
- **Process Lifecycle Management**: Node startup, monitoring, shutdown, and error recovery mechanisms
- **Configuration Structure**: Detailed explanation of config.json fields and their effects

📚 **[View Node Technical Documentation →](https://github.com/LiuStar656/Bionic-Neural-Network-Operating-System)**

This documentation provides deep technical insights beyond what's covered in this README, helping developers understand how nodes work internally and how to create custom implementations.


---

## ✨ Core Features

### 🎨 Visual Neural Network Orchestration

- **Infinite Canvas**: Mouse wheel zoom (0.1x-5.0x), right-click drag pan, free-form neuron layout
- **Drag & Drop**: Drag neurons from list to canvas with automatic position calculation to avoid overlaps
- **Smart Synapse Connections**: Click output anchor → input anchor, auto-configure upstream/downstream paths
- **Straight Line System**: ComfyUI-style orthogonal lines, each segment midpoint has a draggable blue fold handle; long-press + drag to create fold waypoints
- **Multi-select Support**: Hold Ctrl to select multiple neurons for batch operations

### 🖥️ VSCode-Style Dark Interface

- **Black Frameless Window**: VSCode-inspired dark theme (`#1e1e1e`), menu bar inline with title bar
- **Custom Title Bar**: Minimize/maximize/close buttons, double-click to maximize, drag to move
- **Global Dark Theme**: Menus, scrollbars, inputs, tables, dialogs all in dark style

### ⚡ High-Performance Canvas Rendering

- **Viewport Culling**: Only renders elements within visible area, minimizing wasted draws
- **Background Caching**: Grid background cached, no redraw during pan/zoom
- **Smart Refresh**: Only repaints changed regions, smooth panning and zooming without lag

### 🩺 Process Health Detection

- **PID File Persistence**: Writes `.pid` on start, deletes on stop for traceable node status
- **Cross-Session Recovery**: GUI restart auto-scans `.pid` to detect background processes, restores ● running state
- **Periodic Health Check**: Polls running processes every 3s, crashed nodes auto-marked ○ stopped

### 🖱️ Unified Selection System

- **Single/Box/Ctrl+Click** all use unified `box_selected_nodes`
- Box-selected nodes support **group dragging**, right-click menu adapts to single/multi selection
- Dragging nodes **auto-pushes** away adjacent nodes to prevent overlap
- Node expand button `>>` for quick output/config access

### 🎯 Node Style System

- **Rect Nodes** (default): Standard rectangular style with full anchors, expand button, status indicators
- **Dot Nodes**: Compact circular style with three-layer z-architecture (indicator > input > output), text below left-aligned
- **Style Persistence**: Each node's style auto-saved to `canvas_layout.json`, fully restored on restart
- **Selection Ring**: Dot nodes display a floating selection ring (z=10) on selection

### 📂 Project Management

- **VSCode-like Workflow**: Open folder as project, auto-detect `nodes/` directory
- **Auto-save & Recovery**: Persist window state, splitter ratio, last opened project
- **Layout Isolation**: Each project's neuron positions saved independently to `canvas_layout.json`
- **State Persistence**: Complete restoration of network topology after restart

### 🔧 Neuron Lifecycle Management

- **7 Language Support**: Python, Node.js, Go, Java, C++, Rust, Ruby
- **One-click Creation**: Graphical wizard generates standardized templates with isolated venv environments
- **Smart Renaming**: Right-click rename synchronously updates folder, config, and canvas references
- **Independent Runtime**: Each neuron has its own virtual environment, preventing dependency conflicts
- **🚀 Enhanced Rust Nodes** (NEW):
  - **Self-Healing Architecture**: Automatic detection and repair of missing/corrupted build artifacts
  - **Dual Binary System**: Separate executables for processing (`{node_name}`) and listening (`{node_name}_listener`)
  - **Performance Optimization**: Release mode builds with LTO, achieving 10-100x speedup over interpreted languages
  - **Memory Safety**: Compiler-enforced ownership model eliminates data races and memory leaks
  - **Auto-Rebuild on Startup**: Validates Rust toolchain and binaries, rebuilds if necessary before execution
  - **Modular Design**: Clean separation of concerns (main.rs, listener.rs, packet.rs)
  - **Cross-Platform Launchers**: Platform-specific startup scripts with environment validation

### ⚙️ Configuration Editor

- **Double-click Edit**: Quick access to `config.json` via double-click or right-click menu
- **Attention Mechanism Rules**: Visual table editor for filter rules (add/delete/modify/query)
- **Real-time Validation**: Changes take effect immediately without neuron restart
- **Terminal Integration**: One-click terminal launch with activated venv for debugging

### 📊 Real-time Monitoring

- **Status Indicators**: Green (running) / Gray (stopped) lights for instant status awareness
- **Log Viewer**: Real-time `listener.log` streaming with scrollback history
- **Process Control**: One-click start/stop with process group cleanup
- **Error Alerts**: Immediate feedback for startup failures and configuration errors

### 📦 Dynamic Resource Manager

BNOS's core resource abstraction layer, treating nodes, groups, and mounts as unified manageable resources with runtime discovery, registration, organization, and lifecycle management.

**Node Registry**
- **Persistent Records**: `node_registry.json` stores each node's name, path, mount source, and last active time
- **Scan-First Principle**: On restart, scans `nodes/` directory first; registry serves as auxiliary data source
- **Missing Detection**: Registered nodes with missing directories auto-marked as `missing`, preserving history

**External Node Mounting**
- **Cross-Project Reuse**: Select an external node folder; identified via `config.json` and mounted into current project (no file copy)
- **Locked Group Protection**: Auto-creates locked groups (🔒) named by absolute path; nodes cannot be moved in/out; source files preserved
- **Same-Source Sub-grouping**: Mounted nodes from the same root can freely create sub-groups within the locked group
- **Safe Unmount**: Right-click unmount keeps source files intact, only removes project association

**Node Group Management**
- **Flat Organization**: Groups are independent and parallel (like Photoshop layers), no nesting
- **Drag-to-Group**: Drag nodes in the list to move them in/out of groups; supports batch operations
- **Auto-Cleanup**: Empty groups are auto-deleted (except locked groups)
- **Color Coding**: Each group can have a custom color for visual distinction

### 🎯 Smart UI Features

- **Toast Notifications**: Non-intrusive pop-up notifications with stack display
  - ✅ No quantity limit - all notifications visible
  - ✅ Auto-fade in/out animations (300ms)
  - ✅ Boundary detection prevents screen overflow
  - ✅ Fixed at top-right corner, follows window movement
  
- **Node List Panel**: Floating panel fixed at top-left corner
  - ✅ Always visible, follows window movement
  - ✅ Tree structure with node groups support
  - ✅ Multi-select with Ctrl/Shift keys
  - ✅ Context-aware right-click menu
  
- **Context-Aware Menus**: Dynamic menus based on selection state
  - Single node: Start, Stop, Rename, Delete, Add to Canvas
  - Multiple nodes: Batch start/stop, batch move to group
  - Group: Start all nodes in group, expand/collapse
  - Empty area: Create group, refresh, select all

### 💾 Data Persistence

- **Debounce Save**: Auto-save 500ms after canvas changes (movement, connections, zoom)
- **Complete Recovery**: Restore positions, connections, zoom level, scroll position
- **Exception Handling**: Auto-backup corrupted JSON as `.bak` files
- **Color Settings**: Customizable node colors persisted per project
- **Config Validation**: `canvas_layout.json` loading cross-validates against each node's `config.json` `listen_upper_file`, auto-repairing missing edges — config is the source of truth

### 🌐 Multi-Language Support

- **CN/EN bilingual**: 408 i18n key-values in `strings_cn.json` / `strings_en.json`
- **Runtime switch**: File → Settings → Switch language, auto-restart
- **Persistent**: Choice saved to `app_config.json`

### 🎨 PS-Style Drawing Tools

- **5 shapes**: Rectangle, Rounded rect, Polygon (double-click close), Arrow, Text
- **Alt-key toggle**: Default mouse for nodes, Alt for graphics edit (select/drag/scale)
- **Left vertical toolbar**: 40px wide, VSCode theme, undo/redo stack
- **Right-click delete**: Delete graphics directly on canvas

### 🛠️ Other Features

- **Standalone launcher**: `launcher.py` pure tkinter, zero deps, packable as EXE. Splash appears instantly → backgrounds venv main program → real-time progress sync → auto-close at 100%
- **Process isolation**: Optional canvas subprocess mode, crash-safe (debug stage)
- **Settings dialog**: Language + process isolation toggle (Ctrl+,)
- **Unified dialogs**: All popups self-drawn dark, `themed_message` replaces QMessageBox
- **External node mounting**: Mount external project nodes without copying
- **Color settings**: 11 canvas/node/anchor/edge color adjustments, Apply preview, Confirm close


---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│              BNOS Console (PyQt6)                    │
│                                                  │
│  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ Node List    │  │   Neural Network Canvas  │ │
│  │ Panel        │  │                          │ │
│  │ (Top-Left)   │  │  [Nodes & Synapses]      │ │
│  │              │  │                          │ │
│  └──────────────┘  └──────────────────────────┘ │
│         ↓                    ↓                   │
│  ┌──────────────────────────────────────────┐  │
│  │       Local File System (nodes/)          │  │
│  │  config.json | listener.log | output.json │  │
│  └──────────────────────────────────────────┘  │
│         ↓                    ↓                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │Neuron_1  │  │Neuron_2  │  │  Neuron_N    │ │
│  │(venv)    │  │(venv)    │  │  (venv)      │ │
│  └──────────┘  └──────────┘  └──────────────┘ │
└─────────────────────────────────────────────────┘
```

### Module Structure

| Module | File | Description |
|--------|------|-------------|
| **Entry Point** | `bnos_console.py` | Initialize QApplication, launch MainWindow |
| **Main Window** | `ui/main_window.py` | Integrate UI components, AppConfig, Toast, node data |
| **Canvas** | `ui/canvas/canvas_view.py` | QGraphicsView node rendering, dragging, edges |
| **Node Styles** | `ui/canvas/items/node_style.py` | Node style system (rect/dot), 3-layer z-architecture |
| **Node List** | `ui/panels/node_list_panel.py` | Tree view, groups, drag-drop, multi-select |
| **Property Panel** | `ui/panels/property_panel.py` | Config editor, log viewer, process control, colors |
| **Expand Panel** | `ui/panels/node_expand_panel.py` | output.json viewer/editor with live refresh |
| **Node Monitor** | `ui/panels/node_monitor.py` | Real-time logs for all canvas nodes |
| **Group Manager** | `ui/panels/node_group_manager.py` | Node group CRUD and persistence |
| **Floating Panel** | `ui/core/floating_panel.py` | Base class for frameless translucent panels |
| **Logger** | `ui/core/logger.py` | Global logger (console INFO + file DEBUG) |
| **Menu Manager** | `ui/menu/menu_manager.py` | Unified menu bar (File/Edit/Tools/Help) |
| **Node Creator** | `ui/creators/node_creator_manager.py` | Multi-language node creation manager |
| **Tools** | `tools/python_create_node.py` | Python node template generator (venv + scripts) |


---

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.8 or higher
- **OS**: Windows 10/11 (primary), Linux/macOS (partial support)
- **Disk Space**: 500MB+ (for virtual environments)

### Multi-Language Node Support

BNOS supports nodes implemented in multiple programming languages. The following toolchains are required based on your node language choice:

| Language | Required Toolchain | Notes |
|----------|-------------------|-------|
| **Python** | Python 3.8+ + venv | Built-in support |
| **Rust** | Rust toolchain (rustc/cargo) | Auto-detects and rebuilds |
| **Node.js** | Node.js 16+ | npm packages auto-install |
| **Go** | Go 1.18+ | `go mod` support |
| **Java** | JDK 11+ | Maven/Gradle optional |
| **C++** | MSVC/GCC/Clang | CMake optional |
| **Ruby** | Ruby 2.7+ | Bundler support |

> **Note**: Only Python is required to run the BNOS Console itself. Other language toolchains are only needed when creating nodes in those languages.

### Installation

#### Option 1: From Source (Recommended for Development)

```bash
# 1. Clone repository
git clone https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform.git
cd "BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform-main"

# 2. Create virtual environment
python -m venv myenv_new

# 3. Activate environment
# Windows:
myenv_new\Scripts\activate
# Linux/macOS:
source myenv_new/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Launch application
python bnos_console.py
```

#### Option 2: Using Startup Script (Windows)

``powershell
# PowerShell (for paths with spaces)
& ".\start_bnos_console.bat"

# Or CMD
start_bnos_console.bat
```

> **Note**: First run will automatically check and install PyQt6 if missing.

### Your First Project

1. **Create Project**
   ```
   Toolbar → New Project → Select Folder
   ```
   System creates `nodes/` directory automatically.

2. **Create Neurons**
   ```
   Toolbar → New Node → Enter Name → Select Language → OK
   ```
   Generates complete structure: `config.json`, `main.py`, `listener.py`, `start.bat`, `venv/`

3. **Add to Canvas**
   ```
   Right-click node in list → ➕ Add to Canvas
   ```
   Nodes appear with auto-calculated positions.

4. **Connect Neurons**
   - Click and hold **OUT** anchor (blue dot) on source node
   - Drag to **IN** anchor (green dot) on target node
   - Release to create synapse (auto-configures paths)

5. **Start Neurons**
   ```
   Double-click node → Click ▶️ Start
   ```
   Status light turns green when running.


---

## 📋 User Guide

### Node Management

#### Creating Nodes
```
Toolbar → New Node → Name + Language → OK
```
- Supported: Python, Node.js, Go, Java, C++, Rust, Ruby
- Auto-generated: Config, templates, startup scripts, isolated venv

#### Renaming Nodes
```
Right-click → ✏️ Rename → New Name → OK
```
- Updates: Folder name, `node_name` in config, canvas display
- Validates: Unique name, alphanumeric + underscores only

#### Deleting Nodes

**Option 1: Remove from Canvas Only** (Recommended for batch operations)
```
Right-click on canvas → Delete Selected Nodes
```
- Removes nodes from canvas view only
- Does NOT delete source files or configurations
- Safe for temporary cleanup

**Option 2: Complete Deletion**
```
Right-click node in list → 🗑️ Delete → Confirm
```
- Removes entire node folder from disk
- Cleans up related synapses and path configurations
- ⚠️ **Irreversible action** - use with caution

#### Adding to Canvas
```
Right-click → ➕ Add to Canvas
```
- Auto-layout: Avoids overlaps with existing nodes
- First node: Position (200, 150)
- Subsequent: Offset (50, 50) from bottom-right node

### Canvas Operations

#### Navigation
- **Pan**: Ctrl + Left-click drag on empty area (hand cursor)
- **Zoom**: Ctrl + Mouse wheel (0.1x - 5.0x), centered on mouse position
- **Scroll**: Single mouse wheel for vertical scrolling
- **Select**: Left-click on node
- **Multi-select**: 
  - Ctrl + Click nodes (toggle selection)
  - Left-click drag on empty area (box selection with blue rectangle)

#### Node Manipulation
- **Move**: Drag node body (not anchors)
- **Synapses Update**: Bezier curves follow in real-time
- **Auto-save**: Positions saved 500ms after drag stops

#### Synapse Management
- **Create**: OUT anchor → IN anchor
- **Delete**: Right-click synapse → Delete Connection
- **Clear All**: Toolbar → Clear Connections

#### View Control
- **Reset**: Toolbar → Reset View (1.0x zoom, centered)
- **Fit Content**: Coming soon

### Node Groups

#### Creating Groups
```
Right-click empty area → Create Group → Enter Name
```

#### Managing Groups
```
Right-click group → Expand/Collapse
Right-click node → Move to Group → Select Group
```

#### Batch Operations
```
Ctrl + Click multiple nodes → Right-click → Batch Start/Stop
Right-click group → Start All Nodes in Group
```

### Configuration Editing

#### Opening Config Dialog
```
Method 1: Double-click canvas node
Method 2: Right-click → ⚙️ Edit Config
Method 3: Canvas node right-click → ⚙️ Open Config
```

#### Configuration Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `node_name` | string | Unique identifier | `"data_processor"` |
| `language` | string | Programming language | `"Python"` |
| `listen_upper_file` | string | Upstream output path (auto-set) | `"../node_1/output.json"` |
| `output_type` | string | Output data type | `"data_result"` |
| `filter` | array | Attention mechanism rules | `[{"key": "type", "value": "task"}]` |

#### Filter Rules Editor
- **Add**: Click "➕ Add Rule"
- **Delete**: Select row → "➖ Delete Rule"
- **Edit**: Double-click cell
- **Empty Array**: No filtering, process all tasks

#### Quick Actions
- **💻 Terminal**: Open terminal with activated venv (Windows: CMD, macOS: Terminal, Linux: gnome-terminal/konsole)
- **📁 Explorer**: Open node folder in file explorer
- **🔧 VSCode Workspace**: Generate `.code-workspace` file and open in VSCode with configured Python interpreter
- **▶️/⏹️ Start/Stop**: Control node process
- **📄 Logs**: View `listener.log` in real-time

### Project Management

#### Opening Projects
```
Toolbar → Open Project → Select Folder
```
- Auto-detects `nodes/` directory
- Loads all nodes to list
- Restores canvas layout if available

#### Creating New Projects
```
Toolbar → New Project → Select Folder
```
- Creates empty `nodes/` directory
- Clears canvas and node list

#### Auto-Recovery
- Reopens last project on startup
- Restores window state, splitter ratio
- Recovers canvas topology and view state


---

## 🔧 Developer Guide

### Project Structure

```
BNOS/
├── launcher.py                     # Standalone launcher (tkinter, packable EXE)
├── start_bnos_console.vbs          # Zero-window launcher
├── start_bnos_console.bat          # Windows fallback launcher
├── start_bnos_console.sh           # Linux/Mac launcher
├── bnos_console.py                 # Main entry
├── requirements.txt                # Python dependencies
├── build_bnos.spec                 # PyInstaller spec
├── app_config.json                 # App config (window/lang/process mode)
├── README.md / README_CN.md        # Documentation
├── UPDATE_CN.md / UPDATE_EN.md     # Changelog
│
├── ui/                             # UI modules
│   ├── main_window.py              # Main window (BNOSMainWindow)
│   ├── canvas_widget.py            # Canvas compat (Facade)
│   │
│   ├── core/                       # Core components
│   │   ├── i18n.py                 # i18n (cn/en runtime switch)
│   │   ├── strings_cn.json         # Chinese (408 keys)
│   │   ├── strings_en.json         # English (408 keys)
│   │   ├── app_config.py           # App config persistence
│   │   ├── theme.py                # Dark QSS theme
│   │   ├── logger.py               # Logger (console + file)
│   │   ├── node_process.py         # Node process management
│   │   ├── node_creation_worker.py # Async node creation
│   │   ├── node_registry.py        # Node registry (persistent)
│   │   ├── connection_inferrer.py  # Edge config validation
│   │   ├── dark_title_bar.py       # Frameless title bar
│   │   ├── floating_panel.py       # Floating panel base
│   │   ├── splash_screen.py        # Splash (ASCII + log + progress)
│   │   ├── ipc.py                  # IPC (QLocalSocket + JSON)
│   │   ├── process_manager.py      # Subprocess manager
│   │   ├── project_manager.py      # Project (new/open)
│   │   ├── external_node_manager.py# External node mount
│   │   ├── window_state_manager.py # Window state persistence
│   │   ├── toast/                  # Toast notification system
│   │   └── utils/                  # Utility modules
│   │       ├── dialog_utils.py     # Unified dialogs
│   │       ├── file_utils.py       # File operations
│   │       └── log_viewer.py       # Log viewer
│   │
│   ├── menu/                       # Menu system
│   │   └── menu_manager.py
│   │
│   ├── dialogs/                    # Dialogs
│   │   ├── color_settings_dialog.py# Color settings
│   │   └── settings_dialog.py      # Settings (lang/process)
│   │
│   ├── canvas/                     # Canvas engine
│   │   ├── canvas_view.py          # NodeCanvas controller
│   │   ├── canvas_colors.py        # Color management Mixin
│   │   ├── canvas_layout.py        # Layout persistence Mixin
│   │   ├── canvas_menus.py         # Context menu Mixin
│   │   ├── canvas_connections.py   # Connection management Mixin
│   │   ├── canvas_box_select.py    # Box selection Mixin
│   │   ├── canvas_batch_ops.py     # Batch operations Mixin
│   │   ├── canvas_process.py       # Canvas subprocess entry
│   │   ├── graphic_items.py        # Drawing shapes (rect/arrow/text)
│   │   ├── draw_layer.py           # Drawing layer management
│   │   ├── draw_toolbar.py         # PS-style left vertical toolbar
│   │   └── items/                  # Graphics items
│   │       ├── node_item.py        # Node container
│   │       ├── node_style.py       # Node style (rect/dot)
│   │       ├── edge_item.py        # Orthogonal edge + fold
│   │       └── anchor_item.py      # Anchor (IN/OUT port)
│   │
│   ├── panels/                     # Panels
│   │   ├── node_list_panel.py      # Node list panel
│   │   ├── node_list_context.py    # Context menu Mixin
│   │   ├── node_list_drag.py       # Drag-drop grouping Mixin
│   │   ├── property_panel.py       # Property/config panel
│   │   ├── node_group_manager.py   # Group management
│   │   ├── node_expand_panel.py    # Node expansion panel
│   │   ├── node_monitor.py         # Live log monitor
│   │   └── panel_process.py        # Panel subprocess entry
│   │
│   ├── creators/                   # Node creators
│   │   └── node_creator_manager.py # Multi-language node creation
│   │
│   └── docs/                       # Documentation & examples
│
├── tests/                          # Test scripts
├── tools/                          # Node generation tools
│   ├── python_create_node.py       # Python node template generator
│   ├── rust_create_node.py         # Rust node template generator
│   └── README.md
│
└── nodes/                          # Runtime node dir (user-created)
    └── [node_name]/
        ├── config.json             # Node configuration
        ├── output.json             # Output data
        ├── logs/listener.log       # Listener log
        ├── venv/                   # Isolated virtual environment
        └── ...                     # Source code files
```

**Architecture Highlights**:
- ✅ **Unified Floating Panels**: All windows share `FloatingPanel` base class
- ✅ **Modular Canvas**: Split into Items/Core/Mixin multi-layer architecture
- ✅ **Node Style System**: Abstract base class + implementations, rect/dot styles switchable
- ✅ **Separation of Concerns**: UI rendering isolated from business logic
- ✅ **Backward Compatible**: Old import paths still work via Facade pattern
- ✅ **Extensible**: Easy to add custom node types and interactions
- ✅ **Global Logger**: All print() migrated to logger (console + file)
- ✅ **Lean Codebase**: `main_window.py` 935 lines, `canvas_view.py` ~1200 lines

### Extending BNOS

#### Adding Language Support

Edit `detect_language()` in `ui/canvas/canvas_view.py`:

```python
def detect_language(self, node_path):
    """Detect node programming language"""
    if os.path.exists(os.path.join(node_path, "main.py")):
        return "Python"
    elif os.path.exists(os.path.join(node_path, "main.js")):
        return "Node.js"
    # Add new language...
    elif os.path.exists(os.path.join(node_path, "Main.kt")):
        return "Kotlin"
    return "Unknown"
```

#### Customizing Node Styles

Modify `NodeItem.__init__()` in `ui/canvas/items/node_item.py`:

```python
# Node background color
self.setBrush(QBrush(QColor("#f8f9fa")))  # Change color

# Node dimensions
super().__init__(x, y, w, h, None)  # w=140, h=80 adjustable
```

#### Adding Toolbar Buttons

Extend `init_toolbar()` in `ui/main_window.py`:

```python
custom_action = QAction("Custom Feature", self)
custom_action.triggered.connect(self.custom_function)
toolbar.addAction(custom_action)
```

#### Customizing Toast Notifications

Toast system in `ui/main_window.py`:

```python
# Show notification
self.show_toast("Operation successful", "success", duration=3000)

# Types: "info", "success", "warning", "error"
# Duration: milliseconds (default 3000)
```

### Packaging

#### Windows EXE

```bash
# Install PyInstaller
pip install pyinstaller

# Package
pyinstaller --onefile --windowed --name="BNOS" bnos_console.py
```

Output: `dist/BNOS.exe` (~100MB+, includes PyQt6)


---

## 🎯 Use Cases

### 🤖 AI Agent Workflows
- **Perception Nodes**: Image recognition, speech-to-text, sensor data
- **Reasoning Nodes**: LLM calls, logic evaluation, decision making
- **Execution Nodes**: API calls, database ops, file operations
- **Workflow**: Drag-connect to build complete agent pipelines

### 📊 Data Pipelines
- **ETL**: Clean → Transform → Load
- **Real-time**: Collect → Analyze → Alert
- **Batch**: Scan → Process → Archive

### 🌐 Microservices
- **API Gateway**: Route → Auth → Forward
- **Background Jobs**: Schedule → Execute → Notify
- **Event-driven**: Listen → Process → Update

### 🛠️ Automation
- **CI/CD**: Pull → Build → Test → Deploy
- **Monitoring**: Metrics → Thresholds → Alerts
- **Operations**: Health checks → Cleanup → Backup

### 🔬 Research
- **Neural Simulation**: Nodes → Synapses → Signal propagation
- **Attention Studies**: Filter tuning → Task filtering analysis
- **Emergent Behavior**: Multi-node coordination experiments


---

## ⚠️ Known Limitations

1. **Circular Dependencies**: A→B→A cycles not detected (manual avoidance required)
2. **Path Sensitivity**: Moving project folders may break absolute paths (reconnect needed)
3. **Concurrency**: Multiple instances shouldn't operate on same project simultaneously
4. **Performance**: Canvas may lag with >100 nodes (optimization pending)
5. **Cross-platform**: Linux/macOS features partially tested

### Best Practices

✅ **Naming**: Use lowercase + underscores (`data_processor`)  
✅ **Saving**: Manual save after critical operations (Ctrl+S planned)  
✅ **Monitoring**: Check logs immediately after starting nodes  
✅ **Backup**: Regularly backup `nodes/` and `canvas_layout.json`  
✅ **Environments**: Don't manually modify `venv/` directories  


---

## ❓ FAQ

### Q: Node failed to start?
**A**: Check:
- Virtual environment created correctly (`venv/` exists)
- Startup script present (`start.bat` or `start.sh`)
- Error messages in `logs/listener.log`
- Try "💻 Open Terminal" in config dialog for manual start

### Q: Downstream node not receiving data?
**A**: Verify:
- Upstream node is running
- `listen_upper_file` path correct in config
- Downstream logs show no filter blocking
- Upstream `output.json` has content

### Q: Canvas empty after restart?
**A**: Ensure:
- Nodes were on canvas before closing (not just in list)
- `canvas_layout.json` exists in project folder
- Check console for load errors

### Q: How to reset node processing state?
**A**: 
- Edit `upper_data.json`, remove `_processed_<node_name>` field
- Or stop node, delete `output.json`, restart


---

## 📄 License

MIT License © 2026 阿东与守一工作室

See [LICENSE](LICENSE) for details.


---

## 👥 Contributing

Contributions welcome! Please read our guidelines:

### Reporting Issues
- **Bugs**: Describe problem, steps to reproduce, expected vs actual behavior, environment info
- **Features**: Explain use case, requirements, desired outcome

### Pull Requests
1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

### Standards
- Follow PEP 8 style guide
- Add docstrings and comments
- Include tests for new features (planned)
- Update documentation


---

## 🙏 Acknowledgments

- **PyQt6 Team**: Powerful cross-platform GUI framework
- **BNOS Neuron System**: Core bionic architecture concepts
- **Open Source Community**: Inspiration from countless excellent projects


---

## 📞 Contact

- **Team**: 阿东与守一工作室
- **GitHub**: [https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform](https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform)
- **Email**: 1240543656@qq.com
- **Last Updated**: 2026-05-21


---

<div align="center">

![BNOS Banner](https://img.shields.io/badge/BNOS-Visual%20Orchestration-blue?style=for-the-badge&logo=python)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge&logo=python)
![Rust](https://img.shields.io/badge/Rust-Supported-orange?style=for-the-badge&logo=rust)
![PyQt6](https://img.shields.io/badge/PyQt6-Latest-green?style=for-the-badge&logo=qt)
![License](https://img.shields.io/badge/License-MIT-red?style=for-the-badge)

**A Pure Desktop Bionic Visual Orchestration Platform for Building Brain-like Neural Networks**

*Simplify complex distributed neuron systems into an intuitive "drag-connect-run" experience*

[Quick Start](#-quick-start) • [Features](#-core-features) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---