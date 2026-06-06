# 🆕 Recent Updates

## 🆕 Recent Updates (2026-05-19)

### 🔧 Critical Fixes and Enhancements

#### 1. **Rust Node Language Detection Fix** 🦀
- **Problem**: Rust nodes on canvas displayed "Unknown" instead of "Rust"
- **Root Cause**: `detect_language()` method only checked for `main.rs` in root directory, but Rust projects use `src/main.rs` structure
- **Solution**: Enhanced language detection logic, checking both `src/main.rs` and `Cargo.toml` files
- **Technical Implementation**:
  ```python
  # Before: Only check root directory
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
- **Problem**: Clicking "Open Node Folder" opened wrong directory (like Documents folder), not actual node folder
- **Root Cause**: Node paths not properly normalized, may be stored as relative paths, affected by working directory changes
- **Solution**: Implemented three-layer path validation and normalization mechanism

##### **Layer 1: Path Normalization on Node Load** (`ui/main_window.py`)
- **Enhanced `refresh_nodes()` Method**:
  ```python
  # Ensure project path is absolute
  project_path = os.path.abspath(self.current_project_path)
  nodes_dir = os.path.join(project_path, "nodes")
  
  # Normalize each node path
  node_path = os.path.join(nodes_dir, item)
  node_path = os.path.abspath(node_path)  # Convert to absolute path
  node_path = os.path.normpath(node_path)  # Normalize (handles ..\ etc.)
  ```
- **New Features**:
  - ✅ Detailed load log for each node (path, existence state)
  - ✅ Path consistency validation
  - ✅ Auto-correction of inconsistent paths
  - ✅ Shows total number of loaded nodes

##### **Layer 2: Path Validation in Config Dialog** (`ui/property_panel.py`)
- **Enhanced `NodeConfigDialog.open_node_folder()` Method**:
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
  
  # Backup: Get correct path from parent window's nodes_data
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
  - ✅ Auto-detect and correct paths
  - ✅ Backup path recovery from parent window
  - ✅ Comprehensive debug logs (path type, existence, parent directory, etc.)
  - ✅ User-friendly error messages and troubleshooting tips

##### **Layer 3: Path Validation in Node List** (`ui/node_list_panel.py`)
- **Enhanced `NodeListPanel.open_node_folder()` Method**:
  - Same path validation and correction logic as config dialog
  - Backup path recovery from main window's nodes_data
  - Complete debug info output

- **Debug Log Example**:
  ```
  ============================================================
  🔍 [NodeConfigDialog] Opening node folder
  🔍 Node name: node_rust_test
  🔍 Original path: D:\Project\nodes\node_rust_test
  🔍 Final path: D:\Project\nodes\node_rust_test
  🔍 Path exists: True
  🔍 Is directory: True
  🔍 Parent directory: D:\Project\nodes
  🔍 Folder name: node_rust_test
  🔍 Current working directory: D:\Project
  🔍 Expected folder name: node_rust_test
  🔍 Actual folder name: node_rust_test
  🔍 Name matches: True
  ✅ Opened node folder: D:\Project\nodes\node_rust_test
  ============================================================
  ```

- **Before/After Comparison**:
  | Aspect | Before | After |
  |--------|--------|-------|
  | **Path Type** | May be relative | Forced absolute + normalized |
  | **Path Consistency** | May be inconsistent | Auto-validates and corrects |
  | **Error Recovery** | None | Multi-level backup paths |
  | **Debug Info** | None | Detailed console logs |
  | **User Experience** | Opens wrong folder | Always opens correct node folder |

- **Affected Files**:
  - `ui/main_window.py` - `MainWindow.refresh_nodes()` method
  - `ui/property_panel.py` - `NodeConfigDialog.open_node_folder()` method
  - `ui/node_list_panel.py` - `NodeListPanel.open_node_folder()` method
  - `diagnose_rust_node.py` - New Rust node diagnostic tool
  - `RUST_NODE_PATH_FIX.md` - Detailed fix documentation

- **Usage Instructions**:
  1. After starting program, click "Refresh Node List" button
  2. Check console output, confirm all node paths load correctly
  3. Double-click node or right-click → "Edit Config"
  4. Click "📁 Open Node Folder" button
  5. Verify debug logs (lines starting with 🔍) show correct path

- **User Impact**:
  - ✅ All nodes (Python, Rust, Node.js, etc.) now open correct folders
  - ✅ Paths always absolute and normalized, not affected by working directory
  - ✅ Smart error recovery when path missing
  - ✅ Comprehensive debug info for troubleshooting
