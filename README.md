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

[Quick Start](#-quick-start) • [Features](#-core-features) • [Architecture](#-architecture) • [User Guide](#-user-guide) • [Developer Guide](#-developer-guide)

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

---

## ✨ Core Features

### 🎨 Visual Neural Network Orchestration

- **Infinite Canvas**: Mouse wheel zoom (0.1x-5.0x), right-click drag pan, free-form neuron layout
- **Drag & Drop**: Drag neurons from list to canvas with automatic position calculation to avoid overlaps
- **Smart Synapse Connections**: Click output anchor → input anchor, auto-configure upstream/downstream paths
- **Orthogonal Line System**: ComfyUI-style right-angle lines with fold waypoints
- **Multi-select Support**: Hold Ctrl to select multiple neurons for batch operations

### 🖥️ VSCode-Style Dark Interface

- **Black Frameless Window**: VSCode-inspired dark theme (`#1e1e1e`), menu bar inline with title bar
- **Custom Title Bar**: Minimize/maximize/close buttons, double-click to maximize, drag to move
- **Global Dark Theme**: Menus, scrollbars, inputs, tables, dialogs all in dark style

### ⚡ High-Performance Canvas Rendering

- **Viewport Optimization**: Only renders elements within visible area
- **Background Caching**: Grid background cached, no redraw during pan/zoom
- **Smart Refresh**: Only repaints changed regions

### 🩺 Process Health Detection

- **PID File Persistence**: Writes `.pid` on start, deletes on stop for traceable node status
- **Cross-Session Recovery**: GUI restart auto-scans `.pid` to detect background processes
- **Periodic Health Check**: Polls running processes every 3s, crashed nodes auto-marked as stopped
- **Three-State Status Light**: Gray (stopped), Green (idle), Red (running)

### 📂 Project Management

- **VSCode-like Workflow**: Open folder as project, auto-detect `nodes/` directory
- **Auto-save & Recovery**: Persist window state, splitter ratio, last opened project
- **Layout Isolation**: Each project's neuron positions saved independently
- **State Persistence**: Complete restoration of network topology after restart

### 🏷️ Multi-Tab Canvas Management

- **Tabbed Interface**: Multiple project tabs in single window, each with independent canvas state
- **Project Isolation**: Each tab maintains separate node data, layout, and color settings
- **Tab State Persistence**: Tab names, project paths, and pinned states saved/restored

### 🌐 Global Status Synchronization

- **Unified State Source**: All panels subscribe to `polling_manager.node_status_changed` signal
- **Real-time Updates**: Node status changes propagate to all panels simultaneously
- **Consistent Display**: All panels show identical status

### 🔧 Neuron Lifecycle Management

- **Multi-Language Support**: Python (Completed), Rust (Completed), Node.js, Go, Java, C++, Ruby (In Development)
- **One-click Creation**: Graphical wizard generates standardized templates with isolated venv environments
- **Smart Renaming**: Right-click rename synchronously updates folder, config, and canvas references
- **Independent Runtime**: Each neuron has its own virtual environment

### ⚙️ Configuration Editor

- **Double-click Edit**: Quick access to `config.json` via double-click or right-click menu
- **Attention Mechanism Rules**: Visual table editor for filter rules
- **Real-time Validation**: Changes take effect immediately without neuron restart
- **Terminal Integration**: One-click terminal launch with activated venv

### 📊 Real-time Monitoring

- **Status Indicators**: Green (running) / Gray (stopped) lights
- **Log Viewer**: Real-time `listener.log` streaming with scrollback history
- **Process Control**: One-click start/stop with process group cleanup
- **Error Alerts**: Immediate feedback for startup failures and configuration errors

### 📦 Dynamic Resource Manager

- **Node Registry**: Persistent records with `node_registry.json`
- **External Node Mounting**: Cross-project reuse without file copying
- **Node Group Management**: Flat organization with color coding and auto-cleanup

### 🎨 PS-Style Drawing Tools

- **5 Shapes**: Rectangle, Rounded rect, Polygon, Arrow, Text
- **Alt-key Toggle**: Default mouse for nodes, Alt for graphics edit
- **Left Vertical Toolbar**: 56px wide, VSCode theme, undo/redo stack

### 🌐 Multi-Language Support

- **CN/EN bilingual**: 408+ i18n key-values
- **Runtime switch**: File → Settings → Switch language, auto-restart
- **Persistent**: Choice saved to `app_config.json`

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

### Core Modules

| Module | File | Description |
|--------|------|-------------|
| **Entry Point** | `bnos_console.py` | Initialize QApplication, launch MainWindow |
| **Launcher** | `launcher.py` | Standalone tkinter launcher with real-time progress |
| **Main Window** | `ui/main_window.py` | Integrate UI components, manage AppConfig, node data, tabs |
| **Canvas** | `ui/canvas/canvas_view.py` | QGraphicsView node rendering, dragging, edges |
| **Node Styles** | `ui/canvas/items/node_style.py` | Node style system (rect/dot) |
| **Node List** | `ui/panels/node_list_panel.py` | Tree view, groups, drag-drop, multi-select |
| **Property Panel** | `ui/panels/property_panel.py` | Config editor, log viewer, process control |
| **Polling Manager** | `ui/core/polling_manager.py` | Global node status detection and signal distribution |
| **Project Manager** | `ui/core/project_manager.py` | Project operations (new/open/refresh) |
| **Internationalization** | `ui/core/i18n.py` | Language localization system |
| **Logger** | `ui/core/logger.py` | Global logger (console + file) |

---

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.8 or higher
- **OS**: Windows 10/11 (primary), Linux/macOS (partial support)
- **Disk Space**: 500MB+

### Multi-Language Node Support

| Language | Required Toolchain | Notes |
|----------|-------------------|-------|
| **Python** | Python 3.8+ + venv | Built-in support |
| **Rust** | Rust toolchain (rustc/cargo) | Auto-detects and rebuilds |
| **Node.js** | Node.js 16+ | npm packages auto-install |
| **Go** | Go 1.18+ | `go mod` support |
| **Java** | JDK 11+ | Maven/Gradle optional |
| **C++** | MSVC/GCC/Clang | CMake optional |
| **Ruby** | Ruby 2.7+ | Bundler support |

> **Note**: Only Python is required to run the BNOS Console itself.

### Installation

#### Option 1: From Source (Recommended for Development)

```bash
# 1. Clone repository
git clone https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform.git
cd "BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform"

# 2. Create virtual environment
python -m venv venv

# 3. Activate environment
# Windows:
myenv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Launch application
python bnos_console.py
```

#### Option 2: Using Startup Script (Windows)

```powershell
& ".\start_bnos_console.bat"
```

### Your First Project

1. **Create Project**
   ```
   Menu → File → New Project → Select Folder
   ```

2. **Create Neurons**
   ```
   Menu → Edit → New Node → Select Language → OK
   ```

3. **Add to Canvas**
   ```
   Right-click node → Add to Canvas
   ```

4. **Connect Neurons**
   - Click and hold **OUT** anchor on source node
   - Drag to **IN** anchor on target node
   - Release to create synapse

5. **Start Neurons**
   ```
   Double-click node → Click Start
   ```

---

## 📋 User Guide

### Node Management

- **Create**: `Menu → Edit → New Node → Select Language → OK`
- **Rename**: `Right-click → Rename → New Name → OK`
- **Delete**: `Right-click → Delete → Confirm`

### Canvas Operations

- **Pan**: Ctrl + Left-click drag on empty area
- **Zoom**: Ctrl + Mouse wheel (0.1x - 5.0x)
- **Select**: Left-click on node
- **Multi-select**: Ctrl + Click or box selection

### Keyboard Shortcuts

| Shortcut | Function |
|----------|----------|
| `Ctrl+D` | Delete selected nodes/graphics |
| `Ctrl+,` | Open settings dialog |
| `Ctrl+Shift+M` | Open node monitor panel |
| `Ctrl+Shift+O` | Mount external node |

---

## 📁 Project Structure

```
BNOS/
├── launcher.py                     # Standalone launcher (tkinter)
├── bnos_console.py                 # Main entry
├── requirements.txt                # Dependencies
├── app_config.json                 # App configuration
├── ui/                             # UI modules
│   ├── main_window.py              # Main window
│   ├── core/                       # Core components
│   │   ├── i18n.py                 # Internationalization
│   │   ├── logger.py               # Logger
│   │   └── polling_manager.py      # Polling manager
│   ├── canvas/                     # Canvas system
│   │   ├── canvas_view.py          # Canvas view
│   │   └── items/                  # Canvas items
│   ├── panels/                     # UI panels
│   │   ├── node_list_panel.py      # Node list
│   │   └── property_panel.py       # Property panel
│   └── creators/                   # Node creators
├── tools/                          # Node generation tools
│   ├── python_create_node.py       # Python node template
│   └── rust_create_node.py         # Rust node template
└── nodes/                          # Runtime node directory
    └── [node_name]/
        ├── config.json             # Node configuration
        ├── output.json             # Output data
        └── venv/                   # Virtual environment
```

---

## 🎯 Use Cases

### 🤖 AI Agent Workflows
- **Perception Nodes**: Image recognition, speech-to-text, sensor data
- **Reasoning Nodes**: LLM calls, logic evaluation, decision making
- **Execution Nodes**: API calls, database ops, file operations

### 📊 Data Pipelines
- **ETL**: Clean → Transform → Load
- **Real-time**: Collect → Analyze → Alert

### 🌐 Microservices
- **API Gateway**: Route → Auth → Forward
- **Event-driven**: Listen → Process → Update

### 🔬 Research
- **Neural Simulation**: Nodes → Synapses → Signal propagation
- **Attention Studies**: Filter tuning → Task filtering analysis

---

## ⚠️ Known Limitations

1. **Circular Dependencies**: A→B→A cycles not detected
2. **Path Sensitivity**: Moving project folders may break absolute paths
3. **Concurrency**: Multiple instances shouldn't operate on same project simultaneously
4. **Performance**: Canvas may lag with >100 nodes
5. **Cross-platform**: Linux/macOS features partially tested

---

## 📄 License

MIT License © 2026 ADong & Shouyi Studio

See [LICENSE](LICENSE) for details.

---

## 👥 Contributing

Welcome to contribute code, report issues, and suggest improvements!

### Submit Issues
- **Bug Reports**: Describe the problem, reproduction steps, expected behavior, actual behavior, environment info
- **Feature Requests**: Explain the need background, use cases, expected effects

### Submit Pull Requests
1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Open a Pull Request

---

## 📞 Contact

- **Development Team**: ADong & Shouyi Studio
- **GitHub**: [https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform](https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform)
- **Email**: 1240543656@qq.com
- **Last Updated**: 2026-05-25

---

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

</div>