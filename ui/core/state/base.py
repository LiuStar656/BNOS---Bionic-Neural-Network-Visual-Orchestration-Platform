"""状态机基类。

零业务依赖，仅依赖 PySide6.QtCore.QObject / Signal。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class Transition:
    """单条状态转换规则。

    Attributes:
        event:  触发事件名。
        source: 源状态。``"*"`` 表示任意状态均可触发。
        target: 目标状态。
        guard:  可选前置条件，返回 False 时阻止转换。
        action: 可选副作用回调，仅在转换成功时执行。
    """

    event: str
    source: str
    target: str
    guard: Callable[[], bool] | None = None
    action: Callable[[], None] | None = None


class StateMachine(QObject):
    """通用有限状态机。

    用法::

        sm = StateMachine(
            "stopped",
            [
                Transition("start", "stopped", "running", action=lambda: print("started")),
                Transition("stop", "running", "stopped"),
            ],
        )
        sm.state_changed.connect(lambda old, new: print(f"{old} -> {new}"))
        sm.handle("start")  # True, state == "running"
        sm.handle("start")  # False (非法转换)
    """

    state_changed = Signal(str, str)

    def __init__(self, initial_state: str, transitions: list[Transition]):
        super().__init__()
        self._initial_state = initial_state
        self._state = initial_state
        # {(source, event): Transition}
        self._transitions: dict[tuple[str, str], Transition] = {}
        # [Transition]  通配符转换 (* → target)
        self._wildcard_transitions: list[Transition] = []
        for t in transitions:
            if t.source == "*":
                self._wildcard_transitions.append(t)
            else:
                self._transitions[(t.source, t.event)] = t

    # ── 只读属性 ──

    @property
    def state(self) -> str:
        return self._state

    @property
    def initial_state(self) -> str:
        return self._initial_state

    # ── 核心操作 ──

    def handle(self, event: str) -> bool:
        """触发事件。转换成功返回 True，否则返回 False。"""
        t = self._find_transition(event)
        if t is None:
            return False
        if t.guard is not None and not t.guard():
            return False
        old = self._state
        self._state = t.target
        if t.action is not None:
            t.action()
        self.state_changed.emit(old, self._state)
        return True

    def can(self, event: str) -> bool:
        """查询事件是否可触发（不执行转换）。"""
        t = self._find_transition(event)
        if t is None:
            return False
        if t.guard is not None and not t.guard():
            return False
        return True

    def reset(self) -> None:
        """重置到初始状态。"""
        self._state = self._initial_state

    def get_allowed_events(self) -> list[str]:
        """返回当前状态下允许触发的事件列表。"""
        events: set[str] = set()
        for src, evt in self._transitions:
            if src == self._state:
                events.add(evt)
        for t in self._wildcard_transitions:
            events.add(t.event)
        return sorted(events)

    # ── 内部 ──

    def _find_transition(self, event: str) -> Transition | None:
        """优先精确匹配 (source, event)，其次通配符 (*, event)。"""
        key = (self._state, event)
        if key in self._transitions:
            return self._transitions[key]
        for t in self._wildcard_transitions:
            if t.event == event:
                return t
        return None
