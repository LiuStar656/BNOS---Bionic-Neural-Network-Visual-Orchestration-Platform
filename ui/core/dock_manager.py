"""
面板停靠管理器 - 类似PS的面板停靠系统
支持面板吸附边缘停靠，并自动调整画布区域
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QToolButton, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont
from ui.core.i18n import t
from ui.icons.codicon import get_icon, get_icon_font


class DockPanel(QWidget):
    """可停靠面板"""
    
    close_requested = pyqtSignal(object)
    
    def __init__(self, widget, title, parent=None):
        super().__init__(parent)
        self._widget = widget
        self._title = title
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 标题栏
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: rgba(40, 40, 40, 200);")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 4, 4, 4)
        title_layout.setSpacing(4)
        
        # 标题
        title_label = QLabel(self._title)
        title_label.setStyleSheet("color: #858585; font-size: 11px;")
        title_layout.addWidget(title_label)
        
        # 分隔线
        spacer = QWidget()
        spacer.setFixedWidth(1)
        spacer.setStyleSheet("background-color: rgba(255, 255, 255, 15);")
        title_layout.addWidget(spacer)
        
        # 关闭按钮
        close_btn = QToolButton()
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setText(get_icon('x'))
        close_btn.setFont(get_icon_font(12))
        close_btn.setStyleSheet("""
            QToolButton {
                color: #858585;
                border: none;
                padding: 2px;
            }
            QToolButton:hover {
                color: #d4d4d4;
                background-color: rgba(255, 255, 255, 10);
            }
        """)
        close_btn.clicked.connect(lambda: self.close_requested.emit(self))
        title_layout.addWidget(close_btn)
        
        layout.addWidget(title_bar)
        
        # 内容区域
        self._widget.setParent(self)
        layout.addWidget(self._widget, 1)
    
    def get_widget(self):
        """获取内部组件"""
        return self._widget


class DockManager(QWidget):
    """面板停靠管理器"""
    
    panel_closed = pyqtSignal(QWidget)
    dock_changed = pyqtSignal(str, bool)  # edge, is_docked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent_window = parent
        
        # 停靠区域
        self._left_dock = None
        self._right_dock = None
        self._bottom_dock = None
        
        # 当前停靠状态
        self._docked_edges = set()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 主分割器
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setContentsMargins(0, 0, 0, 0)
        self._main_splitter.setStyleSheet("QSplitter { background-color: #1e1e1e; }")
        self._main_splitter.setHandleWidth(1)
        
        # 左侧停靠区域
        self._left_area = QWidget()
        self._left_area.setFixedWidth(0)
        self._left_area.setStyleSheet("background-color: #252526;")
        self._left_layout = QVBoxLayout(self._left_area)
        self._left_layout.setContentsMargins(0, 0, 0, 0)
        self._left_layout.setSpacing(0)
        self._main_splitter.addWidget(self._left_area)
        
        # 中央内容区域（用于放置编辑器）
        self._center_area = QWidget()
        self._center_area.setStyleSheet("background-color: #1e1e1e;")
        self._center_layout = QVBoxLayout(self._center_area)
        self._center_layout.setContentsMargins(0, 0, 0, 0)
        self._center_layout.setSpacing(0)
        self._main_splitter.addWidget(self._center_area)
        
        # 右侧停靠区域
        self._right_area = QWidget()
        self._right_area.setFixedWidth(0)
        self._right_area.setStyleSheet("background-color: #252526;")
        self._right_layout = QVBoxLayout(self._right_area)
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(0)
        self._main_splitter.addWidget(self._right_area)
        
        layout.addWidget(self._main_splitter)
        
        # 底部停靠区域
        self._bottom_area = QWidget()
        self._bottom_area.setFixedHeight(0)
        self._bottom_area.setStyleSheet("background-color: #252526;")
        self._bottom_layout = QHBoxLayout(self._bottom_area)
        self._bottom_layout.setContentsMargins(0, 0, 0, 0)
        self._bottom_layout.setSpacing(0)
        layout.addWidget(self._bottom_area)
    
    def set_center_widget(self, widget):
        """设置中央内容区域的组件"""
        # 清空现有内容
        while self._center_layout.count() > 0:
            item = self._center_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._center_layout.addWidget(widget)
    
    def add_panel_to_dock(self, widget, title, edge='left'):
        """添加面板到指定边缘停靠"""
        dock_panel = DockPanel(widget, title)
        dock_panel.close_requested.connect(self._remove_panel)
        
        if edge == 'left':
            if self._left_dock is None:
                self._left_dock = QWidget()
                self._left_dock.setStyleSheet("background-color: #252526;")
                self._left_layout.addWidget(self._left_dock)
                self._left_layout_inner = QVBoxLayout(self._left_dock)
                self._left_layout_inner.setContentsMargins(0, 0, 0, 0)
                self._left_layout_inner.setSpacing(0)
            
            self._left_layout_inner.addWidget(dock_panel)
            self._left_area.setFixedWidth(250)
            self._docked_edges.add('left')
            self.dock_changed.emit('left', True)
        
        elif edge == 'right':
            if self._right_dock is None:
                self._right_dock = QWidget()
                self._right_dock.setStyleSheet("background-color: #252526;")
                self._right_layout.addWidget(self._right_dock)
                self._right_layout_inner = QVBoxLayout(self._right_dock)
                self._right_layout_inner.setContentsMargins(0, 0, 0, 0)
                self._right_layout_inner.setSpacing(0)
            
            self._right_layout_inner.addWidget(dock_panel)
            self._right_area.setFixedWidth(250)
            self._docked_edges.add('right')
            self.dock_changed.emit('right', True)
        
        elif edge == 'bottom':
            if self._bottom_dock is None:
                self._bottom_dock = QWidget()
                self._bottom_dock.setStyleSheet("background-color: #252526;")
                self._bottom_layout.addWidget(self._bottom_dock)
                self._bottom_layout_inner = QVBoxLayout(self._bottom_dock)
                self._bottom_layout_inner.setContentsMargins(0, 0, 0, 0)
                self._bottom_layout_inner.setSpacing(0)
            
            self._bottom_layout_inner.addWidget(dock_panel)
            self._bottom_area.setFixedHeight(200)
            self._docked_edges.add('bottom')
            self.dock_changed.emit('bottom', True)
        
        return dock_panel
    
    def _remove_panel(self, dock_panel):
        """移除面板"""
        # 检查面板所在的停靠区域
        if self._left_dock and dock_panel.parent() == self._left_dock:
            dock_panel.deleteLater()
            
            # 如果没有面板了，隐藏停靠区域
            if self._left_layout_inner.count() == 0:
                self._left_dock.deleteLater()
                self._left_dock = None
                self._left_area.setFixedWidth(0)
                self._docked_edges.discard('left')
                self.dock_changed.emit('left', False)
        
        elif self._right_dock and dock_panel.parent() == self._right_dock:
            dock_panel.deleteLater()
            
            if self._right_layout_inner.count() == 0:
                self._right_dock.deleteLater()
                self._right_dock = None
                self._right_area.setFixedWidth(0)
                self._docked_edges.discard('right')
                self.dock_changed.emit('right', False)
        
        elif self._bottom_dock and dock_panel.parent() == self._bottom_dock:
            dock_panel.deleteLater()
            
            if self._bottom_layout_inner.count() == 0:
                self._bottom_dock.deleteLater()
                self._bottom_dock = None
                self._bottom_area.setFixedHeight(0)
                self._docked_edges.discard('bottom')
                self.dock_changed.emit('bottom', False)
        
        self.panel_closed.emit(dock_panel.get_widget())
    
    def is_docked(self, edge=None):
        """检查是否有面板停靠"""
        if edge is None:
            return len(self._docked_edges) > 0
        return edge in self._docked_edges
    
    def get_docked_edges(self):
        """获取所有停靠的边缘"""
        return list(self._docked_edges)