"""
NodeMonitor 面板节点同步 Mixin — 消除 node_monitor.py 与 node_monitor_dock.py 顶层的重复逻辑

提供:
  - _sync_panels(): 同步子面板列表与画布节点
  - _add_sub_panel(): 添加节点日志子面板
  - _remove_sub_panel(): 移除节点日志子面板
  - _on_node_status_changed(): 全局节点状态变化处理

需要宿主类提供:
  - self.parent_window: 主窗口引用
  - self._sub_panels: dict[node_name -> NodeLogSubPanel]
  - self._panel_layout: QVBoxLayout（用于 insertWidget）
  - 可选: _create_sub_panel(node_name, node_path, status) 工厂方法
"""
from ui.core.polling_manager import polling_manager


class NodePanelSyncMixin:
    """NodeMonitor 面板同步 Mixin"""

    def _create_sub_panel(self, node_name: str, node_path: str, status: str):
        """工厂方法 — 子类覆盖以使用自己的 NodeLogSubPanel 子类"""
        from ui.panels._shared.node_log_sub_panel import BaseNodeLogSubPanel
        return BaseNodeLogSubPanel(node_name, node_path, status)

    def _sync_panels(self):
        """同步子面板列表与画布节点"""
        if not self.parent_window:
            return

        canvas = getattr(self.parent_window, 'canvas', None)

        # 如果画布不存在或画布上没有节点，清空所有子面板
        if not canvas or not hasattr(canvas, 'nodes') or not canvas.nodes:
            for name in list(self._sub_panels.keys()):
                self._remove_sub_panel(name)
            return

        canvas_nodes = set(canvas.nodes.keys())
        current_nodes = set(self._sub_panels.keys())

        # 移除已不在画布上的节点子面板
        removed = current_nodes - canvas_nodes
        for name in removed:
            self._remove_sub_panel(name)

        # 添加新节点子面板
        added = canvas_nodes - current_nodes
        for name in added:
            if hasattr(self.parent_window, 'nodes_data') and name in self.parent_window.nodes_data:
                node_info = self.parent_window.nodes_data[name]
                self._add_sub_panel(name, node_info.get('path', ''),
                                    node_info.get('status', 'stopped'))

        # 更新状态
        for name in self._sub_panels:
            if hasattr(self.parent_window, 'nodes_data') and name in self.parent_window.nodes_data:
                status = self.parent_window.nodes_data[name].get('status', 'stopped')
                self._sub_panels[name].update_status(status)

    def _add_sub_panel(self, node_name: str, node_path: str, status: str):
        """添加一个节点日志子面板"""
        sub = self._create_sub_panel(node_name, node_path, status)
        # 插入到 stretch 之前
        self._panel_layout.insertWidget(self._panel_layout.count() - 1, sub)
        self._sub_panels[node_name] = sub

    def _remove_sub_panel(self, node_name: str):
        """移除节点日志子面板"""
        if node_name in self._sub_panels:
            sub = self._sub_panels[node_name]
            sub.unsubscribe_monitor()
            self._panel_layout.removeWidget(sub)
            sub.deleteLater()
            del self._sub_panels[node_name]

    def _on_node_status_changed(self, node_name: str, new_status: str):
        """处理全局节点状态变化信号"""
        if node_name in self._sub_panels:
            self._sub_panels[node_name].update_status(new_status)
