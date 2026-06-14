"""圆角矩形图形"""
from PySide6.QtCore import QRectF
from .rect import RectGraphic


class RoundRectGraphic(RectGraphic):
    """圆角矩形"""
    def __init__(self, points=None):
        super().__init__(points)
        self.gtype = "round_rect"

    def paint(self, painter, option, widget):
        if len(self._points) < 2: return
        x1,y1 = self._points[0]; x2,y2 = self._points[1]
        rect = QRectF(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
        painter.setPen(self._stroke)
        painter.setBrush(self._fill)
        painter.drawRoundedRect(rect, 10, 10)
        if self.isSelected():
            self._draw_handles(painter)
