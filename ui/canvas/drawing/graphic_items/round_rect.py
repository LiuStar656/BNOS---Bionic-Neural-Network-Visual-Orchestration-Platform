"""圆角矩形图形"""
from PySide6.QtCore import QRectF
from .rect import RectGraphic


class RoundRectGraphic(RectGraphic):
    """圆角矩形"""
    def __init__(self, points=None):
        super().__init__(points)
        self.gtype = "round_rect"
        self._rx = 10.0
        self._ry = 10.0

    def paint(self, painter, option, widget):
        if len(self._points) < 2: return
        x1,y1 = self._points[0]; x2,y2 = self._points[1]
        rect = QRectF(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
        painter.setPen(self._stroke)
        painter.setBrush(self._fill)
        painter.drawRoundedRect(rect, self._rx, self._ry)
        if self.isSelected():
            self._draw_handles(painter)

    def set_radius(self, rx: float, ry: float = None):
        """设置圆角半径"""
        self._rx = rx
        self._ry = ry if ry is not None else rx
        self.update()
