# 🎯 Node Style System

## 🎯 Node Style System (2026-05-21)

### Core Architecture

**New file**: `ui/canvas/items/node_style.py`

Complete node style abstraction system, cleanly separating appearance, layout, and interaction logic for rectangular and circular nodes:

| Class | Description |
|-------|-------------|
| `NodeStyle` | Abstract base class; defines `style_key`, `selected_border_width`, `selected_color` |
| `RectNodeStyle` | Rectangular node (default); full anchors, expand button, indicators, IN/OUT labels |
| `DarkRectNodeStyle` | Dark rect variant (extends `RectNodeStyle`), the current default style |
| `DotNodeStyle` | Circular node; three-layer z-architecture, hides all rect-specific components |

### Dot Node Three-Layer Z-Architecture

```
z=6  Status indicator (top layer)
z=5  Input anchor (middle layer)
z=4  Output anchor (bottom layer)
```

- Dot nodes hide: anchor labels (IN/OUT), status indicator, expand button `>>`
- Node name displayed left-aligned below the circle, touching its bottom edge
- When selected, a **floating selection ring** (`QGraphicsEllipseItem`, z=10) appears above the node

### Style Switching & Persistence

- Canvas right-click menu "Node Style" submenu with "Rect" and "Dot" options
- All menu actions use `functools.partial` to avoid lambda closure late-binding bugs
- Style switch triggers `_save_timer.start(500)` for auto-save
- `canvas_layout.json` stores a `"style"` field per node (`"rect"` or `"dot"`)
- Layout load restores styles via `STYLES.get(style_key)()`

### Bug Fixes

- Fixed lambda closure late-binding causing wrong menu actions
- Fixed anchor position stacking (constructor offset + setPos offset)
- Fixed `setRect(w, h)` param error → `setRect(0, 0, w, h)`
- Fixed `setBrush(Qt.BrushStyle.NoBrush)` type error → `setBrush(QBrush())`
- Fixed `QLabel(self.node_name)` bool type error → `QLabel(str(self.node_name))`
- Fixed dot node rect too small causing grid rendering artifacts → expanded to 80×80 with `prepareGeometryChange()`

**Affected files**: `ui/canvas/items/node_style.py`(new), `ui/canvas/items/node_item.py`(modified), `ui/canvas/canvas_menus.py`(modified), `ui/canvas/canvas_layout.py`(modified)

---