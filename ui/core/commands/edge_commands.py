"""连线相关命令"""

from __future__ import annotations

from typing import Optional

from ui.core.commands.base import Command, CommandResult, CommandType
from ui.core.logger import logger


class CreateEdgeCommand(Command):
    """创建连线命令"""

    def __init__(self, source_name: str, target_name: str, canvas):
        super().__init__(f"连线: {source_name} → {target_name}")
        self.command_type = CommandType.CREATE_EDGE
        self._source_name = source_name
        self._target_name = target_name
        self._canvas = canvas

    def execute(self) -> CommandResult:
        try:
            src = self._canvas.nodes.get(self._source_name)
            tgt = self._canvas.nodes.get(self._target_name)
            if not src or not tgt:
                return CommandResult(False, "源节点或目标节点不存在")
            self._canvas._begin_replay()
            self._canvas.create_edge(src, tgt)
            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("CreateEdgeCommand 执行失败: %s", e)
            return CommandResult(False, str(e))

    def undo(self) -> CommandResult:
        try:
            src = self._canvas.nodes.get(self._source_name)
            tgt = self._canvas.nodes.get(self._target_name)
            if not src or not tgt:
                return CommandResult(False, "节点不存在")

            self._canvas._begin_replay()
            for edge in list(self._canvas.edges):
                if (edge.start_node == src and edge.end_node == tgt):
                    self._canvas.remove_edge(edge)
                    break
            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("CreateEdgeCommand 撤销失败: %s", e)
            return CommandResult(False, str(e))

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "source_name": self._source_name,
            "target_name": self._target_name,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict, canvas=None):
        source_name = data.get("source_name", "")
        target_name = data.get("target_name", "")
        cmd = cls(source_name, target_name, canvas)
        cmd.timestamp = data.get("timestamp", 0.0)
        cmd.executed = data.get("executed", False)
        return cmd


class DeleteEdgeCommand(Command):
    """删除连线命令"""

    def __init__(self, source_name: str, target_name: str,
                 target_port_name: Optional[str],
                 source_port_name: Optional[str],
                 target_anchor_name: Optional[str],
                 canvas):
        super().__init__(f"断开连线: {source_name} → {target_name}")
        self.command_type = CommandType.DELETE_EDGE
        self._source_name = source_name
        self._target_name = target_name
        self._target_port_name = target_port_name
        self._source_port_name = source_port_name
        self._target_anchor_name = target_anchor_name
        self._canvas = canvas
        self._removed: bool = False

    def execute(self) -> CommandResult:
        try:
            src = self._canvas.nodes.get(self._source_name)
            tgt = self._canvas.nodes.get(self._target_name)
            if not src or not tgt:
                return CommandResult(True)

            self._canvas._begin_replay()
            for edge in list(self._canvas.edges):
                if edge.start_node == src and edge.end_node == tgt:
                    self._canvas.remove_edge(edge)
                    self._removed = True
                    break
            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("DeleteEdgeCommand 执行失败: %s", e)
            return CommandResult(False, str(e))

    def undo(self) -> CommandResult:
        if not self._removed:
            return CommandResult(True)
        try:
            src = self._canvas.nodes.get(self._source_name)
            tgt = self._canvas.nodes.get(self._target_name)
            if not src or not tgt:
                return CommandResult(False, "节点不存在")

            target_anchor = self._resolve_anchor(tgt, self._target_port_name, is_input=True)
            source_anchor = self._resolve_anchor(src, self._source_port_name, is_input=False)

            self._canvas._begin_replay()
            self._canvas.create_edge(src, tgt,
                                     target_anchor=target_anchor,
                                     source_anchor=source_anchor)
            self._canvas._end_replay()
            return CommandResult(True)
        except Exception as e:
            self._canvas._end_replay()
            logger.error("DeleteEdgeCommand 撤销失败: %s", e)
            return CommandResult(False, str(e))

    @staticmethod
    def _resolve_anchor(node, port_name, is_input: bool):
        """根据端口名解析锚点对象"""
        if not port_name:
            return None
        anchors = node.anchor_manager.input_anchors if is_input else node.anchor_manager.output_anchors
        return anchors.get(port_name)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "source_name": self._source_name,
            "target_name": self._target_name,
            "target_port_name": self._target_port_name,
            "source_port_name": self._source_port_name,
            "target_anchor_name": self._target_anchor_name,
            "removed": self._removed,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict, canvas=None):
        source_name = data.get("source_name", "")
        target_name = data.get("target_name", "")
        target_port_name = data.get("target_port_name")
        source_port_name = data.get("source_port_name")
        target_anchor_name = data.get("target_anchor_name")
        cmd = cls(source_name, target_name, target_port_name,
                  source_port_name, target_anchor_name, canvas)
        cmd.timestamp = data.get("timestamp", 0.0)
        cmd.executed = data.get("executed", False)
        cmd._removed = data.get("removed", False)
        return cmd
