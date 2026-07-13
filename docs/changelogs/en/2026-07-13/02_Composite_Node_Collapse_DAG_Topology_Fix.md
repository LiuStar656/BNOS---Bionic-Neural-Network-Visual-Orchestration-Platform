# Composite Node Collapse DAG Topology Update Fix

[Back to Overview](./README.md)

---

## Background

After expanding a composite node, re-wiring sub-node connections (e.g., changing A→B to B→A), collapsing, and starting the composite node, the data processing result did not reflect the new topology. For example:

- Original DAG: node_4(data=1) → node_3(×3) → node_2(+1) → result = 4
- Changed to: node_4(data=1) → node_2(+1) → node_3(×3) → expected result = 6

But the actual result remained 4, indicating the new topology was not applied.

---

## Root Cause Analysis

The issue was in the `_collapse_composite` method's write chain:

1. During collapse, `internal_edge_info` correctly captured the new edges (e.g., `src → node_2, tgt → node_3`)
2. But it was only written to the in-memory dict `comp["_internal_edges"]`
3. **`composite.json`'s `edges` field was never updated**, retaining the original topology from the first compression
4. `_sync_pipeline` reads `composite.json` → `pipeline.json` uses stale DAG
5. `orchestrator.py` reads the DAG from `pipeline.json` → old topology executes

Additionally, `_sync_pipeline` was only called when `new_rules` (entry filter rule changes) was truthy. If only the DAG topology changed but filter rules didn't, `_sync_pipeline` was never invoked.

### Key Code Path (Before Fix)

```python
# Collapse only writes to memory
comp["_internal_edges"] = internal_edge_info

# ... other operations ...

# _sync_pipeline only called when filter rules change
new_rules = self._extract_entry_filter_rules(...)
if new_rules:                           # ← conditional gate
    comp_cfg = self._load_composite_config(comp_id)
    if comp_cfg:
        comp_cfg["input_filter_rules"] = new_rules
        self._write_composite_config(comp_id, comp_cfg)
        self._sync_pipeline(comp_id)    # ← never executed
```

---

## Fix

#### File: `ui/core/node/composite_node.py`

**1. Immediately sync edges to composite.json during collapse**

After `comp["_internal_edges"] = internal_edge_info`, immediately load `composite.json` and update the `edges` field:

```python
comp["_internal_edges"] = internal_edge_info

# Sync DAG topology to composite.json
comp_cfg = self._load_composite_config(comp_id)
if comp_cfg:
    comp_cfg["edges"] = [
        {"from": e["src"], "to": e["tgt"],
         "source_port": e.get("src_port", ""),
         "target_port": e.get("tgt_port", "")}
        for e in internal_edge_info
    ]
```

Format mapping: `src→from, tgt→to, src_port→source_port, tgt_port→target_port`

**2. _sync_pipeline always called unconditionally**

Move `_sync_pipeline` outside the `if new_rules:` block:

```python
new_rules = self._extract_entry_filter_rules(node_names, edges_list, nodes_data)
if new_rules and comp_cfg:
    comp["input_filter_rules"] = new_rules
    comp_cfg["input_filter_rules"] = new_rules

# Always write composite.json and sync pipeline.json
# DAG topology (edges) may have changed even if filter rules haven't
if comp_cfg:
    self._write_composite_config(comp_id, comp_cfg)
    self._sync_pipeline(comp_id)
    self._touch_pipe_signal(comp_id)
```

3. Also write `.pipe` signal file to notify a running orchestrator to hot-reload the new pipeline.

---

## Fixed End-to-End Flow

```
Expand → User re-wires → Collapse
  ↓
_collapse_composite:
  1. internal_edge_info = [new edges]
  2. comp["_internal_edges"] = internal_edge_info        ← memory
  3. comp_cfg["edges"] = format-converted edges           ← composite.json
  4. _write_composite_config(comp_id, comp_cfg)           ← persist
  5. _sync_pipeline(comp_id)                              ← pipeline.json
  6. _touch_pipe_signal(comp_id)                          ← .pipe signal
  ↓
orchestrator.py:
  - Detects .pipe → reloads pipeline.json → new topology takes effect
  - Or reads latest pipeline.json on next start
```

---

## Modified Files

| File | Change |
|------|--------|
| `ui/core/node/composite_node.py` | `_collapse_composite`: added edges sync to composite.json; `_sync_pipeline` now called unconditionally |

---

**Last Updated**: 2026-07-13
