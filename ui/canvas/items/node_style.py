"""
节点样式系统（兼容重定向 — 所有样式类已迁移至 styles/ 目录）

新路径：
    from ui.canvas.items.styles import NodeStyle
    from ui.canvas.items.styles import (RectNodeStyle, DarkRectNodeStyle, DotNodeStyle, DetailedNodeStyle)
    from ui.canvas.items.styles import StyleRegistry, STYLES, DEFAULT_STYLE
"""
import warnings

warnings.warn(
    "node_style.py 已废弃，请改用 ui.canvas.items.styles",
    DeprecationWarning,
    stacklevel=2,
)

from ui.canvas.items.styles import *  # noqa: F401,F403,E402
