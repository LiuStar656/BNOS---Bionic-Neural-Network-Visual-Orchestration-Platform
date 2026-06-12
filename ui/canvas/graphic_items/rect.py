"""矩形图形"""
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPainterPath
from ._base import GraphicBase


class RectGraphic(GraphicBase):
    """矩形图形"""
    def __init__(self, points=None):
        super().__init__("rect", points or [(0,0),(100,80)])

    def boundingRect(self):
        if len(self._points) < 2: return QRectF(0,0,1,1)
        x1,y1 = self._points[0]; x2,y2 = self._points[1]
        return QRectF(min(x1,x2)-8, min(y1,y2)-8, abs(x2-x1)+16, abs(y2-y1)+16)

    def shape(self):
        p = QPainterPath()
        if len(self._points) >= 2:
            x1,y1 = self._points[0]; x2,y2 = self._points[1]
            p.addRect(QRectF(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1)))
        return p

    def paint(self, painter, option, widget):
        if len(self._points) < 2: return
        x1,y1 = self._points[0]; x2,y2 = self._points[1]
        rect = QRectF(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
        painter.setPen(self._stroke)
        painter.setBrush(self._fill)
        painter.drawRect(rect)
        if self.isSelected():
            self._draw_handles(painter)
