"""颜色选择器控件"""
from PyQt6.QtWidgets import QLineEdit, QPushButton, QHBoxLayout, QColorDialog
from PyQt6.QtCore import Qt
from ._base import ParameterWidget, _make_label, ROW_HEIGHT, CONTROL_HEIGHT, LAYOUT_SPACING, MIN_CONTROL_WIDTH


class ColorWidget(ParameterWidget):
    def __init__(self, param, current_value):
        super().__init__(param, current_value)
        self._apply_row_height(ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(_make_label(param.label))
        self._btn = QPushButton()
        self._btn.setFixedSize(28, 22)
        color = str(current_value or "#FFFFFF")
        self._btn.setStyleSheet(f"background-color: {color}; border: 1px solid #555;")
        self._btn.clicked.connect(self._pick_color)
        self._value = QLineEdit(str(current_value or ""))
        self._value.setMinimumHeight(CONTROL_HEIGHT)
        self._value.setMinimumWidth(MIN_CONTROL_WIDTH)
        self._value.editingFinished.connect(lambda: self._emit(self._value.text()))
        layout.addWidget(self._btn)
        layout.addWidget(self._value, 1)

    def _pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            self._btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #555;")
            self._value.setText(hex_color)
            self._emit(hex_color)

    def get_value(self):
        return self._current

    def set_value(self, value):
        self._current = value
        self._btn.setStyleSheet(f"background-color: {str(value)}; border: 1px solid #555;")
        self._value.blockSignals(True)
        self._value.setText(str(value or ""))
        self._value.blockSignals(False)
