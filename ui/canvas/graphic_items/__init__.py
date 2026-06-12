"""
绘图工具图形库 — 矩形/圆角矩形/多边形/箭头/文本

所有图形通过 GraphicRegistry 统一注册和反序列化。
"""
from ._base import GraphicBase, C_STROKE, C_FILL, C_TEXT, STROKE_W, FONT_SIZE
from .rect import RectGraphic
from .round_rect import RoundRectGraphic
from .polygon import PolygonGraphic
from .arrow import ArrowGraphic
from .text import TextGraphic


class GraphicRegistry:
    """图形注册表 — 按 gtype 查找类，支持序列化/反序列化

    用法：
        GraphicRegistry.get("rect")       → RectGraphic 类
        GraphicRegistry.from_dict(d)      → 图形式例
    """

    _types: dict = {
        "rect": RectGraphic,
        "round_rect": RoundRectGraphic,
        "polygon": PolygonGraphic,
        "arrow": ArrowGraphic,
        "text": TextGraphic,
    }

    @classmethod
    def get(cls, gtype: str):
        """按类型查找图形类，未知类型返回 RectGraphic"""
        return cls._types.get(gtype, RectGraphic)

    @classmethod
    def keys(cls):
        return list(cls._types.keys())

    @classmethod
    def from_dict(cls, d: dict):
        """从 dict 重建图形 — 统一反序列化入口"""
        gtype = d.get("type", "rect")
        sty = d.get("style", {})
        if gtype == "text":
            text = d.get("text", "")
            px = d.get("x", 0)
            py = d.get("y", 0)
            obj = TextGraphic(text, px, py)
            obj.set_style(stroke_color=sty.get("stroke"), stroke_w=sty.get("stroke_w"),
                          fill_color=sty.get("fill"),
                          font_size=sty.get("font_size"), text_color=sty.get("text_color"))
        else:
            pts = d.get("points", [])
            cls_type = cls._types.get(gtype, RectGraphic)
            obj = cls_type(pts)
            obj.set_style(stroke_color=sty.get("stroke"), stroke_w=sty.get("stroke_w"),
                          fill_color=sty.get("fill"))
        return obj


__all__ = [
    "GraphicRegistry",
    "GraphicBase",
    "RectGraphic",
    "RoundRectGraphic",
    "PolygonGraphic",
    "ArrowGraphic",
    "TextGraphic",
    "C_STROKE",
    "C_FILL",
    "C_TEXT",
    "STROKE_W",
    "FONT_SIZE",
]
