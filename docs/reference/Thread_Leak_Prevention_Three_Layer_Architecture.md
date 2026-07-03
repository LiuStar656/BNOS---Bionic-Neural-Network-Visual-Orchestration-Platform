# Thread Leak Prevention: Three-Layer Architecture Design

## 1. Problem Analysis

### 1.1 Thread Leak Points in Current Architecture

| Category | Component | Leak Cause |
|----------|-----------|------------|
| Bare thread | `NodeControlService._monitor_threads` | Creates anonymous `QThread()` per monitor (no parent), not stopped when panel closes |
| Bare timer | `EdgeItem._long_press_timer` | `QTimer()` without parent, leaks when edge deleted |
| Panel timer | `PerformancePanel._update_timer` (1000ms) | Depends on `destroyed` signal; may not fire during `deleteLater()` delay |
| Panel timer | `ResourceMonitorDock._update_timer` (3000ms) | No `closeEvent`, no `destroyed.connect`, only global cleanup |
| Panel timer | `NodeMonitorDock._resource_timer` (1000ms) | `closeEvent` unreliable for non-top-level widgets |
| Global singleton | `PollingManager._worker_thread` | Module teardown order undefined; QApplication may be already destroyed |
| Global singleton | `startup_queue._running_workers` | Not explicitly stopped on exit |

### 1.2 UI Lag Root Cause

7 dock panels collectively operate **~10 independent QTimers** firing on the main thread event loop:
- 3–5 timer callbacks compete for CPU per frame
- Each callback includes UI updates (chart redraw, list refresh, text updates)
- 5 panels open simultaneously = event loop ~15–25% consumed by timer callbacks

---

## 2. Design: Photoshop-Inspired Three-Layer Defense Architecture

Photoshop's core philosophy: **Never create temporary threads. Never do temporary cleanup. All resources are managed at the architectural level, not patched "on close."**

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 0: Global Infrastructure (created at init, destroyed at exit) │
│  ┌─────────────────┐  ┌──────────────────┐                   │
│  │   ThreadPool     │  │ UpdateScheduler  │                   │
│  │  (fixed pool)    │  │  (single timer)   │                   │
│  │  CPU-count threads│  │  1 QTimer·shared │                   │
│  └────────┬────────┘  └────────┬─────────┘                   │
│           │                    │                              │
│    Single global instance  Single global instance             │
│    Created at startup      Created at startup                │
│    Destroyed at exit       Destroyed at exit                 │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Base Class Contract (track on create, release on destroy) │
│  ┌──────────────────────────────────────┐                    │
│  │  LifecycleManaged (Mixin)            │                    │
│  │  ───────────────────────────────     │                    │
│  │  _resources: List[QObject]          │ ← Track all child   │
│  │  _register_resource(res)            │     resources       │
│  │  dispose() → for r in _resources:   │ ← Release all       │
│  │      stop() / deleteLater()         │                    │
│  └──────────────────────────────────────┘                    │
│  ┌──────────────────────────────────────┐                    │
│  │  DockPanelBase (QWidget + LCM)       │                    │
│  │  ───────────────────────────────     │                    │
│  │  Auto destroyed.connect(dispose)     │ ← Zero-miss         │
│  │  Auto update_scheduler.subscribe()   │ ← Unified timer    │
│  └──────────────────────────────────────┘                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Runtime Detection (defensive, close the backdoor) │
│  ┌──────────────────────────────────────┐                    │
│  │  Assert all resources released on exit                    │
│  │  if _resources: log WARNING          │                    │
│  │  Dev mode: assert not _resources     │                    │
│  └──────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Component Design

### 3.1 ThreadPool — Global Fixed Thread Pool

**File**: `ui/core/thread_pool.py`

```
ThreadPool (QObject, singleton)
├── _pool: QThreadPool (Qt native, fixed CPU-count threads)
├── run_task(fn, on_done=None) → Submit to pool
├── cancel(task_id) → Cancel a task
└── shutdown() → Wait for all tasks to complete
```

**Principles**:
- Thread count = `QThread.idealThreadCount()` (CPU count), never changes
- Never creates or destroys threads — created at startup, destroyed at exit
- All background short tasks (node monitoring, process waiting) submitted here
- Replaces all bare `QThread()` creation code

### 3.2 UpdateScheduler — Unified Update Scheduler

**File**: `ui/core/update_scheduler.py`

```
UpdateScheduler (QObject, singleton)
├── _timer: QTimer (1000ms fixed interval)
├── _subscribers: Dict[int, List[Callback]]
│     interval_ms → callback list
├── subscribe(owner, interval_ms, callback) → Register
├── unsubscribe(owner) → Unregister (auto via DockPanelBase.destroyed)
├── unsubscribe_all(interval_ms=None) → Bulk unregister
└── run() → Fire timer → iterate subscribers → call due callbacks
```

**Principles**:
- Only one QTimer, shared by all panels
- Panel creates: `subscribe(self, 1000, self._update_ui)`
- Panel destroys: auto `unsubscribe(self)` via `DockPanelBase.destroyed` signal
- Same-interval callbacks share a fire group, checked by `(current_tick % interval)`
- Replaces all per-panel QTimer instances

### 3.3 LifecycleManaged — Lifecycle Management Mixin

**File**: `ui/core/lifecycle_managed.py`

```
LifecycleManaged (Mixin)
├── _resources: List[Disposable]
├── _register_resource(resource) → Add to tracking
├── _unregister_resource(resource) → Remove from tracking
├── _schedule_update(interval_ms, callback) → Register with UpdateScheduler
├── _run_in_thread(fn, on_done=None) → Submit to ThreadPool
├── dispose() → Stop all resources, unregister from scheduler
│       ├── for r in _resources: r.stop() / r.quit()
│       ├── update_scheduler.unsubscribe(self)
│       └── _resources.clear()
└── is_disposed() → Check if already cleaned up
```

**Principles**:
- Any component creating QTimer or QThread inherits this Mixin
- `_register_resource()` called immediately on resource creation
- `dispose()` auto-called on `destroyed` signal
- `dispose()` is idempotent — safe to call multiple times
- Dev mode: `assert not _resources` in `__del__`

### 3.4 DockPanelBase — Unified Dock Panel Base Class

**File**: `ui/core/dock_panel_base.py`

```
DockPanelBase (QWidget, LifecycleManaged)
├── Constructor: auto connect destroyed → dispose
├── set_title(title) → Set panel title
├── get_title() → Get panel title
└── dispose() → LifecycleManaged.dispose() + subclass cleanup
```

**Principles**:
- All dock panels inherit this class instead of `QWidget`
- Constructor auto-handles `destroyed → dispose` binding
- Subclasses only implement `_init_ui()` and business logic
- Subclasses use `_schedule_update()` instead of `QTimer.start()`
- Subclasses use `_run_in_thread()` instead of `QThread()`

---

## 4. Migration Checklist

### 4.1 New Files (4)

| File | Responsibility |
|------|---------------|
| `ui/core/thread_pool.py` | Global fixed thread pool, replaces all bare `QThread()` |
| `ui/core/update_scheduler.py` | Global single-timer scheduler, replaces all panel `QTimer` |
| `ui/core/lifecycle_managed.py` | Lifecycle management Mixin: `_register_resource()` + `dispose()` |
| `ui/core/dock_panel_base.py` | Unified dock panel base: QWidget + LifecycleManaged |

### 4.2 Files to Migrate (6)

| File | Migration |
|------|-----------|
| `ui/panels/performance_panel.py` | Inherit `DockPanelBase`, `_update_timer` → `_schedule_update()`, `_collector_thread` → `_run_in_thread()` |
| `ui/panels/resource_monitor_dock.py` | Inherit `DockPanelBase`, `_update_timer` → `_schedule_update()` |
| `ui/panels/node_monitor_dock.py` | Inherit `DockPanelBase`, `_resource_timer` + `_list_timer` → `_schedule_update()` |
| `ui/canvas/items/edge_item.py` | Add parent to `_long_press_timer`, stop in `dispose()` |
| `ui/core/node_control_service.py` | Bare `QThread()` in `_monitor()` → `thread_pool.run_task()` |

---

## 5. Expected Results

| Metric | Before | After |
|--------|--------|-------|
| Concurrent QThread count | Unbounded (create/destroy per operation) | Fixed CPU-count (created at startup) |
| Main thread QTimer count | ~10 independent | **1** unified scheduler |
| Post-close thread residue | Probabilistic (depends on deleteLater timing) | **Zero** (dispose stops synchronously) |
| Post-close timer residue | Probabilistic | **Zero** (dispose stops synchronously) |
| Exit assertion | None | `dispose()` asserts all resources released |
| Event loop timer load | ~15–25% (5 panels) | ~2% (single timer) |
| Architectural consistency | Per-panel ad-hoc management | Unified base class enforces contract |

---

## 6. Photoshop Design Correspondence

| Photoshop | BNOS |
|-----------|------|
| `ThreadPoolExecutor` (fixed size) | `ThreadPool` (QThreadPool) |
| `requestAnimationFrame` (single frame loop) | `UpdateScheduler` (single QTimer) |
| `IDisposable.Dispose()` | `LifecycleManaged.dispose()` |
| `Panel` base class | `DockPanelBase` |
| Exit assert `assert not _resources` | Dev mode `__del__` assert |
