# 2026-07-13 Update Overview

[Back to Index](../README.md)

---

## Update Catalog

- [01 Composite Node Context Menu Optimization & Input Anchor Exclusive Detection](#01-composite-node-context-menu-optimization--input-anchor-exclusive-detection)
- [02 Composite Node Collapse DAG Topology Update Fix](#02-composite-node-collapse-dag-topology-update-fix)
- [03 Composite Node Expand Coordinate and Edge Fix](#03-composite-node-expand-coordinate-and-edge-fix)
- [04 Node Running State Protection](./04_Node_Running_State_Protection.md)
- [05 Composite Node UI Refactoring & Custom Interface Support](./05_Composite_Node_UI_Refactoring_and_Custom_Interface.md)
- [06 Composite Node Startup Queue Integration](./06_Composite_Node_Startup_Queue_Integration.md)
- [07 Composite Node Rename Feature](./07_Composite_Node_Rename_Feature.md)
- [08 Anchor Manager Multi-Output Port Support](./08_Anchor_Manager_Multi_Output_Port_Support.md)
- [09 DAG Run Status Tracking](./09_DAG_Run_Status_Tracking.md)
- [10 Node Multi-Selection Fix](./10_Node_Multi_Selection_Fix.md)
- [11 Composite Node Startup Queue Fix](./11_Composite_Node_Startup_Queue_Fix.md)
- [12 Multi-Selection Context Menu Optimization](./12_Multi_Selection_Context_Menu_Optimization.md)
- [13 Node Detail Panel Merge and Composite Node Config Window Fix](./13_Node_Detail_Panel_Merge_and_Composite_Node_Config_Window_Fix.md)

---

## 01 Composite Node Context Menu Optimization & Input Anchor Exclusive Detection

See [01_Composite_Node_Context_Menu_and_Input_Anchor_Detection.md](./01_Composite_Node_Context_Menu_and_Input_Anchor_Detection.md).

### Summary

- **Start/Stop mutual exclusion**: Based on `is_running()`, only one of Start or Stop is shown at a time
- **Decompose moved to bottom**: Grayed out with tooltip when running
- **Expand/Collapse running check**: Grayed out with tooltip, additional dialog guard on click
- **Input anchor exclusive detection**: One input anchor can only connect to one output anchor; rejects duplicate connections via `target_anchor.edges` check

---

## 02 Composite Node Collapse DAG Topology Update Fix

See [02_Composite_Node_Collapse_DAG_Topology_Fix.md](./02_Composite_Node_Collapse_DAG_Topology_Fix.md).

### Summary

- **Root cause**: `internal_edge_info` during collapse only saved to memory `comp["_internal_edges"]`; `composite.json` edges were never updated, causing `pipeline.json` to use stale topology
- **Fix**: Immediately sync edges to `composite.json` during collapse (`src→from / tgt→to` format mapping); `_sync_pipeline` now called unconditionally
- **Effect**: After expanding, re-wiring sub-node order, and re-collapsing, the new DAG topology takes effect correctly (e.g., +1 then ×3 vs ×3 then +1)

---

## 03 Composite Node Expand Coordinate and Edge Fix

See [03_Composite_Node_Expand_Coordinate_and_Edge_Fix.md](./03_Composite_Node_Expand_Coordinate_and_Edge_Fix.md).

### Summary

- **Coordinate offset fix**: Use current position `comp_item.pos()` instead of saved stale `canvas_position` when expanding
- **Port name mapping**: Added `"data"` → `"default"` mapping to resolve mismatch between default input anchor name and port identification name
- **Layout save/load filtering**: Skip internal nodes of collapsed composites to prevent old coordinates from causing offsets
- **Execution order adjustment**: Position child nodes first, then create edges, ensuring edge endpoints use correct positions

---

## 04 Node Running State Protection

### Summary

- **Rename protection**: Running nodes cannot be renamed, toast notification shown
- **Delete protection**: Confirmation dialog shown when deleting nodes that include running ones

### Modified Files

| File | Change |
|------|--------|
| `ui/panels/node_list_panel.py` | Running state check before rename; dialog confirmation before deleting running nodes |
| `ui/core/node/node_process.py` | Added `check_node_not_running()` utility function |

---

## 05 Composite Node UI Refactoring & Custom Interface Support

### Summary

- **Reuse regular node components**: Uses `NodeRendering`, `AnchorManager`, `NodeSubComponents`, `NodeParamPanel` for consistent UI
- **Hide redundant elements**: IN/OUT labels and expand button hidden, status indicators preserved
- **Filter system ports**: Filters system-generated ports (e.g., `_out` suffix), only shows custom ports
- **Fix missing attributes**: Explicitly calls `build_text_labels()` to create `name_text` attribute
- **Add composite marker**: Green dot in top-left corner identifies composite nodes

### Modified Files

| File | Change |
|------|--------|
| `ui/canvas/items/composite_node_item.py` | Refactored to reuse regular node components; hide redundant elements; add green dot marker |

---

## 06 Composite Node Startup Queue Integration

### Summary

- **Startup queue support**: Composite nodes now enter the startup queue like regular nodes
- **Auto type detection**: `NodeStartWorker.run()` automatically selects startup method based on `composite_` prefix
- **New startup method**: `_start_composite()` starts composite nodes via `CompositeNodeManager`

### Modified Files

| File | Change |
|------|--------|
| `ui/core/node/node_startup_queue.py` | Added `_start_composite()` method; `run()` auto-detects node type |

---

## 07 Composite Node Rename Feature

### Summary

- **Node list context menu**: Added "Rename Composite Node" option
- **Running state protection**: Running composite nodes cannot be renamed
- **Display name editing**: Edit `display_name` via input dialog; empty restores hex ID display

### Modified Files

| File | Change |
|------|--------|
| `ui/panels/node_list_context.py` | Added `_rename_composite_group()` method; rename option in context menu |

---

## 08 Anchor Manager Multi-Output Port Support

### Summary

- **Multi-output port mode**: Prioritizes `output_ports` configured multiple output ports
- **Position calculation**: Uses `row_positions` positions first, otherwise vertically distributed
- **Fallback mechanism**: Falls back to single default output anchor when no multi-output config

### Modified Files

| File | Change |
|------|--------|
| `ui/canvas/items/anchor_manager.py` | Rewrote output anchor generation logic to support multi-output ports |

---

## 09 DAG Run Status Tracking

### Summary

- **Per-node status tracking**: `DagRunner` records each child node's execution status (ok/fail/pending), error info, and duration
- **Status persistence**: Writes to `status.json` after execution for BNOS monitoring
- **Parallel execution tracking**: Failures in parallel nodes are also recorded

### Modified Files

| File | Change |
|------|--------|
| `ui/core/node/composite_orchestrator.py` | Added `_node_status` tracking; added `_write_status()` method |

---

## 10 Node Multi-Selection Fix

See [10_Node_Multi_Selection_Fix.md](./10_Node_Multi_Selection_Fix.md).

### Summary

- **Root cause**: Qt's `QGraphicsScene` default selection mode is `SingleSelection`, which automatically deselects other nodes when calling `setSelected(True)`
- **Fix**: Use custom selection flag `_is_custom_selected` to completely bypass Qt's selection mode
- **Modified files**: `rendering.py`, `canvas_selection.py`, `canvas_view.py`, `selection_tool.py`

---

## 11 Composite Node Startup Queue Fix

See [11_Composite_Node_Startup_Queue_Fix.md](./11_Composite_Node_Startup_Queue_Fix.md).

### Summary

- **Root cause**: `_composite_start` directly called `mgr.start_inprocess()` without going through the startup queue
- **Fix**: Route through startup queue with toast notification; modify `start_selected_node_by_name` and `stop_selected_node_by_name` to support composite nodes
- **Modified files**: `canvas_menus.py`, `node_list_context.py`, `main_window/node.py`, `composite_node_item.py`

---

## 12 Multi-Selection Context Menu Optimization

See [12_Multi_Selection_Context_Menu_Optimization.md](./12_Multi_Selection_Context_Menu_Optimization.md).

### Summary

- **Selection count fix**: Fixed `SelectedNodesList._sync` to include composite nodes
- **Dynamic menu adjustment**: Hide "Batch Remove" and "Compress to Composite" when composite nodes are selected
- **Start/Stop support**: Modified `start_selected_node_by_name` and `stop_selected_node_by_name` to support composite nodes
- **New menu option**: Clear Selection

---

## 13 Node Detail Panel Merge and Composite Node Config Window Fix

See [13_Node_Detail_Panel_Merge_and_Composite_Node_Config_Window_Fix.md](./13_Node_Detail_Panel_Merge_and_Composite_Node_Config_Window_Fix.md).

### Summary

- **Window merge**: Merged "Expand Node" and "Node Config" windows into a unified node detail panel
- **Composite node config window fix**: Fixed indentation error and project path attribute name to make config window display correctly
- **Composite node restart expand fix**: `save_layout` now saves all nodes (including internal) with `is_internal` flag; `load_layout` restores internal nodes and keeps them hidden
- **Anti-concurrency protection**: Start/stop buttons now have `_operation_in_progress` flag to prevent signal conflicts
- **Internationalization support**: Added translation keys and texts for node detail panel
- **Menu optimization**: Removed duplicate "Expand Node" option from regular node right-click menu

---

## Modified Files

| File | Change |
|------|--------|
| `ui/canvas/mixins/canvas_menus.py` | Rewrote `_show_composite_node_menu`; added `_on_toggle_expand`; `_composite_start` via startup queue; `_show_multi_node_menu` dynamic adjustment; removed duplicate "Expand Node" option |
| `ui/canvas/mixins/canvas_connections.py` | Added input anchor exclusive detection in `create_edge` |
| `ui/core/node/composite_node.py` | Added DAG topology sync logic; expand coordinate fix; port name mapping; execution order adjustment; fault-tolerant handling for missing nodes |
| `ui/canvas/mixins/canvas_layout.py` | Save/load includes internal nodes with `is_internal` flag; internal nodes kept hidden |
| `ui/panels/node_list_panel.py` | Rename/delete running state protection |
| `ui/core/node/node_process.py` | Added `check_node_not_running()` |
| `ui/canvas/items/composite_node_item.py` | UI refactoring, reuse regular node components; added `update_status` method |
| `ui/core/node/node_startup_queue.py` | Composite node startup queue integration; added `_start_composite()` |
| `ui/panels/node_list_context.py` | Composite node rename feature; `_start_composite_group` via startup queue |
| `ui/canvas/items/anchor_manager.py` | Multi-output port support |
| `ui/core/node/composite_orchestrator.py` | DAG run status tracking |
| `ui/core/node/node_config_parser.py` | Input port name validation |
| `ui/canvas/items/node_components/rendering.py` | Use custom selection flag |
| `ui/canvas/mixins/canvas_selection.py` | Multi-selection logic using custom selection flag |
| `ui/canvas/canvas_view.py` | `SelectedNodesList` sync custom selection state; include composite nodes |
| `ui/canvas/drawing/tools/selection_tool.py` | Clear custom selection state on blank click |
| `ui/main_window/node.py` | `start_selected_node_by_name` and `stop_selected_node_by_name` support composite nodes |
| `ui/dialogs/node_detail_panel.py` | Window merge; fixed indentation error; added exception handling |
| `ui/dialogs/node_data_provider.py` | Fixed project path attribute name; new CompositeNodeProvider |
| `ui/dialogs/json_sync_editor.py` | New: Bidirectional sync JSON editor |
| `ui/dialogs/log_viewer_widget.py` | New: Log viewer widget |
| `ui/dialogs/node_control_widget.py` | New: Node control widget (with anti-concurrency protection) |
| `ui/canvas/mixins/canvas_node_manager.py` | Sync update composite when deleting nodes |
| `ui/core/i18n/strings_cn.json` | Added node detail panel translations |
| `ui/core/i18n/strings_en.json` | Added node detail panel translations |
| `ui/core/i18n/translation_keys.py` | Added new translation key constants |

---

**Last Updated**: 2026-07-13
