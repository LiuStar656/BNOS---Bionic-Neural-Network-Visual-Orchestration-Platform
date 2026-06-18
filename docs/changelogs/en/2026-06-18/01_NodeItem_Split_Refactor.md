# 01 NodeItem Split Refactoring

**Date**: 2026-06-18

---

## Background

`node_item.py` was a monolithic class of 846 lines, handling 18 responsibilities across 6 categories (rendering, interaction, config I/O, status management, style management, etc.). It was the largest and most tightly-coupled file in the `ui/canvas/` module.

## Changes

### New Directory Structure

```
ui/canvas/items/
    node_item.py                    (Main class: 227 lines, lifecycle + delegation)
    node_components/                (New folder, 9 sub-components)
        __init__.py                (Package exports)
        rendering.py               (paint, custom colors)
        subcomponents.py            (Text labels / status lights / expand button construction)
        status_manager.py          (Resource monitoring signals, status updates, runtime)
        config_manager.py          (config.json read/write, polling subscription)
        geometry_handler.py        (itemChange, overlap avoidance, edge refresh)
        interaction_handler.py     (Mouse events, anchor connection interaction)
        style_manager.py           (Style settings, dimensions, display updates)
        param_panel.py           (Parameter panel construction and destruction)
```

### Architecture Design Principles

- **Composition Pattern**: The main class `NodeItem` instantiates sub-components in `__init__` and delegates via `self._rendering.paint()` etc.
- **External API Fully Compatible**: All public properties/methods signatures remain unchanged. External code requires no modification.
- **Qt MRO Safety**: Avoids Qt method dispatch problems caused by multiple inheritance, replaced by explicit delegation.
- **Refactoring Reference**: [node_item_refactoring_analysis.md](../../node_item_refactoring_analysis.md)

### Additional Fixes

- **config_manager.py**: Fixed `_on_external_config_change` where `widget.set_value` was not being called (missing parentheses and parameters)

## Scope

- Modified files: 1 file (`node_item.py` reduced from 846 lines to 227 lines)
- New files: 9 files in `node_components/`
- Deleted files: 0
- Zero changes to any files referencing `NodeItem`

---

## Code Reference

For the detailed Chinese version, see [中文版本](../cn/2026-06-18/01_NodeItem_拆分重构.md).
