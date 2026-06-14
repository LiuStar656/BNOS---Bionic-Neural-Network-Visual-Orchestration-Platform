"""
BNOS自定义Dock基类 - 实现PS式停靠、悬浮、堆叠、自动隐藏
"""
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QToolButton, QSizeGrip
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QCursor
from ui.icons.codicon import get_icon, get_icon_font


class BnosDock(QDockWidget):
    """自定义Dock基类"""
    
    closed = Signal(object)
    visibility_changed = Signal(bool)
    
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self._auto_hide = False
        self._collapsed_width = 40
        self._is_closing = False  # 🔒 关闭标志：关闭过程中不发送可见性信号
        self._original_width = None  # 保存原始宽度，用于自动隐藏展开
        
        # 🔴 关键：设置 objectName，让 Qt saveState/restoreState 能正确识别
        self.setObjectName(f"bnos_dock_{title}")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        # 设置样式
        self.setStyleSheet("""
            QDockWidget {
                border: none;
            }
            QDockWidget::title {
                background-color: #252526;
                color: #858585;
                padding: 4px 8px;
                font-size: 11px;
            }
            QDockWidget::close-button, QDockWidget::float-button {
                width: 16px;
                height: 16px;
            }
        """)
        
        # 创建标题栏部件
        self._title_widget = QWidget()
        self._title_layout = QHBoxLayout(self._title_widget)
        self._title_layout.setContentsMargins(4, 2, 4, 2)
        self._title_layout.setSpacing(4)
        # 设置垂直居中对齐
        self._title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # 标题标签
        self._title_label = QLabel(self.windowTitle())
        self._title_label.setStyleSheet("color: #858585; font-size: 11px;")
        self._title_layout.addWidget(self._title_label)
        
        # 弹性空间 - 让后面的按钮靠右对齐
        self._title_layout.addStretch(1)
        
        # 分隔线
        spacer = QWidget()
        spacer.setFixedWidth(1)
        spacer.setStyleSheet("background-color: rgba(255, 255, 255, 15);")
        self._title_layout.addWidget(spacer)
        
        # 自动隐藏按钮
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
        
        # 关闭按钮
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
        
        # 设置自定义标题栏
        self.setTitleBarWidget(self._title_widget)
        
        # 创建中心部件
        self._central_widget = QWidget()
        self.setWidget(self._central_widget)
        
        # 布局
        self._layout = QVBoxLayout(self._central_widget)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
    
    def set_content_widget(self, widget):
        """设置内容部件"""
        # 清空现有内容
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
            # 折叠
            self._auto_hide_btn.setText(get_icon('chevron-right'))
            # 记录原始宽度
            self._original_width = self.width()
            self.setFixedWidth(self._collapsed_width)
            self._title_label.hide()
            self._close_btn.hide()
        else:
            # 展开
            self._auto_hide_btn.setText(get_icon('chevron-left'))
            self.setFixedWidth(self._original_width)
            self._title_label.show()
            self._close_btn.show()
    
    def _close_dock(self):
        """关闭Dock"""
        self.hide()
        self.closed.emit(self)
    
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