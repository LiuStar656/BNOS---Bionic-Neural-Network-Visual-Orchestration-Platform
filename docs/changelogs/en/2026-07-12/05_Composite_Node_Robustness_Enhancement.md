# 05 Composite Node Robustness Enhancement

## Overview

Addressed 4 design gaps in the composite node system: drag performance, disk exception handling, config conflict detection, orchestrator checkpoint/resume, plus a pre-placed distributed transport interface.

---

## I. P0 — 20+ Node Drag Lag

**Root cause**: `canvas_event_handlers.py` `_sync_composite_group_movement` writes back anchor dict per frame, triggering N canvas repaints.

**Fix**: Remove per-frame write-back; batch persist positions on `mouseRelease`.

| File | Change |
|------|------|
| `canvas_event_handlers.py` | Remove anchor per-frame updates, batch on `mouseRelease` |

---

## II. P0 — Orchestrator / Log Disk Exceptions

**Root cause**: `open(log_file, "w")` and `open(orchestrator_path, "w")` had no `PermissionError` / `OSError` branches.

**Fix**: 3 try/except blocks + themed_message friendly dialogs.

| File | Change |
|------|------|
| `composite_node.py` | `start_inprocess()` file open protected with `PermissionError/OSError` |
| `composite_orchestrator.py` | Orchestrator script write protected |

---

## III. P1 — Config External Modification Conflict

**Scenario**: Expand composite node → modify inner node config on canvas → collapse → external changes silently overwritten.

**Fix**: Snapshot `_config_snapshot` on expand → compare on collapse → log warning.

| File | Change |
|------|------|
| `composite_node.py` | `_decompress()` snapshots, `_compress()` compares |

---

## IV. P1 — Orchestrator Checkpoint / Resume

**Scenario**: Internal DAG node fails → full restart required, successful nodes wasted.

**Fix**: `_try_read_cache()` checks sub-node `output.json` → skips completed nodes.

| File | Change |
|------|------|
| `composite_orchestrator.py` | `_try_read_cache` + `execute()` skip logic |

---

## V. P2 — Distributed Transport Interface (Placeholder)

Abstract interface for future multi-machine orchestration, no impact on existing single-machine logic:

| File | Change |
|------|------|
| `transports/__init__.py` | New `TransportHandler` ABC (`send` / `receive` / `ping`) |
| `composite_node.py` | `execute()` → `_execute_local()` dispatch |

Total: ~200 lines, 7 files modified + 1 new.
