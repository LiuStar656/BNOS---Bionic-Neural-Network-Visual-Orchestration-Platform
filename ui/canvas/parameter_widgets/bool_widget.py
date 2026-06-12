"""布尔值复选框控件"""
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout
from PyQt6.QtCore import Qt
from ._base import ParameterWidget, _make_label, ROW_HEIGHT, LAYOUT_SPACING


class BoolWidget(ParameterWidget):
    def __init__(self, param, current_value):
        super().__init__(param, current_value)
        self._apply_row_height(ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(_make_label(""))
        self._check = QCheckBox(param.label)
        self._check.setChecked(bool(current_value))
        self._check.toggled.connect(lambda v: self._emit(v))
        layout.addWidget(self._check, 1)

    def get_value(self):
        return self._check.isChecked()

    def set_value(self, value):
        self._check.blockSignals(True)
        self._check.setChecked(bool(value))
        self._check.blockSignals(False)
        self._current = value
