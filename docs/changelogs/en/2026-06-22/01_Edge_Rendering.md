# 01_Edge Rendering Vector Outline Fill

**Date**: 2026-06-22

## Background

After zooming in on the canvas, edges showed several quality issues that degraded visual clarity:

1. **Jagged stair-step edges**: Bezier curves and straight line segments drawn with `QPen` stroke produced visible stair-step aliasing at high zoom levels.
2. **Narrow transition area**: `QPen` stroke width had an insufficient transition band, so the color blended poorly into the background when the painter device scaled up.
3. **Cached bitmap pixel blocks**: `ItemCoordinateCache` cached items into a low-resolution bitmap; scaling it up enlarged individual pixels and caused visible pixel blocks.
4. **Inconsistent antialiasing between line stroke and arrow polygon fill**: arrows were already filled polygons (smooth), but the line segment was a stroke (jagged), creating a visual mismatch where edges and arrows met.

## Changes

### Core Approach: Expand Line Path - Closed Outline - Brush Fill

The core idea is identical to how arrow polygons are rendered: convert a line path into a **closed outline path** using `QPainterPathStroker`, then fill the resulting shape with `QBrush`. Because this produces a **filled shape** (not a stroke), it is device-independent, smooth at any zoom level, and benefits from Qt's full antialiasing pipeline.

```python
# Before
painter.setRenderHint(QPainter.Antialiasing, True)
painter.setPen(QPen(color, line_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
painter.drawPath(edge_path)

# After
painter.setRenderHint(QPainter.Antialiasing, True)
painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

stroker = QPainterPathStroker()
stroker.setWidth(line_width)
stroker.setCapStyle(Qt.RoundCap)
stroker.setJoinStyle(Qt.RoundJoin)
filled_path = stroker.createStroke(edge_path)

painter.setPen(Qt.NoPen)
painter.setBrush(QBrush(color))
painter.drawPath(filled_path)
```

### EdgeItem.paint() Refactor

**File**: `ui/canvas/items/edge_item.py`, `paint()` method

Changes:
1. Render hints: `Antialiasing` **and** `SmoothPixmapTransform` both enabled.
2. `QPainterPathStroker` builds a closed `filled_path` from the underlying line `QPainterPath` (Bezier or polyline).
3. `setPen(Qt.NoPen)` + `setBrush(QBrush(color))` + `drawPath(filled_path)`.
4. `setCacheMode(NoCache)` - bitmap cache incompatible with fill-based device-independent rendering.

Line width is `3.0px` base, dynamically adjusted by `devicePixelRatio` so physical pixels remain consistent across DPI.

### TempEdgeItem (Drag Dashed Preview)

Same `QPainterPathStroker` + fill pipeline. Uses `NoCache` so the dashed preview updates cleanly during drag.

### EdgeArrowItem

Keeps the existing polygon fill, but additionally applies `NoCache` and `NoPen` to guarantee the same antialiasing consistency as the line outline.

### Cache Mode - All Switched to NoCache

| Item | Before | After |
|------|--------|-------|
| `EdgeItem` | `ItemCoordinateCache` | `NoCache` |
| `TempEdgeItem` | `DeviceCoordinateCache` | `NoCache` |
| `EdgeArrowItem` | (no cache) | `NoCache` |

Rationale: the outline-fill path is a pure vector shape. Re-rasterizing it each paint call with antialiasing is cheap and produces crisp, zoom-stable output - whereas any cached bitmap would become blocky as soon as the user zooms.

### Waypoints / Handles

Waypoint dots and handles use `drawEllipse` + `QBrush` fill. This already produces smooth circles and requires no change.

### Design Highlights

| Feature | Implementation |
|---------|---------------|
| **Antialiasing** | `painter.setRenderHint(QPainter.Antialiasing, True)` on every edge paint |
| **Vector fill** | `QPainterPathStroker.createStroke(line_path)` - closed outline - `painter.drawPath(filled_path)` |
| **Round caps / joins** | `stroker.setCapStyle(Qt.RoundCap)`, `stroker.setJoinStyle(Qt.RoundJoin)` |
| **No bitmap cache** | `setCacheMode(QGraphicsItem.NoCache)` on EdgeItem / TempEdgeItem / EdgeArrowItem |
| **DPI-aware width** | Base `3.0px` x `devicePixelRatio`, guarantees consistent physical pixel width |
| **Smooth pixmap transform** | `SmoothPixmapTransform` hint enabled for any residual pixmap items |

### Before / After

| Dimension | Before | After |
|-----------|--------|-------|
| Line rendering | `QPen` stroke, jagged at high zoom | `QPainterPathStroker` closed outline + `QBrush` fill, smooth at any zoom |
| Arrow-to-line join | Polygon fill vs. pen stroke - visual seam | Both use `QBrush` fill, seamless join |
| Bezier zoom quality | Clear stair-step aliasing | Smooth curve at any scale |
| Cache artifact | Pixel blocks when ItemCoordinateCache scaled | NoCache - re-rendered each time |
| Antialiasing hint | `Antialiasing` only | `Antialiasing` + `SmoothPixmapTransform` |
| Line width scaling | Fixed px, too thin on 4K | `devicePixelRatio` multiplier, consistent physical width |

### Impact

- **Modified**: `ui/canvas/items/edge_item.py`
- **Modified**: `ui/canvas/mixins/canvas_connections.py` (TempEdgeItem render aligned with EdgeItem)
- **Key methods affected**: `EdgeItem.paint()`, `TempEdgeItem.paint()`, `EdgeArrowItem.paint()`
- **Cache mode changes**: 3 items switched to `NoCache`