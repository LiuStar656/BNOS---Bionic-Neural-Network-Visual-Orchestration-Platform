"""
面板模式节点样式 — ComfyUI 风格画布直显
"""
from PySide6.QtWidgets import QGraphicsItem
from PySide6.QtGui import QBrush, QPen, QColor
from PySide6.QtCore import Qt
from ._base import NodeStyle


class DetailedNodeStyle(NodeStyle):
    """面板模式节点 — 画布上直显参数编辑控件

    核心特征：
      - 圆角矩形边框（8px 圆角）
      - 每行一个端口/参数：[左侧锚点] + [标签] + [参数控件]
      - 深色背景（#2d2d30），浅色文字
      - 右侧独立输出锚点（底部一行）
      - 标题栏右侧状态指示灯

    尺寸由子控件内容驱动：
      1. 先 build 所有参数控件并测量其自然尺寸
      2. 节点宽度 = 最长标签 + 最长控件 + 左右边距 + 锚点预留
      3. 节点高度 = 标题高度 + Σ(行高) + 底部留白
    """
    style_key: str = "detailed"
    style_name: str = "k_node_style_detailed"
    is_dot: bool = False
    status_show: bool = True

    # === 几何（继承自 NodeStyle 基类） ===
    # node_width / node_height 由运行时计算，默认值在基类中定义

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
    MIN_NODE_WIDTH = 340

    # === ComfyUI 风格颜色 ===
    body_bg = "#2d2d30"
    body_border = "#454545"
    header_text_color = "#ffffff"
    body_text_color = "#cccccc"

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
        """apply：
        1. 清理旧样式（brush/pen/tags）
        2. _build_detailed_view 构建参数控件 → 计算节点尺寸
        3. build_anchors_from_config 根据 config 生成多锚点
        """
        # 从 canvas 读取颜色设置
        if node_item.canvas:
            self.body_bg = getattr(node_item.canvas, 'node_bg_color', '#2d2d30')
            self.body_border = getattr(node_item.canvas, 'node_border_color', '#454545')
            self.body_text_color = getattr(node_item.canvas, 'node_text_color', '#cccccc')

        # 关闭缓存模式（详细版中有 proxy widgets，缓存会导致视觉错误）
        node_item.setCacheMode(QGraphicsItem.CacheMode.NoCache)

        # 确保 QGraphicsRectItem 不绘制额外的方形背景/边框
        node_item.setBrush(QBrush(QColor(0, 0, 0, 0)))
        node_item.setPen(QPen(Qt.PenStyle.NoPen))

        # 隐藏节点本体（若存在）
        if hasattr(node_item, '_body') and node_item._body:
            node_item._body.setVisible(False)
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
        # 先创建状态控件（_build_detailed_view 会用它设置 CPU/MEM 位置）
        if not hasattr(node_item, "_status_widget") or node_item._status_widget is None:
            from ui.canvas.items.node_status_widget import NodeStatusWidget
            node_item._status_widget = NodeStatusWidget(node_item)
        node_item._status_widget.set_compact(True)
        node_item._status_widget.set_visible(True)

        # 隐藏语言标签（_build_detailed_view 会重新设置正确位置）
        if hasattr(node_item, "lang_text") and node_item.lang_text:
            node_item.lang_text.setVisible(False)

        # 构建详细视图（参数控件 + 锚点位置 + 名称/状态灯/语言标签/CPU/MEM位置）
        node_item._build_detailed_view()

        # 构建多输入锚点
        if hasattr(node_item, "build_anchors_from_config"):
            config = None
            if hasattr(node_item, "_get_node_config"):
                config = node_item._get_node_config()
            node_item.build_anchors_from_config(config)

        # 更新状态控件布局（确保位置正确）
        node_item._status_widget.update_layout()

    def apply_status(self, node_item, status):
        """根据 status 更新指示灯颜色"""
        if not hasattr(node_item, 'status_indicator') or not node_item.status_indicator:
            return
        if status == "running":
            c = QColor(self.status_running)
        elif status == "idle":
            c = QColor(self.status_idle)
        elif status == "queued":
            c = QColor("#4A90E2")
        elif status == "blocked":
            c = QColor("#F5A623")
        elif status == "starting":
            c = QColor("#F5A623")
        else:
            c = QColor(self.status_stopped)
        node_item.status_indicator.setBrush(QBrush(c))
        node_item.status_indicator.setPen(QPen(c, 1))
