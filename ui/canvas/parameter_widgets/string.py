"""字符串输入控件"""
from PySide6.QtWidgets import QLineEdit, QHBoxLayout
from PySide6.QtCore import Qt
from ._base import ParameterWidget, _make_label, ROW_HEIGHT, CONTROL_HEIGHT, LAYOUT_SPACING, MIN_CONTROL_WIDTH


class StringWidget(ParameterWidget):
    def __init__(self, param, current_value):
        super().__init__(param, current_value)
        self._apply_row_height(ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(_make_label(param.label))
        self._edit = QLineEdit(str(current_value or ""))
        self._edit.setMinimumHeight(CONTROL_HEIGHT)
        self._edit.setMinimumWidth(MIN_CONTROL_WIDTH)
        self._edit.textChanged.connect(lambda v: self._emit(v))
        layout.addWidget(self._edit, 1)

    def get_value(self):
        return self._edit.text()

    def set_value(self, value):
        self._current = value
        self._edit.blockSignals(True)
        self._edit.setText(str(value or ""))
        self._edit.blockSignals(False)
