"""
参数控件库 — 将 config.json 中的参数定义渲染为 QWidget，通过 QGraphicsProxyWidget 嵌入画布

设计原则：
  - 统一行高（24px）、统一控件高度（22px）、统一标签宽度（56px）
  - 统一水平布局（HBox），所有类型对齐到同一视觉基线
  - 紧凑间距（spacing=4），减少视觉噪声
  - 每个 Widget 类型独立文件，通过 WidgetRegistry 统一注册
"""
import os

from ._base import (
    ParameterWidget,
    _make_label,
    _apply_dark_style,
    DARK_CONTROL_QSS,
    ROW_HEIGHT,
    CONTROL_HEIGHT,
    LAYOUT_SPACING,
    VALUE_LABEL_WIDTH,
    LEFT_MARGIN,
    RIGHT_MARGIN,
    MIN_CONTROL_WIDTH,
    LABEL_MIN_WIDTH,
)
from .string import StringWidget
from .text import TextWidget
from .password import PasswordWidget
from .int_widget import IntWidget
from .float_widget import FloatWidget
from .bool_widget import BoolWidget
from .enum_widget import EnumWidget
from .file_picker import FilePickerWidget
from .dir_picker import DirPickerWidget
from .color_widget import ColorWidget
from .range_widget import RangeWidget


class WidgetRegistry:
    """参数控件注册表 — 按 param.type 查找对应的 Widget 类

    用法：
        WidgetRegistry.get("int")        → IntWidget 类
        WidgetRegistry.get("unknown")    → StringWidget 类（fallback）
        WidgetRegistry.keys()            → 所有注册类型列表
    """

    _widgets: dict = {
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

    @classmethod
    def get(cls, param_type: str):
        """按类型查找控件类，未知类型返回 StringWidget"""
        return cls._widgets.get(param_type, StringWidget)

    @classmethod
    def keys(cls):
        return list(cls._widgets.keys())


__all__ = [
    # 注册表
    "WidgetRegistry",
    # 基类与辅助
    "ParameterWidget",
    "_make_label",
    "_apply_dark_style",
    "DARK_CONTROL_QSS",
    # 常量
    "ROW_HEIGHT",
    "CONTROL_HEIGHT",
    "LAYOUT_SPACING",
    "VALUE_LABEL_WIDTH",
    "LEFT_MARGIN",
    "RIGHT_MARGIN",
    "MIN_CONTROL_WIDTH",
    "LABEL_MIN_WIDTH",
    # 具体控件
    "StringWidget",
    "TextWidget",
    "PasswordWidget",
    "IntWidget",
    "FloatWidget",
    "BoolWidget",
    "EnumWidget",
    "FilePickerWidget",
    "DirPickerWidget",
    "ColorWidget",
    "RangeWidget",
]
