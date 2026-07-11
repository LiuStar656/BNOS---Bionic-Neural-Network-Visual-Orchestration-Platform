"""Command 模式模块 - 历史回滚功能核心"""

from __future__ import annotations

from ui.core.commands.base import Command, CommandResult, CommandType
from ui.core.commands.compound_commands import MacroCommand
from ui.core.commands.edge_commands import CreateEdgeCommand, DeleteEdgeCommand
from ui.core.commands.history_manager import HistoryManager, HistoryState, history_manager
from ui.core.commands.node_commands import CreateNodeCommand, DeleteNodeCommand, MoveNodeCommand

__all__ = [
    "Command",
    "CommandResult",
    "CommandType",
    "HistoryManager",
    "HistoryState",
    "history_manager",
    "MacroCommand",
    "CreateNodeCommand",
    "DeleteNodeCommand",
    "MoveNodeCommand",
    "CreateEdgeCommand",
    "DeleteEdgeCommand",
]
