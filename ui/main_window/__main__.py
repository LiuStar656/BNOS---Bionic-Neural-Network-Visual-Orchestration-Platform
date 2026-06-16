"""
BNOS 主窗口 - 包含完整的界面布局和核心功能
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QTreeWidget, QTreeWidgetItem, QTextEdit,
    QFormLayout, QLineEdit, QPushButton, QLabel, QGroupBox,
    QComboBox, QDialog, QDialogButtonBox, QHeaderView,
    QTableWidget, QTableWidgetItem, QMenu, QGraphicsView, QGraphicsScene,
    QInputDialog, QGraphicsOpacityEffect, QApplication
)
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QTimer, QThread, QEvent
from PySide6.QtGui import QIcon, QFont, QPainter, QPen, QColor, QAction, QMouseEvent
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.dark_title_bar import DarkTitleBar
from ui.core.utils.dialog_utils import themed_message
from PySide6.QtWidgets import QMenuBar as _QMenuBar

from ui.canvas_widget import NodeCanvas
from ui.dialogs.color_settings_dialog import ColorSettingsDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.creators.node_creator_manager import NodeCreatorManager
from ui.menu.menu_manager import MenuManager
from ui.core.toast.toast_notification import ToastNotification
from ui.core.toast.toast_queue_manager import ToastQueueManager
from ui.core.node_process import start_node_process, stop_node_process, resolve_selected_node, check_running_processes, detect_running_nodes
from ui.core.polling_manager import polling_manager
from ui.core.project_manager import project_new, project_open, project_refresh, _canvas_call
from ui.core.external_node_manager import mount_node, unmount_node as _unmount_node
from ui.core.window_state_manager import save_state, restore_state
from ui.core.node_creation_worker import start_async_node_creation
from ui.core.node_registry import NodeRegistry
from ui.core.app_config import AppConfig
from ui.core.theme import DARK_QSS
from ui.core.process_manager import ProcessManager
from ui.core.canvas_host import CanvasHost

# ===== 解耦基础设施（Step 1-7） =====
from ui.core.event_bus import event_bus
from ui.core.di import container, IConfig
from ui.core.panel_manager import PanelManager
from ui.core.node_control_service import node_control_service, NodeStatus
from ui.core.shutdown_orchestrator import ShutdownOrchestrator
from ui.main_window.state import MainWindowStateMixin
from ui.main_window.lifecycle import MainWindowLifecycleMixin
from ui.main_window.actions import MainWindowActionsMixin
from ui.core.actions import ActionFactory
from ui.main_window.panel import MainWindowPanelMixin
from ui.main_window.ipc import MainWindowIPCMixin
from ui.main_window.node import MainWindowNodeControlMixin
from ui.main_window.interaction import MainWindowInteractionMixin


class BNOSMainWindow(QMainWindow, MainWindowStateMixin, MainWindowLifecycleMixin, MainWindowActionsMixin, MainWindowPanelMixin, MainWindowIPCMixin, MainWindowNodeControlMixin, MainWindowInteractionMixin):
    """BNOS主窗口类"""
    
    _RESIZE_MARGIN = 6
    CANVAS_PROCESS_MODE = False  # 【调试中】画布进程隔离+窗口对齐同步
    
    # PS式布局配置
    ALLOWED_PANEL_AREAS = Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
    
    def __init__(self):
        super().__init__()
        
        # 应用配置
        self.app_config = AppConfig()
        from ui.core.shortcut_manager import ShortcutManager
        self.shortcut_mgr = ShortcutManager(self.app_config)
        
        # 项目状态
        self.current_project_path = None
        self.nodes_data = {}  # {node_name: {config, path, process, status}}
        self.connections = []  # [(source_node, target_node)]
        
        # Toast通知队列管理
        self.toast_manager = ToastQueueManager.get_instance()
        self.toast_manager.initialize(self, self._create_toast)
        
        # 节点启动线程跟踪
        self._node_start_workers = []
        
        # 初始化节点创建管理器
        self.node_creator = NodeCreatorManager.get_instance()
        
        # 无边框 + 自定义标题栏
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        
        # 限制主窗口大小（保留最小尺寸，移除最大尺寸限制支持高分辨率显示器）
        self.setMinimumSize(1024, 768)  # 最小尺寸：1024x768
        
        # 初始化UI
        self.init_ui()
        
        # 应用深色主题
        self._apply_dark_theme()
        
        self.setWindowTitle("BnosConsole")
        
        # 统一轮询管理器（替代原来的 SystemMonitor 和 GlobalDetector）
        polling_manager.node_status_changed.connect(self._on_node_status_changed)
        polling_manager.global_log_changed.connect(self._on_global_log_changed)
        polling_manager.global_config_changed.connect(self._on_global_config_changed)
        polling_manager.app_state_changed.connect(self._on_app_state_changed)
        polling_manager.start(self.nodes_data)

        # ===== 解耦服务初始化（Step 3-5） =====
        # 面板管理器 - 统一管理所有面板的创建/显示/持久化
        self.panel_manager = PanelManager(
            self,
            Path(os.getcwd()) / ".bnos" / "app_config.json"
        )

        # IDE 扫描器 - 自动检测并缓存 VSCode/Trae IDE 路径
        from ui.core.ide_scanner import ide_scanner
        ide_scanner._app_config = self.app_config

        # 节点控制服务 - 注册所有项目节点
        for node_name, node_data in self.nodes_data.items():
            node_control_service.register_node(
                node_name,
                node_data.get("path", "")
            )
        node_control_service.subscribe(self._on_node_service_status)

        # 关闭序列编排器 - 声明式关闭步骤
        self._shutdown_orchestrator = ShutdownOrchestrator()
        self._shutdown_orchestrator.add_step(
            "save_data",
            lambda: self._shutdown_save_all_data(),
            depends_on=[]
        )
        self._shutdown_orchestrator.add_step(
            "stop_polling",
            lambda: polling_manager.stop(),
            depends_on=["save_data"]
        )
        self._shutdown_orchestrator.add_step(
            "stop_terminal_signals",
            lambda: self._disconnect_terminal_signals(),
            depends_on=["save_data"]
        )
        self._shutdown_orchestrator.add_step(
            "stop_terminal_processes",
            lambda: self._stop_terminal_subprocesses(),
            depends_on=["stop_terminal_signals"]
        )
        self._shutdown_orchestrator.add_step(
            "stop_ipc",
            lambda: self._ipc_server.stop() if self._ipc_server else None,
            depends_on=["stop_polling"]
        )
        self._shutdown_orchestrator.add_step(
            "stop_process_manager",
            lambda: self._process_manager.stop_all() if self._process_manager else None,
            depends_on=["stop_ipc"]
        )

        # ===== DI 容器 - 注册配置服务 =====
        container.register_instance(IConfig, self.app_config)

        # 【关键】：先创建面板，再恢复窗口状态
        self._init_and_restore()
        
    def init_ui(self):
        """初始化主界面布局 - PS式固定中心画布架构"""
        # 创建菜单栏（嵌入标题栏）
        self._inline_menubar = _QMenuBar(self)
        self._inline_menubar.setObjectName("titleBarMenu")
        MenuManager.init_menu(self, self._inline_menubar)
        
        # 全局 Ctrl+D 删除动作（通过 Action 系统）
        delete_action = ActionFactory.create_action(self, "canvas.delete_selected")
        if delete_action:
            self.addAction(delete_action)

        # 全局 Ctrl+Z 撤销 / Ctrl+Y 重做
        from ui.core.commands.history_manager import history_manager
        from PySide6.QtGui import QAction
        self._undo_action = QAction("撤销", self)
        self._undo_action.setShortcut("Ctrl+Z")
        self._undo_action.triggered.connect(history_manager.undo)
        self.addAction(self._undo_action)

        self._redo_action = QAction("重做", self)
        self._redo_action.setShortcut("Ctrl+Y")
        self._redo_action.triggered.connect(history_manager.redo)
        self.addAction(self._redo_action)

        history_manager.can_undo_changed.connect(self._on_can_undo_changed)
        history_manager.can_redo_changed.connect(self._on_can_redo_changed)

        # 注入 EventBus（延迟绑定，避免循环导入）
        from ui.core.event_bus import event_bus
        history_manager.set_event_bus(event_bus)
        
        # 标题栏：标题 + 菜单 + 按钮同行
        self._title_bar = DarkTitleBar(self, "BnosConsole", self._inline_menubar)
        self._title_bar.minimize_clicked.connect(self.showMinimized)
        self._title_bar.maximize_clicked.connect(self._toggle_maximize)
        self._title_bar.close_clicked.connect(self.close)
        
        # ========== 画布宿主（CanvasHost）==========
        # PS式布局核心：CanvasHost作为固定的中央控件，与左右面板Dock平级
        # CanvasHost本身固定不动，只有内部的画布Dock可以自由操作
        self._canvas_host = CanvasHost(self)
        
        # 设置CanvasHost作为主窗口的中央控件（永久固定，不可拖动）
        self.setCentralWidget(self._canvas_host)
        
        # 获取活动画布引用（保持向后兼容）
        self.canvas = self._canvas_host.get_active_canvas()
        
        # ========== 停靠管理器（主窗口面板专用）==========
        # 面板只能停靠在左右两侧，不能进入中心CanvasHost区域
        from ui.core.dock_manager import DockManager
        self._dock_manager = DockManager(self)
        # 连接Dock面板关闭信号
        self._dock_manager.panel_closed.connect(self._on_dock_panel_closed)
        
        # ========== CanvasHost信号连接 ==========
        # 画布切换时同步面板数据
        self._canvas_host.canvas_changed.connect(self._on_canvas_changed)
        self._canvas_host.canvas_focused.connect(self._on_canvas_focused)
        # 所有画布关闭时重置项目状态
        self._canvas_host.all_canvases_closed.connect(self._on_all_canvases_closed)
        
        # 设置标题栏（通过setMenuWidget放在窗口顶部，不占用centralWidget空间）
        self.setMenuWidget(self._title_bar)
        
        # ========== IPC 进程间通信（主进程 = Server）==========
        self._ipc_server = None
        self._process_manager = ProcessManager(self)
        self._init_ipc()
        
        # ========== 面板实例（延迟创建）==========
        self.node_list_panel = None
        self.resource_monitor = None
        self.node_monitor_dock = None
        self.history_panel = None
    
    def show_toast(self, message, toast_type="info", duration=3000, node_name=None, operation_type=None):
        """便捷方法：显示Toast通知（通过队列管理器实现有序显示）

        Args:
            message: 通知文本内容
            toast_type: 类型 (info/success/warning/error)
            duration: 显示时长（毫秒），默认3000
            node_name: 关联的节点名称（可选，用于智能替换）
            operation_type: 操作类型（可选，如 'start', 'stop', 'delete'）

        功能特性：
        - 队列管理：Toast按顺序显示，最多同时显示3个
        - 智能替换：同节点同操作的提示会自动替换（如"正在启动"→"启动成功"）
        - 状态优先：操作状态提示（如"正在启动"）优先显示
        """
        self.toast_manager.show_toast(
            message=message,
            toast_type=toast_type,
            duration=duration,
            node_name=node_name,
            operation_type=operation_type
        )
    
    def _create_toast(self, message, toast_type="info", duration=3000, stack_index=0, node_name=None, operation_type=None):
        """创建Toast实例（供ToastQueueManager调用）"""
        toast = ToastNotification(
            message=message,
            parent=self,
            duration=duration,
            toast_type=toast_type,
            stack_index=stack_index,
            node_name=node_name,
            operation_type=operation_type
        )
        return toast
    
    def _on_canvas_changed(self, new_canvas):
        """画布切换事件 — 同步当前画布的数据到面板（不重新扫描磁盘）

        sync_canvas_data_to_main_window 已经把新画布的 nodes_data 同步到主窗口，
        此处只刷新面板/画布的显示，无需重新触发 project_refresh 走磁盘扫描。
        """
        logger.info(f"=== 画布切换 ===")

        # 更新当前画布引用
        self.canvas = new_canvas

        # 从CanvasHost同步当前画布的数据到主窗口
        if hasattr(self, '_canvas_host') and self._canvas_host:
            self._canvas_host.sync_canvas_data_to_main_window(new_canvas)

        # 数据已经在内存，直接刷新面板与画布
        if self.current_project_path and os.path.exists(self.current_project_path):
            self._refresh_panels()
            _canvas_call(self, 'sync_all_nodes_display')
            logger.info("画布切换完成（使用内存数据，未重新扫描磁盘）")
    
    def _on_canvas_focused(self, canvas):
        """画布获得焦点事件 - 同步面板数据"""
        logger.info(f"=== 画布获得焦点 ===")
        
        # 更新当前画布引用
        self.canvas = canvas
        
        # 从CanvasHost同步当前画布的数据到主窗口
        if hasattr(self, '_canvas_host') and self._canvas_host:
            self._canvas_host.sync_canvas_data_to_main_window(canvas)
        
        # 刷新所有面板以适配当前画布
        # 仅在项目路径存在且数据不为空时刷新
        if (self.current_project_path and 
            os.path.exists(self.current_project_path) and 
            len(self.nodes_data) > 0):
            self._refresh_panels()
        elif self.current_project_path and os.path.exists(self.current_project_path):
            # 如果项目路径存在但数据为空，也刷新（可能为新项目）
            self._refresh_panels()
        
        # 刷新资源监测器
        if hasattr(self, 'resource_monitor') and self.resource_monitor:
            # 检查是否有 update_stats 方法，否则尝试 _update_stats
            if hasattr(self.resource_monitor, 'update_stats'):
                self.resource_monitor.update_stats()
            elif hasattr(self.resource_monitor, '_update_stats'):
                self.resource_monitor._update_stats()

    def _on_all_canvases_closed(self):
        """所有画布关闭事件 - 重置项目状态，恢复空白初始状态"""
        logger.info("=== 所有画布已关闭 ===")
        
        # 重置当前画布引用
        self.canvas = None
        
        # 重置项目路径
        self.current_project_path = None
        
        # 清空节点数据
        self.nodes_data.clear()
        self.connections.clear()
        
        # 更新节点列表面板（清空列表）
        if self.node_list_panel:
            self.node_list_panel.update_node_list({})
        
        logger.info("项目状态已重置，回归空白初始状态")

    def open_color_settings(self):
        """打开颜色设置对话框"""
        dialog = ColorSettingsDialog(self.canvas, self)
        dialog.exec()

    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self, self)
        dialog.exec()
    
    def new_project(self):
        project_new(self)
        
    def open_project(self):
        project_open(self)
        
    def update_node_status(self, node_name, status):
        """更新节点状态并同步UI"""
        if node_name in self.nodes_data:
            self.nodes_data[node_name]['status'] = status
            if self.canvas: self.canvas.sync_node_display(node_name)
            self.node_list_panel.update_node_list(self.nodes_data)
        
    def refresh_nodes(self):
        project_refresh(self)
    
    def export_node(self, node_name=None):
        """导出单个节点（支持从菜单调用时自动获取选中节点）"""
        # 如果没有指定节点名，尝试获取选中的节点
        if not node_name:
            selected = resolve_selected_node(self)
            if not selected:
                self.show_toast(t("k_node_select_first"), "warning")
                return
            node_name = selected
        
        from ui.core.import_export_manager import ImportExportManager
        manager = ImportExportManager(self)
        manager.export_node(node_name)
    
    def export_project(self):
        """导出整个项目"""
        from ui.core.import_export_manager import ImportExportManager
        manager = ImportExportManager(self)
        manager.export_project()
    
    def import_node(self):
        """导入节点"""
        from ui.core.import_export_manager import ImportExportManager
        manager = ImportExportManager(self)
        manager.import_node()
    
    def mount_external_node(self):
        mount_node(self)

    def unmount_external_node(self, node_name: str):
        _unmount_node(self, node_name)

    def _on_node_status_changed(self, name, new_status):
        """polling_manager 信号：节点状态变更"""
        # 检查面板是否已创建
        if self.node_list_panel:
            self.node_list_panel.update_node_status(name, new_status)
        if self.canvas:
            self.canvas.update_node_status(name, new_status)
        if new_status == 'stopped':
            exit_code = self.nodes_data.get(name, {}).get('last_exit_code')
            self.show_toast(t("_k_node_exited").format(name=name, code=exit_code or '?'), "warning")

    def _on_global_log_changed(self, log_file, content):
        """polling_manager 信号：全局日志文件变化"""
        logger.debug(f"Global log changed: {log_file}")
        # 可以在这里添加日志变化的处理逻辑，例如更新日志面板

    def _on_global_config_changed(self, config_file):
        """polling_manager 信号：全局配置文件变化"""
        logger.info(f"Global config changed: {config_file}")
        # 如果是 app_config.json，重新加载配置
        if config_file == "app_config.json":
            self.app_config.load()
            self.show_toast(f"配置文件已更新: {config_file}", "info")
        # 如果是 color_settings.json，重新应用主题
        elif config_file == "color_settings.json":
            self._apply_dark_theme()
            self.show_toast(f"颜色配置已更新: {config_file}", "info")

    def _on_app_state_changed(self, state):
        """polling_manager 信号：应用状态变化"""
        logger.info(f"App state changed: {state}")
        # 可以在这里添加状态变化的处理逻辑

    def clear_connections(self):
        """清空所有连线"""
        reply = themed_message(self, t("k_title_confirm"), t("k_confirm_clear_connections"), "question")
        
        if not reply:
            return
        
        # 清空所有下游节点的 listen_upper_file
        for node_name, node_info in self.nodes_data.items():
            config = node_info['config']
            config['listen_upper_file'] = ""
            
            config_path = os.path.join(node_info['path'], "config.json")
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        
        if self.canvas: self.canvas.clear_edges()
        
        self.show_toast(t("k_canvas_cleared"), "success")

    def showEvent(self, event):
        """窗口显示事件 - 恢复终端 dock（必须在主窗口 show 后才能生效）"""
        super().showEvent(event)
        if not hasattr(self, '_terminal_restored'):
            self._terminal_restored = True
            # 延迟恢复，确保 CanvasHost 内的画布 dock 也已完成创建
            QTimer.singleShot(100, self._restore_terminal_dock)
    # 关闭辅助方法（_shutdown_save_all_data / _disconnect_terminal_signals / _stop_terminal_subprocesses）
    # —— 定义在 lifecycle.py 的 MainWindowLifecycleMixin 中，由 ShutdownOrchestrator 统一调用