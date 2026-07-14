# 03 Log Noise Reduction & Steady-State Log Tiering

## Symptom

While idle (no user action), every 3 seconds an INFO-level "Canonical scan → dump authority edge set 40+ lines" burst appears. `bnos.log` inflates rapidly during long-running sessions:

```
[CANONICAL] infer_all_edges done: nodes=X composites=Y ...
[RENDER-GATE] scan  canonical=Z  canvas=Z  ...
    - canonical set (len=Z):
      EdgeKey(...), EdgeKey(...), ... (Z lines)
    - canvas set (len=Z):
      EdgeKey(...), EdgeKey(...), ... (Z lines)
```

## Root Cause Analysis

1. **Fallback scan interval too short**: `CANONICAL_SCAN_INTERVAL_MS = 3000`; at the default INFO logger level a full summary + dump is printed every 3s
2. **Every set delta classified as noisy**: Even legitimate deltas (expand/collapse where the set is supposed to change) dump at INFO. Under steady state (0 change, 0 ghost, 0 broken) the dump is useless for debugging
3. **infer_all_edges summary always INFO**: Steady-state scan result (scanned N nodes, Y composites successfully, 0 broken, 0 stale) does not need repeated INFO prints

## Fix 1 — Longer fallback scan interval

```python
# OLD: CANONICAL_SCAN_INTERVAL_MS = 3_000
# NEW: 10s fallback under steady state
CANONICAL_SCAN_INTERVAL_MS = 10_000
```

Key user actions (expand / collapse / load_layout / calibrate_edges / project open) all trigger a **full immediate scan via `schedule_immediate_scan()`**, independent of the timer. The 10-second interval is only a last-resort consistency check while fully idle. It does not affect normal interactive feedback latency.

## Fix 2 — Render-Gate log tiering

Introduce a composite `noisy` predicate. Only **on actual anomalies or real deltas** do we emit full set dumps at INFO level. Otherwise only a one-line DEBUG summary (not emitted under default INFO logger level):

```python
noisy = (
    bool(ghost_edges)                   # canvas ghost edges (no authority hit → dashed)
    or bool(stats.broken_paths)         # broken config paths
    or (pre_sizes["canonical"], pre_sizes["canvas"])
       != (len(canonical_set), len(canvas_set_from_canvas))
                                        # set sizes changed since last scan
)
# anomaly / delta → INFO (draw attention + full dump)
# steady idle   → DEBUG (no output under normal run)
summary_log = logger.info if noisy else logger.debug
set_log = logger.info if noisy else logger.debug
```

## Fix 3 — infer_all_edges summary tiering

```python
need_attention = (
    bool(stats.broken_paths)                 # broken config paths
    or (stats.stale_routes_cleared or 0) > 0  # stale routes purged (a write happened)
)
summary_log = logger.info if need_attention else logger.debug
summary_log("[CANONICAL] infer_all_edges done: %s", stats.as_log())
```

Steady-state healthy scans → DEBUG level, no INFO noise.

## Fix 4 — ScanStats attribute name typo

First version referenced `stats.stale_cleared`, but ScanStats defines the field as `stale_routes_cleared`. Runtime raised:
```
AttributeError: 'ScanStats' object has no attribute 'stale_cleared'
```
Corrected to `stats.stale_routes_cleared`.

## Effect

| Scenario | Log level | Output volume |
|---|---|---|
| Idle steady state (no user action) | DEBUG (not emitted by default) | ≈ 0 |
| User action expand/collapse / edge creation | INFO | 1 full summary + dump per action (2–3 orders of magnitude less than old 3s bursts) |
| Real anomaly (ghost edge / broken path / stale route) | INFO | Full dump for convenient diagnosis |
| 10s fallback scan | steady→DEBUG / anomaly→INFO | depends on state |

## Files Changed

| File | Changes |
|------|---------|
| `ui/canvas/mixins/canvas_edge_render_gate.py` | `CANONICAL_SCAN_INTERVAL_MS` 3000 → 10000; `_run_scan` gained tiered logging (noisy predicate + summary_log / set_log selection) |
| `ui/core/edge/canonical_edge_resolver.py` | `infer_all_edges` gained tiered logging (INFO only when broken_paths ∨ stale_routes_cleared > 0, else DEBUG); corrected `stats.stale_cleared` → `stats.stale_routes_cleared` |
