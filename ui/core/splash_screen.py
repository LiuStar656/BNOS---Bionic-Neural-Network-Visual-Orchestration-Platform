"""
启动动画 — ASCII 字符拼成的 BNOS + 左下角日志 + 进度条
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QProgressBar, QTextEdit, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

# ── ASCII Art: BNOS (7行 × 宽) ──
ASCII_BNOS = [
    " █████╗     ███╗  ██╗     █████╗     ██████╗ ",
    " ██╔══██╗   ████╗ ██║    ██╔══██╗   ██╔════╝ ",
    " ██████╔╝   ██╔██╗██║    ██║  ██║   ╚█████╗  ",
    " ██╔══██╗   ██║╚████║    ██║  ██║    ╚═══██╗ ",
    " ██████╔╝   ██║ ╚███║    ╚█████╔╝   ██████╔╝ ",
    " ╚═════╝    ╚═╝  ╚══╝     ╚════╝    ╚═════╝  ",
]

_TITLE_STYLE = "color: #ffffff; background: transparent; font-size: 16px;"
_LOG_STYLE = ("QTextEdit { background-color: transparent; color: #aaa; border: none; "
              "font-family: Consolas; font-size: 10px; }")
_BAR_STYLE = """
QProgressBar { background: #2a2a2a; border: 1px solid #555; border-radius: 2px; height: 8px; text-align: center; }
QProgressBar::chunk { background: #777; border-radius: 1px; }
"""
_HINT_STYLE = "color: #888; font-size: 10px; background: transparent;"


class SplashScreen(QWidget):
    """启动闪屏 — 居中屏幕，ASCII 标题 + 日志 + 进度条"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(620, 340)
        self.setStyleSheet("background-color: #1e1e1e; border: 1px solid #555; border-radius: 6px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 14)
        layout.setSpacing(8)

        # ── 标题 ASCII Art ──
        title_widget = QWidget()
        title_widget.setStyleSheet("background: transparent;")
        title_layout = QVBoxLayout(title_widget)
        title_layout.setSpacing(0)
        title_layout.setContentsMargins(0, 0, 0, 0)

        for line in ASCII_BNOS:
            lbl = QLabel(line)
            lbl.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #ffffff; background: transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title_layout.addWidget(lbl)

        # 副标题（从 i18n 读取）
        from ui.core.i18n import t
        sub = QLabel(t("_k_splash_subtitle"))
        sub.setFont(QFont("Consolas", 9))
        sub.setStyleSheet("color: #aaa; background: transparent; letter-spacing: 1px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(sub)

        layout.addWidget(title_widget, 1)

        # ── 日志区 ──
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(80)
        self.log_edit.setStyleSheet(_LOG_STYLE)
        self.log_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_edit.setFont(QFont("Consolas", 10))
        layout.addWidget(self.log_edit)

        # ── 进度条 ──
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(_BAR_STYLE)
        layout.addWidget(self.progress)

        # ── 提示 ──
        hint = QLabel("Loading...")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(_HINT_STYLE)
        layout.addWidget(hint)

        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2
            )

    def append_log(self, text: str):
        """追加一行启动日志"""
        self.log_edit.append(text)
        # 自动滚到底部
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())
        QApplication.instance().processEvents()

    def set_progress(self, value: int, text: str = ""):
        """更新进度条"""
        self.progress.setValue(value)
        # 找到 hint label 并更新
        for child in self.children():
            if isinstance(child, QLabel) and child.styleSheet() == _HINT_STYLE:
                child.setText(text)
                break
        QApplication.instance().processEvents()

    def close_splash(self):
        """关闭闪屏"""
        self.close()
