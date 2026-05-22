"""
BNOS 主窗口 - 包含完整的界面布局和核心功能
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QFormLayout, QLineEdit, QPushButton, QLabel, QGroupBox,
    QComboBox, QTabWidget, QDialog, QDialogButtonBox, QHeaderView,
    QTableWidget, QTableWidgetItem, QMenu, QGraphicsView, QGraphicsScene,
    QInputDialog, QGraphicsOpacityEffect, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF, QTimer, QThread, QEvent
from PyQt6.QtGui import QIcon, QFont, QPainter, QPen, QColor, QAction, QMouseEvent
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.dark_title_bar import DarkTitleBar
from PyQt6.QtWidgets import QMenuBar as _QMenuBar

from ui.canvas_widget import NodeCanvas
from ui.panels.node_list_panel import NodeListPanel
from ui.dialogs.color_settings_dialog import ColorSettingsDialog
from ui.creators.node_creator_manager import NodeCreatorManager
from ui.menu.menu_manager import MenuManager
from ui.core.toast.toast_notification import ToastNotification
from ui.core.node_process import start_node_process, stop_node_process, resolve_selected_node, check_running_processes, detect_running_nodes
from ui.core.project_manager import project_new, project_open, project_refresh
from ui.core.external_node_manager import mount_node, unmount_node as _unmount_node
from ui.core.window_state_manager import save_state, restore_state
from ui.core.node_creation_worker import start_async_node_creation
from ui.core.node_registry import NodeRegistry
from ui.core.app_config import AppConfig
from ui.core.theme import DARK_QSS
from ui.core.ipc import IPCServer, A_ADD_NODE, A_REMOVE_NODE, A_UPDATE_STATUS
from ui.core.ipc import A_CREATE_EDGE, A_REMOVE_EDGE, A_SYNC_DATA, A_CLEAR_ALL
from ui.core.process_manager import ProcessManager


class BNOSMainWindow(QMainWindow):
    """BNOS主窗口类"""
    
    _RESIZE_MARGIN = 6
    
    def __init__(self):
        super().__init__()
        
        # 应用配置
        self.app_config = AppConfig()
        
        # 项目状态
        self.current_project_path = None
        self.nodes_data = {}  # {node_name: {config, path, process, status}}
        self.connections = []  # [(source_node, target_node)]
        
        # Toast通知队列管理
        self.active_toasts = []
        
        # 初始化节点创建管理器
        self.node_creator = NodeCreatorManager.get_instance()
        
        # 无边框 + 自定义标题栏
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        
        # 初始化UI
        self.init_ui()
        
        # 应用深色主题
        self._apply_dark_theme()
        
        # 恢复窗口状态
        self.restore_window_state()
        
        self.setWindowTitle("BnosGui")
        
        # 进程健康检测定时器（每3秒检查运行中的节点是否仍存活）
        self._health_timer = QTimer(self)
        self._health_timer.setInterval(3000)
        self._health_timer.timeout.connect(self._check_node_health)
        self._health_timer.start()
        
        self.auto_open_last_project()
        
    def init_ui(self):
        """初始化主界面布局"""
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建菜单栏（嵌入标题栏）
        self._inline_menubar = _QMenuBar(self)
        self._inline_menubar.setObjectName("titleBarMenu")
        MenuManager.init_menu(self, self._inline_menubar)
        
        # 标题栏：标题 + 菜单 + 按钮同行
        self._title_bar = DarkTitleBar(self, "BnosGui", self._inline_menubar)
        self._title_bar.minimize_clicked.connect(self.showMinimized)
        self._title_bar.maximize_clicked.connect(self._toggle_maximize)
        self._title_bar.close_clicked.connect(self.close)
        main_layout.addWidget(self._title_bar)
        
        # 画布
        self.canvas = NodeCanvas(self)
        main_layout.addWidget(self.canvas, 1)
        
        # IPC 进程间通信（主进程 = Server）
        self._ipc_server = None
        self._process_manager = ProcessManager(self)
        self._init_ipc()
        
        # 节点列表面板
        self.node_list_panel = NodeListPanel(self)
        self.node_list_panel.setWindowTitle(t("k_node_list"))
        
        panel_width = 280
        panel_height = 500
        window_pos = self.pos()
        panel_x = window_pos.x() + 20
        panel_y = window_pos.y() + 40
        self.node_list_panel.setGeometry(panel_x, panel_y, panel_width, panel_height)
        self.node_list_panel.show()
    
    def moveEvent(self, event):
        """窗口移动事件"""
        super().moveEvent(event)
        off = 40
        
        if hasattr(self, 'node_list_panel') and self.node_list_panel.isVisible():
            p = self.pos()
            self.node_list_panel.move(p.x() + 20, p.y() + off)

        if hasattr(self, 'node_monitor') and self.node_monitor is not None and self.node_monitor.isVisible():
            p = self.pos()
            self.node_monitor.move(p.x() + self.width() - 440, p.y() + off)
        
        if hasattr(self, 'active_toasts'):
            for toast in self.active_toasts:
                toast.update_position()
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        off = 40
        
        if hasattr(self, 'node_list_panel') and self.node_list_panel.isVisible():
            p = self.pos()
            self.node_list_panel.move(p.x() + 20, p.y() + off)

        if hasattr(self, 'node_monitor') and self.node_monitor is not None and self.node_monitor.isVisible():
            p = self.pos()
            self.node_monitor.move(p.x() + self.width() - 440, p.y() + off)
        
        if hasattr(self, 'active_toasts'):
            for toast in self.active_toasts:
                toast.update_position()
    
    def show_toast(self, message, toast_type="info", duration=3000):
        """便捷方法：显示Toast通知（支持堆叠显示）
        
        Args:
            message: 通知文本内容
            toast_type: 类型 (info/success/warning/error)
            duration: 显示时长（毫秒），默认3000
            
        功能特性：
        - 新Toast出现时，旧的自动下移
        - 无数量上限，所有Toast都会显示
        """
        # 先更新所有现有Toast的位置（向下移动一位，为新Toast腾出顶部空间）
        for i, existing_toast in enumerate(self.active_toasts):
            existing_toast.stack_index = i + 1
            existing_toast.update_position()
        
        # 创建新的Toast，设置堆叠索引为0（最顶部）
        stack_index = 0
        toast = ToastNotification(
            message=message,
            parent=self,
            duration=duration,
            toast_type=toast_type,
            stack_index=stack_index
        )
        
        # 添加到活动列表的最前面（最新的在最前）
        self.active_toasts.insert(0, toast)
        
        # 显示Toast
        toast.show_toast()
        
        # 当Toast关闭时，从列表中移除并更新其他Toast位置
        original_close = toast.close
        def custom_close():
            if toast in self.active_toasts:
                self.active_toasts.remove(toast)
                # 更新剩余Toast的位置
                for i, remaining_toast in enumerate(self.active_toasts):
                    remaining_toast.stack_index = i
                    remaining_toast.update_position()
            original_close()
        
        toast.close = custom_close
    
    def toggle_node_list_panel(self, checked):
        """切换节点列表面板的显示/隐藏"""
        if checked:
            self.node_list_panel.show()
            self.node_list_panel.raise_()
            self.node_list_panel.activateWindow()
        else:
            self.node_list_panel.hide()

    def show_node_monitor(self):
        """打开节点监测面板"""
        from ui.panels.node_monitor import NodeMonitor
        if not hasattr(self, 'node_monitor') or self.node_monitor is None:
            self.node_monitor = NodeMonitor(self)
            window_pos = self.pos()
            monitor_x = window_pos.x() + self.width() - 440
            monitor_y = window_pos.y() + 40
            self.node_monitor.move(monitor_x, monitor_y)
        self.node_monitor.show()
        self.node_monitor.raise_()

    def open_color_settings(self):
        """打开颜色设置对话框"""
        dialog = ColorSettingsDialog(self.canvas, self)
        dialog.exec()
    
    def new_project(self):
        project_new(self)
        
    def open_project(self):
        project_open(self)
        
    def update_node_status(self, node_name, status):
        """更新节点状态并同步UI"""
        if node_name in self.nodes_data:
            self.nodes_data[node_name]['status'] = status
            
            # 同步更新画布上的节点显示
            self.canvas.sync_node_display(node_name)
            
            # 更新节点列表面板
            self.node_list_panel.update_node_list(self.nodes_data)
        
    def refresh_nodes(self):
        project_refresh(self)
        
    def mount_external_node(self):
        mount_node(self)

    def unmount_external_node(self, node_name: str):
        _unmount_node(self, node_name)

    def create_new_node(self):
        """创建新节点（默认Python）"""
        self.create_new_node_with_language("Python")
    
    def create_new_node_with_language(self, language):
        """使用指定语言创建新节点（供菜单调用）"""
        if not self.current_project_path:
            self.show_toast(t("k_project_no_project"), "warning")
            return

        # 仅 Python 和 Rust 可用
        if language not in ("Python", "Rust"):
            self.show_toast(t("k_node_lang_unsupported").replace("{lang}", language), "warning")
            return

        prompt = t("k_node_enter_name").replace("{lang}", language)
        node_name, ok = QInputDialog.getText(
            self, t("k_node_create"), prompt,
            QLineEdit.EchoMode.Normal
        )
        
        if not ok or not node_name:
            return
        
        lang_map = {"Python": "python", "Rust": "rust"}
        lang_key = lang_map.get(language, language.lower())
        
        if not self.node_creator.has_creator(lang_key):
            self.show_toast(t("k_node_lang_unsupported").replace("{lang}", language), "warning")
            return
        
        self._start_async_node_creation(node_name, lang_key, language)
    
    def _start_async_node_creation(self, node_name, lang_key, display_language):
        start_async_node_creation(self, node_name, lang_key, display_language)

    def start_selected_node(self):
        """启动选中的节点"""
        selected = resolve_selected_node(self)
        if not selected:
            self.show_toast(t("k_node_select_first"), "warning")
            return
        self.start_selected_node_by_name(selected)
    
    def start_selected_node_by_name(self, node_name):
        """按名称启动节点"""
        if node_name not in self.nodes_data:
            return
        node_info = self.nodes_data[node_name]
        if node_info['status'] == 'running':
            self.show_toast(f"节点 {node_name} 已在运行中", "info")
            return
        
        success, err = start_node_process(node_info)
        if success:
            self.node_list_panel.update_node_status(node_name, 'running')
            self.canvas.update_node_status(node_name, 'running')
            self.show_toast(f"节点 {node_name} 已启动", "success")
        else:
            QMessageBox.critical(self, t("k_title_error"), f"启动节点失败: {err}")
    
    def stop_selected_node(self):
        """停止选中的节点"""
        selected = resolve_selected_node(self)
        if not selected:
            self.show_toast(t("k_node_select_first"), "warning")
            return
        self.stop_selected_node_by_name(selected)
    
    def stop_selected_node_by_name(self, node_name):
        """按名称停止节点"""
        if node_name not in self.nodes_data:
            return
        node_info = self.nodes_data[node_name]
        if node_info['status'] == 'stopped':
            self.show_toast(f"节点 {node_name} 未在运行", "info")
            return
        
        stop_node_process(node_info)
        self.node_list_panel.update_node_status(node_name, 'stopped')
        self.canvas.update_node_status(node_name, 'stopped')
        self.show_toast(f"节点 {node_name} 已停止", "success")

    def _check_node_health(self):
        """定时检测运行中节点的进程是否仍存活"""
        dead = check_running_processes(self.nodes_data)
        for name, code in dead:
            self.node_list_panel.update_node_status(name, 'stopped')
            self.canvas.update_node_status(name, 'stopped')
            self.show_toast(f"节点 {name} 已意外退出 (code: {code})", "warning")

    def clear_connections(self):
        """清空所有连线"""
        reply = QMessageBox.question(
            self, t("k_title_confirm"), 
            t("k_confirm_clear_connections"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 清空所有下游节点的 listen_upper_file
        for node_name, node_info in self.nodes_data.items():
            config = node_info['config']
            config['listen_upper_file'] = ""
            
            config_path = os.path.join(node_info['path'], "config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 清空画布连线
        self.canvas.clear_edges()
        
        self.show_toast(t("k_canvas_cleared"), "success")

    def closeEvent(self, event):
        """窗口关闭事件，保存所有状态"""
        logger.info("开始关闭窗口检测...")
        logger.info("   当前项目: %s", self.current_project_path)
        logger.info("   节点总数: %d", len(self.nodes_data))
        
        # 等待节点创建线程完成（如果正在运行）
        if hasattr(self, 'node_creation_worker') and self.node_creation_worker.isRunning():
            logger.info("等待节点创建线程完成...")
            self.node_creation_worker.wait(5000)
            if self.node_creation_worker.isRunning():
                logger.warning("节点创建线程超时，强制终止")
                self.node_creation_worker.terminate()
        
        # 检查是否有运行中的节点
        running_nodes = []
        for node_name, node_info in self.nodes_data.items():
            status = node_info.get('status', 'unknown')
            process = node_info.get('process', None)
            logger.debug("节点 %s: status=%s, process=%s", node_name, status, '存在' if process else 'None')
            
            if status == 'running' and process:
                running_nodes.append(node_name)
        
        logger.info("检测到 %d 个运行中的节点: %s", len(running_nodes), running_nodes)
        
        # 如果有运行中的节点，提示用户
        if running_nodes:
            nodes_list = "\n".join([f"• {name}" for name in running_nodes[:10]])  # 最多显示10个
            if len(running_nodes) > 10:
                nodes_list += f"\n... 还有 {len(running_nodes) - 10} 个节点"
            
            reply = QMessageBox.question(
                self, 
                t("k_title_detect_running"),
                f"以下 {len(running_nodes)} 个节点正在运行：\n\n{nodes_list}\n\n请选择操作：\n• 是：强制停止所有节点并关闭\n• 否：节点继续在后台运行，关闭窗口\n• 取消：返回程序，不关闭窗口",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes  # 默认选择"是"
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 用户选择关闭所有进程
                logger.info("正在关闭 %d 个运行中的节点...", len(running_nodes))
                self._force_stop_all_nodes(running_nodes)
                self.show_toast(f"已关闭 {len(running_nodes)} 个节点", "success")
                # 继续执行后续的保存和关闭逻辑
            elif reply == QMessageBox.StandardButton.No:
                # 用户选择不关闭，让进程继续运行
                logger.info("%d 个节点将继续在后台运行", len(running_nodes))
                self.show_toast(f"{len(running_nodes)} 个节点将在后台继续运行", "info")
                # 继续执行后续的保存和关闭逻辑
            else:
                # 用户选择取消，中止关闭操作
                logger.info("用户取消了关闭操作")
                event.ignore()  # 忽略关闭事件，保持窗口打开
                return
        
        # 保存当前项目布局
        if self.current_project_path:
            self.canvas.save_layout(self.current_project_path)
        
        # 保存应用配置
        self.save_window_state()
        self.app_config.set("last_project", self.current_project_path)
        self.app_config.save()
        
        # 停止 IPC 和子进程
        if self._process_manager:
            self._process_manager.stop_all()
        if self._ipc_server:
            self._ipc_server.stop()

        logger.info("窗口关闭流程完成")
        event.accept()
    
    def _force_stop_all_nodes(self, node_names):
        """强制停止所有指定节点进程"""
        for node_name in node_names:
            if node_name in self.nodes_data:
                stop_node_process(self.nodes_data[node_name])
                logger.info("节点 %s 已停止", node_name)
        self.node_list_panel.update_node_list(self.nodes_data)
        self.canvas.sync_all_nodes_display()
    
    def save_window_state(self):
        save_state(self)

    def restore_window_state(self):
        restore_state(self)
    
    def auto_open_last_project(self):
        """自动打开最后的项目 - 只加载数据，不自动添加节点到画布"""
        last_project = self.app_config.get("last_project")
        if last_project and os.path.exists(last_project):
            nodes_dir = os.path.join(last_project, "nodes")
            if os.path.exists(nodes_dir):
                self.current_project_path = last_project
                
                logger.info("自动打开项目: %s", last_project)
                
                # 1. 刷新节点列表（加载所有节点数据）
                self.refresh_nodes()
                
                # 2. 加载画布布局（包含节点位置、连线关系、视图状态的完整恢复）
                self.canvas.load_layout(last_project)
    
    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        if hasattr(self, '_title_bar'):
            self._title_bar.set_maximized_state(self.isMaximized())
    
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, '_title_bar'):
            self._title_bar.set_maximized_state(self.isMaximized())
    
    def setWindowTitle(self, title: str):
        super().setWindowTitle(title)
        if hasattr(self, '_title_bar'):
            self._title_bar.set_title(title)
    
    def _get_resize_region(self, pos):
        x, y = pos.x(), pos.y()
        w, h, m = self.width(), self.height(), self._RESIZE_MARGIN
        t, b, l, r = y <= m, y >= h - m, x <= m, x >= w - m
        if t and l: return Qt.CursorShape.SizeFDiagCursor, "top-left"
        if t and r: return Qt.CursorShape.SizeBDiagCursor, "top-right"
        if b and l: return Qt.CursorShape.SizeBDiagCursor, "bottom-left"
        if b and r: return Qt.CursorShape.SizeFDiagCursor, "bottom-right"
        if t:      return Qt.CursorShape.SizeVerCursor, "top"
        if b:      return Qt.CursorShape.SizeVerCursor, "bottom"
        if l:      return Qt.CursorShape.SizeHorCursor, "left"
        if r:      return Qt.CursorShape.SizeHorCursor, "right"
        return None, None
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            _, direction = self._get_resize_region(event.pos())
            if direction and self.windowHandle():
                edges = {
                    "top-left": Qt.Edge.TopEdge | Qt.Edge.LeftEdge,
                    "top-right": Qt.Edge.TopEdge | Qt.Edge.RightEdge,
                    "bottom-left": Qt.Edge.BottomEdge | Qt.Edge.LeftEdge,
                    "bottom-right": Qt.Edge.BottomEdge | Qt.Edge.RightEdge,
                    "top": Qt.Edge.TopEdge, "bottom": Qt.Edge.BottomEdge,
                    "left": Qt.Edge.LeftEdge, "right": Qt.Edge.RightEdge,
                }
                self.windowHandle().startSystemResize(edges.get(direction))
                return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if not self.isMaximized():
            cursor, _ = self._get_resize_region(event.pos())
            if cursor: self.setCursor(cursor)
            else: self.unsetCursor()
        super().mouseMoveEvent(event)
    
    # ── 进程间通信 (IPC) ──

    def _init_ipc(self):
        """初始化 IPC Server，接收子进程连接"""
        self._ipc_server = IPCServer(self)
        if not self._ipc_server.start():
            logger.warning("IPC Server 启动失败，进程隔离不可用")
            return
        self._ipc_server.client_connected.connect(self._on_ipc_client_connected)
        self._ipc_server.message_received.connect(self._on_ipc_message)
        self._ipc_server.client_disconnected.connect(self._on_ipc_client_disconnected)
        logger.info("进程间通信已就绪")

    def _start_canvas_process(self):
        """启动画布子进程（可选，默认使用内嵌画布）"""
        if not self._ipc_server:
            return
        self._process_manager.register("canvas", "ui/canvas/canvas_process.py")
        proc = self._process_manager.get("canvas")
        proc.crashed.connect(self._on_canvas_crashed)
        proc.start()

    def _start_panel_process(self):
        """启动面板子进程（可选，默认使用内嵌面板）"""
        if not self._ipc_server:
            return
        self._process_manager.register("panel", "ui/panels/panel_process.py")
        proc = self._process_manager.get("panel")
        proc.crashed.connect(lambda pid: logger.warning("面板进程 %s 崩溃，自动重启", pid))
        proc.start()

    def _on_canvas_crashed(self, pid):
        """画布崩溃 → 自动重启"""
        self.show_toast("画布进程已崩溃，正在重启...", "warning")
        logger.warning("画布子进程 %s 崩溃，准备重启", pid)

    def _start_core_process(self):
        """启动核心业务子进程（可选，默认在主进程跑）"""
        if not self._ipc_server:
            return
        self._process_manager.register("core", "ui/core/core_process.py")
        proc = self._process_manager.get("core")
        proc.crashed.connect(lambda pid: logger.warning("核心进程 %s 崩溃，自动重启", pid))
        proc.start()

    def _on_ipc_client_connected(self, client_id):
        logger.info("IPC 客户端已连接: %s", client_id)

    def _on_ipc_client_disconnected(self, client_id):
        logger.info("IPC 客户端已断开: %s", client_id)

    def _on_ipc_message(self, client_id, msg):
        """处理子进程发来的事件"""
        action = msg.get("action")
        params = msg.get("params", {})
        logger.debug("IPC 收到: %s ← %s", action, client_id)
        # TODO: 根据 action 分发事件

    # ── 画布命令代理（嵌入/远程通用）──

    def _canvas_ipc_sync(self):
        """同步 nodes_data 到画布（嵌入式绕过IPC直接用canvas）"""
        if self.canvas and self.canvas.parent_window:
            # 嵌入式模式
            self.canvas.sync_all_nodes_display()
        elif self._ipc_server:
            self._ipc_server.broadcast(A_SYNC_DATA, {"nodes_data": self.nodes_data})

    def _canvas_ipc_update_status(self, node_name, status):
        if self.canvas and self.canvas.parent_window:
            self.canvas.update_node_status(node_name, status)
        elif self._ipc_server:
            self._ipc_server.broadcast(A_UPDATE_STATUS, {"node_name": node_name, "status": status})

    def _restart_application(self):
        """重启应用程序"""
        import sys, os, subprocess
        logger.info("正在重启应用...")
        self._process_manager.stop_all()
        if self._ipc_server:
            self._ipc_server.stop()
        QApplication.quit()
        # 新进程启动（与原参数一致）
        subprocess.Popen([sys.executable, *sys.argv], cwd=os.getcwd())
        sys.exit(0)

    def _apply_dark_theme(self):
        self.setStyleSheet(DARK_QSS)
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, t("k_title_about"), 
            "BNOS - Bionic Neural Network Program Operating System\n\n"
            "版本: 1.0.0\n"
            "仿生神经网络程序操作系统\n\n"
            "一款基于 PyQt6 的纯桌面端可视化节点编排平台。\n\n"
            "核心特性:\n"
            "• 项目管理：仿 VSCode 模式，打开文件夹即项目\n"
            "• 可视化编排：无限平移画布，拖拽节点，智能连线\n"
            "• 多语言支持：Python、Node.js、Go、Java、C++、Rust、Shell\n"
            "• 环境隔离：每个节点拥有独立虚拟环境\n"
            "• 配置编辑：图形化编辑 config.json\n"
            "• 实时监控：状态指示灯，实时日志查看\n"
            "• 状态持久化：自动保存布局，重启完整恢复"
        )
