"""
CanvasHost - 画布宿主窗口（QMainWindow）

严格按PS布局设计：
1. 作为主窗口的中央控件，与左右Dock面板平级
2. 自身固定不动，内部全域作为画布专属Dock停靠区
3. 每个画布都是独立的BNOSDock，支持停靠、标签、悬浮、独立拖出
4. 与主窗口面板Dock完全隔离，永不混叠
5. 画布Dock强制停靠在顶部，标签页显示在顶部

【架构重构】新增空白缓冲层设计：
- 启动时显示空白缓冲层（BlankPlaceholder），无任何画布
- 用户新建/打开项目时才创建画布Dock
- 关闭所有画布后自动切回缓冲层
"""
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QTabWidget, QWidget, QVBoxLayout, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.core.logger import logger
from ui.core.i18n import t
from ui.canvas import NodeCanvas
from ui.core.bnos_dock import BnosDock


class BlankPlaceholder(QWidget):
    """空白缓冲层 - 纯空白占位，无任何业务逻辑"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI - 深色背景，中央显示提示文字"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 提示标签
        self._hint_label = QLabel(t("k_canvas_empty_hint"))
        self._hint_label.setStyleSheet("""
            QLabel {
                color: #4a4a4a;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint_label)
        
        # 设置深色背景
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)


class CanvasHost(QMainWindow):
    """画布宿主窗口 - 作为Canvas专属的Dock停靠容器（固定不动）"""
    
    canvas_changed = pyqtSignal(object)  # 当前激活的画布变化
    canvas_focused = pyqtSignal(object)  # 画布获得焦点
    all_canvases_closed = pyqtSignal()   # 所有画布已关闭
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent_window = parent
        
        # 核心配置：无边框样式，作为内嵌窗口使用
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # 画布Dock存储
        self._canvas_docks = []
        self._active_canvas = None
        
        # 空白缓冲层
        self._blank_placeholder = None
        
        # 初始化时显示空白缓冲层，不创建任何画布
        self._init_blank_placeholder()
        
        # 设置样式
        self._setup_styles()
    
    def _setup_styles(self):
        """设置CanvasHost样式 - 深色背景作为画布区域"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                border: none;
            }
        """)
    
    def _init_blank_placeholder(self):
        """初始化空白缓冲层 - 作为默认显示"""
        # 清空中央控件
        if self.centralWidget():
            self.centralWidget().deleteLater()
        
        # 创建空白缓冲层
        self._blank_placeholder = BlankPlaceholder(self)
        self.setCentralWidget(self._blank_placeholder)
        
        logger.info("CanvasHost: 已初始化空白缓冲层")
    
    def _remove_blank_placeholder(self):
        """移除空白缓冲层 - 在创建第一个画布时调用"""
        if self._blank_placeholder and self._blank_placeholder.isVisible():
            self.setCentralWidget(None)
            self._blank_placeholder.deleteLater()
            self._blank_placeholder = None
            
            # 启用Dock停靠功能（PS布局要求）
            self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)
            self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks)
            
            logger.info("CanvasHost: 空白缓冲层已移除，启用Dock停靠")
    
    def _create_canvas_dock(self, name=None, project_path=None):
        """创建独立的画布Dock - 每个画布都是独立的QDockWidget，强制停靠在顶部"""
        # 1. 如果还显示缓冲层，先移除
        if self._blank_placeholder:
            self._remove_blank_placeholder()
        
        # 2. 实例化原生NodeCanvas（完全不修改内部代码）
        canvas = NodeCanvas(self)
        canvas.parent_window = self._parent_window
        
        # 如果有项目路径，加载布局
        if project_path:
            canvas.load_layout(project_path)
        
        # 3. 用BNOSDock封装画布
        dock_name = name if name else f"{t('k_canvas')} {len(self._canvas_docks) + 1}"
        canvas_dock = BnosDock(dock_name, self)
        canvas_dock.set_content_widget(canvas)
        
        # 4. 设置画布Dock特性
        # - 可关闭：允许关闭画布
        # - 可移动：可在CanvasHost内部拖动（但仅限顶部区域）
        # - 可浮动：可脱离成为独立顶级窗口
        # - 禁用垂直标题栏：强制标题栏在顶部
        canvas_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
            # 不包含 DockWidgetVerticalTitleBar，强制标题栏在顶部
        )
        
        # 5. 关键设置：只允许停靠在顶部区域，禁止停靠到左右侧
        # 这样Qt会自动将多个画布Dock合并为顶部标签页
        canvas_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea)
        
        # 6. 将画布Dock添加到CanvasHost的顶部区域
        # Qt会自动将同一区域的多个Dock合并为标签页，标签显示在顶部
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, canvas_dock)
        
        # 7. 存储并设置为活动画布
        self._canvas_docks.append(canvas_dock)
        self._active_canvas = canvas
        
        # 8. 连接信号 - 监听关闭事件
        canvas_dock.closed.connect(lambda dock: self._on_canvas_dock_closed(dock))
        canvas_dock.visibilityChanged.connect(lambda visible, c=canvas: self._on_canvas_visibility_changed(visible, c))
        
        logger.info(f"CanvasHost: 画布Dock '{dock_name}' 已创建（顶部停靠）")
        return canvas_dock, canvas
    
    def _on_canvas_dock_closed(self, canvas_dock):
        """画布Dock关闭事件 - 彻底销毁画布、项目实例与节点进程"""
        if canvas_dock not in self._canvas_docks:
            return
        
        # 1. 获取画布内容
        canvas = canvas_dock.get_content_widget()
        
        # 2. 停止画布上所有节点进程（如果有）
        if canvas and hasattr(canvas, 'stop_all_nodes'):
            canvas.stop_all_nodes()
        
        # 3. 从列表中移除
        self._canvas_docks.remove(canvas_dock)
        
        # 4. 彻底销毁画布Dock
        self.removeDockWidget(canvas_dock)
        canvas_dock.deleteLater()
        
        # 5. 更新活动画布
        if self._canvas_docks:
            # 还有其他画布，激活下一个
            last_dock = self._canvas_docks[-1]
            self._active_canvas = last_dock.get_content_widget()
            self.canvas_changed.emit(self._active_canvas)
        else:
            # 所有画布都关闭了，回到空白缓冲层
            self._active_canvas = None
            self._init_blank_placeholder()
            self.all_canvases_closed.emit()
            
            logger.info("CanvasHost: 所有画布已关闭，恢复空白缓冲层")
        
        logger.info(f"CanvasHost: 画布Dock已彻底销毁，剩余画布数: {len(self._canvas_docks)}")
    
    def add_canvas_dock(self, name=None, project_path=None):
        """添加新的独立画布Dock"""
        canvas_dock, canvas = self._create_canvas_dock(name, project_path)
        
        # 更新活动画布
        self._active_canvas = canvas
        self.canvas_changed.emit(canvas)
        
        return canvas
    
    def _on_canvas_visibility_changed(self, visible, canvas):
        """画布可见性变化 - 触发焦点信号"""
        if visible and canvas:
            self._active_canvas = canvas
            self.canvas_focused.emit(canvas)
    
    def get_active_canvas(self):
        """获取当前活动画布"""
        return self._active_canvas
    
    def get_all_canvases(self):
        """获取所有画布"""
        canvases = []
        for dock in self._canvas_docks:
            content = dock.get_content_widget()
            if isinstance(content, NodeCanvas):
                canvases.append(content)
        return canvases
    
    def get_canvas_count(self):
        """获取画布数量"""
        return len(self._canvas_docks)
    
    def sync_project_data(self, project_path, nodes_data):
        """同步项目数据到所有画布"""
        for canvas in self.get_all_canvases():
            canvas.current_project_path = project_path
            if hasattr(canvas, 'nodes_data'):
                canvas.nodes_data = nodes_data
            canvas.refresh_nodes()
    
    def save_all_layouts(self, project_path):
        """保存所有画布布局"""
        for canvas in self.get_all_canvases():
            canvas.save_layout(project_path)
    
    def load_layout_for_active(self, project_path):
        """为活动画布加载布局"""
        if self._active_canvas:
            self._active_canvas.load_layout(project_path)
    
    def closeEvent(self, event):
        """关闭事件 - 保存所有画布布局"""
        if self._parent_window and self._parent_window.current_project_path:
            self.save_all_layouts(self._parent_window.current_project_path)
        super().closeEvent(event)
    
    def is_showing_placeholder(self):
        """是否显示空白缓冲层"""
        return self._blank_placeholder is not None