"""
面板停靠管理器 - 使用Qt原生QDockWidget实现PS式停靠系统
支持面板吸附边缘停靠、堆叠、自动隐藏、布局保存
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QDockWidget, 
    QSplitter, QTabWidget, QToolButton, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QObject
from ui.core.i18n import t
from ui.icons.codicon import get_icon, get_icon_font


class BnosDockWidget(QDockWidget):
    """自定义DockWidget基类"""
    
    closed = pyqtSignal(object)
    visibility_changed = pyqtSignal(bool)
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self._content_widget = None
        self._auto_hide = False
        
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.BottomDockWidgetArea
        )
        
        # 设置样式
        self.setStyleSheet("""
            QDockWidget {
                border: 1px solid #3c3c3c;
                background-color: #252526;
            }
            QDockWidget::title {
                background-color: #252526;
                color: #d4d4d4;
                padding: 4px 8px;
                font-size: 12px;
                border-bottom: 1px solid #3c3c3c;
            }
        """)
    
    def set_content_widget(self, widget):
        """设置内容部件"""
        self._content_widget = widget
        self.setWidget(widget)
    
    def get_content_widget(self):
        """获取内容部件"""
        return self._content_widget
    
    def closeEvent(self, event):
        """关闭事件"""
        self.closed.emit(self._content_widget)
        super().closeEvent(event)


class DockManager(QObject):
    """面板停靠管理器"""
    
    panel_closed = pyqtSignal(QWidget)
    dock_changed = pyqtSignal(str, bool)  # edge, is_docked
    
    def __init__(self, main_window):
        super().__init__()
        self._main_window = main_window
        self._docks = {}  # edge -> list of docks
    
    def add_panel_to_dock(self, widget, title, edge='left'):
        """添加面板到指定边缘停靠（防止重复添加）"""
        # 检查是否已存在相同的内容部件
        for existing_edge, docks in self._docks.items():
            for dock in docks:
                if dock.get_content_widget() == widget:
                    # 如果已存在，显示它并返回
                    dock.show()
                    dock.raise_()
                    return dock
        
        # 创建自定义Dock
        dock = BnosDockWidget(title, self._main_window)
        dock.set_content_widget(widget)
        dock.closed.connect(lambda: self._remove_dock(dock, edge))
        
        # 存储到对应边缘
        if edge not in self._docks:
            self._docks[edge] = []
        self._docks[edge].append(dock)
        
        # 添加到主窗口的停靠区域
        if edge == 'left':
            self._main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        elif edge == 'right':
            self._main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        elif edge == 'bottom':
            self._main_window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        
        dock.show()
        return dock
    
    def _remove_dock(self, dock, edge):
        """移除Dock"""
        if edge in self._docks and dock in self._docks[edge]:
            self._docks[edge].remove(dock)
            self._main_window.removeDockWidget(dock)
            dock.deleteLater()
            self.panel_closed.emit(dock.get_content_widget())
    
    def get_docks_by_edge(self, edge):
        """获取指定边缘的所有Dock"""
        return self._docks.get(edge, [])
    
    def save_layout(self, filepath):
        """保存布局到文件"""
        # 保存主窗口状态
        state = self._main_window.saveState()
        with open(filepath, 'wb') as f:
            f.write(state)
    
    def restore_layout(self, filepath):
        """从文件恢复布局"""
        try:
            with open(filepath, 'rb') as f:
                state = f.read()
            self._main_window.restoreState(state)
            return True
        except Exception:
            return False
    
    def toggle_auto_hide(self, edge):
        """切换自动隐藏模式"""
        for dock in self._docks.get(edge, []):
            dock.toggleViewAction().trigger()