# BNOS Update Log

> 📖 中文版：[UPDATE_CN.md](UPDATE_CN.md)

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
