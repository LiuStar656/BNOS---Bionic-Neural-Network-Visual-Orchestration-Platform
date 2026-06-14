"""浮点数输入控件"""
from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout
from PySide6.QtCore import Qt
from ._base import ParameterWidget, _make_label, ROW_HEIGHT, CONTROL_HEIGHT, LAYOUT_SPACING, MIN_CONTROL_WIDTH


class FloatWidget(ParameterWidget):
    def __init__(self, param, current_value):
        super().__init__(param, current_value)
        self._apply_row_height(ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(_make_label(param.label))
        self._spin = QDoubleSpinBox()
        self._spin.setMinimumHeight(CONTROL_HEIGHT)
        self._spin.setMinimumWidth(MIN_CONTROL_WIDTH)
        self._spin.setDecimals(param.decimals)
        if param.min is not None:
            self._spin.setMinimum(param.min)
        if param.max is not None:
            self._spin.setMaximum(param.max)
        if param.step is not None:
            self._spin.setSingleStep(param.step)
        try:
            self._spin.setValue(float(current_value))
        except (ValueError, TypeError):
            self._spin.setValue(0.0)
        self._spin.valueChanged.connect(lambda v: self._emit(v))
        layout.addWidget(self._spin, 1)

    def get_value(self):
        return self._spin.value()

    def set_value(self, value):
        try:
            self._spin.blockSignals(True)
            self._spin.setValue(float(value))
            self._spin.blockSignals(False)
            self._current = value
        except (ValueError, TypeError):
            pass
