"""直线/箭头图形"""
from PyQt6.QtCore import QRectF, QPointF
from PyQt6.QtGui import QPolygonF
from math import atan2, cos, sin, pi
from ._base import GraphicBase


class ArrowGraphic(GraphicBase):
    """直线/箭头"""
    ARROW_LEN = 14; ARROW_ANGLE = pi/7

    def __init__(self, points=None):
        super().__init__("arrow", points or [(0,0),(100,0)])

    def boundingRect(self):
        if len(self._points) < 2: return QRectF(0,0,1,1)
        x1,y1 = self._points[0]; x2,y2 = self._points[1]
        return QRectF(min(x1,x2)-20, min(y1,y2)-20, abs(x2-x1)+40, abs(y2-y1)+40)

    def paint(self, painter, option, widget):
        if len(self._points) < 2: return
        x1,y1 = self._points[0]; x2,y2 = self._points[1]
        painter.setPen(self._stroke)
        painter.drawLine(QPointF(x1,y1), QPointF(x2,y2))

        # 箭头头部
        angle = atan2(y2-y1, x2-x1)
        p1 = QPointF(x2 - self.ARROW_LEN*cos(angle-self.ARROW_ANGLE),
                      y2 - self.ARROW_LEN*sin(angle-self.ARROW_ANGLE))
        p2 = QPointF(x2 - self.ARROW_LEN*cos(angle+self.ARROW_ANGLE),
                      y2 - self.ARROW_LEN*sin(angle+self.ARROW_ANGLE))
        painter.setBrush(self._stroke.color())
        painter.drawPolygon(QPolygonF([QPointF(x2,y2), p1, p2]))

        if self.isSelected():
            self._draw_handles(painter)
