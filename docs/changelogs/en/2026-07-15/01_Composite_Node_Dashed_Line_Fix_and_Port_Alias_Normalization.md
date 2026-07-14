# 01 Composite Node Dashed Line Fix & Port Alias Normalization

## Symptom

When connecting a standalone node to a composite node, the edge first appears as a solid blue line, then **immediately turns into a red/grey dashed line** (invalid-edge render state). The log shows mismatch between the canvas EdgeKey and the CanonicalEdgeSet.

## Root Cause 1 — Wrong composite.json path concatenation

When the Canonical Edge Resolver back-infers the authoritative edge set for composite nodes, an extra `NODE_DIR_ROOT` layer was concatenated:

```python
# ❌ OLD: resolves to project/nodes/composite_nodes/<id>/composite.json
comp_path = project_path / NODE_DIR_ROOT / COMPOSITE_DIR_NAME / cid
```

In reality composite.json lives at `project/composite_nodes/<id>/composite.json` (`nodes/` and `composite_nodes/` are sibling directories, not nested). Consequences:
- composite.json was never read successfully
- 3 composite edge categories (`COMPOSITE_INPUT` / `COMPOSITE_OUTPUT` / `COMPOSITE_INTERNAL`) **all returned 0**
- Every canvas edge involving a composite node was classified as "ghost edge" → dashed rendering

### Fix

```python
# ✅ NEW: strip the redundant NODE_DIR_ROOT layer
comp_path = project_path / COMPOSITE_DIR_NAME / cid
```

## Root Cause 2 — Port alias mismatch (canvas `default` vs authority `data`)

Canvas anchor names use the UI display name `default`, while the internal routing key in composite.json uses `data` (a historical alias pair in the two naming systems):
- Canvas EdgeKey: `(COMPOSITE_INPUT, upstream_id, comp_id, 'upstream_out', 'default')`
- Authority EdgeKey: `(COMPOSITE_INPUT, upstream_id, comp_id, 'upstream_out', 'data')`

The 5-tuples are not equal → no match → dashed rendering.

The output port has the same problem: external `default` ↔ internal `node_output` are aliases of the same port.

### Fix A — Alias expansion on authority generator (canonical_edge_resolver.py)

When parsing `external_connections.input/output` in composite.json, on recognizing a compatible port-name pair we **add BOTH EdgeKey variants to the authority set**:
- Input alias pair: `{data, default}`
- Output alias pair: `{node_output, default}`

This guarantees a hit regardless of which name the canvas uses.

### Fix B — Alias-aware comparison on static validator (node_state_manager.py `is_edge_valid_static`)

Add a "port alias equivalence" branch to EdgeKey comparison:
```
same_port(a, b) ↔ a == b
                 OR (a,b ∈ {data, default})
                 OR (a,b ∈ {node_output, default})
```
Provides backward compatibility with historical canvas layouts stored under old naming conventions.

### Fix C — Normalize writes on routing setters (composite_node.py set_input_routing / set_output_routing)

Two historical write paths used inconsistent names, causing composite.json to carry **two duplicate entries (data AND default pointing to the same upstream)**:
- `canvas_connections.create_edge` → writes the internal standard name `data`
- `composite_node._sync_configs_for_collapse` (reverse-inferred from child node input_ports) → writes UI anchor name `default`

**Force normalization at the entry point** of `set_input_routing` and `set_output_routing`:

```python
# Input: default and data are equivalent; unify under data
raw_port = (port_name or "").strip() or "default"
norm_port = "data" if raw_port in {"data", "default"} else raw_port

# Output: default and node_output are equivalent; unify under node_output
norm_port = "node_output" if raw_port in {"node_output", "default"} else raw_port
```

After writing, **delete the other alias key** (to clean historical stale data):
```python
if raw_port != norm_port and raw_port in routing["input"]:
    del routing["input"][raw_port]
```

### Fix D — Loose alias matching on routing cleaners (clear_input_routing / clear_output_routing)

Callers may pass either port alias. Cleanup cannot match against a single key name only:
- `clear_input_routing(port)` → delete standard name hit first, then delete alias key (`data` ↔ `default`)
- `clear_output_routing(port)` → delete standard name hit first, then delete alias key (`node_output` ↔ `default`)

Cross-composite reference cleanup in the `node_clusters.json` global sync also uses loose alias-based comparison.

## Verification points

1. Standalone → composite input edge **keeps solid blue for 30+ seconds** (does not turn dashed after 3s)
2. After writing, `composite.json external_connections.input_ports` **contains only `['data']`**, never the double-keyed `['data','default']`
3. Historical layouts (canvas persisted with the `default` convention) also match correctly without dashed rendering
4. `canvas_connections._remove_redundant_composite_edges` no longer reports duplicate edges

## Files Changed

| File | Changes |
|------|---------|
| `ui/core/edge/canonical_edge_resolver.py` | Removed redundant `NODE_DIR_ROOT` in composite.json path; added port-alias expansion for composite edges (both data↔default / node_output↔default EdgeKey variants added to the authority set) |
| `ui/core/state/node_state_manager.py` | `is_edge_valid_static` gained composite-edge port-alias equivalence comparison, tolerant to legacy canvas naming |
| `ui/canvas/mixins/canvas_connections.py` | `create_edge` creates composite edges under internal port names (data / node_output) to reduce downstream conversions |
| `ui/core/node/composite_node.py` | `set_input_routing` / `set_output_routing` entry-point normalization to standard names + alias stale-key cleanup; `clear_input_routing` / `clear_output_routing` loose alias-aware matching |
