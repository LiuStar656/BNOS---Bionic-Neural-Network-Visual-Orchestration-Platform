"""范围滑块控件"""
from PySide6.QtWidgets import QSlider, QLabel, QHBoxLayout
from PySide6.QtCore import Qt
from ._base import ParameterWidget, _make_label, ROW_HEIGHT, LAYOUT_SPACING, VALUE_LABEL_WIDTH


class RangeWidget(ParameterWidget):
    def __init__(self, param, current_value):
        super().__init__(param, current_value)
        self._apply_row_height(ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(_make_label(param.label))
        self._slider = QSlider(Qt.Orientation.Horizontal)
        mn = int(param.min) if param.min is not None else 0
        mx = int(param.max) if param.max is not None else 100
        self._slider.setRange(mn, mx)
        try:
            self._slider.setValue(int(current_value))
        except (ValueError, TypeError):
            self._slider.setValue(mn)
        self._value_label = QLabel(str(self._slider.value()))
        self._value_label.setFixedWidth(VALUE_LABEL_WIDTH)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._value_label)

    def _on_slider(self, v):
        self._value_label.setText(str(v))
        self._emit(v)

    def get_value(self):
        return self._slider.value()

    def set_value(self, value):
        try:
            self._slider.blockSignals(True)
            self._slider.setValue(int(value))
            self._slider.blockSignals(False)
            self._value_label.setText(str(value))
            self._current = value
        except (ValueError, TypeError):
            pass
