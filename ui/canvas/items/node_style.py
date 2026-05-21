"""
节点样式系统 — 方框/圆点等多种节点外观独立封装
"""
from PyQt6.QtGui import QColor


class NodeStyle:
    """节点样式抽象基类 — 只定义属性，不实现渲染"""

    style_name: str = "抽象"
    is_dot: bool = False

    # ===== 几何 =====
    node_width: int = 140
    node_height: int = 80

    # ===== 颜色 =====
    bg_color: str = "#2d2d30"
    border_color: str = "#454545"
    text_color: str = "#d4d4d4"
    selected_color: str = "#007acc"
    selected_border_width: int = 3
    lang_color: str = "#888888"

    status_running: str = "#FF4444"
    status_running_border: str = "#CC0000"
    status_stopped: str = "#44FF44"
    status_stopped_border: str = "#00CC00"

    # ===== 字体 =====
    name_font_family: str = "Arial"
    name_font_size: int = 10
    name_font_bold: bool = True
    lang_font_family: str = "Arial"
    lang_font_size: int = 8
    lang_font_bold: bool = False

    def apply(self, node_item):
        """子类必须实现"""
        raise NotImplementedError

    def apply_status(self, node_item, status):
        """子类必须实现"""
        raise NotImplementedError


# ============================================================
#  方框节点样式
# ============================================================

class RectNodeStyle(NodeStyle):
    """方框节点样式基类"""
    style_name: str = "深色方块"
    is_dot: bool = False

    # 几何
    name_y: int = 15
    lang_y: int = -18
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

    # 颜色
    in_label_color: str = "#6a9955"
    out_label_color: str = "#007acc"
    expand_bg: str = "#555555"
    expand_border: str = "#444444"
    expand_text: str = "#cccccc"

    # 字体
    anchor_font_family: str = "Arial"
    anchor_font_size: int = 7
    anchor_font_bold: bool = False
    expand_font_family: str = "Arial"
    expand_font_size: int = 7
    expand_font_bold: bool = True

    def apply(self, node_item):
        from PyQt6.QtGui import QPen, QBrush, QFont
        from PyQt6.QtCore import Qt
        w, h = self.node_width, self.node_height

        # 隐藏圆点
        if hasattr(node_item, '_body') and node_item._body:
            node_item._body.setVisible(False)

        # 方框本体
        node_item.setBrush(QBrush(QColor(self.bg_color)))
        node_item.setPen(QPen(QColor(self.border_color), self.border_width))
        node_item.setRect(0, 0, w, h)
        node_item.setZValue(1)

        # 名称
        f = QFont(self.name_font_family, self.name_font_size)
        if self.name_font_bold: f.setBold(True)
        node_item.name_text.setDefaultTextColor(QColor(self.text_color))
        node_item.name_text.setFont(f)
        node_item.name_text.setVisible(True)
        nr = node_item.name_text.boundingRect()
        node_item.name_text.setPos((w - nr.width()) / 2, self.name_y)

        # 语言标签
        f2 = QFont(self.lang_font_family, self.lang_font_size)
        if self.lang_font_bold: f2.setBold(True)
        node_item.lang_text.setDefaultTextColor(QColor(self.lang_color))
        node_item.lang_text.setFont(f2)
        node_item.lang_text.setVisible(True)
        lr = node_item.lang_text.boundingRect()
        node_item.lang_text.setPos((w - lr.width()) / 2, h + self.lang_y)

        # IN / OUT 标签
        ft = QFont(self.anchor_font_family, self.anchor_font_size)
        if self.anchor_font_bold: ft.setBold(True)
        if hasattr(node_item, '_in_label') and node_item._in_label:
            node_item._in_label.setDefaultTextColor(QColor(self.in_label_color))
            node_item._in_label.setFont(ft)
            node_item._in_label.setPos(self.in_label_x, h / 2 + self.label_y)
            node_item._in_label.setVisible(True)
        if hasattr(node_item, '_out_label') and node_item._out_label:
            node_item._out_label.setDefaultTextColor(QColor(self.out_label_color))
            node_item._out_label.setFont(ft)
            node_item._out_label.setPos(w + self.out_label_x, h / 2 + self.label_y)
            node_item._out_label.setVisible(True)

        # 锚点
        if hasattr(node_item, 'input_anchor'):
            node_item.input_anchor.setPos(self.anchor_in_x, h / 2 - 8)
            node_item.input_anchor.setVisible(True)
        if hasattr(node_item, 'output_anchor'):
            node_item.output_anchor.setPos(w - 8, h / 2 - 8)
            node_item.output_anchor.setVisible(True)

        # 展开按钮
        ex, ey = w + self.expand_x, self.expand_y
        node_item._expand_btn.setRect(ex, ey, self.expand_w, self.expand_h)
        node_item._expand_btn.setBrush(QBrush(QColor(self.expand_bg)))
        node_item._expand_btn.setPen(QPen(QColor(self.expand_border), 1))
        node_item._expand_btn.setVisible(True)
        node_item._expand_btn_rect.setRect(ex, ey, self.expand_w, self.expand_h)

        ef = QFont(self.expand_font_family, self.expand_font_size)
        if self.expand_font_bold: ef.setBold(True)
        node_item._expand_label.setDefaultTextColor(QColor(self.expand_text))
        node_item._expand_label.setFont(ef)
        node_item._expand_label.setPos(ex + self.expand_text_x, ey + self.expand_text_y)
        node_item._expand_label.setVisible(True)

        # 状态灯
        node_item.status_indicator.setRect(self.indicator_x, self.indicator_y, self.indicator_size, self.indicator_size)
        node_item.status_indicator.setVisible(True)

    def apply_status(self, node_item, status):
        from PyQt6.QtGui import QColor, QBrush, QPen
        c = QColor(self.status_running if status == "running" else self.status_stopped)
        b = QColor(self.status_running_border if status == "running" else self.status_stopped_border)
        node_item.status_indicator.setBrush(QBrush(c))
        node_item.status_indicator.setPen(QPen(b, 1.5))


class DarkRectNodeStyle(RectNodeStyle):
    """VSCode 深色方框（默认）"""
    style_name: str = "深色方块"
    pass


class LightRectNodeStyle(RectNodeStyle):
    """浅色方框"""
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


# ============================================================
#  圆形节点样式
# ============================================================

class DotNodeStyle(NodeStyle):
    """圆形节点 — 圆点即状态灯/输入锚点，名称在左下角相切"""
    style_name: str = "圆形节点"
    is_dot: bool = True

    node_width: int = 80
    node_height: int = 80
    dot_radius: int = 20
    name_font_size: int = 9
    lang_font_size: int = 7

    def apply(self, node_item):
        from PyQt6.QtWidgets import QGraphicsEllipseItem
        from PyQt6.QtGui import QPen, QBrush, QFont
        from PyQt6.QtCore import Qt
        w, h = self.node_width, self.node_height
        r = self.dot_radius
        cx, cy = w // 2 - r, h // 4 - r

        # 方框与圆点一致（选中框不超出圆点）
        node_item.setBrush(QBrush(Qt.GlobalColor.transparent))
        node_item.setPen(QPen(Qt.PenStyle.NoPen))
        node_item.setRect(cx, cy, r * 2, r * 2)

        # 隐藏所有方框专属组件
        for attr in ('input_anchor', 'output_anchor', '_in_label', '_out_label',
                     '_expand_btn', '_expand_label'):
            if hasattr(node_item, attr) and getattr(node_item, attr, None):
                getattr(node_item, attr).setVisible(False)
        node_item.status_indicator.setVisible(False)
        node_item._expand_btn_rect.setRect(-100, -100, 1, 1)

        # 圆点本体
        if not hasattr(node_item, '_body') or node_item._body is None:
            node_item._body = QGraphicsEllipseItem(cx, cy, r * 2, r * 2, node_item)
            node_item._body.setZValue(5)
        else:
            node_item._body.setRect(cx, cy, r * 2, r * 2)
        node_item._body.setVisible(True)
        node_item._body.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.apply_status(node_item, node_item.status)

        # 圆底 y，文字从这里开始（相切）
        dot_bottom = cy + 2 * r
        text_x = cx  # 左对齐

        # 名称
        f = QFont(self.name_font_family, self.name_font_size)
        if self.name_font_bold: f.setBold(True)
        node_item.name_text.setDefaultTextColor(QColor(self.text_color))
        node_item.name_text.setFont(f)
        node_item.name_text.setVisible(True)
        node_item.name_text.setPos(text_x, dot_bottom + 2)

        # 语言标签（名称下方）
        f2 = QFont(self.lang_font_family, self.lang_font_size)
        if self.lang_font_bold: f2.setBold(True)
        node_item.lang_text.setDefaultTextColor(QColor(self.lang_color))
        node_item.lang_text.setFont(f2)
        node_item.lang_text.setVisible(True)
        nr = node_item.name_text.boundingRect()
        node_item.lang_text.setPos(text_x, dot_bottom + 2 + nr.height() + 1)

    def apply_status(self, node_item, status):
        from PyQt6.QtGui import QColor, QBrush, QPen
        if hasattr(node_item, '_body') and node_item._body:
            c = QColor(self.status_running if status == "running" else self.status_stopped)
            b = QColor(self.status_running_border if status == "running" else self.status_stopped_border)
            node_item._body.setBrush(QBrush(c))
            node_item._body.setPen(QPen(b, 2.5))


# ============================================================
#  注册表
# ============================================================

STYLES = {
    "dark_rect": DarkRectNodeStyle,
    "light_rect": LightRectNodeStyle,
    "dot": DotNodeStyle,
}
