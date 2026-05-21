"""
BNOS 主窗口 - 包含完整的界面布局和核心功能
"""
import os
import sys
import json
import subprocess
import signal
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
from ui.core.dark_title_bar import DarkTitleBar
from PyQt6.QtWidgets import QMenuBar as _QMenuBar

from ui.canvas_widget import NodeCanvas
from ui.panels.node_list_panel import NodeListPanel
from ui.panels.property_panel import ColorSettingsDialog
from ui.creators.node_creator_manager import NodeCreatorManager
from ui.menu.menu_manager import MenuManager


class ToastNotification(QLabel):
    """右上角自动消失的通知弹窗（Toast）- 优化版
    
    使用高精度定时器实现流畅的60fps淡入淡出动画
    支持堆叠显示和自动位置调整
    显示在右上角，不干扰画布操作
    """
    
    def __init__(self, message, parent=None, duration=3000, toast_type="info", stack_index=0):
        super().__init__(message, parent)
        
        # 保存堆叠索引
        self.stack_index = stack_index
        
        # 设置基础样式
        base_style = """
            QLabel {
                background-color: rgba(50, 50, 50, 230);
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
        """
        
        # 根据类型调整颜色
        if toast_type == "success":
            base_style = base_style.replace("rgba(50, 50, 50, 230)", "rgba(76, 175, 80, 230)")
        elif toast_type == "warning":
            base_style = base_style.replace("rgba(50, 50, 50, 230)", "rgba(255, 152, 0, 230)")
        elif toast_type == "error":
            base_style = base_style.replace("rgba(50, 50, 50, 230)", "rgba(244, 67, 54, 230)")
        
        self.setStyleSheet(base_style)
        
        # 设置窗口属性（移除 WindowStaysOnTopHint 避免覆盖其他软件窗口）
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 调整大小以适应文本
        self.adjustSize()
        
        # 初始化透明度效果
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0)
        self.setGraphicsEffect(self.opacity_effect)
        
        # 动画参数
        self.duration = duration
        self.fade_duration = 300  # 淡入淡出时间（毫秒）
        self.current_opacity = 0.0
        self.is_fading_in = False
        self.is_fading_out = False
        
        # 使用高精度定时器实现平滑动画（60fps）
        self.animation_timer = QTimer(self)
        self.animation_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.animation_timer.timeout.connect(self.update_animation)
        
        # 停留计时器
        self.stay_timer = QTimer(self)
        self.stay_timer.setSingleShot(True)
        self.stay_timer.timeout.connect(self.start_fade_out)
    
    def show_toast(self):
        """显示通知并启动淡入动画"""
        self.adjustSize()
        
        if self.parent():
            parent_window = self.parent()
            window_pos = parent_window.pos()
            window_size = parent_window.size()
            
            x = window_pos.x() + window_size.width() - self.width() - 20
            y = window_pos.y() + 40 + (self.stack_index * 60)
            
            screen = QApplication.primaryScreen().geometry()
            max_y = screen.bottom() - self.height() - 10
            if y > max_y:
                y = max_y
        else:
            screen = QApplication.primaryScreen().geometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 40 + (self.stack_index * 60)
        
        self.move(x, y)
        self.show()
        
        # 启动淡入动画
        self.current_opacity = 0.0
        self.is_fading_in = True
        self.is_fading_out = False
        self.animation_timer.start(16)  # 16ms ≈ 60fps
    
    def update_animation(self):
        """更新动画帧 - 手动控制透明度实现流畅动画"""
        if self.is_fading_in:
            # 淡入动画：线性增加透明度
            self.current_opacity += 16.0 / self.fade_duration
            if self.current_opacity >= 1.0:
                self.current_opacity = 1.0
                self.is_fading_in = False
                self.opacity_effect.setOpacity(1.0)
                self.animation_timer.stop()
                
                # 开始停留计时（确保只启动一次）
                if not self.stay_timer.isActive():
                    self.stay_timer.start(self.duration)
            else:
                self.opacity_effect.setOpacity(self.current_opacity)
        
        elif self.is_fading_out:
            # 淡出动画：线性减少透明度
            self.current_opacity -= 16.0 / self.fade_duration
            if self.current_opacity <= 0.0:
                self.current_opacity = 0.0
                self.opacity_effect.setOpacity(0.0)
                self.animation_timer.stop()
                
                # 确保所有定时器都停止
                if self.stay_timer.isActive():
                    self.stay_timer.stop()
                
                # 延迟关闭，确保视觉效果完成
                QTimer.singleShot(50, self.close)
            else:
                self.opacity_effect.setOpacity(self.current_opacity)
    
    def update_position(self):
        """更新位置"""
        self.adjustSize()
        
        if self.parent():
            parent_window = self.parent()
            window_pos = parent_window.pos()
            window_size = parent_window.size()
            
            x = window_pos.x() + window_size.width() - self.width() - 20
            y = window_pos.y() + 40 + (self.stack_index * 60)
            
            screen = QApplication.primaryScreen().geometry()
            max_y = screen.bottom() - self.height() - 10
            if y > max_y:
                y = max_y
        else:
            screen = QApplication.primaryScreen().geometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 40 + (self.stack_index * 60)
        
        self.move(x, y)
    
    def start_fade_out(self):
        """开始淡出动画"""
        # 防止重复启动淡出
        if self.is_fading_out or self.is_fading_in:
            return
        
        self.is_fading_out = True
        self.animation_timer.start(16)  # 16ms ≈ 60fps

    def closeEvent(self, event):
        """窗口关闭事件 - 清理资源"""
        # 停止所有定时器
        self.animation_timer.stop()
        if self.stay_timer.isActive():
            self.stay_timer.stop()
        
        # 接受关闭事件
        event.accept()


class AppConfig:
    """应用配置管理 - 全局配置记忆系统"""
    
    def __init__(self):
        # 配置文件路径（程序根目录）
        self.config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "..", 
            "app_config.json"
        )
        
        # 默认配置
        self.config = {
            # 窗口布局持久化
            "window_geometry": {
                "x": 100,
                "y": 100,
                "width": 1400,
                "height": 900,
                "maximized": False
            },
            "splitter_sizes": [250, 1150],  # 左侧节点列表 + 右侧画布
            
            # 项目记忆
            "last_project": None,
            
            # 画布视图状态（最后的项目）
            "canvas_view_state": {
                "scale": 1.0,
                "scroll_x": 0,
                "scroll_y": 0
            }
        }
        
        # 加载配置
        self.load()
    
    def load(self):
        """加载配置 - 带异常处理"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    
                    # 合并配置（保留新字段的默认值）
                    for key in loaded:
                        if key in self.config:
                            if isinstance(self.config[key], dict) and isinstance(loaded[key], dict):
                                # 字典类型：深度合并
                                self.config[key].update(loaded[key])
                            else:
                                # 其他类型：直接覆盖
                                self.config[key] = loaded[key]
                                
                logger.info("配置已加载: %s", self.config_file)
            else:
                logger.info("配置文件不存在，使用默认配置")
                
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("配置文件损坏，重置为默认配置: %s", e)
            # 备份损坏的文件
            if os.path.exists(self.config_file):
                backup_file = self.config_file + ".bak"
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    logger.info("已备份损坏的配置: %s", backup_file)
                except:
                    pass
        except Exception as e:
            logger.error("加载配置失败: %s", e)
    
    def save(self):
        """保存配置 - 带异常处理"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                
            logger.info("配置已保存: %s", self.config_file)
            
        except Exception as e:
            logger.error("保存配置失败: %s", e)
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value


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
        self.node_list_panel.setWindowTitle("节点列表")
        
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
            self, "选择项目目录", "", 
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if not project_dir:
            return
        
        # 确认是否在项目目录下创建nodes子目录
        nodes_dir = os.path.join(project_dir, "nodes")
        if not os.path.exists(nodes_dir):
            reply = QMessageBox.question(
                self, "创建节点目录",
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
            self, "打开项目目录", "", 
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if not project_dir:
            return
        
        nodes_dir = os.path.join(project_dir, "nodes")
        if not os.path.exists(nodes_dir):
            reply = QMessageBox.question(
                self, "未找到节点目录",
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
            self.show_toast("请先打开或新建项目", "warning")
            return
        
        # 确保项目路径是绝对路径
        project_path = os.path.abspath(self.current_project_path)
        nodes_dir = os.path.join(project_path, "nodes")
        
        if not os.path.exists(nodes_dir):
            self.show_toast("nodes/ 目录不存在", "warning")
            return
        
        logger.info("刷新节点列表")
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
        
        # 更新节点组管理器的项目路径（自动加载配置）
        self.node_list_panel.set_project_path(self.current_project_path)
        
        # 更新节点列表面板
        self.node_list_panel.update_node_list(self.nodes_data)
        
        # 同步更新画布上的所有节点显示
        self.canvas.sync_all_nodes_display()
        
    def create_new_node(self):
        """创建新节点（默认Python）"""
        self.create_new_node_with_language("Python")
    
    def create_new_node_with_language(self, language):
        """使用指定语言创建新节点（供菜单调用）"""
        if not self.current_project_path:
            self.show_toast("请先打开或新建项目", "warning")
            return
        
        # 弹出对话框输入节点名称
        node_name, ok = QInputDialog.getText(
            self, "新建节点", 
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
                self.title_label = QLabel("创建节点")
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
                self.message_label = QLabel("正在初始化...")
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
        
        self.show_toast("节点创建已取消", "warning")
        
        # 终止工作线程
        if hasattr(self, 'node_creation_worker'):
            self.node_creation_worker.terminate()
            self.node_creation_worker.wait()
            del self.node_creation_worker
    
    def start_selected_node(self):
        """启动选中的节点（优先从画布获取，回退到节点列表）"""
        # 优先从画布获取选中节点
        selected_node = self.canvas.get_selected_node()
        
        # 如果画布未选中，回退到节点列表
        if not selected_node:
            selected_nodes = self.node_list_panel.get_selected_nodes()
            selected_node = selected_nodes[0] if selected_nodes else None
        
        if not selected_node:
            self.show_toast("请先在画布或节点列表中选择一个节点", "warning")
            return
        
        if selected_node not in self.nodes_data:
            self.show_toast(f"节点 {selected_node} 不存在", "error")
            return
        
        node_info = self.nodes_data[selected_node]
        if node_info['status'] == 'running':
            self.show_toast(f"节点 {selected_node} 已在运行中", "info")
            return
        
        # 启动节点进程 - 使用节点文件夹内的启动脚本
        node_path = node_info['path']
        
        # 确定启动脚本路径
        if os.name == 'nt':  # Windows
            start_script = os.path.join(node_path, "start.bat")
        else:  # Linux/Mac
            start_script = os.path.join(node_path, "start.sh")
        
        if not os.path.exists(start_script):
            QMessageBox.critical(self, "错误", f"启动脚本不存在: {start_script}")
            return
        
        try:
            # 启动进程 - 使用启动脚本
            if os.name == 'nt':
                # Windows: 使用 cmd /c 执行 bat 文件，传入 --no-pause 参数避免pause
                process = subprocess.Popen(
                    [start_script, "--no-pause"],
                    cwd=node_path,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac: 赋予执行权限并执行 shell 脚本，传入 --no-pause 参数
                os.chmod(start_script, 0o755)
                process = subprocess.Popen(
                    ["/bin/bash", start_script, "--no-pause"],
                    cwd=node_path,
                    start_new_session=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            node_info['process'] = process
            node_info['status'] = 'running'
            
            # 更新状态
            self.node_list_panel.update_node_status(selected_node, 'running')
            self.canvas.update_node_status(selected_node, 'running')
            
            self.show_toast(f"节点 {selected_node} 已启动", "success")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动节点失败: {str(e)}")
    
    def start_selected_node_by_name(self, node_name):
        """按名称启动节点（供对话框调用）"""
        if node_name not in self.nodes_data:
            return
        
        node_info = self.nodes_data[node_name]
        if node_info['status'] == 'running':
            self.show_toast("节点已在运行中", "info")
            return
        
        # 启动节点进程 - 使用节点文件夹内的启动脚本
        node_path = node_info['path']
        
        # 确定启动脚本路径
        if os.name == 'nt':  # Windows
            start_script = os.path.join(node_path, "start.bat")
        else:  # Linux/Mac
            start_script = os.path.join(node_path, "start.sh")
        
        if not os.path.exists(start_script):
            QMessageBox.critical(self, "错误", f"启动脚本不存在: {start_script}")
            return
        
        try:
            # 启动进程 - 使用启动脚本
            if os.name == 'nt':
                # Windows: 直接执行 bat 文件，传入 --no-pause 参数避免pause
                process = subprocess.Popen(
                    [start_script, "--no-pause"],
                    cwd=node_path,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac: 赋予执行权限并执行 shell 脚本，传入 --no-pause 参数
                os.chmod(start_script, 0o755)
                process = subprocess.Popen(
                    ["/bin/bash", start_script, "--no-pause"],
                    cwd=node_path,
                    start_new_session=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            
            node_info['process'] = process
            node_info['status'] = 'running'
            
            # 更新状态
            self.node_list_panel.update_node_status(node_name, 'running')
            self.canvas.update_node_status(node_name, 'running')
            
            self.show_toast(f"节点 {node_name} 已启动", "success")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动节点失败: {str(e)}")
    
    def stop_selected_node(self):
        """停止选中的节点（优先从画布获取，回退到节点列表）"""
        # 优先从画布获取选中节点
        selected_node = self.canvas.get_selected_node()
        
        # 如果画布未选中，回退到节点列表
        if not selected_node:
            selected_nodes = self.node_list_panel.get_selected_nodes()
            selected_node = selected_nodes[0] if selected_nodes else None
        
        if not selected_node:
            self.show_toast("请先在画布或节点列表中选择一个节点", "warning")
            return
        
        if selected_node not in self.nodes_data:
            self.show_toast(f"节点 {selected_node} 不存在", "error")
            return
        
        node_info = self.nodes_data[selected_node]
        if node_info['status'] == 'stopped':
            self.show_toast(f"节点 {selected_node} 未在运行", "info")
            return
        
        # 停止进程
        process = node_info['process']
        if process:
            try:
                if os.name == 'nt':
                    # Windows: 直接使用taskkill强制终止进程树（包括子进程）
                    try:
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                     capture_output=True, timeout=10)
                    except subprocess.TimeoutExpired:
                        # 如果 taskkill 超时，尝试直接 kill
                        try:
                            process.kill()
                            process.wait(timeout=3)
                        except:
                            pass
                    except Exception as e:
                        logger.error("taskkill执行失败: %s", e)
                        # 回退到直接终止
                        try:
                            process.kill()
                            process.wait(timeout=3)
                        except:
                            pass
                else:
                    # Linux/Mac: 终止整个进程组
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        process.wait(timeout=5)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        process.wait()
            except Exception as e:
                logger.error("停止节点时出错: %s", e)
                try:
                    process.kill()
                    process.wait()
                except:
                    pass
        
        node_info['process'] = None
        node_info['status'] = 'stopped'
        
        # 更新状态
        self.node_list_panel.update_node_status(selected_node, 'stopped')
        self.canvas.update_node_status(selected_node, 'stopped')
        
        self.show_toast(f"节点 {selected_node} 已停止", "success")
    
    def stop_selected_node_by_name(self, node_name):
        """按名称停止节点 - 强制关闭进程（供对话框调用）"""
        if node_name not in self.nodes_data:
            return
        
        node_info = self.nodes_data[node_name]
        if node_info['status'] == 'stopped':
            self.show_toast("节点未在运行", "info")
            return
        
        # ✅ 强制杀死进程
        process = node_info['process']
        if process:
            try:
                if process.poll() is None:  # 进程仍在运行
                    if os.name == 'nt':
                        # Windows: 使用taskkill强制终止进程树
                        try:
                            subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                         capture_output=True, timeout=10)
                        except Exception as e:
                            logger.error("taskkill执行失败: %s", e)
                            try:
                                process.kill()
                                process.wait(timeout=3)
                            except:
                                pass
                    else:
                        # Linux/Mac: 直接终止进程
                        try:
                            process.kill()
                            process.wait(timeout=3)
                        except Exception as e:
                            logger.error("强制终止进程时出错: %s", e)
                            try:
                                process.terminate()
                                process.wait(timeout=3)
                            except:
                                pass
            except Exception as e:
                logger.error("停止节点时出错: %s", e)
        
        node_info['process'] = None
        node_info['status'] = 'stopped'
        
        # 更新状态
        self.node_list_panel.update_node_status(node_name, 'stopped')
        self.canvas.update_node_status(node_name, 'stopped')
        
        self.show_toast(f"节点 {node_name} 已强制停止", "success")

    def clear_connections(self):
        """清空所有连线"""
        reply = QMessageBox.question(
            self, "确认", 
            "确定要清空所有连线吗？\n这将重置所有节点的 listen_upper_file 配置。",
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
        
        self.show_toast("已清空所有连线", "success")

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
                "检测到运行中的节点",
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
        """强制停止所有指定节点进程
        
        Args:
            node_names: 需要停止的节点名称列表
        """
        
        for node_name in node_names:
            if node_name not in self.nodes_data:
                continue
            
            node_info = self.nodes_data[node_name]
            process = node_info['process']
            
            if not process:
                continue
            
            try:
                if os.name == 'nt':
                    # Windows: 直接使用taskkill强制终止进程树（包括子进程）
                    try:
                        subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                     capture_output=True, timeout=10)
                    except subprocess.TimeoutExpired:
                        # 如果 taskkill 超时，尝试直接 kill
                        try:
                            process.kill()
                            process.wait(timeout=3)
                        except:
                            pass
                    except Exception as e:
                        logger.error("taskkill执行失败: %s", e)
                        # 回退到直接终止
                        try:
                            process.kill()
                            process.wait(timeout=3)
                        except:
                            pass
                else:
                    # Linux/Mac: 终止整个进程组
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        process.wait(timeout=3)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        process.wait()
                
                # 清理进程对象
                node_info['process'] = None
                node_info['status'] = 'stopped'
                
                logger.info("节点 %s 已停止", node_name)
                
            except Exception as e:
                logger.error("停止节点 %s 时出错: %s", node_name, e)
                # 即使出错也清理引用
                node_info['process'] = None
                node_info['status'] = 'stopped'
        
        # 更新UI状态
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
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; border: 2px solid #1e1e1e; }
            QWidget#centralWidget { background-color: #1e1e1e; border: none; }
            QScrollBar:horizontal, QScrollBar:vertical { background-color: #1e1e1e; border: none; }
            QScrollBar:horizontal { height: 10px; } QScrollBar:vertical { width: 10px; }
            QScrollBar::handle:horizontal, QScrollBar::handle:vertical { background-color: #424242; border-radius: 5px; min-width: 30px; min-height: 30px; }
            QScrollBar::handle:horizontal:hover, QScrollBar::handle:vertical:hover { background-color: #555555; }
            QScrollBar::add-line, QScrollBar::sub-line { width: 0px; height: 0px; }
            QScrollBar::add-page, QScrollBar::sub-page { background: none; }
            QDialog { background-color: #252526; color: #cccccc; }
            QMessageBox { background-color: #252526; color: #cccccc; }
            QLabel { color: #cccccc; }
            QLineEdit { background-color: #3c3c3c; color: #cccccc; border: 1px solid #555555; border-radius: 3px; padding: 4px 8px; }
            QLineEdit:focus { border-color: #007acc; }
            QComboBox { background-color: #3c3c3c; color: #cccccc; border: 1px solid #555555; border-radius: 3px; padding: 4px 8px; }
            QComboBox QAbstractItemView { background-color: #252526; color: #cccccc; selection-background-color: #094771; }
            QPushButton { background-color: #0e639c; color: white; border: 1px solid #0e639c; border-radius: 3px; padding: 6px 14px; }
            QPushButton:hover { background-color: #1177bb; }
            QPushButton:pressed { background-color: #094771; }
            QGroupBox { color: #cccccc; border: 1px solid #454545; border-radius: 4px; margin-top: 12px; padding-top: 18px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QTreeWidget { background-color: #252526; color: #cccccc; border: 1px solid #3c3c3c; alternate-background-color: #2d2d2d; }
            QTreeWidget::item:selected { background-color: #094771; } QTreeWidget::item:hover { background-color: #2a2d2e; }
            QHeaderView::section { background-color: #252526; color: #cccccc; border: none; border-right: 1px solid #3c3c3c; border-bottom: 1px solid #3c3c3c; padding: 4px 8px; }
            QTableWidget { background-color: #252526; color: #cccccc; border: 1px solid #3c3c3c; gridline-color: #3c3c3c; }
            QTableWidget::item:selected { background-color: #094771; }
            QTextEdit, QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: 1px solid #3c3c3c; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; }
            QTabWidget::pane { background-color: #1e1e1e; border: 1px solid #3c3c3c; }
            QTabBar::tab { background-color: #2d2d2d; color: #cccccc; padding: 8px 16px; border: none; border-right: 1px solid #3c3c3c; }
            QTabBar::tab:selected { background-color: #1e1e1e; border-top: 2px solid #007acc; } QTabBar::tab:hover { background-color: #3a3a3a; }
            QToolTip { background-color: #383838; color: #cccccc; border: 1px solid #555555; padding: 4px 8px; font-size: 12px; }
            QSplitter::handle { background-color: #3c3c3c; width: 2px; } QSplitter::handle:hover { background-color: #007acc; }
            QProgressBar { background-color: #3c3c3c; color: white; border: none; border-radius: 2px; text-align: center; }
            QProgressBar::chunk { background-color: #0e639c; border-radius: 2px; }
        """)
    
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 BNOS", 
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
