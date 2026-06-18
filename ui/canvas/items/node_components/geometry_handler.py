"""
节点几何变化处理模块 — itemChange、重叠避免、连线刷新、自动保存

从 node_item.py 拆分出来。
"""
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QGraphicsItem
from ui.core.logger import logger


class NodeGeometryHandler:
    """几何变化处理：itemChange、重叠避免、连线刷新、自动保存"""

    def __init__(self, node):
        self._node = node

    def item_change(self, change, value):
        """监听节点变化：选中环显隐、防重叠、保存布局、更新连线"""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self._node._update_selection_ring(value)

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            value = self._avoid_overlap(value)

        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._node.canvas:
                # 1. 遍历所有锚点（包括多端口场景），更新所有连线
                all_edges = set()

                for anchor in self._node.all_output_anchors():
                    for edge in list(anchor.edges):
                        if edge and edge.end_node:
                            all_edges.add(edge)

                for anchor in self._node.all_input_anchors():
                    for edge in list(anchor.edges):
                        if edge and edge.start_node:
                            all_edges.add(edge)

                # 更新所有相关连线
                for edge in all_edges:
                    if edge._waypoints and not isinstance(edge._waypoints[0], tuple):
                        edge._sync_abs_to_rel()
                    edge.update_path()

                # 2. 自动保存布局（防抖500ms）
                if hasattr(self._node.canvas, '_save_timer'):
                    self._node.canvas._save_timer.stop()
                    self._node.canvas._save_timer.start(500)

        # 调用父类的 itemChange 处理
        return super(self._node.__class__, self._node).itemChange(change, value)

    def _avoid_overlap(self, new_pos):
        """检测并避免节点重叠"""
        if not self._node.canvas:
            return new_pos

        rect = self._node.boundingRect()
        r1 = rect.translated(new_pos)

        for other in self._node.canvas.nodes.values():
            if other is self._node:
                continue
            r2 = other.boundingRect().translated(other.pos())
            if r1.intersects(r2):
                # 计算推开方向（从other中心指向self中心）
                cx1, cy1 = r1.center().x(), r1.center().y()
                cx2, cy2 = r2.center().x(), r2.center().y()
                dx = cx1 - cx2
                dy = cy1 - cy2
                # 如果中心重合，随机推开
                if dx == 0 and dy == 0:
                    dx, dy = 1, 0
                dist = (dx * dx + dy * dy) ** 0.5
                # 推开到不重叠的最小距离
                overlap_x = (r1.width() + r2.width()) / 2 - abs(dx)
                overlap_y = (r1.height() + r2.height()) / 2 - abs(dy)
                if overlap_x > 0 and overlap_y > 0:
                    nx = dx / dist
                    ny = dy / dist
                    # 优先横向推开
                    if overlap_x < overlap_y:
                        new_pos.setX(new_pos.x() + nx * overlap_x)
                    else:
                        new_pos.setY(new_pos.y() + ny * overlap_y)

        return new_pos
