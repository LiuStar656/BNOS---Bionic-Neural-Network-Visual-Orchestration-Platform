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
    QInputDialog, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRectF, QTimer
from PyQt6.QtGui import QIcon, QFont, QPainter, QPen, QColor, QAction

from ui.canvas_widget import NodeCanvas
from ui.node_list_panel import NodeListPanel


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
        
        # 设置窗口属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
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
        # 先确保大小已调整
        self.adjustSize()
        
        # 计算位置：使用绝对屏幕坐标，固定在主窗口右上角
        if self.parent():
            # 获取主窗口在屏幕上的位置
            parent_window = self.parent()
            window_pos = parent_window.pos()
            window_size = parent_window.size()
            
            # 计算相对于窗口的右上角位置（使用绝对屏幕坐标）
            x = window_pos.x() + window_size.width() - self.width() - 20
            y = window_pos.y() + 100 + (self.stack_index * 60)  # 留出两层工具栏空间
            
            # 边界检测：确保Toast不会超出屏幕底部
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            max_y = screen.bottom() - self.height() - 10
            if y > max_y:
                y = max_y  # 限制在屏幕内
        else:
            # 如果没有父窗口，使用屏幕右上角
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 100 + (self.stack_index * 60)
        
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
        """更新位置（用于堆叠时的位置调整）"""
        # 重新调整大小以确保准确性
        self.adjustSize()
        
        # 计算位置：使用绝对屏幕坐标，固定在主窗口右上角
        if self.parent():
            # 获取主窗口在屏幕上的位置
            parent_window = self.parent()
            window_pos = parent_window.pos()
            window_size = parent_window.size()
            
            # 计算相对于窗口的右上角位置（使用绝对屏幕坐标）
            x = window_pos.x() + window_size.width() - self.width() - 20
            y = window_pos.y() + 100 + (self.stack_index * 60)  # 留出两层工具栏空间
            
            # 边界检测：确保Toast不会超出屏幕底部
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            max_y = screen.bottom() - self.height() - 10
            if y > max_y:
                y = max_y  # 限制在屏幕内
        else:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            x = screen.right() - self.width() - 20
            y = screen.top() + 100 + (self.stack_index * 60)
        
        # 平滑移动到新位置
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
                                
                print(f"✅ 配置已加载: {self.config_file}")
            else:
                print(f"ℹ️  配置文件不存在，使用默认配置")
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  配置文件损坏，重置为默认配置: {e}")
            # 备份损坏的文件
            if os.path.exists(self.config_file):
                backup_file = self.config_file + ".bak"
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    print(f"📦 已备份损坏的配置: {backup_file}")
                except:
                    pass
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
    
    def save(self):
        """保存配置 - 带异常处理"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                
            print(f"✅ 配置已保存: {self.config_file}")
            
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def get(self, key, default=None):
        """获取配置项"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项"""
        self.config[key] = value


class BNOSMainWindow(QMainWindow):
    """BNOS主窗口类"""
    
    def __init__(self):
        super().__init__()
        
        # 应用配置
        self.app_config = AppConfig()
        
        # 项目状态
        self.current_project_path = None
        self.nodes_data = {}  # {node_name: {config, path, process, status}}
        self.connections = []  # [(source_node, target_node)]
        
        # Toast通知队列管理
        self.active_toasts = []  # 当前显示的Toast列表
        
        # 初始化UI
        self.init_ui()
        self.init_toolbar()
        self.init_menu()
        
        # 恢复窗口状态
        self.restore_window_state()
        
        # 设置窗口属性
        self.setWindowTitle("BNOS 节点编排平台")
        
        # 自动打开最后的项目
        self.auto_open_last_project()
        
    def init_ui(self):
        """初始化主界面布局"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局 - 只包含画布
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 中间画布 - 节点编排（直接添加到主布局）
        self.canvas = NodeCanvas(self)
        main_layout.addWidget(self.canvas)
        
        # 创建节点列表面板（常驻半透明悬浮窗，默认显示）
        self.node_list_panel = NodeListPanel(self)
        self.node_list_panel.setWindowTitle("节点列表")
        # 默认显示，不再隐藏
        
        # 设置节点列表面板的初始位置和大小（窗口内部左上角区域）
        panel_width = 280
        panel_height = 500
        # 计算相对于屏幕的绝对位置
        window_pos = self.pos()
        panel_x = window_pos.x() + 20  # 主窗口左边 + 20px
        panel_y = window_pos.y() + 100  # 主窗口顶部 + 100px（留出两层工具栏空间）
        self.node_list_panel.setGeometry(panel_x, panel_y, panel_width, panel_height)
        self.node_list_panel.show()  # 默认显示
    
    def moveEvent(self, event):
        """窗口移动事件 - 更新节点列表和Toast位置"""
        super().moveEvent(event)
        
        # 更新节点列表面板位置（保持在窗口内部左上角）
        if hasattr(self, 'node_list_panel') and self.node_list_panel.isVisible():
            # 计算相对于屏幕的绝对位置
            # 获取主窗口在屏幕上的位置
            window_pos = self.pos()
            # 节点列表应该在主窗口内部的左上角
            panel_x = window_pos.x() + 20  # 主窗口左边 + 20px
            panel_y = window_pos.y() + 100  # 主窗口顶部 + 100px（留出两层工具栏）
            self.node_list_panel.move(panel_x, panel_y)
        
        # 更新所有Toast的位置
        if hasattr(self, 'active_toasts'):
            for toast in self.active_toasts:
                toast.update_position()
    
    def resizeEvent(self, event):
        """窗口大小改变事件 - 更新节点列表和Toast位置"""
        super().resizeEvent(event)
        
        # 更新节点列表面板位置（保持在窗口内部左上角）
        if hasattr(self, 'node_list_panel') and self.node_list_panel.isVisible():
            # 计算相对于屏幕的绝对位置
            # 获取主窗口在屏幕上的位置
            window_pos = self.pos()
            # 节点列表应该在主窗口内部的左上角
            panel_x = window_pos.x() + 20  # 主窗口左边 + 20px
            panel_y = window_pos.y() + 100  # 主窗口顶部 + 100px（留出两层工具栏）
            self.node_list_panel.move(panel_x, panel_y)
        
        # 更新所有Toast的位置
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
    
    def init_toolbar(self):
        """初始化工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # 文件操作
        new_project_action = QAction("新建项目", self)
        new_project_action.triggered.connect(self.new_project)
        toolbar.addAction(new_project_action)
        
        open_project_action = QAction("打开项目", self)
        open_project_action.triggered.connect(self.open_project)
        toolbar.addAction(open_project_action)
        
        toolbar.addSeparator()
        
        # 视图控制 - 节点列表开关
        toggle_nodes_action = QAction("📋 节点列表", self)
        toggle_nodes_action.setCheckable(True)
        toggle_nodes_action.setToolTip("显示/隐藏节点列表面板")
        toggle_nodes_action.triggered.connect(self.toggle_node_list_panel)
        toolbar.addAction(toggle_nodes_action)
        self.toggle_nodes_action = toggle_nodes_action
        
        toolbar.addSeparator()
        
        # 颜色设置
        color_settings_action = QAction("🎨 颜色设置", self)
        color_settings_action.setToolTip("自定义画布和节点颜色")
        color_settings_action.triggered.connect(self.open_color_settings)
        toolbar.addAction(color_settings_action)
        
        toolbar.addSeparator()
        
        # 节点操作
        refresh_action = QAction("刷新节点", self)
        refresh_action.triggered.connect(self.refresh_nodes)
        toolbar.addAction(refresh_action)
        
        clear_connections_action = QAction("清空连线", self)
        clear_connections_action.triggered.connect(self.clear_connections)
        toolbar.addAction(clear_connections_action)
        
        toolbar.addSeparator()
        
        # 新建节点
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Python", "Node.js", "Go", "Java", "C++", "Rust", "Shell"])
        self.language_combo.setCurrentText("Python")
        toolbar.addWidget(QLabel("语言:"))
        toolbar.addWidget(self.language_combo)
        
        create_node_action = QAction("新建节点", self)
        create_node_action.triggered.connect(self.create_new_node)
        toolbar.addAction(create_node_action)
        
        toolbar.addSeparator()
        
        # 节点控制
        start_node_action = QAction("启动节点", self)
        start_node_action.triggered.connect(self.start_selected_node)
        toolbar.addAction(start_node_action)
        
        stop_node_action = QAction("停止节点", self)
        stop_node_action.triggered.connect(self.stop_selected_node)
        toolbar.addAction(stop_node_action)
        
    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_project_action = file_menu.addAction("新建项目")
        new_project_action.triggered.connect(self.new_project)
        
        open_project_action = file_menu.addAction("打开项目")
        open_project_action.triggered.connect(self.open_project)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("退出")
        exit_action.triggered.connect(self.close)
        
        # 编辑菜单
        edit_menu = menubar.addMenu("编辑")
        
        refresh_action = edit_menu.addAction("刷新节点")
        refresh_action.triggered.connect(self.refresh_nodes)
        
        clear_action = edit_menu.addAction("清空连线")
        clear_action.triggered.connect(self.clear_connections)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        about_action = help_menu.addAction("关于")
        about_action.triggered.connect(self.show_about)
    
    def toggle_node_list_panel(self, checked):
        """切换节点列表面板的显示/隐藏"""
        if checked:
            self.node_list_panel.show()
            self.node_list_panel.raise_()
            self.node_list_panel.activateWindow()
        else:
            self.node_list_panel.hide()
    
    def open_color_settings(self):
        """打开颜色设置对话框"""
        from ui.property_panel import ColorSettingsDialog
        
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
        
        nodes_dir = os.path.join(self.current_project_path, "nodes")
        if not os.path.exists(nodes_dir):
            self.show_toast("nodes/ 目录不存在", "warning")
            return
        
        # 扫描节点
        self.nodes_data.clear()
        for item in os.listdir(nodes_dir):
            node_path = os.path.join(nodes_dir, item)
            if not os.path.isdir(node_path):
                continue
            
            config_path = os.path.join(node_path, "config.json")
            if not os.path.exists(config_path):
                continue
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                node_name = config.get('node_name', item)
                self.nodes_data[node_name] = {
                    'config': config,
                    'path': node_path,
                    'process': None,
                    'status': 'stopped'
                }
            except Exception as e:
                print(f"加载节点 {item} 失败: {e}")
        
        # 更新节点组管理器的项目路径（自动加载配置）
        self.node_list_panel.set_project_path(self.current_project_path)
        
        # 更新节点列表面板
        self.node_list_panel.update_node_list(self.nodes_data)
        
        # 同步更新画布上的所有节点显示
        self.canvas.sync_all_nodes_display()
        
    def create_new_node(self):
        """创建新节点（异步方式，避免UI卡顿）"""
        if not self.current_project_path:
            self.show_toast("请先打开或新建项目", "warning")
            return
        
        language = self.language_combo.currentText()
        
        # 弹出对话框输入节点名称
        node_name, ok = QInputDialog.getText(
            self, "新建节点", 
            "请输入节点名称:",
            QLineEdit.EchoMode.Normal
        )
        
        if not ok or not node_name:
            return
        
        # 检查节点是否已存在
        base_dir = os.path.join(self.current_project_path, "nodes")
        node_dir = os.path.join(base_dir, f"node_{node_name}")
        
        if os.path.exists(node_dir):
            self.show_toast(f"节点 {node_name} 已存在", "warning")
            return
        
        # 启动异步创建流程
        self._start_async_node_creation(node_name, language)
    
    def _start_async_node_creation(self, node_name, language):
        """启动异步节点创建流程"""
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import QThread, pyqtSignal
        
        class NodeCreationWorker(QThread):
            """后台工作线程：负责创建节点"""
            progress_signal = pyqtSignal(str)  # 进度消息
            finished_signal = pyqtSignal(bool, str)  # (成功/失败, 消息)
            
            def __init__(self, project_path, node_name, language):
                super().__init__()
                self.project_path = project_path
                self.node_name = node_name
                self.language = language
            
            def run(self):
                try:
                    import sys
                    import json
                    import subprocess
                    
                    # 获取软件根目录
                    software_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    
                    # 导入create_node模块
                    import importlib.util
                    create_node_path = os.path.join(software_root, "create_node.py")
                    
                    if not os.path.exists(create_node_path):
                        self.finished_signal.emit(False, f"找不到create_node.py: {create_node_path}")
                        return
                    
                    spec = importlib.util.spec_from_file_location("create_node", create_node_path)
                    create_node = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(create_node)
                    
                    # 步骤1：创建目录结构
                    self.progress_signal.emit("📁 创建目录结构...")
                    base_dir = os.path.join(self.project_path, "nodes")
                    node_dir = os.path.join(base_dir, f"node_{self.node_name}")
                    
                    if os.path.exists(node_dir):
                        self.finished_signal.emit(False, f"节点 {self.node_name} 已存在")
                        return
                    
                    os.makedirs(node_dir)
                    os.makedirs(os.path.join(node_dir, "logs"))
                    
                    # 步骤2：创建虚拟环境（最耗时的操作）
                    self.progress_signal.emit("🔧 创建虚拟环境（可能需要10-30秒）...")
                    venv_path = os.path.join(node_dir, "venv")
                    result = subprocess.run(
                        [sys.executable, "-m", "venv", venv_path],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    
                    # 步骤3：创建配置文件
                    self.progress_signal.emit("⚙️ 生成配置文件...")
                    
                    # requirements.txt
                    with open(os.path.join(node_dir, "requirements.txt"), "w", encoding="utf-8") as f:
                        f.write("# 在此添加节点依赖\n")
                    
                    # config.json
                    config = {
                        "node_name": f"node_{self.node_name}",
                        "listen_upper_file": "../data/upper_data.json",
                        "output_file": "./output.json",
                        "filter": {},
                        "output_type": ""
                    }
                    with open(os.path.join(node_dir, "config.json"), "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    
                    # packet.py
                    packet = '''UPPER_PACKET = {"data": None}
OUTPUT_PACKET = {"code": 0, "data": None}
'''
                    with open(os.path.join(node_dir, "packet.py"), "w", encoding="utf-8") as f:
                        f.write(packet.strip())
                    
                    # listener.py
                    listener = '''import os
import json
import time
import subprocess
from datetime import datetime

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(NODE_DIR, "config.json")
LOG_DIR = os.path.join(NODE_DIR, "logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def log(msg, level="INFO"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] [{level}] {msg}"
    print(line)
    with open(os.path.join(LOG_DIR, "listener.log"), "a", encoding="utf-8") as f:
        f.write(line + "\\n")

try:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
except Exception as e:
    log(f"配置加载失败: {e}", "ERROR")
    exit(1)

UPPER_FILE = os.path.abspath(os.path.join(NODE_DIR, cfg["listen_upper_file"]))
OUTPUT_FILE = os.path.abspath(os.path.join(NODE_DIR, cfg["output_file"]))
NODE_NAME = cfg["node_name"]
MY_FILTER = cfg.get("filter", {})
PROCESS_FLAG = f"_processed_{NODE_NAME}"

def is_my_data(data):
    if not MY_FILTER:
        return True
    for k, v in MY_FILTER.items():
        if data.get(k) != v:
            return False
    return True

log("=" * 50)
log(f"节点启动: {NODE_NAME}")
log(f"监听: {UPPER_FILE}")
log(f"过滤: {MY_FILTER}")
log("当前环境: 独立虚拟环境")
log("=" * 50)

while True:
    try:
        if not os.path.exists(UPPER_FILE):
            time.sleep(0.2)
            continue

        with open(UPPER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get(PROCESS_FLAG):
            time.sleep(0.2)
            continue

        if not is_my_data(data):
            time.sleep(0.2)
            continue

        log("✅ 开始处理数据")

        # 【关键】只用自己虚拟环境运行 main.py
        if os.name == "nt":
            py_path = os.path.join(NODE_DIR, "venv", "Scripts", "python.exe")
        else:
            py_path = os.path.join(NODE_DIR, "venv", "bin", "python")

        res = subprocess.run(
            [py_path, os.path.join(NODE_DIR, "main.py"), json.dumps(data)],
            capture_output=True, text=True, encoding="utf-8"
        )

        output = res.stdout.strip()
        if not output:
            log("⚠️ 返回空数据")
            continue

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output)

        data[PROCESS_FLAG] = True
        with open(UPPER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        log(f"✅ 处理完成: {PROCESS_FLAG}")

    except json.JSONDecodeError:
        log("❌ 数据包格式错误", "ERROR")
        time.sleep(1)
    except Exception as e:
        log(f"❌ 异常: {e}", "ERROR")
        time.sleep(1)

    time.sleep(0.2)
'''
                    with open(os.path.join(node_dir, "listener.py"), "w", encoding="utf-8") as f:
                        f.write(listener.strip())
                    
                    # main.py
                    main = '''import sys
import json
import os

NODE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(NODE_DIR, "config.json")
with open(config_path, "r", encoding="utf-8") as f:
    cfg = json.load(f)

def process(data):
    return data.get("data")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"code": -1, "error": "no input"}))
        sys.exit(1)

    input_data = json.loads(sys.argv[1])
    result = process(input_data)

    print(json.dumps({
        "code": 0,
        "type": cfg["output_type"],
        "data": result
    }, ensure_ascii=False))
'''
                    with open(os.path.join(node_dir, "main.py"), "w", encoding="utf-8") as f:
                        f.write(main.strip())
                    
                    # output.json
                    with open(os.path.join(node_dir, "output.json"), "w", encoding="utf-8") as f:
                        f.write('{"code":0,"data":null}')
                    
                    # 自动生成启动脚本
                    if os.name == "nt":
                        start_bat = '''@echo off
cls
echo ======================================
echo        BNOS Node Starter (Windows)
echo ======================================
echo.
cd /d "%~dp0"
chmp 65001 >nul
if not exist "venv\\Scripts\\python.exe" (
    echo ❌ 虚拟环境不存在！
    pause
    exit /b 1
)
call venv\\Scripts\\activate.bat
echo ✅ 启动监听程序...
echo.
venv\\Scripts\\python.exe listener.py
echo.
echo ❌ 程序已退出
pause
'''
                        with open(os.path.join(node_dir, "start.bat"), "w", encoding="utf-8") as f:
                            f.write(start_bat)
                    else:
                        start_sh = '''#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python3 listener.py
'''
                        with open(os.path.join(node_dir, "start.sh"), "w", encoding="utf-8") as f:
                            f.write(start_sh)
                        os.chmod(os.path.join(node_dir, "start.sh"), 0o755)
                    
                    self.progress_signal.emit("✅ 节点创建完成！")
                    self.finished_signal.emit(True, f"节点 {self.node_name} 创建成功")
                    
                except subprocess.CalledProcessError as e:
                    error_msg = f"创建虚拟环境失败: {e.stderr}"
                    self.finished_signal.emit(False, error_msg)
                except Exception as e:
                    error_msg = f"创建节点失败: {str(e)}"
                    import traceback
                    traceback.print_exc()
                    self.finished_signal.emit(False, error_msg)
        
        # 创建工作线程
        self.node_creation_worker = NodeCreationWorker(
            self.current_project_path, 
            node_name, 
            language
        )
        
        # 创建非模态进度提示窗口（右上角浮动）
        from PyQt6.QtWidgets import QWidget, QVBoxLayout
        from PyQt6.QtCore import Qt
        
        class ProgressFloatingWindow(QWidget):
            """右上角浮动进度窗口 - 非模态，不阻塞画布操作"""
            
            def __init__(self, parent=None):
                super().__init__(parent)
                
                # 设置窗口标志：无边框、置顶、工具窗口
                self.setWindowFlags(
                    Qt.WindowType.FramelessWindowHint | 
                    Qt.WindowType.Tool | 
                    Qt.WindowType.WindowStaysOnTopHint
                )
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                
                # 创建布局
                layout = QVBoxLayout(self)
                layout.setContentsMargins(15, 10, 15, 10)
                
                # 标题标签
                self.title_label = QLabel("🔧 创建节点")
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
                
                # 取消按钮
                self.cancel_button = QPushButton("取消")
                self.cancel_button.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(244, 67, 54, 200);
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 15px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: rgba(244, 67, 54, 230);
                    }
                """)
                layout.addWidget(self.cancel_button)
                
                # 设置背景样式
                self.setStyleSheet("""
                    QWidget {
                        background-color: rgba(50, 50, 50, 230);
                        border-radius: 8px;
                    }
                """)
                
                # 调整大小
                self.adjustSize()
                
                # 设置固定最小宽度
                self.setMinimumWidth(250)
        
        # 创建进度窗口实例
        self.progress_window = ProgressFloatingWindow(self)
        
        # 设置窗口位置到右上角（距离右边缘20px，距离顶部80px）
        if self.geometry():
            parent_rect = self.geometry()
            window_width = self.progress_window.width()
            window_height = self.progress_window.height()
            x = parent_rect.right() - window_width - 20
            y = parent_rect.top() + 80  # 留出工具栏空间
            self.progress_window.move(x, y)
        
        # 连接信号
        self.node_creation_worker.progress_signal.connect(
            self.progress_window.message_label.setText
        )
        self.node_creation_worker.finished_signal.connect(
            self._on_node_creation_finished
        )
        self.progress_window.cancel_button.clicked.connect(
            self._on_node_creation_cancelled
        )
        
        # 启动工作线程
        self.node_creation_worker.start()
        self.progress_window.show()
    
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
        
        # 启动节点进程 - 直接执行Python命令而非批处理脚本
        node_path = node_info['path']
        
        # 确定虚拟环境的Python解释器路径
        if os.name == 'nt':  # Windows
            python_exe = os.path.join(node_path, "venv", "Scripts", "python.exe")
        else:  # Linux/Mac
            python_exe = os.path.join(node_path, "venv", "bin", "python")
        
        listener_script = os.path.join(node_path, "listener.py")
        
        if not os.path.exists(python_exe):
            QMessageBox.critical(self, "错误", f"虚拟环境不存在: {python_exe}")
            return
        
        if not os.path.exists(listener_script):
            QMessageBox.critical(self, "错误", f"监听脚本不存在: {listener_script}")
            return
        
        try:
            # 启动进程 - 直接运行Python，不使用shell
            if os.name == 'nt':
                # Windows: 创建新的进程组以便后续可以终止整个进程树
                process = subprocess.Popen(
                    [python_exe, listener_script],
                    cwd=node_path,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac: 使用进程组
                process = subprocess.Popen(
                    [python_exe, listener_script],
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
        
        # 启动节点进程 - 直接执行Python命令而非批处理脚本
        node_path = node_info['path']
        
        # 确定虚拟环境的Python解释器路径
        if os.name == 'nt':  # Windows
            python_exe = os.path.join(node_path, "venv", "Scripts", "python.exe")
        else:  # Linux/Mac
            python_exe = os.path.join(node_path, "venv", "bin", "python")
        
        listener_script = os.path.join(node_path, "listener.py")
        
        if not os.path.exists(python_exe):
            QMessageBox.critical(self, "错误", f"虚拟环境不存在: {python_exe}")
            return
        
        if not os.path.exists(listener_script):
            QMessageBox.critical(self, "错误", f"监听脚本不存在: {listener_script}")
            return
        
        try:
            # 启动进程 - 直接运行Python，不使用shell
            if os.name == 'nt':
                # Windows: 创建新的进程组以便后续可以终止整个进程树
                process = subprocess.Popen(
                    [python_exe, listener_script],
                    cwd=node_path,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                # Linux/Mac: 使用进程组
                process = subprocess.Popen(
                    [python_exe, listener_script],
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
                    # Windows: 先尝试优雅终止
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # 如果超时，强制杀死进程及其子进程
                        import signal
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                else:
                    # Linux/Mac: 终止整个进程组
                    import signal
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        process.wait(timeout=5)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        process.wait()
            except Exception as e:
                print(f"停止节点时出错: {e}")
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
        """按名称停止节点（供对话框调用）"""
        if node_name not in self.nodes_data:
            return
        
        node_info = self.nodes_data[node_name]
        if node_info['status'] == 'stopped':
            self.show_toast("节点未在运行", "info")
            return
        
        # 停止进程
        process = node_info['process']
        if process:
            try:
                if os.name == 'nt':
                    # Windows: 先尝试优雅终止
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # 如果超时，强制杀死进程及其子进程
                        import signal
                        process.send_signal(signal.CTRL_BREAK_EVENT)
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                else:
                    # Linux/Mac: 终止整个进程组
                    import signal
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        process.wait(timeout=5)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        process.wait()
            except Exception as e:
                print(f"停止节点时出错: {e}")
                try:
                    process.kill()
                    process.wait()
                except:
                    pass
        
        node_info['process'] = None
        node_info['status'] = 'stopped'
        
        # 更新状态
        self.node_list_panel.update_node_status(node_name, 'stopped')
        self.canvas.update_node_status(node_name, 'stopped')
        
        self.show_toast(f"节点 {node_name} 已停止", "success")

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
        # 保存当前项目布局
        if self.current_project_path:
            self.canvas.save_layout(self.current_project_path)
        
        # 保存应用配置
        self.save_window_state()
        self.app_config.set("last_project", self.current_project_path)
        self.app_config.save()
        
        # 停止所有运行中的节点
        for node_name, node_info in self.nodes_data.items():
            if node_info['status'] == 'running' and node_info['process']:
                try:
                    node_info['process'].terminate()
                    node_info['process'].wait(timeout=3)
                except:
                    pass
        
        event.accept()
    
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
            
            print("✅ 窗口状态已保存")
            
        except Exception as e:
            print(f"⚠️  保存窗口状态失败: {e}")
    
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
            
            print("✅ 窗口状态已恢复")
            
        except Exception as e:
            print(f"⚠️  恢复窗口状态失败，使用默认布局: {e}")
    
    def auto_open_last_project(self):
        """自动打开最后的项目 - 只加载数据，不自动添加节点到画布"""
        last_project = self.app_config.get("last_project")
        if last_project and os.path.exists(last_project):
            nodes_dir = os.path.join(last_project, "nodes")
            if os.path.exists(nodes_dir):
                self.current_project_path = last_project
                
                print(f"📂 自动打开项目: {last_project}")
                
                # 1. 刷新节点列表（加载所有节点数据）
                self.refresh_nodes()
                
                # 2. 加载画布布局（包含节点位置、连线关系、视图状态的完整恢复）
                self.canvas.load_layout(last_project)
    
    def show_about(self):
        """显示关于对话框"""
