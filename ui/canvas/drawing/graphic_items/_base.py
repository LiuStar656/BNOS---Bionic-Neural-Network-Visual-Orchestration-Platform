"""
绘图工具基类 — 所有图形的公共接口 + 全局默认样式
"""
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPen, QColor, QBrush


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
        return QRectF(-2000, -2000, 4000, 4000)

    def paint(self, painter, option, widget=None):
        pass

    def set_style(self, stroke_color=None, stroke_w=None, fill_color=None, font_size=None, text_color=None):
        if stroke_color is not None:
            self._stroke.setColor(QColor(stroke_color))
        if stroke_w is not None:
            self._stroke.setWidthF(stroke_w)
        if fill_color is not None:
            self._fill.setColor(QColor(fill_color))
        self.update()

    def set_text_color(self, color: str):
        """设置文字颜色（子类可覆盖）"""
        pass

    def move_handle(self, idx, pos):
        """移动指定控制点"""
        if 0 <= idx < len(self._points):
            self._points[idx] = (pos.x(), pos.y())
            self.prepareGeometryChange()
            self._after_edit()

    def _after_edit(self):
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
        """从 dict 重建图形（委托给 GraphicRegistry）"""
        from .__init__ import GraphicRegistry
        return GraphicRegistry.from_dict(d)

    def hit_handle(self, pos):
        """检测是否命中控制点，返回索引或 -1"""
        for i, (x, y) in enumerate(self._points):
            dx = pos.x() - x
            dy = pos.y() - y
            if dx*dx + dy*dy <= self.HANDLE_R * self.HANDLE_R * 2:
                return i
        return -1
