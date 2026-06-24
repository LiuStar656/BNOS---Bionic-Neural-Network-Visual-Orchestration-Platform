"""
面板停靠管理器 - 使用Qt原生QDockWidget实现PS式停靠系统
支持面板吸附边缘停靠、堆叠、自动隐藏、布局保存
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QDockWidget, 
    QSplitter, QTabWidget, QToolButton, QLabel, QFrame, QSizeGrip, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QObject, QTimer, QEvent
from PySide6.QtGui import QColor, QPalette
from ui.core.i18n import t
from ui.icons.codicon import get_icon, get_icon_font
from ui.core.dock_position_manager import DockPositionManager  # DockDoubleClickHandler 已禁用

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
                dock._apply_floating_border_color(active_color)
            else:
                dock._apply_floating_border_color(inactive_color)
            dock.show()
            dock.repaint()
            QApplication.processEvents()


def get_dock_floating_colors():
    """获取当前 Dock 漂浮外边框颜色"""
    return _FLOATING_BORDER_COLOR, _FLOATING_BORDER_COLOR_INACTIVE


class BnosDockWidget(QDockWidget):
    """自定义DockWidget基类
    
    漂浮时自动切换为无边框模式，使用自定义边框颜色（不再跟随系统主题色）。
    漂浮时显示自定义标题栏。
    
    [已禁用] 双击标题栏或边缘区域自动嵌入。
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
        self._title_bar_hidden = False
        self._last_dock_area = None
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
        
        # 创建内部包装容器（用于漂浮时 margin 露出边框色）
        self._central_widget = QWidget()
        self._central_layout = QVBoxLayout(self._central_widget)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self._central_layout.setSpacing(0)
        self.setWidget(self._central_widget)
        
        self._setup_title_bar()
        self._apply_docked_style()
        
        self._position_manager = DockPositionManager(self)
        # [已禁用] DockDoubleClickHandler — 双击切换浮动/停靠功能已屏蔽
        self.installEventFilter(self)
    
    def _setup_title_bar(self):
        """设置自定义标题栏"""
        from ui.icons.codicon import get_icon, get_icon_font
        
        self._title_widget = QWidget()
        self._title_layout = QHBoxLayout(self._title_widget)
        self._title_layout.setContentsMargins(4, 2, 4, 2)
        self._title_layout.setSpacing(4)
        self._title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        self._title_label = QLabel(self.windowTitle())
        self._title_label.setStyleSheet("color: #858585; font-size: 11px;")
        self._title_layout.addWidget(self._title_label)
        
        self._title_layout.addStretch(1)
        
        spacer = QWidget()
        spacer.setFixedWidth(1)
        spacer.setStyleSheet("background-color: rgba(255, 255, 255, 15);")
        self._title_layout.addWidget(spacer)
        
        self._close_btn = QToolButton()
        self._close_btn.setIconSize(QSize(14, 14))
        self._close_btn.setText(get_icon('x'))
        self._close_btn.setFont(get_icon_font(12))
        self._close_btn.setStyleSheet("""
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
        self._close_btn.clicked.connect(self.close)
        self._title_layout.addWidget(self._close_btn)
        
        self.setTitleBarWidget(self._title_widget)
    
    def _apply_floating_border_color(self, color):
        """设置漂浮时的边框颜色：QDockWidget 背景色 + _central_widget margin 露出边框"""
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor(color))
        self.setPalette(pal)
        bw = _FLOATING_BORDER_WIDTH
        self._central_widget.setStyleSheet(f"background-color: #252526; margin: {bw}px;")
    
    def _apply_docked_style(self):
        """停靠状态样式（恢复默认）"""
        self.setAutoFillBackground(False)
        self.setStyleSheet("")
        self._central_widget.setStyleSheet("background-color: #252526;")
        if self._size_grip:
            self._size_grip.hide()
    
    def _apply_floating_style(self):
        """漂浮状态样式（自定义边框色）"""
        self._apply_floating_border_color(_FLOATING_BORDER_COLOR)
        if self._size_grip is None:
            self._size_grip = QSizeGrip(self)
        self._size_grip.show()
    
    def _on_dock_location_changed(self, area):
        """停靠位置变化回调：保存最后停靠区域"""
        if area != Qt.DockWidgetArea.NoDockWidgetArea:
            self._last_dock_area = area
    
    def save_original_dock_info(self, area):
        """保存创建时的原始停靠区域（永久缓存，不随拖动清空）"""
        self._position_manager.save_original_dock_info(area)
    
    def _on_top_level_changed(self, floating):
        """漂浮状态切换回调"""
        self._is_floating = floating
        if floating:
            self._apply_floating_style()
        else:
            self._apply_docked_style()
    
    def changeEvent(self, event):
        """窗口激活状态变化时更新边框颜色"""
        if event.type() == event.Type.ActivationChange and self._is_floating:
            if self.isActiveWindow():
                self._apply_floating_border_color(_FLOATING_BORDER_COLOR)
            else:
                self._apply_floating_border_color(_FLOATING_BORDER_COLOR_INACTIVE)
        super().changeEvent(event)
    
    def nativeEvent(self, eventType, message):
        """处理 Windows 原生事件：支持从窗口边缘拖拽调整大小"""
        import ctypes
        if not self._is_floating or eventType != b"windows_generic_MSG":
            return False, 0
        
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
        
        x = msg.lParam & 0xFFFF
        y = (msg.lParam >> 16) & 0xFFFF
        
        pos = self.mapToGlobal(self.rect().topLeft())
        win_x, win_y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        
        border = 4
        left = x < win_x + border
        right = x > win_x + w - border
        top = y < win_y + border
        bottom = y > win_y + h - border
        
        HTLEFT, HTRIGHT, HTTOP, HTBOTTOM = 10, 11, 12, 15
        HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT = 13, 14, 16, 17
        
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
        self._central_layout.addWidget(widget, 1)
    
    def get_content_widget(self):
        """获取内容部件"""
        return self._content_widget
    
    def eventFilter(self, obj, event):
        """[已禁用] 拦截所有双击事件，防止 Qt 原生 Dock 切换浮动/停靠"""
        if event.type() == QEvent.Type.MouseButtonDblClick:
            return True  # 吞噬事件，阻止传播
        return super().eventFilter(obj, event)
    
    def mouseDoubleClickEvent(self, event):
        """[已禁用] 双击事件已屏蔽"""
        event.accept()  # 吞噬事件，阻止 Qt 原生处理
    
    def set_title(self, title):
        """设置标题"""
        self.setWindowTitle(title)
        if hasattr(self, '_title_label'):
            self._title_label.setText(title)
    
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
        for existing_edge, docks in self._docks.items():
            for dock in docks:
                if dock.get_content_widget() == widget:
                    dock.show()
                    dock.raise_()
                    return dock
        
        dock = BnosDockWidget(title, self._main_window)
        dock.set_content_widget(widget)
        dock.closed.connect(lambda: self._remove_dock(dock, edge))
        
        if edge not in self._docks:
            self._docks[edge] = []
        self._docks[edge].append(dock)
        
        self._dock_info_map[title] = {
            'dock': dock,
            'edge': edge,
            'widget': widget
        }
        
        if edge == 'left':
            area = Qt.DockWidgetArea.LeftDockWidgetArea
        elif edge == 'right':
            area = Qt.DockWidgetArea.RightDockWidgetArea
        else:
            area = Qt.DockWidgetArea.RightDockWidgetArea
        
        self._main_window.addDockWidget(area, dock)
        dock.save_original_dock_info(area)
        
        dock.show()
        return dock
    
    def _remove_dock(self, dock, edge):
        """移除Dock"""
        if edge in self._docks and dock in self._docks[edge]:
            self._docks[edge].remove(dock)
            self._main_window.removeDockWidget(dock)
            
            title_to_remove = None
            for title, info in self._dock_info_map.items():
                if info['dock'] == dock:
                    title_to_remove = title
                    break
            if title_to_remove:
                del self._dock_info_map[title_to_remove]
            
            # 递归停止 content widget 中所有定时器和线程
            self._stop_content_timers(dock)
            
            dock.deleteLater()
            QApplication.processEvents()
            self.panel_closed.emit(dock.get_content_widget())
    
    @staticmethod
    def _stop_content_timers(dock):
        """停止 dock 内部 widget 的所有 QTimer 和 QThread"""
        content = dock.get_content_widget()
        if content is None:
            return
        try:
            from PySide6.QtCore import QTimer, QThread
            for child in content.findChildren(QTimer):
                try:
                    if child.isActive():
                        child.stop()
                except RuntimeError:
                    pass
            for child in content.findChildren(QThread):
                try:
                    if child.isRunning():
                        child.quit()
                        child.wait(500)
                        if child.isRunning():
                            child.terminate()
                            child.wait(500)
                except RuntimeError:
                    pass
        except RuntimeError:
            pass
    
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
