# Single-Entry DAG Validation

[Back to Update Overview](./README.md)

---

## Core Constraint

Composite nodes must be single-entry DAGs. Supported topologies: `A→B→C` or `A→B` concurrently `A→C`. Disallowed: `A→C` and `B→C` (dual entry).

## New Method

`_validate_dag_single_entry` — counts candidate entry nodes with `in_degree==0` and empty `listen_upper_file`:

| Candidates | Behavior |
|-----------|----------|
| 0 | Reject — "No entry node detected" |
| 1 | Pass |
| 2+ | Reject — "Must have exactly one entry" |

## Trigger Points

| Operation | Timing | Rejection Behavior |
|-----------|--------|-------------------|
| Compress | After port identification in `compress()` | `return False, err_msg, None` |
| Collapse | Before any state change in `_collapse_composite()` | `QMessageBox.warning` + `return`, expanded state preserved |
