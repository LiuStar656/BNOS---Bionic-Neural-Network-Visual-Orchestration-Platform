"""Phase 0: StateMachine 基类单元测试 (10 项)。"""

from PySide6.QtWidgets import QApplication

from ui.core.state.base import StateMachine, Transition

# ── 确保 QApplication 存在（QObject 需要） ──
_app = QApplication.instance() or QApplication([])


def _mk(*transitions: tuple[str, str, str]) -> list[Transition]:
    """快速构造 Transition 列表。"""
    return [Transition(evt, src, tgt) for evt, src, tgt in transitions]


# ======================================================================
# T0.1 正常状态转换
# ======================================================================


def test_basic_transition():
    sm = StateMachine("a", _mk(("go", "a", "b")))
    assert sm.state == "a"
    assert sm.handle("go") is True
    assert sm.state == "b"


# ======================================================================
# T0.2 禁止的转换返回 False
# ======================================================================


def test_invalid_event():
    sm = StateMachine("a", _mk(("go", "a", "b")))
    assert sm.handle("no_such_event") is False
    assert sm.state == "a"


def test_event_wrong_source():
    sm = StateMachine("a", _mk(("go", "a", "b")))
    # 在 a 状态可以 go → b
    sm.handle("go")
    assert sm.state == "b"
    # 在 b 状态 go 不该生效（没有 b → go 的 transition）
    assert sm.handle("go") is False
    assert sm.state == "b"


# ======================================================================
# T0.3 guard 返回 False 阻止转换
# ======================================================================


def test_guard_blocks():
    locked = True
    sm = StateMachine(
        "idle",
        [
            Transition("start", "idle", "running", guard=lambda: not locked),
        ],
    )
    assert sm.handle("start") is False
    assert sm.state == "idle"

    locked = False
    assert sm.handle("start") is True
    assert sm.state == "running"


# ======================================================================
# T0.4 action 在转换成功时执行
# ======================================================================


def test_action_executes():
    side_effect = []
    sm = StateMachine(
        "a",
        [
            Transition("go", "a", "b", action=lambda: side_effect.append(1)),
        ],
    )
    assert sm.handle("go") is True
    assert side_effect == [1]

    # 非法转换时 action 不执行
    assert sm.handle("go") is False
    assert side_effect == [1]


# ======================================================================
# T0.5 "*" 通配符可从任何状态触发
# ======================================================================


def test_wildcard_source():
    sm = StateMachine(
        "alpha",
        [
            Transition("reset", "*", "home"),
            Transition("next", "alpha", "beta"),
            Transition("next", "beta", "gamma"),
        ],
    )
    # 从 alpha → home
    assert sm.handle("reset") is True
    assert sm.state == "home"

    # 从 home 走 next 没有定义，但 reset 是通配符
    assert sm.handle("next") is False  # home → next 没定义
    assert sm.handle("reset") is True  # 仍然能触发
    assert sm.state == "home"


# ======================================================================
# T0.6 can() 查询不改变状态
# ======================================================================


def test_can_readonly():
    sm = StateMachine("a", _mk(("go", "a", "b")))
    assert sm.can("go") is True
    assert sm.state == "a"  # 状态未变
    assert sm.can("go") is True  # 第二次查询结果一致
    assert sm.can("invalid") is False


# ======================================================================
# T0.7 reset() 回到初始状态
# ======================================================================


def test_reset():
    sm = StateMachine(
        "init",
        [
            Transition("a2b", "init", "b"),
            Transition("b2c", "b", "c"),
            Transition("c2d", "c", "d"),
        ],
    )
    sm.handle("a2b")
    sm.handle("b2c")
    sm.handle("c2d")
    assert sm.state == "d"

    sm.reset()
    assert sm.state == "init"


# ======================================================================
# T0.8 state_changed 信号正确发射
# ======================================================================


def test_state_changed_signal():
    sm = StateMachine("start", _mk(("go", "start", "end")))
    received: list[tuple[str, str]] = []
    sm.state_changed.connect(lambda old, new: received.append((old, new)))

    sm.handle("go")
    assert received == [("start", "end")]

    # 非法事件不发射信号
    sm.handle("go")
    assert len(received) == 1


# ======================================================================
# T0.9 get_allowed_events() 初始状态返回合法事件列表
# ======================================================================


def test_get_allowed_events():
    sm = StateMachine(
        "idle",
        [
            Transition("start", "idle", "running"),
            Transition("stop", "running", "idle"),
            Transition("panic", "*", "crashed"),
        ],
    )
    assert set(sm.get_allowed_events()) == {"start", "panic"}

    sm.handle("start")
    assert set(sm.get_allowed_events()) == {"stop", "panic"}


# ======================================================================
# T0.10 连续 100 次 handle 状态始终合法
# ======================================================================


def test_consecutive_handles():
    sm = StateMachine(
        "inactive",
        [
            Transition("toggle", "inactive", "active"),
            Transition("toggle", "active", "inactive"),
        ],
    )
    for i in range(100):
        ok = sm.handle("toggle")
        assert ok is True
        expected = "active" if i % 2 == 0 else "inactive"
        assert sm.state == expected

    # 100 次后状态应为 initial (toggle 100 次 = 偶数次)
    assert sm.state == "inactive"
