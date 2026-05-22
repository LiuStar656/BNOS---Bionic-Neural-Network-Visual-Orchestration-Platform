"""
绘图工具栏 — PS 风格左侧竖式，滚轮滚动，宽度 ≤ BNOS logo

嵌入画布进程左侧，固定宽 36px。
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QScrollArea,
                              QColorDialog, QInputDialog, QLabel, QSlider)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


TOOL_W = 36   # 工具栏宽度
BTN_H  = 32   # 按钮高度


class DrawToolbar(QWidget):
    """绘图工具条 — 竖式 PS 风格"""

    tool_changed   = pyqtSignal(str)     # 工具切换
    style_changed  = pyqtSignal(str, object)  # 样式变更 (key, value)
    layer_locked   = pyqtSignal(bool)
    layer_visible  = pyqtSignal(bool)
    undo_requested = pyqtSignal()
    redo_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(TOOL_W)
        self.setStyleSheet("background-color: #2d2d30; border-right: 1px solid #3e3e42;")

        # 滚动区域包裹
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 4px; }")
        scroll.setGeometry(0, 0, TOOL_W, parent.height() if parent else 600)
        self._scroll = scroll

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(2)
        layout.addStretch()

        self._btns = {}
        self._current_tool = None

        btn_style = """
            QPushButton {
                background: #3c3c3c; color: #ccc; border: none;
                border-radius: 3px; font-size: 11px; min-height: 30px;
            }
            QPushButton:hover { background: #505050; }
            QPushButton:checked { background: #007acc; color: #fff; }
        """

        tools = [
            ("rect",      "□"),
            ("round_rect","▢"),
            ("polygon",   "⬠"),
            ("arrow",     "→"),
            ("text",      "T"),
        ]
        for tid, icon in tools:
            btn = QPushButton(icon)
            btn.setCheckable(True)
            btn.setFixedHeight(BTN_H)
            btn.setToolTip(tid)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked, t=tid: self._on_tool(t))
            layout.addWidget(btn)
            self._btns[tid] = btn

        layout.addSpacing(12)

        # 颜色按钮
        self._stroke_btn = QPushButton("◎")
        self._stroke_btn.setFixedHeight(BTN_H)
        self._stroke_btn.setStyleSheet(btn_style)
        self._stroke_btn.setToolTip("描边颜色")
        self._stroke_btn.clicked.connect(self._pick_stroke)
        layout.addWidget(self._stroke_btn)

        self._fill_btn = QPushButton("◉")
        self._fill_btn.setFixedHeight(BTN_H)
        self._fill_btn.setStyleSheet(btn_style)
        self._fill_btn.setToolTip("填充颜色")
        self._fill_btn.clicked.connect(self._pick_fill)
        layout.addWidget(self._fill_btn)

        layout.addSpacing(12)

        # 图层按钮
        self._lock_btn = QPushButton("🔒")
        self._lock_btn.setCheckable(True)
        self._lock_btn.setFixedHeight(BTN_H)
        self._lock_btn.setStyleSheet(btn_style)
        self._lock_btn.setToolTip("锁定绘图层")
        self._lock_btn.clicked.connect(lambda: self.layer_locked.emit(self._lock_btn.isChecked()))
        layout.addWidget(self._lock_btn)

        self._hide_btn = QPushButton("👁")
        self._hide_btn.setCheckable(True)
        self._hide_btn.setFixedHeight(BTN_H)
        self._hide_btn.setStyleSheet(btn_style)
        self._hide_btn.setToolTip("显示/隐藏绘图层")
        self._hide_btn.clicked.connect(lambda: self.layer_visible.emit(not self._hide_btn.isChecked()))
        layout.addWidget(self._hide_btn)

        layout.addSpacing(12)

        # 撤销/重做
        undo_btn = QPushButton("↩")
        undo_btn.setFixedHeight(BTN_H)
        undo_btn.setStyleSheet(btn_style)
        undo_btn.clicked.connect(lambda: self.undo_requested.emit())
        layout.addWidget(undo_btn)

        redo_btn = QPushButton("↪")
        redo_btn.setFixedHeight(BTN_H)
        redo_btn.setStyleSheet(btn_style)
        redo_btn.clicked.connect(lambda: self.redo_requested.emit())
        layout.addWidget(redo_btn)

        layout.addStretch()
        scroll.setWidget(container)

    def _on_tool(self, tid):
        if self._current_tool == tid:
            self._btns[tid].setChecked(False)
            self._current_tool = None
            self.tool_changed.emit("")
        else:
            if self._current_tool and self._current_tool in self._btns:
                self._btns[self._current_tool].setChecked(False)
            self._current_tool = tid
            self._btns[tid].setChecked(True)
            self.tool_changed.emit(tid)

    def _pick_stroke(self):
        c = QColorDialog.getColor()
        if c.isValid():
            self.style_changed.emit("stroke", c.name())
            self._stroke_btn.setStyleSheet(
                self._stroke_btn.styleSheet() + f"QPushButton {{ color: {c.name()}; }}")

    def _pick_fill(self):
        c = QColorDialog.getColor()
        if c.isValid():
            self.style_changed.emit("fill", c.name())
            self._fill_btn.setStyleSheet(
                self._fill_btn.styleSheet() + f"QPushButton {{ color: {c.name()}; }}")

    def resizeEvent(self, event):
        if self._scroll:
            self._scroll.setGeometry(0, 0, TOOL_W, self.height())

    def wheelEvent(self, event):
        if self._scroll:
            bar = self._scroll.verticalScrollBar()
            delta = event.angleDelta().y()
            bar.setValue(bar.value() - delta)
