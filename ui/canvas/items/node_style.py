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
    style_name: str = "k_node_style_square"
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
        # —— 同时清理参数行位置缓存 ——
        if hasattr(node_item, "_param_row_positions"):
            node_item._param_row_positions.clear()

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

        # 锚点（框图模式：左右各一个 default 单锚点）
        # 委托给 AnchorManager.layout_for_rect，不再直接操作 AnchorItem
        if hasattr(node_item, 'anchor_manager'):
            node_item.anchor_manager.layout_for_rect(w, h)
        elif hasattr(node_item, 'input_anchor'):
            # 兜底：老代码路径（理论上永远不会走到）
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
    """节点模式"""
    style_key: str = "dot"
    style_name: str = "k_node_style_circular"
    is_dot: bool = True

    node_width: int = 80
    node_height: int = 80
    dot_radius: int = 20
    name_font_size: int = 9
    lang_font_size: int = 7

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
        # —— 清理参数行位置缓存 ——
        if hasattr(node_item, "_param_row_positions"):
            node_item._param_row_positions.clear()

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

        # ===== 圆形节点：单锚点（不支持多输入，会重叠）=====
        # 委托给 AnchorManager.layout_for_dot，不再直接操作 AnchorItem
        out_sz = r * 2
        in_extra = 6
        in_sz = r * 2 + in_extra
        anchor_out_pos = (cx, cy)
        anchor_in_pos = (cx - in_extra // 2, cy - in_extra // 2)

        if hasattr(node_item, 'anchor_manager'):
            node_item.anchor_manager.layout_for_dot(
                w, h,
                anchor_in_size=in_sz, anchor_in_pos=anchor_in_pos,
                anchor_out_size=out_sz, anchor_out_pos=anchor_out_pos,
            )
        else:
            # 兜底：老代码路径
            if hasattr(node_item, 'destroy_all_anchors'):
                node_item.destroy_all_anchors()
            if hasattr(node_item, '_ensure_default_anchors'):
                node_item._ensure_default_anchors()
            if hasattr(node_item, 'output_anchor') and node_item.output_anchor:
                node_item.output_anchor.setRect(0, 0, out_sz, out_sz)
                node_item.output_anchor.setPos(cx, cy)
                node_item.output_anchor.setZValue(4)
                node_item.output_anchor.setVisible(True)
                node_item.output_anchor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            if hasattr(node_item, 'input_anchor') and node_item.input_anchor:
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
#  面板模式节点样式（ComfyUI 式画布直显）
# ============================================================

class DetailedNodeStyle(RectNodeStyle):
    """ComfyUI 风格面板模式节点 — 画布上直显参数编辑控件

    核心特征：
      - 圆角矩形边框（8px 圆角）
      - 顶部彩色标题栏（按语言/类型区分颜色）
      - 每行一个端口/参数：[左侧锚点] + [标签] + [参数控件]
      - 深色背景（#2d2d30），浅色文字
      - 右侧独立输出锚点（底部一行）

    尺寸由子控件内容驱动（两阶段构建）：
      1. 先 build 所有参数控件并测量其自然尺寸
      2. 节点宽度 = 最长标签 + 最长控件 + 左右边距 + 锚点预留
      3. 节点高度 = 标题高度 + Σ(行高) + 底部留白
    """
    style_key: str = "detailed"
    style_name: str = "k_node_style_detailed"
    is_dot: bool = False
    status_show: bool = False

    # === ComfyUI 风格布局常量 ===
    CORNER_RADIUS = 8           # 圆角半径
    HEADER_HEIGHT = 28           # 标题栏高度
    HEADER_TEXT_PADDING = 10     # 标题栏左右内边距
    ROW_HEIGHT = 32             # 单行基准高度
    ROW_SPACING = 2             # 行间距
    BOTTOM_PADDING = 8           # 底部留白
    LABEL_WIDTH = 80             # 标签列固定宽度
    ANCHOR_ZONE_WIDTH = 16       # 左侧锚点预留宽度
    LEFT_INNER_PADDING = 12       # 内容区左边距
    RIGHT_INNER_PADDING = 12       # 内容区右边距
    MIN_NODE_WIDTH = 380         # 节点最小宽度（确保内容有足够空间）

    # === ComfyUI 风格颜色 ===
    body_bg = "#2d2d30"         # 节点主体背景色
    body_border = "#454545"     # 节点边框色
    header_text_color = "#ffffff"  # 标题栏文字色（白）
    body_text_color = "#cccccc"     # 主体文字色

    # 标题栏颜色：按语言/类型区分（ComfyUI 风格的节点颜色）
    HEADER_COLORS = {
        "python": "#49cc90",    # 绿色系 - Python 节点
        "rust": "#dea584",      # 橙色系 - Rust 节点
        "node": "#3c873a",      # 深绿 - Node.js 节点
        "default": "#555555",   # 灰色 - 默认
    }

    @classmethod
    def header_color_for(cls, language: str) -> str:
        return cls.HEADER_COLORS.get((language or "").lower(), cls.HEADER_COLORS["default"])

    def __init__(self):
        super().__init__()
        self._computed_width = self.MIN_NODE_WIDTH
        self._computed_height = 120

    def set_sizes(self, content_width: int, content_height: int):
        """由 NodeItem 调用 — 根据实际内容尺寸设置节点宽高"""
        self._computed_width = max(self.MIN_NODE_WIDTH, content_width)
        self._computed_height = self.HEADER_HEIGHT + content_height + self.BOTTOM_PADDING
        self.node_width = self._computed_width
        self.node_height = self._computed_height

    def apply(self, node_item):
        """ComfyUI 风格 apply：
        1. 清理旧样式（brush/pen/tags）
        2. _build_detailed_view 构建参数控件 → 计算节点尺寸
        3. build_anchors_from_config 根据 config 生成多锚点
        """
        # 关闭缓存模式（详细版中有 proxy widgets，缓存会导致视觉错误）
        from PyQt6.QtWidgets import QGraphicsItem
        node_item.setCacheMode(QGraphicsItem.CacheMode.NoCache)

        # 确保 QGraphicsRectItem 不绘制额外的方形背景/边框（paint 完全由我们控制）
        from PyQt6.QtGui import QBrush, QPen, QColor
        from PyQt6.QtCore import Qt
        node_item.setBrush(QBrush(QColor(0, 0, 0, 0)))  # 透明
        node_item.setPen(QPen(Qt.PenStyle.NoPen))

        # 隐藏状态控件
        if hasattr(node_item, "_status_widget") and node_item._status_widget:
            node_item._status_widget.set_visible(False)
        # 隐藏 IN/OUT 标签（ComfyUI 风格不显示，改为行内标签）
        if hasattr(node_item, "_in_label") and node_item._in_label:
            node_item._in_label.setVisible(False)
        if hasattr(node_item, "_out_label") and node_item._out_label:
            node_item._out_label.setVisible(False)
        # 隐藏展开按钮
        if hasattr(node_item, "_expand_btn") and node_item._expand_btn:
            node_item._expand_btn.setVisible(False)
        if hasattr(node_item, "_expand_label") and node_item._expand_label:
            node_item._expand_label.setVisible(False)
        # 隐藏状态灯
        if hasattr(node_item, "status_indicator") and node_item.status_indicator:
            node_item.status_indicator.setVisible(False)
        # 隐藏语言标签（标题栏已经显示节点名）
        if hasattr(node_item, "lang_text") and node_item.lang_text:
            node_item.lang_text.setVisible(False)

        # 构建详细视图（标题栏 + 参数控件 + 锚点位置）
        node_item._build_detailed_view()

        # 构建多输入锚点
        if hasattr(node_item, "build_anchors_from_config"):
            config = None
            if hasattr(node_item, "_get_node_config"):
                config = node_item._get_node_config()
            node_item.build_anchors_from_config(config)


# ============================================================
#  注册表
# ============================================================

STYLES = {
    "rect": DarkRectNodeStyle,
    "dot": DotNodeStyle,
    "detailed": DetailedNodeStyle,
}
DEFAULT_STYLE = "rect"