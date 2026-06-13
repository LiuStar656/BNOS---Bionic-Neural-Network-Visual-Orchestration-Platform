"""节点相关命令"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QPointF

from ui.core.commands.base import Command, CommandResult, CommandType
from ui.core.logger import logger


class CreateNodeCommand(Command):
    """创建节点命令"""

    def __init__(self, node_name: str, canvas):
        super().__init__(f"创建节点: {node_name}")
        self.command_type = CommandType.CREATE_NODE
        self._node_name = node_name
        self._canvas = canvas

    def execute(self) -> CommandResult:
        try:
            self._canvas._begin_replay()
            self._canvas.add_node_to_canvas(self._node_name)
            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("CreateNodeCommand 执行失败: %s", e)
            return CommandResult(False, str(e))

    def undo(self) -> CommandResult:
        try:
            self._canvas._begin_replay()
            self._canvas.remove_node_from_canvas(self._node_name)
            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("CreateNodeCommand 撤销失败: %s", e)
            return CommandResult(False, str(e))


class DeleteNodeCommand(Command):
    """删除节点命令

    执行前保存节点的完整状态，撤销时完整恢复。
    """

    def __init__(self, node_name: str, canvas, parent_window):
        super().__init__(f"删除节点: {node_name}")
        self.command_type = CommandType.DELETE_NODE
        self._node_name = node_name
        self._canvas = canvas
        self._parent_window = parent_window

        # 执行前收集恢复数据
        self._position: Optional[Tuple[float, float]] = None
        self._edge_data: List[dict] = []
        self._node_data: Optional[dict] = None
        self._collected: bool = False

    def _collect_state(self):
        """快照节点当前状态"""
        if self._collected:
            return
        self._collected = True

        node = self._canvas.nodes.get(self._node_name)
        if node:
            pos = node.pos()
            self._position = (pos.x(), pos.y())

        # 保存关联的连线信息
        for edge in list(self._canvas.edges):
            src = edge.start_node.node_name if edge.start_node else None
            tgt = edge.end_node.node_name if edge.end_node else None
            if src == self._node_name or tgt == self._node_name:
                self._edge_data.append({
                    "source": src,
                    "target": tgt,
                    "target_port": edge.target_port_name,
                    "source_port": edge.source_port_name,
                    "target_anchor_name": edge.target_anchor.name if edge.target_anchor else None,
                })

        # 保存节点配置数据
        if self._parent_window and hasattr(self._parent_window, 'nodes_data'):
            data = self._parent_window.nodes_data.get(self._node_name)
            if data:
                self._node_data = dict(data)

    def execute(self) -> CommandResult:
        try:
            self._collect_state()
            self._canvas._begin_replay()
            self._canvas.remove_node_from_canvas(self._node_name)
            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("DeleteNodeCommand 执行失败: %s", e)
            return CommandResult(False, str(e))

    def undo(self) -> CommandResult:
        try:
            # 恢复节点数据
            if self._node_data and self._parent_window and hasattr(self._parent_window, 'nodes_data'):
                self._parent_window.nodes_data[self._node_name] = self._node_data

            # 重新创建节点
            self._canvas._begin_replay()
            self._canvas.add_node_to_canvas(self._node_name)

            # 恢复位置
            if self._position:
                node = self._canvas.nodes.get(self._node_name)
                if node:
                    node.setPos(self._position[0], self._position[1])

            # 恢复连线
            for edge_info in self._edge_data:
                src = self._canvas.nodes.get(edge_info["source"])
                tgt = self._canvas.nodes.get(edge_info["target"])
                if src and tgt:
                    self._canvas.create_edge(src, tgt)

            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("DeleteNodeCommand 撤销失败: %s", e)
            return CommandResult(False, str(e))


class MoveNodeCommand(Command):
    """移动节点命令

    在拖拽结束时创建。execute 应用新位置，undo 恢复旧位置。
    """

    def __init__(self, node_positions: Dict[str, Tuple[float, float, float, float]],
                 canvas):
        """
        Args:
            node_positions: {node_name: (old_x, old_y, new_x, new_y)}
        """
        node_names = list(node_positions.keys())
        desc = f"移动节点: {', '.join(node_names[:3])}"
        if len(node_names) > 3:
            desc += f" 等{len(node_names)}个"
        super().__init__(desc)
        self.command_type = CommandType.MOVE_NODE
        self._node_positions = node_positions
        self._canvas = canvas

    def execute(self) -> CommandResult:
        try:
            self._canvas._begin_replay()
            for node_name, (_, _, new_x, new_y) in self._node_positions.items():
                node = self._canvas.nodes.get(node_name)
                if node:
                    node.setPos(new_x, new_y)
            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("MoveNodeCommand 执行失败: %s", e)
            return CommandResult(False, str(e))

    def undo(self) -> CommandResult:
        try:
            self._canvas._begin_replay()
            for node_name, (old_x, old_y, _, _) in self._node_positions.items():
                node = self._canvas.nodes.get(node_name)
                if node:
                    node.setPos(old_x, old_y)
            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("MoveNodeCommand 撤销失败: %s", e)
            return CommandResult(False, str(e))
