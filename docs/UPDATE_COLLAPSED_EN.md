
# BNOS Changelog (Collapsible)

&gt; 📖 Chinese Version: [UPDATE_COLLAPSED_CN.md](UPDATE_COLLAPSED_CN.md)

---

## Quick Navigation

- 📂 [Full Changelog by Date](./changelogs/)
- 🇺🇸 [English Changelog Index](./changelogs/en/INDEX.md)

---

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-06-07&lt;/h2&gt;&lt;/summary&gt;

### 🔄 Node State Sync and Project Persistence Improvements

#### Fixed Issues

**1. Node State Information Not Updating**
- **Problem**: Canvas node CPU, memory info not updating, inconsistent with resource monitor panel
- **Cause**: Node state retrieval method conflicts, different data sources between node_monitor and resource monitor
- **Fix**:
  - Deprecated ui/core/node_monitor.py
  - Resource monitor panel added node_state_updated signal to forward CPU, memory data
  - Canvas nodes receive data via signal, ensuring consistent data source
- **Modified Files**:
  - ui/panels/resource_monitor.py
  - ui/panels/resource_monitor_dock.py
  - ui/canvas/items/node_item.py

**2. Async Call Causing Late Data Loading**
- **Problem**: Nodes cannot receive data signals from resource monitor after creation
- **Cause**: Signal connection timing issue, resource monitor created after nodes
- **Fix**: Main window added _connect_existing_nodes_to_resource_monitor() method
- **Modified File**: ui/main_window.py

**3. Project Persistence Improvements**
- **Problem**: Need to manually open project after GUI restart
- **Fix**:
  - Record project to app_config.json when opened
  - Auto-load last opened project when GUI starts next time
- **Modified Files**:
  - ui/main_window.py
  - ui/core/project_manager.py

---

[View Full Update](./changelogs/en/2026-06-07/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-06-06&lt;/h2&gt;&lt;/summary&gt;

### 🎨 Toast Notification Visual Effects Complete Fix

#### Problem Description

**Toast Notifications Had Severe Visual Defects**
- **Issue 1: Black Background Flash** - Shows black background first before correct style
- **Issue 2: Abrupt Disappear Animation** - Notifications disappear instantly instead of smooth fade

#### Fix Solution

**Adopted "Outer Transparent Window + Inner Style Container" Double Layer Architecture**
1. Inheritance Adjustment: `QLabel` → `QWidget`
2. Window Attribute Simplification: Only set `WA_TranslucentBackground`
3. Style Container: Set `rgba` background on inner `QLabel`
4. Animation Rebuild: Use `QTimer` to drive `setWindowOpacity()`

### 🔧 Code Robustness Fixes

- Fixed multiple potential null pointer exceptions
- Optimized exception handling logic
- Enhanced code robustness

---

[View Full Update](./changelogs/en/2026-06-06/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-06-05&lt;/h2&gt;&lt;/summary&gt;

### 🔄 Force Delete Node Folder
- Can force delete even if files are in use
- Supports deleting locked node folders

### ⚡ Async Operation Optimization
- **Async Node Deletion** - No GUI blocking
- **Async Node Start/Stop** - No GUI blocking
- **Async Node Mount/Unmount/Refresh** - No GUI blocking

### 🖥️ Drawing Toolbar Shows On Demand
- Toolbar only shows when needed
- Optimized interface layout

### 🌳 Process Tree Termination
- Complete node process tree termination
- Prevents zombie processes

### 🐍 JSON Virtual Environment Startup Support
- Supports virtual environment startup via JSON config
- More flexible node startup method

---

[View Full Update](./changelogs/en/2026-06-05/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-20&lt;/h2&gt;&lt;/summary&gt;

See [2026-05-20 Updates](./changelogs/en/2026-05-20/) for complete content.

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-19&lt;/h2&gt;&lt;/summary&gt;

### 🔧 Critical Fixes and Enhancements

#### 1. **Rust Node Language Detection Fix** 🦀
- **Problem**: Rust nodes displayed "Unknown" instead of "Rust"
- **Solution**: Enhanced language detection, checks both `src/main.rs` and `Cargo.toml`

#### 2. **Node Folder Path Resolution Fix** 📁
- **Problem**: "Open Node Folder" opened wrong directory
- **Solution**: Implemented three-layer path validation and normalization

[View Complete Update](./changelogs/en/2026-05-19/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-18&lt;/h2&gt;&lt;/summary&gt;

### ✨ New Features and Optimizations

#### 1. **Canvas Node Right-Click Menu Enhancement** ⚡
- Dynamic start/stop option on right-click

#### 2. **Node Configuration Dialog All-New Layout** 🎨
- Horizontal layout, direct JSON editing

#### 3. **Node List Drag & Drop and Smart Grouping** 🎯
- Drag nodes between groups, auto-create on overlap

#### 4. **Node List Multi-Select Menu Optimization** 📋
- Batch operations when multi-selected

#### 5. **Canvas Box Selection Optimization** 📦
- Only triggers on blank areas

#### 6. **Canvas Node Double-Click Opens Config** ⚙️
- Double-click node to open config dialog

#### 7. **Node List Multi-Select Batch Delete** 🗑️
- Shift/Ctrl multi-select for batch delete

#### 8. **Window Closing Process Detection** 🛑
- Detects running nodes on close with confirmation

[View Complete Update](./changelogs/en/2026-05-18/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-17&lt;/h2&gt;&lt;/summary&gt;

### ✨ New Features and Optimizations

#### 1. **Enhanced Rust Node Generator** 🔧
- Completely rewritten with self-healing capabilities
- Automatic environment detection and repair
- 10-100x faster than Python equivalent

[View Complete Update](./changelogs/en/2026-05-17/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-08&lt;/h2&gt;&lt;/summary&gt;

### ✨ New Features and Optimizations

#### 1. **VSCode Workspace Integration** 🔧
- Added "Open as VSCode Workspace" button
- Auto-generates .code-workspace file

#### 2. **VSCode Workspace Feature Optimization** ⚡
- Smart VSCode installation detection
- Friendly user interaction

[View Complete Update](./changelogs/en/2026-05-08/)

&lt;/details&gt;

&lt;details&gt;
&lt;summary&gt;&lt;h2&gt;📅 2026-05-07&lt;/h2&gt;&lt;/summary&gt;

### ✨ New Features and Optimizations

#### 1. **Connection Anchor Position Fix** 🔧
- Uses `sceneBoundingRect().center()` for correct connections

#### 2. **Window Topmost Behavior Optimization** 🪟
- Removed unnecessary `WindowStaysOnTopHint` flags

#### 3. **Best Practices Documentation** 📚
- Created knowledge base

[View Complete Update](./changelogs/en/2026-05-07/)

&lt;/details&gt;

---

[View Complete Index](./changelogs/en/INDEX.md)

---

## Usage Instructions

- Click on a date title to expand/collapse updates for that date
- Each date contains a summary of the main updates
- Click "View Full Update" to see detailed update records for that date

---

*Last Updated: 2026-06-07*

