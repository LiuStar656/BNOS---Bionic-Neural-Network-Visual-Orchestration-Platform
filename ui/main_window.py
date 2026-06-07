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
    QComboBox, QDialog, QDialogButtonBox, QHeaderView,
    QTableWidget, QTableWidgetItem, QMenu, QGraphicsView, QGraphicsScene,
    QInputDialog, QGraphicsOpacityEffect, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF, QTimer, QThread, QEvent
from PyQt6.QtGui import QIcon, QFont, QPainter, QPen, QColor, QAction, QMouseEvent
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.dark_title_bar import DarkTitleBar
from ui.core.utils.dialog_utils import themed_message
from PyQt6.QtWidgets import QMenuBar as _QMenuBar

from ui.canvas_widget import NodeCanvas
from ui.dialogs.color_settings_dialog import ColorSettingsDialog
from ui.dialogs.settings_dialog import SettingsDialog
from ui.creators.node_creator_manager import NodeCreatorManager
from ui.menu.menu_manager import MenuManager
from ui.core.toast.toast_notification import ToastNotification
from ui.core.toast.toast_queue_manager import ToastQueueManager
from ui.core.node_process import start_node_process, stop_node_process, resolve_selected_node, check_running_processes, detect_running_nodes
from ui.core.polling_manager import polling_manager
from ui.core.project_manager import project_new, project_open, project_refresh
from ui.core.external_node_manager import mount_node, unmount_node as _unmount_node
from ui.core.window_state_manager import save_state, restore_state
from ui.core.node_creation_worker import start_async_node_creation
from ui.core.node_registry import NodeRegistry
from ui.core.app_config import AppConfig
from ui.core.theme import DARK_QSS
from ui.core.ipc import IPCServer, A_ADD_NODE, A_REMOVE_NODE, A_UPDATE_STATUS
from ui.core.ipc import A_CREATE_EDGE, A_REMOVE_EDGE, A_SYNC_DATA, A_CLEAR_ALL, A_WIN_SYNC
from ui.core.process_manager import ProcessManager
from ui.core.canvas_host import CanvasHost


class BNOSMainWindow(QMainWindow):
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
        
        # 限制主窗口大小
        self.setMinimumSize(1024, 768)  # 最小尺寸：1024x768
        self.setMaximumSize(1920, 1080)  # 最大尺寸：1920x1080
        
        # 初始化UI
        self.init_ui()
        
        # 应用深色主题
        self._apply_dark_theme()
        
        # 恢复窗口状态
        self.restore_window_state()
        
        self.setWindowTitle("BnosConsole")
        
        # 统一轮询管理器（替代原来的 SystemMonitor 和 GlobalDetector）
        polling_manager.node_status_changed.connect(self._on_node_status_changed)
        polling_manager.global_log_changed.connect(self._on_global_log_changed)
        polling_manager.global_config_changed.connect(self._on_global_config_changed)
        polling_manager.app_state_changed.connect(self._on_app_state_changed)
        polling_manager.start(self.nodes_data)
        
        self.auto_open_last_project()
        
    def init_ui(self):
        """初始化主界面布局 - PS式固定中心画布架构"""
        # 创建菜单栏（嵌入标题栏）
        self._inline_menubar = _QMenuBar(self)
        self._inline_menubar.setObjectName("titleBarMenu")
        MenuManager.init_menu(self, self._inline_menubar)
        
        # 全局 Ctrl+D 删除动作
        self._action_delete = QAction(self)
        self._action_delete.setShortcut("Ctrl+D")
        self._action_delete.triggered.connect(self._on_ctrl_d)
        self.addAction(self._action_delete)
        
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
        
        # ========== IPC 进程间通信（主进程 = Server） ==========
        self._ipc_server = None
        self._process_manager = ProcessManager(self)
        self._init_ipc()
        
        # ========== 面板实例（延迟创建） ==========
        self.node_list_panel = None
        self.resource_monitor = None
        self.node_monitor_dock = None
    
    def moveEvent(self, event):
        """窗口移动事件"""
        super().moveEvent(event)
        if self.CANVAS_PROCESS_MODE:
            self._sync_canvas_geometry()
        
        # 浮动的节点监测面板跟随主窗口移动
        if hasattr(self, 'node_monitor') and self.node_monitor is not None and self.node_monitor.isVisible():
            p = self.pos()
            monitor_x = p.x() + self.width() - 440
            monitor_y = p.y() + 40
            self.node_monitor.move(monitor_x, monitor_y)
        
        if hasattr(self, 'toast_manager'):
            self.toast_manager._update_positions()
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        super().resizeEvent(event)
        if self.CANVAS_PROCESS_MODE:
            self._sync_canvas_geometry()
        
        # 浮动的节点监测面板跟随主窗口调整位置
        if hasattr(self, 'node_monitor') and self.node_monitor is not None and self.node_monitor.isVisible():
            p = self.pos()
            monitor_x = p.x() + self.width() - 440
            monitor_y = p.y() + 40
            self.node_monitor.move(monitor_x, monitor_y)
        
        if hasattr(self, 'toast_manager'):
            self.toast_manager._update_positions()
    
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
    
    def _refresh_panels(self):
        """刷新所有面板以适配当前画布"""
        # 刷新节点列表（浮动面板）
        if hasattr(self, 'node_list_panel') and self.node_list_panel and hasattr(self, 'nodes_data'):
            self.node_list_panel.update_node_list(self.nodes_data)
        
        # 刷新浮动版节点列表
        if hasattr(self, 'node_list_floating') and self.node_list_floating and hasattr(self, 'nodes_data'):
            self.node_list_floating.update_node_list(self.nodes_data)
        
        # 刷新节点列表 Dock 面板
        if hasattr(self, 'node_list_dock') and self.node_list_dock and hasattr(self, 'nodes_data'):
            self.node_list_dock.update_node_list(self.nodes_data)
    
    def _on_canvas_changed(self, new_canvas):
        """画布切换事件 - 同步面板数据"""
        logger.info(f"=== 画布切换 ===")
        
        # 更新当前画布引用
        self.canvas = new_canvas
        
        # 从CanvasHost同步当前画布的数据到主窗口
        if hasattr(self, '_canvas_host') and self._canvas_host:
            self._canvas_host.sync_canvas_data_to_main_window(new_canvas)
        
        # 如果画布有项目路径，同步数据
        # 但只在项目路径存在且至少有一个节点数据时才刷新面板
        if (self.current_project_path and 
            os.path.exists(self.current_project_path) and 
            len(self.nodes_data) > 0):
            # 刷新节点列表
            self.refresh_nodes()
            
            # 刷新所有面板
            self._refresh_panels()
            
            logger.info("面板数据已同步到新画布")
        elif self.current_project_path and os.path.exists(self.current_project_path):
            # 如果项目路径存在但节点数据为空，可能是刚创建画布还没加载完数据
            # 这种情况下也尝试刷新（例如在打开项目时）
            self.refresh_nodes()
            self._refresh_panels()
            logger.info("面板数据已同步到新画布（可能为空数据集）")
    
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

    def toggle_node_list_panel(self, checked):
        """切换节点列表面板（Dock版）- 停靠到左侧"""
        if checked:
            if self.node_list_panel is None:
                from ui.panels.node_list_dock import NodeListDockPanel
                self.node_list_panel = NodeListDockPanel(self)
                # 同步节点数据
                if hasattr(self, 'current_project_path') and self.current_project_path:
                    self.node_list_panel.set_project_path(self.current_project_path)
                if hasattr(self, 'nodes_data') and self.nodes_data:
                    self.node_list_panel.update_node_list(self.nodes_data)
            self._dock_manager.add_panel_to_dock(self.node_list_panel, t("k_node_list_dock"), edge='left')
            # 记录面板已打开
            self._save_panel_visibility_state('node_list_dock', True)
        else:
            # 记录面板已关闭
            self._save_panel_visibility_state('node_list_dock', False)

    def show_node_list_floating(self):
        """打开节点列表面板（浮动版）- 带位置持久化"""
        from ui.panels.node_list_panel import NodeListPanel
        if not hasattr(self, 'node_list_floating') or self.node_list_floating is None:
            self.node_list_floating = NodeListPanel(self)
            # 从配置加载位置（使用 node_list_floating 键名，避免与 Dock 版冲突）
            pos = self.app_config.get('panel_positions', {}).get('node_list_floating', {'x': 10, 'y': 100})
            self.node_list_floating.move(pos['x'], pos['y'])
            # 连接关闭信号保存位置和可见性
            self.node_list_floating.closed.connect(self._on_node_list_floating_closed)
            # 更新节点数据
            if hasattr(self, 'nodes_data') and self.nodes_data:
                self.node_list_floating.update_node_list(self.nodes_data)
        self.node_list_floating.show()
        self.node_list_floating.raise_()
        # 记录面板已打开
        self._save_panel_visibility_state('node_list_floating', True)

    def show_node_monitor(self):
        """打开节点监测面板（浮动版）- 带位置持久化"""
        from ui.panels.node_monitor import NodeMonitor
        if not hasattr(self, 'node_monitor') or self.node_monitor is None:
            self.node_monitor = NodeMonitor(self)
            # 从配置加载位置（使用 node_monitor_floating 键名，避免与 Dock 版冲突）
            pos = self.app_config.get('panel_positions', {}).get('node_monitor_floating', {'x': 10, 'y': 100})
            self.node_monitor.move(pos['x'], pos['y'])
            # 连接关闭信号保存位置和可见性
            self.node_monitor.closed.connect(self._on_node_monitor_closed)
        self.node_monitor.show()
        self.node_monitor.raise_()
        # 记录面板已打开
        self._save_panel_visibility_state('node_monitor_floating', True)

    def show_node_monitor_dock(self):
        """打开节点监测面板（Dock版）- 停靠到右侧"""
        if not hasattr(self, 'node_monitor_dock') or self.node_monitor_dock is None:
            from ui.panels.node_monitor_dock import NodeMonitorDock
            self.node_monitor_dock = NodeMonitorDock(self)
        self._dock_manager.add_panel_to_dock(self.node_monitor_dock, t("k_node_monitor_dock"), edge='right')
        # 记录面板已打开
        self._save_panel_visibility_state('node_monitor_dock', True)

    def show_resource_monitor(self):
        """打开资源监测面板（浮动版）- 带位置持久化"""
        from ui.panels.resource_monitor import ResourceMonitor
        if not hasattr(self, 'resource_monitor_floating') or self.resource_monitor_floating is None:
            self.resource_monitor_floating = ResourceMonitor(self)
            # 从配置加载位置（使用 resource_monitor_floating 键名，避免与 Dock 版冲突）
            pos = self.app_config.get('panel_positions', {}).get('resource_monitor_floating', {'x': 10, 'y': 100})
            self.resource_monitor_floating.move(pos['x'], pos['y'])
            # 连接关闭信号保存位置和可见性
            self.resource_monitor_floating.closed.connect(self._on_resource_monitor_floating_closed)
            
            # 确保已存在的节点能连接到信号
            self._connect_existing_nodes_to_resource_monitor(self.resource_monitor_floating)
            
        self.resource_monitor_floating.show()
        self.resource_monitor_floating.raise_()
        # 记录面板已打开
        self._save_panel_visibility_state('resource_monitor_floating', True)

    def show_resource_monitor_dock(self):
        """打开资源监测面板（Dock版）- 停靠到左侧"""
        if self.resource_monitor is None:
            from ui.panels.resource_monitor_dock import ResourceMonitorDock
            self.resource_monitor = ResourceMonitorDock(self)
            
            # 确保已存在的节点能连接到信号（如果Dock版有这个信号）
            if hasattr(self.resource_monitor, 'node_state_updated'):
                self._connect_existing_nodes_to_resource_monitor(self.resource_monitor)
                
        self._dock_manager.add_panel_to_dock(self.resource_monitor, t("k_resource_monitor_dock"), edge='left')
        # 记录面板已打开
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
        # 更新对应的通用键（用于向后兼容）
        if panel_key.endswith('_dock'):
            base_key = panel_key[:-5]  # 去掉 '_dock'
            visibility[base_key] = visibility.get(base_key, False) or visible
        elif panel_key.endswith('_floating'):
            base_key = panel_key[:-9]  # 去掉 '_floating'
            visibility[base_key] = visibility.get(base_key, False) or visible
        self.app_config.set('panel_visibility', visibility)
        self.app_config.save()
    
    def _on_node_list_floating_closed(self):
        """浮动节点列表面板关闭处理"""
        # 保存位置（使用 node_list_floating 键名，避免与 Dock 版冲突）
        self._save_panel_position('node_list_floating', self.node_list_floating)
        # 记录面板已关闭
        self._save_panel_visibility_state('node_list_floating', False)
    
    def _on_node_monitor_closed(self):
        """节点监测面板关闭处理"""
        # 保存位置（使用 node_monitor_floating 键名，避免与 Dock 版冲突）
        self._save_panel_position('node_monitor_floating', self.node_monitor)
        # 记录面板已关闭
        self._save_panel_visibility_state('node_monitor_floating', False)
    
    def _on_resource_monitor_floating_closed(self):
        """浮动资源监测面板关闭处理"""
        # 保存位置（使用 resource_monitor_floating 键名，避免与 Dock 版冲突）
        self._save_panel_position('resource_monitor_floating', self.resource_monitor_floating)
        # 记录面板已关闭
        self._save_panel_visibility_state('resource_monitor_floating', False)

    def _on_dock_panel_closed(self, widget):
        """Dock面板关闭处理"""
        # 清除主窗口中对应的面板引用，避免访问已删除的对象
        if self.node_list_panel == widget:
            self.node_list_panel = None
            self._save_panel_visibility_state('node_list_dock', False)
        elif self.resource_monitor == widget:
            self.resource_monitor = None
            self._save_panel_visibility_state('resource_monitor_dock', False)
        elif self.node_monitor_dock == widget:
            self.node_monitor_dock = None
            self._save_panel_visibility_state('node_monitor_dock', False)
    
    def _save_panel_visibility(self):
        """保存所有面板的可见性状态到配置"""
        # 获取当前配置中的状态（保留已关闭面板的状态）
        current_visibility = self.app_config.get('panel_visibility', {})
        
        # 检查面板是否真正可见（而不仅仅是对象是否存在）
        def is_panel_visible(panel):
            if panel is None:
                return None  # 返回 None 表示面板对象不存在，不更新状态
            visible = panel.isVisible()
            logger.debug("面板可见性检查: %s = %s", type(panel).__name__, visible)
            return visible
        
        # 只更新存在的面板状态，不存在的面板保留配置中的值
        visibility = current_visibility.copy()
        
        # 更新存在的面板状态
        dock_panels = [
            ('node_list_dock', self.node_list_panel),
            ('resource_monitor_dock', self.resource_monitor),
            ('node_monitor_dock', getattr(self, 'node_monitor_dock', None)),
        ]
        floating_panels = [
            ('node_list_floating', getattr(self, 'node_list_floating', None)),
            ('resource_monitor_floating', getattr(self, 'resource_monitor_floating', None)),
            ('node_monitor_floating', getattr(self, 'node_monitor', None)),
        ]
        
        for key, panel in dock_panels + floating_panels:
            visible = is_panel_visible(panel)
            if visible is not None:
                visibility[key] = visible
        
        # 更新旧格式（兼容旧配置）
        visibility['node_list'] = is_panel_visible(self.node_list_panel) or is_panel_visible(getattr(self, 'node_list_floating', None)) or False
        visibility['resource_monitor'] = is_panel_visible(self.resource_monitor) or is_panel_visible(getattr(self, 'resource_monitor_floating', None)) or False
        visibility['node_monitor'] = is_panel_visible(getattr(self, 'node_monitor_dock', None)) or is_panel_visible(getattr(self, 'node_monitor', None)) or False
        
        logger.info("保存面板可见性状态: %s", visibility)
        self.app_config.set('panel_visibility', visibility)
    
    def _restore_panel_state(self):
        """从配置恢复面板可见性状态"""
        visibility = self.app_config.get('panel_visibility', {})
        logger.info("开始恢复面板状态，配置值: %s", visibility)
        
        # 检查旧的配置项（兼容旧版本）
        old_visible = self.app_config.get('node_list_panel', {}).get('visible', False)
        logger.info("旧配置项 node_list_panel.visible: %s", old_visible)
        
        # ===== 节点列表面板 =====
        # 优先使用新格式（带后缀），只有当新格式不存在时才使用旧格式（基础键）
        show_node_dock = visibility.get('node_list_dock')
        show_node_float = visibility.get('node_list_floating')
        
        # 如果新格式键不存在，使用旧格式作为备选
        if show_node_dock is None:
            show_node_dock = visibility.get('node_list', old_visible)
        if show_node_float is None:
            show_node_float = False
        
        logger.info("节点列表 - dock: %s, floating: %s", show_node_dock, show_node_float)
        
        # 根据配置分别显示，不再强制优先显示Dock版
        if show_node_dock:
            logger.info("恢复节点列表 Dock 版")
            self.toggle_node_list_panel(True)
        if show_node_float:
            logger.info("恢复节点列表 浮动版")
            QTimer.singleShot(100, self.show_node_list_floating)
        
        # ===== 资源监测面板 =====
        show_resource_dock = visibility.get('resource_monitor_dock')
        show_resource_float = visibility.get('resource_monitor_floating')
        
        if show_resource_dock is None:
            show_resource_dock = visibility.get('resource_monitor', False)
        if show_resource_float is None:
            show_resource_float = False
        
        logger.info("资源监测 - dock: %s, floating: %s", show_resource_dock, show_resource_float)
        
        if show_resource_dock:
            logger.info("恢复资源监测 Dock 版")
            self.show_resource_monitor_dock()
        if show_resource_float:
            logger.info("恢复资源监测 浮动版")
            QTimer.singleShot(150, self.show_resource_monitor)
        
        # ===== 节点监测面板 =====
        show_monitor_dock = visibility.get('node_monitor_dock')
        show_monitor_float = visibility.get('node_monitor_floating')
        
        if show_monitor_dock is None:
            show_monitor_dock = visibility.get('node_monitor', False)
        if show_monitor_float is None:
            show_monitor_float = False
        
        logger.info("节点监测 - dock: %s, floating: %s", show_monitor_dock, show_monitor_float)
        
        if show_monitor_dock:
            logger.info("恢复节点监测 Dock 版")
            self.show_node_monitor_dock()
        if show_monitor_float:
            logger.info("恢复节点监测 浮动版")
            QTimer.singleShot(200, self.show_node_monitor)

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

        from ui.core.utils.dialog_utils import themed_input
        prompt = t("k_node_enter_name").replace("{lang}", language)
        node_name = themed_input(self, t("k_node_create"), prompt)
        if not node_name:
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
        """按名称启动节点（异步执行，不阻塞 GUI）"""
        if node_name not in self.nodes_data:
            return
        node_info = self.nodes_data[node_name]
        if node_info['status'] in ('running', 'idle'):
            self.show_toast(t("_k_node_running").format(name=node_name), "info")
            return
        
        # 立即显示启动中状态
        self.node_list_panel.update_node_status(node_name, 'idle')
        if self.canvas: 
            self.canvas.update_node_status(node_name, 'idle')
        # 使用新的替换机制显示"正在启动"
        self.show_toast(t("_k_node_starting").format(name=node_name), "info", 
                        node_name=node_name, operation_type="start")
        
        # 异步执行启动
        QTimer.singleShot(10, lambda: self._start_node_async(node_name))

    def _start_node_async(self, node_name):
        """异步启动节点（使用后台线程执行，不阻塞GUI）"""
        if node_name not in self.nodes_data:
            return
        
        # 创建后台工作线程
        class StartNodeWorker(QThread):
            finished = pyqtSignal(bool, str)
            
            def __init__(self, node_info, parent=None):
                super().__init__(parent)
                self.node_info = node_info
            
            def run(self):
                # 在后台线程中执行启动操作
                success, err = start_node_process(self.node_info)
                self.finished.emit(success, err)
        
        node_info = self.nodes_data[node_name]
        worker = StartNodeWorker(node_info)
        
        # 添加到跟踪列表
        self._node_start_workers.append(worker)
        
        # 连接完成信号
        def on_complete(success, err):
            # 从跟踪列表中移除
            if worker in self._node_start_workers:
                self._node_start_workers.remove(worker)
            
            if success:
                self.node_list_panel.update_node_status(node_name, 'idle')
                if self.canvas: 
                    self.canvas.update_node_status(node_name, 'idle')
                # 替换"正在启动"为"启动成功"
                self.show_toast(t("_k_node_started").format(name=node_name), "success", 
                                node_name=node_name, operation_type="start")
            else:
                self.node_list_panel.update_node_status(node_name, 'stopped')
                if self.canvas: 
                    self.canvas.update_node_status(node_name, 'stopped')
                themed_message(self, t("k_title_error"), t("_k_start_fail").format(err=err), "error")
        
        worker.finished.connect(on_complete)
        # 线程完成后自动删除
        worker.finished.connect(worker.deleteLater)
        worker.start()
    
    def stop_selected_node(self):
        """停止选中的节点"""
        selected = resolve_selected_node(self)
        if not selected:
            self.show_toast(t("k_node_select_first"), "warning")
            return
        self.stop_selected_node_by_name(selected)
    
    def stop_selected_node_by_name(self, node_name):
        """按名称停止节点（异步执行，不阻塞 GUI）"""
        if node_name not in self.nodes_data:
            return
        node_info = self.nodes_data[node_name]
        if node_info['status'] == 'stopped':
            self.show_toast(t("_k_node_not_running_toast").format(name=node_name), "info")
            return
        
        # 立即显示停止中状态
        self.node_list_panel.update_node_status(node_name, 'stopped')
        if self.canvas: 
            self.canvas.update_node_status(node_name, 'stopped')
        # 使用新的替换机制显示"正在停止"
        self.show_toast(t("_k_node_stopping").format(name=node_name), "info", 
                        node_name=node_name, operation_type="stop")
        
        # 异步执行停止
        QTimer.singleShot(10, lambda: self._stop_node_async(node_name))

    def _stop_node_async(self, node_name):
        """异步停止节点（内部方法）"""
        if node_name not in self.nodes_data:
            return
        
        node_info = self.nodes_data[node_name]
        stop_node_process(node_info)
        
        # 在主线程中更新 UI
        def on_complete():
            self.node_list_panel.update_node_status(node_name, 'stopped')
            if self.canvas: 
                self.canvas.update_node_status(node_name, 'stopped')
            # 替换"正在停止"为"停止成功"
            self.show_toast(t("_k_node_stopped").format(name=node_name), "success", 
                            node_name=node_name, operation_type="stop")
        
        QTimer.singleShot(10, on_complete)

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

    def closeEvent(self, event):
        """窗口关闭事件，保存所有状态"""
        logger.info("开始关闭窗口检测...")
        logger.info("   当前项目: %s", self.current_project_path)
        logger.info("   节点总数: %d", len(self.nodes_data))
        
        # 等待节点创建线程完成（如果正在运行）
        if hasattr(self, 'node_creation_worker'):
            try:
                # 检查对象是否仍然有效（未被deleteLater删除）
                if self.node_creation_worker and self.node_creation_worker.isRunning():
                    logger.info("等待节点创建线程完成...")
                    self.node_creation_worker.wait(5000)
                    if self.node_creation_worker.isRunning():
                        logger.warning("节点创建线程超时，强制终止")
                        self.node_creation_worker.terminate()
            except RuntimeError:
                # 对象已被删除
                logger.info("节点创建线程对象已被清理")
        
        # 等待节点启动线程完成
        if hasattr(self, '_node_start_workers') and self._node_start_workers:
            logger.info("等待 %d 个节点启动线程完成...", len(self._node_start_workers))
            for worker in list(self._node_start_workers):
                if worker.isRunning():
                    worker.wait(3000)
                    if worker.isRunning():
                        logger.warning("节点启动线程超时，强制终止")
                        worker.terminate()
        
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
            
            from ui.core.utils.dialog_utils import MSG_ACCEPT, MSG_REJECT, MSG_CANCEL
            reply = themed_message(
                self, t("k_title_detect_running"),
                t("_k_close_running_nodes").format(count=len(running_nodes), nodes=nodes_list),
                "question3"
            )
            
            if reply == MSG_ACCEPT:
                logger.info("正在关闭 %d 个运行中的节点...", len(running_nodes))
                self._force_stop_all_nodes(running_nodes)
                self.show_toast(t("_k_nodes_closed").format(count=len(running_nodes)), "success")
            elif reply == MSG_REJECT:
                # 用户选择不关闭，让进程继续运行
                logger.info("%d 个节点将继续在后台运行", len(running_nodes))
                self.show_toast(t("_k_nodes_background").format(count=len(running_nodes)), "info")
                # 继续执行后续的保存和关闭逻辑
            else:
                # 用户选择取消，中止关闭操作
                logger.info("用户取消了关闭操作")
                event.ignore()  # 忽略关闭事件，保持窗口打开
                return
        
        # 同步当前主窗口数据到活动画布（用于保存）
        if hasattr(self, '_canvas_host') and self._canvas_host:
            self._canvas_host.update_canvas_data_from_main_window(self.canvas)
        
        # 保存所有画布布局（通过CanvasHost）
        if self.current_project_path and hasattr(self, '_canvas_host'):
            self._canvas_host.save_all_layouts(self.current_project_path)
        
        # 保存应用配置
        self.save_window_state()
        self.app_config.set("last_project", self.current_project_path)
        
        # 保存面板可见性状态
        logger.info("准备保存面板状态...")
        self._save_panel_visibility()
        
        # 保存所有浮动面板的位置（即使它们没有被手动关闭）
        panels = [
            ('node_list', getattr(self, 'node_list_floating', None)),
            ('resource_monitor', getattr(self, 'resource_monitor_floating', None)),
            ('node_monitor', getattr(self, 'node_monitor', None)),
        ]
        for panel_name, panel_widget in panels:
            if panel_widget and panel_widget.isVisible():
                logger.info("保存面板位置: %s = (%d, %d)", panel_name, panel_widget.pos().x(), panel_widget.pos().y())
                self._save_panel_position(panel_name, panel_widget)
        
        # 强制同步保存配置到文件（确保所有修改都写入磁盘）
        logger.info("强制保存配置到文件...")
        self.app_config.save()
        
        # 验证保存是否成功
        import os
        if os.path.exists(self.app_config.config_file):
            logger.info("配置文件保存成功: %s", self.app_config.config_file)
            # 读取验证
            try:
                with open(self.app_config.config_file, 'r', encoding='utf-8') as f:
                    saved_config = f.read()
                    logger.debug("已保存的配置内容长度: %d 字符", len(saved_config))
            except Exception as e:
                logger.warning("验证配置文件失败: %s", e)
        else:
            logger.error("配置文件保存失败，文件不存在")
        
        # 停止统一轮询管理器（在配置保存完成后）
        logger.info("停止轮询管理器...")
        polling_manager.stop()
        
        # 停止 IPC 和子进程（在配置保存完成后）
        logger.info("停止 IPC 和子进程...")
        if self._process_manager:
            self._process_manager.stop_all()
        if self._ipc_server:
            self._ipc_server.stop()

        logger.info("窗口关闭流程完成，所有数据已安全保存")
        event.accept()
    
    def _force_stop_all_nodes(self, node_names):
        """强制停止所有指定节点进程"""
        for node_name in node_names:
            if node_name in self.nodes_data:
                stop_node_process(self.nodes_data[node_name])
                logger.info("节点 %s 已停止", node_name)
        self.node_list_panel.update_node_list(self.nodes_data)
        if self.canvas: self.canvas.sync_all_nodes_display()
    
    def save_window_state(self):
        save_state(self)

    def restore_window_state(self):
        restore_state(self)
    
    def auto_open_last_project(self):
        """自动打开上次打开的项目：
        - 如果有上次打开的项目，自动打开
        - 如果没有，保持空白，等待用户手动打开
        """
        # 先恢复面板状态
        QTimer.singleShot(100, self._restore_panel_state)
        
        # 检查是否有上次打开的项目
        last_project = self.app_config.get("last_project")
        if last_project and isinstance(last_project, str) and os.path.exists(last_project):
            # 有上次打开的项目，自动打开
            logger.info("自动打开上次项目: %s", last_project)
            # 使用 QTimer 延迟打开，确保 UI 初始化完成
            QTimer.singleShot(200, lambda: self._auto_open_project(last_project))
        else:
            logger.info("没有上次项目或项目不存在，等待用户手动打开项目")
    
    def _auto_open_project(self, project_dir):
        """内部方法：自动打开指定项目
        
        这个方法类似于 project_open，但不需要用户交互
        """
        # 检查项目是否已经打开
        if hasattr(self, '_canvas_host') and self._canvas_host:
            if self._canvas_host.is_project_open(project_dir):
                logger.info("项目已经打开，无需重复打开: %s", project_dir)
                return
        
        # 验证是否为有效项目
        nodes_dir = os.path.join(project_dir, "nodes")
        has_nodes = os.path.isdir(nodes_dir)
        has_layout = os.path.isfile(os.path.join(project_dir, "canvas_layout.json"))
        
        if not has_nodes and not has_layout:
            logger.warning("不是有效项目目录: %s", project_dir)
            return
        
        # 确保 nodes/ 存在
        if not has_nodes:
            os.makedirs(nodes_dir, exist_ok=True)
        
        # 加载项目数据
        project_name = os.path.basename(project_dir)
        self.current_project_path = project_dir
        self.nodes_data.clear()
        self.connections.clear()
        
        # 同步加载项目
        from ui.core.project_manager import project_refresh
        project_refresh(self, async_mode=False)
        
        # 创建画布
        if hasattr(self, '_canvas_host'):
            self._canvas_host.add_canvas_dock(project_name, project_dir)
        
        # 加载布局
        self._canvas_host.load_layout_for_active(project_dir)
        
        # 保存项目到配置
        self.app_config.set("last_project", self.current_project_path)
        self.app_config.save()
        
        self.show_toast(f"已自动打开项目: {project_name}", "success")
    
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
            if direction:
                self._resize_direction = direction
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_original_geometry = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        if hasattr(self, '_resize_direction') and self._resize_direction:
            # 执行窗口调整大小
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            new_geo = self._resize_original_geometry
            
            if 'left' in self._resize_direction:
                new_width = max(self.minimumWidth(), new_geo.width() - delta.x())
                new_geo.setX(new_geo.x() + (new_geo.width() - new_width))
                new_geo.setWidth(new_width)
            
            if 'right' in self._resize_direction:
                new_geo.setWidth(max(self.minimumWidth(), self._resize_original_geometry.width() + delta.x()))
            
            if 'top' in self._resize_direction:
                new_height = max(self.minimumHeight(), new_geo.height() - delta.y())
                new_geo.setY(new_geo.y() + (new_geo.height() - new_height))
                new_geo.setHeight(new_height)
            
            if 'bottom' in self._resize_direction:
                new_geo.setHeight(max(self.minimumHeight(), self._resize_original_geometry.height() + delta.y()))
            
            self.setGeometry(new_geo)
        else:
            if not self.isMaximized():
                cursor, _ = self._get_resize_region(event.pos())
                if cursor: self.setCursor(cursor)
                else: self.unsetCursor()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if hasattr(self, '_resize_direction') and self._resize_direction:
            self._resize_direction = None
            self._resize_start_pos = None
            self._resize_original_geometry = None
        super().mouseReleaseEvent(event)
    
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
        self.show_toast(t("_k_canvas_crashed"), "warning")
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

    def _start_canvas_and_load(self, project_path):
        """启动画布子进程并加载布局"""
        self._start_canvas_process()
        # 延迟布局同步
        QTimer.singleShot(600, lambda: self._sync_canvas_geometry())
        QTimer.singleShot(800, lambda: self._canvas_ipc_sync() if self._ipc_server else None)

    def _sync_canvas_geometry(self):
        """发送主窗口几何信息给画布子进程，实现视觉一体化"""
        if not self._ipc_server:
            return
        g = self.geometry()
        # 画布应在标题栏下方
        self._ipc_server.broadcast(A_WIN_SYNC, {
            "x": g.x(), "y": g.y() + 40,    # 40 = 标题栏高度
            "w": g.width(), "h": g.height() - 40,
        })

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
        
        # 检查是否有运行中的节点
        running_nodes = []
        for node_name, node_info in self.nodes_data.items():
            status = node_info.get('status', 'unknown')
            process = node_info.get('process', None)
            if status == 'running' and process:
                running_nodes.append(node_name)
        
        logger.info("检测到 %d 个运行中的节点: %s", len(running_nodes), running_nodes)
        
        # 如果有运行中的节点，提示用户
        if running_nodes:
            nodes_list = "\n".join([f"• {name}" for name in running_nodes[:10]])  # 最多显示10个
            if len(running_nodes) > 10:
                nodes_list += f"\n... 还有 {len(running_nodes) - 10} 个节点"
            
            from ui.core.utils.dialog_utils import MSG_ACCEPT, MSG_REJECT, MSG_CANCEL
            reply = themed_message(
                self, t("k_title_detect_running"),
                t("_k_close_running_nodes").format(count=len(running_nodes), nodes=nodes_list),
                "question3"
            )
            
            if reply == MSG_ACCEPT:
                logger.info("正在关闭 %d 个运行中的节点...", len(running_nodes))
                self._force_stop_all_nodes(running_nodes)
                self.show_toast(t("_k_nodes_closed").format(count=len(running_nodes)), "success")
            elif reply == MSG_REJECT:
                # 用户选择不关闭，让进程继续运行
                logger.info("%d 个节点将继续在后台运行", len(running_nodes))
                self.show_toast(t("_k_nodes_background").format(count=len(running_nodes)), "info")
                # 继续执行后续的保存和关闭逻辑
            else:
                # 用户选择取消，中止重启操作
                logger.info("用户取消了重启操作")
                self.show_toast(t("_k_restart_canceled"), "info")
                return
        
        self._process_manager.stop_all()
        if self._ipc_server:
            self._ipc_server.stop()
        # 确保配置已刷盘
        try:
            self.app_config.save()
        except Exception:
            pass
        # 使用退出码 42 驱动主函数重启（避免 sys.exit 被 Qt 事件循环吞掉）
        QApplication.instance().exit(42)

    @property
    def _canvas_mode(self):
        return self.CANVAS_PROCESS_MODE and self._process_manager is not None

    def _apply_dark_theme(self):
        self.setStyleSheet(DARK_QSS)

    def _on_ctrl_d(self):
        """Ctrl+D 统一删除：画布选区/节点列表/绘图图形/节点组"""
        # 节点列表面板有焦点 → 删除选中节点或组
        if self.node_list_panel and self.node_list_panel.isVisible():
            try:
                from PyQt6.QtWidgets import QApplication
                fw = QApplication.focusWidget()
                if fw and self.node_list_panel.isAncestorOf(fw):
                    sel = self.node_list_panel.get_selected_nodes()
                    if sel:
                        self.node_list_panel.batch_delete_nodes()
                        return
                    grps = self.node_list_panel.get_selected_groups()
                    for g in grps:
                        self.node_list_panel.delete_group(g)
                    if grps:
                        return
            except Exception:
                pass

        # 画布有焦点 → 删除选中节点/图形
        if self.canvas:
            if self.canvas.box_selected_nodes:
                self.canvas.batch_remove_nodes_from_canvas()
                return
            self.canvas.draw_layer.delete_selected()
            return
    
    def show_about(self):
        """显示关于对话框"""
        themed_message(self, t("k_title_about"), t("_k_about_text"), "info")