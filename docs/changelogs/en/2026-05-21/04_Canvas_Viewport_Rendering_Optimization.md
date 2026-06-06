# ⚡ Canvas Viewport Rendering Optimization

## ⚡ Canvas Viewport Rendering Optimization (2026-05-21)

**Modified file**: `ui/canvas/canvas_view.py`

- Viewport update mode changed from `FullViewportUpdate` to `SmartViewportUpdate`: only repaints changed areas
- Added `CacheBackground`: grid background cached, no redraw during drag/zoom
- Added `DontSavePainterState` / `DontClipPainter` optimization flags to reduce Qt paint pipeline overhead
- Significant FPS and responsiveness improvement during pan, zoom, and node movement

---