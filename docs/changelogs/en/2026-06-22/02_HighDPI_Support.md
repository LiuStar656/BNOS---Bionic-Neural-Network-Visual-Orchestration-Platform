# 02_High DPI Screen Adaptation

**Date**: 2026-06-22

## Background

On 4K, Retina and other high-DPI displays where `devicePixelRatio != 1`, Qt defaults did not automatically scale the UI. This produced:

1. **Lines too thin / too small**: QPen widths measured in logical pixels, so on a 2x device the line appeared half its intended physical size.
2. **Blurry fonts and icons**: Pixmap assets rendered at 1x and then scaled up by the OS, producing visible blurriness.
3. **Subprocess canvas mismatch**: BNOS spawns a separate canvas process (`ui/canvas/canvas_process.py`) to render node graphs in a dedicated QApplication. That subprocess lacked high-DPI attributes, so the canvas window remained in low-DPI mode even when the main window was scaled.

## Changes

### bnos_console.py - Main Process

Both attributes are set **before** `QApplication` is created, which is required by Qt (attributes set after construction are ignored).

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

app = QApplication(sys.argv)
```

### ui/canvas/canvas_process.py - Subprocess Canvas

Identical two attribute settings, ensuring the subprocess window uses the same high-DPI scaling path as the main window.

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

app = QApplication(sys.argv)
```

### Painter Render Hints - SmoothPixmapTransform

In `EdgeItem.paint()`, `TempEdgeItem.paint()`, and `EdgeArrowItem.paint()`:

```python
painter.setRenderHint(QPainter.Antialiasing, True)
painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
```

`SmoothPixmapTransform` provides bilinear interpolation when pixmaps or bitmap-backed items are drawn at non-integer scales - which happens constantly on a high-DPI device where `devicePixelRatio` is a fractional value. Combined with `Antialiasing` it delivers a clean, consistently sharp look across 1080p, 1440p, 4K, and Retina.

### Attribute Description

| Attribute | Effect |
|-----------|--------|
| `AA_EnableHighDpiScaling` | Enables Qt's automatic logical-pixel to physical-pixel scaling. Widgets, fonts, and QPainter coordinates are expressed in logical pixels; Qt multiplies by `devicePixelRatio` at rasterization. |
| `AA_UseHighDpiPixmaps` | Icon resource loading picks `@2x` / `@3x` variants when available; otherwise upscales with high-quality filtering. Icons look crisp on Retina/4K instead of being pixel-doubled. |

### Effect Comparison

| Display | devicePixelRatio | Before | After |
|---------|------------------|--------|-------|
| 1080p desktop | ~1.0 | Looks fine | Looks identical (no change) |
| 1440p laptop | ~1.25-1.5 | Slightly blurry icons | Crisp icons; lines match design width |
| 4K desktop | ~1.75-2.0 | Lines too thin, text fuzzy | Sharp text; properly scaled lines |
| Retina (macOS) | ~2.0 | Icon blurriness + thin lines | Normal icon size; smooth outline fill |

### Impact

- **Modified**: `bnos_console.py` - attribute initialization block at top of main
- **Modified**: `ui/canvas/canvas_process.py` - same attribute initialization block
- **Modified**: `ui/canvas/items/edge_item.py` - `SmoothPixmapTransform` render hint enabled in paint methods
- **Order matters**: Both attributes must be set **before** `QApplication(sys.argv)` - moving them after construction causes a no-op in PySide6