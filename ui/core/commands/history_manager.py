"""HistoryManager - 扁平列表 + 指针模型，支持 Photoshop 式历史面板跳转"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional

from PySide6.QtCore import QObject, Signal

from ui.core.commands.base import Command, CommandResult
from ui.core.commands.compound_commands import MacroCommand
from ui.core.logger import logger


@dataclass
class HistoryState:
    """历史记录状态（扁平列表 + 当前指针，实现 Photoshop 式跳转）

    核心数据结构：
      commands:     [C0, C1, C2, C3, C4]  ← 所有已执行命令（按时间序）
      current_index: 3                    ← 指向 C3（当前状态）

    关键语义：
      - current_index = -1 表示初始状态（空画布，未执行任何命令）
      - commands[0] ~ commands[current_index] 构成"已生效"区间
      - commands[current_index+1:] 是"可重做"区间
      - 在非末尾位置执行新命令 → 截断 current_index 之后的所有命令
    """
    commands: List[Command] = field(default_factory=list)
    current_index: int = -1
    max_history: int = 50
    is_recording: bool = True

    def get_can_undo(self) -> bool:
        return self.current_index >= 0

    def get_can_redo(self) -> bool:
        return self.current_index < len(self.commands) - 1

    def get_current_command(self) -> Optional[Command]:
        if 0 <= self.current_index < len(self.commands):
            return self.commands[self.current_index]
        return None

    def get_undo_description(self) -> Optional[str]:
        cmd = self.get_current_command()
        return cmd.description if cmd else None

    def get_redo_description(self) -> Optional[str]:
        redo_index = self.current_index + 1
        if redo_index < len(self.commands):
            return self.commands[redo_index].description
        return None

    def get_all_descriptions(self) -> List[dict]:
        """获取全部历史条目信息（供 HistoryPanel 显示）"""
        result = []
        for i, cmd in enumerate(self.commands):
            result.append({
                "index": i,
                "description": cmd.description,
                "command_type": cmd.command_type.name,
                "is_current": (i == self.current_index),
                "is_future": (i > self.current_index),
            })
        return result

    def truncate_future(self):
        """截断当前指针之后的所有命令（在新操作执行前调用）"""
        if self.current_index + 1 < len(self.commands):
            self.commands = self.commands[:self.current_index + 1]

    def trim_head(self):
        """超出最大历史限制时，从头部丢弃最旧命令"""
        while len(self.commands) > self.max_history:
            self.commands.pop(0)
            self.current_index -= 1


class HistoryManager(QObject):
    """历史记录管理器 - 单例（扁平列表 + 指针，支持 Photoshop 式跳转）"""

    history_changed = Signal()       # 历史内容变更
    can_undo_changed = Signal(bool)  # 是否可撤销
    can_redo_changed = Signal(bool)  # 是否可重做
    index_changed = Signal(int)      # 当前指针变更

    _instance: Optional[HistoryManager] = None

    def __new__(cls) -> HistoryManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self.state = HistoryState()
        self._initialized = True
        self._event_bus = None

    def set_event_bus(self, event_bus):
        """注入 EventBus（延迟绑定，避免循环导入）"""
        self._event_bus = event_bus
        if event_bus:
            event_bus.subscribe('project.opened', self._on_project_opened)
            event_bus.subscribe('project.closed', self._on_project_closed)

    # ── 核心操作 ──

    def execute_command(self, command: Command) -> CommandResult:
        """执行命令并记录到历史列表"""
        if not self.state.is_recording:
            return command.execute()

        result = command.execute()
        if not result.success:
            return result

        # 如果在历史中间（非末尾），截断后面的"未来"
        if self.state.current_index < len(self.state.commands) - 1:
            self.state.truncate_future()

        command.timestamp = time.time()
        command.executed = True

        self.state.commands.append(command)
        self.state.current_index = len(self.state.commands) - 1
        self.state.trim_head()

        self._emit_change_signals()
        self.index_changed.emit(self.state.current_index)

        logger.debug("Command: %s (index=%d)", command.description, self.state.current_index)
        return result

    def record_only(self, command: Command):
        """仅记录命令到历史，不执行（用于已由外部执行的操作）"""
        if not self.state.is_recording:
            return
        if self.state.current_index < len(self.state.commands) - 1:
            self.state.truncate_future()
        command.timestamp = time.time()
        command.executed = True
        self.state.commands.append(command)
        self.state.current_index = len(self.state.commands) - 1
        self.state.trim_head()
        self._emit_change_signals()
        self.index_changed.emit(self.state.current_index)
        logger.debug("Record-only: %s (index=%d)", command.description, self.state.current_index)

    def undo(self) -> CommandResult:
        """撤销一步"""
        if not self.state.get_can_undo():
            return CommandResult(False, "没有可撤销的操作")

        cmd = self.state.get_current_command()
        result = cmd.undo()
        if result.success:
            self.state.current_index -= 1
            self._emit_change_signals()
            self.index_changed.emit(self.state.current_index)
            logger.debug("Undo: %s -> index=%d", cmd.description, self.state.current_index)
        return result

    def redo(self) -> CommandResult:
        """重做一步"""
        if not self.state.get_can_redo():
            return CommandResult(False, "没有可重做的操作")

        next_index = self.state.current_index + 1
        cmd = self.state.commands[next_index]
        result = cmd.redo()
        if result.success:
            self.state.current_index = next_index
            self._emit_change_signals()
            self.index_changed.emit(self.state.current_index)
            logger.debug("Redo: %s -> index=%d", cmd.description, self.state.current_index)
        return result

    def jump_to(self, target_index: int) -> CommandResult:
        """跳转到指定的历史位置（Photoshop 核心交互）

        通过正向/逆向重放指令到达目标状态。
        """
        current = self.state.current_index

        if target_index == current:
            return CommandResult(True, "已在目标状态")
        if target_index < -1 or target_index >= len(self.state.commands):
            return CommandResult(False, f"无效的目标索引: {target_index}")

        try:
            if target_index < current:
                for i in range(current, target_index, -1):
                    result = self.state.commands[i].undo()
                    if not result.success:
                        logger.error("跳转失败: undo index=%d 出错", i)
                        return CommandResult(False, f"撤销 {self.state.commands[i].description} 失败")
            else:
                for i in range(current + 1, target_index + 1):
                    result = self.state.commands[i].redo()
                    if not result.success:
                        logger.error("跳转失败: redo index=%d 出错", i)
                        return CommandResult(False, f"重做 {self.state.commands[i].description} 失败")

            self.state.current_index = target_index
            self._emit_change_signals()
            self.index_changed.emit(target_index)
            logger.info("跳转到 index=%d (移动了 %d 步)", target_index, abs(target_index - current))
            return CommandResult(True)
        except Exception as e:
            logger.error("跳转异常: %s", e)
            return CommandResult(False, str(e))

    def clear_history(self):
        """清空历史记录"""
        self.state.commands.clear()
        self.state.current_index = -1
        self._emit_change_signals()
        self.index_changed.emit(-1)
        logger.info("History cleared")

    # ── 历史查看接口 ──

    def get_history_entries(self) -> List[dict]:
        return self.state.get_all_descriptions()

    def get_current_index(self) -> int:
        return self.state.current_index

    def can_undo(self) -> bool:
        return self.state.get_can_undo()

    def can_redo(self) -> bool:
        return self.state.get_can_redo()

    # ── 录制控制 ──

    def begin_macro(self, description: str) -> MacroCommand:
        """开始宏（批量操作包装为一个历史条目）"""
        return MacroCommand(description)

    def pause_recording(self):
        self.state.is_recording = False

    def resume_recording(self):
        self.state.is_recording = True

    # ── 持久化 ──

    def save_history(self, project_path: str):
        """保存历史到项目文件"""
        if not project_path:
            return

        history_file = os.path.join(project_path, "history.json")
        data = {
            "commands": [cmd.to_dict() for cmd in self.state.commands],
            "current_index": self.state.current_index,
        }
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("History saved to %s", history_file)
        except Exception as e:
            logger.error("Failed to save history: %s", e)

    def load_history(self, project_path: str):
        """从项目文件加载历史"""
        if not project_path:
            return

        history_file = os.path.join(project_path, "history.json")
        if not os.path.exists(history_file):
            return

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error("Failed to load history: %s", e)
            return

        commands_data = data.get("commands", [])
        current_index = data.get("current_index", -1)

        from ui.core.commands.node_commands import (
            CreateNodeCommand, DeleteNodeCommand, MoveNodeCommand
        )
        from ui.core.commands.edge_commands import (
            CreateEdgeCommand, DeleteEdgeCommand
        )
        from ui.core.commands.base import CommandType

        command_type_map = {
            CommandType.CREATE_NODE: CreateNodeCommand,
            CommandType.DELETE_NODE: DeleteNodeCommand,
            CommandType.MOVE_NODE: MoveNodeCommand,
            CommandType.CREATE_EDGE: CreateEdgeCommand,
            CommandType.DELETE_EDGE: DeleteEdgeCommand,
        }

        canvas = None
        if self._event_bus:
            canvas = self._event_bus._app_context.canvas if hasattr(self._event_bus, '_app_context') else None
            if canvas and hasattr(canvas, 'current_canvas'):
                canvas = canvas.current_canvas

        self.state.commands.clear()
        for cmd_data in commands_data:
            cmd_type_name = cmd_data.get("command_type", "")
            try:
                cmd_type = CommandType[cmd_type_name]
                cmd_class = command_type_map.get(cmd_type)
                if cmd_class:
                    cmd = cmd_class.from_dict(cmd_data, canvas)
                    self.state.commands.append(cmd)
                else:
                    logger.warning(f"未知命令类型: {cmd_type_name}")
            except KeyError:
                logger.warning(f"无效命令类型: {cmd_type_name}")

        self.state.current_index = current_index
        self._emit_change_signals()
        self.index_changed.emit(current_index)
        logger.info("History loaded: %d commands, current index=%d",
                    len(self.state.commands), current_index)

    # ── 内部方法 ──

    def _emit_change_signals(self):
        self.history_changed.emit()
        self.can_undo_changed.emit(self.can_undo())
        self.can_redo_changed.emit(self.can_redo())

    def _on_project_opened(self, project_path: str):
        self.clear_history()

    def _on_project_closed(self):
        self.clear_history()


# 全局单例
history_manager = HistoryManager()
