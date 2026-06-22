# 02_高 DPI 屏幕适配

**日期**: 2026-06-22

## 背景

4K / Retina 屏幕下 `devicePixelRatio != 1` 时，Qt 未启用高 DPI 缩放导致线条、字体、节点图标过小或模糊；子进程画布同样需要高 DPI 支持。

## 变更内容

### bnos_console.py：主进程高 DPI

在 `QApplication` **创建之前**调用 `setAttribute`，确保 Qt 初始化时即启用高 DPI。

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
app = QApplication(sys.argv)
```

### ui/canvas/canvas_process.py：子进程高 DPI

画布子进程独立运行，同样需要设置相同属性。

```python
QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
app = QApplication(sys.argv)
```

### painter 渲染提示

在 `EdgeItem` / `TempEdgeItem` / `EdgeArrowItem` 的 `paint()` 中同时启用 `SmoothPixmapTransform`，使 pixmap 在缩放变换时采用平滑采样。

```python
painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
```

### 属性说明

| 属性 | 作用 |
|------|------|
| `AA_EnableHighDpiScaling` | Qt 根据显示器 DPI 自动缩放逻辑像素到物理像素，保证线条、字体、图标在高 DPI 屏上显示比例合理 |
| `AA_UseHighDpiPixmaps` | `QPixmap` 图标资源使用高 DPI 版本渲染，避免图标模糊或边缘锯齿 |

## 在不同屏幕上的效果对比

| 屏幕 | 修复前 | 修复后 |
|------|--------|--------|
| **1080p (DPR ≈ 1.0)** | 正常显示 | 正常显示（无变化） |
| **4K (DPR ≈ 2.0)** | 线条/字体偏小，图标模糊 | 线条/字体比例合理，图标清晰 |
| **Retina (DPR ≈ 2.0)** | 线条边缘模糊 | 边缘锐利平滑 |

## 影响范围

- **修改文件**: `bnos_console.py`、`ui/canvas/canvas_process.py`、`ui/canvas/items/edge_item.py`
- **核心改动**: 两处 `QApplication.setAttribute` 调用（主进程 + 子进程）
- **渲染提示**: `EdgeItem` / `TempEdgeItem` / `EdgeArrowItem` 的 `paint()` 中新增 `SmoothPixmapTransform`