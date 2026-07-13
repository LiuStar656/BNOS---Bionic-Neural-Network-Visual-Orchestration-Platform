# Composite Node Context Menu Optimization & Input Anchor Exclusive Detection

[Back to Overview](./README.md)

---

## Part 1: Composite Node Context Menu Optimization

### Background

The right-click menu had three issues:
1. "Start" and "Stop" were both visible simultaneously, risking misoperation
2. "Decompose" was at the top of the menu, inconsistent with operation frequency and risk level
3. Expand/Collapse and Decompose were available while the composite was running, which could cause data corruption

### Changes

#### File: `ui/canvas/mixins/canvas_menus.py`

**1. Start/Stop Mutual Exclusion**

Check `mgr.is_running(comp_id)` at menu entry point, and show only one of "Start" or "Stop":

```python
is_running = mgr.is_running(comp_id)
if is_running:
    stop_action = menu.addAction("Stop Composite Node")
else:
    start_action = menu.addAction("Start Composite Node")
```

**2. Decompose Moved to Bottom + Running State Check**

Decompose moved to the very bottom of the menu; disabled with tooltip when running:

```python
decompress_action = menu.addAction("Decompose into Independent Nodes")
if is_running:
    decompress_action.setEnabled(False)
    decompress_action.setToolTip("Composite node is running, please stop first")
```

**3. Expand/Collapse Running State Check**

Expand/Collapse is disabled with tooltip when running. A new `_on_toggle_expand` method provides an additional dialog guard (prevents bypassing via other entry points):

```python
def _on_toggle_expand(self, mgr, comp_id):
    if mgr.is_running(comp_id):
        themed_message(None, "Warning",
                       "Composite node is running, please stop before expanding/collapsing",
                       "warning")
        return
    mgr.toggle_expand(comp_id)
```

**4. Final Menu Structure**

Top to bottom:
1. Start Composite Node / Stop Composite Node (mutually exclusive)
2. --- separator ---
3. Expand / Collapse (disabled when running)
4. --- separator ---
5. Runtime Mode submenu (process / inprocess)
6. --- separator ---
7. Decompose into Independent Nodes (disabled when running)

---

## Part 2: Input Anchor Exclusive Detection

### Background

Connection rules: one output anchor → many input anchors (already implemented), but there was no restriction preventing multiple output anchors from connecting to the same input anchor. Multiple upstream nodes writing to the same input would cause data races.

### Changes

#### File: `ui/canvas/mixins/canvas_connections.py`

Two new guard sections in `create_edge`, placed after the duplicate check and before EdgeItem construction:

**1. Specific input anchor (multi-port nodes)**

Check `target_anchor.edges` to see if the anchor already has an edge:

```python
if target_anchor and hasattr(target_anchor, "port_name"):
    if target_anchor.edges:
        port_label = getattr(target_anchor, "port_label", "") or getattr(target_anchor, "port_name", "")
        themed_message(self.canvas, "Connection Rejected",
                       f"Input port '{port_label}' is already connected. "
                       "One input port can only accept one connection.",
                       "warning")
        return
```

**2. No specific anchor (default input port)**

Check `target_node.input_anchor.edges` for the default input:

```python
else:
    default_input = getattr(target_node, "input_anchor", None)
    if default_input and default_input.edges:
        themed_message(self.canvas, "Connection Rejected",
                       "This node's input is already connected. "
                       "One input port can only accept one connection.",
                       "warning")
        return
```

### Unaffected

- Output anchor → multiple input anchors: unchanged, continues to work
- Layout loading (`CanvasLayout.load_layout`): constructs EdgeItem directly, bypasses `create_edge`; saved layouts load correctly
- Existing same-source-same-target duplicate check: preserved after the exclusive detection

---

## Modified Files

| File | Change |
|------|--------|
| `ui/canvas/mixins/canvas_menus.py` | Rewrote `_show_composite_node_menu`; added `_on_toggle_expand` |
| `ui/canvas/mixins/canvas_connections.py` | Added input anchor exclusive detection in `create_edge` |

---

**Last Updated**: 2026-07-13
