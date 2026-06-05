# BNOS Update Log

> 📖 中文版：[UPDATE_CN.md](UPDATE_CN.md)

---

## 🔧 Force Delete Node Folder (2026-06-05)

### Problem Description

**Node folder deletion fails due to file being accessed**
- **Problem**: When deleting a node, the folder may be occupied by unknown programs (File Explorer, antivirus, Python processes, etc.), causing deletion to fail
- **Impact**: Users cannot delete nodes normally, affecting user experience

### Fix Solution

**Three-layer Force Delete Mechanism**

1. **Layer 1: Try Renaming**
   - Rename folder to temporary name to bypass certain occupation scenarios

2. **Layer 2: Windows rmdir Command**
   - Use `rmdir /s /q` command to force delete
   - Windows-specific, can handle file occupation scenarios

3. **Layer 3: Scan and Terminate Occupying Processes**
   - Use psutil to scan all processes
   - Check if process working directory and open files contain node path
   - Force terminate these processes then retry deletion

### Technical Implementation

```python
def _force_stop_node_processes(self, node_path):
    """Force stop processes that may occupy node folder"""
    import psutil
    
    for proc in psutil.process_iter(['pid', 'name', 'open_files', 'cwd']):
        try:
            # Check working directory
            cwd = proc.cwd()
            if node_path_lower in cwd.lower():
                proc.kill()
            
            # Check open files
            for f in proc.open_files():
                if node_path_lower in f.path.lower():
                    proc.kill()
                    break
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass

def _force_delete_directory(self, node_path):
    """Force delete directory"""
    import shutil
    import time
    
    # Method 1: Rename and delete
    try:
        os.rename(node_path, temp_name)
        node_path = temp_name
    except OSError:
        pass
    
    # Method 2: shutil.rmtree
    try:
        shutil.rmtree(node_path)
        return True, "Success"
    except:
        pass
    
    # Method 3: Windows rmdir
    if os.name == 'nt':
        subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', node_path])
    
    # Method 4: Terminate processes and retry
    self._force_stop_node_processes(node_path)
    time.sleep(0.5)
    shutil.rmtree(node_path)
```

### Modified Files

- `ui/panels/node_list_panel.py` - Added force delete functions
- `ui/panels/node_list_dock.py` - Added force delete functions

### Acceptance Criteria

✅ Normal node deletion functionality unaffected
✅ Auto-trigger force delete mechanism when files are occupied
✅ Log terminated processes after successful force deletion
✅ Batch node deletion also uses force delete mechanism

---

## 🔧 Async Node Deletion, Non-blocking GUI (2026-06-05)

### Problem Description

**GUI unresponsive when deleting nodes**
- **Problem**: When deleting nodes, the deletion operation is synchronous and blocking, causing the entire GUI to become unresponsive
- **Impact**: When batch deleting multiple nodes, the GUI remains unresponsive for a long time, resulting in poor user experience

### Fix Solution

**Async Delete Mechanism**

1. **Single delete async**
   - Use `QTimer.singleShot` to put delete operation in event queue
   - GUI can continue to respond to user operations
   - Update UI through callback after deletion completes

2. **Batch delete one by one**
   - One confirmation, then delete asynchronously one by one
   - 100ms interval between each node deletion
   - Display summary results after all deletions complete

### Technical Implementation

```python
def delete_node(self, node_name):
    """Delete node (async, non-blocking GUI)"""
    # Show confirmation dialog
    reply = themed_message(...)
    if not reply:
        return
    
    # Use QTimer to execute deletion async
    QTimer.singleShot(10, lambda: self._delete_node_async(node_name, 
        lambda ok, err: self._on_delete_node_complete(node_name, ok, err)))

def batch_delete_nodes(self):
    """Batch delete (async, one by one)"""
    # One confirmation
    reply = themed_message(...)
    if not reply:
        return
    
    # Async delete one by one
    def delete_next(index):
        if index >= len(selected_nodes):
            # Display summary
            return
        self._delete_node_async(node_name, lambda ok, err: delete_next(index + 1))
    
    delete_next(0)
```

### Modified Files

- `ui/panels/node_list_panel.py` - Added async delete methods
- `ui/panels/node_list_dock.py` - Added async delete methods

### Acceptance Criteria

✅ GUI can respond normally when deleting nodes
✅ Batch delete requires only one confirmation
✅ Display correct results after deletion completes
✅ Mounted nodes are skipped during batch delete

---

## 🔧 Node Config Dialog Stays Open After Start (2026-06-05)

### Fixed Issue

**Node config dialog closes automatically after starting node**
- **Problem**: After clicking "Start Node" button, the config dialog closes automatically, requiring user to reopen it for subsequent operations
- **Cause**: Missing status persistence and update mechanism
- **Fix**: Added status display label, subscribed to status change signal, ensured dialog stays open

### Feature Improvements

**Real-time Status Display**
- Added status display label in node info card
- Subscribed to `polling_manager.node_status_changed` signal
- Real-time status update (running/idle/stopped)

**Dialog Stays Open**
- Dialog stays open after starting node, updates status display
- Dialog stays open after stopping node, updates status display
- User can continue operating in the dialog

### Modified Files

- `ui/dialogs/node_config_dialog.py` - Added status display and signal subscription

### Technical Implementation

```python
# Subscribe to status change signal
polling_manager.node_status_changed.connect(self._on_node_status_changed)

# Status display update
def _update_status_display(self):
    status = node_data.get('status', 'unknown')
    if status == 'running':
        self._status_label.setText("状态: ● 运行中")
        self._status_label.setStyleSheet("color: #FF4444;")
    elif status == 'idle':
        self._status_label.setText("状态: ● 空闲")
        self._status_label.setStyleSheet("color: #44FF44;")
    else:
        self._status_label.setText("状态: ○ 已停止")
        self._status_label.setStyleSheet("color: gray;")

# Update status after starting node (dialog stays open)
def start_node(self):
    self.parent_window.start_selected_node_by_name(self.node_name)
    self._update_status_display()  # Update status, don't close dialog
```

### Acceptance Criteria

✅ After clicking "Start Node", config dialog stays open
✅ Dialog shows node status update (status indicator changes)
✅ User can continue operating in the dialog (stop node, view logs, etc.)
✅ User can manually close dialog by clicking close button
✅ When start fails, dialog stays open and shows error message

---

## 🎨 Drawing Toolbar On-Demand Display (2026-06-05)

### Feature Improvement

**Drawing Toolbar On-Demand Display (Enhanced)**
- **Problem**: Drawing toolbar was automatically displayed and fixed on the left side when canvas starts, occupying 36px width of canvas space
- **Fix**: Changed to on-demand display mode, hidden by default, user can toggle display via shortcut key or menu

**New Features**:
- ✅ **Persistence**: Toolbar visibility saved to `canvas_layout.json`, restored after restart
- ✅ **Right-click menu toggle**: Added "Show/Hide Drawing Toolbar" option in canvas context menu

### Technical Implementation

**New Methods** (`draw_layer.py`):
```python
def show_toolbar(self):
    """Show drawing toolbar"""

def hide_toolbar(self):
    """Hide drawing toolbar"""

def toggle_toolbar(self):
    """Toggle drawing toolbar visibility"""
```

**Persistence** (`canvas_layout.py`):
- `save_layout()`: Saves `toolbar_visible` to `canvas_layout.json`
- `load_layout()`: Restores toolbar visibility when loading

**Shortcut Key**:
- `D` key: Toggle drawing toolbar display/hide

**Right-click Menu**:
- "Show Drawing Toolbar"
- "Hide Drawing Toolbar"

**Modified Files**:
- `ui/canvas/draw_layer.py` - Added toolbar toggle methods
- `ui/canvas/canvas_layout.py` - Added toolbar state persistence
- `ui/canvas/canvas_menus.py` - Added right-click menu option
- `ui/canvas/canvas_view.py` - Added toggle method
- `ui/core/strings_cn.json` - Added Chinese translations
- `ui/core/strings_en.json` - Added English translations

### Acceptance Criteria

✅ Canvas starts with drawing toolbar hidden by default
✅ Press `D` key to toggle toolbar display/hide
✅ Hidden toolbar doesn't affect canvas node operations
✅ Hidden toolbar won't be accidentally shown when window resizes
✅ Toolbar visibility persists to `canvas_layout.json`
✅ Right-click menu has "Show/Hide Drawing Toolbar" option
✅ Toolbar state restored after reopening project

---

## 🔨 Process Tree Termination Mechanism (2026-06-05)

### Feature Improvement

**Thorough Process Tree Termination**
- **Problem**: Previous stop node function only terminated Python processes, couldn't terminate child processes created by other languages
- **Fix**: Implemented process tree tracking mechanism, recursively queries and terminates all child processes (supports any language)

### Technical Implementation

**Process Tree Query** (`_get_process_tree`)
- Windows: Uses WMI to query Win32_Process, recursively finds via ParentProcessId
- Linux/Mac: Uses pstree or ps command to query process tree
- Returns all process PIDs, sorted depth-first (child processes first)

**Process Tree Termination** (`_kill_process_tree`)
- First queries process tree to get all PIDs
- Terminates processes in order (child processes first, root process last)
- Ensures all child processes are terminated

**Stop Node Flow**
```
1. Read PID file to get main process PID
2. Call _kill_process_tree() to terminate process tree
3. Fallback: Process scan to clean residual processes
4. Delete PID file, update status
```

### Modified Files

- `ui/core/node_process.py` - Added process tree query and termination functions
- `tests/test_process_tree.py` - Test script

### Test Method

```bash
# Automatic test mode
python tests/test_process_tree.py

# Interactive test mode
python tests/test_process_tree.py --interactive
```

### Acceptance Criteria

✅ When stopping node, main process and all child processes are terminated
✅ Supports child processes created by any language (Python, Node.js, Java, etc.)
✅ Cross-platform support (Windows, Linux, macOS)
✅ Fallback mechanism ensures orphan processes are cleaned

---

## 🐍 JSON Launch Virtual Environment Support (2026-06-05)

### Fixed Issue

**JSON launch cannot activate virtual environment**
- **Problem**: When launching Python nodes via JSON configuration, the virtual environment cannot be properly activated, causing node startup to fail
- **Cause**: `python_create_node.py` generated `start.json` without virtual environment path configuration
- **Fix**: Added `python_exe` field to `start.json`, launcher prioritizes this configuration

### Feature Improvements

**Virtual Environment Path Configuration**
- Modified `python_create_node.py` to create virtual environment before generating `start.json`
- Added `python_exe` field to `start.json`, recording the absolute path of the virtual environment Python interpreter

**Launcher Configuration Reading**
- Modified `_python_exe_for_node()` function to support reading configuration from `start_config` parameter
- Prioritizes path configured in `start.json`, falls back to default path if not configured

**Virtual Environment Validation**
- Added `_validate_venv()` function to validate Python interpreter validity
- Checks file existence, execution permissions, version compatibility
- Validates before launch, provides clear error messages on failure

### Modified Files

- `tools/python_create_node.py` - Add python_exe field to start.json
- `ui/core/node_process.py` - Support reading venv configuration from start.json, add validation mechanism

### Technical Implementation

```python
# python_create_node.py - Add python_exe to start.json
start_content = {
    "nodes": [
        {
            "name": f"node_python_{node_name}",
            "path": full_node_dir,
            "python_exe": python_exe_path,  # New field
            "config": {...}
        }
    ]
}

# node_process.py - Prioritize reading from start.json
def _python_exe_for_node(node_path, start_config=None, node_name=None):
    # Prioritize reading python_exe from start_config
    if start_config and 'nodes' in start_config:
        for n in start_config['nodes']:
            if n.get('name') == node_name or n.get('path') == node_path:
                if 'python_exe' in n and n['python_exe']:
                    return os.path.normpath(n['python_exe'])
    # Fallback to default path
    return os.path.join(node_path, "venv", "Scripts" if os.name == 'nt' else "bin", "python.exe")
```

### Acceptance Criteria

✅ `start.json` generated by `python_create_node.py` contains `python_exe` field  
✅ Python nodes launched via JSON configuration can correctly activate virtual environment  
✅ Clear error messages on startup failure (e.g., missing venv, incompatible Python version)  
✅ Cross-platform support (Windows 10/11, Linux, macOS)

---

## 🔧 Node Status Display & Process Detection Fix (2026-06-05)

### Fixed Issues

**1. Node list status requires manual refresh to display**
- **Problem**: Status indicator in node list does not update properly when node status changes
- **Cause**: Status check only evaluates `status == 'running'`, ignoring 'idle' status (running but no active task)
- **Fix**: Change status check logic to `status in ('running', 'idle')`
- **Modified Files**:
  - `ui/panels/node_list_dock.py`
  - `ui/panels/node_list_panel.py`

**2. Circular node text layout becomes square style after refresh**
- **Problem**: After refreshing nodes, text position on circular nodes changes to square node layout
- **Cause**: `update_display` method hardcodes text positions (15px and h-18px), overriding positions set by circular node style
- **Fix**: Refactor `update_display` method, remove hardcoded text position settings, call `self._style.apply(self)` to reapply style when node name or language changes
- **Modified File**: `ui/canvas/items/node_item.py`

**3. Node unexpectedly exits after GUI restart**
- **Problem**: When exiting GUI with "don't stop nodes" option, nodes continue running in background. After restarting GUI, nodes show "running" first, then exit unexpectedly after a few seconds
- **Cause**: Logic flaw in `check_running_processes()` function. When process scan (PowerShell command) fails, even if recorded PID is still alive, node is incorrectly marked as `stopped` and PID file is deleted
- **Fix**: When process scan fails but PID is still alive, preserve node status instead of forcing it to `stopped`
- **Modified File**: `ui/core/node_process.py`

### Technical Implementation Details

**Node List Status Fix**:
```python
# Before
if status == 'running':
    item.setText(0, f"● {node_name}")
    item.setForeground(0, QColor("green"))

# After
if status in ('running', 'idle'):
    item.setText(0, f"● {node_name}")
    item.setForeground(0, QColor("green"))
```

**Circular Node Text Position Fix**:
```python
# Before
def update_display(self, node_name=None, language=None, status=None):
    w = self.rect().width()
    h = self.rect().height()
    if node_name:
        self.name_text.setPos((w - name_rect.width()) / 2, 15)  # Hardcoded position
    if language:
        self.lang_text.setPos((w - lang_rect.width()) / 2, h - 18)  # Hardcoded position

# After
def update_display(self, node_name=None, language=None, status=None):
    # Only update content, position is determined by style
    if node_name:
        self.name_text.setPlainText(node_name)
    if language:
        self.lang_text.setPlainText(language)
    # Reapply style to update text position
    if node_name or language:
        self._style.apply(self)
```

**Process Detection Logic Fix**:
```python
# Before
if pid is not None and _is_pid_alive(pid):
    pass  # Continue to logic below, mark as stopped

# After
if pid is not None and _is_pid_alive(pid):
    # Process is still running, but process scan didn't find it (may be permission or environment issue)
    # Preserve current status, don't force mark as stopped
    logger.warning("Node %s PID=%d is alive, but process scan found no matching process", name, pid)
    continue  # ← Key fix: preserve node status
```

### Acceptance Criteria

✅ Node status indicator turns green (●) after startup, no manual refresh needed  
✅ Node status indicator turns gray (○) after stopping  
✅ Circular nodes maintain correct text layout and style after refresh  
✅ When exiting GUI with "don't stop nodes", nodes continue running in background  
✅ After restarting GUI, background nodes are correctly detected  
✅ Node status remains "running" or "idle", not incorrectly marked as "stopped"  
✅ PID file is not incorrectly deleted  

---

## 🌐 Global Status Synchronization Refactor (2026-05-23)

### Feature Improvements

**Global Status Subscription Mechanism**
- All panels subscribe to `polling_manager.node_status_changed` signal
- Achieve true global status synchronization, ensuring all panels display consistently
- When node status changes, all panels automatically synchronize updates

**Modified Panels**
| Panel | File Path |
|-------|-----------|
| Node List Panel (Floating) | `ui/panels/node_list_panel.py` |
| Node List Dock Panel | `ui/panels/node_list_dock.py` |
| Resource Monitor Panel (Floating) | `ui/panels/resource_monitor.py` |
| Resource Monitor Dock Panel | `ui/panels/resource_monitor_dock.py` |
| Node Monitor Panel (Floating) | `ui/panels/node_monitor.py` |
| Node Monitor Dock Panel | `ui/panels/node_monitor_dock.py` |

### Technical Implementation

- **Signal Subscription Mechanism**: All panels subscribe to `polling_manager.node_status_changed` signal
- **Status Update Callback**: Each panel implements `_on_node_status_changed` callback method
- **Unified Data Source**: All panels get node status from PollingManager
- **Real-time Synchronization**: All panels update display immediately when node status changes

### Fixed Issues

1. **Node Status Display Inconsistency**: All panels now display the same status
2. **Status Update Delay**: Panels respond more promptly
3. **High Resource Usage**: Unified detection mechanism reduces duplicate work

### Code Changes

**Node List Panel**
- Subscribe to global status signal
- Implement status update callback
- Remove independent detection logic

**Resource Monitor Panel**
- Subscribe to global status signal
- Implement status update callback
- Use unified data source

**Node Monitor Panel**
- Subscribe to global status signal
- Implement status update callback
- Display real-time status information

---

## 🖼️ Canvas Layout Loading Enhancement (2026-05-23)

### Feature Improvements

**Auto-add Missing Nodes**
- `load_layout` method now automatically adds missing nodes to canvas
- Get node information from project data, create nodes and apply layout configurations
- Ensure all nodes can be displayed correctly when switching tabs

**Fixed Issues**
- Node position information was not loaded correctly when switching tabs
- Nodes in canvas layout files were not displayed on canvas
- Color configuration and style information loading incomplete

### Technical Implementation

- **Node Existence Check**: Iterate through layout data, check if nodes are already on canvas
- **Auto-create Nodes**: Automatically create and add when node doesn't exist but exists in project data
- **Configuration Application**: Apply position, style, color and other configuration information
- **Exception Handling**: Improve exception handling mechanism to avoid errors interrupting loading

### Code Changes

**Canvas Layout Module** (`ui/canvas/canvas_layout.py`)
- Modify `load_layout` method, add automatic node addition logic
- Improve exception handling, fix syntax errors
- Add logging for debugging and tracking

**Fix Details**
- Fixed `try-except` syntax error
- Added automatic creation feature for missing nodes
- Improved color and style configuration application logic
- Enhanced error handling and logging

---

## 🛠️ Panel State Persistence & Resource Monitor Fixes (2026-05-23)

### Fixed Issues

**1. Panel Auto-start Conflict**
- Fixed issue where floating panel auto-start causes Dock panel to disappear
- Fixed issue where floating panel fails to auto-start when Dock panel is auto-started
- Modified file: `ui/main_window.py`

**2. Null Pointer Error Fix**
- Fixed `AttributeError: 'NoneType' object has no attribute 'update_node_status'`
- Added null checks before accessing panels
- Modified file: `ui/main_window.py`

**3. Resource Monitor Dock Panel Node Data Loading**
- Fixed issue where node resource usage was not displayed
- Added `parent_window` reference for automatic node data retrieval
- Modified file: `ui/panels/resource_monitor_dock.py`

**4. Dock Panel Close Handling**
- Fixed issue where accessing deleted objects after closing Dock panel
- Connected `panel_closed` signal to clear references on close
- Modified file: `ui/main_window.py`

**5. Node Monitor Panel Status Sync**
- Fixed PID file path issue (prioritize `.pid` file)
- Sync status display during resource monitoring
- Modified file: `ui/panels/node_monitor_dock.py`

### Feature Improvements

**Panel State Persistence**
- Support independent visibility state saving for Dock and floating panels
- Support panel position persistence
- Auto-restore panel state and position after restart

**Resource Monitor Layout Optimization**
- CPU, RAM, Disk displayed horizontally and centered
- Node resource list displayed vertically
- Consistent layout between Dock and floating versions

### Modified Files
- `ui/main_window.py` - Panel state restoration, null checks, Dock close handling
- `ui/panels/resource_monitor_dock.py` - Node data loading, status sync
- `ui/panels/node_monitor_dock.py` - PID file path fix, status sync
- `ui/core/app_config.py` - Singleton pattern
- `ui/core/dock_manager.py` - Duplicate creation prevention

---

## 🖼️ Sidebar Toolbar Size Increase & Icon Fixes (2026-05-23)

### Dimension Adjustments

**Modified file**: `ui/canvas/draw_toolbar.py`

| Item | Before | After |
|------|--------|-------|
| Toolbar width | 40px | **56px** |
| Button height | 34px | **44px** |
| Icon font size | 14px | **18px** |

### Icon Fixes

Fixed several invalid icons that displayed as exclamation mark `!`:

| Function | Old Icon | New Icon | Description |
|----------|----------|----------|-------------|
| Rectangle tool | `layout-panel` | ✅ `layout-panel` | Panel icon |
| Round rectangle | `circle` | ✅ `circle` | Circle icon |
| Polygon | `triangle-up` | ✅ `triangle-up` | Triangle icon |
| Arrow tool | `arrow-right` | ✅ `arrow-right` | Arrow icon |
| Text tool | `file-text` | ✅ `file-text` | Text file icon |
| Stroke color | `pencil` | ✅ `pencil` | Pencil icon |
| Fill color | `paintcan` | ✅ `paintcan` | Paint bucket icon |
| Lock | `lock` | ✅ `lock` | Lock icon |
| Show/Hide | `eye` | ✅ `eye` | Eye icon |
| Undo | `arrow-left` → **`chevron-left`** | ✅ `chevron-left` | Left chevron |
| Redo | `arrow-right` → **`chevron-right`** | ✅ `chevron-right` | Right chevron |
| Delete selected | `trash` | ✅ `trash` | Trash icon |
| Clear all | `clear-all` → **`close`** | ✅ `close` | Close icon |

---

## 🎨 VS Code Codicon Icon System Integration (2026-05-23)

### Icon Resource Management

**New icon source directory**: `codicon-source/` (formerly `vscode-codicons-main`)

- Full VS Code Codicon icon library (MIT License)
- Font file: `codicon.ttf`
- Icon definitions: `codiconsLibrary.ts`

### Icon Manager

**Updated**: `ui/icons/codicon.py`

- Icon mappings expanded from 527 to **597 icons**
- New icon categories: AI, Debug, Git, Terminal, Layout
- Convenient `get_icon()` and `get_icon_font()` interfaces

### New Icon Categories

| Category | New Icons |
|----------|-----------|
| AI Assistant | `copilot`, `thinking`, `sparkle`, `openai`, `claude` |
| Debug | `debug-all`, `debug-step-in`, `debug-step-out`, `debug-coverage` |
| Git | `git-compare`, `repo-clone`, `repo-pull`, `repo-push` |
| Terminal | `terminal-bash`, `terminal-cmd`, `terminal-powershell` |
| Layout | `layout`, `layout-panel`, `layout-sidebar-left/right` |
| Run | `run-all`, `run-coverage`, `run-with-deps` |

### UI Icon Replacement

**Modified files**:
- `ui/menu/menu_manager.py` - Menu icons
- `ui/canvas/draw_toolbar.py` - Drawing toolbar icons

### Usage Example

```python
from ui.icons import get_icon, get_icon_font

icon_char = get_icon('copilot')    # AI assistant icon
icon_char = get_icon('run-all')    # Run icon
```

---

## 🔄 Unified Polling Manager + Global State Monitoring Refactor (2026-05-23)

### Unified Polling Manager

**New**: `ui/core/polling_manager.py` (Singleton Pattern)

Centralized management for all periodic polling tasks:

| Polling Task | Interval | Description |
|--------------|----------|-------------|
| Node Health Check | 3s | Detect node process status |
| Global Log Monitoring | 2s | Detect global log file changes |
| Global Config Monitoring | 5s | Detect global config file changes |
| Node Log Monitoring | 2s | Detect individual node log changes |
| Node Config Monitoring | 5s | Detect individual node config changes |
| Node Output JSON | 1s | Detect output.json changes |
| Application State | 1s | Monitor overall application status |

**Core Features**:
- Singleton pattern for global unique instance
- Support task registration/cancellation/pause/resume
- Precise timing based on QTimer
- PyQt signal mechanism for panel notifications

### Module Consolidation

**Deleted Redundant Files**:
- `ui/core/system_monitor.py` → merged into polling_manager
- `ui/core/global_detector.py` → merged into polling_manager

### Panel Adaptations

| Panel | Changes |
|-------|---------|
| `ui/main_window.py` | Replaced SystemMonitor/GlobalDetector with polling_manager |
| `ui/panels/node_monitor.py` | Subscribed to polling_manager log signals |
| `ui/panels/node_expand_panel.py` | Subscribed to config/output signals |
| `ui/dialogs/node_config_dialog.py` | Subscribed to config change signals |

### Affected Files

`polling_manager.py`(new), `main_window.py`, `node_monitor.py`, `node_expand_panel.py`, `node_config_dialog.py`, `system_monitor.py`(deleted), `global_detector.py`(deleted)

---

## 🔄 Standalone Launcher + 3-State Indicators + Ctrl+D Delete + Color Fixes (2026-05-23)

### Standalone tkinter Launcher

Replaced embedded PyQt6 splash with `launcher.py` (251 lines):
- Pure tkinter, zero dependencies on venv, packable as standalone EXE
- Splash appears instantly → background spawns venv pythonw → real-time progress file polling
- Smooth progress bar animation, precisely synced with main program loading
- Auto-close 0.2s after 100%. `.vbs` zero-window launcher
- Missing venv: shows install guide on splash then exits

### 3-State Status Indicator

| Color | State | Detection |
|-------|-------|-----------|
| Gray `#888` | Stopped | listener PID absent |
| Green `#44FF44` | Idle | listener alive, no main child |
| Red `#FF4444` | Running | listener + main child active |

Uses `psutil` process tree detection, zero node code changes. Health check polls every 3s, UI fully adapted for 3-state model.

### Ctrl+D Unified Delete Shortcut

`Ctrl+D` context-aware:
- Node list focused → batch delete nodes/groups
- Canvas box-selected nodes → remove from canvas
- Canvas selected graphics → delete

Right-click delete removed (conflicted with context menu).

### Color Settings Fixes

- **Canvas background**: `drawBackground` directly `painter.fillRect` using `canvas_bg_color`; `resetCachedContent` + `repaint` for instant update
- **Color dialog**: BNOS dark theme Frameless window, draggable, visible border
- **Key name alignment**: `choose_color`'s `canvas_bg` now matches `collect_settings`'s `temp_canvas_bg_color`

### Shortcut Manager

New `ui/core/shortcut_manager.py`: 11 shortcuts centrally defined + persisted to `app_config.json` + settings panel visual editor + double-click capture.

### Language Switching Fixed

Fixed Python `from import LANG` value-copy bug (added `get_lang()`) + restart via `exit(42)` exit code + `AppConfig` supports new key persistence.

### Affected Files

`launcher.py`(new), `node_process.py`, `node_style.py`, `canvas_colors.py`, `canvas_view.py`, `shortcut_manager.py`(new), `color_settings_dialog.py`, `settings_dialog.py`, `menu_manager.py`, `main_window.py`, `i18n.py`, `app_config.py`, `start_bnos_console.vbs`(new), startup scripts

---

## 🚀 Splash Screen + Brand Rename BnosConsole + README Update (2026-05-23)

### Splash Screen

New `ui/core/splash_screen.py` (114 lines):
- **ASCII Art BNOS**: 6-line █ block characters, Consolas 13pt bold, monochrome
- **BNOS CONSOLE** subtitle + project tagline (i18n)
- **Bottom-left live log**: QTextEdit 80px, scrolled startup steps
- **Bottom progress bar**: 0→100%, gray chunk
- **Delayed close**: 2 seconds after main window appears

### Brand Rename: BnosGui → BnosConsole

| Old | New |
|-----|-----|
| `bnos_gui.py` | `bnos_console.py` |
| `start_bnos_gui.bat` | `start_bnos_console.bat` |
| `start_bnos_gui.sh` | `start_bnos_console.sh` |
| `requirements_gui.txt` | `requirements.txt` |
| `"BnosGui"` window title | `"BnosConsole"` |
| `logs/bnos_gui.log` | `logs/bnos_console.log` |
| `_k_app_name` | `"BNOS Console"` (cn/en unified) |

25+ files affected: `main_window.py`, `dark_title_bar.py`, `logger.py`, `build_bnos.spec`, README, UPDATE, tests, etc.

### Affected Files

`splash_screen.py`(new), `bnos_console.py`(rename + splash delay), `strings_cn/en.json`, `main_window.py`, `dark_title_bar.py`, `logger.py`, `build_bnos.spec`, startup scripts, README, UPDATE, tests

---

## 🔧 ComfyUI-Style Line Refactor + Manual Fold (2026-05-22)

### Bezier → Orthogonal Lines + Manual Folding 📏

**Complete rewrite**: `ui/canvas/items/edge_item.py`

- **Straight lines**: Bezier curves replaced with straight line segments
- **Fold handles**: Each segment's midpoint shows a draggable blue handle, always visible
- **Fold waypoints**: Existing waypoints are orange dots, directly draggable to adjust
- **Relative coordinates**: Waypoints stored as `(t, off_x, off_y)` relative to endpoints, auto-follow when nodes move
- **Selected color (not thicker)**: Selected → bright blue `#2aaaff`, hovered → 140% brighter, same width
- **Delete**: Double-click waypoint to remove it

**Interaction**:
| Element | Color | Behavior |
|---------|-------|----------|
| Segment midpoint handle | Blue | Short press = select line, Long press 250ms + drag = new fold |
| Existing waypoint | Orange | Direct drag to adjust, double-click to delete |

**Serialization**: New `waypoints` field in `canvas_layout.json` edges, backward compatible.

### Temp Edge Sync ✨

`canvas_view.py` drag-to-connect now renders straight dashed temp line matching final style.

---

## 🆕 Node Registry + External Node Mount (2026-05-22)

### Node Registry Component 📋

**New**: `ui/core/node_registry.py`

- **Persistent file**: `<project>/node_registry.json`
- **Scan-first principle**: `refresh_nodes()` scans nodes/ dir as primary source, registry as auxiliary
- **Auto-sync**: Scanned nodes → active, unscanned local nodes → missing
- **Mount support**: `mount_root` field for external sources

### External Node Mounting 🔗

**New feature**: Edit menu → "Mount External Node" (Ctrl+Shift+O)

- **Select external folder** → read `config.json` → mount to project (no file copy)
- **Auto-create locked group**: Named after mount root absolute path, shows 🔒
- **Lock rules**:
  - ❌ No move out of mount group
  - ❌ No move into mount group
  - ❌ Mount group cannot be renamed/deleted
  - ✅ Same mount group nodes can freely create sub-groups
- **Restart recovery**: `refresh_nodes()` auto-restores mounted nodes from registry
- **Unmount**: Right-click node → "Unmount External Node" (keeps source files)

### NodeGroupManager Locked Groups

**Modified**: `ui/panels/node_group_manager.py`

- New `_locked_groups` set + `lock_group()`/`unlock_group()`/`is_group_locked()`
- Persisted to `node_groups.json` `locked_groups` field
- Empty locked groups are not auto-cleaned

---

## 🔗 Connection Config Validation + Edge Interaction Fixes (2026-05-21)

### Config.json Fallback Validation 🔍

**New component**: `ui/core/connection_inferrer.py`

`canvas_layout.json` loading now silently cross-validates against each node's `config.json`:

- **Inference**: Parses `listen_upper_file` from every node's `config.json`, extracting upstream node names from paths
- **Path Compatibility**: Supports absolute (`F:/project/nodes/A/output.json`), relative (`../A/output.json`), and Windows paths
- **Auto-Repair**: Edges in config but missing on canvas → auto-added (log: `[Config兜底] 补充缺失连线`)
- **Suspicious Edges**: Edges on canvas but missing from config → logged as warning, NOT auto-removed (safety-first)
- **Fully Silent**: Validation runs transparently; all logs tagged with `[Config兜底]`

**Affected files**: `ui/core/connection_inferrer.py`(new), `ui/canvas/canvas_layout.py`(modified)

### Edge Selection & Deletion Fixes 🔧

**Modified files**: `ui/canvas/items/edge_item.py`, `ui/canvas/canvas_menus.py`

- **Selection enabled**: `EdgeItem` sets `ItemIsSelectable` flag, left-click selects with +4px highlight
- **Wider hit area**: `shape()` returns 8px stroke path for easier clicking on Bezier curves
- **Arrow as child**: Arrow reparented as EdgeItem child `QGraphicsPolygonItem(self)`, mouse events disabled, clicks pass through
- **Right-click menu**: Canvas `contextMenuEvent` now detects `EdgeItem` → [Delete Edge] [Change Edge Color] [Clear Selection]
- **Dead code removed**: Eliminated broken `scene.items()` search for `NodeCanvas` (it's a `QGraphicsView`, not a scene item)
- **Emoji cleanup**: Edge right-click menu emoji removed

---

## 🔧 GUI Architecture Refactor & Feature Enhancements (2026-05-21)

### Code Decoupling 📦

**10 new modules** created, eliminating code duplication:

| Module | Responsibility | Source |
|--------|---------------|--------|
| `ui/core/app_config.py` | Global config persistence | Extracted from main_window |
| `ui/core/theme.py` | Dark QSS stylesheet | Extracted from main_window |
| `ui/core/node_process.py` | Process start/stop/PID/health | New, eliminates 4 duplicates |
| `ui/canvas/canvas_colors.py` | Canvas color management Mixin | Extracted from canvas_view |
| `ui/canvas/canvas_layout.py` | Canvas layout persistence Mixin | Extracted from canvas_view |
| `ui/canvas/canvas_menus.py` | Canvas right-click menu Mixin | Extracted from canvas_view |

- `main_window.py`: 1491 → **935 lines** (-556)
- `canvas_view.py`: 1911 → **~1200 lines** (-680)
- Eliminated Toast 170-line duplicate, process management 180-line duplicate

### Process Health Detection 🩺

- **PID File Persistence**: `start_node_process` writes `.pid`, `stop_node_process` deletes it
- **Cross-Session Recovery**: GUI restart auto-scans `.pid` files, detects running processes, restores ● status
- **Periodic Health Check**: Polls running processes every 3s, crashed nodes auto-update to ○ stopped
- Fixed `subprocess.PIPE` buffer deadlock, switched to `DEVNULL`

### Selection System Unification 🖱️

- Removed `selected_node` standalone property
- Single-click / box-select / Ctrl+click all use unified `box_selected_nodes`
- Box-selected nodes auto-call `setSelected(True)`, support **group dragging**
- Fixed lambda closure late-binding causing right-click menu color failure

### Node Anti-Overlap 🧱

- Auto-detect and push away adjacent nodes during drag
- `setPos()` during layout loading also triggers anti-overlap

### Startup Script Fixes 🔨

`tools/rust_create_node.py` and `tools/python_create_node.py`:
- Support `--no-pause` flag (silent mode for GUI invocation)
- Use `start /b` / `nohup &` for background launch, no longer blocking
- Auto-write `.pid` file after launch
- Fixed Rust dual-file detection and auto-build logic

### Development Guidelines 📋

Added `开发维护准则.md` (10 coding standards + priority fix list) and `tools/Node_Generator_Guidelines_EN.md` (new language node standard template).

---

## 🎯 Node Style System (2026-05-21)

### Core Architecture

**New file**: `ui/canvas/items/node_style.py`

Complete node style abstraction system, cleanly separating appearance, layout, and interaction logic for rectangular and circular nodes:

| Class | Description |
|-------|-------------|
| `NodeStyle` | Abstract base class; defines `style_key`, `selected_border_width`, `selected_color` |
| `RectNodeStyle` | Rectangular node (default); full anchors, expand button, indicators, IN/OUT labels |
| `DarkRectNodeStyle` | Dark rect variant (extends `RectNodeStyle`), the current default style |
| `DotNodeStyle` | Circular node; three-layer z-architecture, hides all rect-specific components |

### Dot Node Three-Layer Z-Architecture

```
z=6  Status indicator (top layer)
z=5  Input anchor (middle layer)
z=4  Output anchor (bottom layer)
```

- Dot nodes hide: anchor labels (IN/OUT), status indicator, expand button `>>`
- Node name displayed left-aligned below the circle, touching its bottom edge
- When selected, a **floating selection ring** (`QGraphicsEllipseItem`, z=10) appears above the node

### Style Switching & Persistence

- Canvas right-click menu "Node Style" submenu with "Rect" and "Dot" options
- All menu actions use `functools.partial` to avoid lambda closure late-binding bugs
- Style switch triggers `_save_timer.start(500)` for auto-save
- `canvas_layout.json` stores a `"style"` field per node (`"rect"` or `"dot"`)
- Layout load restores styles via `STYLES.get(style_key)()`

### Bug Fixes

- Fixed lambda closure late-binding causing wrong menu actions
- Fixed anchor position stacking (constructor offset + setPos offset)
- Fixed `setRect(w, h)` param error → `setRect(0, 0, w, h)`
- Fixed `setBrush(Qt.BrushStyle.NoBrush)` type error → `setBrush(QBrush())`
- Fixed `QLabel(self.node_name)` bool type error → `QLabel(str(self.node_name))`
- Fixed dot node rect too small causing grid rendering artifacts → expanded to 80×80 with `prepareGeometryChange()`

**Affected files**: `ui/canvas/items/node_style.py`(new), `ui/canvas/items/node_item.py`(modified), `ui/canvas/canvas_menus.py`(modified), `ui/canvas/canvas_layout.py`(modified)

---

## ⚡ Canvas Viewport Rendering Optimization (2026-05-21)

**Modified file**: `ui/canvas/canvas_view.py`

- Viewport update mode changed from `FullViewportUpdate` to `SmartViewportUpdate`: only repaints changed areas
- Added `CacheBackground`: grid background cached, no redraw during drag/zoom
- Added `DontSavePainterState` / `DontClipPainter` optimization flags to reduce Qt paint pipeline overhead
- Significant FPS and responsiveness improvement during pan, zoom, and node movement

---

## 🎨 VSCode-Style Dark Frameless Window (2026-05-21)

**New component**: `ui/core/dark_title_bar.py`

- Main window switched to frameless design with custom 40px dark title bar (`#1e1e1e`)
- Menu bar embedded in same row as title bar: `[BnosGui] [File] [Edit] [Tools] [Help] ←→ [─] [□] [✕]`
- Global dark QSS theme: menus, scrollbars, inputs, buttons, tables, dialogs all dark-styled
- Edge-drag resize support for frameless window (6px sensitive margin)
- Custom minimize/maximize/close buttons, close button turns red (`#e81123`) on hover
- Double-click title bar to toggle maximize/restore, drag title bar to move window

---

## 🆕 Four Major Plans Implemented (2026-05-21)

### **Plan 1: Node Expand Panel** 📤

**New component**: `ui/panels/node_expand_panel.py`

- `>>` expand button on canvas node top-right corner, opens floating panel centered on node
- Left: output.json editor (dark theme/editable/auto-refresh)
- Right: Start/Stop, Config, Delete three action buttons
- Right-click menu adds "Expand Node" entry
- Panel center aligns with node center coordinates

### **Plan 2: Node Monitor Panel** 📊

**New component**: `ui/panels/node_monitor.py`

- Global real-time log viewer, parent window + collapsible sub-panel architecture
- Syncs canvas nodes every 3s, auto-refreshes logs on mtime change every 2s
- Menu bar adds "Tools(&T)" → "Node Monitor" (Ctrl+Shift+M)
- Canvas right-click menu adds "Node Monitor"
- Window type matches NodeListPanel, follows main window

### **Plan 3: print → logging Migration** 📝

**New module**: `ui/core/logger.py`

- Console INFO + File DEBUG dual-channel output
- All 211 `print()` calls across 9 files migrated to `logger`
- Log file: `logs/bnos_gui.log` (excluded by .gitignore)

### **Plan 4: Floating Panel Base Class** 🪟

**New base class**: `ui/core/floating_panel.py`

- Unifies frameless, translucent, draggable, titled window behavior
- `NodeListPanel` → extends `FloatingPanel`
- `NodeConfigDialog` → extends `FloatingPanel` (removed QDialogButtonBox)
- `NodeMonitor` → extends `FloatingPanel`
- `NodeExpandPanel` → extends `FloatingPanel`
- Unified visual style: `rgba(30,30,30,220)` translucent dark container

---

## 🎨 UI Simplification & Optimization (2026-05-21)

### **Emoji Removal + Name Simplification** 🧹

- All Emoji patterns removed from UI buttons, menus, dialog titles
- Button names simplified to 2-4 characters (e.g., "Clear All Edges" → "Clear Edges")
- 6 files affected: canvas_view.py, property_panel.py, node_list_panel.py, main_window.py, menu_manager.py, bnos_gui.py

### **Button Colors Unified to Black/White/Gray** ⚫

- All colorful button backgrounds replaced with monochrome (`#333`/`#555`/`#666`)
- 14 locations in `property_panel.py`

### **Canvas Right-Click Menu Enhanced** 📋

- Canvas blank area right-click adds "New Node" submenu (7 languages)
- Canvas blank area right-click adds "Node Monitor"

### **Box Selection Logic Fixed** 🎯

- Clicking node sub-items (status indicator, text, expand button) no longer triggers box selection
- Uses `parentItem()` chain lookup instead of flat `isinstance` check

### **Bug Fixes** 🔧

- Fixed single-node right-click start/stop crash (missing `start_single_node`/`stop_single_node` methods)
- `.gitignore` adds `logs/` to exclude log directory

---

## Import Path Fixes & Code Quality Optimization (2026-05-21 Evening)

### Core Fixes Overview 🔧

This update includes comprehensive import path corrections and code quality improvements:

1. **Import Path Unification** - All module imports use correct subdirectory paths
2. **Toolbar→Menu Migration Complete** - MenuManager now handles all menus
3. **Node Creation Fix** - NodeCreatorManager path resolution fixed
4. **Code Quality** - Removed redundant imports, added missing imports

---

### 1. Import Path Fixes 📁

**Problem**: After `ui/` directory restructuring, multiple modules used incorrect flat import paths instead of subdirectory paths.

| File | Wrong Import | Correct Import |
|------|-------------|----------------|
| `main_window.py` | `from ui.property_panel import` | `from ui.panels.property_panel import` |
| `main_window.py` | `from ui.node_list_panel import` | `from ui.panels.node_list_panel import` |
| `main_window.py` | `from ui.node_creator_manager import` | `from ui.creators.node_creator_manager import` |
| `node_list_panel.py` | `from ui.node_group_manager import` | `from ui.panels.node_group_manager import` |

**Affected Files**:
- `ui/__init__.py` - Removed non-existent `NodeStyleDialog` import
- `ui/main_window.py` - 3 import path corrections
- `ui/panels/node_list_panel.py` - 2 import path corrections

---

### 2. Toolbar Removed, MenuManager Takes Over 📋

**Changes**:
- ✅ Removed `init_toolbar()` method (68 lines)
- ✅ Removed old `init_menu()` method
- ✅ `MenuManager.init_menu(self)` handles all menus
- ✅ Added `create_new_node_with_language(language)` method
- ✅ Completed `show_about()` method body

**Menu Structure**:
```
File(&F)    Edit(&E)         Help(&H)
├ New      ├ New Node >     └ About
├ Open     │ ├ Python
├ NodeList │ ├ Node.js
├ Colors   │ ├ Go
└ Exit     │ ├ Java
           │ ├ C++
           │ ├ Rust
           │ └ Shell
           ├ Refresh
           ├ Clear Edges
           ├ Start Node
           └ Stop Node
```

---

### 3. Node Creation Fix 🔧

**Problem**: Clicking "New Node" in menu couldn't invoke creation scripts in `tools/`.

**Root Cause**: In `node_creator_manager.py`, `base_dir` only went up 2 directory levels:
- Before: `os.path.dirname(os.path.dirname(__file__))` → `ui/` ❌
- After: `os.path.dirname(os.path.dirname(os.path.dirname(__file__)))` → project root ✅

**Fix**: Added one more `os.path.dirname()` to correctly point to project root.

---

### 4. Code Quality Improvements 🧹

| Improvement | Location | Description |
|-------------|----------|-------------|
| Added missing imports | `main_window.py` | `QThread`, `signal`, `QApplication` moved to top |
| Removed redundant import | `main_window.py` | Duplicate `NodeCreatorManager` in `__init__` |
| Removed inline imports | `main_window.py` | `QApplication` from `show_toast`, `update_position` |
| Removed inline imports | `main_window.py` | `signal` from `stop_selected_node`, `_force_stop_all_nodes` |
| Removed inline imports | `main_window.py` | Qt components from `_start_async_node_creation` |
| Lambda fix | `menu_manager.py` | `checked` parameter changed to default `None` |
| Windows process kill | `main_window.py` | Unified to use `taskkill /F /T /PID` instead of `terminate()` |

---

### 5. Windows Process Management Unified 🪟

All 3 process termination methods now use consistent, reliable approach:

```python
# Unified taskkill for force-terminating process trees
subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
               capture_output=True, timeout=10)
```

Affected methods: `stop_selected_node`, `stop_selected_node_by_name`, `_force_stop_all_nodes`

---

## Major Architecture Refactoring: UI Modularization & Menu Integration (2026-05-21)

### Core Improvements Overview 🎯

This update completed three major refactorings:

1. **Toolbar Integrated into Menu Bar** - Simplified interface, desktop-standard UX
2. **Toast Notification System Modularized** - Fully decoupled, cross-module reusable
3. **UI Directory Restructured** - Layered by function, clear responsibilities

---

### 1. Toolbar Integrated into Menu Bar 📋

**Design**: Pure menu bar design, removed standalone toolbar, all functions integrated into standard menus.

**Changes**:
- ✅ Removed top toolbar, freeing vertical space
- ✅ All functions integrated into "File", "Edit", "Help" menus
- ✅ High-frequency operations grouped in submenus (e.g., 7 languages under "New Node")
- ✅ Each menu item has clear shortcuts and visual identifiers
- ✅ Business logic unchanged, only access entry points changed

**Key Files**:
- `ui/menu/menu_manager.py` - Menu manager (new)
- `ui/main_window.py` - Delegates to MenuManager

---

### 2. Toast Notification System Modularized 🔔

**Design**: Extracted Toast from main window into independent module, fully decoupled.

**Core Features**:
- ✅ **Fully Decoupled** - Toast independent of main window, independently testable
- ✅ **Stack Management** - Auto handles multi-toast stacking
- ✅ **60fps Animation** - Smooth fade in/out
- ✅ **Four Types** - success, error, warning, info

**New Files**:
- `ui/core/toast/toast_notification.py` - Toast core class
- `ui/core/toast/toast_manager.py` - Toast manager (stack management)

---

### 3. UI Directory Restructured 📁

```
ui/
├── __init__.py
├── main_window.py
├── core/              # Core components
│   └── toast/
├── menu/              # Menu system
│   └── menu_manager.py
├── canvas/            # Canvas system
│   ├── canvas_view.py
│   └── items/
├── panels/            # Panel components
│   ├── node_list_panel.py
│   ├── property_panel.py
│   └── node_group_manager.py
├── creators/          # Creators
│   └── node_creator_manager.py
└── docs/              # Documentation
```

---

## Canvas Widget Modular Split (2026-05-20)

### Canvas Widget Refactored into Layered Architecture 🎨

Successfully refactored the monolithic `canvas_widget.py` (91.9KB) into a four-layer architecture.

**Before/After Metrics**:

| Metric | Before | After |
|--------|--------|-------|
| Single file size | 91.9KB | 74.5KB (core) + items |
| Module count | 1 | 5 core modules |
| Lines of code | ~2200 | ~1763 (core) + items |
| Responsibility clarity | Mixed | Layered ✅ |

**New Architecture**:
- **Layer 1 - Items**: Pure UI rendering (`anchor_item.py`, `node_item.py`, `edge_item.py`)
- **Layer 2 - Core**: Canvas management & business logic (`canvas_view.py`)
- **Layer 3 - Compat**: Facade pattern (`canvas_widget.py`, 15 lines)
- **Layer 4 - Exports**: Unified imports (`__init__.py`)

---

## Previous Updates (2026-05-19 ~ 2026-05-07)

For earlier updates (including Rust node language detection fix, path resolution fixes, VSCode workspace integration, etc.), please refer to [UPDATE_CN.md](UPDATE_CN.md) (Chinese version).

---

## Performance ⚡

| Metric | Value | Rating |
|--------|-------|--------|
| Startup time | < 2s | ⚡ Fast |
| Node loading | 4 nodes < 1s | ⚡ Fast |
| Canvas rendering | Smooth, no lag | ⚡ Excellent |
| Memory usage | Normal | ✅ Reasonable |
| CPU usage | < 5% | ✅ Low |
