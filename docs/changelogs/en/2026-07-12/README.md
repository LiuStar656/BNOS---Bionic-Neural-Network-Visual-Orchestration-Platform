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

See full details in [01__port_routing_Port_Routing_Mechanism.md](./01__port_routing_Port_Routing_Mechanism.md).

---

## 02 Composite Node Connection & Collapse Fixes

See full details in [02_Composite_Node_Connection_Collapse_Fixes.md](./02_Composite_Node_Connection_Collapse_Fixes.md).

---

## 03 Single-Entry DAG Validation

See full details in [03_Single_Entry_DAG_Validation.md](./03_Single_Entry_DAG_Validation.md).

---

## 04 Validation i18n

See full details in [04_Validation_i18n.md](./04_Validation_i18n.md).

---

## 05 Composite Node UI Interaction & Edge System Round 2 Fixes

See full details in [05_Composite_Node_UI_Interaction_Round_2.md](./05_Composite_Node_UI_Interaction_Round_2.md).

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

See full details in [08_Composite_Node_Monitoring_Log_Fix.md](./08_Composite_Node_Monitoring_Log_Fix.md).

### Summary

- **Monitoring black hole fixed**: `CompositeNodeItem` integrates `NodeStatusWidget`; collapsed composite nodes show CPU/MEM/status light
- **Log black hole fixed**: `stdout/stderr=PIPE` → file output (`composite_output.log` / `composite_error.log`); View Log supports composite dual logs
- **PID fallback**: `get_node_pid()` falls back to `__composite_{id}.pid` for composite nodes

---

## 09 Composite Node Robustness Enhancement

See full details in [09_Composite_Node_Robustness_Enhancement.md](./09_Composite_Node_Robustness_Enhancement.md).

### Summary

- **Drag performance (P0)**: Removed per-frame anchor write-back; batch persist on `mouseRelease`
- **Disk exceptions (P0)**: 3 try/except blocks (`PermissionError`/`OSError`) + themed_message dialogs
- **Config conflict detection (P1)**: Snapshot on expand → compare on collapse → log warning
- **Orchestrator checkpoint (P1)**: `_try_read_cache()` skips completed nodes via `output.json`
- **Distributed transport (P2)**: `TransportHandler` ABC placeholder

---

## 10 BNOS Build Driver Engine Design

See full details in [10_BNOS_Build_Driver_Engine_Design.md](./10_BNOS_Build_Driver_Engine_Design.md).

### Summary

- **Concept**: Export mode → driver layer injection; engine isolated from source files
- **Commands**: `bnos build` / `--force` / `--clean` / `--update` / `--docker`
- **Runtime**: `python -m bnos_runtime.engine pipeline.json` (no GUI needed)

---

## 11 `except Exception: pass` Governance

See full details in [11_Except_Exception_Pass_Governance.md](./11_Except_Exception_Pass_Governance.md).

### Summary

- **Scale**: 100 patterns → 0 across 26 files
- **Types**: `OSError`, `ProcessLookupError`, `NoSuchProcess`/`AccessDenied`, `RuntimeError`, `ValueError`

---

## 12 Orthogonal Edge Snapping

See full details in [12_Orthogonal_Edge_Snapping.md](./12_Orthogonal_Edge_Snapping.md).

### Summary

- **Feature**: Waypoint drag snaps to 90°/180° intersections
- **Toggle**: Shift disables; right-click menu global toggle; `SNAP_THRESHOLD = 20px`

---

## 13 Composite Node Dialog Style Unification

See full details in [13_Composite_Node_Dialog_Style_Unification.md](./13_Composite_Node_Dialog_Style_Unification.md).

### Summary

- **6 QMessageBox** → `themed_message()` — dark rounded borderless consistent with BNOS theme

---

## 14 Node Config Dialog I18n

See full details in [14_Node_Config_Dialog_I18n.md](./14_Node_Config_Dialog_I18n.md).

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

See full details in [16_Startup_Guard_Resource_Monitor.md](./16_Startup_Guard_Resource_Monitor.md).

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
