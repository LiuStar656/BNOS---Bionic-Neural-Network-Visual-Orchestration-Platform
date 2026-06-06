# 🆕 Previous Updates

## 🆕 Previous Updates (2026-05-18)

### ✨ New Features and Optimizations

#### 1. **Canvas Node Right-Click Menu Enhancement - Start/Stop Node** ⚡
- **Feature**: When right-clicking a node on canvas, added dynamic start/stop node option that intelligently shows corresponding action based on current node state
- **Design Philosophy**: **Context-aware shortcut operations**, let users control node lifecycle directly on canvas without switching to list panel or config dialog
- **Core Features**:
  - **State-aware Menu**: Dynamically displays "▶️ Start Node" or "⏹️ Stop Node" based on node running state
  - **Reuse Existing Logic**: Fully calls main window's `start_selected_node_by_name` and `stop_selected_node_by_name` methods
  - **Instant Feedback**: Notifies user through console log and Toast notification after operation completes
  - **Exception Handling**: Complete error catching and user-friendly prompt messages
  
- **Technical Implementation**:
  - **Menu Refactoring**: Added conditional judgment in `NodeCanvas.contextMenuEvent()` for node menu
  - **State Detection**: Checks `node_info['status'] == 'running'` to decide which option to display
  - **New Methods**:
    - `start_single_node(node_name)` - Start single node, reuse main window start logic
    - `stop_single_node(node_name)` - Stop single node, reuse main window stop logic
  - **Safety Validation**:
    - Checks if node exists in `nodes_data`
    - Prevents duplicate start (prompts when already running)
    - Prevents invalid stop (prompts when not running)
  
- **User Experience Improvements**:
  - ✅ **Convenient Operation**: Right-click directly on canvas to start/stop nodes, reduce steps
  - ✅ **Clear Visuals**: Menu items with icons and clear text, easy to understand
  - ✅ **State Sync**: Immediately updates node indicator color and status text after operation
  - ✅ **Fault Tolerant**: Clear prompts for misoperations, won't cause program crash
  - ✅ **High Consistency**: Fully consistent with start/stop features in node list and config dialog
  
- **Use Cases**:
  ```
  Case 1: Quick Node Testing
  1. Find node to test on canvas
  2. Right-click → Select "▶️ Start Node"
  3. Observe node status light turn green
  4. Check log output to confirm normal operation
  
  Case 2: Batch Node Management
  1. Right-click multiple nodes sequentially
  2. Start or stop as needed
  3. Real-time observation of each node's state changes
  ```
  
- **Affected Files**:
  - `ui/canvas_widget.py` - `NodeCanvas.contextMenuEvent()` method (modified node right-click menu)
  - `ui/canvas_widget.py` - Added `start_single_node()` and `stop_single_node()` methods

#### 2. **Node Configuration Dialog All-New Layout Design** 🎨
- **Feature**: Redesigned node configuration dialog with horizontal rectangular window layout, left side has two windows showing complete config.json and output.json (editable), right side has node info and control buttons
- **Design Philosophy**: **Intuitive JSON Editing + Quick Operation Separation**, shows config data and output data in plain text, improves editing flexibility and visualization
- **Core Features**:
  - **Horizontal Wide Layout**: Window size adjusted to 1200x700px, better for modern displays
  - **Left-Right Split Design**: Left side takes 2/3 space for JSON editing, right side takes 1/3 space for control and info display
  - **Complete JSON Editing**: No longer uses scattered form fields, directly edits complete JSON file content
  - **Dark Theme Editor**: Consolas font, VSCode style colors (#1e1e1e background, #d4d4d4 text)
  
- **Left Area Details**:
  - **Upper Half - config.json Editor**:
    - 📝 **Complete Config Editing**: Directly view and modify all config items (node_name, listen_upper_file, output_file, output_type, filter, etc.)
    - 🔄 **Real-time Refresh**: Reload latest config.json from disk
    - 💾 **Smart Save**:
      - Auto-formats JSON (2-space indent, ensure_ascii=False)
      - JSON format validation, warns on error but still allows forced save
      - Syncs memory data (nodes_data)
      - Auto-syncs node display on canvas
    
  - **Lower Half - output.json Editor**:
    - 📊 **Output Data Monitoring**: Real-time view of node processing results
    - ✏️ **Editable Mode**: Supports manual modification of output data for testing
    - 🔄 **Quick Refresh**: One-click reload of file content
    - 💾 **Safe Save**: Format validation + user confirmation mechanism
  
- **Right Area Details**:
  - **ℹ️ Node Info Card**:
    - Node name (bold display)
    - Node path (auto-wraps, adapts to long paths)
  
  - **🎮 Node Control Group**:
    - ▶️ **Start Node**: Green button, large font (13px), bold
    - ⏹️ **Stop Node**: Red button, prominent display
    - (10px spacing)
  
  - **🔧 Quick Operation Group**:
    - 📁 **Open Node Folder**: Orange button
    - 💻 **Open Command Line**: Blue button, auto-activates virtual environment
    - 🔧 **Open VSCode**: Dark blue button (#007ACC), creates workspace file
  
- **Technical Implementation**:
  - **Layout Refactoring**:
    - Main container: `QHBoxLayout` for left-right split
    - Left side: `QVBoxLayout` containing two `QGroupBox` (config.json and output.json)
    - Right side: `QVBoxLayout` containing three `QGroupBox` (info, control, quick operations)
    - Elastic ratio: Left stretch=2, Right stretch=1
  
  - **New Methods**:
    - `load_config_json()` - Load and format config.json from disk
    - `save_config_from_editor()` - Save config.json from editor, includes format validation and memory sync
  
  - **Deleted Methods**:
    - ❌ `add_filter_rule()` - No longer needs table to manage Filter
    - ❌ `delete_filter_rule()` - Edit directly in JSON
    - ❌ Old form fields (`listen_file_edit`, `output_type_edit`, `filter_table`)
  
  - **Import Fix**: Added missing `QHBoxLayout` import
  
- **User Experience Improvements**:
  - ✅ **Enhanced Flexibility**: Can directly copy-paste config blocks, batch-modify multiple fields
  - ✅ **Better Visualization**: Complete JSON structure一目了然, easier to understand config relationships
  - ✅ **Higher Efficiency**: No need to switch between multiple form fields, direct text editing is faster
  - ✅ **High Fault Tolerance**: Warns on JSON format errors but still allows save (for special scenarios)
  - ✅ **Reasonable Layout**: Horizontal wide screen better for modern displays, reduces scrolling
  - ✅ **Concentrated Operations**: Right side control buttons vertical layout, quick access to common functions
  
- **Affected Files**:
  - `ui/property_panel.py` - `NodeConfigDialog` class (completely refactored init_ui method)
  - `ui/canvas_widget.py` - Added `mouseDoubleClickEvent()` method to trigger config dialog

#### 3. **Node List Drag & Drop and Smart Grouping** 🎯
- **Feature**: Supports dragging nodes to different groups in node list, auto-generates new group when nodes on canvas overlap, node nesting operations auto-convert to group creation, empty groups auto-deleted
- **Design Philosophy**: **Photoshop-like layer management**, node groups are parallel, no nesting structure. User seemingly performs nesting operation, system auto-converts to group creation
- **Core Features**:
  - **Drag & Drop**: Directly drag nodes to target group or root level in node list
  - **Smart Grouping**: When two nodes on canvas overlap by more than 50%, auto-creates new node group and adds them
  - **Nesting to Grouping**: When user attempts to drag node onto another node (nesting), intelligently handles based on target node state:
    - Target node in group → directly merges into that group
    - Target node not in group → creates new group containing all nodes
  - **Empty Group Cleanup**: Detects empty node groups and auto-deletes, no user confirmation needed
  - **Anti-Stacking Limit**: Strictly prohibits node stacking on canvas, prevents movement if drag would overlap with other nodes
  
- **Drag & Drop Implementation** (Full Self-Control):
  - **Enable Drag**: Enabled `DragEnabled`, `InternalMove`, and `AcceptDrops` for `QTreeWidget`
  - **Override dropEvent**: Intercepts all drop operations, doesn't rely on `rowsMoved` signal
  - **Smart Handling**:
    - Dropped on group header: Calls `add_nodes_to_group()` to add nodes to target group
    - Dropped on blank: Removes nodes from original group, becomes independent nodes
    - Dropped on group node: Checks target node's group membership, directly merges or creates new group
    - Dropped on root level node: Creates new group containing all involved nodes
  - **Atomic Operation**: Completes all data changes first, finally refreshes UI once, avoids intermediate states
  - **Real-time Feedback**: Refreshes list after move, shows Toast notification
  
- **Nesting to Grouping Logic** (Core Innovation):
  - **Intercept Drop**: Overrides `dropEvent`, checks target type before drop occurs
  - **Smart Judgment**:
    ```python
    if target is node:
        if target node is in some group:
            directly add dragged node to that group  # merge into existing group
        else:
            create new group containing all nodes  # create parallel group
    elif target is blank:
        remove node from all groups  # become independent node
    ```
  - **User Experience**: User feels like creating nesting, actually gets more reasonable parallel group structure
  - **Debounce Mechanism**: Uses timer to delay creation, avoids frequent operations
  
- **Auto Create Group Logic** (Canvas Overlap Detection):
  - **Overlap Detection**: Listens for position changes in `NodeItem.itemChange()`
  - **Area Calculation**: Calculates overlap area ratio of two nodes (threshold 50%)
  - **Duplicate Check**: Checks if overlapping nodes already in same group, avoids duplicate creation
  - **Smart Naming**: Auto-generates unique group name (Group_1, Group_2, ...)
  - **Random Color**: Assigns random color to new group for visual distinction
  - **Instant Sync**: Immediately refreshes node list and canvas display after creation
  - **Debounce Optimization**: Uses 500ms timer delay, waits for user to stop dragging
  
- **Anti-Stacking Limit** (New):
  - **Pre-check**: Detects if new position would cause stacking during `ItemPositionChange` phase
  - **Precise Calculation**: Calculates scene coordinate rectangle of node in new position, collision detection with other nodes
  - **Prevents Movement**: If stacking would occur, returns current position, rejects position change
  - **Smart Add**: When adding nodes to canvas from node list, auto-calculates non-overlapping position
    - **Multi-strategy Candidate Position Generation**: Prioritizes placing around existing nodes, then uses grid scan
    - **Real-time Collision Detection**: Iterates all existing nodes, ensures new position won't overlap
    - **Fallback**: If all candidate positions overlap, auto-places at bottom-right
  - **User Experience**: Can't overlap other nodes when dragging, auto-avoids existing nodes when adding, keeps canvas clean and organized
  
- **Empty Group Cleanup Mechanism** (Automated):
  - **Trigger Timing**: Auto-checks after each node move
  - **Smart Recognition**: Iterates all groups, finds empty groups with 0 nodes
  - **Auto Delete**: Immediately auto-deletes when empty group detected, no user confirmation needed
  - **Unified Refresh**: Performs all data operations first, finally refreshes list once
  - **Friendly Prompt**: Shows number of deleted empty groups through Toast
  
- **Technical Implementation**:
  - New/Modified Methods:
    - `_intercept_drop_event()` - Intercepts and intelligently handles all drop operations (core method)
    - `_get_dragged_nodes_from_event()` - Extracts node list from drag event
    - `_create_group_for_dragged_nodes()` - Creates new group for dragged nodes
    - `on_nodes_moved()` - Handles node drag move event (backup, main logic in _intercept_drop_event)
    - `_move_nodes_to_group()` - Moves nodes to specified group (optimized refresh strategy)
    - `_move_nodes_to_ungrouped()` - Removes nodes from group (optimized refresh strategy)
    - `_cleanup_empty_groups(refresh=True)` - Cleans empty node groups (supports refresh control)
    - `_check_node_overlap_and_create_group()` - Detects node overlap (NodeItem class, added debounce)
    - `_delayed_create_group()` - Delayed group creation (NodeItem class, debounce execution)
    - `_create_group_for_overlapping_nodes()` - Creates group for overlapping nodes (NodeItem class)
  - Architecture Optimization:
    - **Full Self-Control**: Doesn't rely on Qt's default drag behavior, handles all logic ourselves
    - **Atomic Operation**: Completes all data changes first, then refreshes UI, avoids intermediate states
    - **Parameterized Refresh**: `_cleanup_empty_groups()` supports `refresh` parameter, caller decides when to refresh
    - **Exception Handling**: Uses try-except wrapping drag handling logic, ensures stability
  - Non-intrusive design: Only adds new function calls in existing methods, no modification to original core logic
  
- **User Experience Improvements**:
  - ✅ Intuitive drag operations, completes node grouping without right-click menu
  - ✅ Smart nesting conversion, user operation simple, system auto-optimizes data structure
  - ✅ Auto-cleans empty groups, keeps node list clean and organized, no manual maintenance
  - ✅ Clear visual feedback and operation prompts, each step has log output
  - ✅ Atomic refresh, avoids interface flicker and intermediate states
  
- **Affected Files**:
  - `ui/node_list_panel.py` - `NodeListPanel` class (drag interception, smart grouping, empty group cleanup)
  - `ui/canvas_widget.py` - `NodeItem` class (overlap detection, debounce group creation)

#### 4. **Node List Multi-Select Right-Click Menu Optimization** 📋
- **Feature**: Refactored node list panel multi-select right-click menu logic, all features sync to all selected nodes
- **Design Philosophy**: Follows "context-aware right-click menu design specification", dynamically shows different menu content based on selection state
- **Optimization Plan**:
  - **Single Select Mode**: Shows complete operation menu for single node (add to canvas, move group, start/stop, rename, open folder, view log, edit config, delete, etc.)
  - **Multi Select Mode**: Only shows batch operation menu, all features auto-apply to all selected nodes
  
- **New Batch Features**:
  - **Batch Add to Canvas**: Adds multiple selected nodes to canvas at once, auto-skips nodes already on canvas
  - **Batch Move to Group**: Moves all selected nodes to specified group
  - **Batch Remove from Group**: When all selected nodes in same group, provides batch remove option
  - **Batch Start/Stop**: Starts or stops all selected nodes simultaneously (existing feature, retained)
  - **Batch Open Folders**: Opens all selected node folders simultaneously
  - **Batch View Logs**: Combines and displays log content of all selected nodes for comparison
  - **Batch Edit Configs**: Opens config dialog for each node sequentially for editing
  - **Batch Delete**: Deletes all selected nodes and their files simultaneously (existing feature, enhanced confirmation prompt)
  
- **Technical Implementation**:
  - Refactored `_show_node_context_menu()` method, uses conditional branches to distinguish single and multi select modes
  - Added 7 batch operation methods:
    - `batch_add_nodes_to_canvas()` - Batch add to canvas
    - `batch_open_node_folders()` - Batch open folders
    - `batch_view_node_logs()` - Batch view logs
    - `batch_edit_node_configs()` - Batch edit configs
    - `_get_common_group()` - Get common group (helper method)
    - `batch_remove_nodes_from_group()` - Batch remove from group
  - Smart judgment: Detects if selected nodes in same group, dynamically displays related menu items
  - User friendly: All batch operations provide detailed success/failure stats and Toast notifications
  
- **User Experience Improvements**:
  - ✅ Menu cleaner when multi-selecting, only shows related batch operations
  - ✅ Avoids misoperations: Won't accidentally execute single node operations when multi-selecting
  - ✅ Improves efficiency: One operation handles multiple nodes
  - ✅ Clear feedback: Clearly shows number of nodes and operation results
  
- **Affected Files**: `ui/node_list_panel.py` - `NodeListPanel` class

#### 5. **Canvas Box Selection Optimization** 📦
- **Feature**: Strictly limits box selection to only trigger on completely blank canvas areas, avoids accidental box selection on nodes
- **Background**: Previous box selection judgment not strict enough, may accidentally trigger box selection mode when clicking nodes or other interactive items, affecting normal node selection and drag operations
- **Optimization Plan**:
  - **Strict Blank Detection**: Modified box selection trigger condition in `mousePressEvent`, only allows box selection when `item is None`
  - **Removed Loose Condition**: Deleted original `or` branch judgment, ensures box selection won't trigger on any QGraphicsItem
  - **Clear Log Prompt**: Added "(blank area)" identifier, easier for debugging and user understanding
  
- **Technical Implementation**:
  - Before: `if item is None or (not isinstance(item, NodeItem) and ...)`
  - After: `if item is None:` (only when completely blank)
  - If any item clicked (node, edge, anchor, etc.), directly calls `super().mousePressEvent(event)` to let default behavior handle
  - Maintains mutual exclusivity with other interaction modes (Ctrl+click multi-select, pan mode)
  
- **User Experience Improvements**:
  - ✅ Normal select/drag when clicking node, won't accidentally enter box selection mode
  - ✅ Normal response when clicking edge or anchor, doesn't trigger box selection
  - ✅ Only shows box selection rectangle on truly blank canvas area with long press
  - ✅ More precise operation, reduces misoperations
  
- **Affected Files**: `ui/canvas_widget.py` - `NodeCanvas.mousePressEvent()` method

#### 6. **Canvas Node Double-Click Opens Config** ⚙️
- **Feature**: Double-click node on canvas to directly open config dialog, quickly edit node config
- **Implementation Details**:
  - **Double-Click Detection**: Listens for canvas `mouseDoubleClickEvent` event
  - **Target Recognition**: Detects if double-click position is node item (NodeItem) through `itemAt()` method
  - **Config Loading**: Auto-obtains node config info and path from parent window
  - **Dialog Display**: Opens complete `NodeConfigDialog`, includes:
    - Basic config editing (listen file, output type, etc.)
    - Filter attention rule management
    - Output.json content viewing and editing
    - Node control buttons (start/stop/open folder/command line/VSCode workspace)
    - Config save function
  
- **Technical Implementation**:
  - Added `mouseDoubleClickEvent()` method to `NodeCanvas` class
  - Uses `isinstance(item, NodeItem)` for precise target judgment
  - Calls existing `NodeConfigDialog` component, reuses existing features
  - Follows Qt event handling specification: Calls `event.accept()` and `return` after handling
  - Non-intrusive design: Only adds new method, no modification to existing code logic
  
- **Usage**:
  ```
  1. Find node to configure on canvas
  2. Double-click that node
  3. System automatically pops up config dialog
  4. Edit config and click "Save Config" button
  5. Config takes effect immediately and syncs to memory data
  ```
  
- **Affected Files**: `ui/canvas_widget.py` - `NodeCanvas` class
- **User Value**: Simplifies config editing workflow, no need for right-click menu or list panel, improves operation efficiency

#### 7. **Node List Multi-Select Batch Delete** 🗑️
- **Feature**: Supports batch deleting nodes after Shift/Ctrl multi-select in node list panel
- **Implementation Details**:
  - **Multi-Select Support**: Hold Shift or Ctrl key to select multiple nodes (existing feature)
  - **Right-Click Menu Enhancement**: When multiple nodes selected, right-click menu shows "🗑️ Delete Selected X Nodes" option
  - **Secondary Confirmation Mechanism**: Shows confirmation dialog before deletion, lists all to-be-deleted node names (shows max 10)
  - **Complete Cleanup Process**:
    - Auto-stops running node processes
    - Deletes node folders and all files
    - Removes references from node groups
    - Deletes from memory data
    - Removes node display from canvas
  - **Detailed Result Feedback**: Shows success/failure statistics, failed nodes listed separately
  - **Toast Notification**: Notifies user through Toast after operation completes
  
- **Technical Implementation**:
  - Added `batch_delete_nodes()` method to handle batch delete logic
  - Added conditional judgment in `_show_node_context_menu()` to show batch delete option when multiple nodes selected
  - Complete exception handling, ensures single node failure doesn't affect others
  - Follows project specification: Provides clear secondary confirmation, prevents misoperations
  
- **Usage**:
  ```
  1. In node list panel, hold Shift or Ctrl key to select multiple nodes
  2. Right-click on any selected node
  3. Select "🗑️ Delete Selected X Nodes"
  4. Confirm delete operation
  5. System automatically completes all node cleanup work
  ```
  
- **Affected Files**: `ui/node_list_panel.py` - `NodeListPanel` class
- **User Value**: Improves node management efficiency, simplifies batch cleanup operations, reduces accidental deletion risk

#### 8. **Window Closing Process Detection and Management** 🛑
- **Feature**: Intelligently detects running nodes when closing app, provides friendly confirmation dialog
- **Implementation Details**:
  - **Auto Detection**: Scans all nodes in `nodes_data`, identifies nodes with 'running' state and active process
  - **Smart Prompt**: Clearly shows running node list (displays max 10, uses ellipsis for excess)
  - **Three-Option Dialog**:
    - **Yes**: Force stop all running nodes and close window (default, ensures safety)
    - **No**: Allow nodes to continue running in background, but close window
    - **Cancel**: Aborts close operation, returns to app to continue using
  - **Cross-Platform Process Termination**:
    - Windows: Graceful termination → CTRL_BREAK_EVENT → forced kill with timeout protection
    - Linux/macOS: Sends SIGTERM to process group → uses SIGKILL when necessary
  - **Robust Error Handling**: Single node failure doesn't affect others; correctly cleans up all process references
  - **UI Sync Update**: Auto-updates node list panel and canvas display after batch operation
  - **User Feedback**: Notifies user of operation result through Toast (how many nodes stopped or running in background)
  
- **Technical Implementation**:
  - Enhanced `BNOSMainWindow.closeEvent()` method, added detection logic
  - Added `_force_stop_all_nodes()` helper method for batch process termination
  - Follows external process management architecture specification
  - Maintains consistency with existing node lifecycle management
  
- **User Workflow**:
  ```
  User clicks window close button (X)
  ↓
  System detects 3 running nodes: Node_A, Node_B, Node_C
  ↓
  Pops up dialog: "Following 3 nodes are running... Please choose operation:"
  ↓
  User chooses:
    • Yes → stops all nodes, closes window
    • No → nodes continue running in background, closes window
    • Cancel → window stays open, user continues working
  ```
  
- **Use Cases**:
  - ✅ **Prevents Accidental Close**: User can cancel when accidentally clicking close
  - ✅ **Background Processing**: Allows long-running tasks to continue execution after closing GUI
  - ✅ **Safe Close**: Ensures clean termination of all processes before exit
  - ✅ **Flexibility**: Three options cover all possible user intentions
  
- **Technical Highlights**:
  - Default selects "Yes", safety-first strategy
  - Correct resource cleanup, prevents zombie processes
  - Exception handling ensures stability even if some processes can't stop
  - Console log provides detailed operation tracking, easier for debugging
  
- **Affected Files**:
  - `ui/main_window.py` - `BNOSMainWindow.closeEvent()` and new `_force_stop_all_nodes()` method
  
- **Code Quality**:
  - Follows project's external process management specification
  - Cross-platform compatible, uses OS-specific strategies
  - Clear separation of concerns (detection logic vs. termination logic)
  - Comprehensive error handling and user feedback
