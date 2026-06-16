"""
Canvas 模块 - VueFlow 风格的可视化编排画布

分层架构（按子目录）：
- items/:           图形项层（NodeItem, EdgeItem, AnchorItem, 节点样式）
- mixins/:          逻辑层（7 个 Mixin + 4 个组合类 + controllers 控制器）
- drawing/:         绘图层（draw_layer, draw_toolbar, graphic_items）
- parameter_widgets/: 参数编辑控件集合

根目录仅保留：
- canvas_view.py    (NodeCanvas 主类，装配所有组合层)
- canvas_process.py (子进程启动入口)
- __init__.py       (当前文件，含旧路径兼容代理)
"""
import sys

from ui.canvas.items.anchor_item import AnchorItem
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.edge_item import EdgeItem
from ui.canvas.canvas_view import NodeCanvas

__all__ = ['AnchorItem', 'NodeItem', 'EdgeItem', 'NodeCanvas']


# ---------------------------------------------------------------------------
# 旧路径兼容代理（目录重构期间保持外部 import 不报错）
# 例如：from ui.canvas.canvas_layout import CanvasLayoutMixin
# 实际从 ui.canvas.mixins.canvas_layout 中获取模块
# ---------------------------------------------------------------------------

def _register_alias(alias_name: str, real_name: str) -> None:
    """把 alias_name 注册到 sys.modules，使其等价于 real_name 指向的模块。"""
    try:
        real = __import__(real_name, fromlist=['_'])
    except Exception:
        return
    # 用 sys.modules 做别名；避免重复注册
    sys.modules.setdefault(alias_name, real)


_COMPAT_MAP = {
    # 7 个 Mixin + 4 个组合类
    "ui.canvas.canvas_connections":      "ui.canvas.mixins.canvas_connections",
    "ui.canvas.canvas_box_select":       "ui.canvas.mixins.canvas_box_select",
    "ui.canvas.canvas_batch_ops":        "ui.canvas.mixins.canvas_batch_ops",
    "ui.canvas.canvas_menus":            "ui.canvas.mixins.canvas_menus",
    "ui.canvas.canvas_layout":           "ui.canvas.mixins.canvas_layout",
    "ui.canvas.canvas_colors":           "ui.canvas.mixins.canvas_colors",
    "ui.canvas.canvas_selection":        "ui.canvas.mixins.canvas_selection",
    "ui.canvas.canvas_background_renderer": "ui.canvas.mixins.canvas_background_renderer",
    "ui.canvas.canvas_node_manager":     "ui.canvas.mixins.canvas_node_manager",
    "ui.canvas.canvas_event_handlers":   "ui.canvas.mixins.canvas_event_handlers",
    # controllers
    "ui.canvas.controllers":             "ui.canvas.mixins.controllers",
    # 绘图层
    "ui.canvas.draw_layer":              "ui.canvas.drawing.draw_layer",
    "ui.canvas.draw_toolbar":            "ui.canvas.drawing.draw_toolbar",
    "ui.canvas.graphic_items":           "ui.canvas.drawing.graphic_items",
}

for _alias, _real in _COMPAT_MAP.items():
    _register_alias(_alias, _real)
