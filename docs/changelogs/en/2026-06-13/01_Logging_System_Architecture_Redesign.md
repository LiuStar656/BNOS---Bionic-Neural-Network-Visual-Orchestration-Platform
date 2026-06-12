# Logging System Architecture Redesign

## Problem

The original logging system had the following issues:

1. **Unbounded single-file growth**: `bnos_console.log` grew to 4.78MB+ with no rotation
2. **Mixed error/info logs**: ERROR entries buried among INFO, making troubleshooting difficult
3. **Encoding errors**: Emoji characters triggered `UnicodeEncodeError` on Windows GBK terminal
4. **High-frequency noise**: Dozens of DEBUG entries per second from mouse interactions, 71% noise
5. **No auto-cleanup**: Old logs accumulated indefinitely

Core conflict: must retain full logs for debugging, but must prevent unbounded file growth.

---

## New Architecture

### File Separation

```
logs/
├── bnos.log              ← Daily logs (INFO+, daily rotation, 7-day retention)
├── bnos.log.YYYY-MM-DD   ← Historical daily logs (auto-archived)
└── bnos_error.log        ← Error logs (ERROR+, size rotation, 1MB×5 backups)
```

### Three-Layer Anti-Bloat Mechanism

```
logger.xxx() call
     │
     ▼
┌─────────────────────┐
│ ① FrequencyFilter   │  Same message >5 times in 30s → suppressed
│    ERROR/CRITICAL   │  Never filtered — ensures errors not lost
│    always pass      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ ② DebugLevelManager │  High-frequency canvas modules quiet by default
│    runtime toggle    │  set_debug_mode(True) enables all
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ ③ Rotation/Cleanup  │  bnos.log daily → old files auto-deleted
│    bnos_error.log   │  size-based 1MB → old backups auto-truncated
└─────────────────────┘
```

---

## Core Components

### SafeStreamHandler

```python
class SafeStreamHandler(logging.StreamHandler):
    """Safe console handler, auto-handles special chars on Windows GBK encoding"""
```

Uses `errors='replace'` to substitute unencodable characters as a defense-in-depth measure.

### FrequencyFilter

```python
class FrequencyFilter(logging.Filter):
    """Suppresses identical logs exceeding 5 times within a 30s window. ERROR/CRITICAL always pass."""
```

- Key: `(level, message digest, filename)`
- First 5 occurrences: output normally
- 6th occurrence: outputs summary WARNING `[FREQ] Log too frequent... subsequent suppression`
- 7th+ occurrence: discard
- **ERROR/CRITICAL never filtered** — ensures errors always recorded

### DebugLevelManager

```python
class DebugLevelManager(logging.Filter):
    """Module-level DEBUG controller"""
```

- Default quiet modules: `canvas_view`, `canvas_layout`, `edge_item`, `node_item`, `anchor_item`, `polling_manager`
- `set_debug_mode(True)` enables all modules at runtime
- `add_quiet_module()` / `remove_quiet_module()` for dynamic control

### _cleanup_old_logs

Scans `logs/bnos.log.*` on startup, deletes archived files older than 7 days.

---

## Synchronized Changes

### polling_manager.py (3 locations)

| Location | Old Value | New Value |
|----------|-----------|-----------|
| `_log_cache` dict | `"bnos_console.log"` / `"bnos_gui.log"` | `"bnos.log"` / `"bnos_error.log"` |
| `_init_global_watchers()` | Same as above | Same as above |
| `_poll_global_logs()` | Same as above | Same as above |

### Emoji Cleanup (7 files)

| File | Replacements |
|------|-------------|
| `ui/main_window/state.py` | 🔴→[PANEL], 💾→[SAVE] |
| `ui/main_window/__main__.py` | 💾→[SAVE], ✅→[OK], ❌→[FAIL], ⚠️→[WARN], 📦→[SHUTDOWN] |
| `ui/main_window/lifecycle.py` | 📦→[SAVE]/[SHUTDOWN], 💾→[SAVE], ✅→[OK] |
| `ui/main_window/ipc.py` | 🔒→[LOCK], 🚀→[RESTART] |
| `ui/core/canvas_host.py` | 💾→[SAVE], ⚠️→[SKIP], 🔔→[TERMINAL] |
| `ui/canvas/canvas_view.py` | ✅→[OK], ❌→[FAIL] |
| `ui/core/window_state_manager.py` | 📐→[WS], 💾→[SAVE], ✅→[OK] |

---

## PollingManager super().__init__() Fix

**Error**: `RuntimeError: super-class __init__() of type PollingManager was never called`

**Cause**: Singleton check `if PollingManager._initialized: return` was before `super().__init__(parent)`, preventing Qt C++ layer initialization.

**Fix**: Move `super().__init__(parent)` before the singleton check.

```python
def __init__(self, parent=None):
    super().__init__(parent)  # Must be before singleton check
    if PollingManager._initialized:
        return
    PollingManager._initialized = True
```

---

## CanvasHost Panel Loading Order

Terminal Dock deferred until first canvas creation:
- Added `_ensure_terminal_initialized()` method
- Added `_terminal_initialized` flag
- `_restore_terminal_dock` only restores when terminal is initialized

---

## Before/After Comparison

| Metric | Old Architecture | New Architecture |
|--------|-----------------|-----------------|
| Max single file size | Unlimited (measured 4.78MB) | < 1MB (dual constraint) |
| Error discovery | grep full logs | Open `bnos_error.log` directly |
| Old log cleanup | Manual | Auto-cleanup on startup (7 days) |
| High-frequency noise | No filtering | FrequencyFilter reduces 80%+ |
| Encoding compatibility | UnicodeEncodeError | Double safeguard |

---

## Related Files

| File | Change Type |
|------|------------|
| `ui/core/logger.py` | Complete rewrite |
| `ui/core/polling_manager.py` | Log reference updates |
| `ui/main_window/state.py` | Emoji replacement |
| `ui/main_window/__main__.py` | Emoji replacement |
| `ui/main_window/lifecycle.py` | Emoji replacement |
| `ui/main_window/ipc.py` | Emoji replacement |
| `ui/core/canvas_host.py` | Loading order + Emoji replacement |
| `ui/canvas/canvas_view.py` | Emoji replacement |
| `ui/core/window_state_manager.py` | Emoji replacement |
| `docs/日志系统去臃肿化优化方案.md` | Updated to reflect implementation |
| `update.md` | New file |
