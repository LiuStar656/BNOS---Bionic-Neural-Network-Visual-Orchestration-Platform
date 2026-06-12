"""枚举下拉选择控件"""
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtCore import Qt
from ._base import ParameterWidget, _make_label, ROW_HEIGHT, CONTROL_HEIGHT, LAYOUT_SPACING, MIN_CONTROL_WIDTH
from ._proxy_combo import _ProxyAwareComboBox


class EnumWidget(ParameterWidget):
    def __init__(self, param, current_value):
        super().__init__(param, current_value)
        self._apply_row_height(ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(_make_label(param.label))
        self._combo = _ProxyAwareComboBox()
        self._combo.setMinimumHeight(CONTROL_HEIGHT)
        self._combo.setMinimumWidth(MIN_CONTROL_WIDTH)
        self._combo.addItems(param.options)
        if current_value in param.options:
            self._combo.setCurrentText(str(current_value))
        self._combo.currentTextChanged.connect(lambda v: self._emit(v))
        layout.addWidget(self._combo, 1)

    def get_value(self):
        return self._combo.currentText()

    def set_value(self, value):
        if value in self.param.options:
            self._combo.blockSignals(True)
            self._combo.setCurrentText(str(value))
            self._combo.blockSignals(False)
            self._current = value
