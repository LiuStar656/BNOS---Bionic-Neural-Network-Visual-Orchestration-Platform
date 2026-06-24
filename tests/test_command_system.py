"""
test_command_system.py — Command 系统单元测试
覆盖: base.py (CommandType, CommandResult, Command), history_manager.py (HistoryState, HistoryManager 核心逻辑)
"""
import pytest
from ui.core.commands.base import Command, CommandResult, CommandType
from ui.core.commands.history_manager import HistoryState, HistoryManager


# ═══════════════════ 测试用模拟 Command ═══════════════════

class _DummyCommand(Command):
    """可测试的模拟命令 — execute / undo 均可控"""
    def __init__(self, description="test", should_fail=False):
        super().__init__(description)
        self.command_type = CommandType.GENERIC
        self.should_fail = should_fail
        self.exec_count = 0
        self.undo_count = 0
        self._data = {}

    def execute(self):
        if self.should_fail:
            return CommandResult(False, "模拟失败")
        self.exec_count += 1
        return CommandResult(True, "执行成功", data=self._data)

    def undo(self):
        self.undo_count += 1
        return CommandResult(True, "撤销成功")

    def to_dict(self):
        d = super().to_dict()
        d.update(self._data)
        return d

    @classmethod
    def from_dict(cls, data, canvas=None):
        cmd = cls(data.get("description", ""))
        cmd._data = data
        cmd.timestamp = data.get("timestamp", 0)
        cmd.executed = data.get("executed", False)
        return cmd


# ═══════════════════ CommandType ═══════════════════

class TestCommandType:
    def test_enum_values(self):
        assert CommandType.CREATE_NODE is not None
        assert CommandType.DELETE_NODE is not None
        assert CommandType.MOVE_NODE is not None
        assert CommandType.CREATE_EDGE is not None
        assert CommandType.DELETE_EDGE is not None
        assert CommandType.MACRO is not None
        assert CommandType.GENERIC is not None

    def test_from_string_roundtrip(self):
        for t in CommandType:
            assert CommandType[t.name] == t


# ═══════════════════ CommandResult ═══════════════════

class TestCommandResult:
    def test_success(self):
        r = CommandResult(True, "OK")
        assert r.success is True
        assert r.message == "OK"
        assert r.data is None

    def test_failure(self):
        r = CommandResult(False, "Error", data={"detail": "xxx"})
        assert r.success is False
        assert r.data == {"detail": "xxx"}


# ═══════════════════ Command 基类 ═══════════════════

class TestCommand:
    def test_init_defaults(self):
        cmd = _DummyCommand()
        assert cmd.description == "test"
        assert cmd.command_type == CommandType.GENERIC
        assert cmd.timestamp == 0.0
        assert cmd.executed is False

    def test_execute_success(self):
        cmd = _DummyCommand()
        r = cmd.execute()
        assert r.success is True
        assert cmd.exec_count == 1

    def test_execute_failure(self):
        cmd = _DummyCommand(should_fail=True)
        r = cmd.execute()
        assert r.success is False
        assert cmd.exec_count == 0

    def test_undo(self):
        cmd = _DummyCommand()
        r = cmd.undo()
        assert r.success is True
        assert cmd.undo_count == 1

    def test_redo_delegates_to_execute(self):
        cmd = _DummyCommand()
        cmd.redo()
        assert cmd.exec_count == 1

    def test_to_dict(self):
        cmd = _DummyCommand("my desc")
        cmd.timestamp = 12345.0
        cmd.executed = True
        d = cmd.to_dict()
        assert d["description"] == "my desc"
        assert d["command_type"] == "GENERIC"
        assert d["timestamp"] == 12345.0
        assert d["executed"] is True

    def test_from_dict(self):
        data = {"description": "restored", "timestamp": 99.0, "executed": True}
        cmd = _DummyCommand.from_dict(data)
        assert cmd.description == "restored"
        assert cmd.timestamp == 99.0
        assert cmd.executed is True

    def test_repr(self):
        cmd = _DummyCommand("hello")
        assert "hello" in repr(cmd)


# ═══════════════════ HistoryState ═══════════════════

class TestHistoryState:
    def test_initial_state(self):
        s = HistoryState()
        assert s.commands == []
        assert s.current_index == -1
        assert s.max_history == 50
        assert s.is_recording is True

    def test_can_undo_false_initially(self):
        s = HistoryState()
        assert s.get_can_undo() is False

    def test_can_undo_after_execute(self):
        s = HistoryState()
        s.commands.append(_DummyCommand("c1"))
        s.current_index = 0
        assert s.get_can_undo() is True

    def test_can_redo_false_initially(self):
        s = HistoryState()
        assert s.get_can_redo() is False

    def test_can_redo_when_future_exists(self):
        s = HistoryState()
        s.commands = [_DummyCommand("c1"), _DummyCommand("c2")]
        s.current_index = 0
        assert s.get_can_redo() is True

    def test_get_current_command(self):
        s = HistoryState()
        cmd = _DummyCommand("c1")
        s.commands.append(cmd)
        s.current_index = 0
        assert s.get_current_command() is cmd

    def test_get_current_command_when_empty(self):
        s = HistoryState()
        assert s.get_current_command() is None

    def test_get_undo_description(self):
        s = HistoryState()
        s.commands.append(_DummyCommand("undo me"))
        s.current_index = 0
        assert s.get_undo_description() == "undo me"

    def test_get_undo_description_none(self):
        s = HistoryState()
        assert s.get_undo_description() is None

    def test_get_redo_description(self):
        s = HistoryState()
        s.commands = [_DummyCommand("c1"), _DummyCommand("redo me")]
        s.current_index = 0
        assert s.get_redo_description() == "redo me"

    def test_get_all_descriptions(self):
        s = HistoryState()
        s.commands = [_DummyCommand("a"), _DummyCommand("b"), _DummyCommand("c")]
        s.current_index = 1
        entries = s.get_all_descriptions()
        assert len(entries) == 3
        assert entries[0]["is_current"] is False
        assert entries[1]["is_current"] is True   # b is current
        assert entries[2]["is_current"] is False
        assert entries[2]["is_future"] is True    # c is future

    def test_truncate_future(self):
        s = HistoryState()
        s.commands = [_DummyCommand("a"), _DummyCommand("b"), _DummyCommand("c"), _DummyCommand("d")]
        s.current_index = 1  # 停在 b
        s.truncate_future()
        assert len(s.commands) == 2
        assert s.commands[0].description == "a"
        assert s.commands[1].description == "b"

    def test_truncate_future_at_end_does_nothing(self):
        s = HistoryState()
        s.commands = [_DummyCommand("a"), _DummyCommand("b")]
        s.current_index = 1
        s.truncate_future()
        assert len(s.commands) == 2

    def test_trim_head_exceeds_max(self):
        s = HistoryState()
        s.max_history = 3
        s.commands = [_DummyCommand(str(i)) for i in range(5)]  # 0,1,2,3,4
        s.current_index = 4
        s.trim_head()
        assert len(s.commands) == 3
        assert s.commands[0].description == "2"
        assert s.current_index == 2  # 4 → 2（减了 2）

    def test_trim_head_no_exceed(self):
        s = HistoryState()
        s.max_history = 10
        s.commands = [_DummyCommand(str(i)) for i in range(5)]
        s.current_index = 4
        s.trim_head()
        assert len(s.commands) == 5


# ═══════════════════ HistoryManager 核心 ─══════════════════

class TestHistoryManager:
    def setup_method(self):
        """每个测试前重置单例状态"""
        HistoryManager._instance = None
        self.hm = HistoryManager()

    def test_singleton(self):
        hm2 = HistoryManager()
        assert self.hm is hm2

    def test_initial_state(self):
        assert self.hm.can_undo() is False
        assert self.hm.can_redo() is False
        assert self.hm.get_current_index() == -1

    def test_execute_command_success(self):
        cmd = _DummyCommand("test")
        r = self.hm.execute_command(cmd)
        assert r.success is True
        assert self.hm.can_undo() is True
        assert self.hm.get_current_index() == 0

    def test_execute_command_failure_not_recorded(self):
        cmd = _DummyCommand("fail", should_fail=True)
        r = self.hm.execute_command(cmd)
        assert r.success is False
        assert self.hm.can_undo() is False  # 失败不记录

    def test_undo(self):
        cmd = _DummyCommand("test")
        self.hm.execute_command(cmd)
        r = self.hm.undo()
        assert r.success is True
        assert self.hm.can_undo() is False
        assert self.hm.get_current_index() == -1

    def test_undo_when_nothing(self):
        r = self.hm.undo()
        assert r.success is False
        assert "没有可撤销" in r.message

    def test_redo(self):
        cmd = _DummyCommand("test")
        self.hm.execute_command(cmd)
        self.hm.undo()
        r = self.hm.redo()
        assert r.success is True
        assert self.hm.can_undo() is True
        assert self.hm.can_redo() is False

    def test_redo_when_nothing(self):
        r = self.hm.redo()
        assert r.success is False
        assert "没有可重做" in r.message

    def test_truncate_future_on_execute(self):
        """非末尾执行新命令 → 截断未来"""
        self.hm.execute_command(_DummyCommand("a"))
        self.hm.execute_command(_DummyCommand("b"))
        self.hm.execute_command(_DummyCommand("c"))
        self.hm.undo()  # → index 1 (b)
        self.hm.undo()  # → index 0 (a)
        # 在 a 之后执行新命令 → 截断 b,c
        self.hm.execute_command(_DummyCommand("d"))
        assert self.hm.get_current_index() == 1
        assert len(self.hm.get_history_entries()) == 2
        assert self.hm.get_history_entries()[1]["description"] == "d"

    def test_clear_history(self):
        self.hm.execute_command(_DummyCommand("a"))
        self.hm.execute_command(_DummyCommand("b"))
        self.hm.clear_history()
        assert self.hm.can_undo() is False
        assert self.hm.get_current_index() == -1
        assert self.hm.get_history_entries() == []

    def test_record_only(self):
        cmd = _DummyCommand("record-only")
        self.hm.record_only(cmd)
        assert self.hm.can_undo() is True
        assert cmd.exec_count == 0  # execute 未被调用

    def test_pause_resume_recording(self):
        self.hm.pause_recording()
        cmd = _DummyCommand("paused")
        r = self.hm.execute_command(cmd)
        assert r.success is True
        assert self.hm.can_undo() is False  # 暂停录制时不记录

        self.hm.resume_recording()
        r2 = self.hm.execute_command(_DummyCommand("resumed"))
        assert r2.success is True
        assert self.hm.can_undo() is True
        assert self.hm.get_current_index() == 0

    def test_jump_to_forward(self):
        self.hm.execute_command(_DummyCommand("a"))
        self.hm.execute_command(_DummyCommand("b"))
        self.hm.execute_command(_DummyCommand("c"))
        # jump to index 0 (undo b,c)
        r = self.hm.jump_to(0)
        assert r.success is True
        assert self.hm.get_current_index() == 0

    def test_jump_to_backward(self):
        self.hm.execute_command(_DummyCommand("a"))
        self.hm.execute_command(_DummyCommand("b"))
        self.hm.undo()
        self.hm.undo()
        # jump to index 1 (redo a,b)
        r = self.hm.jump_to(1)
        assert r.success is True
        assert self.hm.get_current_index() == 1

    def test_jump_to_same_index(self):
        self.hm.execute_command(_DummyCommand("a"))
        r = self.hm.jump_to(0)
        assert r.success is True

    def test_jump_to_invalid_negative(self):
        r = self.hm.jump_to(-5)
        assert r.success is False

    def test_jump_to_invalid_out_of_range(self):
        self.hm.execute_command(_DummyCommand("a"))
        r = self.hm.jump_to(10)
        assert r.success is False

    def test_history_entries_format(self):
        self.hm.execute_command(_DummyCommand("first"))
        self.hm.execute_command(_DummyCommand("second"))
        entries = self.hm.get_history_entries()
        assert len(entries) == 2
        for e in entries:
            assert "index" in e
            assert "description" in e
            assert "command_type" in e
            assert "is_current" in e
            assert "is_future" in e

    def test_max_history_limit_via_execute(self):
        """超过 max_history 时自动丢弃旧命令"""
        self.hm.state.max_history = 3
        for i in range(5):
            self.hm.execute_command(_DummyCommand(str(i)))
        entries = self.hm.get_history_entries()
        assert len(entries) == 3
        assert entries[0]["description"] == "2"
        assert entries[1]["description"] == "3"
        assert entries[2]["description"] == "4"
