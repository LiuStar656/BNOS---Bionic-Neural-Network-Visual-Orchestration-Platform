# 2026-07-13 Update Overview

[Back to Index](../README.md)

---

## Update Catalog

- [01 Composite Node Context Menu Optimization & Input Anchor Exclusive Detection](#01-composite-node-context-menu-optimization--input-anchor-exclusive-detection)
- [02 Composite Node Collapse DAG Topology Update Fix](#02-composite-node-collapse-dag-topology-update-fix)

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

## Modified Files

| File | Change |
|------|--------|
| `ui/canvas/mixins/canvas_menus.py` | Rewrote `_show_composite_node_menu`; added `_on_toggle_expand` |
| `ui/canvas/mixins/canvas_connections.py` | Added input anchor exclusive detection in `create_edge` |
| `ui/core/node/composite_node.py` | Added DAG topology sync logic in `_collapse_composite` |

---

**Last Updated**: 2026-07-13
