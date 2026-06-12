"""文本图形"""
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsTextItem
from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QPen, QColor, QBrush, QFont

from ._base import C_STROKE, C_FILL, C_TEXT, STROKE_W, FONT_SIZE


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
