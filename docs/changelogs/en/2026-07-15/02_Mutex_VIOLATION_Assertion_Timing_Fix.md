# 02 MUTEX-VIOLATION Assertion Timing Fix

## Error Symptom

At the end of the composite node expand / collapse flow an `AssertionError: MUTEX-VIOLATION` is raised, followed by `_rollback_cluster_state`:

```
AssertionError: MUTEX-VIOLATION expand ... node_clusters.json composite expanded=True but disk composite.json expanded=False (or vice versa)
```

## Root Cause — Assertion runs **before** RouteCache.flush

PhaseB/C in expand/collapse only write to the `RouteCache` in-memory buffer; the actual persistence to JSON on disk happens at PhaseD `RouteCache.flush()`. But the original mutex assertion was placed **right after PhaseC and before flush**:

```
❌ OLD order:
  PhaseB CLEAR     → RouteCache in-memory mark for clear
  PhaseC CREATE    → RouteCache in-memory mark for write
  ASSERT           → reads composite.json / listen_upper_file FROM DISK (still old values!)
  FLUSH            → finally flushes PhaseC new values out
  ROLLBACK(false positive) → assertion wipes correctly-routed data
```

Result: assertion reads the transient disk state **after PhaseB CLEAR but before PhaseC FLUSH**, producing a false-positive "expanded mismatch" and rollback empties out the RouteCache-orchestrated changes.

## Fix — FLUSH before ASSERT

```python
# ✅ NEW order:
PhaseB CLEAR → PhaseC CREATE → [PhaseD FLUSH to disk] → ASSERT reads disk
```

Core code:

```python
# Step 6: RouteCache.flush (atomic write all configs to disk)
# MUST run BEFORE mutex assertion! Otherwise assertion reads stale disk.
flushed = RouteCache.flush()
logger.info("[MORPH-EXPAND-SUMMARY] comp=%s PhaseD-FLUSH flushed_cfgs=%d", comp_id, flushed)

# Step 5.5: Hard mutex assertion (after expand, expanded=True must be consistent)
# NOTE: placed after flush so disk reflects the RouteCache-written values.
# No rollback on failure: flush has already atomically persisted.
mutex_assertion_ok = True
try:
    self._assert_mutex_consistency(comp_id, morph_list, expanded=True)
except AssertionError as ae:
    mutex_assertion_ok = False
    logger.error(
        "[MORPH-MUTEX-FAILED-EXPAND] %s (RouteCache already flushed=%d, skip rollback)",
        ae, flushed, exc_info=True,
    )
```

Identical adjustment applied to the collapse flow.

### Side fix — Do not rollback after assertion failure

Once flush has **atomically persisted to disk**, `_rollback_cluster_state` can only roll back the in-memory `node_clusters.json` object, not the disk. The result would be **memory vs disk inconsistency**. Therefore assertion failure only emits an ERROR log and never triggers rollback.

The 4 assertion checks:
1. `node_clusters.json expanded` boolean matches `composite.json expanded`
2. Routing key count matches (expand: input/output routing count = actual child node port count)
3. `_assert_input_mutex_consistency`: child node `config.json listen_upper_file` equals the upstream output.json recorded under composite.json
4. `_assert_output_mutex_consistency`: child node `config.json output_file` equals downstream listen reverse-lookup recorded under composite.json

## Verification points

1. After expand: `mutex_assertion=True`, no `MUTEX-VIOLATION` ERROR
2. After collapse: `mutex_assertion=True`, no `MUTEX-VIOLATION` ERROR
3. 10 consecutive expand ↔ collapse cycles: `composite.json expanded` on disk always matches in-memory value
4. Even on genuine inconsistency (user manually corrupts config): only ERROR log, no mistaken rollback

## Files Changed

| File | Changes |
|------|---------|
| `ui/core/node/composite_node.py` | In `expand_composite` / `collapse_composite`, moved `RouteCache.flush()` before `_assert_mutex_consistency`; assertion failure changed from `raise + rollback` to `ERROR log only + skip rollback (already flushed)` |
