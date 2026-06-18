"""
节点样式管理模块 — 样式设置、尺寸管理、显示更新

从 node_item.py 拆分出来。
"""
from PySide6.QtGui import QColor, QFont, QPen
from ui.canvas.items.styles import DetailedNodeStyle
from ui.canvas.items.node_status_widget import NodeStatusWidget
from ui.core.logger import logger


class NodeStyleManager:
    """样式管理：set_style、尺寸、update_display、sync_with_data"""

    def __init__(self, node):
        self._node = node

    def set_style(self, style):
        """设置节点样式（统一使用面板模式）"""
        # 销毁所有 Proxy 控件
        if hasattr(self._node, '_proxy_widgets') and self._node._proxy_widgets:
            self._node._destroy_detailed()

        # 只有 DetailedNodeStyle 被支持
        self._node._style = style or DetailedNodeStyle()
        self._node._style.node_width = self._node.rect().width() or 340
        self._node._style.node_height = self._node.rect().height() or 80

        # 应用新样式（刷新设备坐标缓存，让新样式立即生效）
        self._node.setCacheMode(self._node.CacheMode.NoCache)
        self._node.prepareGeometryChange()
        self._node.setRect(0, 0, self._node._style.node_width, self._node._style.node_height)
        self._node._style.apply(self._node)
        self._node._style.apply_status(self._node, self._node.status)

        # 同步显示状态控件
        if not self._node._status_widget:
            self._node._status_widget = NodeStatusWidget(self._node)
        self._node._status_widget.set_compact(True)
        self._node._status_widget.set_visible(True)
        self._node._status_widget.update_layout()
        self._node._start_time = None
        self._node._status_manager.connect_resource_monitor_signals()

        self._node._update_selection_ring(self._node.isSelected())

        # 只标记本节点 item 为 dirty，不触发全场景重绘
        self._node.setCacheMode(self._node.CacheMode.DeviceCoordinateCache)
        self._node.update()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._ensure_rect(
            self._node._style.node_width, self._node._style.node_height))

    def _ensure_rect(self, w, h):
        """兜底：事件循环后强制校正节点尺寸"""
        if self._node._style.style_key == "detailed":
            return  # 详细版由内容驱动尺寸
        current_rect = self._node.rect()
        if abs(current_rect.width() - w) > 0.5 or abs(current_rect.height() - h) > 0.5:
            self._node.prepareGeometryChange()
            self._node.setCacheMode(self._node.CacheMode.NoCache)
            self._node.setRect(0, 0, w, h)
            self._node.setCacheMode(self._node.CacheMode.DeviceCoordinateCache)
            self._node.update()

    def update_display(self, node_name=None, language=None, status=None):
        """更新节点显示信息（与数据同步）"""
        w = self._node.rect().width()
        h = self._node.rect().height()

        if node_name:
            self._node.node_name = node_name
            self._node.name_text.setPlainText(node_name)

        if language:
            self._node.language = language
            self._node.lang_text.setPlainText(language)

        if node_name or language:
            self._node._style.apply(self._node)

        if status:
            self._node._status_manager.update_status(status)

    def sync_with_data(self, node_data):
        """从节点数据字典同步所有信息"""
        if 'name' in node_data:
            self.update_display(node_name=node_data['name'])
        if 'language' in node_data:
            self.update_display(language=node_data['language'])
        if 'status' in node_data:
            self.update_display(status=node_data['status'])
