# 12 Startup Guards & Resource Monitor Two-Layer Architecture

## Overview

Two complementary features that improve system safety and monitoring clarity. Startup Guards enforce bidirectional mutual exclusion between composite nodes and their sub-nodes — preventing conflicting daemon-process states. The Resource Monitor redesign introduces a two-layer display architecture where the composite node's orchestrator process gets its own independent monitoring row with real PID and resource metrics, while sub-nodes appear as indented `[sub]` children rows.

---

## I. Startup Guards: Bidirectional Mutual Exclusion

Starting a standalone node that belongs to a running composite, or starting a composite whose sub-nodes are running independently, can create daemon-process conflicts. The guard system intercepts both paths and offers the user a choice.

### 1.1 Standalone Node → Composite Check

When a user starts a standalone node, the system checks whether that node belongs to a currently running composite.

- **If no conflict** → start normally.
- **If conflict detected** → a dialog presents 3 choices:

| Option | Behavior |
|--------|----------|
| **Cancel** | Abort the start, leave everything as-is |
| **Stop composite then start** | Gracefully stop the running composite (and all its sub-nodes), then start the standalone node |
| **Force start** | Start the standalone node regardless (the composite and sub-nodes keep running) |

### 1.2 Composite Node → Sub-Node Check

When a user starts a composite, the system checks whether any of its sub-nodes are already running independently (outside the composite context).

- **If no conflict** → start the composite normally.
- **If conflict detected** → prompt to stop the independently-running sub-nodes first, then proceed with composite start.

### 1.3 Files Changed

| File | Change |
|------|--------|
| `ui/core/node/composite_node.py` | New methods: `check_subnode_start()`, `check_composite_start()`, `stop_conflicting_subnodes()` |
| `ui/main_window/node.py` | Guard hook inserted into `start_selected_node_by_name()` |
| `ui/core/i18n/translation_keys.py` | +2 new translation keys |
| `ui/core/i18n/strings_cn.json` | +2 new CN entries |
| `ui/core/i18n/strings_en.json` | +2 new EN entries |

---

## II. Resource Monitor Two-Layer Architecture

### 2.1 Before vs After

**Before**: The composite node was merely a visual `=>` marker in the resource monitor. Sub-nodes were intermingled with regular standalone nodes — there was no distinction, and the orchestrator process itself was invisible.

**After**: The composite node's orchestrator process gets its own dedicated row with:
- Real **PID** (the orchestrator process ID)
- Real **CPU %** and **Memory** usage
- Real **Status** (Running / Idle / Error)

Sub-nodes are shown as indented `[sub]` rows beneath their parent composite, with `—` placeholders for resources (since they run inside the orchestrator process and their individual resource usage is tracked at the orchestrator level).

### 2.2 Display Format

```
▶ image_pipeline  PID=32604   12%  3.2GB  Running    ← orchestrator process
    inference [sub]             —     —     Idle       ← inside orchestrator
    preprocess [sub]            —     —     Idle
standalone_node                 5%   0.3GB  Running    ← regular node
    postprocess [sub]          85%   1.2GB  Running    ← sub-node running independently
```

- `▶` prefix marks the parent composite row (collapsible/expandable).
- `[sub]` tag marks a child row that belongs to a composite.
- Sub-nodes running **inside** the orchestrator show `—` for CPU/Memory and `Idle` for status (lifecycle managed by orchestrator).
- Sub-nodes running **independently** (standalone) show their own real PID and resource metrics.
- Standalone regular nodes have no prefix and display normally.

### 2.3 Files Changed

| File | Change |
|------|--------|
| `ui/panels/resource_monitor.py` | Two-layer row model: parent composite rows + indented `[sub]` children rows; PID/resource display logic for both layers |
| `ui/panels/resource_monitor_dock.py` | Dock-level integration for the new two-layer data model |
| `ui/panels/_shared/system_resource_collector.py` | Collector now reports orchestrator PID and resources separately from sub-node state |

---

## III. Test Status

All existing tests pass. No regressions in standalone node startup, composite node startup, or resource monitor display.
