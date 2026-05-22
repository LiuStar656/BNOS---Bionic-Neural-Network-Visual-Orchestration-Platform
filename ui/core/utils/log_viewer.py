"""
日志查看工具 — 统一日志对话框，消除 node_list_panel 中 view_node_log 和 batch_view_node_logs 的重复代码
"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton


def show_log_dialog(parent, title, content, width=800, height=600):
    """显示日志查看对话框

    Args:
        parent: 父窗口
        title: 对话框标题
        content: 日志文本内容
        width: 窗口宽度（默认 800）
        height: 窗口高度（默认 600）
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setGeometry(200, 200, width, height)

    layout = QVBoxLayout(dialog)

    text_edit = QTextEdit()
    text_edit.setReadOnly(True)
    text_edit.setText(content)
    layout.addWidget(text_edit)

    close_button = QPushButton("关闭")
    close_button.clicked.connect(dialog.close)
    layout.addWidget(close_button)

    dialog.exec()
