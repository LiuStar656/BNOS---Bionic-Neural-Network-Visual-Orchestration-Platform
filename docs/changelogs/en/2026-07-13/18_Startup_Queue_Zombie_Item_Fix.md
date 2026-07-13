# Startup Queue Zombie Item Fix

## Problem

Composite nodes could not be started again after being stopped. Clicking start showed "Failed to join queue".

## Root Cause

`NodeStartupQueueManager._on_node_start_complete` set `item.status = QueueStatus.SUCCESS` after successful startup but **never removed the item from `self._queue`**.

When the user clicked start again, `enqueue()` checked `node_name in [item.node_name for item in self._queue]` and found the stale SUCCESS item from the previous run, returning `False` and blocking re-enqueue.

## Fix

### 1. Clean up terminal items

In `_on_node_start_complete`, call `_remove_from_queue()` when items reach terminal state:

```python
def _on_node_start_complete(self, item, success, error):
    if success:
        item.status = QueueStatus.SUCCESS
        self._remove_from_queue(item)  # ← New
        ...
    else:
        if item.retry_count < self._max_retry:
            item.status = QueueStatus.QUEUED  # Retry, don't remove
        else:
            item.status = QueueStatus.FAILED
            self._remove_from_queue(item)  # ← New
```

### 2. Defensive enqueue check

`enqueue` duplicate check now only considers non-terminal items:

```python
def enqueue(self, node_name, ...):
    active_names = {
        item.node_name
        for item in self._queue
        if item.status not in (SUCCESS, FAILED, CANCELLED)
    }
    if node_name in active_names:
        return False  # Truly active duplicate → reject
    # Terminal items won't block re-enqueue even if stale
```

## Improvements

- Composite nodes can now restart normally after being stopped
- Startup queue won't grow indefinitely (SUCCESS/FAILED items auto-cleaned)
- Defensive design ensures no blocking even if cleanup is missed

## Modified Files

| File | Change |
|------|--------|
| `ui/core/node/node_startup_queue.py` | `_on_node_start_complete`: call `_remove_from_queue` after SUCCESS/FAILED; new `_remove_from_queue` method; `enqueue`: duplicate check filters terminal items |
