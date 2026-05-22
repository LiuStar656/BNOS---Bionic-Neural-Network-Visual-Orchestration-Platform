"""
框选系统 Mixin — 框选状态清除
"""
from PyQt6.QtGui import QPen, QColor
from ui.core.logger import logger


class CanvasBoxSelectMixin:
    """框选状态管理（Mixin 注入到 NodeCanvas）"""

    def clear_box_selection(self):
        """清除框选状态"""
        if self.box_select_rect:
            self.scene.removeItem(self.box_select_rect)
            self.box_select_rect = None

        for node_name, node in self.nodes.items():
            node.setPen(QPen(QColor(self.node_border_color), 2))
            node.setSelected(False)

        self.box_selected_nodes = []
        self.is_box_selecting = False
        self.box_select_start_pos = None

        logger.debug("框选状态已清除（选中 %d 个节点）", len(self.box_selected_nodes))
