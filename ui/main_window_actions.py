"""
BNOS 主窗口业务操作模块

负责主窗口的业务操作方法，包括：
- 项目相关操作
- 消息对话框
- 视图操作
"""
import os
import subprocess
import sys
from typing import Optional
from PyQt6.QtWidgets import QMessageBox
from ui.core.logger import logger
from ui.core.i18n import t


class MainWindowActionsMixin:
    """
    主窗口业务操作 Mixin
    
    提供各种业务操作方法，需要与 BNOSMainWindow 配合使用。
    """
    
    def _show_message_box(self, title: str, message: str, 
                          icon: QMessageBox.Icon = QMessageBox.Icon.Information) -> None:
        """显示消息对话框"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon)
        msg_box.exec()
    
    def _show_error_message(self, message: str) -> None:
        """显示错误消息"""
        self._show_message_box(t("error"), message, QMessageBox.Icon.Critical)
    
    def _show_warning_message(self, message: str) -> None:
        """显示警告消息"""
        self._show_message_box(t("warning"), message, QMessageBox.Icon.Warning)
    
    def _show_info_message(self, message: str) -> None:
        """显示信息消息"""
        self._show_message_box(t("information"), message, QMessageBox.Icon.Information)
    
    def _open_project_directory(self, project_path: str) -> None:
        """打开项目目录（跨平台）"""
        if not project_path or not os.path.isdir(project_path):
            logger.warning("无效的项目路径: %s", project_path)
            return
        
        try:
            if sys.platform == 'win32':
                subprocess.Popen(['explorer', project_path])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', project_path])
            else:
                subprocess.Popen(['xdg-open', project_path])
        except Exception as e:
            logger.error("打开项目目录失败: %s", e)
            self._show_error_message(t("_k_open_dir_fail").format(path=project_path))
    
    def _get_canvas(self):
        """获取画布实例（简化重复检查）"""
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, 'canvas') and ch.canvas:
                return ch.canvas
        return None
    
    def _refresh_canvas(self) -> None:
        """刷新画布"""
        canvas = self._get_canvas()
        if canvas:
            canvas.refresh()
    
    def _clear_canvas(self) -> None:
        """清空画布"""
        canvas = self._get_canvas()
        if canvas:
            canvas.clear()
    
    def _toggle_fullscreen(self) -> None:
        """切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
    
    def _reset_layout(self) -> None:
        """重置布局"""
        logger.info("重置布局")
        
        # 关闭所有浮动面板
        if hasattr(self, 'node_monitor') and self.node_monitor:
            self.node_monitor.close()
            self.node_monitor = None
        
        # 重置窗口状态
        self.restoreGeometry(b'')
        self.restoreState(b'')
        
        # 重置配置
        self.app_config.set("panel_visibility", {})
        self.app_config.save()
    
    def _handle_node_created(self, node_name: str) -> None:
        """处理节点创建事件"""
        logger.info("节点创建: %s", node_name)
        
        # 更新节点列表
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_list(self.nodes_data)
        
        # 更新画布
        canvas = self._get_canvas()
        if canvas:
            canvas.sync_all_nodes_display()
    
    def _handle_node_deleted(self, node_name: str) -> None:
        """处理节点删除事件"""
        logger.info("节点删除: %s", node_name)
        
        # 从节点数据中移除
        if node_name in self.nodes_data:
            del self.nodes_data[node_name]
        
        # 更新节点列表
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_list(self.nodes_data)
        
        # 更新画布
        canvas = self._get_canvas()
        if canvas:
            canvas.remove_node(node_name)
    
    def _handle_node_status_changed(self, node_name: str, status: str) -> None:
        """处理节点状态变更事件"""
        logger.info("节点状态变更: %s -> %s", node_name, status)
        
        # 更新节点列表
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_status(node_name, status)
        
        # 更新画布
        canvas = self._get_canvas()
        if canvas:
            canvas.update_node_status(node_name, status)
        
        # 更新节点监测面板
        if hasattr(self, 'node_monitor') and self.node_monitor:
            self.node_monitor.update_node_status(node_name, status)
    
    def _handle_project_opened(self, project_path: Optional[str]) -> None:
        """处理项目打开事件"""
        if not project_path:
            logger.warning("项目路径为空")
            return
        
        logger.info("项目打开: %s", project_path)
        self.current_project_path = project_path
        
        # 保存上次打开的项目
        self.app_config.set("last_project", project_path)
        self.app_config.save()
    
    def _handle_project_closed(self) -> None:
        """处理项目关闭事件"""
        logger.info("项目关闭")
        self.current_project_path = None
        self.nodes_data = {}
        self.connections = []
        
        # 更新UI
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_list({})
        
        self._clear_canvas()