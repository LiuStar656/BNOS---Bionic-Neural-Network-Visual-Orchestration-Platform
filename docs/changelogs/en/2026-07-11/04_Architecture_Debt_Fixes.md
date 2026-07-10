# Architecture Debt Fixes

## Overview

Systematic fixes for architecture-level technical debt, including eliminating dual selection state, fixing lazy imports, removing unreliable destructors, and fixing node scanning logic and process cleanup issues.

## Core Changes

### 1. P0-1: Eliminate Dual Selection State

**Problem**: `box_selected_nodes` (Python list) and `QGraphicsItem.isSelected()` (Qt C++) were two independent state sources. Every selection operation required manual synchronization between both lists, leading to the Ctrl+click toggle bug.

**Solution**: Instead of removing `box_selected_nodes`, transform it from independent state storage into a **projection of Qt's selection** — using a proxy class `SelectedNodesList` that delegates all read/write to `QGraphicsScene.selectedItems()`.

Modified `ui/canvas/canvas_view.py`:

- **Added `SelectedNodesList` proxy class** (65 lines): Implements `__iter__` / `__len__` / `__contains__` / `__getitem__` / `__bool__` / `append` / `remove` / `clear`, all delegated to `scene.selectedItems()`, maintaining full backward compatibility with the original list interface
- `self.box_selected_nodes = []` → `SelectedNodesList(self)`
- Promoted `CompositeNodeItem` / `CompositeNode` lazy imports to module-level

Modified `ui/canvas/mixins/canvas_selection.py`:

- `on_node_selected()`: Uses `scene.clearSelection()` + `node.setSelected(True)` instead of manual list manipulation
- `_toggle_node_selection()`: Checks `node.isSelected()` instead of `node_name in box_selected_nodes`
- `clear_selection()`: Calls `scene.clearSelection()`

Modified `ui/canvas/mixins/canvas_box_select.py`:

- `self.canvas.box_selected_nodes = []` → `.clear()` (direct assignment would replace the proxy object, causing a severe bug)

Modified `ui/canvas/mixins/canvas_event_handlers.py`:

- Box-select logic: Uses `scene.clearSelection()` + `setSelected(True/False)` instead of manual `.append()` loop

Modified `ui/canvas/mixins/canvas_batch_ops.py`:

- `self.canvas.selection.box_selected_nodes` → `self.canvas.box_selected_nodes` (fixed path)

### 2. P1-1: Fix CompositeNode Lazy Imports

**Problem**: `CompositeNode` was lazily imported inside method bodies across multiple files, causing duplicate imports and unnecessary runtime overhead.

Modified `ui/panels/node_list_context.py`:

- Removed duplicate `from ui.core.composite_node import CompositeNode` inside `_ensure_composite_manager()` (already imported at module level)

Modified `ui/canvas/canvas_view.py`:

- Promoted `CompositeNodeItem` / `CompositeNode` from lazy imports in `restore_composites()` to module-level imports

### 3. P1-2: Eliminate `__del__` Process Cleanup

**Problem**: `TerminalProcess.__del__` relied on Python GC's non-deterministic destructor to terminate child processes, which is unreliable in Qt environments. C++ objects may already be destroyed when Python GC runs.

Modified `ui/core/terminal/terminal_process.py`:

- `__del__` → `dispose()` explicit cleanup method, calls `stop()` + `deleteLater()`
- Caller explicitly calls `dispose()` in `TerminalWidget.close_terminal()`

Modified `ui/core/terminal/terminal_widget.py`:

- `close_terminal()` changed from `self.process.stop()` to `self.process.dispose()`

### 4. Bug Fix: Directories Without config.json Loaded as Nodes

**Problem**: Folders under `nodes/` without `config.json` were still loaded as nodes in the node list. Future subdirectories placed in `nodes/` for other purposes would also be misidentified as nodes.

**Root Cause**: Both node scanning paths (`project_load_worker.py` and `core_process.py`) only filtered out non-directories without checking for `config.json` existence. Missing config would either generate a synthetic default (GUI) or use empty config (headless), neither rejecting the directory.

Modified `ui/core/project_load_worker.py`:

- Added `config.json` existence check after `is_dir` check, skipping directory with `continue` if missing
- Removed synthetic default config branch (no longer fakes config for directories without `config.json`)

Modified `ui/core/core_process.py`:

- Added `config.json` existence check after `is_dir` check, skipping directory with `continue` if missing
- Also skips with `continue` on config.json parse failure

### 5. Bug Fix: QProcess Destroyed While Running

**Problem**: When closing the application, the terminal widget's `closeEvent` could be skipped during parent widget cascade destruction, causing `QProcess` to be destroyed while powershell.exe was still running, triggering a Qt warning.

**Root Cause**: `closeEvent()` is only triggered when the widget is closed via user action. Cascade destruction of child widgets during full window close does not guarantee `closeEvent()` is called.

Modified `ui/core/terminal/terminal_widget.py`:

- Added `self.destroyed.connect(self.close_terminal)` in `__init__`, using Qt's `destroyed` signal (emitted synchronously at QObject destruction start) as a safety net
- `_is_closing` guard prevents duplicate cleanup
