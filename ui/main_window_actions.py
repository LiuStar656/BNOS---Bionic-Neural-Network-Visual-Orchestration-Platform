"""
BNOS 主窗口业务操作模块

负责主窗口的业务操作方法，包括：
- 项目相关操作
- 节点相关操作
- 面板操作
- 视图操作
"""
import os
from PyQt6.QtWidgets import QMessageBox
from ui.core.logger import logger
from ui.core.i18n import t


class MainWindowActionsMixin:
    """
    主窗口业务操作 Mixin
    
    提供各种业务操作方法，需要与 BNOSMainWindow 配合使用。
    """
    
    def _create_node_list_panel(self, dock=True):
        """创建节点列表面板"""
        from ui.panels.node_list_panel import NodeListPanel
        
        if self.node_list_panel:
            logger.info("节点列表面板已存在")
            return
        
        logger.info("创建节点列表面板, dock=%s", dock)
        self.node_list_panel = NodeListPanel(self, self.app_config)
        
        if dock:
            self.addDockWidget(
                self.DOCK_PANEL_CONFIG["node_list"]["area"],
                self.node_list_panel
            )
        else:
            # 浮动版本
            self.node_list_panel.setWindowFlags(
                self.node_list_panel.windowFlags() | 
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint
            )
            self.node_list_panel.show()
    
    def _create_resource_monitor(self, dock=True):
        """创建资源监测面板"""
        from ui.panels.resource_monitor_panel import ResourceMonitorPanel
        
        if self.resource_monitor:
            logger.info("资源监测面板已存在")
            return
        
        logger.info("创建资源监测面板, dock=%s", dock)
        self.resource_monitor = ResourceMonitorPanel(self)
        
        if dock:
            self.addDockWidget(
                self.DOCK_PANEL_CONFIG["resource_monitor"]["area"],
                self.resource_monitor
            )
    
    def _create_node_monitor(self, floating=False):
        """创建节点监测面板"""
        from ui.panels.node_monitor_panel import NodeMonitorPanel
        
        if hasattr(self, 'node_monitor') and self.node_monitor:
            logger.info("节点监测面板已存在")
            return
        
        logger.info("创建节点监测面板, floating=%s", floating)
        self.node_monitor = NodeMonitorPanel(self)
        
        if floating:
            self.node_monitor.setWindowFlags(
                self.node_monitor.windowFlags() | 
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint
            )
            # 定位到主窗口右侧
            p = self.pos()
            monitor_x = p.x() + self.width() - 440
            monitor_y = p.y() + 40
            self.node_monitor.move(monitor_x, monitor_y)
            self.node_monitor.show()
        else:
            self.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea,
                self.node_monitor
            )
    
    def _create_toast(self, message, type="info", duration=3000):
        """创建Toast通知"""
        from ui.widgets.toast_widget import ToastWidget
        
        toast = ToastWidget(self, message, type, duration)
        toast.show()
        return toast
    
    def _show_message_box(self, title, message, icon=QMessageBox.Icon.Information):
        """显示消息对话框"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec()
    
    def _show_error_message(self, message):
        """显示错误消息"""
        self._show_message_box(t("error"), message, QMessageBox.Icon.Critical)
    
    def _show_warning_message(self, message):
        """显示警告消息"""
        self._show_message_box(t("warning"), message, QMessageBox.Icon.Warning)
    
    def _show_info_message(self, message):
        """显示信息消息"""
        self._show_message_box(t("information"), message, QMessageBox.Icon.Information)
    
    def _open_project_directory(self, project_path):
        """打开项目目录"""
        if os.path.isdir(project_path):
            import subprocess
            try:
                subprocess.Popen(['explorer', project_path])
            except Exception as e:
                logger.error("打开项目目录失败: %s", e)
    
    def _refresh_canvas(self):
        """刷新画布"""
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, 'canvas') and ch.canvas:
                ch.canvas.refresh()
    
    def _clear_canvas(self):
        """清空画布"""
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, 'canvas') and ch.canvas:
                ch.canvas.clear()
    
    def _toggle_fullscreen(self):
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def _reset_layout(self):
        """重置布局"""
        logger.info("重置布局")
        
        # 关闭所有浮动面板
        if hasattr(self, 'node_monitor') and self.node_monitor:
            self.node_monitor.close()
            self.node_monitor = None
        
        # 重置窗口状态
        self.restoreGeometry(b'')
        self.restoreState(b'')
        
        # 重新创建默认面板
        self._create_node_list_panel(dock=True)
        self._create_resource_monitor(dock=True)
        
        # 重置配置
        self.app_config.set("panel_visibility", {})
        self.app_config.save()
    
    def _handle_node_created(self, node_name):
        """处理节点创建事件"""
        logger.info("节点创建: %s", node_name)
        
        # 更新节点列表
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_list(self.nodes_data)
        
        # 更新画布
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, 'canvas') and ch.canvas:
                ch.canvas.sync_all_nodes_display()
    
    def _handle_node_deleted(self, node_name):
        """处理节点删除事件"""
        logger.info("节点删除: %s", node_name)
        
        # 从节点数据中移除
        if node_name in self.nodes_data:
            del self.nodes_data[node_name]
        
        # 更新节点列表
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_list(self.nodes_data)
        
        # 更新画布
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, 'canvas') and ch.canvas:
                ch.canvas.remove_node(node_name)
    
    def _handle_node_status_changed(self, node_name, status):
        """处理节点状态变更事件"""
        logger.info("节点状态变更: %s -> %s", node_name, status)
        
        # 更新节点列表
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_status(node_name, status)
        
        # 更新画布
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, 'canvas') and ch.canvas:
                ch.canvas.update_node_status(node_name, status)
        
        # 更新节点监测面板
        if hasattr(self, 'node_monitor') and self.node_monitor:
            self.node_monitor.update_node_status(node_name, status)
    
    def _handle_project_opened(self, project_path):
        """处理项目打开事件"""
        logger.info("项目打开: %s", project_path)
        self.current_project_path = project_path
        
        # 保存上次打开的项目
        self.app_config.set("last_project", project_path)
        self.app_config.save()
    
    def _handle_project_closed(self):
        """处理项目关闭事件"""
        logger.info("项目关闭")
        self.current_project_path = None
        self.nodes_data = {}
        self.connections = []
        
        # 更新UI
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_list({})
        
        self._clear_canvas()
