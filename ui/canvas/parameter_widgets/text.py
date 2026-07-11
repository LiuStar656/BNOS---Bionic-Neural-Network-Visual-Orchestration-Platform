"""多行文本输入控件"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPlainTextEdit

from ._base import LAYOUT_SPACING, ROW_HEIGHT, ParameterWidget, _make_label


class TextWidget(ParameterWidget):
    """多行文本 — 紧凑模式：标签 + 小尺寸编辑框（根据 rows 扩展高度）"""

    def __init__(self, param, current_value):
        super().__init__(param, current_value)
        rows = max(1, int(param.rows)) if param.rows else 1
        widget_h = ROW_HEIGHT + max(0, (rows - 1) * 22)
        self._apply_row_height(widget_h)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(_make_label(param.label))
        self._edit = QPlainTextEdit()
        self._edit.setPlainText(str(current_value or ""))
        self._edit.textChanged.connect(lambda: self._emit(self._edit.toPlainText()))
        layout.addWidget(self._edit, 1)

    def get_value(self):
        return self._edit.toPlainText()

    def set_value(self, value):
        self._current = value
        self._edit.blockSignals(True)
        self._edit.setPlainText(str(value or ""))
        self._edit.blockSignals(False)
