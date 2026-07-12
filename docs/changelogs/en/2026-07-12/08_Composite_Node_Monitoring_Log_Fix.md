# 08 Composite Node Monitoring & Log Fix

## Overview

Fixed two critical gaps in the composite node system: "monitoring black hole" (no CPU/MEM display when collapsed) and "log black hole" (no log file output). Collapsed composite nodes now show aggregated CPU/MEM and run status; logs are written to disk for viewing.

---

## I. Root Cause

| Issue | Root Cause | Impact |
|------|------|------|
| **Monitoring black hole** | `CompositeNodeItem` not integrated with `NodeStatusWidget`, doesn't subscribe to `node_state_updated` signal | No CPU/MEM or status visible when collapsed |
| **Log black hole** | `start_inprocess()` uses `stdout/stderr=PIPE`, never writes to file | `node_output.log` / `node_error.log` don't exist, "View Log" shows nothing |

The composite node's **PID already existed** (`__composite_{id}.pid`) and `psutil` process tree collection was already in place — just not connected.

---

## II. Changes

| File | Change | Lines |
|------|------|:---:|
| `composite_node.py` | PIPE → file output + `_composite_log_files` dict + `stop_composite` closes handles | +20 |
| `composite_node_item.py` | QTimer + psutil process tree collection + collapsed CPU/MEM/status light | +85 |
| `system_resource_collector.py` | `get_node_pid()` fallback to `__composite_{id}.pid` | +14 |
| `node_list_ops.py` | `view_node_log` → composite dual log paths | +30 |

---

## III. Result

```
Collapsed composite node (running):
┌──────────────────────────────────┐
│ ◈ image_pipeline    ● running    │  ← new status light
│ 3 nodes · inprocess              │
│ CPU: 145%  MEM: 3.18 GB          │  ← new aggregated CPU/MEM
└──────────────────────────────────┘

Right-click → View Log:
  composite_output.log    ← orchestrator stdout
  composite_error.log     ← orchestrator stderr (includes sub-node errors)
```

Key design: resource monitoring reuses `collect_process_resources(pid)` process tree traversal — one PID automatically aggregates all child processes.
