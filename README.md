# BNOS - Bionic Neural Network Visual Orchestration Platform

🌍 **Language Selection**: [中文](README_CN.md) | **English**

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

> 📋 **See [UPDATE_EN.md](UPDATE_EN.md) for recent changes**

---

## 🆕 Previous Updates (2026-05-18)

### ✨ New Features & Improvements

#### 1. **Canvas Node Context Menu Enhancement - Start/Stop Nodes** ⚡
- **Feature**: Added dynamic start/stop node options when right-clicking nodes on canvas, intelligently displaying corresponding operations based on current node status
- **Design Philosophy**: **Context-Aware Quick Operations**, allowing users to directly control node lifecycle on canvas without switching to list panel or configuration dialog
- **Core Features**:
  - **Status-Aware Menu**: Dynamically displays "▶️ Start Node" or "⏹️ Stop Node" based on node running status
  - **Logic Reuse**: Fully utilizes main window's [start_selected_node_by_name](file://d:\BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform-main\ui\main_window.py#L1010-L1064) and `stop_selected_node_by_name` methods
  - **Instant Feedback**: Informs users of results through console logs and Toast notifications after operation
  - **Exception Handling**: Comprehensive error catching and user-friendly prompt messages
  
- **Technical Implementation**:
  - **Menu Refactoring**: Adds conditional judgment to node menu in `NodeCanvas.contextMenuEvent()`
  - **Status Detection**: Checks `node_info['status'] == 'running'` to decide which option to display
  - **New Methods**:
    - `start_single_node(node_name)` - Starts single node, reuses main window startup logic
    - `stop_single_node(node_name)` - Stops single node, reuses main window stop logic
  - **Safety Validation**:
    - Checks if node exists in [nodes_data](file://d:\BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform-main\ui\main_window.py#L0-L0)
    - Prevents duplicate startup (prompts if already running)
    - Prevents invalid stop (prompts if not running)
  
- **User Experience Improvements**:
  - ✅ **Convenient Operation**: Right-click on canvas to start/stop nodes, reducing operation steps
  - ✅ **Clear Visuals**: Menu items with icons and clear text,一目了然
  - ✅ **Status Sync**: Immediately updates node indicator light color and status text after operation
  - ✅ **Strong Error Tolerance**: Clear prompts for misoperations, won't cause program crashes
  - ✅ **High Consistency**: Maintains complete consistency with start/stop functions in node list and configuration dialog
  
- **Usage Scenarios**:
  ```
  Scenario 1: Quick Node Testing
  1. Find the node to test on canvas
  2. Right-click → Select "▶️ Start Node"
  3. Observe node status light turn green
  4. Check log output to confirm normal operation
  
  Scenario 2: Batch Node Management
  1. Right-click multiple nodes sequentially
  2. Start or stop as needed
  3. Real-time observation of each node's status changes
  ```
  
- **Affected Files**:
  - `ui/canvas_widget.py` - `NodeCanvas.contextMenuEvent()` method (modified node context menu)
  - `ui/canvas_widget.py` - Added `start_single_node()` and `stop_single_node()` methods

#### 2. **Node Configuration Dialog - Complete Layout Redesign** 🎨
- **Feature**: Redesigned node configuration dialog with horizontal rectangular window layout, left side displays complete config.json and output.json editors (editable) in vertical stack, right side shows node information and control buttons
- **Design Philosophy**: **Intuitive JSON Editing + Quick Operations Separation**, displaying configuration data and output data as plain text to enhance editing flexibility and visualization
- **Core Features**:
  - **Horizontal Wide-Screen Layout**: Window size adjusted to 1200x700px, better suited for modern displays
  - **Left-Right Split Design**: Left side occupies 2/3 space for JSON editing, right side occupies 1/3 space for controls and information
  - **Complete JSON Editing**: No longer uses scattered form fields, directly edit complete JSON file content
  - **Dark Theme Editor**: Consolas font, VSCode-style coloring (#1e1e1e background, #d4d4d4 text)
  
- **Left Area Details**:
  - **Top Section - config.json Editor**:
    - 📝 **Complete Configuration Editing**: Directly view and modify all configuration items (node_name, listen_upper_file, output_file, output_type, filter, etc.)
    - 🔄 **Real-time Refresh**: Reload latest config.json file from disk
    - 💾 **Smart Save**:
      - Auto-format JSON (2-space indentation, ensure_ascii=False)
      - JSON format validation, provide warning on errors but still allow forced save
      - Synchronize update memory data (nodes_data)
      - Auto-sync node display on canvas
    
  - **Bottom Section - output.json Editor**:
    - 📊 **Output Data Monitoring**: Real-time view of node processing results
    - ✏️ **Editable Mode**: Support manual modification of output data for testing
    - 🔄 **Quick Refresh**: One-click reload file content
    - 💾 **Safe Save**: Format validation + user confirmation mechanism
  
- **Right Area Details**:
  - **ℹ️ Node Information Card**:
    - Node name (bold display)
    - Node path (auto-wrap for long paths)
  
  - **🎮 Node Control Group**:
    - ▶️ **Start Node**: Green button, large font (13px), bold
    - ⏹️ **Stop Node**: Red button, eye-catching alert
    - *(10px spacing)*
  
  - **🔧 Quick Actions Group**:
    - 📁 **Open Node Folder**: Orange button
    - 💻 **Open Terminal**: Blue button, auto-activate virtual environment
    - 🔧 **Open VSCode**: Dark blue button (#007ACC), create workspace file
  
- **Technical Implementation**:
  - **Layout Refactoring**:
    - Main container: `QHBoxLayout` for left-right split
    - Left side: `QVBoxLayout` containing two `QGroupBox` (config.json and output.json)
    - Right side: `QVBoxLayout` containing three `QGroupBox` (info, control, quick actions)
    - Stretch ratio: Left stretch=2, Right stretch=1
  
  - **New Methods**:
    - `load_config_json()` - Load and format display config.json from disk
    - `save_config_from_editor()` - Save config.json from editor, including format validation and memory sync
  
  - **Removed Methods**:
    - ❌ `add_filter_rule()` - No longer need table-based Filter management
    - ❌ `delete_filter_rule()` - Edit directly in JSON
    - ❌ Old form fields (`listen_file_edit`, `output_type_edit`, `filter_table`)
  
  - **Import Fix**: Added missing `QHBoxLayout` import
  
- **User Experience Improvements**:
  - ✅ **Enhanced Flexibility**: Can directly copy-paste configuration blocks, batch modify multiple fields
  - ✅ **Improved Visualization**: Complete JSON structure at a glance, easier to understand configuration relationships
  - ✅ **Higher Efficiency**: No need to switch between multiple form fields, direct text editing is faster
  - ✅ **Strong Error Tolerance**: Warning on JSON format errors, but still allows save (for special scenarios)
  - ✅ **Reasonable Layout**: Horizontal wide-screen better suits modern displays, reduces scrolling
  - ✅ **Centralized Operations**: Right-side control buttons vertically arranged for quick access to common functions
  
- **Affected Files**:
  - `ui/property_panel.py` - `NodeConfigDialog` class (completely refactored init_ui method)
  - `ui/canvas_widget.py` - Added `mouseDoubleClickEvent()` method to trigger configuration dialog

#### 2. **Node List Drag-and-Drop Movement & Smart Grouping** 🎯
- **Feature**: Support drag-and-drop movement of nodes to different groups in the node list, automatically create new groups when nodes overlap on canvas, convert nesting operations to group creation, and automatically delete empty groups
- **Design Philosophy**: **Similar to Photoshop layer management**, node groups are parallel relationships without nesting structure. When users appear to create nesting, the system automatically converts it to creating new groups
- **Core Features**:
  - **Drag-and-Drop Movement**: Directly drag nodes to target groups or root level in the node list
  - **Smart Grouping**: When two nodes overlap more than 50% on canvas, automatically create a new node group and add them
  - **Nesting-to-Group Conversion**: When users attempt to drag a node onto another node (nesting), intelligently handle based on target node status:
    - Target node in a group → Directly merge into that group
    - Target node not in a group → Create new group containing all nodes
  - **Empty Group Cleanup**: Automatically delete empty node groups when detected, no user confirmation needed
  - **Anti-Stacking Restriction**: Strictly prohibit node stacking on canvas, prevent movement if it would overlap with other nodes
  
- **Drag-and-Drop Implementation** (Fully Autonomous Control):
  - **Enable Dragging**: Enable `DragEnabled`, `InternalMove`, and `AcceptDrops` for `QTreeWidget`
  - **Override dropEvent**: Intercept all drag-and-drop operations, don't rely on `rowsMoved` signal
  - **Smart Processing**:
    - Drag to group title: Call `add_nodes_to_group()` to add nodes to target group
    - Drag to blank area: Remove nodes from original group, become independent nodes
    - Drag to node within group: Check target node's group membership, merge or create new group
    - Drag to root-level node: Create new group containing all involved nodes
  - **Atomic Operations**: Complete all data changes first, then refresh UI once at the end, avoiding intermediate states
  - **Real-time Feedback**: Refresh list after movement, display Toast notification
  
- **Nesting-to-Group Conversion Logic** (Core Innovation):
  - **Intercept Drop**: Override `dropEvent`, check target type before drop occurs
  - **Smart Judgment**:
    ```python
    if target is node:
        if target node is in a group:
            Directly add dragged nodes to that group  # Merge into existing group
        else:
            Create new group containing all nodes  # Create parallel group
    elif target is blank area:
        Remove nodes from all groups  # Become independent nodes
    ```
  - **User Experience**: Users feel like they're creating nesting, but actually get more reasonable parallel group structure
  - **Debounce Mechanism**: Use timer to delay creation, avoid frequent operations
  
- **Auto-Create Group Logic** (Canvas Overlap Detection):
  - **Overlap Detection**: Monitor position changes in `NodeItem.itemChange()`
  - **Area Calculation**: Calculate overlap area ratio between two nodes (threshold 50%)
  - **Deduplication Check**: Check if overlapping nodes are already in the same group to avoid duplicate creation
  - **Smart Naming**: Automatically generate unique group names (Group_1, Group_2, ...)
  - **Random Coloring**: Assign random colors to new groups for visual distinction
  - **Instant Sync**: Immediately refresh node list and canvas display after creation
  - **Debounce Optimization**: Use timer to delay execution by 500ms, wait for user to stop dragging
  
- **Anti-Stacking Restriction** (New):
  - **Pre-check**: Detect if new position would cause stacking during `ItemPositionChange` phase
  - **Precise Calculation**: Calculate node's scene coordinate rectangle at new position, perform collision detection with other nodes
  - **Block Movement**: If stacking is detected, return current position and reject position change
  - **Smart Addition**: When adding nodes from node list to canvas, automatically calculate non-overlapping positions
    - **Multi-Strategy Candidate Generation**: Prioritize placement around existing nodes, then use grid scanning
    - **Real-time Collision Detection**: Iterate through all existing nodes to ensure new position won't overlap
    - **Fallback Solution**: If all candidate positions overlap, automatically place at bottom-right corner
  - **User Experience**: Nodes cannot overlap with others when dragging, and automatically avoid existing nodes when adding, keeping canvas tidy and organized
  
- **Empty Group Cleanup Mechanism** (Automated):
  - **Trigger Timing**: Automatically check after each node movement
  - **Smart Identification**: Iterate through all groups to find empty groups with 0 nodes
  - **Automatic Deletion**: Immediately delete empty groups when detected, no user confirmation needed
  - **Unified Refresh**: Execute all data operations first, then refresh list once at the end
  - **Friendly Notification**: Display number of deleted empty groups via Toast
  
- **Technical Implementation**:
  - New/Modified methods:
    - `_intercept_drop_event()` - Intercept and intelligently handle all drag-and-drop operations (core method)
    - `_get_dragged_nodes_from_event()` - Extract node list from drag event
    - `_create_group_for_dragged_nodes()` - Create new group for dragged nodes
    - `on_nodes_moved()` - Handle node drag-and-drop movement events (backup, main logic in _intercept_drop_event)
    - `_move_nodes_to_group()` - Move nodes to specified group (optimized refresh strategy)
    - `_move_nodes_to_ungrouped()` - Move nodes out of groups (optimized refresh strategy)
    - `_cleanup_empty_groups(refresh=True)` - Clean up empty node groups (supports refresh control)
    - `_check_node_overlap_and_create_group()` - Detect node overlap (NodeItem class, added debounce)
    - `_delayed_create_group()` - Delayed group creation (NodeItem class, debounce execution)
    - `_create_group_for_overlapping_nodes()` - Create group for overlapping nodes (NodeItem class)
  - Architecture Optimization:
    - **Fully Autonomous Control**: Don't rely on Qt's default drag-and-drop behavior, handle all logic ourselves
    - **Atomic Operations**: Complete all data changes first, then refresh UI once, avoiding intermediate states
    - **Parameterized Refresh**: `_cleanup_empty_groups()` supports `refresh` parameter, caller decides when to refresh
    - **Exception Handling**: Wrap drag-and-drop processing logic with try-except to ensure stability
  - Non-intrusive design: Only add new feature calls in existing methods without modifying original core logic
  
- **User Experience Improvements**:
  - ✅ Intuitive drag-and-drop operation, complete node grouping without right-click menu
  - ✅ Intelligent nesting conversion, simple user operation, system automatically optimizes data structure
  - ✅ Automatic empty group cleanup, keep node list tidy and organized, no manual maintenance needed
  - ✅ Clear visual feedback and operation prompts, every step has log output
  - ✅ Atomic refresh, avoid interface flickering and intermediate states
  
- **Affected Files**:
  - `ui/node_list_panel.py` - `NodeListPanel` class (drag interception, smart grouping, empty group cleanup)
  - `ui/canvas_widget.py` - `NodeItem` class (overlap detection, debounce group creation)

#### 2. **Node List Multi-Select Context Menu Optimization** 📋
- **Feature**: Refactored the multi-select right-click menu logic in the node list panel, all functions synchronously apply to all selected nodes
- **Design Philosophy**: Follows "Context-Aware Context Menu Design Specification", dynamically displaying different menu content based on selection state
- **Optimization Solution**:
  - **Single Selection Mode**: Displays complete operation menu for individual nodes (add to canvas, move to group, start/stop, rename, open folder, view log, edit config, delete, etc.)
  - **Multi-Selection Mode**: Only displays batch operation menus, all functions automatically apply to all selected nodes
  
- **New Batch Functions**:
  - **Batch Add to Canvas**: Add multiple selected nodes to canvas at once, automatically skip nodes already on canvas
  - **Batch Move to Group**: Move all selected nodes to specified group
  - **Batch Remove from Group**: When all selected nodes are in the same group, provide batch removal option
  - **Batch Start/Stop**: Start or stop all selected nodes simultaneously (existing feature, retained)
  - **Batch Open Folders**: Open folders of all selected nodes at once
  - **Batch View Logs**: Merge and display logs of all selected nodes for easy comparison and analysis
  - **Batch Edit Configs**: Sequentially open configuration dialog for each node
  - **Batch Delete**: Delete all selected nodes and their files simultaneously (existing feature, enhanced confirmation prompt)
  
- **Technical Implementation**:
  - Refactored `_show_node_context_menu()` method, using conditional branches to distinguish single and multi-selection modes
  - Added 7 new batch operation methods:
    - `batch_add_nodes_to_canvas()` - Batch add to canvas
    - `batch_open_node_folders()` - Batch open folders
    - `batch_view_node_logs()` - Batch view logs
    - `batch_edit_node_configs()` - Batch edit configs
    - `_get_common_group()` - Get common group (helper method)
    - `batch_remove_nodes_from_group()` - Batch remove from group
  - Smart detection: Check if selected nodes are in the same group, dynamically display related menu items
  - User-friendly: All batch operations provide detailed success/failure statistics and Toast notifications
  
- **User Experience Improvements**:
  - ✅ Cleaner menu when multi-selecting, only showing relevant batch operations
  - ✅ Prevent accidental operations: Won't accidentally execute single-node operations during multi-selection
  - ✅ Improved efficiency: Handle multiple nodes with one operation
  - ✅ Clear feedback: Clearly display operation count and results
  
- **Affected Files**: `ui/node_list_panel.py` - `NodeListPanel` class

#### 3. **Canvas Box Selection Optimization** 📦
- **Feature**: Strictly restrict box selection to trigger only on completely blank canvas areas, preventing accidental activation on nodes
- **Problem Background**: The previous box selection trigger condition was not strict enough, potentially causing unintended box selection mode when clicking on nodes or other interactive items, affecting normal node selection and dragging operations
- **Optimization Solution**:
  - **Strict Blank Detection**: Modified the box selection trigger condition in `mousePressEvent` to only allow box selection when `item is None`
  - **Removed Lenient Conditions**: Deleted the original `or` branch judgment to ensure box selection won't trigger on any QGraphicsItem
  - **Clear Log Indication**: Added "(blank area)"标识 for easier debugging and user understanding
  
- **Technical Implementation**:
  - Before: `if item is None or (not isinstance(item, NodeItem) and ...)`
  - After: `if item is None:` (only when completely blank)
  - If any item is clicked (node, edge, anchor, etc.), directly call `super().mousePressEvent(event)` to let default behavior handle it
  - Maintains mutual exclusivity with other interaction modes (Ctrl+click multi-select, pan mode)
  
- **User Experience Improvements**:
  - ✅ Clicking nodes normally selects/drags without accidentally entering box selection mode
  - ✅ Clicking edges or anchors responds normally without triggering box selection
  - ✅ Box selection rectangle only appears when long-pressing on truly blank canvas areas
  - ✅ More precise operations, reduced accidental actions
  
- **Affected Files**: `ui/canvas_widget.py` - `NodeCanvas.mousePressEvent()` method

#### 4. **Double-Click Node to Open Configuration** ⚙️
- **Feature**: Double-click nodes on the canvas to directly open the configuration dialog for quick editing
- **Implementation Details**:
  - **Double-Click Detection**: Monitors the canvas's `mouseDoubleClickEvent` event
  - **Target Recognition**: Uses `itemAt()` method to detect if the double-click position is on a node item (NodeItem)
  - **Configuration Loading**: Automatically retrieves node configuration and path from parent window
  - **Dialog Display**: Opens the complete [NodeConfigDialog](file://d:\BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform-main\ui\property_panel.py#L17-L490), including:
    - Basic configuration editing (listen file, output type, etc.)
    - Filter attention rule management
    - Output.json content viewing and editing
    - Node control buttons (start/stop/open folder/command line/VSCode workspace)
    - Configuration save functionality
  
- **Technical Implementation**:
  - Added new `mouseDoubleClickEvent()` method in `NodeCanvas` class
  - Precise target detection using `isinstance(item, NodeItem)`
  - Reuses existing `NodeConfigDialog` component without code duplication
  - Follows Qt event handling specifications: calls `event.accept()` and `return` after processing
  - Non-intrusive design: only adds new method without modifying existing code logic
  
- **Usage**:
  ```
  1. Find the node you want to configure on the canvas
  2. Double-click the node
  3. System automatically opens the configuration dialog
  4. Edit configuration and click "Save Configuration" button
  5. Configuration takes effect immediately and syncs to memory data
  ```
  
- **Affected Files**: `ui/canvas_widget.py` - `NodeCanvas` class
- **User Value**: Simplifies configuration editing workflow, no need to use context menu or list panel, improves operational efficiency

#### 5. **Multi-Select Batch Delete in Node List** 🗑️
- **Feature**: Support batch deletion of nodes after multi-selection using Shift/Ctrl in the node list panel
- **Implementation Details**:
  - **Multi-Selection Support**: Hold Shift or Ctrl key to select multiple nodes (existing feature)
  - **Enhanced Context Menu**: When multiple nodes are selected, right-click menu displays "🗑️ Delete X Selected Nodes" option
  - **Double Confirmation Mechanism**: Shows confirmation dialog before deletion, listing all nodes to be deleted (up to 10 displayed)
  - **Complete Cleanup Process**:
    - Automatically stops running node processes
    - Deletes node folders and all files
    - Removes references from node groups
    - Deletes from memory data
    - Removes node display from canvas
  - **Detailed Result Feedback**: Displays success/failure statistics, with failed nodes listed separately
  - **Toast Notification**: Notifies users via Toast after operation completion
  
- **Technical Implementation**:
  - Added `batch_delete_nodes()` method to handle batch deletion logic
  - Enhanced `_show_node_context_menu()` with conditional logic to show batch delete option when multiple nodes are selected
  - Comprehensive exception handling ensures failure of one node doesn't affect others
  - Follows project specifications: provides clear double confirmation to prevent accidental operations
  
- **Usage**:
  ```
  1. In the node list panel, hold Shift or Ctrl to select multiple nodes
  2. Right-click on any selected node
  3. Select "🗑️ Delete X Selected Nodes"
  4. Confirm the deletion operation
  5. System automatically completes cleanup for all nodes
  ```
  
- **Affected Files**: `ui/node_list_panel.py` - `NodeListPanel` class
- **User Value**: Improves node management efficiency, simplifies batch cleanup operations, reduces risk of accidental deletion

#### 6. **Window Close Process Detection & Management** 🛑
- **Feature**: Intelligent detection of running nodes when closing the application, with user-friendly confirmation dialog
- **Functionality**:
  - **Automatic Detection**: Scans all nodes in `nodes_data` to identify those with status 'running' and active process objects
  - **Smart Notification**: Displays a clear list of running nodes (up to 10 shown, with ellipsis for additional nodes)
  - **Three-Option Dialog**:
    - **Yes**: Force stop all running nodes and close the window (default option for safety)
    - **No**: Allow nodes to continue running in background, but close the window
    - **Cancel**: Abort the close operation and return to the application
  - **Cross-Platform Process Termination**:
    - Windows: Graceful terminate → CTRL_BREAK_EVENT → force kill with timeout protection
    - Linux/macOS: SIGTERM to process group → SIGKILL if needed
  - **Robust Error Handling**: Individual node failures don't affect other nodes; all process references cleaned up properly
  - **UI Synchronization**: Automatically updates node list panel and canvas display after batch operations
  - **User Feedback**: Toast notifications inform users of the outcome (number of nodes stopped or left running)
  
- **Implementation Details**:
  - Enhanced `BNOSMainWindow.closeEvent()` method with detection logic
  - New `_force_stop_all_nodes()` helper method for batch process termination
  - Follows external process management architecture specification
  - Maintains consistency with existing node lifecycle management
  
- **User Workflow**:
  ```
  User clicks window close button (X)
  ↓
  System detects 3 running nodes: Node_A, Node_B, Node_C
  ↓
  Dialog appears: "The following 3 nodes are running... Choose action:"
  ↓
  User selects:
    • Yes → All nodes stopped, window closes
    • No → Nodes continue in background, window closes
    • Cancel → Window stays open, user continues working
  ```
  
- **Use Cases**:
  - ✅ **Prevent Accidental Closure**: Users can cancel if they clicked close by mistake
  - ✅ **Background Processing**: Allow long-running tasks to continue after closing GUI
  - ✅ **Safe Shutdown**: Ensure clean termination of all processes before exit
  - ✅ **Flexibility**: Three options cover all possible user intentions
  
- **Technical Highlights**:
  - Default selection is "Yes" for safety-first approach
  - Proper resource cleanup prevents zombie processes
  - Exception handling ensures stability even if some processes fail to stop
  - Console logging provides detailed operation trace for debugging
  
- **Affected Files**: 
  - `ui/main_window.py` - `BNOSMainWindow.closeEvent()` and new `_force_stop_all_nodes()` methods
  
- **Code Quality**:
  - Follows project specifications for external process management
  - Cross-platform compatible with OS-specific strategies
  - Clean separation of concerns (detection vs. termination logic)
  - Comprehensive error handling and user feedback

---

## 🆕 Recent Updates (2026-05-17)

### ✨ New Features & Improvements

#### 1. **Enhanced Rust Node Generator** 🔧
- **Feature**: Complete rewrite of Rust node generation system with self-healing capabilities
- **Functionality**:
  - **Auto Environment Detection**: Automatically checks for Rust toolchain and build artifacts on startup
  - **Self-Repair Mechanism**: Detects missing or corrupted binaries and automatically rebuilds using `cargo build --release`
  - **Dual Binary Architecture**: Generates two executables:
    - `{node_name}`: Main processing logic (single execution mode)
    - `{node_name}_listener`: Persistent listener with auto-healing (continuous monitoring mode)
  - **Smart Build System**: Release mode optimization with LTO, codegen-units=1, and symbol stripping for maximum performance
  - **Cross-Platform Support**: Works seamlessly on Windows (.exe), macOS, and Linux
  
- **Implementation Details**:
  - **Modular Source Structure**: 
    - `src/main.rs`: Core business logic with JSON I/O handling
    - `src/listener.rs`: File monitoring loop with environment self-healing
    - `src/packet.rs`: Standardized output packet structure (success/error responses)
  - **Configuration Management**: Auto-generated `config.json` with filter rules, upstream/downstream paths, and output type settings
  - **Startup Scripts**: Platform-specific launchers (`start.bat` for Windows, `start.sh` for Unix) with built-in environment validation
  - **Logging System**: Automatic log rotation in `logs/listener.log` with timestamp formatting
  
- **User Workflow**:
  ```bash
  # Generate new Rust node
  python tools/rust_create_node.py my_processor
  
  # Enter directory and implement logic
  cd node_rust_my_processor
  # Edit src/main.rs to add custom processing logic
  
  # Build and run (auto-repair if needed)
  start.bat  # Windows
  ./start.sh # macOS/Linux
  ```
  
- **Performance Benefits**:
  - **10-100x faster** than Python equivalents due to compiled nature
  - **Memory safe**: Compiler-enforced ownership model prevents data races
  - **Zero-cost abstractions**: High-level ergonomics with low-level control
  - **Minimal runtime**: No garbage collector pauses, predictable latency
  
- **Self-Healing Capabilities**:
  - ✅ Checks for `rustc` and `cargo` availability before execution
  - ✅ Validates existence of `target/release/` directory
  - ✅ Verifies binary integrity by attempting execution
  - ✅ Automatically cleans corrupted build artifacts
  - ✅ Rebuilds project with detailed error reporting
  - ✅ Continues operation after successful repair without manual intervention
  
- **Affected Files**: 
  - `tools/rust_create_node.py` - Complete node generator with 1083 lines of template code
  - `node_rust_9/` - Example implementation demonstrating the architecture
  
- **Technical Highlights**:
  - Uses `serde` and `serde_json` for robust JSON serialization/deserialization
  - Implements chrono library for precise timestamp logging
  - Employs thread-based polling with configurable sleep intervals (200ms default)
  - Supports attention mechanism filtering via config.json rules
  - Graceful error handling with structured error packets

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

#### 2. **VSCode Workspace Optimization** ⚡
- **Smart Detection**: Pre-checks if VSCode is installed before attempting to open
  - Windows: Uses `where code` command
  - macOS/Linux: Uses `which code` command
  - Timeout protection (3 seconds) prevents hanging
- **Relative Path Configuration**: 
  - Uses `"path": "."` for workspace folder (relative path)
  - Uses `${workspaceFolder}` variable for Python interpreter path
  - Ensures project portability and safe migration
- **User-Friendly Interaction**:
  - If VSCode not detected: Shows confirmation dialog with clear guidance
  - User can choose to create workspace file anyway (for future use)
  - Provides installation tips: "Add 'code' command to PATH"
  - Respects user choice: Can cancel without creating any files
- **Cross-Platform Support**: Works seamlessly on Windows, macOS, and Linux
- **Enhanced Feedback**: Different success messages based on VSCode availability
  - With VSCode: "✅ Created and auto-opened"
  - Without VSCode: "✅ Created, double-click to open after installing VSCode"
- **Technical Improvement**: Separated detection logic into `_check_vscode_installed()` method for better maintainability

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
├── start_bnos_gui.bat             # Windows launcher
├── start_bnos_gui.sh              # Linux/Mac launcher
│
├── ui/                            # UI modules (Modular Architecture)
│   ├── __init__.py
│   ├── main_window.py            # Main window + Toast system
│   ├── canvas_widget.py          # Compatibility layer (Facade pattern, 15 lines)
│   ├── node_list_panel.py        # Node list with groups
│   ├── node_group_manager.py     # Group management logic
│   ├── node_creator_manager.py   # Node creation tool manager
│   ├── property_panel.py         # Config dialog + Log viewer
│   │
│   └── canvas/                   # 🆕 Modular Canvas Architecture
│       ├── __init__.py           # Module exports
│       ├── canvas_view.py        # Core layer: NodeCanvas controller (1763 lines)
│       ├── CANVAS_SPLIT_REPORT.md # Detailed refactoring documentation
│       │
│       └── items/                # Items layer: Pure UI rendering components
│           ├── __init__.py       # Graphics item exports
│           ├── anchor_item.py    # AnchorItem: Input/output ports
│           ├── node_item.py      # NodeItem: Node container
│           └── edge_item.py      # EdgeItem: Bezier curve connections
│
├── tools/                         # Development tools
│   ├── README.md                 # Tools documentation
│   ├── python_create_node.py     # Python node template generator
│   └── rust_create_node.py       # Rust node template generator
│
├── nodes/                         # Node instances
│   └── (user-created nodes)
│
├── app_config.json                # App settings (window state, last project)
├── canvas_layout.json             # Current project layout (auto-generated)
├── color_settings.json            # Node color customization (.gitignored)
└── requirements_gui.txt           # Python dependencies
```

**Architecture Highlights**:
- ✅ **Modular Canvas**: Split into 4 layers (Items, Core, Compatibility, Exports)
- ✅ **Separation of Concerns**: UI rendering isolated from business logic
- ✅ **Backward Compatible**: Old import paths still work via Facade pattern
- ✅ **Extensible**: Easy to add custom node types and interactions
- ✅ **Maintainable**: Each module has single responsibility

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
- **Last Updated**: 2026-05-17


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

## 🆕 Recent Updates (2026-05-20)
### 🏗️ Major Architecture Refactoring: UI Component Modularization & Menu Bar Integration (2026-05-21)

#### **Core Improvements Overview** 🎯

This update completes three major refactorings, significantly improving code maintainability, extensibility, and user experience:

1. **Toolbar Integrated into Menu Bar** - Simplified interface, following desktop application conventions
2. **Toast Notification System Componentized** - Fully decoupled, supporting cross-module reuse
3. **UI Directory Structure Reorganized** - Layered by functionality with clear responsibilities

---

#### **1. Toolbar Integrated into Menu Bar** 📋

**Design Philosophy**: Adopt pure menu bar design, remove standalone toolbar, integrate all functions into standard menus.

**Specific Changes**:
- ✅ Removed top toolbar, freeing up vertical space
- ✅ All functions integrated into "File", "Edit", "Help" three main menus
- ✅ High-frequency operations use submenu grouping (e.g., 7 language options under "New Node")
- ✅ Each menu item configured with clear shortcuts and visual identifiers (Emoji/Icon)
- ✅ Original business logic unchanged, only access entry modified

**Advantages**:
- 🎨 **Clean Interface** - Reduce visual clutter, focus on canvas workspace
- ⚡ **Efficient Operation** - Keyboard shortcuts + hierarchical menus for quick function location
- 📱 **Familiar Pattern** - Follows standard desktop application interaction patterns
- 🔧 **Easy Maintenance** - Menu logic centralized in `MenuManager` class

**Related Files**:
- `ui/menu/menu_manager.py` - Menu Manager (new)
- `ui/main_window.py` - Delegates to MenuManager

---

#### **2. Toast Notification System Componentized** 🔔

**Design Philosophy**: Extract Toast notifications from main window into independent module for complete decoupling.

**Core Features**:
- ✅ **Fully Decoupled** - Toast doesn't depend on main window, can be tested independently
- ✅ **Stack Management** - Automatically handles stacking display of multiple notifications
- ✅ **60fps Animation** - Smooth fade-in/fade-out effects
- ✅ **Four Types** - success, error, warning, info
- ✅ **Custom Duration** - Supports dynamic display time settings
- ✅ **Boundary Detection** - Intelligently adjusts position to avoid going off-screen

**New Files**:
- `ui/core/toast/toast_notification.py` - Toast core class
- `ui/core/toast/toast_manager.py` - Toast manager (stack management)
- `ui/docs/toast_examples.py` - Usage examples

**Migration Strategy**:
- ✅ Retain source backup (original class definition in main_window.py)
- ✅ Progressive migration, import new module first then delete old code
- ✅ Backward compatible, existing calling code needs no modification

---

#### **3. UI Directory Structure Reorganization** 📁

**Design Philosophy**: Organize by functional domains, each module has single responsibility, easy to maintain and extend.

**Reorganized Structure**:
```
ui/
├── __init__.py                      # Unified entry point
├── main_window.py                   # Main window
│
├── core/                            # Core components
│   ├── app_config.py                # Application configuration management
│   └── toast/                       # Toast notification system
│       ├── toast_notification.py
│       └── toast_manager.py
│
├── menu/                            # Menu system
│   └── menu_manager.py              # Menu bar manager
│
├── canvas/                          # Canvas system
│   ├── canvas_view.py               # Canvas view
│   └── items/                       # Canvas elements
│       ├── node_item.py             # Node item
│       ├── edge_item.py             # Edge item
│       └── anchor_item.py           # Anchor item
│
├── panels/                          # Panel components
│   ├── node_list_panel.py           # Node list panel
│   ├── property_panel.py            # Property panel
│   └── node_group_manager.py        # Node group management
│
├── creators/                        # Creators
│   └── node_creator_manager.py      # Node creator manager
│
└── docs/                            # Documentation
    └── toast_examples.py
```

**Import Method Comparison**:

```python
# Old method (still available)
from ui.toast_notification import ToastNotification
from ui.menu_manager import MenuManager

# New method (recommended)
from ui.core import AppConfig, ToastManager, ToastNotification
from ui.menu import MenuManager
from ui.panels import NodeListPanel
from ui.canvas import NodeCanvas
from ui.creators import NodeCreatorManager
```

**Verification Results**:
```
Total tests: 20
Passed: 20 ✅
Failed: 0 ❌
🎉 All tests passed! UI reorganization successful!
```

**Core Value**:
- 🎯 **Clear Structure** - Immediately see component ownership
- 🔧 **Easy Maintenance** - Related files managed together
- ♻️ **Support Reuse** - More convenient cross-module imports
- 📚 **Complete Documentation** - Detailed explanation for each module
- 🛡️ **Safe & Reliable** - Thoroughly tested, backward compatible

---

#### **Bug Fix: New Node Creation Feature** 🔧

**Problem**: New node creation feature failed

**Cause**: Path calculation error in NodeCreatorManager

**Fix**: Added one more dirname call to reach project root directory

**Results**:
- ✅ Python node creation works normally
- ✅ Rust node creation works normally
- ✅ Automatic node list refresh

---

#### **Performance Metrics** ⚡

| Metric | Value | Rating |
|--------|-------|--------|
| Startup Time | < 2 seconds | ⚡ Fast |
| Node Loading | 4 nodes < 1 second | ⚡ Fast |
| Canvas Rendering | Smooth without lag | ⚡ Excellent |
| Memory Usage | Normal | ✅ Reasonable |
| CPU Usage | < 5% | ✅ Low |

---

#### **Related Documentation** 📚

- [UI_REFACTORING_COMPLETE.md](UI_REFACTORING_COMPLETE.md) - Complete UI refactoring report
- [IMPORT_PATH_FIXES.md](IMPORT_PATH_FIXES.md) - Import path fix records
- [FIX_NODE_CREATION.md](FIX_NODE_CREATION.md) - New node creation fix
- [TEST_REPORT_UI_REFACTORING.md](TEST_REPORT_UI_REFACTORING.md) - Test report

---


### 🏗️ Major Architecture Refactoring: Canvas Widget Modularization

#### **Canvas Widget Split into Layered Architecture** 🎨
- **Overview**: Successfully refactored the monolithic canvas_widget.py (91.9KB) into a modular four-layer architecture, significantly improving code maintainability, testability, and extensibility
- **Motivation**: 
  - Single file exceeded 2200 lines, difficult to maintain and extend
  - Mixed responsibilities (UI rendering + business logic + event handling)
  - Poor testability due to tight coupling
  - Violation of SOLID principles

##### **New Architecture Design**

**Layer 1: Items Layer** (ui/canvas/items/)
- **Responsibility**: Pure UI rendering components, no business logic
- **Components**:
  - nchor_item.py: Node ports (input/output anchors), supports hover highlighting and connection state display
  - 
ode_item.py: Node container, manages title, labels, selection state
  - edge_item.py: Connection lines, draws Bezier curves, supports dynamic updates
- **Design Principles**:
  - No canvas references held
  - Communication via callback functions
  - Focus on visual presentation and interaction feedback

**Layer 2: Core Layer** (ui/canvas/canvas_view.py)
- **Responsibility**: Canvas core management and business logic
- **Contains**:
  - NodeCanvas class: Main canvas controller (74.5KB, ~1763 lines)
  - Node/edge management (CRUD operations)
  - Mouse/keyboard event handling
  - Layout save/load
  - Zoom/pan control
  - Box selection/multi-selection features
- **Key Features**:
  - QGraphicsView + QGraphicsScene architecture
  - VueFlow-style infinite canvas experience
  - Supports 5000x5000 pixel canvas space
  - Grid background rendering
  - Auto-save mechanism (debounced 500ms)

**Layer 3: Compatibility Layer** (ui/canvas_widget.py)
- **Responsibility**: Maintain backward compatibility
- **Implementation**: Facade pattern, redirects to new modules
- **Code Size**: Only 15 lines
- **Migration Strategy**: 
  `python
  # Old code (still works)
  from ui.canvas_widget import NodeCanvas
  
  # New code (recommended)
  from ui.canvas import NodeCanvas
  `

**Layer 4: Module Exports** (ui/canvas/__init__.py, ui/canvas/items/__init__.py)
- **Responsibility**: Unified import interfaces
- **Advantage**: Simplifies caller code, hides internal structure

##### **Refactoring Results**

**Code Metrics Comparison**:

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Single File Size** | 91.9KB | 74.5KB (core) + distributed items | ⬇️ 19% |
| **Module Count** | 1 | 5 core modules | ⬆️ 5x |
| **Lines of Code** | ~2200 | ~1763 (core) + items | Similar |
| **Responsibility Clarity** | Mixed | Clear layering | ✅ Significant improvement |
| **Testability** | Difficult | Easy unit testing | ✅ Significant improvement |
| **Maintainability** | Low | High | ✅ Significant improvement |

##### **Verification Results**

**Functional Completeness Check**:
- ✅ Node drag functionality works normally
- ✅ Anchor connection functionality works normally
- ✅ Bezier curve rendering works normally
- ✅ Zoom/pan functionality works normally
- ✅ Box selection/multi-selection works normally
- ✅ Layout save/load works normally
- ✅ Right-click menu functionality works normally
- ✅ Node configuration dialog works normally

**Compatibility Check**:
- ✅ Old import method still works: rom ui.canvas_widget import NodeCanvas
- ✅ New import method available: rom ui.canvas import NodeCanvas
- ✅ All existing features have no breaking changes

**Performance Check**:
- ✅ Canvas rendering frame rate has no significant change
- ✅ Memory usage has no significant increase
- ✅ Node operation response speed remains consistent

##### **Affected Files**:
- ui/canvas/__init__.py - **NEW**: Module export interface
- ui/canvas/canvas_view.py - **NEW**: Core view and business logic (1763 lines)
- ui/canvas/items/__init__.py - **NEW**: Graphics item module exports
- ui/canvas/items/anchor_item.py - **NEW**: Anchor item (input/output ports)
- ui/canvas/items/node_item.py - **NEW**: Node container item
- ui/canvas/items/edge_item.py - **NEW**: Connection line (Bezier curve)
- ui/canvas_widget.py - **MODIFIED**: Reduced to 15 lines (Facade pattern)
- ui/canvas/CANVAS_SPLIT_REPORT.md - **NEW**: Detailed refactoring report

##### **User Impact**: 
- ✅ **Zero Breaking Changes**: All existing functionality preserved
- ✅ **Improved Stability**: Better code organization reduces bug risk
- ✅ **Faster Future Development**: Modular architecture enables rapid feature additions
- ✅ **Better Documentation**: Clear separation makes code easier to understand

##### **Documentation**:
- Full technical details: [ui/canvas/CANVAS_SPLIT_REPORT.md](ui/canvas/CANVAS_SPLIT_REPORT.md)

---

## 🆕 Recent Updates (2026-05-19)

### 🔧 Critical Bug Fixes & Enhancements

#### 1. **Rust Node Language Detection Fix** 🦀
- **Issue**: Rust nodes displayed as "Unknown" on canvas instead of "Rust"
- **Root Cause**: The `detect_language()` method only checked for `main.rs` in the root directory, but Rust projects use `src/main.rs` structure
- **Solution**: Enhanced language detection logic to check both `src/main.rs` and `Cargo.toml` files
- **Technical Implementation**:
  ```python
  # Before: Only checked root directory
  elif os.path.exists(os.path.join(node_path, "main.rs")):
      return "Rust"
  
  # After: Check standard Rust project structure
  elif os.path.exists(os.path.join(node_path, "src", "main.rs")) or \
       os.path.exists(os.path.join(node_path, "Cargo.toml")):
      return "Rust"
  ```
- **Affected Files**:
  - `ui/canvas_widget.py` - `NodeCanvas.detect_language()` method
- **User Impact**: ✅ Rust nodes now correctly display "Rust" label on canvas

#### 2. **Node Folder Path Resolution Fix** 📁
- **Issue**: Clicking "Open Node Folder" opened incorrect directories (e.g., Documents folder) instead of actual node folders
- **Root Cause**: Node paths were not properly normalized, potentially stored as relative paths affected by working directory changes
- **Solution**: Implemented three-layer path validation and normalization mechanism

##### **Layer 1: Path Normalization During Node Loading** (`ui/main_window.py`)
- **Enhanced `refresh_nodes()` method**:
  ```python
  # Ensure project path is absolute
  project_path = os.path.abspath(self.current_project_path)
  nodes_dir = os.path.join(project_path, "nodes")
  
  # Normalize each node path
  node_path = os.path.join(nodes_dir, item)
  node_path = os.path.abspath(node_path)  # Convert to absolute path
  node_path = os.path.normpath(node_path)  # Normalize (handle ..\ etc.)
  ```
- **New Features**:
  - ✅ Detailed loading logs for each node (path, existence status)
  - ✅ Path consistency validation
  - ✅ Automatic correction of inconsistent paths
  - ✅ Display total loaded node count

##### **Layer 2: Path Validation in Config Dialog** (`ui/property_panel.py`)
- **Enhanced `NodeConfigDialog.open_node_folder()` method**:
  ```python
  # Ensure path is absolute and normalized
  original_path = self.node_path
  corrected_path = os.path.abspath(original_path)
  corrected_path = os.path.normpath(corrected_path)
  
  if original_path != corrected_path:
      print(f"⚠️  Path corrected:")
      print(f"   Original: {original_path}")
      print(f"   Corrected: {corrected_path}")
      self.node_path = corrected_path
  
  # Fallback: Get correct path from parent window's nodes_data
  if not os.path.exists(self.node_path):
      if self.parent_window and hasattr(self.parent_window, 'nodes_data'):
          node_info = self.parent_window.nodes_data.get(self.node_name)
          if node_info and 'path' in node_info:
              correct_path = os.path.abspath(node_info['path'])
              correct_path = os.path.normpath(correct_path)
              if os.path.exists(correct_path):
                  self.node_path = correct_path
  ```
- **New Features**:
  - ✅ Automatic path detection and correction
  - ✅ Fallback path recovery from parent window
  - ✅ Comprehensive debug logging (path type, existence, parent directory, etc.)
  - ✅ User-friendly error messages with troubleshooting tips

##### **Layer 3: Path Validation in Node List** (`ui/node_list_panel.py`)
- **Enhanced `NodeListPanel.open_node_folder()` method**:
  - Same path validation and correction logic as config dialog
  - Fallback to main window's nodes_data for path recovery
  - Complete debug information output

- **Debug Log Example**:
  ```
  ============================================================
  🔍 [NodeConfigDialog] Opening Node Folder
  🔍 Node Name: node_rust_test
  🔍 Original Path: D:\Project\nodes\node_rust_test
  🔍 Final Path: D:\Project\nodes\node_rust_test
  🔍 Path Exists: True
  🔍 Is Directory: True
  🔍 Parent Directory: D:\Project\nodes
  🔍 Folder Name: node_rust_test
  🔍 Current Working Directory: D:\Project
  🔍 Expected Folder: node_rust_test
  🔍 Actual Folder: node_rust_test
  🔍 Name Match: True
  ✅ Opened node folder: D:\Project\nodes\node_rust_test
  ============================================================
  ```

- **Before vs After**:
  | Aspect | Before Fix | After Fix |
  |--------|-----------|-----------|
  | **Path Type** | Possibly relative | Forced absolute + normalized |
  | **Path Consistency** | May be inconsistent | Auto-validated and corrected |
  | **Error Recovery** | None | Multi-level fallback paths |
  | **Debug Info** | None | Detailed console logs |
  | **User Experience** | Opens wrong folder | Always opens correct node folder |

- **Affected Files**:
  - `ui/main_window.py` - `MainWindow.refresh_nodes()` method
  - `ui/property_panel.py` - `NodeConfigDialog.open_node_folder()` method
  - `ui/node_list_panel.py` - `NodeListPanel.open_node_folder()` method
  - `diagnose_rust_node.py` - New diagnostic tool for Rust nodes
  - `RUST_NODE_PATH_FIX.md` - Detailed fix documentation

- **Usage Instructions**:
  1. After starting the program, click "Refresh Node List" button
  2. Check console output to confirm all node paths are loaded correctly
  3. Double-click a node or right-click → "Edit Config"
  4. Click "📁 Open Node Folder" button
  5. Verify the debug logs (lines starting with 🔍) show correct paths

- **User Impact**: 
  - ✅ All nodes (Python, Rust, Node.js, etc.) now open the correct folder
  - ✅ Paths are always absolute and normalized, unaffected by working directory
  - ✅ Intelligent error recovery when paths are missing
  - ✅ Comprehensive debugging information for troubleshooting

---

