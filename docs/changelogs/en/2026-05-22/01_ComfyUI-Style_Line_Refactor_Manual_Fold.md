# 🔧 ComfyUI-Style Line Refactor + Manual Fold

## 🔧 ComfyUI-Style Line Refactor + Manual Fold (2026-05-22)

### Bezier → Orthogonal Lines + Manual Folding 📏

**Complete rewrite**: `ui/canvas/items/edge_item.py`

- **Straight lines**: Bezier curves replaced with straight line segments
- **Fold handles**: Each segment's midpoint shows a draggable blue handle, always visible
- **Fold waypoints**: Existing waypoints are orange dots, directly draggable to adjust
- **Relative coordinates**: Waypoints stored as `(t, off_x, off_y)` relative to endpoints, auto-follow when nodes move
- **Selected color (not thicker)**: Selected → bright blue `#2aaaff`, hovered → 140% brighter, same width
- **Delete**: Double-click waypoint to remove it

**Interaction**:
| Element | Color | Behavior |
|---------|-------|----------|
| Segment midpoint handle | Blue | Short press = select line, Long press 250ms + drag = new fold |
| Existing waypoint | Orange | Direct drag to adjust, double-click to delete |

**Serialization**: New `waypoints` field in `canvas_layout.json` edges, backward compatible.

### Temp Edge Sync ✨

`canvas_view.py` drag-to-connect now renders straight dashed temp line matching final style.

---