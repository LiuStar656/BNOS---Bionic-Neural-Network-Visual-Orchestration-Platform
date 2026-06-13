"""复合命令 (MacroCommand) — 将多个原子操作包装为一个历史条目"""

from __future__ import annotations

import time
from typing import List

from ui.core.commands.base import Command, CommandResult, CommandType
from ui.core.logger import logger


class MacroCommand(Command):
    """复合命令：将一系列子命令作为一个整体记录

    用于批量操作 —— 如"粘贴多个节点"、"框选删除一组节点"。
    在历史面板中只显示一条条目，但内部包含多个子命令。
    """

    def __init__(self, description: str = "批量操作"):
        super().__init__(description)
        self.command_type = CommandType.MACRO
        self._commands: List[Command] = []
        self._closed: bool = False

    def add_command(self, command: Command):
        """向宏中添加子命令（内部使用，自动执行）"""
        if self._closed:
            logger.warning("MacroCommand 已关闭，不能再添加子命令")
            return
        self._commands.append(command)

    def close(self):
        """关闭宏，后续不可再添加子命令"""
        self._closed = True

    def execute(self) -> CommandResult:
        """执行宏中所有子命令"""
        for i, cmd in enumerate(self._commands):
            result = cmd.execute()
            if not result.success:
                # 回滚已执行的命令
                for j in range(i - 1, -1, -1):
                    self._commands[j].undo()
                return CommandResult(False, f"子命令 #{i} 执行失败: {result.message}")
        return CommandResult(True)

    def undo(self) -> CommandResult:
        """逆序撤销宏中所有子命令"""
        for i in range(len(self._commands) - 1, -1, -1):
            result = self._commands[i].undo()
            if not result.success:
                logger.warning("Macro undo: 子命令 #%d 撤销失败: %s", i, result.message)
        return CommandResult(True)

    def redo(self) -> CommandResult:
        """重做宏（顺序执行所有子命令）"""
        for i, cmd in enumerate(self._commands):
            result = cmd.redo()
            if not result.success:
                return CommandResult(False, f"子命令 #{i} 重做失败: {result.message}")
        return CommandResult(True)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data["sub_commands"] = [cmd.to_dict() for cmd in self._commands]
        return data

    def __len__(self) -> int:
        return len(self._commands)

    def __iter__(self):
        return iter(self._commands)
