"""
节点绘制模块 — paint 方法实现与自定义颜色应用

从 node_item.py 拆分出来，负责视觉渲染。
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QPainterPath


class NodeRendering:
    """绘制与自定义颜色管理"""

    def __init__(self, node):
        self._node = node

    def paint(self, painter: QPainter, option, widget=None):
        """绘制节点 — 圆角矩形 + 选中高亮边框"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self._node.rect()
        w = rect.width()
        h = rect.height()
        corner_radius = self._node._style.CORNER_RADIUS
        body_bg = self._node._style.body_bg
        body_border = self._node._style.body_border
        node_rect = QRectF(0, 0, w, h)

        # 1. 主体圆角矩形背景
        body_path = QPainterPath()
        body_path.addRoundedRect(node_rect, corner_radius, corner_radius)
        painter.setBrush(QBrush(QColor(body_bg)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(body_path)

        # 2. 边框（选中状态高亮）
        border_color = QColor("#66b0ff") if self._node.isSelected() else QColor(body_border)
        border_width = 2 if self._node.isSelected() else 1
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(QBrush())
        painter.drawPath(body_path)

    def apply_custom_colors(self):
        """加载并应用节点的自定义颜色配置"""
        if not self._node.canvas or not self._node.canvas.parent_window:
            return

        node_name = self._node.node_name
        if node_name not in self._node.canvas.parent_window.nodes_data:
            return

        node_info = self._node.canvas.parent_window.nodes_data[node_name]
        config = node_info.get("config", {})

        # 应用自定义背景色
        if "custom_bg_color" in config:
            try:
                custom_color = QColor(config["custom_bg_color"])
                if custom_color.isValid():
                    self._node.setBrush(custom_color)
            except Exception:
                pass
        if "custom_border_color" in config:
            try:
                custom_color = QColor(config["custom_border_color"])
                if custom_color.isValid():
                    self._node.setPen(QPen(custom_color, 2))
            except Exception:
                pass

        # 应用自定义文字色
        if "custom_text_color" in config:
            try:
                custom_color = QColor(config["custom_text_color"])
                if custom_color.isValid():
                    self._node.name_text.setDefaultTextColor(custom_color)
            except Exception:
                pass
