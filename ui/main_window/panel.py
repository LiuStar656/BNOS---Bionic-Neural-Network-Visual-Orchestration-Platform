"""
BNOS 主窗口面板管理模块

负责所有面板的创建、显示、关闭和位置持久化管理，包括：
- 节点列表面板（浮动版/Dock版）
- 节点监测面板（浮动版/Dock版）
- 资源监测面板（浮动版/Dock版）
- 面板位置和可见性状态管理
"""
from PySide6.QtCore import Qt
from ui.core.i18n import t
from ui.core.logger import logger


class MainWindowPanelMixin:
    """面板管理Mixin - 处理所有面板的创建和状态管理"""

    def toggle_terminal(self):
        """切换终端 Dock 的显示/隐藏"""
        if hasattr(self, '_canvas_host') and hasattr(self._canvas_host, 'toggle_terminal'):
            self._canvas_host.toggle_terminal()

    def _refresh_panels(self):
        """刷新所有面板以适配当前画布"""
        if hasattr(self, 'node_list_panel') and self.node_list_panel and hasattr(self, 'nodes_data'):
            self.node_list_panel.update_node_list(self.nodes_data)

        if hasattr(self, 'node_list_floating') and self.node_list_floating and hasattr(self, 'nodes_data'):
            self.node_list_floating.update_node_list(self.nodes_data)

        if hasattr(self, 'node_list_dock') and self.node_list_dock and hasattr(self, 'nodes_data'):
            self.node_list_dock.update_node_list(self.nodes_data)

    def toggle_node_list_panel(self, checked):
        """切换节点列表面板（Dock版）- 停靠到左侧"""
        if checked:
            if self.node_list_panel is None:
                from ui.panels.node_list_dock import NodeListDockPanel
                self.node_list_panel = NodeListDockPanel(self)
            # 总是刷新项目路径和节点数据（无论面板是新建还是已存在）
            if self.node_list_panel is not None:
                if hasattr(self, 'current_project_path') and self.current_project_path:
                    self.node_list_panel.set_project_path(self.current_project_path)
                if hasattr(self, 'nodes_data') and self.nodes_data:
                    self.node_list_panel.update_node_list(self.nodes_data)
            self._dock_manager.add_panel_to_dock(self.node_list_panel, t("k_node_list_dock"), edge='left')
            self._save_panel_visibility_state('node_list_dock', True)
        else:
            if self.node_list_panel is not None:
                dock = self._dock_manager.get_dock_by_title(t("k_node_list_dock"))
                if dock:
                    dock.close()
                else:
                    self.node_list_panel = None
            self._save_panel_visibility_state('node_list_dock', False)

    def show_node_list_floating(self):
        """打开节点列表面板（浮动版）- 带位置持久化"""
        from ui.panels.node_list_panel import NodeListPanel
        if not hasattr(self, 'node_list_floating') or self.node_list_floating is None:
            self.node_list_floating = NodeListPanel(self)
            pos = self.app_config.get('panel_positions', {}).get('node_list_floating', {'x': 10, 'y': 100})
            self.node_list_floating.move(pos['x'], pos['y'])
            self.node_list_floating.closed.connect(self._on_node_list_floating_closed)
            if hasattr(self, 'nodes_data') and self.nodes_data:
                self.node_list_floating.update_node_list(self.nodes_data)
        self.node_list_floating.show()
        self.node_list_floating.raise_()
        self._save_panel_visibility_state('node_list_floating', True)

    def show_node_monitor(self):
        """打开节点监测面板（浮动版）- 带位置持久化"""
        from ui.panels.node_monitor import NodeMonitor
        if not hasattr(self, 'node_monitor') or self.node_monitor is None:
            self.node_monitor = NodeMonitor(self)
            pos = self.app_config.get('panel_positions', {}).get('node_monitor_floating', {'x': 10, 'y': 100})
            self.node_monitor.move(pos['x'], pos['y'])
            self.node_monitor.closed.connect(self._on_node_monitor_closed)
        self.node_monitor.show()
        self.node_monitor.raise_()
        self._save_panel_visibility_state('node_monitor_floating', True)

    def show_node_monitor_dock(self):
        """打开节点监测面板（Dock版）- 停靠到右侧"""
        if not hasattr(self, 'node_monitor_dock') or self.node_monitor_dock is None:
            from ui.panels.node_monitor_dock import NodeMonitorDock
            self.node_monitor_dock = NodeMonitorDock(self)
        self._dock_manager.add_panel_to_dock(self.node_monitor_dock, t("k_node_monitor_dock"), edge='right')
        self._save_panel_visibility_state('node_monitor_dock', True)

    def show_resource_monitor(self):
        """打开资源监测面板（浮动版）- 带位置持久化"""
        from ui.panels.resource_monitor import ResourceMonitor
        if not hasattr(self, 'resource_monitor_floating') or self.resource_monitor_floating is None:
            self.resource_monitor_floating = ResourceMonitor(self)
            pos = self.app_config.get('panel_positions', {}).get('resource_monitor_floating', {'x': 10, 'y': 100})
            self.resource_monitor_floating.move(pos['x'], pos['y'])
            self.resource_monitor_floating.closed.connect(self._on_resource_monitor_floating_closed)
            self._connect_existing_nodes_to_resource_monitor(self.resource_monitor_floating)
        self.resource_monitor_floating.show()
        self.resource_monitor_floating.raise_()
        self._save_panel_visibility_state('resource_monitor_floating', True)

    def show_resource_monitor_dock(self):
        """打开资源监测面板（Dock版）- 停靠到左侧"""
        if self.resource_monitor is None:
            from ui.panels.resource_monitor_dock import ResourceMonitorDock
            self.resource_monitor = ResourceMonitorDock(self)
            if hasattr(self.resource_monitor, 'node_state_updated'):
                self._connect_existing_nodes_to_resource_monitor(self.resource_monitor)
        self._dock_manager.add_panel_to_dock(self.resource_monitor, t("k_resource_monitor_dock"), edge='left')
        self._save_panel_visibility_state('resource_monitor_dock', True)

    def _connect_existing_nodes_to_resource_monitor(self, resource_monitor_panel):
        """确保已存在的节点能连接到资源监测面板的信号"""
        if not hasattr(self, 'canvas') or not self.canvas:
            return
        for node_name, node_item in self.canvas.nodes.items():
            if hasattr(node_item, '_connect_resource_monitor_signals'):
                node_item._connect_resource_monitor_signals()

    def _save_panel_position(self, panel_name, panel_widget):
        """保存面板位置到配置"""
        pos = panel_widget.pos()
        positions = self.app_config.get('panel_positions', {})
        positions[panel_name] = {'x': pos.x(), 'y': pos.y()}
        self.app_config.set('panel_positions', positions)
        self.app_config.save()

    def _save_panel_visibility_state(self, panel_key, visible):
        """保存单个面板的可见性状态"""
        visibility = self.app_config.get('panel_visibility', {})
        visibility[panel_key] = visible
        if panel_key.endswith('_dock'):
            base_key = panel_key[:-5]
            visibility[base_key] = visibility.get(base_key, False) or visible
        elif panel_key.endswith('_floating'):
            base_key = panel_key[:-9]
            visibility[base_key] = visibility.get(base_key, False) or visible
        self.app_config.set('panel_visibility', visibility)
        self.app_config.save()

    def _on_node_list_floating_closed(self):
        """浮动节点列表面板关闭处理"""
        self._save_panel_position('node_list_floating', self.node_list_floating)
        self._save_panel_visibility_state('node_list_floating', False)

    def _on_node_monitor_closed(self):
        """节点监测面板关闭处理"""
        self._save_panel_position('node_monitor_floating', self.node_monitor)
        self._save_panel_visibility_state('node_monitor_floating', False)

    def _on_resource_monitor_floating_closed(self):
        """浮动资源监测面板关闭处理"""
        self._save_panel_position('resource_monitor_floating', self.resource_monitor_floating)
        self._save_panel_visibility_state('resource_monitor_floating', False)

    def _on_dock_panel_closed(self, widget):
        """Dock面板关闭处理"""
        if self.node_list_panel == widget:
            self.node_list_panel = None
            self._save_panel_visibility_state('node_list_dock', False)
        elif self.resource_monitor == widget:
            self.resource_monitor = None
            self._save_panel_visibility_state('resource_monitor_dock', False)
        elif self.node_monitor_dock == widget:
            self.node_monitor_dock = None
            self._save_panel_visibility_state('node_monitor_dock', False)
        elif self.history_panel == widget:
            self.history_panel = None
            self._save_panel_visibility_state('history_dock', False)

    def show_history_panel(self):
        """打开历史记录面板（Dock版）- 停靠到右侧"""
        if not hasattr(self, 'history_panel') or self.history_panel is None:
            from ui.panels.history_panel import HistoryPanelWidget
            self.history_panel = HistoryPanelWidget(self)
        self._dock_manager.add_panel_to_dock(self.history_panel, t("k_view_history_panel"), edge='right')
        self._save_panel_visibility_state('history_dock', True)

    def show_performance_panel(self):
        """打开性能分析面板（浮动版）"""
        from ui.panels.performance_panel import PerformancePanel
        if not hasattr(self, 'performance_panel') or self.performance_panel is None:
            self.performance_panel = PerformancePanel(self)
            pos = self.app_config.get('panel_positions', {}).get('performance_panel', {'x': 100, 'y': 100})
            self.performance_panel.move(pos['x'], pos['y'])
            self.performance_panel.closed.connect(self._on_performance_panel_closed)
        self.performance_panel.show()
        self.performance_panel.raise_()
        self._save_panel_visibility_state('performance_panel', True)

    def show_debug_panel(self):
        """打开调试面板（浮动版）"""
        from ui.panels.debug_panel import DebugPanel
        if not hasattr(self, 'debug_panel') or self.debug_panel is None:
            self.debug_panel = DebugPanel(self)
            pos = self.app_config.get('panel_positions', {}).get('debug_panel', {'x': 200, 'y': 200})
            self.debug_panel.move(pos['x'], pos['y'])
            self.debug_panel.closed.connect(self._on_debug_panel_closed)
        self.debug_panel.show()
        self.debug_panel.raise_()
        self._save_panel_visibility_state('debug_panel', True)

    def show_template_selector(self):
        """打开预设节点库"""
        from ui.dialogs.preset_library_dialog import PresetLibraryDialog
        dialog = PresetLibraryDialog(self)
        dialog.show()

    def _add_node_to_canvas(self, node_name):
        """将节点添加到画布"""
        canvas_host = self._get_canvas_host()
        if canvas_host and hasattr(canvas_host, 'add_node_to_canvas'):
            canvas_host.add_node_to_canvas(node_name)
        elif hasattr(self, 'canvas') and hasattr(self.canvas, 'add_node_to_canvas'):
            self.canvas.add_node_to_canvas(node_name)

    def _get_canvas_host(self):
        """获取画布主机"""
        if hasattr(self, 'canvas_host'):
            return self.canvas_host
        if hasattr(self, 'canvas') and hasattr(self.canvas, 'parent'):
            return self.canvas.parent()
        return None

    def _on_performance_panel_closed(self):
        """性能分析面板关闭处理"""
        self._save_panel_position('performance_panel', self.performance_panel)
        self._save_panel_visibility_state('performance_panel', False)

    def _on_debug_panel_closed(self):
        """调试面板关闭处理"""
        self._save_panel_position('debug_panel', self.debug_panel)
        self._save_panel_visibility_state('debug_panel', False)