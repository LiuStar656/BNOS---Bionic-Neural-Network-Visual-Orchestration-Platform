# 【2026-06-15】V2.0.15 - Node Style Unification & Anchor Coordinate Fixes

---

## Update List

### 1. Node Style Unification & Anchor Coordinate Fixes

[View Details](./01_Node_Style_Unification_Anchor_Fixes_and_Lifecycle_Protection.md)

- **Style System Simplification**: Deleted rect.py / dot.py style files; unified entire system to panel mode (DetailedNodeStyle)
- **Anchor Position Unification**: Input/output anchor fallback positions changed to left/right edge midpoints (x=0/nw, y=h/2)
- **Coordinate System Fix**: Corrected the `setPos` double-offset bug (subtracting `size/2`) and the compensating `_find_nearest` `+half` bug, eliminating 8px visual offset
- **Inheritance Chain Fix**: DetailedNodeStyle now directly inherits NodeStyle base class, no longer depends on deleted RectNodeStyle
- **Process Lifecycle Protection**: Added RuntimeError guards for already-destroyed QProcess C++ objects during TerminalProcess destruction

---

## Key Updates

| Category | Details |
|------|----------|
| **Style System** | Deleted rect.py / dot.py; unified to DetailedNodeStyle panel mode |
| **Anchor Coordinates** | Fallback positions unified to left/right edge midpoints; setPos offset bug fixed |
| **Bug Fixes** | DetailedNodeStyle import chain breakage; 8px anchor visual offset; QProcess destruction RuntimeError |
| **Code Quality** | Removed is_dot branching in node_item.py; StyleRegistry reduced to single style |

---

## Verification Results

- ✅ 11/11 modified files compile successfully
- ✅ No `ModuleNotFoundError: No module named 'ui.canvas.items.styles.rect'`
- ✅ Zero `RectNodeStyle` / `DotNodeStyle` code references remaining
