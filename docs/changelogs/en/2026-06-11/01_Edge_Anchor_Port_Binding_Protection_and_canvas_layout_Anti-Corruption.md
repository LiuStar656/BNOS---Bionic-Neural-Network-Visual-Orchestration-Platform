# Edge Anchor Port Binding Protection & canvas_layout Anti-Corruption

## 📋 Update Overview

This update fixes the core issue where **`canvas_layout.json` gets silently rewritten** when reopening a project's canvas dock. When edges were bound to specific port anchors (e.g., `prompt`, `context`), anchor reconstruction during reload caused edges to silently fall back to the default anchor, causing `target_port` to change from `"prompt"` to `"default"` and potentially creating duplicate edge entries. This fix introduces a "Desired Port Name Memory" mechanism and "Anchor-Missing No-Degradation" protection to ensure edges always bind to the correct anchors.

---

## 🎯 Root Cause Analysis

### Problem Symptoms

1. User creates a project, connects an edge to a `prompt` port anchor
2. `canvas_layout.json` correctly saves `"target_port": "prompt"`
3. After app restart, opening the project → `canvas_layout.json` is rewritten:
   - `"target_port": "prompt"` → `"target_port": "default"`
   - Duplicate edge entries appear

### Triple Root Causes

| # | Issue | Impact |
|---|-------|--------|
| 1 | `load_layout` called twice | Second call finds anchors already reconstructed, causing duplicate edges |
| 2 | `EdgeItem` doesn't remember desired port name | After anchor rebuild, `_validate_edge_anchor_binding` uses `end_anchor.port_name` for lookup—but it's already `"default"` |
| 3 | Silent fallback to default anchor when port anchor missing | When `get_input("prompt")` returns `None`, `EdgeItem` binds to `input_anchor` (default), port info lost on save |

---

## 🔧 Core Changes

### 1. EdgeItem: Desired Port Name Memory Fields

**New Fields** (2):
- `_desired_target_port_name`: Target port name ("prompt" / "context" / None)
- `_desired_source_port_name`: Source port name

**Constructor signature**:
```python
def __init__(self, start_node, end_node, canvas=None,
             target_anchor=None, source_anchor=None,
             target_port_name=None, source_port_name=None):
```

**_setup_anchor_binding enhanced logic**:
- When `_desired_target_port_name` is set, prefer `anchor_manager.get_input(port_name)` lookup
- Only allow fallback to default anchor when **no specific port name is specified**
- If a port name is specified but the anchor doesn't exist, keep `end_anchor = None`, no silent degradation

**Modified file**: `ui/canvas/items/edge_item.py`

### 2. load_layout: Skip Edge When Port Anchor Missing (No Degradation)

**New protection logic**: Verify anchor existence before creating edge

```python
src_port = ed.get("source_port")
tgt_port = ed.get("target_port")

# Critical protection: Non-default port specified but anchor not found → skip + warn
if tgt_port and tgt_port != "default" and tgt_anchor is None:
    logger.warning("[load_layout] Skipping edge: port '%s' anchor not found on target '%s'",
                   tgt_port, node_name)
    continue
```

**Modified file**: `ui/canvas/canvas_layout.py`

### 3. _validate_edge_anchor_binding: Desired Port Name Priority

**Lookup order changed**:

```
Anchor lookup order (after fix):
  1. edge._desired_target_port_name  → original target_port from JSON
  2. edge.end_anchor.port_name       → current anchor name (may be wrong)
  3. No specific port → use default anchor
```

**No-degradation rule**: If desired port name is specific (non-default/None), keep `end_anchor = None` on miss, no fallback.

**Modified file**: `ui/canvas/canvas_layout.py`

### 4. canvas_connections: Pass Port Names on Manual Edge Creation

`create_edge()` also passes port name arguments to `EdgeItem`, ensuring manually-drawn edges also have re-binding capability after anchor reconstruction.

```python
tgt_port_name = target_anchor.port_name if target_anchor else None
src_port_name = source_anchor.port_name if source_anchor else None
edge = EdgeItem(source_node, target_node, canvas,
                target_anchor, source_anchor,
                target_port_name=tgt_port_name,
                source_port_name=src_port_name)
```

**Modified file**: `ui/canvas/canvas_connections.py`

---

## 📝 Modified Files Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `ui/canvas/items/edge_item.py` | Modify | New desired port name fields, enhanced setup binding |
| `ui/canvas/canvas_layout.py` | Modify | load_layout skips missing-port edges, _validate uses desired port priority |
| `ui/canvas/canvas_connections.py` | Modify | create_edge passes port name args to EdgeItem |

---

## 🧪 Verification Scenarios

| Scenario | Before Fix | After Fix |
|----------|-----------|-----------|
| Specified port `prompt` exists | ✅ Normal binding | ✅ Normal binding |
| Specified port `prompt` missing (config lacks `source: "node"`) | ❌ Falls back to default, port lost on save | ✅ Skipped + warned, file unchanged |
| Anchor reconstruction after style switch | ❌ May rebind to default | ✅ Uses desired port name for correct lookup |
| Multi-port edges on same node pair (prompt + default) | ❌ May collapse to default | ✅ Each edge keeps its port binding |

---

## 🔒 Design Principles

1. **No Silent Fallback**: If a specific port is specified, the edge must bind to that anchor; if not found, skip it
2. **Desired > Current**: After anchor reconstruction, use "desired port name" as lookup key, not "current anchor's port name"
3. **Verbose Warning**: All binding anomalies are output via `logger.warning` for easy debugging
