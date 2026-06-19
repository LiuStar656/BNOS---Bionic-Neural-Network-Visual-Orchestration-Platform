"""节点相关命令"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF

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

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "node_name": self._node_name,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict, canvas=None):
        node_name = data.get("node_name", "")
        cmd = cls(node_name, canvas)
        cmd.timestamp = data.get("timestamp", 0.0)
        cmd.executed = data.get("executed", False)
        return cmd


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
            if self._node_data and self._parent_window and hasattr(self._parent_window, 'nodes_data'):
                self._parent_window.nodes_data[self._node_name] = self._node_data

            self._canvas._begin_replay()
            self._canvas.add_node_to_canvas(self._node_name)

            if self._position:
                node = self._canvas.nodes.get(self._node_name)
                if node:
                    node.setPos(self._position[0], self._position[1])

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

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "node_name": self._node_name,
            "position": self._position,
            "edge_data": self._edge_data,
            "node_data": self._node_data,
            "collected": self._collected,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict, canvas=None):
        node_name = data.get("node_name", "")
        parent_window = canvas.parent_window if canvas else None
        cmd = cls(node_name, canvas, parent_window)
        cmd.timestamp = data.get("timestamp", 0.0)
        cmd.executed = data.get("executed", False)
        cmd._position = data.get("position")
        cmd._edge_data = data.get("edge_data", [])
        cmd._node_data = data.get("node_data")
        cmd._collected = data.get("collected", False)
        return cmd


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

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "node_positions": self._node_positions,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict, canvas=None):
        node_positions = data.get("node_positions", {})
        cmd = cls(node_positions, canvas)
        cmd.timestamp = data.get("timestamp", 0.0)
        cmd.executed = data.get("executed", False)
        return cmd
