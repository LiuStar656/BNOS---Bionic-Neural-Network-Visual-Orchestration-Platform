"""
节点样式注册表 — 统一入口，只保留面板模式(detailed)
"""
from ._base import NodeStyle
from .detailed import DetailedNodeStyle


class StyleRegistry:
    """样式注册表 — 只返回 DetailedNodeStyle（面板模式）

    用法：
        StyleRegistry.get("detailed")  → DetailedNodeStyle 类
        StyleRegistry.keys()           → ["detailed"]
        StyleRegistry.default_key()    → "detailed"
    """

    _styles: dict = {
        "detailed": DetailedNodeStyle,
    }

    @classmethod
    def get(cls, style_key: str):
        """按 key 获取样式类，所有 key 都返回 DetailedNodeStyle"""
        return cls._styles.get(style_key, cls._styles["detailed"])

    @classmethod
    def keys(cls):
        return list(cls._styles.keys())

    @classmethod
    def default_key(cls) -> str:
        return "detailed"


# 兼容旧代码的模块级别名
STYLES = StyleRegistry._styles
DEFAULT_STYLE = "detailed"

__all__ = [
    "NodeStyle",
    "DetailedNodeStyle",
    "StyleRegistry",
    "STYLES",
    "DEFAULT_STYLE",
]
