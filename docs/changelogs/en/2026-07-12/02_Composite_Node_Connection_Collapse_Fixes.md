# Composite Node Connection & Collapse Fixes

[Back to Update Overview](./README.md)

---

## Expand/Collapse Edge Update Fixes

- `_morph_composite_to_internal_edges`: Added `update_path()` after creating temp edges
- `_expand_composite`: Added `update_path()` after restoring internal edges
- `_morph_internal_to_composite_edges`: Added `update_path()` after restoring original edges

## Expand/Collapse Jitter Fixes

- `_sync_composite_group_movement`: Skip dragging node to avoid duplicate `setPos` triggering double `itemChange`
- New `_batch_updating` flag: Wraps per-node refresh during expand/collapse; `_batch_update_edges_for_nodes` called once at the end to refresh all edges

## Config Diagnostics Fix

- Added detailed logging on silent `return` paths in `_update_composite_config_edge`
- Added `_composite_manager` lazy initialization fallback

## _port_routing Residue Cleanup

- `_refresh_ports_on_collapse`: Added cleanup logic at the end — traverses `_port_routing` and removes entries referencing stale port names
