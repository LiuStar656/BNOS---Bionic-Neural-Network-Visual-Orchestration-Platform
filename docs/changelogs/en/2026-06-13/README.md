# 【2026-06-13】V2.0.13 - Logging System Architecture Redesign

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

---

## Main Updates

| Category | Update |
|----------|--------|
| **Logging Architecture** | Dual-file separation, three-layer anti-bloat, independent error storage |
| **Bug Fix** | PollingManager QObject init order fix |
| **Panel Optimization** | CanvasHost loading order adjustment |
| **Encoding Compatibility** | Emoji cleanup + SafeStreamHandler double safeguard |

---

## Verification Results

- ✅ New log files `bnos.log` / `bnos_error.log` generated correctly
- ✅ Console output free of UnicodeEncodeError
- ✅ polling_manager global file watcher references synced
- ✅ All old log file references cleaned up

---

[← Back to Index](../README.md)
