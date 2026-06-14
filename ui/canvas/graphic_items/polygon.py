"""折线多边形图形 — 单击加点，双击闭合"""
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPainterPath, QPolygonF
from ._base import GraphicBase


class PolygonGraphic(GraphicBase):
    """折线多边形 — 单击加点，双击闭合"""
    def __init__(self, points=None):
        super().__init__("polygon", points or [])

    def boundingRect(self):
        if not self._points: return QRectF(0,0,1,1)
        xs = [p[0] for p in self._points]; ys = [p[1] for p in self._points]
        return QRectF(min(xs)-10, min(ys)-10, max(xs)-min(xs)+20, max(ys)-min(ys)+20)

    def shape(self):
        p = QPainterPath()
        if len(self._points) >= 2:
            p.moveTo(*self._points[0])
            for pt in self._points[1:]: p.lineTo(*pt)
            p.closeSubpath()
        return p

    def add_point(self, x, y):
        self._points.append((x, y))
        self.prepareGeometryChange()

    def paint(self, painter, option, widget):
        if not self._points: return
        pts = [QPointF(x,y) for x,y in self._points]
        painter.setPen(self._stroke)
        if len(pts) >= 2 and self.isFinished():
            painter.setBrush(self._fill)
            painter.drawPolygon(QPolygonF(pts))
        else:
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolyline(QPolygonF(pts))
        if self.isSelected():
            self._draw_handles(painter)

    def isFinished(self):
        """至少 3 个点才算闭合多边形"""
        return len(self._points) >= 3
