"""
面板停靠管理器 - 使用Qt原生QDockWidget实现PS式停靠系统
支持面板吸附边缘停靠、堆叠、自动隐藏、布局保存
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QDockWidget, 
    QSplitter, QTabWidget, QToolButton, QLabel, QFrame, QSizeGrip
)
from PySide6.QtCore import Qt, Signal, QSize, QObject
from PySide6.QtGui import QColor
from ui.core.i18n import t
from ui.icons.codicon import get_icon, get_icon_font

# ── 漂浮时外边框颜色（可通过 set_dock_floating_colors() 修改） ──
_FLOATING_BORDER_COLOR = "#007acc"
_FLOATING_BORDER_COLOR_INACTIVE = "#3c3c3c"
_FLOATING_BORDER_WIDTH = 2


def set_dock_floating_colors(active_color, inactive_color):
    """设置 Dock 漂浮时的外边框颜色（由颜色设置模块调用）"""
    global _FLOATING_BORDER_COLOR, _FLOATING_BORDER_COLOR_INACTIVE
    _FLOATING_BORDER_COLOR = active_color
    _FLOATING_BORDER_COLOR_INACTIVE = inactive_color
    
    for dock in BnosDockWidget._instances:
        if dock.isFloating():
            dock._is_floating = True
            if dock.isActiveWindow():
                dock.setStyleSheet(dock._dock_css(active_color, _FLOATING_BORDER_WIDTH))
            else:
                dock.setStyleSheet(dock._dock_css(inactive_color, _FLOATING_BORDER_WIDTH))
            dock.show()
            dock.repaint()


def get_dock_floating_colors():
    """获取当前 Dock 漂浮外边框颜色"""
    return _FLOATING_BORDER_COLOR, _FLOATING_BORDER_COLOR_INACTIVE


class BnosDockWidget(QDockWidget):
    """自定义DockWidget基类
    
    漂浮时自动切换为无边框模式，使用自定义边框颜色（不再跟随系统主题色）。
    """
    
    _instances = []
    
    closed = Signal(object)
    visibility_changed = Signal(bool)
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        BnosDockWidget._instances.append(self)
        self._content_widget = None
        self._auto_hide = False
        self._size_grip = None
        self._is_floating = False
        
        # 🔴 关键：设置 objectName，让 Qt saveState/restoreState 能正确识别
        self.setObjectName(f"bnos_dock_widget_{title}")
        
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
        
        # 初始样式（停靠状态）
        self._apply_docked_style()
        
        # 监听漂浮状态变化
        self.topLevelChanged.connect(self._on_top_level_changed)
    
    @staticmethod
    def _dock_css(border_color, border_width):
        """生成 QDockWidget 样式"""
        return f"""
            QDockWidget {{
                border: {border_width}px solid {border_color};
                background-color: #252526;
            }}
            QDockWidget::title {{
                background-color: #252526;
                color: #d4d4d4;
                padding: 4px 8px;
                font-size: 12px;
                border-bottom: 1px solid #3c3c3c;
            }}
        """
    
    def _apply_docked_style(self):
        """停靠状态样式"""
        self.setStyleSheet(self._dock_css("#3c3c3c", 1))
        if self._size_grip:
            self._size_grip.hide()
    
    def _apply_floating_style(self):
        """漂浮状态样式（无边框 + 自定义边框色）"""
        # 先显示确保窗口创建完成，再设无边框
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(self._dock_css(_FLOATING_BORDER_COLOR, _FLOATING_BORDER_WIDTH))
        # 添加右下角大小调节手柄
        if self._size_grip is None:
            self._size_grip = QSizeGrip(self)
        self._size_grip.show()
        self.show()  # 重新显示以应用窗口标志
    
    def _on_top_level_changed(self, floating):
        """漂浮状态切换回调"""
        self._is_floating = floating
        if floating:
            self._apply_floating_style()
        else:
            # 停靠恢复：去掉无边框标志
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.FramelessWindowHint)
            self._apply_docked_style()
            self.show()
    
    def changeEvent(self, event):
        """窗口激活状态变化时更新边框颜色"""
        if event.type() == event.Type.ActivationChange and self._is_floating:
            if self.isActiveWindow():
                self.setStyleSheet(self._dock_css(_FLOATING_BORDER_COLOR, _FLOATING_BORDER_WIDTH))
            else:
                self.setStyleSheet(self._dock_css(_FLOATING_BORDER_COLOR_INACTIVE, _FLOATING_BORDER_WIDTH))
        super().changeEvent(event)
    
    def nativeEvent(self, eventType, message):
        """处理 Windows 原生事件：支持从窗口边缘拖拽调整大小"""
        import ctypes
        if not self._is_floating or eventType != b"windows_generic_MSG":
            return False, 0
        
        # WM_NCHITTEST = 0x0084：让系统知道鼠标在窗口的哪个区域
        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("message", ctypes.c_uint),
                ("wParam", ctypes.c_ulonglong),
                ("lParam", ctypes.c_longlong),
                ("time", ctypes.c_uint),
                ("pt_x", ctypes.c_long),
                ("pt_y", ctypes.c_long),
            ]
        msg = MSG.from_address(int(message))
        if msg.message != 0x0084:
            return False, 0
        
        # 解析鼠标屏幕坐标
        x = msg.lParam & 0xFFFF
        y = (msg.lParam >> 16) & 0xFFFF
        
        # 获取窗口矩形
        pos = self.mapToGlobal(self.rect().topLeft())
        win_x, win_y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        
        border = 6  # 边缘拖动检测宽度
        left = x < win_x + border
        right = x > win_x + w - border
        top = y < win_y + border
        bottom = y > win_y + h - border
        
        # 返回对应的 HT* 区域码
        HTLEFT, HTRIGHT, HTTOP, HTBOTTOM = 10, 11, 12, 15
        HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT = 13, 14, 16, 17
        HTCLIENT = 1
        
        if top and left:
            return True, HTTOPLEFT
        if top and right:
            return True, HTTOPRIGHT
        if bottom and left:
            return True, HTBOTTOMLEFT
        if bottom and right:
            return True, HTBOTTOMRIGHT
        if left:
            return True, HTLEFT
        if right:
            return True, HTRIGHT
        if top:
            return True, HTTOP
        if bottom:
            return True, HTBOTTOM
        
        return False, 0
    
    def set_content_widget(self, widget):
        """设置内容部件"""
        self._content_widget = widget
        self.setWidget(widget)
    
    def get_content_widget(self):
        """获取内容部件"""
        return self._content_widget
    
    def closeEvent(self, event):
        """关闭事件：清理实例引用"""
        if self in BnosDockWidget._instances:
            BnosDockWidget._instances.remove(self)
        self.closed.emit(self._content_widget)
        super().closeEvent(event)


class DockManager(QObject):
    """面板停靠管理器"""
    
    panel_closed = Signal(QWidget)
    dock_changed = Signal(str, bool)  # edge, is_docked
    
    def __init__(self, main_window):
        super().__init__()
        self._main_window = main_window
        self._docks = {}  # edge -> list of docks
        self._dock_info_map = {}  # title -> {'dock': dock, 'edge': edge, 'widget': widget}
    
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
        
        # 创建自定义 Dock
        dock = BnosDockWidget(title, self._main_window)
        dock.set_content_widget(widget)
        dock.closed.connect(lambda: self._remove_dock(dock, edge))
        
        # 存储到对应边缘
        if edge not in self._docks:
            self._docks[edge] = []
        self._docks[edge].append(dock)
        
        # 记录 Dock 信息
        self._dock_info_map[title] = {
            'dock': dock,
            'edge': edge,
            'widget': widget
        }
        
        # PS式布局：面板仅允许停靠在左右两侧
        if edge == 'left':
            self._main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        elif edge == 'right':
            self._main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        else:
            # 默认停靠到右侧（PS布局不允许底部停靠）
            self._main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        
        dock.show()
        return dock
    
    def _remove_dock(self, dock, edge):
        """移除Dock"""
        if edge in self._docks and dock in self._docks[edge]:
            self._docks[edge].remove(dock)
            self._main_window.removeDockWidget(dock)
            
            # 从信息映射中移除
            title_to_remove = None
            for title, info in self._dock_info_map.items():
                if info['dock'] == dock:
                    title_to_remove = title
                    break
            if title_to_remove:
                del self._dock_info_map[title_to_remove]
            
            dock.deleteLater()
            self.panel_closed.emit(dock.get_content_widget())
    
    def get_docks_by_edge(self, edge):
        """获取指定边缘的所有Dock"""
        return self._docks.get(edge, [])
    
    def get_dock_by_title(self, title):
        """按标题获取 Dock"""
        info = self._dock_info_map.get(title)
        return info['dock'] if info else None
    
    def get_all_dock_titles(self):
        """获取所有 Dock 标题"""
        return list(self._dock_info_map.keys())
    
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