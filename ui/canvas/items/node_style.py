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
    node_height: int = 120  # 增加高度以容纳状态显示
    
    # 状态显示相关
    status_show: bool = False  # 是否显示状态信息
    status_cpu_y: int = -45    # CPU 信息Y坐标
    status_mem_y: int = -30    # 内存信息Y坐标
    status_duration_x: int = -80  # 运行时长X坐标
    status_duration_y: int = 10   # 运行时长Y坐标
    status_bar_height: int = 6    # 进度条高度

    # ===== 颜色 =====
    bg_color: str = "#2d2d30"
    border_color: str = "#454545"
    text_color: str = "#d4d4d4"
    selected_color: str = "#007acc"
    selected_border_width: int = 3
    lang_color: str = "#888888"

    status_stopped: str = "#888888"          # 灰色 = 已停止
    status_stopped_border: str = "#666666"
    status_idle: str = "#44FF44"            # 绿色 = 空闲（listener 运行，无任务）
    status_idle_border: str = "#00CC00"
    status_running: str = "#FF4444"         # 红色 = 运行中（main 正在执行）
    status_running_border: str = "#CC0000"
    
    # 状态显示颜色
    cpu_text_color: str = "#4ecdc4"    # CPU 文本颜色
    cpu_bar_color: str = "#4ecdc4"     # CPU 进度条颜色
    mem_text_color: str = "#ff6b6b"    # 内存文本颜色
    mem_bar_color: str = "#ff6b6b"     # 内存进度条颜色
    duration_text_color: str = "#ffe66d"  # 运行时长颜色
    status_bar_bg: str = "#333333"     # 进度条背景颜色
    status_bar_border: str = "#555555" # 进度条边框颜色

    # ===== 字体 =====
    name_font_family: str = "Arial"
    name_font_size: int = 10
    name_font_bold: bool = True
    lang_font_family: str = "Arial"
    lang_font_size: int = 8
    lang_font_bold: bool = False
    status_font_family: str = "Arial"
    status_font_size: int = 7
    status_font_bold: bool = True

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
    style_key: str = "rect"
    style_name: str = "方形"
    is_dot: bool = False
    status_show: bool = True  # 方形节点显示状态信息

    # 几何
    name_x: int = -1  # 名称X坐标，居中，设为-1表示居中
    name_y: int = 0   # 名称Y坐标，底边贴于最上方边线
    lang_y: int = -18  # 语言标签Y坐标，在节点下方
    anchor_in_x: int = -8
    anchor_out_x: int = -8
    indicator_x: int = 10  # 指示灯X坐标
    indicator_y: int = 10  # 指示灯Y坐标，在名称下方
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
        
        # 确定X坐标
        if self.name_x == -1:
            # 居中
            nx = (w - nr.width()) / 2
        else:
            nx = self.name_x
        
        # 确定Y坐标，让名称的底边贴于最上方边线
        ny = self.name_y - nr.height()
        
        node_item.name_text.setPos(nx, ny)

        # 语言标签
        f2 = QFont(self.lang_font_family, self.lang_font_size)
        if self.lang_font_bold: f2.setBold(True)
        node_item.lang_text.setDefaultTextColor(QColor(self.lang_color))
        node_item.lang_text.setFont(f2)
        node_item.lang_text.setVisible(True)
        lr = node_item.lang_text.boundingRect()
        
        # 语言标签的顶边和节点的底边相切
        lx = (w - lr.width()) / 2
        ly = h
        
        node_item.lang_text.setPos(lx, ly)

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

        # 锚点（在节点本体上方一线）
        if hasattr(node_item, 'input_anchor'):
            node_item.input_anchor.setRect(0, 0, 16, 16)  # 重置锚点尺寸为标准大小
            node_item.input_anchor.setPos(self.anchor_in_x, h / 2 - 8)
            node_item.input_anchor.setZValue(1)
            node_item.input_anchor.setVisible(True)
        if hasattr(node_item, 'output_anchor'):
            node_item.output_anchor.setRect(0, 0, 16, 16)  # 重置锚点尺寸为标准大小
            node_item.output_anchor.setPos(w - 8, h / 2 - 8)
            node_item.output_anchor.setZValue(1)
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


# ============================================================
#  圆形节点样式
# ============================================================

class DotNodeStyle(NodeStyle):
    """圆形节点"""
    style_key: str = "dot"
    style_name: str = "圆形"
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

        # 方框覆盖整个节点区域（圆点+文字），避免移动时网格残影
        node_item.prepareGeometryChange()
        node_item.setBrush(QBrush(Qt.GlobalColor.transparent))
        node_item.setPen(QPen(Qt.PenStyle.NoPen))
        node_item.setRect(0, 0, w, h)

        # 隐藏方框专属组件
        for attr in ('_in_label', '_out_label', '_expand_btn', '_expand_label'):
            if hasattr(node_item, attr) and getattr(node_item, attr, None):
                getattr(node_item, attr).setVisible(False)
        node_item.status_indicator.setVisible(False)
        node_item._expand_btn_rect.setRect(-100, -100, 1, 1)

        # ===== 三层锚点架构 =====
        # 输出锚点 — 最下层 (z=4)，尺寸=指示灯
        out_sz = r * 2
        node_item.output_anchor.setRect(0, 0, out_sz, out_sz)
        node_item.output_anchor.setPos(cx, cy)
        node_item.output_anchor.setZValue(4)
        node_item.output_anchor.setVisible(True)
        node_item.output_anchor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        # 输入锚点 — 中层 (z=5)，比指示灯大
        in_extra = 6
        in_sz = r * 2 + in_extra
        node_item.input_anchor.setRect(0, 0, in_sz, in_sz)
        node_item.input_anchor.setPos(cx - in_extra // 2, cy - in_extra // 2)
        node_item.input_anchor.setZValue(5)
        node_item.input_anchor.setVisible(True)
        node_item.input_anchor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        # 指示灯 — 最上层 (z=6)，可点击穿透
        body_sz = r * 2
        if not hasattr(node_item, '_body') or node_item._body is None:
            node_item._body = QGraphicsEllipseItem(cx, cy, body_sz, body_sz, node_item)
        else:
            node_item._body.setRect(cx, cy, body_sz, body_sz)
        node_item._body.setZValue(6)
        node_item._body.setVisible(True)
        node_item._body.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.apply_status(node_item, node_item.status)

        # 文字
        dot_bottom = cy + 2 * r
        text_x = cx
        f = QFont(self.name_font_family, self.name_font_size)
        if self.name_font_bold: f.setBold(True)
        node_item.name_text.setDefaultTextColor(QColor(self.text_color))
        node_item.name_text.setFont(f)
        node_item.name_text.setVisible(True)
        node_item.name_text.setPos(text_x, dot_bottom + 2)

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
            if status == "running":
                c, b = QColor(self.status_running), QColor(self.status_running_border)
            elif status == "idle":
                c, b = QColor(self.status_idle), QColor(self.status_idle_border)
            else:
                c, b = QColor(self.status_stopped), QColor(self.status_stopped_border)
            node_item._body.setBrush(QBrush(c))
            node_item._body.setPen(QPen(b, 2.5))


# ============================================================
#  注册表
# ============================================================

STYLES = {
    "rect": DarkRectNodeStyle,
    "dot": DotNodeStyle,
}
DEFAULT_STYLE = "rect"