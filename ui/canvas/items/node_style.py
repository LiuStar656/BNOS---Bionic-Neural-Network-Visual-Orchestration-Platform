"""
节点样式系统 — 分离视觉样式，支持方块/圆点等多套节点外观
"""
from PyQt6.QtGui import QColor


class NodeStyle:
    """节点样式基类"""

    style_name: str = "方块"

    # ===== 几何 =====
    node_width: int = 140
    node_height: int = 80
    name_y: int = 15
    lang_y: int = -18
    anchor_size: int = 16
    anchor_in_x: int = -8
    anchor_out_x: int = -8
    indicator_x: int = 8
    indicator_y: int = 8
    indicator_size: int = 10
    expand_x: int = -20
    expand_y: int = 4
    expand_w: int = 14
    expand_h: int = 14
    expand_text_x: int = -1
    expand_text_y: int = -1
    in_label_x: int = -22
    out_label_x: int = 4
    label_y: int = -5
    border_width: int = 2
    selected_border_width: int = 3

    # ===== 颜色 =====
    bg_color: str = "#2d2d30"
    border_color: str = "#454545"
    text_color: str = "#d4d4d4"
    selected_color: str = "#007acc"
    lang_color: str = "#888888"
    in_label_color: str = "#6a9955"
    out_label_color: str = "#007acc"
    status_running: str = "#FF4444"
    status_running_border: str = "#CC0000"
    status_stopped: str = "#44FF44"
    status_stopped_border: str = "#00CC00"
    expand_bg: str = "#555555"
    expand_border: str = "#444444"
    expand_text: str = "#cccccc"

    # ===== 字体 =====
    name_font_family: str = "Arial"
    name_font_size: int = 10
    name_font_bold: bool = True
    lang_font_family: str = "Arial"
    lang_font_size: int = 8
    lang_font_bold: bool = False
    anchor_font_family: str = "Arial"
    anchor_font_size: int = 7
    anchor_font_bold: bool = False
    expand_font_family: str = "Arial"
    expand_font_size: int = 7
    expand_font_bold: bool = True

    # ===== 类型标识 =====
    is_dot: bool = False   # 是否为圆点样式

    def apply(self, node_item):
        from PyQt6.QtGui import QPen, QBrush, QFont
        w, h = self.node_width, self.node_height

        # 隐藏圆点组件（方块样式默认无）
        if hasattr(node_item, '_body') and node_item._body:
            node_item._body.setVisible(False)

        node_item.setBrush(QBrush(QColor(self.bg_color)))
        node_item.setPen(QPen(QColor(self.border_color), self.border_width))
        node_item.setRect(0, 0, w, h)

        # 恢复可见性（从圆点切换回来时）
        if hasattr(node_item, '_in_label') and node_item._in_label:
            node_item._in_label.setVisible(True)
        if hasattr(node_item, '_out_label') and node_item._out_label:
            node_item._out_label.setVisible(True)
        node_item.status_indicator.setVisible(True)

        self._apply_texts(node_item, w, h)
        self._apply_anchors(node_item, w, h)
        self._apply_expand(node_item, w)
        self._apply_indicator(node_item)

    def apply_status(self, node_item, status):
        from PyQt6.QtGui import QColor, QBrush, QPen
        if self.is_dot and hasattr(node_item, '_body') and node_item._body:
            c = QColor(self.status_running if status == "running" else self.status_stopped)
            b = QColor(self.status_running_border if status == "running" else self.status_stopped_border)
            node_item._body.setBrush(QBrush(c))
            node_item._body.setPen(QPen(b, 2))
        else:
            c = QColor(self.status_running if status == "running" else self.status_stopped)
            b = QColor(self.status_running_border if status == "running" else self.status_stopped_border)
            node_item.status_indicator.setBrush(QBrush(c))
            node_item.status_indicator.setPen(QPen(b, 1.5))

    def _apply_texts(self, node_item, w, h):
        from PyQt6.QtGui import QFont
        f = QFont(self.name_font_family, self.name_font_size)
        if self.name_font_bold: f.setBold(True)
        node_item.name_text.setDefaultTextColor(QColor(self.text_color))
        node_item.name_text.setFont(f)
        nr = node_item.name_text.boundingRect()
        node_item.name_text.setPos((w - nr.width()) / 2, self.name_y)

        f2 = QFont(self.lang_font_family, self.lang_font_size)
        if self.lang_font_bold: f2.setBold(True)
        node_item.lang_text.setDefaultTextColor(QColor(self.lang_color))
        node_item.lang_text.setFont(f2)
        lr = node_item.lang_text.boundingRect()
        node_item.lang_text.setPos((w - lr.width()) / 2, h + self.lang_y)

    def _apply_anchors(self, node_item, w, h):
        from PyQt6.QtGui import QFont
        ft = QFont(self.anchor_font_family, self.anchor_font_size)
        if self.anchor_font_bold: ft.setBold(True)
        # 恢复锚点默认位置（方块样式）
        if hasattr(node_item, 'input_anchor'):
            node_item.input_anchor.setPos(self.anchor_in_x, h / 2 - 8)
        if hasattr(node_item, 'output_anchor'):
            node_item.output_anchor.setPos(w - 8, h / 2 - 8)
        if hasattr(node_item, '_in_label') and node_item._in_label:
            node_item._in_label.setDefaultTextColor(QColor(self.in_label_color))
            node_item._in_label.setFont(ft)
            node_item._in_label.setPos(self.in_label_x, h / 2 + self.label_y)
        if hasattr(node_item, '_out_label') and node_item._out_label:
            node_item._out_label.setDefaultTextColor(QColor(self.out_label_color))
            node_item._out_label.setFont(ft)
            node_item._out_label.setPos(w + self.out_label_x, h / 2 + self.label_y)

    def _apply_expand(self, node_item, w):
        from PyQt6.QtGui import QPen, QBrush, QFont
        ex, ey = w + self.expand_x, self.expand_y
        node_item._expand_btn.setRect(ex, ey, self.expand_w, self.expand_h)
        node_item._expand_btn.setBrush(QBrush(QColor(self.expand_bg)))
        node_item._expand_btn.setPen(QPen(QColor(self.expand_border), 1))
        node_item._expand_btn_rect.setRect(ex, ey, self.expand_w, self.expand_h)
        ef = QFont(self.expand_font_family, self.expand_font_size)
        if self.expand_font_bold: ef.setBold(True)
        node_item._expand_label.setDefaultTextColor(QColor(self.expand_text))
        node_item._expand_label.setFont(ef)
        node_item._expand_label.setPos(ex + self.expand_text_x, ey + self.expand_text_y)

    def _apply_indicator(self, node_item):
        node_item.status_indicator.setRect(self.indicator_x, self.indicator_y, self.indicator_size, self.indicator_size)


class DarkNodeStyle(NodeStyle):
    """VSCode 深色方块"""
    style_name: str = "深色方块"
    pass


class LightNodeStyle(NodeStyle):
    """浅色方块"""
    style_name: str = "浅色方块"
    bg_color: str = "#ffffff"
    border_color: str = "#d4d4d4"
    text_color: str = "#333333"
    lang_color: str = "#999999"
    in_label_color: str = "#388a34"
    out_label_color: str = "#007acc"
    status_running: str = "#e81123"
    status_running_border: str = "#cc0000"
    status_stopped: str = "#00cc00"
    status_stopped_border: str = "#009900"
    expand_bg: str = "#e0e0e0"
    expand_border: str = "#cccccc"
    expand_text: str = "#666666"


class DotNodeStyle(NodeStyle):
    """圆形节点 — 节点本体就是状态灯，名称/类型浮在下方"""
    style_name: str = "圆形节点"
    is_dot: bool = True

    # 圆点尺寸
    node_width: int = 60
    node_height: int = 60
    dot_radius: int = 20

    # 文字浮在下方
    name_y: int = 40
    lang_y: int = 22
    name_font_size: int = 9
    lang_font_size: int = 7

    # 隐藏状态灯（圆点本体就是）
    indicator_x: int = -100
    indicator_y: int = -100
    indicator_size: int = 1

    # 输入锚点在圆心
    anchor_in_x: int = 10
    label_y: int = 0

    # 展开按钮移到右侧
    expand_x: int = 6
    expand_y: int = -6

    def apply(self, node_item):
        from PyQt6.QtWidgets import QGraphicsEllipseItem
        from PyQt6.QtGui import QPen, QBrush
        from PyQt6.QtCore import Qt
        w, h = self.node_width, self.node_height

        # 方块透明
        node_item.setBrush(QBrush(Qt.GlobalColor.transparent))
        node_item.setPen(QPen(Qt.PenStyle.NoPen))
        node_item.setRect(0, 0, w, h)

        # 圆点本体（不拦截鼠标事件，让NodeItem处理）
        r = self.dot_radius
        cx, cy = w // 2 - r, h // 2 - r - 5
        if not hasattr(node_item, '_body') or node_item._body is None:
            node_item._body = QGraphicsEllipseItem(cx, cy, r * 2, r * 2, node_item)
            node_item._body.setZValue(5)
            node_item._body.setAcceptHoverEvents(False)
        else:
            node_item._body.setRect(cx, cy, r * 2, r * 2)
        node_item._body.setVisible(True)
        # 不拦截鼠标，事件穿透到 NodeItem
        node_item._body.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        # 状态颜色
        self.apply_status(node_item, node_item.status)

        # 输入锚点移到圆心（覆盖圆点）
        if hasattr(node_item, 'input_anchor'):
            node_item.input_anchor.setPos(cx, cy)
        # 输出锚点在右侧
        if hasattr(node_item, 'output_anchor'):
            node_item.output_anchor.setPos(w - 16, cy - 4)

        # 隐藏 IN/OUT 文字标签（圆点自明）
        if hasattr(node_item, '_in_label') and node_item._in_label:
            node_item._in_label.setVisible(False)
        if hasattr(node_item, '_out_label') and node_item._out_label:
            node_item._out_label.setVisible(False)
        # 隐藏独立状态灯（圆点就是）
        node_item.status_indicator.setVisible(False)

        self._apply_texts(node_item, w, h)
        self._apply_expand(node_item, w)

    def apply_status(self, node_item, status):
        from PyQt6.QtGui import QColor, QBrush, QPen
        if hasattr(node_item, '_body') and node_item._body:
            c = QColor(self.status_running if status == "running" else self.status_stopped)
            b = QColor(self.status_running_border if status == "running" else self.status_stopped_border)
            node_item._body.setBrush(QBrush(c))
            node_item._body.setPen(QPen(b, 2.5))


# 注册表
STYLES = {
    "dark_block": DarkNodeStyle,
    "light_block": LightNodeStyle,
    "dot": DotNodeStyle,
}
