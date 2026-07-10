# Process Log Capture & DI Container Enhancement

## Overview

Targeted improvements addressing two issues identified in code review: insufficient debugging visibility (subprocess output discarded) and overly simplistic DI container (type-key-only dict). Subprocess output is now persisted to log files, and the DI container gains named registration, scope control, and service listing — all fully backward compatible.

## Core Changes

### 1. Subprocess stdout/stderr Log File Capture

**Problem**: Node subprocess `stdout` / `stderr` was discarded to `subprocess.DEVNULL`. When a node failed to start, there was zero log output to diagnose the issue — all you got was `exit=1`.

**Solution**: Redirect output to log files in the node directory. On startup failure, automatically read the log tails and include them in the error message.

Modified `ui/core/node_process.py`:

- **New `_rotate_log()`**: Automatically truncates logs over 5MB, keeping the tail half to prevent unbounded disk growth
- **New `_open_node_logs()`**: Creates `node_output.log` and `node_error.log` in the node directory on startup, with timestamp headers
- **New `_read_tail()`**: Reads the last N lines (default 50) of a log file, with encoding tolerance
- **Modified `start_node_process()`**:
  - Replaced all 4 `subprocess.DEVNULL` instances with log file handles
  - Startup failure path no longer calls meaningless `process.communicate()`; instead reads log file tails
  - On successful startup, closes parent-side log handles immediately after `Popen` (child has independent handle copies)
  - Exception path has fallback log handle cleanup
- **New public API `get_node_log_tail(node_path)`**: UI panels can call this anytime to fetch live stdout/stderr tails of running nodes

### 2. DI Container Enhancement

**Problem**: `DIContainer` internally used `Dict[Type, Any]` with class types as keys. This meant: (a) no way to register multiple implementations of the same interface; (b) no string-name registration (e.g., for third-party interfaces); (c) factories were always treated as singletons; (d) resolve failures only showed the type name with no hint of what was registered.

**Solution**: Refactored internal storage to composite key `(interface, name)`, added `register()` / `resolve_named()` / `list_registered()` methods, while keeping the old API signatures and semantics fully intact.

Modified `ui/core/di.py`:

- **Internal `_Key` composite key**: `(interface_type, name)`, where `name=None` is equivalent to the old unqualified registration
- **Unified `register(interface, instance_or_factory, *, name, scope)`**:
  - Named registration with `name="file"` — multiple implementations per interface
  - Scope `scope="transient"` — factory called fresh on every `resolve()`
  - Default `scope="singleton"` — cached singleton, identical to old behavior
  - Smart detection: callable non-class objects are treated as factory functions
- **Enhanced `resolve()`**:
  - `resolve(str)` — global lookup by name
  - `resolve(Type, name=...)` — type + name qualifier
  - `resolve(Type)` — backward compatible, equivalent to `resolve(Type, name=None)`
- **Enhanced `is_registered()`**: supports `is_registered("name")` string queries
- **`resolve_named(name)`**: convenience method for name-based resolution
- **`list_registered()`**: lists all registered services as `[(type, name, scope), ...]`
- **Enhanced `_not_found_msg()`**: on resolution failure, automatically lists all registered services (with names and scopes), dramatically improving debugging efficiency
- **Old API fully compatible**: `register_instance()` / `register_factory()` / `resolve()` / `is_registered()` signatures and semantics unchanged

## Test Updates

Modified `tests/test_di_container.py`:

- Retained all 6 original tests (`TestDIContainerBackwardCompat` class)
- Added 12 new tests covering:
  - Named registration and name-based resolution
  - Multiple implementations of the same interface
  - Transient scope (fresh instance every time)
  - Singleton scope (cached instance)
  - Invalid scope parameter rejection
  - `is_registered()` string queries
  - `list_registered()` service listing
  - Error messages include registered service list on resolution failure

## Affected Files

| File | Change Type |
|------|------------|
| `ui/core/node_process.py` | 4 new helper functions, modified `start_node_process()` output redirection |
| `ui/core/di.py` | Refactored `DIContainer` internal storage, added `register()` / `resolve_named()` / `list_registered()` |
| `tests/test_di_container.py` | Retained old tests + 12 new tests |
