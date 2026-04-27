# BNOS - Bionic Neural Network Visual Orchestration Platform

🌍 Language | Language Selection: [中文](README_CN.md) | **English**

## 📖 Project Overview

**BNOS (Bionic Neural Network Program Operating System)** is a pure desktop-based **bionic visual orchestration platform** built with **PyQt6**, providing graphical configuration, drag-and-drop neural circuit construction, and real-time monitoring capabilities for the **BNOS Bionic Neural Network Node System**.

> **Core Philosophy**: Simplify complex distributed neuron systems into an intuitive "drag-connect-run" experience, enabling every developer to easily build brain-like architecture applications, just like constructing a digital brain with thinking capabilities.

### 🎯 Core Pain Points Solved

1. **Complex Neural Synapse Configuration**: Manual editing of JSON configuration files is error-prone, and path mapping is cumbersome
2. **Non-intuitive Neuron Relationships**: Traditional methods struggle to clearly display data flow and dependencies between neurons
3. **Difficult Neural Signal Monitoring**: Unable to view neuron runtime status, log output, and error information in real-time
4. **Chaotic Multi-environment Management**: Conflicts in independent runtime environments of multiple neurons, cumbersome start/stop operations

BNOS completely solves these problems through **neural network canvas**, **automatic synapse path configuration**, **real-time neural signal monitoring**, and **one-click start/stop**.

---

## ✨ Core Features

### 🎨 Neural Network Visual Orchestration
- **Infinite Brain Cortex**: Support mouse wheel zoom, right-click drag pan, freely layout neurons
- **Drag Interaction**: Drag neurons from the neuron list to the canvas, automatically calculate optimal positions to avoid overlap
- **Intelligent Synapse Connection**: Click output anchor → input anchor, automatically configure upstream/downstream listening paths
- **Bezier Curves**: Elegant neural synapse paths, clearly displaying neural signal flow direction

### 📂 Brain Instance Management
- **VSCode-like Mode**: Open folder as brain instance, automatically recognize `nodes/` directory
- **Auto-save**: Persist last opened brain instance path, window position, Splitter ratio
- **Neural Network Layout Isolation**: Each brain instance's neuron positions and synapse relationships are independently saved to `canvas_layout.json`
- **Restart Recovery**: Completely restore neural network state after closing and reopening the program

### 🔧 Neuron Full Lifecycle Management
- **7 Language Support**: Python, Node.js, Go, Java, C++, Rust, Ruby
- **One-click Creation**: Graphical wizard generates standardized neuron templates, including independent runtime environments and startup scripts
- **Smart Renaming**: Triggered by right-click menu, synchronously update folder name, config file, and neural network references
- **Neuron Independent Runtime Environment**: Each neuron has its own venv, avoiding dependency conflicts

### ⚙️ Configuration Editing
- **Double-click to Edit**: Double-click neuron or right-click "Edit Config" to pop up dialog for modifying `config.json`
- **Attention Mechanism Rule Table**: Visually edit Filter rules, supporting add/delete/modify/query
- **Real-time Validation**: Configuration changes take effect immediately without restarting neurons
- **Command Line Integration**: One-click to open terminal and activate independent runtime environment for debugging

### 📊 Real-time Monitoring
- **Status Indicator Lights**: Green (active) / Gray (dormant), intuitively displaying neuron status
- **Log Viewer**: Real-time reading of `listener.log`, supporting scroll viewing and historical backtracking
- **Process Management**: One-click start/stop neurons, using process groups to ensure thorough cleanup
- **Error Alerts**: Immediate feedback on abnormal situations such as startup failures and configuration errors

### 💾 State Persistence
- **Debounce Save**: Auto-save 500ms after neuron movement, synapse changes, view scaling, etc.
- **Complete Recovery**: Fully restore neuron positions, synapse relationships, zoom ratio, scroll position after restart
- **Exception Tolerance**: Automatically backup corrupted JSON as `.bak`, preventing program crashes

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────┐
│              BNOS GUI (PyQt6)                    │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐ │
│  │Neuron List│ │Neural Canvas │ │Config Dialog│ │
│  │ Panel    │  │  Canvas      │  │  Dialog   │ │
│  └──────────┘  └──────────────┘  └───────────┘ │
│         ↓              ↓               ↓        │
│  ┌──────────────────────────────────────────┐  │
│  │       Local File System (nodes/)          │  │
│  │  config.json | listener.log | output.json │  │
│  └──────────────────────────────────────────┘  │
│         ↓              ↓               ↓        │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Neuron_1 │  │  Neuron_2    │  │ Neuron_3  │ │
│  │ (venv)   │  │   (venv)     │  │  (venv)   │ │
│  └──────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────┘
```

### Core Components

| Module | File | Function |
|--------|------|----------|
| **Main Entry** | `bnos_gui.py` | Initialize QApplication, launch MainWindow |
| **Main Window** | `ui/main_window.py` | Integrate left list, center canvas, right toolbar; manage AppConfig |
| **Neural Network Canvas** | `ui/canvas_widget.py` | QGraphicsView implements neuron drawing, dragging, synapse connections, layout saving |
| **Neuron List** | `ui/node_list_panel.py` | Display all neurons in brain instance, provide right-click menu (start, logs, delete, rename) |
| **Config Dialog** | `ui/property_panel.py` | NodeConfigDialog, edit config.json, view logs, start/stop control |
| **Neuron Tool** | `create_node.py` | Multi-language neuron template generator, auto-create venv and startup scripts |

---

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.8+
- **Operating System**: Windows 10/11 (primary support), Linux/macOS (some features pending testing)
- **Disk Space**: At least 500MB (for independent runtime environments and dependencies)

### Installation Steps

#### Method 1: Run from Source (Recommended for Development)

```bash
# 1. Clone or download the project
git clone <your-repo-url>
cd "Bionic Neural Network Program Operating System"

# 2. Create virtual environment
python -m venv myenv_new

# 3. Activate virtual environment
# Windows:
myenv_new\Scripts\activate
# Linux/macOS:
source myenv_new/bin/activate

# 4. Install dependencies
pip install pyqt6

# 5. Launch the application
python bnos_gui.py
```

#### Method 2: Use Startup Script (Windows)

```powershell
# PowerShell (use & for paths with spaces)
& "f:\Bionic Neural Network Program Operating System\start_bnos_gui.bat"

# Or CMD
start_bnos_gui.bat
```

> **Note**: The script will automatically check and install PyQt6 on first run, please be patient.

### Build Your First Brain Instance

1. **Open Brain Instance Folder**
   - Click the "Open Project" button in the toolbar
   - Select an empty folder (e.g., `D:/MyBNOSProject`)
   - System automatically creates `nodes/` subdirectory

2. **Create Neurons**
   - Click the "New Node" button in the toolbar
   - Enter neuron name (e.g., `data_processor`)
   - Select language (e.g., Python)
   - System automatically generates complete neuron structure

3. **Add to Neural Network Canvas**
   - Right-click neuron in the left neuron list
   - Select "➕ Add to Canvas"
   - Neuron appears at canvas center

4. **Create Neural Synapses**
   - Click the **OUT** anchor point on the right side of a neuron (blue dot)
   - Drag to the **IN** anchor point on the left side of another neuron (green dot)
   - Release mouse, automatically configure listening path

5. **Activate Neurons**
   - Double-click neuron to open config dialog
   - Click "▶️ Start" button
   - Status light turns green, indicating neuron is actively running

---

## 📋 User Guide

### Neuron Management

#### Create Neuron
```
Toolbar → New Node → Enter Name → Select Language → OK
```
- Supported languages: Python, Node.js, Go, Java, C++, Rust, Ruby
- Auto-generated: `config.json`, `listener.py`, `main.py`, `start.bat/sh`, `venv/`

#### Rename Neuron
```
Neuron List Right-click → ✏️ Rename → Enter New Name → OK
```
- Synchronous updates: folder name, `node_name` in `config.json`, neural network canvas display
- Validation rules: unique name, only allows letters, numbers, underscores

#### Delete Neuron
```
Neuron List Right-click → 🗑️ Delete Node → Confirm
```
- Physical deletion: entire neuron folder removed from disk
- Clean up synapses: automatically delete related neural synapses, clear upstream/downstream `listen_upper_file`

#### Add to Neural Network Canvas
```
Neuron List Right-click → ➕ Add to Canvas
```
- Ordered layout: automatically calculate positions to avoid overlap with existing neurons
- First addition: placed at (200, 150)
- Subsequent additions: offset (50, 50) from the bottom-right neuron

### Neural Network Canvas Operations

#### Basic Interactions
- **Pan**: Right-click and drag
- **Zoom**: Mouse wheel (range 0.1x - 5.0x)
- **Select**: Left-click neuron
- **Multi-select**: Hold Ctrl and click multiple neurons

#### Neuron Dragging
- Left-click and hold neuron body area (not anchors) to drag
- Neural synapses follow neuron movement in real-time (dynamic Bezier curve updates)
- Auto-save position 500ms after stopping drag

#### Neural Synapse Operations
- **Create**: Click source neuron OUT anchor → drag to target neuron IN anchor
- **Delete**: Right-click neural synapse → select "Delete Connection"
- **Clear**: Toolbar → "Clear Connections" (will clear all listen_upper_file configurations)

#### View Control
- **Reset View**: Toolbar → "Reset View" (restore to 1.0x zoom, centered display)
- **Fit Content**: Pending implementation (auto-adjust zoom to show all neurons)

### Configuration Editing

#### Open Config Dialog
```
Method 1: Double-click neuron on neural network canvas
Method 2: Neuron list right-click → ⚙️ Edit Config
Method 3: Canvas neuron right-click → ⚙️ Open Config
```

#### Configuration Items

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `node_name` | string | Unique neuron identifier | `"data_processor"` |
| `language` | string | Programming language | `"Python"` |
| `listen_upper_file` | string | Upstream output file path (auto-configured) | `"../node_1/output.json"` |
| `output_type` | string | Output data type | `"data_result"` |
| `filter` | array | Attention mechanism filter rules (table format) | `[{"key": "type", "value": "task"}]` |

#### Attention Mechanism Rule Editing
- **Add Rule**: Click "➕ Add Rule" button
- **Delete Rule**: Select row then click "➖ Delete Rule"
- **Edit Rule**: Double-click cell directly to modify
- **Empty Rules**: Means no filtering, process all tasks

#### Quick Operations
- **💻 Open Command Line**: Launch terminal and activate independent runtime environment (requires neuron started first)
- **📁 Open Folder**: Open neuron directory with file explorer
- **▶️ Start / ⏹️ Stop**: Control neuron process
- **📄 View Logs**: Real-time display of `listener.log` content

### Brain Instance Management

#### Open Brain Instance
```
Toolbar → Open Project → Select Folder
```
- Automatically recognize `nodes/` directory
- Load all neurons to left list
- Restore neural network layout (if `canvas_layout.json` exists)

#### Create New Brain Instance
```
Toolbar → New Project → Select Folder
```
- Create empty `nodes/` directory
- Clear neural network canvas and neuron list

#### Auto Recovery
- Automatically open last closed brain instance on program startup
- Restore window position, size, Splitter ratio
- Restore neural network neuron positions, synapse relationships, view state

---

## 🔧 Developer Guide

### Project Structure

```
Bionic Neural Network Program Operating System/
│
├── bnos_gui.py                    # Main entry point
├── create_node.py                 # Neuron template generator
├── start_bnos_gui.bat             # Windows startup script
├── package_bnos.bat               # Windows packaging script
│
├── ui/                            # UI modules
│   ├── __init__.py
│   ├── main_window.py            # Main window + AppConfig
│   ├── canvas_widget.py          # Neural network canvas component
│   ├── node_list_panel.py        # Neuron list panel
│   └── property_panel.py         # Config dialog
│
├── nodes/                         # Example neurons (can be deleted)
│   ├── node_test/
│   └── node_llama_cpp_engine/
│
├── docs/                          # Documentation
│   ├── README.md                 # This file
│   ├── QUICK_START.md
│   └── ...
│
├── app_config.json                # App-level config (window state, last brain instance)
├── canvas_layout.json             # Current brain instance neural network layout (auto-generated)
└── myenv_new/                     # Virtual environment (gitignore)
```

### Extension Development

#### Add New Language Support
Edit the `detect_language()` method in `ui/canvas_widget.py`:

```python
def detect_language(self, node_path):
    """Detect neuron language"""
    if os.path.exists(os.path.join(node_path, "main.py")):
        return "Python"
    elif os.path.exists(os.path.join(node_path, "main.js")):
        return "Node.js"
    # Add new language...
    elif os.path.exists(os.path.join(node_path, "Main.kt")):
        return "Kotlin"
    return "Unknown"
```

#### Customize Neuron Styles
Modify colors and dimensions in `NodeItem.__init__()` in `ui/canvas_widget.py`:

```python
# Neuron background color
self.setBrush(QBrush(QColor("#f8f9fa")))  # Change to other colors

# Neuron dimensions
super().__init__(x, y, w, h, None)  # w=140, h=80 adjustable
```

#### Add New Toolbar Buttons
Add in the `init_toolbar()` method in `ui/main_window.py`:

```python
custom_action = QAction("Custom Feature", self)
custom_action.triggered.connect(self.custom_function)
toolbar.addAction(custom_action)
```

### Packaging and Distribution

#### Windows EXE Packaging

```bash
# 1. Install PyInstaller
pip install pyinstaller

# 2. Execute packaging script
package_bnos.bat

# Or use command
pyinstaller --onefile --windowed --name="BNOS Node Orchestration Platform" bnos_gui.py
```

The generated `dist/BNOS节点编排平台.exe` can be distributed.

> **Note**: The packaged exe is large (about 100MB+) because it includes the PyQt6 library.

---

## 🎯 Application Scenarios

BNOS visual platform is suitable for the following scenarios:

### 🤖 AI Agent Construction
- **Perception Neurons**: Image recognition, speech transcription, sensor data collection
- **Reasoning Neurons**: LLM invocation, logical judgment, decision generation
- **Execution Neurons**: API calls, database operations, file writing
- **Orchestration Method**: Drag-and-drop connections to form complete Agent workflows

### 📊 Data Pipelines
- **ETL Processes**: Data cleaning → transformation → storage
- **Real-time Processing**: Log collection → analysis → alerting
- **Batch Tasks**: File scanning → processing → archiving

### 🌐 Microservice Components
- **API Gateway**: Request routing → authentication → forwarding
- **Background Tasks**: Scheduled execution → execution → result notification
- **Event-driven**: Message listening → business processing → status updates

### 🛠️ Automation Toolchains
- **CI/CD**: Code pull → compile → test → deploy
- **Monitoring & Alerting**: Metric collection → threshold judgment → notification sending
- **Operations Scripts**: Health checks → log cleanup → backup archiving

### 🔬 Bionic Computing Experiments
- **Neural Network Simulation**: Neurons → synapse connections → signal transmission
- **Attention Mechanism Research**: Filter rule adjustment → task filtering effect observation
- **Distributed Collaboration**: Multi-neuron coordination → emergent behavior exploration

---

## ⚠️ Precautions

### Known Limitations

1. **Circular Dependency Detection**: Currently not implemented for A→B→A cycles, users must avoid manually
2. **Cross-brain Instance Movement**: Moving brain instance folders may invalidate absolute paths, requiring reconnection
3. **Concurrency Safety**: Does not support multiple instances operating on the same brain instance simultaneously
4. **Large-scale Neural Network Performance**: Canvas rendering may lag when neuron count >100 (pending optimization)

### Best Practices

1. **Naming Convention**: Use lowercase letters and underscores for neuron names (e.g., `data_processor`)
2. **Regular Saving**: Although auto-save is enabled, manual saving is recommended after important operations (Ctrl+S, pending implementation)
3. **Log Monitoring**: Check logs promptly after starting neurons to confirm normal operation
4. **Backup Configuration**: Regularly backup `nodes/` directory and `canvas_layout.json` for important brain instances
5. **Environment Isolation**: Do not manually modify neuron `venv/` directories, use the "Open Command Line" feature in the config dialog

### FAQ

#### Q: Neuron startup failed?
**A**: Check the following:
- Whether the independent runtime environment was created correctly (check `venv/` directory)
- Whether startup scripts exist (`start.bat` or `start.sh`)
- Check error messages in log file `logs/listener.log`
- Try clicking "💻 Open Command Line" in the config dialog to start manually

#### Q: Downstream neuron not receiving data after neural synapse connection?
**A**: 
- Confirm upstream neuron is started and running normally
- Check if `listen_upper_file` path in `config.json` is correct
- Check downstream neuron logs to confirm if filtered by attention mechanism rules
- Verify if upstream neuron's `output.json` has content

#### Q: Neural network canvas is empty after restart?
**A**: 
- Confirm neurons were on the canvas before closing (not just in the neuron list)
- Check if `canvas_layout.json` exists in the brain instance folder
- Check console output for error prompts during loading

#### Q: How to reset neuron processing state?
**A**: 
- Manually edit `upper_data.json`, delete `_processed_<node_name>` field
- Or stop neuron in config dialog, delete `output.json`, then restart

---

## 📄 License

This project uses the **MIT License** open source protocol.

```
MIT License

Copyright (c) 2026 Ahdong&Shouey Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👥 Contribution Guidelines

Contributions, bug reports, and suggestions are welcome!

### Submitting Issues
- **Bug Reports**: Describe the problem, reproduction steps, expected behavior, actual behavior, environment information
- **Feature Requests**: Explain requirement background, use cases, desired effects

### Submitting Pull Requests
1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Standards
- Follow PEP 8 code style
- Add necessary comments and docstrings
- Ensure new features have corresponding test cases (pending improvement)
- Update relevant documentation

---

## 🙏 Acknowledgments

- **PyQt6 Team**: For providing powerful cross-platform GUI framework
- **BNOS Neuron System**: For providing core bionic architecture concepts
- **Open Source Community**: Inspiration from numerous excellent projects

---

## 📞 Contact

- **Development Team**: Ahdong&Shouey Team
- **GitHub**: [https://github.com/LiuStar656/BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform]
- **Email**: [1240543656@qq.com]
- **Last Updated**: 2026-04-27

---

**⭐ If this project helps you, please give it a Star to show your support!**
