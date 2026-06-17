"""
标注样式预设系统 — 为节点标注场景提供一键样式切换
"""
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class StylePreset:
    """样式预设定义"""
    name: str                # 显示名称
    key: str                 # 唯一标识
    stroke_color: str        # 描边颜色
    stroke_width: float      # 描边宽度
    fill_color: str          # 填充颜色
    text_color: str          # 文字颜色
    dash_pattern: Optional[List[int]] = None  # 虚线模式


# 预设定义
PRESETS: Dict[str, StylePreset] = {
    "error": StylePreset(
        name="错误",
        key="error",
        stroke_color="#F44336",
        stroke_width=2.0,
        fill_color="rgba(244,67,54,0.15)",
        text_color="#F44336",
    ),
    "warning": StylePreset(
        name="警告",
        key="warning",
        stroke_color="#FF9800",
        stroke_width=2.0,
        fill_color="rgba(255,152,0,0.15)",
        text_color="#FF9800",
    ),
    "success": StylePreset(
        name="成功",
        key="success",
        stroke_color="#4CAF50",
        stroke_width=2.0,
        fill_color="rgba(76,175,80,0.15)",
        text_color="#4CAF50",
    ),
    "info": StylePreset(
        name="信息",
        key="info",
        stroke_color="#2196F3",
        stroke_width=2.0,
        fill_color="rgba(33,150,243,0.15)",
        text_color="#2196F3",
    ),
    "highlight": StylePreset(
        name="高亮",
        key="highlight",
        stroke_color="transparent",
        stroke_width=0.0,
        fill_color="rgba(255,235,59,0.4)",
        text_color="#333333",
    ),
    "note": StylePreset(
        name="注释",
        key="note",
        stroke_color="#9E9E9E",
        stroke_width=1.0,
        fill_color="rgba(158,158,158,0.1)",
        text_color="#CCCCCC",
        dash_pattern=[4, 2],
    ),
}


def get_preset_names() -> List[str]:
    """获取所有预设名称列表"""
    return [p.name for p in PRESETS.values()]


def get_preset_keys() -> List[str]:
    """获取所有预设 key 列表"""
    return list(PRESETS.keys())


def apply_preset(graphic, preset_key: str):
    """将预设样式应用到图形对象"""
    preset = PRESETS.get(preset_key)
    if not preset:
        return

    kwargs = {
        "stroke_color": preset.stroke_color,
        "stroke_w": preset.stroke_width,
        "fill_color": preset.fill_color,
    }

    # 文本颜色通过 text_color 参数传递
    if hasattr(graphic, "set_style"):
        graphic.set_style(**kwargs)

    # 单独设置文本颜色（如果图形支持）
    if hasattr(graphic, "set_text_color"):
        graphic.set_text_color(preset.text_color)
    elif hasattr(graphic, "_text_item"):
        from PySide6.QtGui import QColor
        graphic._text_color = QColor(preset.text_color)
        graphic._text_item.setDefaultTextColor(graphic._text_color)
        graphic.update()

    # 虚线模式
    if preset.dash_pattern and hasattr(graphic, "set_dash"):
        graphic.set_dash(preset.dash_pattern)
    elif preset.dash_pattern and hasattr(graphic, "_stroke"):
        graphic._stroke.setDashPattern(preset.dash_pattern)
        graphic.update()
