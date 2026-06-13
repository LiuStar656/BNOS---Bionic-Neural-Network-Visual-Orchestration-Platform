# 【2026-06-13】V2.0.13 - Logging System Redesign & History Rollback

---

## Update List

### 1. Logging System Architecture Redesign

[View Details](./01_Logging_System_Architecture_Redesign.md)

- Dual-file separation: `bnos.log` (daily rotation) + `bnos_error.log` (size-based rotation, independent error storage)
- Three-layer anti-bloat: FrequencyFilter → DebugLevelManager → Rotation & Cleanup
- ERROR/CRITICAL never filtered, error logs independently queryable
- SafeStreamHandler for Windows GBK encoding compatibility
- Auto-cleanup of logs older than 7 days on startup

### 2. PollingManager super().__init__() Fix

- Fixed QObject C++ layer initialization crash in singleton mode
- Moved `super().__init__(parent)` before singleton check

### 3. CanvasHost Panel Loading Order Adjustment

- Terminal Dock deferred until first canvas creation
- Canvas panels loaded before terminal panel to reduce startup flicker

### 4. Emoji Cleanup

- All emoji in log calls replaced with `[TAG]` prefixes
- Completely resolved UnicodeEncodeError on Windows GBK terminal

### 5. Process Management Comprehensive Performance & Security Fix

[View Details](./03_Process_Management_Comprehensive_Fix.md)

- **Atomic Process Tree Kill**: `taskkill /F /T` ensures child processes terminate synchronously with parents, eliminating zombie processes
- **PID-Priority Detection**: `_is_pid_alive` uses `OpenProcess` for direct process liveness check, replacing full PowerShell scanning (10x+ performance improvement)
- **Stopped Node Skip**: `check_running_processes` skips stopped nodes without PID, reducing wasted polling
- **Monitor Thread Tracking & Cleanup**: `NodeControlService` monitor threads now have `finally` cleanup blocks to prevent thread leaks
- **NodeItem.dispose()**: Disconnects signals, stops timers, clears cache when nodes are removed from canvas — preventing signal/memory leaks
- **subprocess PIPE→DEVNULL**: Child process pipe buffers changed to DEVNULL, preventing pipe buffer blocking that causes process hangs

### 6. Photoshop-Style History Rollback

[View Details](./04_Photoshop_Style_History_Rollback.md)

- **Command Pattern**: CreateNodeCommand / DeleteNodeCommand / MoveNodeCommand / CreateEdgeCommand / DeleteEdgeCommand
- **HistoryManager Singleton**: Flat commands list + current_index pointer, supporting undo/redo/jump_to for jumping to any history state
- **HistoryPanel UI**: Visual history list, click any entry to jump to its corresponding state
- **Auto-Recording**: Edge creation/deletion auto-recorded with replay guard to prevent double execution
- **Precise Anchor Restoration**: `_resolve_anchor` prioritizes `_desired_target_port_name` for correct anchor lookup, fixing multi-port restoration errors

### 7. Resource Monitor and Other Bug Fixes

[View Details](./05_Resource_Monitor_and_Other_Bug_Fixes.md)

- **Resource Monitor Network Download 100% on Startup Fix**: Pre-warm `net_io_counters()` result into `_last_net_*` variables, first query diff is zero
- **Node Style Switch Size Not Updating Fix**: `DeviceCoordinateCache` invalidation timing fix + `_ensure_rect()` safety net
- **History Panel Menu Entry Addition**: Added 「History」 entry to Tools menu

---

## Main Updates

| Category | Update |
|----------|--------|
| **Logging Architecture** | Dual-file separation, three-layer anti-bloat, independent error storage |
| **Process Management** | Atomic process tree kill, PID-priority detection, pipe anti-blocking, thread leak fixes |
| **History Rollback** | Photoshop-style Command pattern + HistoryManager + HistoryPanel |
| **Bug Fixes** | PollingManager QObject init, resource monitor first-load 100%, node style switch size |
| **Panel Optimization** | CanvasHost loading order, history panel menu entry |
| **Encoding Compatibility** | Emoji cleanup + SafeStreamHandler double safeguard |

---

## Verification Results

- ✅ New log files `bnos.log` / `bnos_error.log` generated correctly
- ✅ Console output free of UnicodeEncodeError
- ✅ polling_manager global file watcher references synced
- ✅ All old log file references cleaned up
- ✅ Process tree atomically killed via `/F /T`, no zombie processes
- ✅ History rollback undo/redo correctly restores node positions, edges, and anchor bindings
- ✅ Resource monitor network download displays correctly on first load (no more 100%)
- ✅ Panel mode → Block diagram mode size switches correctly
