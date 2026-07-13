# 09 DAG Run Status Tracking

## Problem Description

Composite node DAG execution couldn't track per-node execution status, hindering troubleshooting and monitoring.

## Fix Solution

### 9.1 Per-Node Status Tracking

**File**: `ui/core/node/composite_orchestrator.py`

`DagRunner` records each child node's execution status:
- `status`: ok / fail / pending
- `error`: error message
- `duration_ms`: execution duration

**Code Change**:
```python
self._node_status = {}

# Record status at each execution stage
self._node_status[node_name] = {
    "status": "ok",
    "duration_ms": int((time.time() - t0) * 1000),
    "output_lines": len(output_text.splitlines())
}
```

### 9.2 Status Persistence

**File**: `ui/core/node/composite_orchestrator.py`

Write status to `status.json` after execution for BNOS monitoring.

**Code Change**:
```python
def _write_status(self):
    for node_name in self._node_paths:
        if node_name not in self._node_status:
            self._node_status[node_name] = {"status": "pending"}
    status = {
        "comp_id": "{comp_id}",
        "updated_at": datetime.now().isoformat(),
        "last_run_id": self._run_id,
        "nodes": self._node_status,
    }
    (COMP_DIR / "status.json").write_text(json.dumps(status, ...))
```

### 9.3 Parallel Execution Tracking

**File**: `ui/core/node/composite_orchestrator.py`

Failures in parallel nodes are also recorded.

## Modified Files

| File | Change |
|------|--------|
| `ui/core/node/composite_orchestrator.py` | Added `_node_status` tracking; added `_write_status()` method |

## Verification

After fix:
- ✅ Each child node's execution status, error info, and duration recorded
- ✅ Status persisted to `status.json` after execution
- ✅ Unexecuted nodes marked as pending
- ✅ Parallel node failures also tracked

---

**Last Updated**: 2026-07-13
