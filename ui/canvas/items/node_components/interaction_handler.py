"""
节点鼠标交互处理模块 — mousePressEvent、选中环、展开按钮

从 node_item.py 拆分出来。
"""
from PySide6.QtCore import Qt, QRectF
from ui.canvas.items.anchor_item import ANCHOR_SIZE, ANCHOR_HALF
from ui.core.logger import logger


class NodeInteractionHandler:
    """鼠标交互处理：mousePressEvent、选中环、展开按钮"""

    def __init__(self, node):
        self._node = node

    def update_selection_ring(self, selected):
        """更新选中环 — 面板模式下由 paint 方法直接绘制选中高亮"""
        self._node._selection_ring.setVisible(False)

    def handle_mouse_press(self, event):
        """鼠标按下事件处理"""
        if event.button() != Qt.MouseButton.LeftButton:
            return False

        pos_in_item = self._node.mapFromScene(event.scenePos())
        w = self._node.rect().width()
        h = self._node.rect().height()

        # 展开按钮（保留扩展点）
        if self._node._expand_btn_rect.contains(pos_in_item):
            if self._node.on_expand_requested:
                self._node.on_expand_requested(self._node.node_name)
            event.accept()
            return True

        # 输出锚点（开始连线）
        clicked_output = self._node.find_nearest_output_anchor(pos_in_item, max_dist=20)
        if clicked_output is None:
            default_output_rect = QRectF(
                w - ANCHOR_HALF, h / 2 - ANCHOR_HALF, ANCHOR_SIZE, ANCHOR_SIZE)
            if default_output_rect.contains(pos_in_item):
                clicked_output = self._node.anchor_manager.get_output("default")
        if clicked_output:
            port_label = (
                clicked_output.port_name
                if getattr(clicked_output, "port_name", None)
                else "default"
            )
            logger.debug("NodeItem[%s]: 输出锚点命中 %s", self._node.node_name, port_label)
            if self._node.canvas:
                self._node.canvas.start_connection_from_output(self._node, clicked_output)
            event.accept()
            return True

        # 输入锚点（完成连线）
        clicked_anchor = self._node.find_nearest_input_anchor(pos_in_item, max_dist=20)
        if clicked_anchor is None:
            if (len(self._node.anchor_manager.input_anchors) == 1
                    and "default" in self._node.anchor_manager.input_anchors):
                default_rect = QRectF(
                    -ANCHOR_HALF, h / 2 - ANCHOR_HALF, ANCHOR_SIZE, ANCHOR_SIZE)
                if default_rect.contains(pos_in_item):
                    clicked_anchor = self._node.anchor_manager.input_anchors["default"]
        if clicked_anchor:
            port_label = (
                clicked_anchor.port_name
                if getattr(clicked_anchor, "port_name", None)
                else "default"
            )
            logger.debug("NodeItem[%s]: 输入锚点命中 %s", self._node.node_name, port_label)
            if self._node.canvas and self._node.canvas.is_connecting:
                self._node.canvas.complete_connection_to_input(self._node, clicked_anchor)
            event.accept()
            return True

        # Ctrl+单击
        if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and self._node.canvas:
            self._node.canvas._toggle_node_selection(self._node.node_name)
            event.accept()
            return True

        # 普通单击
        if self._node.canvas:
            self._node.canvas.on_node_selected(self._node)

        return False
