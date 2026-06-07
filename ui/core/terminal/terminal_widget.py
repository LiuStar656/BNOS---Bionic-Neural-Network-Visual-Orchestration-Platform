"""
终端界面组件
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QLineEdit, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.core.i18n import t
from ui.core.logger import logger
from .terminal_process import TerminalProcess


class HistoryLineEdit(QLineEdit):
    """带历史记录的输入框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._command_history = []
        self._history_index = -1
        self._current_text = ''
        # 保存输入时的文本
        self.textChanged.connect(self._on_text_changed)
    
    def _on_text_changed(self, text):
        """记录用户输入的文本"""
        if not hasattr(self, '_history_browsing') or not self._history_browsing:
            self._current_text = text

    def keyPressEvent(self, event):
        """处理按键事件"""
        if event.key() == Qt.Key.Key_Up:
            self._history_browsing = True
            self._navigate_history(-1)
            return
        elif event.key() == Qt.Key.Key_Down:
            self._history_browsing = True
            self._navigate_history(1)
            return
        
        self._history_browsing = False
        super().keyPressEvent(event)
    
    def add_to_history(self, command):
        """添加命令到历史"""
        command = command.strip()
        if command and (not self._command_history or self._command_history[-1] != command):
            self._command_history.append(command)
        self._history_index = len(self._command_history)
        self._current_text = ''
    
    def _navigate_history(self, direction: int):
        """导航命令历史"""
        if not self._command_history:
            return
        
        # 更新索引
        self._history_index += direction
        
        # 边界检查
        if self._history_index < 0:
            self._history_index = 0
            self.clear()
        elif self._history_index >= len(self._command_history):
            self._history_index = len(self._command_history)
            self.setText(self._current_text)
        else:
            # 设置历史命令
            self.setText(self._command_history[self._history_index])
            # 移动光标到末尾
            self.setCursorPosition(len(self.text()))


class TerminalWidget(QWidget):
    """终端界面组件 - 支持命令历史"""

    def __init__(self, working_dir: str = None, parent=None):
        super().__init__(parent)
        self.working_dir = working_dir
        self.process = TerminalProcess(working_dir)
        self._is_closing = False

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 终端输出区域
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setAcceptRichText(False)
        self.output_edit.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                border: none;
            }
        """)

        # 终端输入区域
        self.input_edit = HistoryLineEdit()
        self.input_edit.setPlaceholderText(t("k_terminal_input_hint"))
        self.input_edit.setStyleSheet("""
            QLineEdit {
                background-color: #252526;
                color: #d4d4d4;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid #3c3c3c;
                padding: 4px;
            }
        """)

        layout.addWidget(self.output_edit)
        layout.addWidget(self.input_edit)

    def _connect_signals(self):
        """连接信号"""
        self.process.output_received.connect(self._on_output)
        self.process.error_received.connect(self._on_error)
        self.input_edit.returnPressed.connect(self._on_input)

    def start_terminal(self, terminal_type: str = "powershell"):
        """启动终端"""
        self.process.start(terminal_type)

    def _on_output(self, data: str):
        """处理输出"""
        # 去除多余的控制字符并显示
        data = data.replace('\r\n', '\n').replace('\r', '\n')
        self.output_edit.insertPlainText(data)
        # 滚动到底部
        scrollbar = self.output_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_error(self, data: str):
        """处理错误"""
        # 去除多余的控制字符并显示
        data = data.replace('\r\n', '\n').replace('\r', '\n')
        self.output_edit.insertPlainText(data)
        # 滚动到底部
        scrollbar = self.output_edit.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _on_input(self):
        """处理输入"""
        command = self.input_edit.text()
        
        # 添加到历史记录
        self.input_edit.add_to_history(command)
        
        # 发送命令到终端
        self.process.write(command)
        self.input_edit.clear()

    def close_terminal(self):
        """安全关闭终端，终止子进程"""
        if self._is_closing:
            return
        self._is_closing = True
        logger.info("TerminalWidget: 正在关闭终端...")
        self.process.stop()

    def closeEvent(self, event):
        """关闭事件 - 确保子进程被终止"""
        self.close_terminal()
        super().closeEvent(event)
