# 2026-07-12 Update Overview

[Back to Index](../README.md)

---

## Update Contents

- [01 _port_routing Port Routing Mechanism](#01-_port_routing-port-routing-mechanism)
- [02 Composite Node Connection & Collapse Fixes](#02-composite-node-connection--collapse-fixes)
- [03 Single-Entry DAG Validation](#03-single-entry-dag-validation)
- [04 Validation i18n](#04-validation-i18n)
- [05 Composite Node UI Interaction & Edge System Round 2 Fixes](#05-composite-node-ui-interaction--edge-system-round-2-fixes)
- [06 Code Standardization Overhaul](#06-code-standardization-overhaul)
- [07 Node Resource Limiting](#07-node-resource-limiting)
- [08 Composite Node Monitoring & Log Fix](#08-composite-node-monitoring--log-fix)
- [09 Composite Node Robustness Enhancement](#09-composite-node-robustness-enhancement)
- [10 BNOS Build Driver Engine Design](#10-bnos-build-driver-engine-design)
- [11 `except Exception: pass` Governance](#11-except-exception-pass-governance)
- [12 Orthogonal Edge Snapping](#12-orthogonal-edge-snapping)
- [13 Composite Node Dialog Style Unification](#13-composite-node-dialog-style-unification)
- [14 Node Config Dialog I18n](#14-node-config-dialog-i18n)
- [15 Composite Node Config & Resource Group](#15-composite-node-config--resource-group)
- [16 Startup Guards & Two-Layer Resource Monitor](#16-startup-guards--two-layer-resource-monitor)

---

## 01 _port_routing Port Routing Mechanism

### Problem

When compositing nodes connected, `_update_composite_config_edge` wrote `listen_upper_file` into internal node `config.json`, causing `_identify_ports` (line 175 `if not listen`) to skip the node — input ports disappeared.

### Solution

Migrate routing information from internal node `config.json` into the new `_port_routing` field in `node_clusters.json`, decoupling port routing from node configuration.

### Modified Files

| File | Changes |
|------|---------|
| `ui/core/node/composite_node.py` | New `_port_routing` helpers: `set_input_routing`, `set_output_routing`, `clear_input_routing`, `clear_output_routing`; `_sync_configs_for_expand` dual-phase sync (scan canvas edges + read `_port_routing`); `_sync_configs_for_collapse` dual-phase sync (write back `_port_routing` + clear internal config) |
| `ui/canvas/mixins/canvas_connections.py` | All three branches of `_update_composite_config_edge` switched to `set_input_routing` / `set_output_routing`, no longer writing `listen_upper_file` to internal nodes; `remove_edge` composite→composite branch uses `clear_input_routing` / `clear_output_routing`; removed unused `_sync_internal_out_connections` method |
| `ui/core/node/composite_orchestrator.py` | Generated orchestrator script reads `_port_routing.input` in `__main__`, injecting `external_input` into `runner.run()` |

### _port_routing Data Structure

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

### Constraint Scope

- **Node `main.py`**: Zero changes. `_port_routing` is only read by the orchestrator script for injection; node's own `process()` remains unchanged.
- **Node development spec**: No new constraints. `main.py` in composite mode is still invoked directly via `importlib`, not through `listener.py`.

---

## 02 Composite Node Connection & Collapse Fixes

### Expand/Collapse Edge Update Fixes

- `_morph_composite_to_internal_edges`: Added `update_path()` after creating temp edges
- `_expand_composite`: Added `update_path()` after restoring internal edges
- `_morph_internal_to_composite_edges`: Added `update_path()` after restoring original edges

### Expand/Collapse Jitter Fixes

- `_sync_composite_group_movement`: Skip dragging node to avoid duplicate `setPos` triggering double `itemChange`
- New `_batch_updating` flag: Wraps per-node refresh during expand/collapse; `_batch_update_edges_for_nodes` called once at the end to refresh all edges

### Config Diagnostics Fix

- Added detailed logging on silent `return` paths in `_update_composite_config_edge`
- Added `_composite_manager` lazy initialization fallback

### _port_routing Residue Cleanup

- `_refresh_ports_on_collapse`: Added cleanup logic at the end — traverses `_port_routing` and removes entries referencing stale port names

---

## 03 Single-Entry DAG Validation

### Core Constraint

Composite nodes must be single-entry DAGs. Supported topologies: `A→B→C` or `A→B` concurrently `A→C`. Disallowed: `A→C` and `B→C` (dual entry).

### New Method

`_validate_dag_single_entry` — counts candidate entry nodes with `in_degree==0` and empty `listen_upper_file`:

| Candidates | Behavior |
|-----------|----------|
| 0 | Reject — "No entry node detected" |
| 1 | Pass |
| 2+ | Reject — "Must have exactly one entry" |

### Trigger Points

| Operation | Timing | Rejection Behavior |
|-----------|--------|-------------------|
| Compress | After port identification in `compress()` | `return False, err_msg, None` |
| Collapse | Before any state change in `_collapse_composite()` | `QMessageBox.warning` + `return`, expanded state preserved |

---

## 04 Validation i18n

3 new translation keys covering Chinese and English:

| Key | Chinese | English |
|-----|---------|---------|
| `_COMPOSITE_NO_ENTRY` | "未检测到入口节点" | "No entry node detected" |
| `_COMPOSITE_MULTI_ENTRY` | "检测到 {count} 个入口节点" | "Detected {count} entry nodes" |
| `COMPOSITE_COLLAPSE_BLOCKED_TITLE` | "无法折叠" | "Cannot Collapse" |

Modified files:
- `ui/core/i18n/translation_keys.py` — Key definitions
- `ui/core/i18n/strings_cn.json` — Chinese translations
- `ui/core/i18n/strings_en.json` — English translations

---

## 05 Composite Node UI Interaction & Edge System Round 2 Fixes

### Right-Click Menu Expand/Collapse

- `canvas_menus.py`: Added "Expand"/"Collapse" menu items to `_show_composite_node_menu`, replacing double-click expand
- Fixed canvas-level `contextMenuEvent` intercepting CompositeNodeItem events, causing missing right-click menu

### Composite Output Anchor Edge Creation

- `composite_node_item.py`: Added `output_anchor` / `input_anchor` / `node_name` properties, enabling the edge system to recognize composite node anchors
- `canvas_connections.py`: `create_edge` now handles composite-involved edges via `_update_composite_config_edge` writing `out_connections` on both sides
- `remove_edge`: Added `_clean_target_config` / `_clean_source_out_connections` helpers for composite target config cleanup

### Expanded State UI Interaction Fix

- `composite_group_frame.py`: Overrode `shape()` to cover only the collapse button area, preventing the default full-rect response region from eating mouse events meant for internal nodes and anchors

### Edge Residue Cleanup After Collapse

- `compress()` / `decompress()`: Hide internal edges during compression, track in `_internal_edges`, restore on decompression
- `_handle_line_visibility_on_collapse/expand`: Multi-composite safety — check if edge endpoints belong to another expanded composite before restoring, preventing false restoration

### Composite Edge config.json Synchronization

- Full config.json re-alignment on every expand/collapse cycle:
  - `_sync_configs_for_expand`: Scans canvas edges + reads `_port_routing`, writes `listen_upper_file` and `out_connections` to internal nodes
  - `_sync_configs_for_collapse`: Reads from internal nodes, writes back to `_port_routing` and clears internal config
- Port identification `_identify_ports`: Changed from pure DAG edge detection to also checking `config.json`'s `listen_upper_file` and `out_connections`

### Edge Anchor Invalidation Fix After Collapse

- `_refresh_ports_on_collapse`: `update_ports()` destroys old anchors, but existing edges still hold old anchor references → invalid
- Fix: Save composite-connected edges → refresh ports → rebind edges to new anchors (via `find_anchor_by_port`); stale edges that fail rebinding are removed

### Internal Node Drag Fluttering Fix

- `canvas_event_handlers.py`: New `_prepare_composite_drag_anchor` (presets anchors in `mousePressEvent`) and `_clear_composite_drag_anchors`
- `_sync_composite_group_movement` rewritten: Updates anchor positions every frame; only the actually-dragged node has a position delta, eliminating the feedback loop where non-dragged nodes were misidentified as "moved"
- Group frame `composite_group_frame.py` now synchronizes movement with internal nodes

### PermissionError Save Retry

- `composite_node.py` `save()` method: Added `_saving` re-entrant lock + 3 retries (0.1s→0.2s→0.3s delays) + delete-then-rename fallback, resolving Windows file lock conflicts

### Other Fixes

- `SelectedNodesList` not JSON serializable: `node_names = list(node_names)` normalization in `compress()`
- `AnchorItem.__init__()` parameter mismatch: Corrected constructor args to match actual signature `(x, y, anchor_type, port_name, port_type, size, parent)`

---

## Modified File List

| File | Type |
|------|------|
| `ui/core/node/composite_node.py` | Modified |
| `ui/canvas/mixins/canvas_connections.py` | Modified |
| `ui/core/node/composite_orchestrator.py` | Modified |
| `ui/core/i18n/translation_keys.py` | Modified |
| `ui/core/i18n/strings_cn.json` | Modified |
| `ui/core/i18n/strings_en.json` | Modified |
| `ui/canvas/items/composite_node_item.py` | Modified |
| `ui/canvas/items/composite_group_frame.py` | Modified |
| `ui/canvas/mixins/canvas_menus.py` | Modified |
| `ui/canvas/mixins/canvas_event_handlers.py` | Modified |
| `docs/design/复合节点开发方案.md` | Updated |

---

## 06 Code Standardization Overhaul

See full details in [06_Code_Standardization.md](./06_Code_Standardization.md).

### Summary

- **Toolchain**: Ruff + Pre-commit + EditorConfig + Pylance (greenfield)
- **8 real bugs fixed**: `NameError`, `ImportError`, closure capture, dead code, etc.
- **Logger unified**: 4 styles → 1 (`from ui.core.logger import logger`)
- **`print()` migrated**: → `logger.info()`
- **`from __future__ import annotations`**: 219 files
- **`# type: ignore` eliminated**: 8 → 0
- **`os.path` → `pathlib.Path`**: 691 → 156 (-77%)
- **Dead code removed**: `if/else: pass`, empty exception handlers
- **Runtime fixes**: `_morphed_edges` serialization, `config_file` Path compat

### Final Pass

```
ruff check    → All checks passed!
pytest        → 172 passed, 0 failed
py_compile    → 227 files, 0 errors
Pylance       → 0 diagnostics
pre-commit    → Installed
```

---

**Last Updated**: 2026-07-12

---

## 07 Node Resource Limiting

See full details in [07_Node_Resource_Limiting.md](./07_Node_Resource_Limiting.md).

### Summary

- **Cross-platform resource limiting**: Linux cgroups v2 (CPU + memory hard limits), Windows Job Objects (CPU + memory hard limits), macOS (nice priority)
- **config.json fields**: `priority` / `cpu_affinity` / `cpu_percent` / `memory_mb` — all optional
- **22 new tests**: Factory function, priority mapping, context manager, graceful degradation, macOS fallback, config edge cases
- **Docs updated**: `config_json_开发规范` new Chapter 8 with 7 usage scenario recommendations

---

## 08 Composite Node Monitoring & Log Fix

See full details in [04_Composite_Node_Monitoring_Log_Fix.md](./04_Composite_Node_Monitoring_Log_Fix.md).

### Summary

- **Monitoring black hole fixed**: `CompositeNodeItem` integrates `NodeStatusWidget`; collapsed composite nodes show CPU/MEM/status light
- **Log black hole fixed**: `stdout/stderr=PIPE` → file output (`composite_output.log` / `composite_error.log`); View Log supports composite dual logs
- **PID fallback**: `get_node_pid()` falls back to `__composite_{id}.pid` for composite nodes

---

## 09 Composite Node Robustness Enhancement

See full details in [05_Composite_Node_Robustness_Enhancement.md](./05_Composite_Node_Robustness_Enhancement.md).

### Summary

- **Drag performance (P0)**: Removed per-frame anchor write-back; batch persist on `mouseRelease`
- **Disk exceptions (P0)**: 3 try/except blocks (`PermissionError`/`OSError`) + themed_message dialogs
- **Config conflict detection (P1)**: Snapshot on expand → compare on collapse → log warning
- **Orchestrator checkpoint (P1)**: `_try_read_cache()` skips completed nodes via `output.json`
- **Distributed transport (P2)**: `TransportHandler` ABC placeholder

---

## 10 BNOS Build Driver Engine Design

See full details in [06_BNOS_Build_Driver_Engine_Design.md](./06_BNOS_Build_Driver_Engine_Design.md).

### Summary

- **Concept**: Export mode → driver layer injection; engine isolated from source files
- **Commands**: `bnos build` / `--force` / `--clean` / `--update` / `--docker`
- **Runtime**: `python -m bnos_runtime.engine pipeline.json` (no GUI needed)

---

## 11 `except Exception: pass` Governance

See full details in [07_Except_Exception_Pass_Governance.md](./07_Except_Exception_Pass_Governance.md).

### Summary

- **Scale**: 100 patterns → 0 across 26 files
- **Types**: `OSError`, `ProcessLookupError`, `NoSuchProcess`/`AccessDenied`, `RuntimeError`, `ValueError`

---

## 12 Orthogonal Edge Snapping

See full details in [08_Orthogonal_Edge_Snapping.md](./08_Orthogonal_Edge_Snapping.md).

### Summary

- **Feature**: Waypoint drag snaps to 90°/180° intersections
- **Toggle**: Shift disables; right-click menu global toggle; `SNAP_THRESHOLD = 20px`

---

## 13 Composite Node Dialog Style Unification

See full details in [09_Composite_Node_Dialog_Style_Unification.md](./09_Composite_Node_Dialog_Style_Unification.md).

### Summary

- **6 QMessageBox** → `themed_message()` — dark rounded borderless consistent with BNOS theme

---

## 14 Node Config Dialog I18n

See full details in [10_Node_Config_Dialog_I18n.md](./10_Node_Config_Dialog_I18n.md).

### Summary

- **20 hardcoded strings** -> `t(TK.KEY)`; Resource Limits section fully i18n'd; +19 keys

---

## 15 Composite Node Config & Resource Group

See full details in [11_Composite_Node_Config_Resource_Group.md](./11_Composite_Node_Config_Resource_Group.md).

### Summary

- **composite.json** Schema (identity + DAG + ports + resource budget); self-healing from node_clusters.json
- **node_registry.json** runtime registry (status, PID, launch origin, independent runs)
- **Compress**: creates `composite_nodes/<id>/` with full directory structure
- **Startup**: auto-migrates composites missing config files
- **Decompress**: logs archived to `.archive/<id>_<fingerprint>_<timestamp>/`, then deleted
- **Log path** migrated from `{name}_venv/logs/` to `composite_nodes/<id>/logs/`
- Composite venv lifecycle-bound: decompress = deletion

### Modified Files

| File | Change |
|------|--------|
| `ui/core/node/composite_node.py` | +280 lines (10 new methods) |
| `ui/panels/node_list_ops.py` | _get_log_files path fix |

---

## 16 Startup Guards & Two-Layer Resource Monitor

See full details in [12_Startup_Guard_Resource_Monitor.md](./12_Startup_Guard_Resource_Monitor.md).

### Summary

- **Startup guards (bidirectional)**: standalone checks composite running + 3-choice dialog; composite checks sub-nodes + auto-stop
- **Resource monitor two-layer**: orchestrator PID independent row; sub-node `[sub]` indented rows
- **Running**: sub-nodes in orchestrator process, display `--` (no double counting)
- **Stopped**: sub-nodes running independently show individual PID resources

### Modified Files

| File | Change |
|------|--------|
| `ui/core/node/composite_node.py` | +3 methods (check_subnode_start / check_composite_start / stop_conflicting_subnodes) |
| `ui/main_window/node.py` | start_selected_node_by_name guard |
| `ui/panels/resource_monitor.py` | _update_node_stats + _refresh_node_table rewrite |
| `ui/panels/resource_monitor_dock.py` | same |
| `ui/panels/_shared/system_resource_collector.py` | +3 methods |
| `ui/core/i18n/translation_keys.py` + strings | +2 keys
