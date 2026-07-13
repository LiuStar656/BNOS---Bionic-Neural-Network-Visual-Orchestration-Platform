# Composite Lifecycle State Machine Integration

## Problem

The composite node management system had the following state management issues:
- No duplicate start protection (TOCTOU race condition)
- Resource leaks on exception paths (log file handles not closed)
- Stop operations had no feedback (unknown if kill succeeded)
- `is_running` check relied on in-memory Popen object (not persistent)

## Solution

Integrated `CompositeLifecycleSM` into 5 key methods of `composite_node.py`.

### `_get_lifecycle(comp_id)`

Gets or creates a composite node lifecycle state machine, stored in `self._lifecycle` dict.

### `start_inprocess`

```python
lc = self._get_lifecycle(comp_id)
# TOCTOU protection: SM is_restartable replaces bare dict check
if not lc.is_restartable:
    return False, "already running"
lc.handle("start")  # → STARTING

# ... launch orchestrator process ...

lc.handle("start_ok")      # → RUNNING (success)
lc.handle("start_timeout") # → CRASHED (process exited immediately)
lc.handle("start_fail")    # → CRASHED (exception)
```

**Resource leak fix**: Completed `_composite_log_files` cleanup on exception path:
```python
log_files = self._composite_log_files.pop(comp_id, (None, None))
for fh in log_files:
    if fh is not None:
        try: fh.close()
        except OSError: pass
```

### `stop_composite`

```python
lc = self._get_lifecycle(comp_id)
# SM guard: only allow stop when in active state
if not lc.is_active:
    return False, "not running"
lc.handle("stop")  # → STOPPING

# ... kill process tree ...

lc.handle("stop_ok")   # → STOPPED (success)
lc.handle("stop_fail")  # → CRASHED (fallback cleanup failed)
```

### `decompress`

```python
lc = self._get_lifecycle(comp_id)
lc.handle("decompress")     # → REMOVING
# ... decompress cleanup ...
lc.handle("remove_done")    # → REMOVED
# Clean up lifecycle SM
self._lifecycle.pop(comp_id, None)
```

### `is_running`

Delegates to lifecycle SM:
```python
def is_running(self, comp_id):
    lc = self._lifecycle.get(comp_id)
    if lc is not None:
        return lc.is_active  # STARTING / RUNNING / STOPPING
    # Fallback: when SM not initialized, fall back to Popen check
    proc = self._active_processes.get(f"__composite_{comp_id}")
    return proc is not None and proc.poll() is None
```

## Improvements

- TOCTOU race eliminated: `is_restartable` single check covers CREATED/STOPPED/CRASHED restartable states
- Resource leak fixed: exception paths now properly close log file handles
- Stop feedback: `stop_ok` / `stop_fail` clearly distinguish success vs failure
- State consistency: `is_running` reads from SM (CREATED=compressing phase=not running)

## Modified Files

| File | Change |
|------|--------|
| `ui/core/node/composite_node.py` | `start_inprocess`: TOCTOU is_restartable guard + resource leak fix; `stop_composite`: is_active guard + stop_ok/stop_fail transitions; `decompress`: decompress/remove_done transitions + cleanup; `_on_compress_worker_done`: create lifecycle SM; `is_running`: delegate to lifecycle SM; new `_get_lifecycle` + `_lifecycle` dict |
