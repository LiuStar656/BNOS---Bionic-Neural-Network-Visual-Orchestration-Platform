# 2026-06-11 Changelog

## 📋 Update Overview

This update fixes the core issue where **`canvas_layout.json` gets silently rewritten** when reopening a project. When edges were bound to specific port anchors (`prompt`, `context`, etc.), project restart and canvas dock re-opening caused edges to silently fall back to the default anchor, causing `target_port` to change from `"prompt"` to `"default"` and potentially creating duplicate edges. This fix introduces a **"Desired Port Name Memory" mechanism** and **"Anchor-Missing No-Degradation" protection** to ensure edges remain bound to the correct anchors and config files are no longer silently corrupted.

---

## ✨ Update Contents

### 1. 🔌 Edge Anchor Port Binding Protection

**Core Fixes**:
- `EdgeItem` adds `_desired_target_port_name` / `_desired_source_port_name` fields to remember which port the edge should bind to
- In `_setup_anchor_binding`: When a specific port is specified but the anchor doesn't exist, **no fallback to default**—`end_anchor` stays `None`
- In `_validate_edge_anchor_binding`: Lookup anchors by "desired port name" first, not "current anchor's port_name" (which may already be wrong)
- In `load_layout`: When JSON specifies a non-default port but the matching anchor is not found, **skip this edge and log a warning**—don't silently degrade

**Key Protection Mechanisms**:
- **No Silent Fallback**: If a specific port is specified, the edge must bind to that anchor; if not found, skip it
- **Desired > Current**: After anchor reconstruction, use "desired port name" as the lookup key, not the "current anchor's port name"
- **Verbose Warning**: All binding anomalies are logged via `logger.warning` for easy debugging

**Modified Files** (3 files):
- `ui/canvas/items/edge_item.py` (constructor new args, `_setup_anchor_binding` enhanced)
- `ui/canvas/canvas_layout.py` (`load_layout` skips missing-port edges, `_validate_edge_anchor_binding` uses desired port priority)
- `ui/canvas/canvas_connections.py` (`create_edge` passes port name args)

**Detailed Document**: [Edge Anchor Port Binding Protection & canvas_layout Anti-Corruption](./01_Edge_Anchor_Port_Binding_Protection_and_canvas_layout_Anti-Corruption.md)

---

## 🎯 Root Cause Summary

| # | Issue | Impact |
|---|-------|--------|
| 1 | `load_layout` called twice | Second call finds anchors already reconstructed, causing duplicate edges |
| 2 | `EdgeItem` doesn't remember desired port name | After anchor rebuild, validation uses `end_anchor.port_name`—already `"default"` |
| 3 | Silent fallback to default anchor when port anchor missing | `get_input("prompt")` returns `None`, `EdgeItem` binds to default, port lost on save |

---

## 🧪 Verification Scenarios

| Scenario | Before Fix | After Fix |
|----------|-----------|-----------|
| Specified port `prompt` exists | ✅ Normal binding | ✅ Normal binding |
| Specified port `prompt` missing (config lacks `source: "node"`) | ❌ Falls back to default, port lost on save | ✅ Skipped + warned, file unchanged |
| Anchor reconstruction after style switch | ❌ May rebind to default | ✅ Uses desired port name for correct lookup |
| Multi-port edges on same node pair (prompt + default) | ❌ May collapse to default | ✅ Each edge keeps its port binding |

---

## 📋 Overview

| Feature | Status |
|---------|--------|
| EdgeItem desired port name memory fields | ✅ Done |
| Skip edges when specified port anchor missing (no degradation) | ✅ Done |
| _validate_edge_anchor_binding desired port priority lookup | ✅ Done |
| Pass port name args on manual edge creation | ✅ Done |
| canvas_layout.json no longer silently rewritten | ✅ Done |
| Duplicate edge creation prevention | ✅ Done |

---

**Update Date**: 2026-06-11
