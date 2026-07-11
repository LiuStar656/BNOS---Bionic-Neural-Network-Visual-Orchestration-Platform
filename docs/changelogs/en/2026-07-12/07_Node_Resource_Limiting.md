# 07 Node Resource Limiting

## Overview

Added cross-platform node resource limiting capability to BNOS. Users can declare a `resource_limit` field in the node's `config.json` to cap CPU usage and memory consumption for that node's process. The underlying implementation automatically selects the best mechanism per OS: Linux cgroups v2, Windows Job Objects, macOS nice priority.

---

## New Files

| File | Description |
|------|-------------|
| `ui/core/system/resource_limit.py` | Cross-platform resource limiting core component (357 lines) |
| `tests/test_resource_limit.py` | Unit tests (21 cases, ~140 lines) |

---

## Architecture

### Class Hierarchy

```
ResourceLimit (ABC)                           ← Abstract base: priority + affinity + hard limit interface
├── _LinuxResourceLimit                       ← cgroups v2: cpu.max + memory.max
├── _WindowsResourceLimit                     ← Job Objects: CPU Rate Control + ProcessMemoryLimit
└── _DarwinResourceLimit                      ← macOS: priority only (hard limits unsupported)
```

### Factory Function

```python
from ui.core.system.resource_limit import create_resource_limit

limit = create_resource_limit(pid, config["resource_limit"])
applied = limit.apply()
# → ["priority=below_normal", "memory_mb=4096", "cpu_percent=200"]
```

### config.json Fields

| Field | Type | Description | Linux | Windows | macOS |
|------|------|-------------|:---:|:---:|:---:|
| `priority` | `string` | Process priority | nice | PriorityClass | nice |
| `cpu_affinity` | `list[int]` | Bind to CPU cores | ✅ | ✅ | ignored |
| `cpu_percent` | `int` | CPU cap (100 = 1 core) | cgroups | JobObject | ignored |
| `memory_mb` | `int` | Memory hard limit (MB) | cgroups | JobObject | ignored |

### Priority Mapping

| Value | Linux (nice) | Windows (PriorityClass) |
|-------|-------------|------------------------|
| `"low"` | 19 | IDLE |
| `"below_normal"` | 10 | BELOW_NORMAL |
| `"normal"` | 0 | NORMAL |
| `"above_normal"` | -5 | ABOVE_NORMAL |
| `"high"` | -10 | HIGH |

---

## Key Design Decisions

### Lazy Process Acquisition

`ResourceLimit.__init__` no longer fetches `psutil.Process` during construction — deferred to `apply()` stage. Non-existent PIDs degrade gracefully instead of raising exceptions.

### Cross-Platform Graceful Degradation

- macOS lacks hard CPU/memory limiting → logs only, does not block node launch
- Windows/Linux without admin/root privileges → logs warning, does not block pipeline
- CPU affinity silently ignored on macOS

### Context Manager Support

```python
with create_resource_limit(pid, config) as limit:
    limit.apply()
    # Auto-cleanup on exit (no explicit cleanup needed currently, but interface reserved)
```

---

## Modified Files

| File | Type | Description |
|------|------|-------------|
| `ui/core/system/resource_limit.py` | New | Core component (357 lines) |
| `tests/test_resource_limit.py` | New | 21 test cases |
| `docs/guides/config_json_开发规范.md` | Updated | Added Chapter 8 resource_limit docs |
| `tools/config_json_开发规范.md` | Updated | Synced copy |

---

## Test Coverage

| Test Class | Cases | Coverage |
|-----------|:---:|------|
| `TestFactory` | 3 | Factory function, platform selection, config validation |
| `TestPriorityMapping` | 7 | 5 priority levels + unknown + empty skip |
| `TestContextManager` | 1 | `__enter__` / `__exit__` |
| `TestApplyNoProcess` | 1 | Graceful degradation on non-existent PID |
| `TestDarwinFallback` | 1 | macOS hard limits return empty |
| `TestInterfaceConsistency` | 4 | Method existence, return types |
| `TestConfigEdgeCases` | 4 | Negative, zero, partial configs |

```
tests/test_resource_limit.py ............ 21 passed
All 193 tests passing, zero regression
```

---

## Documentation Updates

`docs/guides/config_json_开发规范.md` and `tools/config_json_开发规范.md` have a new **Chapter 8: resource_limit — Node Resource Limiting**, including:

- Full documentation for 4 fields with macOS unsupported notes
- `priority` 5-level Linux/Windows comparison table
- Complete Stable Diffusion node config example
- Recommended configuration table for 7 usage scenarios (lightweight data processing → scientific computing)
- Python runtime invocation code example
- 5 cautionary notes (permissions, subprocess inheritance, memory undersizing risks, etc.)

---

**Last Updated**: 2026-07-12
