"""
启动动画 — ASCII 字符拼成的 BNOS + 左下角日志 + 进度条
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                               QProgressBar, QTextEdit, QApplication)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

ASCII_BNOS = [
    " █████╗     ███╗  ██╗     █████╗     ██████╗ ",
    " ██╔══██╗   ████╗ ██║    ██╔══██╗   ██╔════╝ ",
    " ██████╔╝   ██╔██╗██║    ██║  ██║   ╚█████╗  ",
    " ██╔══██╗   ██║╚████║    ██║  ██║    ╚═══██╗ ",
    " ██████╔╝   ██║ ╚███║    ╚█████╔╝   ██████╔╝ ",
    " ╚═════╝    ╚═╝  ╚══╝     ╚════╝    ╚═════╝  ",
]


class SplashScreen(QWidget):
    """启动闪屏 — 外边框可见，内部无任何边框"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setFixedSize(620, 346)
        self.setStyleSheet(
            "SplashScreen {"
            "  background-color: #1e1e1e;"
            "  border: 3px solid #777;"
            "  border-radius: 8px;"
            "}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(6)

        for line in ASCII_BNOS:
            lbl = QLabel(line)
            lbl.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #fff; background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)

        cs = QLabel("BNOS  CONSOLE")
        cs.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        cs.setStyleSheet("color: #ccc; background: transparent; border: none; letter-spacing: 3px;")
        cs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(cs)

        from ui.core.i18n import t
        sub = QLabel(t("_k_splash_subtitle"))
        sub.setFont(QFont("Consolas", 9))
        sub.setStyleSheet("color: #aaa; background: transparent; border: none;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        layout.addStretch(1)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(80)
        self.log_edit.setStyleSheet(
            "QTextEdit { background: transparent; color: #aaa; border: none;"
            " font-family: Consolas; font-size: 10px; }")
        self.log_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.log_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.log_edit)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            "QProgressBar { background: #2a2a2a; border: none; border-radius: 2px; height: 8px; }"
            "QProgressBar::chunk { background: #777; border-radius: 1px; }")
        layout.addWidget(self.progress)

        self._hint = QLabel("Loading...")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet("color: #888; font-size: 10px; background: transparent; border: none;")
        layout.addWidget(self._hint)

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
        # 注意：QTextEdit.append 会自动触发 repaint，无需手动 processEvents
        # processEvents 可能导致信号重入递归，已移除
        self.log_edit.append(text)
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_progress(self, value: int, text: str = ""):
        # QProgressBar.setValue / QLabel.setText 会自动触发 repaint
        # processEvents 已移除，避免主线程信号重入
        self.progress.setValue(value)
        self._hint.setText(text)

    def close_splash(self):
        self.close()
