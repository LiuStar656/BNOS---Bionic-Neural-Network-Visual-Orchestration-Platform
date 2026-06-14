"""
方框节点样式 — 框图模式（默认）
"""
from PySide6.QtGui import QPen, QBrush, QFont, QColor
from PySide6.QtCore import Qt
from ._base import NodeStyle


class RectNodeStyle(NodeStyle):
    """方框节点样式基类"""
    style_key: str = "rect"
    style_name: str = "k_node_style_square"
    is_dot: bool = False
    status_show: bool = True

    # 几何
    name_x: int = -1
    name_y: int = 0
    lang_y: int = -18
    anchor_in_x: int = -8
    anchor_out_x: int = -8
    indicator_x: int = 10
    indicator_y: int = 10
    indicator_size: int = 10
    expand_x: int = -20
    expand_y: int = 8
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
        # —— 清理 panel 模式留下的 proxy widgets ——
        if hasattr(node_item, "_proxy_widgets") and node_item._proxy_widgets:
            for p in node_item._proxy_widgets:
                try:
                    p.setWidget(None)
                    if p.scene():
                        p.scene().removeItem(p)
                except Exception:
                    pass
            node_item._proxy_widgets.clear()
        if hasattr(node_item, "_param_row_positions"):
            node_item._param_row_positions.clear()

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
        if self.name_font_bold:
            f.setBold(True)
        node_item.name_text.setDefaultTextColor(QColor(self.text_color))
        node_item.name_text.setFont(f)
        node_item.name_text.setVisible(True)
        nr = node_item.name_text.boundingRect()
        nx = (w - nr.width()) / 2 if self.name_x == -1 else self.name_x
        ny = self.name_y - nr.height()
        node_item.name_text.setPos(nx, ny)

        # 语言标签
        f2 = QFont(self.lang_font_family, self.lang_font_size)
        if self.lang_font_bold:
            f2.setBold(True)
        node_item.lang_text.setDefaultTextColor(QColor(self.lang_color))
        node_item.lang_text.setFont(f2)
        node_item.lang_text.setVisible(True)
        lr = node_item.lang_text.boundingRect()
        lx = (w - lr.width()) / 2
        ly = h
        node_item.lang_text.setPos(lx, ly)

        # IN / OUT 标签
        ft = QFont(self.anchor_font_family, self.anchor_font_size)
        if self.anchor_font_bold:
            ft.setBold(True)
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

        # 锚点（框图模式：左右各一个 default 单锚点）
        if hasattr(node_item, 'anchor_manager'):
            node_item.anchor_manager.layout_for_rect(w, h)
        elif hasattr(node_item, 'input_anchor'):
            if node_item.input_anchor:
                node_item.input_anchor.setRect(0, 0, 16, 16)
                node_item.input_anchor.setPos(self.anchor_in_x, h / 2 - 8)
                node_item.input_anchor.setZValue(1)
                node_item.input_anchor.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
                node_item.input_anchor.setVisible(True)
            if hasattr(node_item, 'output_anchor') and node_item.output_anchor:
                node_item.output_anchor.setRect(0, 0, 16, 16)
                node_item.output_anchor.setPos(w - 8, h / 2 - 8)
                node_item.output_anchor.setZValue(1)
                node_item.output_anchor.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
                node_item.output_anchor.setVisible(True)

        # 展开按钮
        ex, ey = w + self.expand_x, self.expand_y
        node_item._expand_btn.setRect(ex, ey, self.expand_w, self.expand_h)
        node_item._expand_btn.setBrush(QBrush(QColor(self.expand_bg)))
        node_item._expand_btn.setPen(QPen(QColor(self.expand_border), 1))
        node_item._expand_btn.setVisible(True)
        node_item._expand_btn_rect.setRect(ex, ey, self.expand_w, self.expand_h)

        ef = QFont(self.expand_font_family, self.expand_font_size)
        if self.expand_font_bold:
            ef.setBold(True)
        node_item._expand_label.setDefaultTextColor(QColor(self.expand_text))
        node_item._expand_label.setFont(ef)
        node_item._expand_label.setPos(ex + self.expand_text_x, ey + self.expand_text_y)
        node_item._expand_label.setVisible(True)

        # 状态灯
        node_item.status_indicator.setRect(self.indicator_x, self.indicator_y, self.indicator_size, self.indicator_size)
        node_item.status_indicator.setVisible(True)

    def apply_status(self, node_item, status):
        if status == "running":
            c, b = QColor(self.status_running), QColor(self.status_running_border)
        elif status == "idle":
            c, b = QColor(self.status_idle), QColor(self.status_idle_border)
        else:
            c, b = QColor(self.status_stopped), QColor(self.status_stopped_border)
        node_item.status_indicator.setBrush(QBrush(c))
        node_item.status_indicator.setPen(QPen(b, 1.5))


class DarkRectNodeStyle(RectNodeStyle):
    """VSCode 深色方框（默认）"""
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
    status_stopped: str = "#888888"
    status_stopped_border: str = "#666666"
    status_idle: str = "#44FF44"
    status_idle_border: str = "#00CC00"
    status_running: str = "#e81123"
    status_running_border: str = "#cc0000"
    expand_bg: str = "#e0e0e0"
    expand_border: str = "#cccccc"
    expand_text: str = "#666666"
