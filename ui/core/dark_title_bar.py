"""
VSCode 风格的深色自定义标题栏
标题 + 菜单栏 + 窗口按钮 同排，支持拖动、最小化、最大化/还原、关闭
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QMenuBar
from PyQt6.QtCore import Qt, QPoint, pyqtSignal


class DarkTitleBar(QWidget):
    """VSCode 风格深色标题栏"""

    minimize_clicked = pyqtSignal()
    maximize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()

    def __init__(self, parent=None, title="BnosConsole", menubar=None):
        super().__init__(parent)
        self._parent_window = parent
        self._is_maximized = False
        self._drag_pos = None

        self.setFixedHeight(40)
        self.setObjectName("darkTitleBar")

        self._init_ui(title, menubar)
        self._apply_styles()

    def _init_ui(self, title, menubar):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 标题
        self.title_label = QLabel(title)
        self.title_label.setObjectName("titleBarTitle")
        self.title_label.setFixedHeight(40)
        layout.addWidget(self.title_label)

        # 菜单栏
        if menubar:
            menubar.setObjectName("titleBarMenu")
            menubar.setNativeMenuBar(False)
            menubar.setFixedHeight(40)
            layout.addWidget(menubar)

        layout.addStretch(1)

        # 最小化
        self.min_btn = QPushButton("─")
        self.min_btn.setObjectName("titleBarMinBtn")
        self.min_btn.setFixedSize(50, 40)
        self.min_btn.clicked.connect(self.minimize_clicked.emit)
        layout.addWidget(self.min_btn)

        # 最大化/还原
        self.max_btn = QPushButton("□")
        self.max_btn.setObjectName("titleBarMaxBtn")
        self.max_btn.setFixedSize(50, 40)
        self.max_btn.clicked.connect(self._on_max_clicked)
        layout.addWidget(self.max_btn)

        # 关闭
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("titleBarCloseBtn")
        self.close_btn.setFixedSize(50, 40)
        self.close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(self.close_btn)

    def _apply_styles(self):
        self.setStyleSheet("""
            #darkTitleBar {
                background-color: #1e1e1e;
                border-bottom: 1px solid #3c3c3c;
            }
            #titleBarTitle {
                color: #cccccc;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                padding: 0px 12px 3px 12px;
            }
            #darkTitleBar QPushButton {
                background-color: transparent;
                border: none;
                color: #cccccc;
                font-size: 16px;
                font-family: 'Segoe UI', sans-serif;
            }
            #darkTitleBar QPushButton:hover {
                background-color: #3a3a3a;
            }
            QPushButton#titleBarMaxBtn {
                font-size: 25px;
                padding: 0px 0px 6px 0px;
            }
            #titleBarCloseBtn:hover {
                background-color: #e81123 !important;
                color: white;
            }
            #titleBarMenu {
                background-color: transparent;
                color: #cccccc;
                font-size: 13px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                padding: 0px;
                margin: 0px;
            }
            #titleBarMenu::item {
                padding: 10px 12px;
                background-color: transparent;
                border-radius: 4px;
            }
            #titleBarMenu::item:selected {
                background-color: #3a3a3a;
            }
            QMenu {
                background-color: #252526;
                color: #cccccc;
                border: 1px solid #454545;
                padding: 4px 0px;
                font-size: 13px;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            }
            QMenu::item {
                padding: 8px 32px 8px 16px;
            }
            QMenu::item:selected {
                background-color: #094771;
            }
            QMenu::separator {
                height: 1px;
                background-color: #454545;
                margin: 4px 8px;
            }
        """)

    def _on_max_clicked(self):
        if self._is_maximized:
            self.max_btn.setText("□")
            self._is_maximized = False
        else:
            self.max_btn.setText("❐")
            self._is_maximized = True
        self.maximize_clicked.emit()

    def set_maximized_state(self, is_maximized):
        self._is_maximized = is_maximized
        self.max_btn.setText("❐" if is_maximized else "□")

    def set_title(self, title):
        self.title_label.setText(title)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            if self._parent_window:
                delta = event.globalPosition().toPoint() - self._drag_pos
                self._parent_window.move(self._parent_window.pos() + delta)
                self._drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_max_clicked()
            event.accept()
