"""
启动动画 — ASCII 字符拼成的 BNOS + 左下角日志 + 进度条
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QProgressBar, QTextEdit, QApplication, QFrame)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

# ── ASCII Art: BNOS (6行) ──
ASCII_BNOS = [
    " █████╗     ███╗  ██╗     █████╗     ██████╗ ",
    " ██╔══██╗   ████╗ ██║    ██╔══██╗   ██╔════╝ ",
    " ██████╔╝   ██╔██╗██║    ██║  ██║   ╚█████╗  ",
    " ██╔══██╗   ██║╚████║    ██║  ██║    ╚═══██╗ ",
    " ██████╔╝   ██║ ╚███║    ╚█████╔╝   ██████╔╝ ",
    " ╚═════╝    ╚═╝  ╚══╝     ╚════╝    ╚═════╝  ",
]

_LOG_STYLE = ("QTextEdit { background-color: transparent; color: #aaa; border: none; "
              "font-family: Consolas; font-size: 10px; }")
_BAR_STYLE = """
QProgressBar { background: #2a2a2a; border: 1px solid #555; border-radius: 2px; height: 8px; text-align: center; }
QProgressBar::chunk { background: #777; border-radius: 1px; }
"""
_HINT_STYLE = "color: #888; font-size: 10px; background: transparent;"


class SplashScreen(QWidget):
    """启动闪屏 — 居中屏幕，ASCII 标题 + 日志 + 进度条"""

    _CONTENT_W = 600
    _CONTENT_H = 330
    _BORDER = 3

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self._CONTENT_W + self._BORDER * 2,
                          self._CONTENT_H + self._BORDER * 2)

        # 外框透明，内框有边
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── 内容容器（带可见边框）──
        inner = QFrame(self)
        inner.setStyleSheet(
            f"QFrame {{ background-color: #1e1e1e; border: {self._BORDER}px solid #777; "
            f"border-radius: 8px; }}"
        )
        inner.setFixedSize(self._CONTENT_W, self._CONTENT_H)
        outer.addWidget(inner, 0, Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(inner)
        layout.setContentsMargins(20, 10, 20, 14)
        layout.setSpacing(6)

        # ── ASCII Art ──
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

        console_sub = QLabel("BNOS  CONSOLE")
        console_sub.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        console_sub.setStyleSheet("color: #ccc; background: transparent; letter-spacing: 3px;")
        console_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(console_sub)

        from ui.core.i18n import t
        sub = QLabel(t("_k_splash_subtitle"))
        sub.setFont(QFont("Consolas", 9))
        sub.setStyleSheet("color: #aaa; background: transparent; letter-spacing: 1px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(sub)

        layout.addWidget(title_widget, 1)

        # ── 日志 ──
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
        self.log_edit.append(text)
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())
        QApplication.instance().processEvents()

    def set_progress(self, value: int, text: str = ""):
        self.progress.setValue(value)
        for child in self.children():
            if isinstance(child, QLabel) and child.styleSheet() == _HINT_STYLE:
                child.setText(text)
                break
        QApplication.instance().processEvents()

    def close_splash(self):
        self.close()
