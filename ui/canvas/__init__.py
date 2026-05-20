"""
Canvas 模块 - VueFlow风格的可视化编排画布

分层架构：
- items: 图形项层（AnchorItem, NodeItem, EdgeItem）
- core: 核心管理层（NodeCanvas）
- interactions: 交互处理层（待扩展）
- config: 配置管理层（待扩展）
"""

from ui.canvas.items.anchor_item import AnchorItem
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.edge_item import EdgeItem
from ui.canvas.canvas_view import NodeCanvas

__all__ = ['AnchorItem', 'NodeItem', 'EdgeItem', 'NodeCanvas']
