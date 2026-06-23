"""
BNOS自定义Dock基类 - 实现PS式停靠、悬浮、堆叠、自动隐藏
"""
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QToolButton, QSizeGrip, QMainWindow, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QCursor, QPalette, QColor
from ui.icons.codicon import get_icon, get_icon_font
from ui.core.logger import logger
from ui.core.dock_position_manager import DockPositionManager

# ── 漂浮时外边框颜色（可通过 set_dock_floating_colors() 修改） ──
_FLOATING_BORDER_COLOR = "#007acc"
_FLOATING_BORDER_COLOR_INACTIVE = "#3c3c3c"
_FLOATING_BORDER_WIDTH = 2


def set_dock_floating_colors(active_color, inactive_color):
    """设置 Dock 漂浮时的外边框颜色（由颜色设置模块调用）"""
    global _FLOATING_BORDER_COLOR, _FLOATING_BORDER_COLOR_INACTIVE
    _FLOATING_BORDER_COLOR = active_color
    _FLOATING_BORDER_COLOR_INACTIVE = inactive_color
    
    for dock in BnosDock._instances:
        if dock.isFloating():
            dock._is_floating = True
            if dock.isActiveWindow():
                dock._apply_floating_border_color(active_color)
            else:
                dock._apply_floating_border_color(inactive_color)
            dock.show()
            dock.repaint()
    
    from ui.core.dock_manager import set_dock_floating_colors as set_mgr_colors
    set_mgr_colors(active_color, inactive_color)


def get_dock_floating_colors():
    """获取当前 Dock 漂浮外边框颜色"""
    return _FLOATING_BORDER_COLOR, _FLOATING_BORDER_COLOR_INACTIVE


class BnosDock(QDockWidget):
    """自定义Dock基类
    
    漂浮时自动切换为无边框模式，使用自定义边框颜色（不再跟随系统主题色）。
    
    增强功能：双击漂浮状态下的边缘区域可自动嵌入到父容器并隐藏标题栏。
    """
    
    _instances = []
    
    closed = Signal(object)
    visibility_changed = Signal(bool)
    title_bar_hidden = Signal(bool)  # 标题栏隐藏状态变化
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        BnosDock._instances.append(self)
        self._auto_hide = False
        self._collapsed_width = 40
        self._is_closing = False
        self._original_width = None
        self._is_floating = False
        self._floating_size_grip = None
        self._title_bar_hidden = False  # 标题栏是否隐藏
        
        self.setObjectName(f"bnos_dock_{title}")
        
        self._setup_ui()
        
        self._position_manager = DockPositionManager(self)
    
    def _setup_ui(self):
        """设置UI"""
        # 先创建 central_widget（_apply_docked_style 需要用到）
        self._central_widget = QWidget()
        self.setWidget(self._central_widget)
        self._layout = QVBoxLayout(self._central_widget)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        self._apply_docked_style()
        
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
        
        self._auto_hide_btn = QToolButton()
        self._auto_hide_btn.setIconSize(QSize(14, 14))
        self._auto_hide_btn.setText(get_icon('chevron-left'))
        self._auto_hide_btn.setFont(get_icon_font(12))
        self._auto_hide_btn.setStyleSheet("""
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
        self._auto_hide_btn.clicked.connect(self._toggle_auto_hide)
        self._title_layout.addWidget(self._auto_hide_btn)
        
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
        self._close_btn.clicked.connect(self._close_dock)
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
        """停靠状态样式"""
        self.setAutoFillBackground(False)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        self.setPalette(pal)
        self.setStyleSheet("")
        self._central_widget.setStyleSheet("background-color: #252526;")
        if self._floating_size_grip:
            self._floating_size_grip.hide()
    
    def _apply_floating_style(self):
        """漂浮状态样式（自定义边框色）"""
        self._apply_floating_border_color(_FLOATING_BORDER_COLOR)
        if self._floating_size_grip is None:
            self._floating_size_grip = QSizeGrip(self)
        self._floating_size_grip.show()
    
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
        while self._layout.count() > 0:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._layout.addWidget(widget, 1)
    
    def get_content_widget(self):
        """获取内容部件"""
        if self._layout.count() > 0:
            item = self._layout.itemAt(0)
            return item.widget()
        return None
    
    def _toggle_auto_hide(self):
        """切换自动隐藏状态"""
        self._auto_hide = not self._auto_hide
        
        if self._auto_hide:
            self._auto_hide_btn.setText(get_icon('chevron-right'))
            self._original_width = self.width()
            self.setFixedWidth(self._collapsed_width)
            self._title_label.hide()
            self._close_btn.hide()
        else:
            self._auto_hide_btn.setText(get_icon('chevron-left'))
            self.setFixedWidth(self._original_width)
            self._title_label.show()
            self._close_btn.show()
    
    def _close_dock(self):
        """关闭Dock"""
        self.hide()
        self.closed.emit(self)
    
    def mouseDoubleClickEvent(self, event):
        """双击事件：双击标题栏或边缘区域都触发嵌入"""
        pos = event.pos()
        w, h = self.width(), self.height()
        
        border = 4
        is_on_edge = (pos.x() < border or pos.x() > w - border or
                     pos.y() < border or pos.y() > h - border)
        
        is_on_title_bar = False
        if self._title_widget and not self._title_bar_hidden:
            title_bar_rect = self._title_widget.geometry()
            if title_bar_rect.contains(pos):
                is_on_title_bar = True
        
        if is_on_edge or is_on_title_bar:
            if hasattr(self, '_position_manager'):
                self._position_manager.save_current_state_before_toggle()
            
            if self.isFloating():
                self._auto_embed_and_hide_title()
            else:
                self.setFloating(True)
            event.accept()
            return
        
        event.ignore()
    
    def _auto_embed_and_hide_title(self):
        """自动嵌入到父容器并隐藏标题栏"""
        self.hide_title_bar()
        self._position_manager.restore_to_docked_position()
        
        logger.info(f"BnosDock: '{self.windowTitle()}' 已自动嵌入并隐藏标题栏")
    
    def hide_title_bar(self):
        """隐藏标题栏"""
        if self._title_bar_hidden:
            return
        
        self._title_bar_hidden = True
        self.setTitleBarWidget(None)
        self.title_bar_hidden.emit(True)
        
        # 调整样式，移除标题栏占用的空间
        self._central_widget.setStyleSheet("background-color: #252526; margin: 0px;")
    
    def show_title_bar(self):
        """显示标题栏"""
        if not self._title_bar_hidden:
            return
        
        self._title_bar_hidden = False
        self.setTitleBarWidget(self._title_widget)
        self.title_bar_hidden.emit(False)
    
    def is_title_bar_hidden(self):
        """检查标题栏是否隐藏"""
        return self._title_bar_hidden
    
    def set_title(self, title):
        """设置标题"""
        self.setWindowTitle(title)
        self._title_label.setText(title)
    
    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        if not getattr(self, '_is_closing', False):
            self.visibility_changed.emit(True)
    
    def hideEvent(self, event):
        """隐藏事件"""
        super().hideEvent(event)
        if not getattr(self, '_is_closing', False):
            self.visibility_changed.emit(False)
    
    def closeEvent(self, event):
        """关闭事件：清理实例引用"""
        if self in BnosDock._instances:
            BnosDock._instances.remove(self)
        super().closeEvent(event)
