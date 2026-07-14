# 04 State Machine System — Development Stage Audit (Node Track + Edge Track)

This entry audits the true development maturity and integration depth of the BNOS state machine system (standalone package at `ui/core/state/`) as of 2026-07-15, separating "SM defined + unit-test green" from "truly wired into business code".

---

## 1. Source Tree

```
ui/core/state/
├── __init__.py                      # Public exports (NodeStateManager / StateMachine / ...)
├── base.py                          # Common infra: Transition dataclass + StateMachine(QObject)
├── transition_table.py              # Data-driven TRANSITION_TABLE (Phase 2)
├── node_state_manager.py            # Big manager: orthogonal composition + event dispatch + guards + signals + debounce + audit
├── node_state_action_service.py     # Real I/O executor layer (stub; full actions not yet wired)
├── node_runtime.py                  # Phase 1 NodeRuntimeSM (node runtime)
├── node_runtime_bridge.py           # Phase 1 bridge: node_process.py ↔ NodeRuntimeSM
├── composite_lifecycle.py           # Phase 3 CompositeLifecycleSM (composite lifecycle)
├── canvas_mode.py                   # Phase 4 CanvasModeSM (canvas interaction mode machine)
├── edge_interaction.py              # Phase 4 EdgeInteractionSM (edge interaction state machine)
├── route_cache.py                   # RouteCache: atomic config writes + PendingWrites + Transaction
├── state_validator.py               # Combined-state validity checks (is_valid_combined_state / validate_all_states)
├── orthogonal/                      # Orthogonal sub-SMs (3 dimensions for NodeStateManager)
│   ├── node_membership.py           #   MembershipSM: STANDALONE / CHILD_VISIBLE / CHILD_HIDDEN / COMPOSITE_NODE
│   ├── node_visibility.py           #   VisibilitySM: VISIBLE / HIDDEN / TRANSPARENT
│   └── node_connection.py           #   ConnectionSM: UpstreamState × DownstreamState
└── tests/                           # 7 test files
    ├── test_base.py                 #   StateMachine base
    ├── test_node_runtime.py         #   Phase 1: 13 cases
    ├── test_composite_lifecycle.py
    ├── test_canvas_mode.py
    ├── test_edge_interaction.py     #   Phase 4: 8 cases
    └── test_phase2_state_manager.py # Phase 2: TRANSITION_TABLE + Guards
```

---

## 2. Node Runtime Track — Stage-by-Stage Conclusion

| Phase | SM / Module | Defined + Tested | Real Business Integration | Maturity |
|---|---|---|---|---|
| **Phase 1 NodeRuntimeSM** | `node_runtime.py` 6 states STOPPED/STARTING/RUNNING/IDLE/STOPPING/CRASHED + 14 transition events | ✅ 13 tests covered | ✅ **node_process.py 10 live calls** transition_state(start/start_ok/start_fail/stop/stop_ok/stop_fail/child_resume/child_idle/crash) | 🟢 Production Ready |
| **Phase 1 Bridge** | `node_runtime_bridge.py` ensure_sm/get_state/transition_state — SM transparently attached to `node_info["_sm"]`, syncs status field | ✅ Zero extra state footprint | ✅ node_process.py L15 import + L401/L492/L500/L513/L530/L565/L572/L731/L735/L746/L749/L754 entire lifecycle | 🟢 Production Ready |
| **Phase 3 CompositeLifecycleSM** | 8 states INACTIVE/STARTING/ACTIVE/STOPPING/RESTARTING/ERROR/CRASHED/REMOVING + 15 transitions + `is_active` / `is_restartable` properties | ✅ Full tests | ✅ **composite_node.py 4 live integrations**: L3545 instantiation → `self._lifecycle[comp_id]`; L3552 `is_active` delegation; L3266 TOCTOU guard `not lc.is_restartable`; L3387 STOP guard `lc.is_active`; L3040 decompress `lc.handle("decompress")` | 🟢 Production Ready |
| **Phase 2 Orthogonal SMs (×3)** | MembershipSM × VisibilitySM × ConnectionSM; transition_table.py defines Guards (`guard_not_running`, `guard_composite_children_not_running`) + data-driven TRANSITION_TABLE | ✅ test_phase2_state_manager.py covers register/event dispatch/combined-state | ⚠️ **Partial integration**: NodeStateManager instantiated in composite_node/canvas_view/canvas_layout; internal dispatch already handles 8 events: compress/decompress/expand/collapse/connect_upstream/disconnect_upstream. BUT NodeStateActionService "real file-I/O actions + child traversal" still flows through legacy composite_node.py paths. | 🟡 Mid-Integration |
| **Phase 2 NSM Render-Gate API** | `register_edge / unregister_edge / is_edge_valid_static / get_all_edges` + _port_alias_equal (data↔default / node_output↔default) | ✅ Render-gate actively uses it (per changelog entry #01) | ✅ canvas_edge_render_gate.py L28 import → `NodeStateManager.is_edge_valid_static`; canonical_edge_resolver.py consumes the alias-equivalence rules | 🟢 Production Ready |
| **RouteCache (under state package)** | `begin/commit/rollback/flush`; PendingWrites; Transaction context manager | ✅ expand/collapse flows in composite_node rely on exact `begin → PhaseB CLEAR → PhaseC CREATE → FLUSH → ASSERT` ordering | ✅ composite_node.py atomic writes + node_state_manager.py self-owned route_cache | 🟢 Production Ready |

### Node Track Integration Points (real imports = in-use)

```
node_process.py      L15  from ui.core.state.node_runtime_bridge import get_state, transition_state
composite_node.py    L39  from ui.core.state.composite_lifecycle import CompositeLifecycleSM
composite_node.py    L41  from ui.core.state.node_state_manager import NodeStateManager  → L170 instantiate
canvas_view.py       L286 from ui.core.state.node_state_manager import NodeStateManager  → instantiate
canvas_layout.py     L738 from ui.core.state.node_state_manager import NodeStateManager  → lazy import
canvas_edge_render_gate.py  L28  import NodeStateManager  → is_edge_valid_static call
```

---

## 3. Edge Interaction Track — Stage-by-Stage Conclusion

| Phase | SM / Module | Defined + Tested | Real Business Integration | Maturity |
|---|---|---|---|---|
| **Phase 4 EdgeInteractionSM** | 6 states IDLE/HOVERING_HANDLE/HOVERING_WP/HOLDING_HANDLE/DRAGGING_NEW_WP/DRAGGING_WP + 14 events (hover_handle/hover_wp/leave/press_handle/long_press/release/press_wp) + complete docstring state diagram | ✅ 8 tests covered | 🔴 **0% integration**: edge_item.py still keeps the 8 legacy scattered boolean vars `_hovered_handle / _hovered_wp / _drag_wp_index / _drag_is_new / _press_pos / _press_on_handle / _long_press_fired / _long_press_timer`. All press/move/release handlers manipulate the old vars — EdgeInteractionSM is never instantiated. | 🟠 Defined, Awaiting Integration |
| **Phase 4 CanvasModeSM** | 6 modes NONE/SELECT/PAN/CONNECT/BOX_SELECT/EDIT + 14 transitions + `is_interacting` property | ✅ Full tests | 🔴 **0% integration**: canvas_view.py + drawing-tools layer contains NO CanvasModeSM instance. Modes are still controlled via raw strings/enums. | 🟠 Defined, Awaiting Integration |

### Current edge_item.py reality (vs EdgeInteractionSM design intent)

The **8 fragmented state variables that EdgeInteractionSM is meant to replace** all still remain in edge_item.py (last verified L122/L128–L132/L711/L721/L724/L802–L813/L829/L843/L874–L884/L908–L912/L937/L1024 manipulate the old variables):

| Legacy Variable | EdgeInteractionSM equivalent | Integration Progress |
|---|---|---|
| `_hovered_handle = -1` | `self.state == HOVERING_HANDLE` vs IDLE state guard | Not Started |
| `_hovered_wp = None` / `_drag_wp_index = None` | `HOVERING_WP` / `DRAGGING_WP` / `DRAGGING_NEW_WP` states | Not Started |
| `_drag_is_new` / `_press_pos` / `_press_on_handle` | HOLDING_HANDLE → DRAGGING_NEW_WP branch transitions | Not Started |
| `_long_press_fired` / `_long_press_timer` | HOLDING_HANDLE `long_press` event → DRAGGING_NEW_WP transition | Not Started |

---

## 4. Global Summary

```
Phase 1 NodeRuntimeSM          Def ✅ Tests ✅ Integration ✅ (10 call sites) — 100% Done   🟢
Phase 2 Orthogonal SMs + Guard Def ✅ Tests ✅ Partial integr. (instance + dispatch OK, actions legacy) — ~60% Done  🟡
Phase 3 CompositeLifecycleSM   Def ✅ Tests ✅ Integration ✅ (4 call sites + prop deleg.) — 100% Done   🟢
Phase 4 CanvasModeSM           Def ✅ Tests ✅ Integration ❌                       — 40% Done    🟠
Phase 4 EdgeInteractionSM      Def ✅ Tests ✅ Integration ❌                       — 40% Done    🟠
Render-Gate API (NSM)          Def ✅ In-use ✅                                        — 100% Done   🟢
RouteCache atomic writes       Def ✅ expand/collapse end-to-end ✅                 — 100% Done   🟢
```

## 5. Next-Step Priority Roadmap

| Priority | Work Item | Acceptance Criteria |
|---|---|---|
| P0 | **Wire EdgeInteractionSM into edge_item.py** | All 8 legacy state variables in edge_item.py deleted; mousePressEvent/mouseMoveEvent/mouseReleaseEvent drive a single `self._eism.handle("press_handle")` flow; all branching replaced by `self._eism.state` dispatch. Original 8 unit tests green + 5+ new integration regression tests (hover / long-press / drag / release / leave safety). |
| P1 | **Wire CanvasModeSM into canvas_view.py + tools** | Every mode switch in the drawing-tools stack flows through `canvas_mode_sm.handle("enter_select"/"start_connect"/...)`; raw string mode values are banned from the call path. |
| P2 | **Wire full NodeStateActionService.invoke** | Every `action` in TRANSITION_TABLE has a concrete implementation under NodeStateActionService; migrate expand/collapse/compress/decompress/connect/disconnect flow-code out of composite_node.py legacy paths into Guard + Action driven; composite_node expand/collapse becomes a thin shell calling NodeStateManager.handle_event(...). |
| P3 | **RouteCache consistency self-test on boot** | After a project loads, run validate_all_states(node_clusters + composite + configs) once; failures emit ERROR + GUI toast. |

---

## 6. State-Machine-Related Business Files

| File | Role |
|---|---|
| `ui/core/state/` (15 modules + 6 tests) | Entire state machine system |
| `ui/core/node/node_process.py` | Phase 1 NodeRuntimeSM real integration (10 lifecycle events) |
| `ui/core/node/composite_node.py` | Phase 3 CompositeLifecycleSM wiring + NodeStateManager instantiation + RouteCache orchestration |
| `ui/canvas/canvas_view.py` | Phase 2 NodeStateManager canvas-scoped instantiation |
| `ui/canvas/mixins/canvas_edge_render_gate.py` | NSM.is_edge_valid_static render-gate consumer |
| `ui/canvas/mixins/canvas_layout.py` | NSM lazy import (layout-load time hook) |
