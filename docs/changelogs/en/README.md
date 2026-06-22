# BNOS Changelog Index

> Click the triangle on the left to expand the complete log for that version
> 📖 中文版本：[中文版](../cn/README.md)

---

<details open>
<summary><strong>【2026-06-22】V2.0.19 - Vector Outline Filling for Edge Rendering, High DPI Support and Canvas Resolution Customization</strong></summary>

[View Full Update](./2026-06-22/README.md) | [01_Edges](./2026-06-22/01_Edge_Rendering.md) | [02_HighDPI](./2026-06-22/02_HighDPI_Support.md) | [03_Resolution](./2026-06-22/03_Canvas_Resolution.md)

**Main Updates:**
- 01 Edge Rendering: QPainterPathStroker expands line paths into closed outline paths, filled with QBrush (consistent with arrow polygon fill), completely eliminating zoom-in jagged edges
- 02 High DPI Support: Both main process and canvas subprocess enable AA_EnableHighDpiScaling / AA_UseHighDpiPixmaps, ensuring proper rendering on 4K/Retina displays
- 03 Canvas Resolution: New "Rendering" tab in settings dialog, 5 presets (1000-10000) + custom W/H + antialiasing toggle, configuration persisted to app_config.json

</details>

<details>
<summary><strong>【2026-06-20】V2.0.18 - Floating Panel System, Preset Library Refactoring, Translation & UI Unification</strong></summary>

[View Full Update](./2026-06-20/README.md) | [01_Perf](./2026-06-20/01_Performance_Panel_Fix.md) | [02_Debug](./2026-06-20/02_Debug_Panel_Translation.md) | [03_Preset](./2026-06-20/03_Preset_Library_Refactoring.md) | [04_IPC](./2026-06-20/04_IPC_Core_Process.md) | [05_Polling](./2026-06-20/05_Polling_Manager.md) | [06_i18n](./2026-06-20/06_Translation_Key_Revision.md)

**Main Updates:**
- 01 Performance Panel: ChartCanvas custom paint, QPainter/QPainterPath import fix, drag-pause refresh
- 02 Debug Panel: 17 CN/EN translation keys completed (port, mode, action, breakpoints, etc.)
- 03 Preset Library: Deprecated skeleton template system, reuses `.bnos` for complete node packaging, new PresetLibraryDialog
- 04 IPC Core Process: Added node.stop_all (batch stop) and node.detect_running commands
- 05 Polling Manager: CPU-load-adaptive dynamic frequency adjustment (1s/2s/4s)
- 06 Translation Overhaul: 3 mismatch fixes, 29 new keys, 17 deprecated keys removed

</details>

<details>
<summary><strong>【2026-06-18】V2.0.17 - NodeItem Split Refactoring & Mixin Architecture Composition</strong></summary>

[View Full Update](./2026-06-18/README.md)

**Main Updates:**
- NodeItem monolithic class split: `node_item.py` reduced from 846 lines to 227 lines, split into 9 sub-components (rendering, geometry, interaction, status, config, style, parameter panel, etc.), external API fully compatible
- Mixin architecture refactoring: 6 Mixin classes (CanvasConnections / CanvasBatchOps / CanvasMenu / CanvasBoxSelect / CanvasColors / CanvasLayout) fully converted to composition pattern, explicit dependencies via `self.canvas`, eliminating implicit MRO dependencies
- Bug fixes: `NodeCanvas.__init__` explicit initialization of `box_select_rect` / `box_selected_nodes` / `is_connecting` and other state variables; added `_save_color_settings()` / `_load_color_settings()` forwarding APIs; `CanvasLayout` `self` references changed to `self.canvas`
- Complete startup test verification: 11 module imports, 10 composition layer components, 3 key API calls, full flow passed

</details>

<details>
<summary><strong>【2026-06-17】V2.0.16 - Canvas Layout Loading Fix, Auto-Open Project Async Refactoring & Node Add/Remove Persistence</strong></summary>

[View Full Update](./2026-06-17/README.md)

**Main Updates:**
- Canvas layout loading fix: `load_layout` wrapped in `try/finally` to guarantee `setUpdatesEnabled(True)`; added `scene.update()` + `viewport.update()` force refresh; canvas nodes only sourced from `canvas_layout.json`
- Auto-open project async refactoring: `_auto_open_project` switched to `ProjectLoadWorker` Signal pattern, ensuring `nodes_data` populated before canvas creation; added `CanvasHost.remove_canvas_dock_by_path()` to prevent dock residue
- Node add/remove auto-save trigger: `add_node_to_canvas` / `remove_node_from_canvas` now trigger `_save_timer.start(500)` debounced save; fixed subprocess mode parameter mismatch
- Null reference fixes: `_terminal_dock` protected with `hasattr` before initialization; `NodeListDockPanel` now has convenient `refresh()` method

</details>

<details>
<summary><strong>【2026-06-16】V2.0.15 - Performance Optimization Plan</strong></summary>

[View Full Update](./2026-06-16/README.md)

**Main Updates:**
- Rendering layer optimization: SmartViewportUpdate, DeviceCoordinateCache, replaced full scene refresh
- IO async: New `ProjectLoadWorker` background thread for disk scanning and JSON parsing
- Algorithm layer optimization: `load_layout` traversal merge, skip re-scanning disk on project switch
- Background noise reduction: PollingManager frequency lowering, reduce idle CPU usage

</details>

<details>
<summary><strong>【2026-06-15】V2.0.14 - Node Style Unification, Bug Fixes & Portable Virtual Env for Python Nodes</strong></summary>

[View Full Update](./2026-06-15/README.md)

**Main Updates:**
- Node style unification: deleted rectangular/dot styles, unified system to panel mode; anchor coordinate fixed to left/right edge midpoints
- dialog_utils pick Functions UnboundLocalError fix: closure definitions moved forward
- Async project open & canvas layout fix: `project_open` changed to QTimer.singleShot two-phase async loading
- Portable virtual environment for Python nodes: `--copies` venv creation, start.json de-absolute-pathed, `_repair_portable_venv` auto-repairs on import

</details>

<details>
<summary><strong>【2026-06-13】V2.0.13 - Logging System Redesign & History Rollback</strong></summary>

[View Full Update](./2026-06-13/README.md)

**Main Updates:**
- Logging architecture redesign: dual-file (`bnos.log` + `bnos_error.log`), three-layer anti-bloat
- Process management comprehensive fix: `taskkill /F /T` atomic process tree kill, PID-priority detection (10x+ perf), pipe anti-blocking, thread leak fixes
- Photoshop-style history rollback: Command pattern + HistoryManager singleton + HistoryPanel UI
- Resource monitor network download 100% on first load fix
- Node style switch size not updating fix (DeviceCoordinateCache invalidation timing)
- History panel menu entry addition
- Encoding: emoji cleanup + SafeStreamHandler double safeguard

</details>

<details>
<summary><strong>【2026-06-12】V2.0.12 - Main Window Decoupling & Code Quality Enhancement</strong></summary>

[View Full Update](./2026-06-12/README.md)

**Main Updates:**
- ApplicationContext singleton aggregates 11 global services with unified lifecycle management
- Main window reduced from 1500 lines to **499 lines**, split into 7 Mixin modules (State, Lifecycle, Actions, Panel, IPC, Node Control, Interaction)
- Testing framework with 9 test files and 28+ unit test cases
- i18n string key standardization using `{domain}.{object}.{action}` naming convention
- Code quality improvements: type annotations, code deduplication, enhanced error handling
- Cross-platform support: Windows/macOS/Linux
- Fixed Unicode encoding, permission checking, path validation issues

</details>

<details>
<summary><strong>【2026-06-11】V2.0.11 - Edge Anchor Port Binding Protection & canvas_layout Anti-Corruption</strong></summary>

[View Full Update](./2026-06-11/README.md)

**Main Updates:**
- EdgeItem adds desired port name fields (_desired_target_port_name), enabling correct anchor lookup after reconstruction
- Skip edges when specified port anchor missing (no fallback to default), canvas_layout.json no longer silently rewritten
- _validate_edge_anchor_binding uses desired port name priority over current (possibly wrong) anchor port name
- Manual edge creation also passes port name args, ensuring end-to-end consistency

</details>

<details>
<summary><strong>【2026-06-10】V2.0.10 - IDE Auto-Detection & Adaptive Node View & Multi-Anchor Refinement</strong></summary>

[View Full Update](./2026-06-10/README.md)

**Main Updates:**
- IDEScanner auto-scanner, cross-platform VSCode / Trae IDE detection
- Third node style "Panel" (ComfyUI-style), 11 parameter widget types
- Multi-input port support (prompt / context etc.), distributed on node left side
- Port mapping correction (default → listen_upper_file), edge persistence no longer lost

</details>

<details>
<summary><strong>【2026-06-09】V2.0.9 - CanvasHost Splitter Position Persistence Fix</strong></summary>

[View Full Update](./2026-06-09/README.md)

**Main Updates:**
- CanvasHost window splitter position persistence
- Support restoring splitter position when auto/manual opening project
- Dual save mechanism ensures correctness

</details>

<details>
<summary><strong>【2026-06-08】V2.0.8 - Drawing Tool Display State Persistence</strong></summary>

[View Full Update](./2026-06-08/README.md)

**Main Updates:**
- Drawing toolbar display state persistence
- Fixed two consecutive operations issue
- Configuration file integration

</details>

<details>
<summary><strong>【2026-06-07】V2.0.7 - Toast Queue Management & Action System Unification</strong></summary>

[View Full Update - Part 1](./2026-06-07/01_Node_State_Sync_and_Project_Persistence_Improveme.md)  
[View Full Update - Part 2](./2026-06-07/02_Toast_Queue_Management_and_Action_System.md)

**Main Updates:**
- Toast notification queue management with smart replacement
- Unified action registry system (ActionRegistry/ActionFactory)
- Async node startup with immediate feedback
- Secondary windows unified as floating panels
- Thread lifecycle management fixes

</details>

<details>
<summary><strong>【2026-06-06】V2.0.6 - Toast Notification Visual Effects Complete Fix</strong></summary>

[View Full Update](./2026-06-06/README.md)

**Main Updates:**
- Toast notification visual defects fix
- Code robustness fixes

</details>

<details>
<summary><strong>【2026-06-05】V2.0.5 - Multiple Async Optimizations & Feature Enhancements</strong></summary>

[View Full Update](./2026-06-05/README.md)

**Main Updates:**
- Force delete node folder
- Multiple async operation optimizations
- Drawing toolbar on-demand display
- Process tree termination mechanism
- JSON launch virtual environment support

</details>

<details>
<summary><strong>【2026-05-23】V2.0.4 - Multiple Architecture & UI Improvements</strong></summary>

[View Full Update](./2026-05-23/README.md)

**Main Updates:**
- Splash screen, brand renaming
- Standalone launcher, 3-state indicator lights
- Unified polling manager
- VS Code Codicon icon system integration

</details>

<details>
<summary><strong>【2026-05-22】V2.0.3 - Connection & Node Management Improvements</strong></summary>

[View Full Update](./2026-05-22/README.md)

**Main Updates:**
- ComfyUI-style connection refactoring
- Manual fold interaction
- Node registry, external node mounting

</details>

<details>
<summary><strong>【2026-05-21】V2.0.2 - Major Architecture Refactoring</strong></summary>

[View Full Update](./2026-05-21/README.md)

**Main Updates:**
- Major architecture refactoring, UI component modularization
- Menu bar integration
- VSCode-style dark frameless window
- Node style system
- Canvas viewport rendering optimization

</details>

<details>
<summary><strong>【2026-05-20】V2.0.1 - Canvas Widget Modular Split</strong></summary>

[View Full Update](./2026-05-20/README.md)

**Main Updates:**
- Canvas Widget modular split

</details>

<details>
<summary><strong>【2026-05-19】V2.0.0 - Rust Node & Path Resolution Fixes</strong></summary>

[View Full Update](./2026-05-19/README.md)

**Main Updates:**
- Rust node language detection fix
- Node folder path resolution fix

</details>

<details>
<summary><strong>【2026-05-18】V1.9.0 - Node Management & Configuration Improvements</strong></summary>

[View Full Update](./2026-05-18/README.md)

**Main Updates:**
- Canvas node right-click menu enhancement
- Node config dialog all-new layout
- Node list drag & drop and smart grouping
- Multiple batch operation features

</details>

<details>
<summary><strong>【2026-05-17】V1.8.0 - Rust Node Generator</strong></summary>

[View Full Update](./2026-05-17/README.md)

**Main Updates:**
- Enhanced Rust node generator
- Self-healing capability, performance optimization

</details>

<details>
<summary><strong>【2026-05-08】V1.7.0 - VSCode Workspace Integration</strong></summary>

[View Full Update](./2026-05-08/README.md)

**Main Updates:**
- VSCode workspace integration
- VSCode workspace feature optimization

</details>

<details>
<summary><strong>【2026-05-07】V1.6.0 - Connection & Window Behavior Fixes</strong></summary>

[View Full Update](./2026-05-07/README.md)

**Main Updates:**
- Connection anchor position fix
- Window topmost behavior optimization
- Best practices documentation

</details>

---

## Quick Navigation

- [Browse by Date](INDEX.md)
- [Back to Project Root](../../README.md)

---

### Architecture Description

This changelog uses a **"Single Index Page + Version-Separate MD Sub-Files"** architecture:
- **Index Page**: This file, responsible for navigation, folding, and linking
- **Date-Separate Folders**: All detailed content organized by date
- **Full Decoupling**: New versions only require adding files to the corresponding date folder, no need to modify old code

### Usage Instructions

1. Click the triangle on the left of the date to expand/collapse the version summary
2. Click the "View Full Update" link to enter the detailed update page for that date
3. Each date folder contains all update entries for that date, supporting independent browsing and archiving
