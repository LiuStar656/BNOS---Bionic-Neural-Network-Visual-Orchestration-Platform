# BNOS Changelog

📖 Chinese Version: [INDEX.md](../cn/INDEX.md)

---

## Changelog Index

Click on dates below to view detailed updates for that date:

### [2026-06-18](./2026-06-18/)
- **NodeItem Monolithic Class Split into Composition Pattern**: `node_item.py` reduced from 846 lines to 227 lines, split into 9 sub-components (rendering, geometry, interaction, status, config, style, parameter panel, etc.)
- **6 Mixin Classes Converted to Composition Pattern**: `CanvasConnections` / `CanvasBatchOps` / `CanvasMenu` / `CanvasBoxSelect` / `CanvasColors` / `CanvasLayout` — explicit dependencies via `self.canvas`, eliminating implicit MRO dependencies
- **Node Startup Queue Feature Implementation**: Smart scheduler with concurrency control, priority scheduling, error retry, startup interval control, queue persistence (currently for rate limiting only)
- **Node Startup Queue and Batch Stop Fixes**: Fixed 10 issues including right-click menu no response, `box_selected_nodes` attribute reference error, batch stop only stopping one node, unable to restart after stopping, second batch start invalid, etc.
- **Complete Startup Test Validation**: All module imports / instantiations / API calls / complete application startup flow passed

### [2026-06-17](./2026-06-17/)
- **Canvas Layout Loading Fix**: `load_layout` now wrapped in `try/finally` to guarantee `setUpdatesEnabled(True)`; added `scene.update()` + `viewport.update()` force refresh; canvas nodes only sourced from `canvas_layout.json`
- **Auto-Open Project Async Refactoring**: `_auto_open_project` switched to `ProjectLoadWorker` Signal pattern ensuring `nodes_data` populated before canvas creation; added `CanvasHost.remove_canvas_dock_by_path()` to prevent dock residue
- **Node Add/Remove Auto-Save**: `add_node_to_canvas` / `remove_node_from_canvas` now trigger `_save_timer.start(500)` debounced save; fixed subprocess mode parameter mismatch

### [2026-06-16](./2026-06-16/)
- **Performance Optimization Plan**: Rendering layer (SmartViewportUpdate, DeviceCoordinateCache), IO async (ProjectLoadWorker), algorithm layer (load_layout merge traversal), background noise reduction (PollingManager frequency lowering) four-phase optimization plan

### [2026-06-15](./2026-06-15/)
- **Node Style Unification**: Deleted rectangular/dot styles, unified system to panel mode, DetailedNodeStyle now inherits NodeStyle base class directly
- **Anchor Coordinate Fixes**: Input/output anchor fallback positions changed to left/right edge midpoints, fixed setPos/_find_nearest double-offset bug
- **Process Lifecycle Protection**: RuntimeError guard for already-destroyed QProcess during TerminalProcess destruction
- **dialog_utils pick Functions UnboundLocalError Fix**: `go_up` / `sel_path` closure definitions moved forward, fixing crashes when opening/importing/exporting projects and nodes
- **Async Project Open & Canvas Layout Fix**: `project_open` changed to QTimer.singleShot two-phase async loading; fixed second project canvas empty node issue (canvas_host.py signal firing order)
- **Portable Virtual Environment for Python Nodes**: `--copies` venv creation, start.json de-absolute-pathed, `_repair_portable_venv` auto-repairs pyvenv.cfg on import, bytecode cache skipped during packaging; no `pip install` needed after cross-machine migration

### [2026-06-14](./2026-06-14/)
- **PyQt6 → PySide6 Full-Stack Migration**: License upgrade GPLv3 → LGPLv3, 100 source files with 233 import replacements, signal/slot syntax adaptation (pyqtSignal→Signal, pyqtSlot→Slot), zero business logic changes

### [2026-06-13](./2026-06-13/)
- **Logging System Architecture Redesign**: Dual-file separation (`bnos.log` daily rotation + `bnos_error.log` size rotation), three-layer anti-bloat filters, ERROR/CRITICAL never filtered with independent storage
- **PollingManager Fix**: Fixed QObject C++ layer init crash (`super().__init__()` ordering issue)
- **Panel Loading Order Optimization**: CanvasHost loads canvas panels before terminal, reducing startup flicker
- **Emoji Cleanup**: Full replacement with `[TAG]` labels, eliminating Windows GBK encoding errors
- **Process Management Comprehensive Fix**: `taskkill /F /T` atomic process tree kill, PID-priority detection (10x+), pipe anti-blocking, thread leak fixes
- **Photoshop-Style History Rollback**: Command pattern + HistoryManager singleton + HistoryPanel UI with click-to-jump
- **Resource Monitor and Other Bug Fixes**: Network download 100% on startup, node style switch size not updating, history panel menu entry

### [2026-06-12](./2026-06-12/)
- **P2 Optimization: Main Window Further Decoupling**: Reduced main window file from ~1500 lines to **499 lines**, added 4 new Mixin modules (Panel Management, IPC Communication, Node Control, Window Interaction) for fine-grained responsibility separation
- **Bug Fixes**: Fixed 5 issues including Unicode encoding, permission checking, path validation
- **Code Quality Improvements**: Added type annotations, code deduplication, cross-platform support (Windows/macOS/Linux)

### [2026-06-11](./2026-06-11/)
- **Edge Anchor Port Binding Protection & canvas_layout Anti-Corruption**: Fixed edge port anchor loss after restart, introduced "Desired Port Name Memory" mechanism and "Anchor-Missing No-Degradation" protection

### [2026-06-10](./2026-06-10/)
- **Phase 10**: IDE Auto Detection + Right-Click Menu Action Integration (cross-platform VSCode / Trae IDE detection, non-standard path recognition)
- **Phase 12**: Adaptive Node View (ComfyUI-Style Panel Mode), 11 parameter widget types, rendered directly on canvas with real-time config.json sync
- **Multi-Anchor Refinement**: Anchor differentiation (16px/10px), port mapping correction, edge persistence, batch cleanup

### [2026-06-09](./2026-06-09/)
- **CanvasHost Splitter Position Persistence**: Save divider positions between the left node panel and right debug panel to app_config
- **Architecture Decoupling & Function Unification**: Right-click menu functions migrated to Action system, separating UI components from business logic

### [2026-06-08](./2026-06-08/)
- **Drawing Tool State Persistence**: Save brush/eraser selection state to project configuration

### [2026-06-07](./2026-06-07/)
- **Node State Sync & Project Persistence**: Node start/stop state, configuration write-back and restore
- **Toast Notification Queue & Action System Extension**: Unified notification queue management

### [2026-06-06](./2026-06-06/)
- **Toast Notification Visual Fixes**: Notification bubble styling, animation, positioning
- **Code Robustness Fixes**: Null value / exception handling improvements across multiple areas

### [2026-06-05](./2026-06-05/)
- **Force Delete Node Folders**: Node directory cleanup
- **Async Start/Stop/Mount/Refresh Nodes**: Non-blocking GUI interaction
- **Node Config Menu Remains Open After Launch**
- **Drawing Toolbar On-Demand Display**
- **Process Tree Termination Mechanism**
- **JSON-Based Launch Virtual Environment Support**
- **Node Status Display & Process Detection Fixes**

### [2026-05-23](./2026-05-23/)
- **Global State Sync Refactor**: Unified polling manager, resource monitoring refactor
- **Canvas Layout Loading Enhancements**
- **Panel State Persistence**
- **Sidebar Toolbar Size Increase & Icon Fixes**
- **VS Code Codicon Icon System Integration**
- **Independent Launcher, 3-State Status Lights, Ctrl+D Delete**
- **Splash Screen, Brand Rename (BnosConsole → BNOS), README Refactor**

### [2026-05-22](./2026-05-22/)
- **ComfyUI-Style Connection Line Refactor + Manual Fold**：Bezier curves, node collapse/expand
- **Node Registry + External Node Mount**：Extensible node management system

### [2026-05-21](./2026-05-21/)
- **GUI Architecture Refactor & Feature Enhancements**: QGraphicsView/Scene foundation
- **Node Style System**: Square / Circle style switching
- **Canvas Viewport Rendering Optimization**
- **VSCode-Style Dark Frameless Window**
- **Four Major Plans Implemented**
- **UI Simplification & Optimization**
- **Major Architecture Refactor: UI Component Modularization & Menu Bar Integration**

### [2026-05-20](./2026-05-20/)
- **Canvas Widget Modular Split**: Canvas components split into separate modules by responsibility

### [2026-05-19](./2026-05-19/)
- Early feature & UI iterations

### [2026-05-18](./2026-05-18/)
- Basic features & node management

### [2026-05-17](./2026-05-17/)
- Early project version iterations

### [2026-05-08](./2026-05-08/)
- Early project version iterations

### [2026-05-07](./2026-05-07/)
- Early project version iterations

---

**Last Updated**: 2026-06-18