# BNOS - Bionic Neural Network Visual Orchestration Platform

🌍 **Language Selection**: [中文](README_CN.md) | **English**

<div align="center">

![BNOS Banner](https://img.shields.io/badge/BNOS-Visual%20Orchestration-blue?style=for-the-badge&logo=python)
![Python](https://img.shields.io/badge/Python-3.8+-yellow?style=for-the-badge&logo=python)
![PyQt6](https://img.shields.io/badge/PyQt6-Latest-green?style=for-the-badge&logo=qt)
![License](https://img.shields.io/badge/License-MIT-red?style=for-the-badge)

**A Pure Desktop Bionic Visual Orchestration Platform for Building Brain-like Neural Networks**

*Simplify complex distributed neuron systems into an intuitive "drag-connect-run" experience*

[Quick Start](#-quick-start) • [Features](#-core-features) • [Documentation](#-documentation) • [Contributing](#-contributing)

</div>

---

## 🆕 Recent Updates (2026-05-08)

### ✨ New Features & Improvements

#### 1. **VSCode Workspace Integration** 🔧
- **Feature**: Added "Open as VSCode Workspace" button in Node Configuration Dialog
- **Functionality**:
  - Automatically generates standard `.code-workspace` configuration file for the node folder
  - Configures Python virtual environment interpreter path (cross-platform: Windows/macOS/Linux)
  - Excludes `__pycache__` and `.pyc` files from workspace view
  - Opens the workspace directly in VSCode with one click
- **Implementation**: Non-invasive design, only added new function `open_vscode_workspace()` without modifying existing code
- **Affected File**: `ui/property_panel.py` - `NodeConfigDialog` class
- **User Benefit**: Streamlines development workflow by providing instant access to node source code with proper environment configuration

---

## 🆕 Recent Updates (2026-05-07)

### ✨ New Features & Improvements

#### 1. **Connection Anchor Position Fix** 🔧
- **Issue**: Anchors displayed correctly during drag, but shifted to status indicator after connection
- **Fix**: Use `sceneBoundingRect().center()` to directly get anchor geometric center, ensuring connections always attach to anchor center
- **Affected File**: `ui/canvas_widget.py` - `EdgeItem.update_path()` method
- **Technical Improvement**: Eliminated manual offset calculation, improving coordinate accuracy and reliability

#### 2. **Window Stay-on-Top Behavior Optimization** 🪟
- **Issue**: Node list, Toast notifications, and progress windows remained globally on top after switching applications, covering other software windows
- **Fix**: Removed unnecessary `WindowStaysOnTopHint` flags while keeping `Qt.WindowType.Tool` flag
- **Affected Files**:
  - `ui/node_list_panel.py` - Node list panel
  - `ui/main_window.py` - ToastNotification and ProgressFloatingWindow
- **Result**: Tool windows now maintain hierarchy only within the application, without interfering with other applications

#### 3. **Best Practices Documentation** 📚
- Created memory knowledge base documenting QGraphicsItem anchor position calculation best practices
- Documented Qt tool window stay-on-top issue solutions
- Provided technical references and guidelines for future development

### 🎯 Technical Highlights

- **More Accurate Coordinate Calculation**: Replaced `scenePos() + offset` with `sceneBoundingRect().center()`
- **Better User Experience**: Tool windows follow standard Windows behavior, no longer covering other applications
- **Code Quality Improvement**: Captured best practices through memory system to avoid repeating mistakes

---

## 📖 Overview

**BNOS (Bionic Neural Network Program Operating System)** is a desktop-based visual orchestration platform built with **PyQt6**, designed for the BNOS Bionic Neural Network Node System. It provides graphical configuration, drag-and-drop neural circuit construction, and real-time monitoring capabilities.

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
- **Bezier Curves**: Elegant neural pathways clearly showing signal flow direction
- **Multi-select Support**: Hold Ctrl to select multiple neurons for batch operations

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

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│              BNOS GUI (PyQt6)                    │
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
| **Entry Point** | `bnos_gui.py` | Initialize QApplication, launch MainWindow |
| **Main Window** | `ui/main_window.py` | Integrate UI components, manage AppConfig, handle Toast notifications |
| **Canvas** | `ui/canvas_widget.py` | QGraphicsView for neuron rendering, dragging, synapse connections |
| **Node List** | `ui/node_list_panel.py` | Tree view of nodes/groups, context menus, multi-select support |
| **Property Panel** | `ui/property_panel.py` | Config editor, log viewer, process control dialog |
| **Group Manager** | `ui/node_group_manager.py` | Node group management, persistence, batch operations |
| **Node Creator** | `create_node.py` | Multi-language template generator with venv setup |

---

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.8 or higher
- **OS**: Windows 10/11 (primary), Linux/macOS (partial support)
- **Disk Space**: 500MB+ (for virtual environments)

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
pip install -r requirements_gui.txt

# 5. Launch application
python bnos_gui.py
```

#### Option 2: Using Startup Script (Windows)

``powershell
# PowerShell (for paths with spaces)
& ".\start_bnos_gui.bat"

# Or CMD
start_bnos_gui.bat
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
│
├── bnos_gui.py                    # Main entry point
├── create_node.py                 # Node template generator
├── start_bnos_gui.bat             # Windows launcher
├── test_and_start_bnos.bat        # Test + launcher
│
├── ui/                            # UI modules
│   ├── __init__.py
│   ├── main_window.py            # Main window + Toast system
│   ├── canvas_widget.py          # Neural canvas component
│   ├── node_list_panel.py        # Node list with groups
│   ├── node_group_manager.py     # Group management logic
│   └── property_panel.py         # Config dialog
│
├── nodes/                         # Node instances
│   └── (user-created nodes)
│
├── app_config.json                # App settings (window state, last project)
├── canvas_layout.json             # Current project layout (auto-generated)
├── color_settings.json            # Node color customization
└── requirements_gui.txt           # Python dependencies
```

### Extending BNOS

#### Adding Language Support

Edit `detect_language()` in `ui/canvas_widget.py`:

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

Modify `NodeItem.__init__()` in `ui/canvas_widget.py`:

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
pyinstaller --onefile --windowed --name="BNOS" bnos_gui.py
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

MIT License © 2026 Ahdong&Shouey Team

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

- **Team**: Ahdong&Shouey Team
- **GitHub**: [https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform](https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform)
- **Email**: 1240543656@qq.com
- **Last Updated**: 2026-05-08

---

<div align="center">

**⭐ If BNOS helps you, please give it a Star!**

Made with ❤️ by Ahdong&Shouey Team

</div>
