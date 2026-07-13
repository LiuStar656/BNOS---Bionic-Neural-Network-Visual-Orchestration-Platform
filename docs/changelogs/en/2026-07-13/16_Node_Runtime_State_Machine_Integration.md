# Node Runtime State Machine Integration

## Problem

`node_process.py` directly manipulated `node_info["status"]` bare strings without transition validation, causing:
- Running nodes could be started again (no guard)
- Stopped nodes not correctly identified (state inconsistency)
- `check_running_processes` polling directly assigned status, bypassing the state machine

## Solution

### Bridge Layer (`node_runtime_bridge.py`)

Created a lightweight compatibility layer that doesn't affect existing `node_info["status"]` dict reads/writes:

```python
def ensure_sm(node_info) -> NodeRuntimeSM   # Get or create SM
def get_state(node_info) -> str              # Read state from SM (with fallback)
def transition_state(node_info, event) -> bool  # Trigger transition + sync dict
def sync_status_to_dict(node_info) -> None   # Sync SM → dict
```

### node_process.py Integration

**`start_node_process`**
- Beginning: `transition_state(node_info, "start")` — STOPPED/CRASHED → STARTING, illegal state rejected immediately
- Success: `transition_state(node_info, "start_ok")` — STARTING → RUNNING
- Failure: `transition_state(node_info, "start_fail")` — STARTING → CRASHED (process exit / exception)

**`stop_node_process`**
- Beginning: `transition_state(node_info, "stop")` — RUNNING/IDLE → STOPPING, illegal state rejected immediately
- Success: `transition_state(node_info, "stop_ok")` — STOPPING → STOPPED
- Failure: `transition_state(node_info, "stop_fail")` — STOPPING → CRASHED (fallback cleanup failed)

**`check_running_processes`**
- Process alive + active child → `child_resume` (IDLE → RUNNING)
- Process alive + no active child → `child_idle` (RUNNING → IDLE)
- Process dead → `crash` (RUNNING/IDLE → CRASHED)
- Zombie process (SM out of sync with reality) → directly fix dict + reset SM

**`detect_running_nodes`**
- `info.get("status")` → `get_state(info)` unified read

## Modified Files

| File | Change |
|------|--------|
| `ui/core/state/node_runtime_bridge.py` | New: bridge compatibility layer (`ensure_sm` / `transition_state` / `get_state`) |
| `ui/core/node/node_process.py` | `start_node_process`: SM start guard + start/start_ok/start_fail transitions; `stop_node_process`: SM stop guard + stop/stop_ok/stop_fail transitions; `check_running_processes`: child_resume/child_idle/crash transitions + zombie handling; `detect_running_nodes`: unified get_state read |
