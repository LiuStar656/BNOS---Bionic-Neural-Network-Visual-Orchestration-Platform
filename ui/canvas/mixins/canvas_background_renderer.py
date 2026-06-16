"""画布背景与网格渲染器（组合模式，从 NodeCanvas 拆分）

职责：
- 背景颜色填充（绕开 stylesheet 可能覆盖的默认行为）
- 网格创建与绘制（DPR 感知线宽，锐利网格线）
- 网格可见性控制（缩放过小时隐藏）

使用方式（由 NodeCanvas __init__ 初始化）：

    self.background = BackgroundRenderer(self)
    # 在 NodeCanvas.drawBackground 中转发：
    self.background.drawBackground(painter, rect)
    # 在 NodeCanvas.__init__ 中调用：
    self.background._ensure_grid_item()

状态（由 BackgroundRenderer 持有）：
- _grid_item: QGraphicsPathItem 网格项
- draw_grid: 是否绘制网格（由 __init__ 设置 True）
"""
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath
from PySide6.QtCore import Qt


class BackgroundRenderer:
    """画布背景与网格渲染器

    组合模式：持有对 canvas 的引用，通过 self.canvas 访问画布状态
    """

    def __init__(self, canvas):
        self.canvas = canvas
        # 网格项（延迟创建，在首次 drawBackground 或 _ensure_grid_item 中生成）
        self._grid_item = None
        # 是否绘制网格（默认开启，可由外部修改）
        self.draw_grid = True

    def drawBackground(self, painter, rect):
        """背景：直接用 canvas_bg_color 填充

        对应原 NodeCanvas.drawBackground
        """
        painter.fillRect(rect, QColor(self.canvas.canvas_bg_color))
        self._ensure_grid_item()

    def _ensure_grid_item(self):
        """确保网格作为独立 QGraphicsPathItem 存在（z=-10，最底层）

        对应原 NodeCanvas._ensure_grid_item
        """
        if not self.draw_grid:
            if self._grid_item:
                self.canvas.scene.removeItem(self._grid_item)
                self._grid_item = None
            return

        # 缩放过小时隐藏网格
        from PySide6.QtWidgets import QGraphicsPathItem

        scale = self.canvas.transform().m11()
        if scale <= 0.5:
            if self._grid_item:
                self._grid_item.setVisible(False)
            return

        need_create = self._grid_item is None
        if need_create:
            self._grid_item = QGraphicsPathItem()
            self._grid_item.setZValue(-10)
            self._grid_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.canvas.scene.addItem(self._grid_item)
        else:
            self._grid_item.setVisible(True)

        # 仅样式变化时重建路径
        cache_key = (
            self.canvas.grid_color,
            self.canvas.grid_opacity,
            self.canvas.canvas_width,
            self.canvas.canvas_height,
        )
        if not need_create and getattr(self._grid_item, '_cache_key', None) == cache_key:
            return

        cw, ch = self.canvas.canvas_width, self.canvas.canvas_height
        half_w, half_h = cw // 2, ch // 2
        grid = 20

        # DPR 感知线宽：高 DPR 下保证物理像素 1px 锐利网格线
        dpr = (
            self.canvas.devicePixelRatioF()
            if hasattr(self.canvas, 'devicePixelRatioF')
            else 1.0
        )
        line_width = 1.0 / dpr

        # 像素对齐的网格路径
        path = QPainterPath()
        x = -half_w
        while x <= half_w:
            path.moveTo(x, -half_h)
            path.lineTo(x, half_h)
            x += grid
        y = -half_h
        while y <= half_h:
            path.moveTo(-half_w, y)
            path.lineTo(half_w, y)
            y += grid

        gc = QColor(self.canvas.grid_color)
        gc.setAlphaF(self.canvas.grid_opacity)
        pen = QPen(gc, line_width)
        pen.setCosmetic(True)

        self._grid_item.setPath(path)
        self._grid_item.setPen(pen)
        self._grid_item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        # 网格线关闭抗锯齿，保证线条锐利（无模糊/断裂）
        self._grid_item.setCacheMode(QGraphicsPathItem.CacheMode.NoCache)
        self._grid_item._cache_key = cache_key
