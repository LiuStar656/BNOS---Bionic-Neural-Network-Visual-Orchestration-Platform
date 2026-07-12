# Composite Node UI Interaction & Edge System Round 2 Fixes

[Back to Update Overview](./README.md)

---

## Right-Click Menu Expand/Collapse

- `canvas_menus.py`: Added "Expand"/"Collapse" menu items to `_show_composite_node_menu`, replacing double-click expand
- Fixed canvas-level `contextMenuEvent` intercepting CompositeNodeItem events, causing missing right-click menu

## Composite Output Anchor Edge Creation

- `composite_node_item.py`: Added `output_anchor` / `input_anchor` / `node_name` properties, enabling the edge system to recognize composite node anchors
- `canvas_connections.py`: `create_edge` now handles composite-involved edges via `_update_composite_config_edge` writing `out_connections` on both sides
- `remove_edge`: Added `_clean_target_config` / `_clean_source_out_connections` helpers for composite target config cleanup

## Expanded State UI Interaction Fix

- `composite_group_frame.py`: Overrode `shape()` to cover only the collapse button area, preventing the default full-rect response region from eating mouse events meant for internal nodes and anchors

## Edge Residue Cleanup After Collapse

- `compress()` / `decompress()`: Hide internal edges during compression, track in `_internal_edges`, restore on decompression
- `_handle_line_visibility_on_collapse/expand`: Multi-composite safety — check if edge endpoints belong to another expanded composite before restoring, preventing false restoration

## Composite Edge config.json Synchronization

- Full config.json re-alignment on every expand/collapse cycle:
  - `_sync_configs_for_expand`: Scans canvas edges + reads `_port_routing`, writes `listen_upper_file` and `out_connections` to internal nodes
  - `_sync_configs_for_collapse`: Reads from internal nodes, writes back to `_port_routing` and clears internal config
- Port identification `_identify_ports`: Changed from pure DAG edge detection to also checking `config.json`'s `listen_upper_file` and `out_connections`

## Edge Anchor Invalidation Fix After Collapse

- `_refresh_ports_on_collapse`: `update_ports()` destroys old anchors, but existing edges still hold old anchor references → invalid
- Fix: Save composite-connected edges → refresh ports → rebind edges to new anchors (via `find_anchor_by_port`); stale edges that fail rebinding are removed

## Internal Node Drag Fluttering Fix

- `canvas_event_handlers.py`: New `_prepare_composite_drag_anchor` (presets anchors in `mousePressEvent`) and `_clear_composite_drag_anchors`
- `_sync_composite_group_movement` rewritten: Updates anchor positions every frame; only the actually-dragged node has a position delta, eliminating the feedback loop where non-dragged nodes were misidentified as "moved"
- Group frame `composite_group_frame.py` now synchronizes movement with internal nodes

## PermissionError Save Retry

- `composite_node.py` `save()` method: Added `_saving` re-entrant lock + 3 retries (0.1s→0.2s→0.3s delays) + delete-then-rename fallback, resolving Windows file lock conflicts

## Other Fixes

- `SelectedNodesList` not JSON serializable: `node_names = list(node_names)` normalization in `compress()`
- `AnchorItem.__init__()` parameter mismatch: Corrected constructor args to match actual signature `(x, y, anchor_type, port_name, port_type, size, parent)`
