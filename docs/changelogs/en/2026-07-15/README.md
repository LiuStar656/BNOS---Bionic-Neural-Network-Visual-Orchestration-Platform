# 2026-07-15 Update Overview

[Back to Index](../README.md)

---

## Update Index

- [01 Composite Node Dashed Line Fix & Port Alias Normalization](#01-composite-node-dashed-line-fix--port-alias-normalization)
- [02 MUTEX-VIOLATION Assertion Timing Fix](#02-mutex-violation-assertion-timing-fix)
- [03 Log Noise Reduction & Steady-State Log Tiering](#03-log-noise-reduction--steady-state-log-tiering)
- [04 State Machine System Development Stage Audit (Node Track + Edge Track)](#04-state-machine-system-development-stage-audit-node-track--edge-track)

---

## 01 Composite Node Dashed Line Fix & Port Alias Normalization

See [01_Composite_Node_Dashed_Line_Fix_and_Port_Alias_Normalization.md](./01_Composite_Node_Dashed_Line_Fix_and_Port_Alias_Normalization.md).

### Summary

- **composite.json read path fix**: Removed the redundant `NODE_DIR_ROOT` concatenation in canonical_edge_resolver.py (`nodes/composite_nodes` → `composite_nodes`); COMPOSITE_INPUT/OUTPUT/INTERNAL authority edges now load correctly
- **Authority-set alias expansion**: When parsing composite.json external connections, both EdgeKey variants — input ports `{data, default}` and output ports `{node_output, default}` — are added to the CanonicalEdgeSet, providing backward compatibility with historical layouts
- **NodeStateManager alias equivalence**: `is_edge_valid_static` gained composite-edge data↔default / node_output↔default port-alias equivalence comparison
- **Unified write normalization**: `set_input_routing` / `set_output_routing` entry-points force standard internal names (data for input, node_output for output) and reverse-delete alias stale keys; resolves duplicate data+default entries in composite.json
- **Loose alias-aware cleanup**: `clear_input_routing` / `clear_output_routing` correctly delete standard-name + alias keys regardless of which alias the caller passes

---

## 02 MUTEX-VIOLATION Assertion Timing Fix

See [02_Mutex_VIOLATION_Assertion_Timing_Fix.md](./02_Mutex_VIOLATION_Assertion_Timing_Fix.md).

### Summary

- **Root cause**: Old ASSERT(disk read) → FLUSH(disk write) ordering. Assertion ran before RouteCache atomic flush, reading the transient disk state right after PhaseB CLEAR but before PhaseC new values were persisted → false positive MUTEX-VIOLATION + bogus rollback
- **Fix**: Both expand/collapse now run `PhaseB CLEAR → PhaseC CREATE → [PhaseD RouteCache.flush] → _assert_mutex_consistency`. Assertion reads the freshly-flushed disk values
- **Failure strategy adjusted**: After flush already persisted we no longer rollback (rollback only touches memory, making memory vs disk inconsistency worse). Only ERROR-level log is retained.
- **Impact**: Consecutive expand/collapse no longer throws AssertionError. Genuine manual corruptions also do not trigger mistaken rollbacks.

---

## 03 Log Noise Reduction & Steady-State Log Tiering

See [03_Log_Noise_Reduction_and_Steady_State_Log_Tiering.md](./03_Log_Noise_Reduction_and_Steady_State_Log_Tiering.md).

### Summary

- **Fallback scan interval**: `CANONICAL_SCAN_INTERVAL_MS` 3000ms → 10000ms (expand/collapse/load_layout/calibrate all trigger immediate scan independent of timer)
- **Render-Gate tiering**: noisy = ghost_edges > 0 ∨ broken_paths > 0 ∨ set size delta; noisy=True → INFO full summary + canonical/canvas set dump; noisy=False (steady idle) → one DEBUG summary line (no output by default)
- **infer_all_edges tiering**: need_attention = broken_paths > 0 ∨ stale_routes_cleared > 0; True→INFO, False→DEBUG
- **ScanStats field name correction**: `stats.stale_cleared` → `stats.stale_routes_cleared`, eliminating AttributeError
- **Effect**: Idle ≈ 0 log volume; user actions produce one full round; anomalies (ghost/broken/stale) retain full INFO dumps

---

## 04 State Machine System Development Stage Audit (Node Track + Edge Track)

See [04_State_Machine_System_Development_Stage_Audit.md](./04_State_Machine_System_Development_Stage_Audit.md).

### Summary

- **Node Track Maturity**: Phase 1 NodeRuntimeSM ✅ 100% (10 real transition_state call sites in node_process.py); Phase 3 CompositeLifecycleSM ✅ 100% (4 real integration sites in composite_node.py + is_active/is_restartable property delegation); Phase 2 Orthogonal SM Composition + TRANSITION_TABLE + Guards 🟡 ~60% (NodeStateManager instantiated in many places, event dispatch already accepts 8 events, but NodeStateActionService action layer still runs legacy paths); Render-Gate API ✅ 100% (canvas_edge_render_gate.py live-calls is_edge_valid_static); RouteCache ✅ 100% (expand/collapse end-to-end)
- **Edge Track Maturity**: Phase 4 EdgeInteractionSM 🟠 Definition/unit tests 100% complete BUT 0% business integration (edge_item.py still manipulates the 8 legacy boolean state variables — EdgeInteractionSM is never instantiated); CanvasModeSM 🟠 Definition/unit tests 100% complete BUT 0% business integration (canvas modes still driven by raw strings)
- **Source Tree**: `ui/core/state/` standalone package, 15 modules + 7 test files (base, NodeRuntime, CompositeLifecycle, CanvasMode, EdgeInteraction, phase2_state_manager)
- **Roadmap P0→P3**: P0 Wire EdgeInteractionSM → edge_item.py; P1 Wire CanvasModeSM → canvas_view; P2 Fully wire NodeStateActionService actions; P3 Boot-time validate_all_states self-test

---

## Files Changed

| File | Changes |
|------|---------|
| `ui/core/edge/canonical_edge_resolver.py` | Removed redundant `NODE_DIR_ROOT` from composite.json path; added port alias expansion for composite edges; tiered `infer_all_edges` logging; fixed `stale_cleared` → `stale_routes_cleared` field name |
| `ui/core/state/node_state_manager.py` | `is_edge_valid_static` gained composite-edge data↔default / node_output↔default alias equivalence comparison |
| `ui/canvas/mixins/canvas_connections.py` | `create_edge` creates composite edges under internal standard port names (data / node_output) |
| `ui/core/node/composite_node.py` | `set_input_routing` / `set_output_routing` entry normalization + alias stale-key cleanup; `clear_input_routing` / `clear_output_routing` loose alias matching; expand/collapse flows flush RouteCache BEFORE assertion; assertion failure no longer rolls back (ERROR log only) |
| `ui/canvas/mixins/canvas_edge_render_gate.py` | `CANONICAL_SCAN_INTERVAL_MS` 3_000 → 10_000; `_run_scan` gained noisy predicate + summary/set dump tiered logging |
| `ui/core/state/` (15 modules + 7 tests) + 6 integration call sites (node_process / composite_node / canvas_view / canvas_layout / canvas_edge_render_gate) | State machine system audit: Node Track Phases 1-3 production-ready, Phase 2 mid-integration; Edge Track Phase 4 defined & tests green, edge_item.py / canvas_view not yet wired |


---

**Last Updated**: 2026-07-15
