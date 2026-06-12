"""目录选择器控件"""
from PyQt6.QtWidgets import QLineEdit, QPushButton, QHBoxLayout, QFileDialog
from PyQt6.QtCore import Qt
from ._base import ParameterWidget, _make_label, ROW_HEIGHT, CONTROL_HEIGHT, LAYOUT_SPACING, MIN_CONTROL_WIDTH


class DirPickerWidget(ParameterWidget):
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
        self._btn = QPushButton("…")
        self._btn.setFixedWidth(28)
        self._btn.setFixedHeight(CONTROL_HEIGHT)
        self._btn.clicked.connect(self._pick_dir)
        layout.addWidget(self._edit, 1)
        layout.addWidget(self._btn)

    def _pick_dir(self):
        path = QFileDialog.getExistingDirectory(self, self.param.label)
        if path:
            self._edit.setText(path)

    def get_value(self):
        return self._edit.text()

    def set_value(self, value):
        self._current = value
        self._edit.blockSignals(True)
        self._edit.setText(str(value or ""))
        self._edit.blockSignals(False)
