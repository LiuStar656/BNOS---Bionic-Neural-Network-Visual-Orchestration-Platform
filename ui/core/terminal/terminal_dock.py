"""
终端 Dock 组件
"""
from PySide6.QtWidgets import (
    QComboBox, QWidget, QVBoxLayout, QToolButton, QHBoxLayout, QTabWidget, QTabBar
)
from PySide6.QtCore import Qt
from ui.core.bnos_dock import BnosDock
from ui.core.i18n import t
from .terminal_widget import TerminalWidget
from ui.icons.codicon import get_icon, get_icon_font
from ui.core.logger import logger


class TerminalDock(BnosDock):
    """终端 Dock - 支持多标签页"""
    
    def __init__(self, parent=None, main_window=None):
        super().__init__(t("k_terminal_dock_title"), parent)
        self.main_window = main_window
        self._canvas_host = parent  # parent 是 CanvasHost
        self._initialized = False
        
        self._setup_content_area()
        self._setup_toolbar()
        
        # 不在此处创建终端，延迟到首次显示时创建
    
    def _setup_content_area(self):
        """设置内容区域"""
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self.set_content_widget(self._content_widget)
        
        # 工具栏容器
        self._toolbar_widget = QWidget()
        self._toolbar_layout = QHBoxLayout(self._toolbar_widget)
        self._toolbar_layout.setContentsMargins(4, 2, 4, 2)
        self._toolbar_layout.setSpacing(4)
        self._content_layout.addWidget(self._toolbar_widget)
        
        # 标签页
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #252526;
                color: #858585;
                padding: 4px 8px;
                border: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2d2d2d;
            }
        """)
        # 允许关闭标签页
        self._tab_widget.setTabsClosable(True)
        self._tab_widget.tabCloseRequested.connect(self._close_terminal_tab)
        self._content_layout.addWidget(self._tab_widget, 1)
    
    def _setup_toolbar(self):
        """设置工具栏"""
        # 创建新终端按钮
        new_terminal_btn = QToolButton()
        new_terminal_btn.setText(get_icon('plus'))
        new_terminal_btn.setFont(get_icon_font(12))
        new_terminal_btn.setStyleSheet("""
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
        new_terminal_btn.clicked.connect(self._add_new_terminal)
        new_terminal_btn.setToolTip(t("k_terminal_new"))
        
        # 分隔线
        separator = QWidget()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 15);")
        
        # 终端类型选择
        self.terminal_type_combo = QComboBox()
        self.terminal_type_combo.addItems([
            t("k_terminal_type_powershell"),
            t("k_terminal_type_cmd"),
            t("k_terminal_type_bash")
        ])
        self.terminal_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #252526;
                color: #858585;
                border: 1px solid #3c3c3c;
                padding: 2px 4px;
                font-size: 10px;
            }
            QComboBox::drop-down {
                border: none;
                width: 14px;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #858585;
            }
        """)
        
        # 添加到工具栏
        self._toolbar_layout.addWidget(new_terminal_btn)
        self._toolbar_layout.addWidget(separator)
        self._toolbar_layout.addWidget(self.terminal_type_combo)
        self._toolbar_layout.addStretch(1)
    
    def _get_current_project_path(self):
        """获取当前活动画布的项目路径"""
        if self._canvas_host and hasattr(self._canvas_host, 'get_active_canvas'):
            active_canvas = self._canvas_host.get_active_canvas()
            if active_canvas and hasattr(self._canvas_host, 'get_canvas_data'):
                canvas_data = self._canvas_host.get_canvas_data(active_canvas)
                project_path = canvas_data.get('project_path')
                if project_path:
                    return project_path
        # 回退到主窗口的项目路径
        if self.main_window and hasattr(self.main_window, 'current_project_path'):
            return self.main_window.current_project_path
        return None
    
    def _ensure_first_terminal(self):
        """确保至少有一个终端标签页"""
        if self._tab_widget.count() == 0:
            self._add_new_terminal()
    
    def showEvent(self, event):
        """显示事件 - 首次显示时创建终端"""
        self._ensure_first_terminal()
        super().showEvent(event)
    
    def _get_next_terminal_name(self):
        """获取下一个可用的终端名称"""
        used_numbers = set()
        for i in range(self._tab_widget.count()):
            text = self._tab_widget.tabText(i)
            if text.startswith("Terminal "):
                try:
                    num = int(text.replace("Terminal ", ""))
                    used_numbers.add(num)
                except ValueError:
                    pass
        
        # 找最小的未使用的数字
        num = 1
        while num in used_numbers:
            num += 1
        return f"Terminal {num}"
    
    def _add_new_terminal(self):
        """添加新的终端标签页"""
        working_dir = self._get_current_project_path()
        
        terminal = TerminalWidget(working_dir, self)
        
        # 获取选中的终端类型
        terminal_type_text = self.terminal_type_combo.currentText()
        terminal_type = "powershell"
        if terminal_type_text == t("k_terminal_type_cmd"):
            terminal_type = "cmd"
        elif terminal_type_text == t("k_terminal_type_bash"):
            terminal_type = "bash"
        
        # 生成终端名称
        terminal_name = self._get_next_terminal_name()
        
        # 添加标签页
        tab_index = self._tab_widget.addTab(terminal, terminal_name)
        self._tab_widget.setCurrentIndex(tab_index)
        
        terminal.start_terminal(terminal_type)
        
        logger.debug(f"Added new terminal tab: {terminal_name}")
    
    def _close_terminal_tab(self, index):
        """关闭指定的终端标签页"""
        if self._tab_widget.count() <= 1:
            # 至少保留一个标签页
            return
        
        widget = self._tab_widget.widget(index)
        if widget and isinstance(widget, TerminalWidget):
            widget.close_terminal()
            widget.deleteLater()
        
        self._tab_widget.removeTab(index)
        
        logger.debug(f"Closed terminal tab at index: {index}")
    
    def stop_all_terminals(self):
        """停止所有终端子进程"""
        logger.info("TerminalDock: 停止所有终端进程...")
        for i in range(self._tab_widget.count()):
            widget = self._tab_widget.widget(i)
            if widget and isinstance(widget, TerminalWidget):
                widget.close_terminal()
    
    def closeEvent(self, event):
        """Dock 关闭事件 - 停止所有终端进程"""
        self.stop_all_terminals()
        super().closeEvent(event)
    
    def sync_to_canvas(self):
        """同步到当前活动画布"""
        logger.debug("Syncing terminal to active canvas")
        
        # 获取新的工作目录
        new_working_dir = self._get_current_project_path()
        logger.debug(f"New working directory: {new_working_dir}")
        
        # 如果还没有终端，创建一个
        if self._tab_widget.count() == 0:
            self._add_new_terminal()
