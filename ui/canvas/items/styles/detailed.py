"""
面板模式节点样式 — ComfyUI 风格画布直显
"""
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QBrush, QPen, QColor
from PyQt6.QtCore import Qt
from .rect import RectNodeStyle


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
    CORNER_RADIUS = 8
    HEADER_HEIGHT = 28
    HEADER_TEXT_PADDING = 10
    ROW_HEIGHT = 32
    ROW_SPACING = 2
    BOTTOM_PADDING = 8
    LABEL_WIDTH = 80
    ANCHOR_ZONE_WIDTH = 16
    LEFT_INNER_PADDING = 12
    RIGHT_INNER_PADDING = 12
    MIN_NODE_WIDTH = 380

    # === ComfyUI 风格颜色 ===
    body_bg = "#2d2d30"
    body_border = "#454545"
    header_text_color = "#ffffff"
    body_text_color = "#cccccc"

    HEADER_COLORS = {
        "python": "#49cc90",
        "rust": "#dea584",
        "node": "#3c873a",
        "default": "#555555",
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
        node_item.setCacheMode(QGraphicsItem.CacheMode.NoCache)

        # 确保 QGraphicsRectItem 不绘制额外的方形背景/边框
        node_item.setBrush(QBrush(QColor(0, 0, 0, 0)))
        node_item.setPen(QPen(Qt.PenStyle.NoPen))

        # 隐藏圆点节点本体
        if hasattr(node_item, '_body') and node_item._body:
            node_item._body.setVisible(False)
        # 隐藏状态控件
        if hasattr(node_item, "_status_widget") and node_item._status_widget:
            node_item._status_widget.set_visible(False)
        # 隐藏 IN/OUT 标签
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
        # 隐藏语言标签
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
