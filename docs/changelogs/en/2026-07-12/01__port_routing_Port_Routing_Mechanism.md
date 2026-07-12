# _port_routing Port Routing Mechanism

[Back to Update Overview](./README.md)

---

## Problem

When compositing nodes connected, `_update_composite_config_edge` wrote `listen_upper_file` into internal node `config.json`, causing `_identify_ports` (line 175 `if not listen`) to skip the node — input ports disappeared.

## Solution

Migrate routing information from internal node `config.json` into the new `_port_routing` field in `node_clusters.json`, decoupling port routing from node configuration.

## Modified Files

| File | Changes |
|------|---------|
| `ui/core/node/composite_node.py` | New `_port_routing` helpers: `set_input_routing`, `set_output_routing`, `clear_input_routing`, `clear_output_routing`; `_sync_configs_for_expand` dual-phase sync (scan canvas edges + read `_port_routing`); `_sync_configs_for_collapse` dual-phase sync (write back `_port_routing` + clear internal config) |
| `ui/canvas/mixins/canvas_connections.py` | All three branches of `_update_composite_config_edge` switched to `set_input_routing` / `set_output_routing`, no longer writing `listen_upper_file` to internal nodes; `remove_edge` composite→composite branch uses `clear_input_routing` / `clear_output_routing`; removed unused `_sync_internal_out_connections` method |
| `ui/core/node/composite_orchestrator.py` | Generated orchestrator script reads `_port_routing.input` in `__main__`, injecting `external_input` into `runner.run()` |

## _port_routing Data Structure

```json
{
  "input": {
    "port_name": {"source_output_path": "nodes/xxx/output.json"}
  },
  "output": {
    "port_name": {
      "target_composite": "composite_xxx",
      "target_node": "internal_name",
      "target_port": "port_name"
    }
  }
}
```

## Constraint Scope

- **Node `main.py`**: Zero changes. `_port_routing` is only read by the orchestrator script for injection; node's own `process()` remains unchanged.
- **Node development spec**: No new constraints. `main.py` in composite mode is still invoked directly via `importlib`, not through `listener.py`.
