# Node Startup Queue Feature Implementation

---

## Update Overview

This update implements a complete Node Startup Queue System (V2.0), designed as a smart scheduler with concurrency control, priority scheduling, error retry, startup interval control, and queue persistence. Currently for rate limiting only, dependency-based startup is not supported.

---

## Core Features

### 1. Startup Queue Management

Supports nodes entering the queue for startup, providing complete queue operation interfaces:

| Interface | Function |
|-----------|----------|
| `enqueue(node_name, priority, dependencies)` | Add node to queue |
| `dequeue(node_name)` | Remove node from queue |
| `promote(node_name, priority)` | Promote node priority (cut in line) |
| `clear()` | Clear queue |
| `get_status(node_name)` | Get node queue status |
| `get_queue_info()` | Get overall queue information |

### 2. Concurrency Control

Configurable maximum concurrent startup nodes, default value is 2 to prevent resource competition:

```python
startup_queue = NodeStartupQueueManager(
    max_concurrent=2,   # Maximum concurrent count
    max_retry=3,        # Maximum retry times
    batch_delay=300     # Batch interval (ms)
)
```

### 4. Status Feedback

New queue status added to complete the node status system:

| Status | Icon | Color | Description |
|--------|------|-------|-------------|
| `queued` | ◎ | blue | Waiting in queue |
| `starting` | ◐ | yellow | Starting |
| `running/idle` | ● | green | Running/Idle |
| `failed` | ✗ | red | Failed to start |

### 5. Error Retry

Automatic retry mechanism on failure, configurable retry count (default 3):
- On startup failure, automatically reset node status to `QUEUED`
- Wait for configured retry delay before rescheduling
- Mark as `FAILED` when maximum retry count reached

### 6. Startup Interval Control

Smooth delay between batches to avoid resource contention:
- Uses `QTimer.singleShot` for recursive scheduling
- 200ms~500ms interval between adjacent batches
- Gives system time for resource release and status synchronization

### 7. Queue Persistence

Saves queue state on exit, restores on restart:

**Snapshot Management**:
- `save_snapshot()`: Save queue state to JSON file
- `load_snapshot()`: Load queue snapshot on startup
- Recovery prompt support: Display last incomplete queue status

---

## Event Notification Mechanism

Decouples queue manager from UI layer via event callbacks:

| Event | Trigger | Parameters |
|-------|---------|------------|
| `queue_updated` | Queue content changed | `queue_info: dict`, `blocked_info: dict` |
| `node_enqueued` | Node enqueued | `node_name: str`, `position: int`, `priority: int` |
| `node_dequeued` | Node dequeued | `node_name: str`, `status: QueueStatus` |
| `node_starting` | Node starting | `node_name: str` |
| `node_started` | Node started successfully | `node_name: str` |
| `node_failed` | Node startup failed | `node_name: str`, `error: str`, `retry_count: int` |
| `node_retry` | Node preparing for retry | `node_name: str`, `retry_count: int` |
| `queue_empty` | Queue processing complete | - |

---

## Data Structure Design

### QueueItem Class

```python
class QueueItem:
    def __init__(self, node_name: str, priority: int = 0):
        self.node_name = node_name          # Node name
        self.priority = priority            # Priority
        self.status = QueueStatus.QUEUED    # Current status
        self.retry_count = 0                # Retry count
        self.enqueue_time = None            # Enqueue time
        self.start_time = None              # Start time
        self.complete_time = None           # Complete time
        self.error_message = None           # Error message
```

### QueueStatus Enum

```python
class QueueStatus(Enum):
    QUEUED = "queued"           # Waiting in queue
    STARTING = "starting"       # Starting
    SUCCESS = "success"         # Started successfully
    FAILED = "failed"           # Failed to start
    CANCELLED = "cancelled"     # Cancelled
```

---

## Key Implementation Details

### Smart Queue Scheduler

```python
def _process_queue(self):
    """Queue scheduling main logic - Smart Scheduler
    
    Core Features:
    1. Concurrency Control: No more than max_concurrent nodes starting simultaneously
    2. Priority Scheduling: High priority nodes first
    3. Smooth Startup: Delay between batches to avoid resource competition
    """
    # Check available slots
    running_count = len([item for item in self._queue 
                         if item.status == QueueStatus.STARTING])
    
    if running_count >= self._max_concurrent:
        self._schedule_next_process()
        return
    
    # Get ready nodes (queued nodes)
    ready_items = self._get_ready_nodes()
    
    # Sort by priority
    ready_items.sort(key=lambda x: (-x.priority, x.enqueue_time))
    
    # Start next ready node
    next_item = ready_items[0]
    self._start_node(next_item)
    
    # Schedule next processing (with delay)
    self._schedule_next_process()
```

---

## Configuration and Default Values

| Configuration | Default | Description |
|---------------|---------|-------------|
| `max_concurrent` | 2 | Maximum concurrent startup nodes |
| `max_retry` | 3 | Maximum retry count |
| `retry_delay` | 5000 | Retry delay (ms) |
| `batch_delay` | 300 | Batch startup interval (ms) |
| `queue_timeout` | 60000 | Queue timeout (ms) |

---

## New Files

| File | Description |
|------|-------------|
| `ui/core/node_startup_queue.py` | Core implementation of Node Startup Queue Manager |

## Modified Files

| File | Changes |
|------|---------|
| `ui/core/node_process.py` | Integrated queue startup flow |
| `ui/core/node_control_service.py` | Queue status management |
| `ui/panels/node_list_ops.py` | Batch start integrated with queue |

---

## Backward Compatibility

- ✅ Existing `start_selected_node()` method remains compatible
- ✅ New `queued` status doesn''t affect existing state transitions
- ✅ Configuration items provide default values, no need to modify existing config files
- ✅ Queue persistence is optional, doesn''t affect existing functionality