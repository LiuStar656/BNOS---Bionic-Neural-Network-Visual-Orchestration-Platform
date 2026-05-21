"""
节点样式系统 — 分离视觉样式，为多套节点外观做基础
"""
from PyQt6.QtGui import QColor


class NodeStyle:
    """节点样式基类 — 所有节点外观的抽象"""

    # ===== 几何布局 =====
    node_width: int = 140
    node_height: int = 80

    name_y: int = 15                     # 节点名称 Y 偏移
    lang_y: int = -18                    # 语言标签 Y 偏移（距底边）
    anchor_size: int = 16                # 锚点尺寸
    anchor_in_x: int = -8                # 输入端 X 偏移
    anchor_out_x: int = -8               # 输出端 X 偏移（距右边界）

    indicator_x: int = 8                 # 状态灯 X
    indicator_y: int = 8                 # 状态灯 Y
    indicator_size: int = 10             # 状态灯直径

    expand_x: int = -20                  # 展开按钮 X（距右边界）
    expand_y: int = 4                    # 展开按钮 Y
    expand_w: int = 14                   # 展开按钮宽
    expand_h: int = 14                   # 展开按钮高
    expand_text_x: int = -1              # 展开文字 X 偏移
    expand_text_y: int = -1              # 展开文字 Y 偏移

    in_label_x: int = -22                # IN 标签 X
    out_label_x: int = 4                 # OUT 标签 X（距右边界）
    label_y: int = -5                    # 标签 Y（距中心）

    border_width: int = 2                # 普通边框宽度
    selected_border_width: int = 3       # 选中边框宽度

    # ===== 颜色 =====
    bg_color: str = "#2d2d30"
    border_color: str = "#454545"
    text_color: str = "#d4d4d4"
    selected_color: str = "#007acc"

    lang_color: str = "#888888"          # 语言标签色
    in_label_color: str = "#6a9955"      # IN 标签色
    out_label_color: str = "#007acc"     # OUT 标签色

    status_running: str = "#FF4444"      # 运行中 — 红灯
    status_running_border: str = "#CC0000"
    status_stopped: str = "#44FF44"      # 已停止 — 绿灯
    status_stopped_border: str = "#00CC00"

    expand_bg: str = "#555555"           # 展开按钮背景
    expand_border: str = "#444444"       # 展开按钮边框
    expand_text: str = "#cccccc"         # 展开符号色

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

    def apply(self, node_item):
        """将样式应用到节点"""
        from PyQt6.QtGui import QPen, QBrush, QFont
        from PyQt6.QtCore import Qt

        w = self.node_width
        h = self.node_height

        # 背景 + 边框
        node_item.setBrush(QBrush(QColor(self.bg_color)))
        node_item.setPen(QPen(QColor(self.border_color), self.border_width))
        node_item.setRect(0, 0, w, h)

        # 文字
        node_item.name_text.setDefaultTextColor(QColor(self.text_color))
        font = QFont(self.name_font_family, self.name_font_size)
        if self.name_font_bold:
            font.setBold(True)
        node_item.name_text.setFont(font)
        nr = node_item.name_text.boundingRect()
        node_item.name_text.setPos((w - nr.width()) / 2, self.name_y)

        # 语言标签
        node_item.lang_text.setDefaultTextColor(QColor(self.lang_color))
        font2 = QFont(self.lang_font_family, self.lang_font_size)
        if self.lang_font_bold:
            font2.setBold(True)
        node_item.lang_text.setFont(font2)
        lr = node_item.lang_text.boundingRect()
        node_item.lang_text.setPos((w - lr.width()) / 2, h + self.lang_y)

        # IN / OUT 标签
        ft = QFont(self.anchor_font_family, self.anchor_font_size)
        if self.anchor_font_bold:
            ft.setBold(True)
        if hasattr(node_item, '_in_label'):
            node_item._in_label.setDefaultTextColor(QColor(self.in_label_color))
            node_item._in_label.setFont(ft)
            node_item._in_label.setPos(self.in_label_x, h / 2 + self.label_y)
        if hasattr(node_item, '_out_label'):
            node_item._out_label.setDefaultTextColor(QColor(self.out_label_color))
            node_item._out_label.setFont(ft)
            node_item._out_label.setPos(w + self.out_label_x, h / 2 + self.label_y)

        # 展开按钮
        ex = w + self.expand_x
        ey = self.expand_y
        node_item._expand_btn.setRect(ex, ey, self.expand_w, self.expand_h)
        node_item._expand_btn.setBrush(QBrush(QColor(self.expand_bg)))
        node_item._expand_btn.setPen(QPen(QColor(self.expand_border), 1))
        node_item._expand_btn_rect.setRect(ex, ey, self.expand_w, self.expand_h)

        efont = QFont(self.expand_font_family, self.expand_font_size)
        if self.expand_font_bold:
            efont.setBold(True)
        node_item._expand_label.setDefaultTextColor(QColor(self.expand_text))
        node_item._expand_label.setFont(efont)
        node_item._expand_label.setPos(ex + self.expand_text_x, ey + self.expand_text_y)

        # 状态灯
        node_item.status_indicator.setRect(
            self.indicator_x, self.indicator_y,
            self.indicator_size, self.indicator_size
        )

    def apply_status(self, node_item, status):
        """应用运行状态颜色"""
        from PyQt6.QtGui import QColor, QBrush, QPen
        if status == "running":
            node_item.status_indicator.setBrush(QBrush(QColor(self.status_running)))
            node_item.status_indicator.setPen(QPen(QColor(self.status_running_border), 1.5))
        else:
            node_item.status_indicator.setBrush(QBrush(QColor(self.status_stopped)))
            node_item.status_indicator.setPen(QPen(QColor(self.status_stopped_border), 1.5))


class DarkNodeStyle(NodeStyle):
    """VSCode 深色主题节点样式（默认）"""
    pass


class LightNodeStyle(NodeStyle):
    """浅色主题节点样式"""
    bg_color: str = "#ffffff"
    border_color: str = "#d4d4d4"
    text_color: str = "#333333"
    selected_color: str = "#007acc"
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


# 预设风格注册表
STYLES = {
    "dark": DarkNodeStyle,
    "light": LightNodeStyle,
}
