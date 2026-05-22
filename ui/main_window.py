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
from ui.panels.property_panel import ColorSettingsDialog
from ui.creators.node_creator_manager import NodeCreatorManager
from ui.menu.menu_manager import MenuManager
from ui.core.toast.toast_notification import ToastNotification
from ui.core.node_process import start_node_process, stop_node_process, resolve_selected_node, check_running_processes, detect_running_nodes
from ui.core.node_registry import NodeRegistry
from ui.core.app_config import AppConfig
from ui.core.theme import DARK_QSS


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
        """新建项目"""
        # 保存当前项目布局（如果有）
        if self.current_project_path:
            self.canvas.save_layout(self.current_project_path)
        
        project_dir = QFileDialog.getExistingDirectory(
            self, t("k_project_select_dir"), "", 
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if not project_dir:
            return
        
        # 确认是否在项目目录下创建nodes子目录
        nodes_dir = os.path.join(project_dir, "nodes")
        if not os.path.exists(nodes_dir):
            reply = QMessageBox.question(
                self, t("k_project_create_nodes_dir"),
                f"在 {project_dir} 下创建 nodes/ 目录？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.makedirs(nodes_dir, exist_ok=True)
            else:
                return
        
        # 绑定项目
        self.current_project_path = project_dir
        self.nodes_data.clear()
        self.connections.clear()
        self.canvas.clear_canvas()
        
        # 刷新节点列表
        self.refresh_nodes()
        
        self.show_toast(f"已创建项目: {os.path.basename(project_dir)}", "success")
        
    def open_project(self):
        """打开项目"""
        # 保存当前项目布局（如果有）
        if self.current_project_path:
            self.canvas.save_layout(self.current_project_path)
        
        project_dir = QFileDialog.getExistingDirectory(
            self, t("k_project_open_dir"), "", 
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if not project_dir:
            return
        
        nodes_dir = os.path.join(project_dir, "nodes")
        if not os.path.exists(nodes_dir):
            reply = QMessageBox.question(
                self, t("k_project_no_nodes_dir"),
                f"{project_dir} 下未找到 nodes/ 目录，是否创建？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                os.makedirs(nodes_dir, exist_ok=True)
            else:
                return
        
        # 绑定项目
        self.current_project_path = project_dir
        self.nodes_data.clear()
        self.connections.clear()
        self.canvas.clear_canvas()
        
        # 刷新节点列表
        self.refresh_nodes()
        
        # 加载画布布局
        self.canvas.load_layout(project_dir)
        
        self.show_toast(f"已打开项目: {os.path.basename(project_dir)}", "success")
        
    def update_node_status(self, node_name, status):
        """更新节点状态并同步UI"""
        if node_name in self.nodes_data:
            self.nodes_data[node_name]['status'] = status
            
            # 同步更新画布上的节点显示
            self.canvas.sync_node_display(node_name)
            
            # 更新节点列表面板
            self.node_list_panel.update_node_list(self.nodes_data)
        
    def refresh_nodes(self):
        """刷新节点列表"""
        if not self.current_project_path:
            self.show_toast(t("k_project_no_project"), "warning")
            return
        
        # 确保项目路径是绝对路径
        project_path = os.path.abspath(self.current_project_path)
        nodes_dir = os.path.join(project_path, "nodes")
        
        if not os.path.exists(nodes_dir):
            self.show_toast(t("k_project_nodes_not_exist"), "warning")
            return
        
        logger.info(t("k_log_load_node"))
        logger.debug("项目路径: %s", project_path)
        logger.debug("Nodes 目录: %s", nodes_dir)
        
        # 扫描节点
        self.nodes_data.clear()
        for item in os.listdir(nodes_dir):
            node_path = os.path.join(nodes_dir, item)
            
            # 强制转换为绝对路径并规范化
            node_path = os.path.abspath(node_path)
            node_path = os.path.normpath(node_path)
            
            if not os.path.isdir(node_path):
                continue
            
            config_path = os.path.join(node_path, "config.json")
            if not os.path.exists(config_path):
                continue
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                node_name = config.get('node_name', item)
                
                # 再次验证路径是否正确
                expected_path = os.path.join(nodes_dir, item)
                expected_path = os.path.abspath(expected_path)
                expected_path = os.path.normpath(expected_path)
                
                if node_path != expected_path:
                    logger.warning("节点 '%s' 路径不一致: 期望=%s, 实际=%s", item, expected_path, node_path)
                    node_path = expected_path
                
                self.nodes_data[node_name] = {
                    'config': config,
                    'path': node_path,  # 确保存储的是规范的绝对路径
                    'process': None,
                    'status': 'stopped'
                }
                
                logger.info("加载节点: %s (文件夹=%s)", node_name, item)
                logger.debug("   路径: %s, 存在: %s", node_path, os.path.exists(node_path))
                
            except Exception as e:
                logger.error("加载节点 %s 失败: %s", item, e)
                import traceback
                traceback.print_exc()
        
        logger.info("共加载 %d 个节点", len(self.nodes_data))
        
        # === 同步节点注册表（扫描结果优先，注册表辅助） ===
        try:
            registry = NodeRegistry(self.current_project_path)
            registry.load()
            # 以当前扫描结果为准同步注册表
            scan_result = {name: info['path'] for name, info in self.nodes_data.items()}
            registry.sync_from_scan(scan_result)
            registry.save()
            logger.info("节点注册表已同步: active=%d, missing=%d, total=%d",
                        registry.active_count, registry.missing_count, registry.node_count)

            # === 恢复外部挂载节点 ===
            mounted_nodes = registry.get_mounted_nodes()
            for m_name, m_info in mounted_nodes.items():
                if m_name not in self.nodes_data and m_info.get("status") == "active":
                    m_path = m_info.get("path", "")
                    m_config_path = os.path.join(m_path, "config.json")
                    m_mount_root = m_info.get("mount_root", "")
                    try:
                        if os.path.exists(m_config_path):
                            with open(m_config_path, 'r', encoding='utf-8') as f:
                                m_config = json.load(f)
                        else:
                            m_config = {'node_name': m_name}
                        self.nodes_data[m_name] = {
                            'config': m_config,
                            'path': m_path,
                            'process': None,
                            'status': 'stopped',
                            'mounted': True,
                            'mount_root': m_mount_root
                        }
                        logger.info("恢复挂载节点: %s (mount_root=%s)", m_name, m_mount_root)
                    except Exception as ex:
                        logger.warning("恢复挂载节点 %s 失败: %s", m_name, ex)
            logger.info("共恢复 %d 个挂载节点", len(mounted_nodes))
        except Exception as e:
            logger.warning("节点注册表同步失败: %s", e)
        
        # 更新节点组管理器的项目路径（自动加载配置）
        self.node_list_panel.set_project_path(self.current_project_path)
        
        # 更新节点列表面板
        self.node_list_panel.update_node_list(self.nodes_data)
        
        # 同步更新画布上的所有节点显示
        self.canvas.sync_all_nodes_display()
        
        # 检测后台运行的进程（跨会话恢复）
        running = detect_running_nodes(self.nodes_data)
        if running:
            for name, pid in running:
                self.node_list_panel.update_node_status(name, 'running')
                self.canvas.update_node_status(name, 'running')
            self.show_toast(f"检测到 {len(running)} 个节点在后台运行", "info")
        
    def mount_external_node(self):
        """挂载外部节点到当前项目
        
        通过选择节点文件夹识别文件夹内的 config.json 挂载到当前项目，
        自动创建以该节点根目录（绝对路径）命名的锁定组。
        """
        if not self.current_project_path:
            self.show_toast(t("k_project_no_project"), "warning")
            return

        # 选择外部节点文件夹
        folder_path = QFileDialog.getExistingDirectory(
            self, t("k_node_select_external"),
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )

        if not folder_path:
            return

        folder_path = os.path.abspath(folder_path)
        config_path = os.path.join(folder_path, "config.json")

        if not os.path.exists(config_path):
            self.show_toast(f"所选文件夹中未找到 config.json:\n{folder_path}", "warning")
            return

        # 读取 config.json
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            self.show_toast(f"读取 config.json 失败: {e}", "error")
            return

        node_name = config.get('node_name', os.path.basename(folder_path))

        # 检查是否已存在同名节点
        if node_name in self.nodes_data:
            self.show_toast(f"节点 '{node_name}' 已存在，无法重复挂载", "warning")
            return

        # 确定挂载根目录（节点的父目录绝对路径）
        mount_root = os.path.dirname(folder_path)
        mount_root = os.path.abspath(mount_root)

        # 注册到 nodes_data
        self.nodes_data[node_name] = {
            'config': config,
            'path': folder_path,
            'process': None,
            'status': 'stopped',
            'mounted': True,
            'mount_root': mount_root
        }

        # 同步到节点注册表（标记为外部挂载）
        try:
            registry = NodeRegistry(self.current_project_path)
            registry.load()
            registry.register_node(node_name, folder_path, mount_root=mount_root)
            registry.save()
            logger.info("挂载节点已注册: name=%s, path=%s, mount_root=%s",
                        node_name, folder_path, mount_root)
        except Exception as e:
            logger.warning("挂载节点注册表同步失败: %s", e)

        # 创建以挂载根目录命名的锁定组
        # 组名称使用绝对路径作为标识
        mount_group_name = mount_root
        if not self.node_list_panel.group_manager.groups.get(mount_group_name):
            self.node_list_panel.group_manager.create_group(mount_group_name, "#E67E22")
        self.node_list_panel.group_manager.add_nodes_to_group(mount_group_name, [node_name])
        self.node_list_panel.group_manager.lock_group(mount_group_name)

        # 刷新 UI
        self.node_list_panel.set_project_path(self.current_project_path)
        self.node_list_panel.update_node_list(self.nodes_data)
        self.canvas.sync_all_nodes_display()

        self.show_toast(f"已挂载外部节点: {node_name}", "success")
        logger.info("外部节点挂载完成: %s -> %s (group=%s)", node_name, folder_path, mount_group_name)

    def unmount_external_node(self, node_name: str):
        """卸载外部挂载节点

        Args:
            node_name: 要卸载的节点名称
        """
        if node_name not in self.nodes_data:
            return

        node_info = self.nodes_data[node_name]
        if not node_info.get('mounted'):
            self.show_toast(f"节点 '{node_name}' 不是外部挂载节点", "warning")
            return

        mount_root = node_info.get('mount_root')
        mount_group_name = mount_root

        # 从注册表注销
        try:
            registry = NodeRegistry(self.current_project_path)
            registry.load()
            registry.unregister_node(node_name)
            registry.save()
        except Exception:
            pass

        # 从组中移除
        if mount_group_name:
            self.node_list_panel.group_manager.remove_nodes_from_group(mount_group_name, [node_name])
            # 如果组内没有其他节点，解锁并删除组
            remaining = self.node_list_panel.group_manager.get_group_nodes(mount_group_name)
            if not remaining:
                self.node_list_panel.group_manager.unlock_group(mount_group_name)
                self.node_list_panel.group_manager.delete_group(mount_group_name)

        # 从数据中移除
        del self.nodes_data[node_name]

        # 刷新 UI
        self.node_list_panel.update_node_list(self.nodes_data)
        self.canvas.remove_node_from_canvas(node_name)

        self.show_toast(f"已卸载外部节点: {node_name}", "success")

    def create_new_node(self):
        """创建新节点（默认Python）"""
        self.create_new_node_with_language("Python")
    
    def create_new_node_with_language(self, language):
        """使用指定语言创建新节点（供菜单调用）"""
        if not self.current_project_path:
            self.show_toast(t("k_project_no_project"), "warning")
            return
        
        # 弹出对话框输入节点名称
        node_name, ok = QInputDialog.getText(
            self, t("k_node_create"), 
            f"请输入节点名称（{language}）:",
            QLineEdit.EchoMode.Normal
        )
        
        if not ok or not node_name:
            return
        
        # 映射语言标识
        lang_map = {
            "Python": "python",
            "Node.js": "nodejs",
            "Go": "go",
            "Java": "java",
            "C++": "cpp",
            "Rust": "rust",
            "Shell": "shell"
        }
        
        lang_key = lang_map.get(language, language.lower())
        
        # 检查是否支持该语言
        if not self.node_creator.has_creator(lang_key):
            self.show_toast(f"暂不支持创建 {language} 节点", "warning")
            logger.warning("未注册的语言创建器: %s, 当前支持: %s", lang_key, self.node_creator.get_supported_languages())
            return
        
        # 启动异步创建流程
        self._start_async_node_creation(node_name, lang_key, language)
    
    def _start_async_node_creation(self, node_name, lang_key, display_language):
        """启动异步节点创建流程（使用节点创建管理器）"""
        class NodeCreationWorker(QThread):
            """后台工作线程：负责创建节点"""
            progress_signal = pyqtSignal(str)  # 进度消息
            finished_signal = pyqtSignal(bool, str)  # (成功/失败, 消息)
            
            def __init__(self, project_path, node_name, lang_key, display_language):
                super().__init__()
                self.project_path = project_path
                self.node_name = node_name
                self.lang_key = lang_key
                self.display_language = display_language
            
            def run(self):
                try:
                    # 切换到项目 nodes 目录
                    original_cwd = os.getcwd()
                    nodes_dir = os.path.join(self.project_path, "nodes")
                    
                    if not os.path.exists(nodes_dir):
                        os.makedirs(nodes_dir)
                    
                    os.chdir(nodes_dir)
                    
                    try:
                        # 发送开始消息
                        self.progress_signal.emit(f"开始创建 {self.display_language} 节点...")
                        
                        # 获取节点创建管理器实例
                        manager = NodeCreatorManager.get_instance()
                        
                        # 调用对应的创建器
                        success = manager.create_node(self.lang_key, self.node_name)
                        
                        if success:
                            self.finished_signal.emit(True, f"{self.display_language} 节点 '{self.node_name}' 创建成功")
                        else:
                            self.finished_signal.emit(False, f"{self.display_language} 节点创建失败")
                    
                    finally:
                        # 恢复原始工作目录
                        os.chdir(original_cwd)
                        
                except Exception as e:
                    error_msg = f"创建节点异常: {str(e)}"
                    self.finished_signal.emit(False, error_msg)
                    import traceback
                    traceback.print_exc()
        
        # 创建浮动进度窗口（右上角）
        class ProgressFloatingWindow(QWidget):
            """右上角浮动进度窗口 - 非模态，不阻塞画布操作"""
            
            def __init__(self, parent=None):
                super().__init__(parent)
                
                # 设置窗口标志：无边框、工具窗口
                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint | 
                    Qt.WindowType.Tool
                )
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                
                # 创建布局
                layout = QVBoxLayout(self)
                layout.setContentsMargins(15, 10, 15, 10)
                
                # 标题标签
                self.title_label = QLabel(t("k_node_creating"))
                self.title_label.setStyleSheet("""
                    QLabel {
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 5px;
                    }
                """)
                layout.addWidget(self.title_label)
                
                # 进度消息标签
                self.message_label = QLabel(t("k_node_init"))
                self.message_label.setStyleSheet("""
                    QLabel {
                        color: rgba(255, 255, 255, 0.9);
                        font-size: 12px;
                        padding: 5px;
                    }
                """)
                layout.addWidget(self.message_label)
                
                # 设置背景样式
                self.setStyleSheet("""
                    QWidget {
                        background-color: rgba(33, 33, 33, 230);
                        border-radius: 8px;
                    }
                """)
                
                # 更新位置到右上角
                self.update_position()
            
            def update_position(self):
                """更新窗口位置到父窗口右上角"""
                if self.parent():
                    parent_rect = self.parent().geometry()
                    window_width = self.width() if self.width() > 0 else 250
                    window_height = self.height() if self.height() > 0 else 100
                    
                    x = parent_rect.right() - window_width - 20
                    y = parent_rect.top() + 40
                    
                    self.move(x, y)
        
        # 创建工作线程（保存为实例变量以便清理）
        self.node_creation_worker = NodeCreationWorker(
            self.current_project_path,
            node_name,
            lang_key,
            display_language
        )
        
        # 设置线程在父对象销毁时自动删除
        self.node_creation_worker.setParent(self)
        
        # 创建进度窗口
        progress_window = ProgressFloatingWindow(self)
        progress_window.show()
        
        # 连接信号
        def update_progress(message):
            if progress_window.isVisible():
                progress_window.message_label.setText(message)
        
        def creation_finished(success, message):
            # 确保在主线程中关闭窗口
            if progress_window.isVisible():
                progress_window.close()
            
            if success:
                self.show_toast(message, "success")
                # 刷新节点列表
                self.refresh_nodes()
            else:
                self.show_toast(message, "error")
        
        self.node_creation_worker.progress_signal.connect(update_progress)
        self.node_creation_worker.finished_signal.connect(creation_finished)
        
        # 启动线程
        self.node_creation_worker.start()
    
    def _on_node_creation_finished(self, success, message):
        """节点创建完成的回调"""
        # 关闭进度窗口
        if hasattr(self, 'progress_window'):
            self.progress_window.close()
        
        if success:
            self.show_toast(message, "success")
            # 刷新节点列表和画布
            self.refresh_nodes()
            self.canvas.sync_all_nodes_display()
        else:
            self.show_toast(message, "error")
        
        # 清理工作线程
        if hasattr(self, 'node_creation_worker'):
            self.node_creation_worker.quit()
            self.node_creation_worker.wait()
            del self.node_creation_worker
    
    def _on_node_creation_cancelled(self):
        """用户取消节点创建"""
        # 关闭进度窗口
        if hasattr(self, 'progress_window'):
            self.progress_window.close()
        
        self.show_toast(t("k_node_creation_cancelled"), "warning")
        
        # 终止工作线程
        if hasattr(self, 'node_creation_worker'):
            self.node_creation_worker.terminate()
            self.node_creation_worker.wait()
            del self.node_creation_worker
    
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
        """保存窗口状态 - 完整布局持久化"""
        try:
            # 1. 保存窗口几何信息（位置、尺寸、最大化状态）
            geometry = {
                "x": self.geometry().x(),
                "y": self.geometry().y(),
                "width": self.geometry().width(),
                "height": self.geometry().height(),
                "maximized": self.isMaximized()
            }
            self.app_config.set("window_geometry", geometry)
            
            # 2. 保存当前项目路径
            if self.current_project_path:
                self.app_config.set("last_project", self.current_project_path)
                
                # 4. 保存画布视图状态（缩放、滚动位置）
                view_state = {
                    "scale": self.canvas.transform().m11(),  # 获取缩放比例
                    "scroll_x": self.canvas.horizontalScrollBar().value(),
                    "scroll_y": self.canvas.verticalScrollBar().value()
                }
                self.app_config.set("canvas_view_state", view_state)
                
                # 5. 保存节点列表面板状态
                panel_state = {
                    "visible": self.node_list_panel.isVisible(),
                    "x": self.node_list_panel.geometry().x(),
                    "y": self.node_list_panel.geometry().y(),
                    "width": self.node_list_panel.geometry().width(),
                    "height": self.node_list_panel.geometry().height()
                }
                self.app_config.set("node_list_panel", panel_state)
                
                # 6. 保存画布布局（节点位置、连线）
                self.canvas.save_layout(self.current_project_path)
            
            # 7. 保存到文件
            self.app_config.save()
            
            logger.info("窗口状态已保存")
            
        except Exception as e:
            logger.error("保存窗口状态失败: %s", e)
    
    def restore_window_state(self):
        """恢复窗口状态 - 完整布局还原"""
        try:
            # 1. 恢复窗口几何信息
            geom = self.app_config.get("window_geometry")
            if geom:
                if geom.get("maximized", False):
                    self.showMaximized()
                else:
                    self.setGeometry(
                        geom.get("x", 100),
                        geom.get("y", 100),
                        geom.get("width", 1400),
                        geom.get("height", 900)
                    )
            
            # 2. 恢复节点列表面板状态
            panel_state = self.app_config.get("node_list_panel")
            if panel_state and hasattr(self, 'node_list_panel'):
                if isinstance(panel_state, dict):
                    # 恢复面板位置和大小
                    x = panel_state.get("x", 50)
                    y = panel_state.get("y", 100)
                    width = panel_state.get("width", 280)
                    height = panel_state.get("height", 600)
                    self.node_list_panel.setGeometry(x, y, width, height)
                    
                    # 恢复可见状态
                    visible = panel_state.get("visible", False)
                    if visible:
                        self.node_list_panel.show()
                        self.toggle_nodes_action.setChecked(True)
                    else:
                        self.node_list_panel.hide()
                        self.toggle_nodes_action.setChecked(False)
            
            logger.info("窗口状态已恢复")
            
        except Exception as e:
            logger.warning("恢复窗口状态失败，使用默认布局: %s", e)
    
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
