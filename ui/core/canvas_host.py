"""
CanvasHost - 画布宿主窗口（QMainWindow）

严格按PS布局设计：
1. 作为主窗口的中央控件，与左右Dock面板平级
2. 自身固定不动，内部全域作为画布专属Dock停靠区
3. 每个画布都是独立的BNOSDock，支持停靠、标签、悬浮、独立拖出
4. 与主窗口面板Dock完全隔离，永不混叠
5. 画布Dock强制停靠在顶部，标签页显示在顶部
"""
from PyQt6.QtWidgets import (
    QMainWindow, QDockWidget, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.core.logger import logger
from ui.core.i18n import t
from ui.canvas import NodeCanvas
from ui.core.bnos_dock import BnosDock


class CanvasHost(QMainWindow):
    """画布宿主窗口 - 作为Canvas专属的Dock停靠容器（固定不动）"""
    
    canvas_changed = pyqtSignal(object)  # 当前激活的画布变化
    canvas_focused = pyqtSignal(object)  # 画布获得焦点
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent_window = parent
        
        # 核心配置：无边框样式，作为内嵌窗口使用
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # 关键设置：清空中央控件，使CanvasHost内部全域成为画布Dock的停靠区
        self.setCentralWidget(None)
        
        # 强制Dock标签页显示在顶部（PS布局要求）
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks)
        
        # 画布Dock存储
        self._canvas_docks = []
        self._active_canvas = None
        
        # 初始化时创建默认画布Dock
        self._create_canvas_dock()
        
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
    
    def _create_canvas_dock(self, name=None, project_path=None):
        """创建独立的画布Dock - 每个画布都是独立的QDockWidget，强制停靠在顶部"""
        # 1. 实例化原生NodeCanvas（完全不修改内部代码）
        canvas = NodeCanvas(self)
        canvas.parent_window = self._parent_window
        
        # 如果有项目路径，加载布局
        if project_path:
            canvas.load_layout(project_path)
        
        # 2. 用BNOSDock封装画布
        dock_name = name if name else f"{t('k_canvas')} {len(self._canvas_docks) + 1}"
        canvas_dock = BnosDock(dock_name, self)
        canvas_dock.set_content_widget(canvas)
        
        # 3. 设置画布Dock特性
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
        
        # 4. 关键设置：只允许停靠在顶部区域，禁止停靠到左右侧
        # 这样Qt会自动将多个画布Dock合并为顶部标签页
        canvas_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea)
        
        # 5. 将画布Dock添加到CanvasHost的顶部区域
        # Qt会自动将同一区域的多个Dock合并为标签页，标签显示在顶部
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, canvas_dock)
        
        # 6. 存储并设置为活动画布
        self._canvas_docks.append(canvas_dock)
        self._active_canvas = canvas
        
        # 7. 连接信号
        canvas_dock.visibilityChanged.connect(lambda visible: self._on_canvas_visibility_changed(visible, canvas))
        
        logger.info(f"CanvasHost: 画布Dock '{dock_name}' 已创建（顶部停靠）")
        return canvas_dock, canvas
    
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