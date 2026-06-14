"""
参数控件基类 + 辅助函数 + 视觉常量 — 共享基础层
"""
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, Signal

from ui.core.node_config_parser import ParameterDef


# ========== 统一视觉常量（单一间距来源，便于维护） ==========
ROW_HEIGHT = 24
CONTROL_HEIGHT = 22
LAYOUT_SPACING = 4
VALUE_LABEL_WIDTH = 40
LEFT_MARGIN = 10
RIGHT_MARGIN = 10
MIN_CONTROL_WIDTH = 120
LABEL_MIN_WIDTH = 40


# ========== 深色主题控件样式（用于嵌入画布上的节点） ==========
DARK_CONTROL_QSS = """
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    padding: 2px 4px;
    selection-background-color: #094771;
    selection-color: #ffffff;
}
QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #007acc;
}
QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    color: #e0e0e0;
    selection-background-color: #094771;
    border: 1px solid #3a3a3a;
}
QCheckBox {
    color: #cccccc;
    background: transparent;
}
QPushButton {
    background-color: #3a3a3a;
    color: #e0e0e0;
    border: 1px solid #555555;
    border-radius: 3px;
    padding: 2px 8px;
}
QPushButton:hover {
    background-color: #4a4a4a;
}
"""


def _make_label(text, font=None) -> QLabel:
    """创建参数标签：右对齐，最小宽度由内容决定（字体测量），深色主题文字色"""
    label = QLabel(text)
    if font:
        label.setFont(font)
    fm = label.fontMetrics()
    text_width = fm.horizontalAdvance(text)
    label.setFixedWidth(max(LABEL_MIN_WIDTH, text_width + 8))
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    label.setStyleSheet("color: #cccccc; background: transparent;")
    return label


def _apply_dark_style(widget):
    """为控件统一应用深色主题样式"""
    widget.setStyleSheet(DARK_CONTROL_QSS)
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)


class ParameterWidget(QWidget):
    """参数控件基类 — 封装统一的尺寸/布局/信号规范

    关键：控件宽度由父级（NodeItem）决定，这里只约束高度，
    这样节点宽度可以跟随内容（最长标签 + 最长控件）自动扩张。
    """
    value_changed = Signal(str, object)

    def row_height(self):
        return self.height() or ROW_HEIGHT

    def __init__(self, param: ParameterDef, current_value=None):
        super().__init__()
        self.param = param
        self._current = current_value if current_value is not None else param.default

    def _apply_row_height(self, h: int = ROW_HEIGHT):
        """参数行高度统一 — 不限制宽度（让 QVBoxLayout 横向填满容器）"""
        self.setMinimumHeight(h)
        _apply_dark_style(self)

    def get_value(self):
        return self._current

    def set_value(self, value):
        raise NotImplementedError

    def _emit(self, value):
        self._current = value
        self.value_changed.emit(self.param.name, value)

    @classmethod
    def create(cls, param: ParameterDef, current_value=None):
        """工厂方法 — 按 param.type 分发到对应的 Widget 类"""
        from . import WidgetRegistry
        widget_cls = WidgetRegistry.get(param.type)
        return widget_cls(param, current_value)
