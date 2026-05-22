"""
绘图工具基础图形类 — 矩形/圆角矩形/多边形/箭头/文本

所有图形继承 GraphicBase，统一交互接口。
"""
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem
from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QPen, QColor, QBrush, QPainter, QFont, QPainterPath, QPolygonF
from math import atan2, cos, sin, pi


# ── 全局默认样式 ──
C_STROKE   = QColor("#00AAFF")
C_FILL     = QColor(0, 0, 0, 0)
C_TEXT     = QColor("#FFFFFF")
STROKE_W   = 2.0
FONT_SIZE  = 14


class GraphicBase(QGraphicsItem):
    """图形基类 — 所有绘图工具的公共接口"""

    HANDLE_R = 5.0  # 控制点半径

    def __init__(self, gtype: str, points: list = None):
        super().__init__()
        self.gtype = gtype
        self._points = points or []       # 关键点坐标列表
        self._stroke = QPen(C_STROKE, STROKE_W)
        self._fill = QBrush(C_FILL)
        self.selected_handle = -1          # 选中的控制点索引，-1 表示无

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        return QRectF(-2000, -2000, 4000, 4000)  # 画布级，具体由于类覆盖

    def paint(self, painter, option, widget=None):
        pass

    def set_style(self, stroke_color=None, stroke_w=None, fill_color=None, font_size=None, text_color=None):
        if stroke_color is not None:
            self._stroke.setColor(QColor(stroke_color))
        if stroke_w is not None:
            self._stroke.setWidthF(stroke_w)
        if fill_color is not None:
            self._fill.setColor(QColor(fill_color))
        if self.gtype == "text" and font_size is not None:
            self._font_size = font_size
        self.update()

    def move_handle(self, idx, pos):
        """移动指定控制点"""
        if 0 <= idx < len(self._points):
            self._points[idx] = (pos.x(), pos.y())
            self.prepareGeometryChange()
            self._after_edit()

    def _after_edit(self):
        """子类覆盖：控制点移动后更新图形"""
        pass

    def _draw_handles(self, painter):
        """绘制所有控制点"""
        painter.setPen(QPen(QColor("#FFFFFF"), 1))
        painter.setBrush(QBrush(QColor("#00AAFF")))
        for i, (x, y) in enumerate(self._points):
            painter.drawEllipse(QPointF(x, y), self.HANDLE_R, self.HANDLE_R)

    def to_dict(self):
        return {
            "type": self.gtype,
            "points": self._points,
            "style": {
                "stroke": self._stroke.color().name(),
                "stroke_w": self._stroke.widthF(),
                "fill": self._fill.color().name() if self._fill.color().alpha() > 0 else None,
            }
        }

    @staticmethod
    def from_dict(d):
        gtype = d.get("type", "rect")
        pts = d.get("points", [])
        sty = d.get("style", {})
        if gtype == "rect":
            obj = RectGraphic(pts)
        elif gtype == "round_rect":
            obj = RoundRectGraphic(pts)
        elif gtype == "polygon":
            obj = PolygonGraphic(pts)
        elif gtype == "arrow":
            obj = ArrowGraphic(pts)
        elif gtype == "text":
            text = d.get("text", "")
            px = d.get("x", 0)
            py = d.get("y", 0)
            obj = TextGraphic(text, px, py)
        else:
            obj = RectGraphic(pts)
        obj.set_style(stroke_color=sty.get("stroke"), stroke_w=sty.get("stroke_w"),
                       fill_color=sty.get("fill"))
        return obj

    def hit_handle(self, pos):
        """检测是否命中控制点，返回索引或 -1"""
        for i, (x, y) in enumerate(self._points):
            dx = pos.x() - x
            dy = pos.y() - y
            if dx*dx + dy*dy <= self.HANDLE_R * self.HANDLE_R * 2:
                return i
        return -1


# ══════════════════════════════════════════
# 具体图形类
# ══════════════════════════════════════════

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


class TextGraphic(QGraphicsItem):
    """文本图形 — 包含背景矩形"""
    def __init__(self, text="Text", x=0, y=0):
        super().__init__()
        self.gtype = "text"
        self._text = text
        self._px, self._py = x, y
        self._stroke = QPen(C_STROKE, STROKE_W)
        self._fill = QBrush(QColor(40,40,40))
        self._font = QFont("Microsoft YaHei", FONT_SIZE)
        self._text_color = QColor(C_TEXT)

        self._text_item = QGraphicsTextItem(self)
        self._text_item.setDefaultTextColor(self._text_color)
        self._text_item.setFont(self._font)
        self._text_item.setPlainText(text)
        self._text_item.setPos(x, y)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setAcceptHoverEvents(True)

    def boundingRect(self):
        r = self._text_item.boundingRect()
        return QRectF(self._px-8, self._py-8, r.width()+16, r.height()+16)

    def paint(self, painter, option, widget):
        if hasattr(self, '_fill') and self._fill.color().alpha() > 0:
            r = self._text_item.boundingRect()
            painter.setPen(self._stroke)
            painter.setBrush(self._fill)
            painter.drawRoundedRect(QRectF(self._px-4, self._py-4, r.width()+8, r.height()+8), 4, 4)

    def set_style(self, stroke_color=None, stroke_w=None, fill_color=None, font_size=None, text_color=None):
        if stroke_color is not None: self._stroke.setColor(QColor(stroke_color))
        if stroke_w is not None: self._stroke.setWidthF(stroke_w)
        if fill_color is not None: self._fill.setColor(QColor(fill_color))
        if font_size is not None:
            self._font.setPointSize(font_size)
            self._text_item.setFont(self._font)
        if text_color is not None:
            self._text_color = QColor(text_color)
            self._text_item.setDefaultTextColor(self._text_color)
        self.update()

    @property
    def points(self):
        return []

    def to_dict(self):
        return {
            "type": "text",
            "text": self._text,
            "x": self._px, "y": self._py,
            "style": {
                "stroke": self._stroke.color().name(),
                "stroke_w": self._stroke.widthF(),
                "fill": self._fill.color().name(),
                "font_size": self._font.pointSize(),
                "text_color": self._text_color.name(),
            }
        }
