# 05_Polling Manager Dynamic Frequency Adjustment

**Date**: 2026-06-20

## Background

`PollingManager` is BNOS's background task scheduler responsible for periodic node status, log, and configuration polling. Before this update, it used a **fixed 2-second interval**:

- **Idle**: No nodes running but still polling every 2 seconds, wasting CPU
- **Heavy load**: Nodes running densely, 2-second interval caused UI refresh delay

## Changes

### Frequency Mode Definition

```python
# Frequency mode constants (seconds)
FREQ_HIGH = 1       # CPU < 30%
FREQ_NORMAL = 2     # 30% <= CPU <= 60%
FREQ_LOW = 4        # CPU > 60%

# Thresholds
CPU_LOW_THRESHOLD = 30
CPU_HIGH_THRESHOLD = 60
```

### Frequency Adjustment Algorithm

```python
def _adjust_frequency(self):
    """Dynamically adjust polling interval based on CPU load"""
    cpu_usage = self._get_cpu_usage()

    if cpu_usage < self.CPU_LOW_THRESHOLD:
        new_interval = self.FREQ_HIGH    # 1 sec
    elif cpu_usage <= self.CPU_HIGH_THRESHOLD:
        new_interval = self.FREQ_NORMAL  # 2 sec
    else:
        new_interval = self.FREQ_LOW     # 4 sec

    if new_interval != self._interval:
        self._interval = new_interval
        self._timer.setInterval(self._interval * 1000)
```

### Trigger Timing

```python
# Check every 10 ticks in _execute_tick()
def _execute_tick(self):
    self._last_cpu_check += 1
    if self._last_cpu_check >= self._cpu_check_interval:
        self._last_cpu_check = 0
        self._adjust_frequency()
    # ... execute actual polling tasks
```

### CPU Detection

```python
def _get_cpu_usage(self):
    """Get current system CPU usage"""
    try:
        import psutil
        return psutil.cpu_percent(interval=0.1)
    except ImportError:
        return self.CPU_LOW_THRESHOLD  # Keep low freq if psutil unavailable
```

### Design Highlights

| Feature | Implementation |
|---------|---------------|
| **Smooth transitions** | Check every 10 ticks to avoid frequent switching |
| **Graceful degradation** | Returns low threshold when `psutil` unavailable |
| **Non-invasive** | Only adjusts `self._timer.setInterval()` internally |

## Effect

| Scenario | Before | After | CPU Saved |
|----------|--------|-------|-----------|
| Idle (CPU < 30%) | 2 sec | 1 sec | UI more responsive |
| Normal (30-60%) | 2 sec | 2 sec | No change |
| Heavy load (> 60%) | 2 sec | 4 sec | ~50% polling overhead reduction |

## Impact

- **Modified**: `ui/core/polling_manager.py`
- **New constants**: `FREQ_HIGH`, `FREQ_NORMAL`, `FREQ_LOW`, `CPU_LOW_THRESHOLD`, `CPU_HIGH_THRESHOLD`
- **New attributes**: `_interval`, `_last_cpu_check`, `_cpu_check_interval`
- **New methods**: `_adjust_frequency()`, `_get_cpu_usage()`
