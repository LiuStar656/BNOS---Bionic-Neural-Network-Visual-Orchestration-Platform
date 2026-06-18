"""
框选状态管理（组合类）— 负责清除框选状态（含节点选中与绘图图形）
"""
from PySide6.QtGui import QPen, QColor
from ui.core.logger import logger


class CanvasBoxSelect:
    """框选状态管理（组合类，通过 self.canvas 访问画布上下文）"""

    def __init__(self, canvas):
        self.canvas = canvas

    def clear_box_selection(self):
        """清除框选状态 — 重置节点边框、清除矩形、清除选中节点列表与图形选中状态"""
        if self.canvas.box_select_rect:
            self.canvas.scene.removeItem(self.canvas.box_select_rect)
            self.canvas.box_select_rect = None

        for node_name, node in self.canvas.nodes.items():
            node.setPen(QPen(QColor(self.canvas.node_border_color), 2))
            node.setSelected(False)

        # 同时清除绘图图形的选中状态
        if hasattr(self.canvas, 'draw_layer') and hasattr(self.canvas.draw_layer, 'graphics'):
            for g in self.canvas.draw_layer.graphics:
                g.setSelected(False)
                if hasattr(g, 'selected_handle'):
                    g.selected_handle = -1

        self.canvas.box_selected_nodes = []
        self.canvas.is_box_selecting = False
        self.canvas.box_select_start_pos = None

        logger.debug("框选状态已清除（选中 %d 个节点）", len(self.canvas.box_selected_nodes))
