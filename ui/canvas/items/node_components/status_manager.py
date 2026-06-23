"""
节点状态管理模块 — 资源监测信号、状态更新、NodeStatusWidget 管理

从 node_item.py 拆分出来。
"""
from datetime import datetime
from ui.core.logger import logger
from ui.canvas.items.node_status_widget import NodeStatusWidget


class NodeStatusManager:
    """状态管理：资源监测信号连接、状态更新、开始时间"""

    def __init__(self, node):
        self._node = node

    def connect_resource_monitor_signals(self):
        """连接资源监测面板的信号"""
        if not self._node.canvas or not self._node.canvas.parent_window:
            return

        parent = self._node.canvas.parent_window

        if hasattr(parent, 'resource_monitor') and parent.resource_monitor:
            if hasattr(parent.resource_monitor, 'node_state_updated'):
                parent.resource_monitor.node_state_updated.connect(
                    self._on_status_updated)

    def _on_status_updated(self, node_name, cpu_percent, mem_mb):
        """状态更新回调（从资源监测面板接收）"""
        if node_name == self._node.node_name and self._node._status_widget:
            self._node._status_widget.update_status(cpu_percent, mem_mb)

    def try_initialize_start_time(self):
        """尝试从节点数据中初始化开始时间"""
        if not self._node.canvas or not self._node.canvas.parent_window:
            return

        if self._node.node_name in self._node.canvas.parent_window.nodes_data:
            node_info = self._node.canvas.parent_window.nodes_data[self._node.node_name]
            if node_info.get('status') in ['running', 'idle']:
                self._node._start_time = datetime.now()

    def update_status(self, status):
        """更新节点状态"""
        self._node.status = status
        self._node._style.apply_status(self._node, status)

        if status in ["running", "idle"]:
            if self._node._status_widget:
                if self._node._start_time is None:
                    self._node._start_time = datetime.now()
                self.connect_resource_monitor_signals()
            elif self._node._style.status_show:
                self._node._status_widget = NodeStatusWidget(self._node)
                self._node._status_widget.set_visible(True)
                self._node._start_time = datetime.now()
                self.connect_resource_monitor_signals()
        else:
            self._node._start_time = None

    def dispose_signals(self):
        """断开所有资源监测面板信号连接"""
        if self._node.canvas and self._node.canvas.parent_window:
            parent = self._node.canvas.parent_window
            try:
                if hasattr(parent, 'resource_monitor') and parent.resource_monitor:
                    if hasattr(parent.resource_monitor, 'node_state_updated'):
                        parent.resource_monitor.node_state_updated.disconnect(
                            self._on_status_updated)
            except (TypeError, RuntimeError):
                pass

    def dispose_status_widget(self):
        """停止状态组件计时器"""
        if self._node._status_widget:
            try:
                self._node._status_widget.stop_timer()
            except Exception:
                pass
