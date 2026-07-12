# 11 `except Exception: pass` Comprehensive Governance

## Overview

Eliminated 100 `except Exception: pass` patterns project-wide, replacing them with precise exception types. The largest single code quality governance in BNOS history.

---

## I. Why Governance

`except Exception: pass` silently swallows **all** exceptions including `KeyboardInterrupt`, `SystemExit`, and `MemoryError`. In runtime error scenarios, this creates a "nothing happened and we don't know why" black hole experience.

---

## II. Scope

| | Before | After |
|------|:---:|:---:|
| `except Exception: pass` | **100** / 25 files | **0** |
| Files modified | — | **26** |

---

## III. Exception Type Mapping

| Scenario | New Exception Type | Count |
|------|------|:---:|
| psutil process access | `(NoSuchProcess, AccessDenied)` | ~16 |
| File I/O / PID read-write | `OSError` | ~35 |
| Qt graphics item operations | `(AttributeError, RuntimeError)` | ~25 |
| Process management (kill/terminate) | `(ProcessLookupError, OSError)` | ~8 |
| JSON config read-write | `(ValueError, OSError)` | ~10 |
| Other (group/dialog/layout) | `RuntimeError` | ~6 |

---

## IV. Top 5 Worst Files

| File | Before | After |
|------|:---:|:---:|
| `system_resource_collector.py` | 10 | 0 |
| `composite_node.py` | 8 | 0 |
| `settings_dialog.py` | 6 | 0 |
| `edge_item.py` | 4 | 0 |
| `node_config_dialog.py` | 3 | 0 |

---

## V. Principle

Each replacement follows "only catch what can actually happen":
- File operations → `OSError` (not `Exception`)
- Exited process → `ProcessLookupError` (not `Exception`)
- Destroyed Qt object → `RuntimeError` (not `Exception`)
- psutil permission denied → `AccessDenied` (not `Exception`)

Doesn't mask bugs, while still gracefully handling runtime boundary conditions.
