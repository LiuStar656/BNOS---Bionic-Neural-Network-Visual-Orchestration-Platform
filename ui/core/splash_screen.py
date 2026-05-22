"""
启动动画 — ASCII 字符拼成的 BNOS + 左下角日志 + 进度条
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QProgressBar, QTextEdit, QApplication)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

# ── ASCII Art: BNOS (6行) ──
ASCII_BNOS = [
    " █████╗     ███╗  ██╗     █████╗     ██████╗ ",
    " ██╔══██╗   ████╗ ██║    ██╔══██╗   ██╔════╝ ",
    " ██████╔╝   ██╔██╗██║    ██║  ██║   ╚█████╗  ",
    " ██╔══██╗   ██║╚████║    ██║  ██║    ╚═══██╗ ",
    " ██████╔╝   ██║ ╚███║    ╚█████╔╝   ██████╔╝ ",
    " ╚═════╝    ╚═╝  ╚══╝     ╚════╝    ╚═════╝  ",
]

_BAR_STYLE = """
QProgressBar { background: #2a2a2a; border: 1px solid #555; border-radius: 2px; height: 8px; text-align: center; }
QProgressBar::chunk { background: #777; border-radius: 1px; }
"""


class SplashScreen(QWidget):
    """启动闪屏 — 外边框可见，内部纯内容"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(620, 346)

        # 外框样式：透明背景 + 纯外边框
        self.setStyleSheet(
            "SplashScreen { background-color: transparent; "
            "border: 3px solid #777; border-radius: 8px; }"
        )

        # 内容区（内边距避开边框）
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(6)

        # ── ASCII Art ──
        for line in ASCII_BNOS:
            lbl = QLabel(line)
            lbl.setFont(QFont("Consolas", 13, QFont.Weight.Bold))
            lbl.setStyleSheet("color: #ffffff; background: transparent; border: none;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)

        # BNOS CONSOLE
        console_sub = QLabel("BNOS  CONSOLE")
        console_sub.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
        console_sub.setStyleSheet("color: #ccc; background: transparent; border: none; letter-spacing: 3px;")
        console_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(console_sub)

        # 描述
        from ui.core.i18n import t
        sub = QLabel(t("_k_splash_subtitle"))
        sub.setFont(QFont("Consolas", 9))
        sub.setStyleSheet("color: #aaa; background: transparent; border: none;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        layout.addStretch(1)

        # ── 日志 ──
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(80)
        self.log_edit.setStyleSheet(
            "QTextEdit { background-color: transparent; color: #aaa; border: none; "
            "font-family: Consolas; font-size: 10px; }")
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
        self._hint = QLabel("Loading...")
        self._hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint.setStyleSheet("color: #888; font-size: 10px; background: transparent; border: none;")
        layout.addWidget(self._hint)

        self._fill_bg()

        self.center_on_screen()

    def _fill_bg(self):
        """绘制不透明背景（边框内部）"""
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        # 背景填充用 stylesheet 做不了透明+不透明混合，改用子 widget
        # 简化方案：background 直接走 widget 的样式
        pass

    def paintEvent(self, event):
        """自绘背景，只填充内部区域"""
        from PyQt6.QtGui import QPainter, QBrush, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 背景（避开边框 3px）
        margin = 3
        r = self.rect().adjusted(margin, margin, -margin, -margin)
        p.setBrush(QColor("#1e1e1e"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 5, 5)

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
        self._hint.setText(text)
        QApplication.instance().processEvents()

    def close_splash(self):
        self.close()
