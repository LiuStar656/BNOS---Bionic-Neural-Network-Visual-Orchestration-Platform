# State Machine System

## Problem

Multiple modules in the project had implicit state management logic using bare string comparisons and scattered bool flags, causing:
- No validation on state transitions (e.g., duplicate start, illegal stop)
- TOCTOU race conditions (state could change between check and action)
- Resource leaks (exception paths not cleaned up)
- Inconsistent state values (3 contradictory status string sets coexisting)

## Design

Created an independent state machine package under `ui/core/state/`, zero business dependencies, based on `QObject` + `Signal` architecture.

### State Machine Base (`base.py`)

```python
class StateMachine(QObject):
    """Generic finite state machine based on QObject + Signal."""
    state_changed = Signal(str, str)  # (old_state, new_state)

    def handle(event: str) -> bool    # Trigger event, returns success
    def can(event: str) -> bool       # Read-only check (no side effects)
    def reset() -> None               # Reset to initial state
    def get_allowed_events() -> list  # Get currently allowed events
```

`Transition` dataclass: `event` / `source` / `target` / `guard` / `action`, with `"*"` wildcard support.

### Phase 1: NodeRuntimeSM — Node Runtime State Machine

File: `ui/core/state/node_runtime.py`

```
STOPPED → STARTING → RUNNING ⇄ IDLE
                            ↓ crash
                         CRASHED
STARTING → CRASHED (timeout)
RUNNING → STOPPING → STOPPED
STOPPING → CRASHED (kill failed)
CRASHED → STARTING (retry)
```

- 6 states (`NodeRuntimeState` str Enum)
- 14 transition rules
- Unifies 3 contradictory status value sets across `node_process.py` / `node_control_service.py` / `node_startup_queue.py`

### Phase 2: CompositeLifecycleSM — Composite Node Lifecycle State Machine

File: `ui/core/state/composite_lifecycle.py`

```
CREATED → STARTING → RUNNING → STOPPING → STOPPED → STARTING (restart)
                ↓ timeout/err    ↓ crash     ↓ kill_fail
             CRASHED ←───────────────────────┘
CREATED/STOPPED/CRASHED → REMOVING → REMOVED (decompress)
```

- 8 states
- 15 transition rules
- Properties: `is_active`, `is_terminal`, `is_restartable`

### Phase 3: CanvasModeSM — Canvas Interaction Mode State Machine

File: `ui/core/state/canvas_mode.py`

```
NORMAL ⇄ CONNECTING
NORMAL ⇄ PANNING
NORMAL ⇄ BOX_SELECTING
NORMAL ⇄ SINGLE_SELECT
```

- 6 modes (`CanvasMode` str Enum)
- 14 transition rules
- Exclusion rules: CONNECTING blocks PANNING; BOX_SELECTING blocks CONNECTING

### Phase 4: EdgeInteractionSM — Edge Interaction State Machine

File: `ui/core/state/edge_interaction.py`

```
IDLE → HOVERING_HANDLE → HOLDING_HANDLE → DRAGGING_NEW_WP
IDLE → HOVERING_WP → DRAGGING_WP
```

- 6 states
- 8 transition rules
- `is_interacting` property distinguishes interaction from idle

## Tests

5 test files, 52 unit tests, all passing:

| File | Tests |
|------|-------|
| `test_base.py` | 11 |
| `test_node_runtime.py` | 13 |
| `test_composite_lifecycle.py` | 10 |
| `test_canvas_mode.py` | 10 |
| `test_edge_interaction.py` | 8 |

## Modified Files

| File | Change |
|------|--------|
| `ui/core/state/__init__.py` | New: exports StateMachine, Transition |
| `ui/core/state/base.py` | New: state machine base class |
| `ui/core/state/node_runtime.py` | New: NodeRuntimeSM + NodeRuntimeState |
| `ui/core/state/composite_lifecycle.py` | New: CompositeLifecycleSM + CompositeLifecycleState |
| `ui/core/state/canvas_mode.py` | New: CanvasModeSM + CanvasMode |
| `ui/core/state/edge_interaction.py` | New: EdgeInteractionSM + EdgeInteractionState |
| `ui/core/state/tests/test_base.py` | New: 11 tests |
| `ui/core/state/tests/test_node_runtime.py` | New: 13 tests |
| `ui/core/state/tests/test_composite_lifecycle.py` | New: 10 tests |
| `ui/core/state/tests/test_canvas_mode.py` | New: 10 tests |
| `ui/core/state/tests/test_edge_interaction.py` | New: 8 tests |
