"""
绘图工具栏 — PS 风格左侧竖式，滚轮滚动，宽度 36px
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QScrollArea,
                              QColorDialog, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal


TOOL_W = 36
BTN_H  = 32

TOOLS = [
    ("rect",       "□",  "矩形(R)"),
    ("round_rect", "◻",  "圆角矩形"),
    ("polygon",    "◇",  "多边形(P)"),
    ("arrow",      "→",  "箭头(A)"),
    ("text",       "T",  "文字(T)"),
]

BTN_BASE = """
QPushButton {
    background: #3c3c3c; color: #999; border: none;
    border-radius: 3px; font-size: 13px; min-height: 28px;
}
QPushButton:hover { background: #505050; color: #fff; }
"""

BTN_ON = "QPushButton { background: #007acc; color: #fff; border: none; border-radius: 3px; font-size: 13px; }"


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
        self.setStyleSheet("background-color: #2d2d30; border-right: 1px solid #3e3e42;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar:vertical { width: 4px; }")
        main_layout.addWidget(scroll, 1)  # stretch=1 fill all space
        self._scroll = scroll

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(2)

        self._btns = {}
        self._current_tool = None

        # 工具按钮
        for tid, icon, tip in TOOLS:
            btn = QPushButton(icon)
            btn.setFixedHeight(BTN_H)
            btn.setToolTip(tip)
            btn.setStyleSheet(BTN_BASE)
            btn.clicked.connect(lambda checked, t=tid: self._pick(t))
            layout.addWidget(btn)
            self._btns[tid] = btn

        # 分隔
        s1 = QLabel("─" * 3); s1.setStyleSheet("color: #555; font-size: 7px; padding: 2px 0;")
        s1.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(s1)

        # 样式
        self._stroke_btn = self._mk_btn("⊙", "描边颜色", layout)
        self._stroke_btn.clicked.connect(self._pick_stroke)
        self._fill_btn = self._mk_btn("◉", "填充颜色", layout)
        self._fill_btn.clicked.connect(self._pick_fill)

        s2 = QLabel("─" * 3); s2.setStyleSheet("color: #555; font-size: 7px; padding: 2px 0;")
        s2.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(s2)

        # 图层控制
        self._lock_btn = self._mk_btn("🔒", "锁定绘图层", layout)
        self._lock_btn.clicked.connect(lambda: self._toggle_lock())

        self._hide_btn = self._mk_btn("👁", "显示/隐藏", layout)
        self._hide_btn.clicked.connect(lambda: self._toggle_visible())

        s3 = QLabel("─" * 3); s3.setStyleSheet("color: #555; font-size: 7px; padding: 2px 0;")
        s3.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(s3)

        # 操作
        self._mk_btn("↩", "撤销", layout).clicked.connect(lambda: self.undo_requested.emit())
        self._mk_btn("↪", "重做", layout).clicked.connect(lambda: self.redo_requested.emit())

        s4 = QLabel("─" * 3); s4.setStyleSheet("color: #555; font-size: 7px; padding: 2px 0;")
        s4.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(s4)

        del_btn = self._mk_btn("✕", "删除选中", layout)
        del_btn.setStyleSheet(BTN_BASE + "QPushButton:hover { background: #a00; color: #fff; }")
        del_btn.clicked.connect(lambda: self.delete_requested.emit())

        clr_btn = self._mk_btn("⌫", "清空全部", layout)
        clr_btn.setStyleSheet(BTN_BASE + "QPushButton:hover { background: #a00; color: #fff; }")
        clr_btn.clicked.connect(lambda: self.clear_requested.emit())

        layout.addStretch()
        scroll.setWidget(container)
        self._locked = False
        self._visible = True

    def _mk_btn(self, icon, tip, layout):
        btn = QPushButton(icon)
        btn.setFixedHeight(BTN_H)
        btn.setToolTip(tip)
        btn.setStyleSheet(BTN_BASE)
        layout.addWidget(btn)
        return btn

    def _pick(self, tid):
        if self._current_tool == tid:
            # 取消选择
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
        self._lock_btn.setStyleSheet(BTN_ON if self._locked else BTN_BASE)
        self._lock_btn.setText("🔒" if not self._locked else "🔏")
        self.layer_locked.emit(self._locked)

    def _toggle_visible(self):
        self._visible = not self._visible
        self._hide_btn.setStyleSheet(BTN_BASE + "QPushButton { color: #666; }" if not self._visible else BTN_BASE)
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
