# Composite Node System

## Overview

Implemented the composite node feature, allowing multiple nodes on the canvas to be compressed into a single virtual node with unified orchestration and decompression support. This solves BNOS's core pain point of only supporting single-layer orchestration without sub-flow abstraction.

## Core Changes

### 1. Composite Node Core Logic

New `ui/core/composite_node.py` (~600 lines), implementing:

- **Compress**: Multiple node names -> topological sort -> DAG port derivation -> orchestrator script generation -> write to `node_clusters.json`
- **Decompress**: Restore original nodes + delete node group + clean up PID files
- **Run / start_inprocess**: Dynamically `importlib.import_module` each node's main.py in DAG order, chain-execute `process(inputs)`
- **run_id / timestamp**: Generate unique ID and timestamp per run, output to `output.json`
- **Auto-create node group**: Automatically create same-name group in NodeGroupManager with lock on compression

### 2. Canvas Rendering

New `ui/canvas/items/composite_node_item.py` (~190 lines):

- Dashed teal-green border to distinguish from regular nodes
- ⊞ icon identifier (`font-size: 14px`)
- Composite node title display
- Right-click menu: Decompress / Start / Stop / Switch Runtime Mode
- Real-time position persistence to `node_clusters.json` on drag

### 3. Canvas Right-Click Menu

Modified `ui/canvas/mixins/canvas_menus.py`:

- Multi-select right-click menu adds "⊞ Compress to Composite Node" option (showing node count)
- Composite-node-specific right-click menu (decompress confirmation / start / stop / runtime mode switch)

### 4. Action Registration

New `ui/core/actions/node/composite_actions.py`:

- `canvas.compress_to_composite` — compress selected nodes
- `canvas.decompress_composite` — decompress composite node

### 5. Node List Integration

Modified `ui/panels/node_list_dock.py` and `ui/panels/node_list_context.py`:

- Composite node groups display ⊞ icon + teal highlight + 🔒 lock indicator in list
- Composite group specific right-click menu (decompress / start / stop), no rename/delete options

### 6. Project Load/Save Integration

Modified `ui/canvas/canvas_view.py`:

- `restore_composites()` — rebuild all composite nodes from `node_clusters.json` on project open
- Canvas serialization compatible with `CompositeNodeItem`

Modified `ui/canvas_widget.py`:
- Added `CompositeNodeItem` export

## Affected Files

| File | Action | Description |
|------|--------|-------------|
| `ui/core/composite_node.py` | **New** | Core logic |
| `ui/canvas/items/composite_node_item.py` | **New** | Canvas element |
| `ui/core/actions/node/composite_actions.py` | **New** | Action registration |
| `ui/canvas/mixins/canvas_menus.py` | Modified | Menu integration |
| `ui/panels/node_list_dock.py` | Modified | List styles |
| `ui/panels/node_list_context.py` | Modified | List menu |
| `ui/canvas/canvas_view.py` | Modified | Load/restore |
| `ui/canvas_widget.py` | Modified | Export |
