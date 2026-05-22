"""
绘图工具栏 — PS 风格左侧竖式，匹配菜单栏深色主题
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QScrollArea,
                              QColorDialog, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


TOOL_W = 40          # 工具栏宽度（够按钮显示）
BTN_H  = 34          # 按钮高度
FONT   = QFont("Consolas", 12)

# 配色：与菜单栏/标题栏统一
BG_TOOLBAR   = "#1e1e1e"
BG_BTN       = "#252525"      # 按键融入工具栏
FG_BTN       = "#aaaaaa"
BG_BTN_ON    = "#007acc"
FG_BTN_ON    = "#ffffff"
BG_DANGER    = "#c03030"
BORDER       = "#3e3e42"
SEPARATOR    = "#3e3e42"

TOOLS = [
    ("rect",       "▯",  "矩形"),
    ("round_rect", "◰",  "圆角矩形"),
    ("polygon",    "⬠",  "多边形"),
    ("arrow",      "➤",  "箭头"),
    ("text",       "T",  "文字"),
]

BTN_BASE = f"""
QPushButton {{
    background: {BG_BTN}; color: {FG_BTN};
    border: none; border-left: 3px solid transparent;
    font-size: 14px; font-weight: bold;
    min-height: {BTN_H-4}px; max-height: {BTN_H-4}px;
    text-align: center;
}}
QPushButton:hover {{ background: #333333; }}
"""

BTN_ON = f"""
QPushButton {{
    background: {BG_BTN}; color: {FG_BTN_ON};
    border: none; border-left: 3px solid {BG_BTN_ON};
    font-size: 14px; font-weight: bold;
    min-height: {BTN_H-4}px; max-height: {BTN_H-4}px;
    text-align: center;
}}
"""


class DrawToolbar(QWidget):
    """绘图工具条"""

    tool_changed   = pyqtSignal(str)
    style_changed  = pyqtSignal(str, object)
    layer_locked   = pyqtSignal(bool)
    layer_visible  = pyqtSignal(bool)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()
    delete_requested = pyqtSignal()
    clear_requested  = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(TOOL_W)
        self.setStyleSheet(f"DrawToolbar {{ background-color: {BG_TOOLBAR}; border-right: 2px solid {BORDER}; }}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; }} QScrollBar:vertical {{ width: 3px; background: {BG_TOOLBAR}; }}")
        main_layout.addWidget(scroll, 1)
        self._scroll = scroll

        container = QWidget()
        container.setStyleSheet(f"background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(3, 4, 3, 4)
        layout.setSpacing(2)

        self._btns = {}
        self._current_tool = None

        for tid, icon, tip in TOOLS:
            btn = QPushButton(icon)
            btn.setFont(FONT)
            btn.setFixedHeight(BTN_H)
            btn.setToolTip(tip)
            btn.setStyleSheet(BTN_BASE)
            btn.clicked.connect(lambda checked, t=tid: self._pick(t))
            layout.addWidget(btn)
            self._btns[tid] = btn

        self._sep(layout)

        self._stroke_btn = self._mk_btn("S", "描边颜色", layout)
        self._stroke_btn.clicked.connect(self._pick_stroke)
        self._fill_btn = self._mk_btn("F", "填充颜色", layout)
        self._fill_btn.clicked.connect(self._pick_fill)

        self._sep(layout)

        self._lock_btn = self._mk_btn("L", "锁定绘图层", layout)
        self._lock_btn.clicked.connect(lambda: self._toggle_lock())
        self._hide_btn = self._mk_btn("V", "显示/隐藏", layout)
        self._hide_btn.clicked.connect(lambda: self._toggle_visible())

        self._sep(layout)

        self._mk_btn("<", "撤销", layout).clicked.connect(lambda: self.undo_requested.emit())
        self._mk_btn(">", "重做", layout).clicked.connect(lambda: self.redo_requested.emit())

        self._sep(layout)

        d = self._mk_btn("X", "删除选中", layout)
        d.setStyleSheet(BTN_BASE + f"QPushButton:hover {{ background: {BG_DANGER}; color: #fff; }}")
        d.clicked.connect(lambda: self.delete_requested.emit())

        c = self._mk_btn("C", "清空全部", layout)
        c.setStyleSheet(BTN_BASE + f"QPushButton:hover {{ background: {BG_DANGER}; color: #fff; }}")
        c.clicked.connect(lambda: self.clear_requested.emit())

        layout.addStretch()
        scroll.setWidget(container)

        self._locked = False
        self._visible = True

    def _sep(self, layout):
        s = QLabel()
        s.setFixedHeight(1)
        s.setStyleSheet(f"background-color: {SEPARATOR}; margin: 3px 2px;")
        layout.addWidget(s)

    def _mk_btn(self, icon, tip, layout):
        btn = QPushButton(icon)
        btn.setFont(FONT)
        btn.setFixedHeight(BTN_H)
        btn.setToolTip(tip)
        btn.setStyleSheet(BTN_BASE)
        layout.addWidget(btn)
        return btn

    def _pick(self, tid):
        if self._current_tool == tid:
            self._btns[tid].setStyleSheet(BTN_BASE)
            self._current_tool = None
            self.tool_changed.emit("")
        else:
            if self._current_tool and self._current_tool in self._btns:
                self._btns[self._current_tool].setStyleSheet(BTN_BASE)
            self._current_tool = tid
            self._btns[tid].setStyleSheet(BTN_ON)
            self.tool_changed.emit(tid)

    def _toggle_lock(self):
        self._locked = not self._locked
        if self._locked:
            self._lock_btn.setStyleSheet(BTN_ON)
        else:
            self._lock_btn.setStyleSheet(BTN_BASE)
        self.layer_locked.emit(self._locked)

    def _toggle_visible(self):
        self._visible = not self._visible
        if not self._visible:
            self._hide_btn.setStyleSheet(f"""
                QPushButton {{ background: {BG_BTN}; color: #555555;
                    border: none; border-left: 3px solid transparent;
                    font-size: 14px; font-weight: bold; min-height: 30px; max-height: 30px; }}
            """)
        else:
            self._hide_btn.setStyleSheet(BTN_BASE)
        self.layer_visible.emit(self._visible)

    def _pick_stroke(self):
        c = QColorDialog.getColor()
        if c.isValid():
            self.style_changed.emit("stroke", c.name())

    def _pick_fill(self):
        c = QColorDialog.getColor()
        if c.isValid():
            self.style_changed.emit("fill", c.name())

    def showEvent(self, event):
        super().showEvent(event)
        if self.parent():
            self.setGeometry(0, 0, TOOL_W, self.parent().height())

    def wheelEvent(self, event):
        if self._scroll:
            bar = self._scroll.verticalScrollBar()
            bar.setValue(bar.value() - event.angleDelta().y())
