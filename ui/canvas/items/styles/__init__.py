"""
节点样式注册表 — 统一入口，按 style_key 查找样式类
"""
from ._base import NodeStyle
from .rect import RectNodeStyle, DarkRectNodeStyle, LightRectNodeStyle
from .dot import DotNodeStyle
from .detailed import DetailedNodeStyle


class StyleRegistry:
    """样式注册表 — 替代原 STYLES dict

    用法：
        StyleRegistry.get("dot")       → DotNodeStyle 类
        StyleRegistry.keys()           → ["rect", "dot", "detailed"]
        StyleRegistry.default_key()    → "rect"
    """

    _styles: dict = {
        "rect": DarkRectNodeStyle,
        "dot": DotNodeStyle,
        "detailed": DetailedNodeStyle,
    }

    @classmethod
    def get(cls, style_key: str):
        """按 key 获取样式类，未知 key 返回默认样式"""
        return cls._styles.get(style_key, cls._styles["rect"])

    @classmethod
    def keys(cls):
        return list(cls._styles.keys())

    @classmethod
    def default_key(cls) -> str:
        return "rect"


# 兼容旧代码的模块级别名
STYLES = StyleRegistry._styles
DEFAULT_STYLE = "rect"

__all__ = [
    "NodeStyle",
    "RectNodeStyle",
    "DarkRectNodeStyle",
    "LightRectNodeStyle",
    "DotNodeStyle",
    "DetailedNodeStyle",
    "StyleRegistry",
    "STYLES",
    "DEFAULT_STYLE",
]
