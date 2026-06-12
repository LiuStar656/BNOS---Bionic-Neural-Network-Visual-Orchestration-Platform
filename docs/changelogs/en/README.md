# BNOS Changelog Index

> Click the triangle on the left to expand the complete log for that version
> 📖 中文版本：[中文版](../cn/README.md)

---

<details open>
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
