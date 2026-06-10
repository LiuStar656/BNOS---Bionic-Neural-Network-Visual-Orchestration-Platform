"""
画布参数控件库 — 将 config.json 中的参数定义渲染为 QWidget
通过 QGraphicsProxyWidget 嵌入画布上的节点

设计原则：
  - 统一行高（24px）、统一控件高度（22px）、统一标签宽度（56px）
  - 统一水平布局（HBox），所有类型对齐到同一视觉基线
  - 紧凑间距（spacing=4），减少视觉噪声
  - 标签右对齐 + 垂直居中，便于视觉分组
"""
import os
from PyQt6.QtWidgets import (QWidget, QLineEdit, QPlainTextEdit, QSpinBox,
    QDoubleSpinBox, QCheckBox, QComboBox, QSlider, QPushButton,
    QHBoxLayout, QVBoxLayout, QLabel, QFileDialog, QColorDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor

from ui.core.node_config_parser import ParameterDef


# ========== 统一视觉常量（单一间距来源，便于维护） ==========
# 注意：LABEL_WIDTH 已改为"标签列的最大宽度"，在 _build_detailed_view 中动态计算
ROW_HEIGHT = 24
CONTROL_HEIGHT = 22
LAYOUT_SPACING = 4
VALUE_LABEL_WIDTH = 40
LEFT_MARGIN = 10      # 节点内容左侧留白
RIGHT_MARGIN = 10     # 节点内容右侧留白（要考虑锚点可能在右侧外侧，所以这里只留小边距）
MIN_CONTROL_WIDTH = 120  # 输入控件的最小宽度，防止太窄导致数值被截
LABEL_MIN_WIDTH = 40


class ParameterWidget(QWidget):
    """参数控件基类 — 封装统一的尺寸/布局/信号规范

    关键：控件宽度由父级（NodeItem）决定，这里只约束高度，
    这样节点宽度可以跟随内容（最长标签 + 最长控件）自动扩张。
    """
    value_changed = pyqtSignal(str, object)

    # 供外部统一调用：每个参数行的高度
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
        mapping = {
            "string": StringWidget,
            "text": TextWidget,
            "password": PasswordWidget,
            "int": IntWidget,
            "float": FloatWidget,
            "bool": BoolWidget,
            "enum": EnumWidget,
            "file": FilePickerWidget,
            "directory": DirPickerWidget,
            "color": ColorWidget,
            "range": RangeWidget,
        }
        widget_cls = mapping.get(param.type, StringWidget)
        return widget_cls(param, current_value)


def _make_label(text, font=None) -> QLabel:
    """创建参数标签：右对齐，最小宽度由内容决定（字体测量），深色主题文字色"""
    label = QLabel(text)
    if font:
        label.setFont(font)
    fm = label.fontMetrics()
    text_width = fm.horizontalAdvance(text)
    # 标签宽度 = 文本宽度 + 少量呼吸空间
    label.setFixedWidth(max(LABEL_MIN_WIDTH, text_width + 8))
    label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    label.setStyleSheet("color: #cccccc; background: transparent;")
    return label


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


def _apply_dark_style(widget):
    """为控件统一应用深色主题样式"""
    widget.setStyleSheet(DARK_CONTROL_QSS)
    widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)


# ========================================================================
#  具体控件 — 全部遵循：HBox 布局 + 统一行高 + Qt.AlignVCenter
# ========================================================================

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


class PasswordWidget(ParameterWidget):
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
        self._edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._edit.textChanged.connect(lambda v: self._emit(v))
        layout.addWidget(self._edit, 1)

    def get_value(self):
        return self._edit.text()

    def set_value(self, value):
        self._current = value
        self._edit.blockSignals(True)
        self._edit.setText(str(value or ""))
        self._edit.blockSignals(False)


class IntWidget(ParameterWidget):
    def __init__(self, param, current_value):
        super().__init__(param, current_value)
        self._apply_row_height(ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(_make_label(param.label))
        self._spin = QSpinBox()
        self._spin.setMinimumHeight(CONTROL_HEIGHT)
        self._spin.setMinimumWidth(MIN_CONTROL_WIDTH)
        if param.min is not None:
            self._spin.setMinimum(int(param.min))
        if param.max is not None:
            self._spin.setMaximum(int(param.max))
        try:
            self._spin.setValue(int(current_value))
        except (ValueError, TypeError):
            self._spin.setValue(0)
        self._spin.valueChanged.connect(lambda v: self._emit(v))
        layout.addWidget(self._spin, 1)

    def get_value(self):
        return self._spin.value()

    def set_value(self, value):
        try:
            self._spin.blockSignals(True)
            self._spin.setValue(int(value))
            self._spin.blockSignals(False)
            self._current = value
        except (ValueError, TypeError):
            pass


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


class _ProxyAwareComboBox(QComboBox):
    """在 QGraphicsProxyWidget 中使用的 ComboBox — 修复下拉弹窗的全局坐标映射 bug。

    问题背景：QComboBox.showPopup() 内部通过 mapToGlobal 计算弹窗位置，
    但当 widget 被嵌入 QGraphicsProxyWidget 后，mapToGlobal 返回错误坐标，
    导致弹窗被截断/出现在屏幕其他位置。
    解决：重写 showPopup，基于 QGraphicsProxyWidget 的 scene→view→屏幕坐标自己计算。
    """

    def showPopup(self):
        proxy = None
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "metaObject") and parent.metaObject() and \
               parent.metaObject().className() == b"QGraphicsProxyWidget":
                proxy = parent
                break
            # 也兼容通过 widget() 获取 proxy 的常见模式
            try:
                from PyQt6.QtWidgets import QGraphicsProxyWidget as _GPW
                if isinstance(parent, _GPW):
                    proxy = parent
                    break
            except Exception:
                pass
            parent = parent.parent() if hasattr(parent, "parent") else None

        if proxy is not None and hasattr(proxy, "scenePos"):
            # 以 proxy 在 scene 中的坐标为锚点，映射到 view→全局屏幕坐标
            scene = proxy.scene()
            views = scene.views() if scene else []
            if views:
                view = views[0]
                proxy_scene_bottom = proxy.mapToScene(proxy.rect().bottomLeft())
                view_pt = view.mapFromScene(proxy_scene_bottom)
                screen_pt = view.viewport().mapToGlobal(view_pt)
            else:
                screen_pt = self.mapToGlobal(self.rect().bottomLeft())
            popup_width = max(self.width(), 200)
            # 让父类先构建弹窗，再移动到正确位置
            try:
                super().showPopup()
            except Exception:
                super().showPopup()
            popup = self.findChild(type(self).__bases__[0].__subclasses__()[0]) if False else None
            # 更可靠的方式：直接找 QFrame（QComboBox 内部的 popup 容器）
            from PyQt6.QtWidgets import QFrame
            for child in self.children():
                if isinstance(child, QFrame) and child.isWindow():
                    child.move(screen_pt)
                    child.resize(popup_width, min(child.height(), 400))
                    break
        else:
            super().showPopup()


class EnumWidget(ParameterWidget):
    def __init__(self, param, current_value):
        super().__init__(param, current_value)
        self._apply_row_height(ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(LAYOUT_SPACING)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(_make_label(param.label))
        # 使用 proxy-aware 的 ComboBox（在 QGraphicsProxyWidget 中下拉正常工作）
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


class FilePickerWidget(ParameterWidget):
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
        self._btn.clicked.connect(self._pick_file)
        layout.addWidget(self._edit, 1)
        layout.addWidget(self._btn)

    def _pick_file(self):
        f_filter = self.param.file_filter or "所有文件 (*)"
        path, _ = QFileDialog.getOpenFileName(self, self.param.label, "", f_filter)
        if path:
            self._edit.setText(path)

    def get_value(self):
        return self._edit.text()

    def set_value(self, value):
        self._current = value
        self._edit.blockSignals(True)
        self._edit.setText(str(value or ""))
        self._edit.blockSignals(False)


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
