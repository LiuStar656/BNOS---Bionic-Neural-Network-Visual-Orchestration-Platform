"""Command 基类和数据结构"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class CommandType(Enum):
    """命令类型枚举"""
    CREATE_NODE = auto()
    DELETE_NODE = auto()
    MOVE_NODE = auto()
    CREATE_EDGE = auto()
    DELETE_EDGE = auto()
    MACRO = auto()
    GENERIC = auto()


@dataclass
class CommandResult:
    """命令执行结果"""
    success: bool
    message: str = ""
    data: Optional[dict] = None


class Command(ABC):
    """命令基类

    每个子类需实现 execute() 和 undo()。
    命令对象本身存储足够的状态数据以支持撤销。
    """

    def __init__(self, description: str = ""):
        self.description = description
        self.command_type = CommandType.GENERIC
        self.timestamp: float = 0.0
        self.executed: bool = False

    @abstractmethod
    def execute(self) -> CommandResult:
        """执行命令"""
        ...

    @abstractmethod
    def undo(self) -> CommandResult:
        """撤销命令"""
        ...

    def redo(self) -> CommandResult:
        """重做命令（默认等同于 execute）"""
        return self.execute()

    def to_dict(self) -> dict:
        """序列化为字典（用于持久化）"""
        return {
            "description": self.description,
            "command_type": self.command_type.name,
            "timestamp": self.timestamp,
            "executed": self.executed,
        }

    @classmethod
    def from_dict(cls, data: dict, canvas=None):
        """从字典重建命令对象"""
        raise NotImplementedError(f"{cls.__name__} 未实现 from_dict 方法")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.description}>"
