"""复合节点生命周期状态机。

消除 TOCTOU 竞态、资源泄漏、stop 无反馈。

状态图::

    CREATED → STARTING → RUNNING
                  ↓ timeout/err      ↓ crash
               CRASHED ←─────────────┘
    CREATED → REMOVING → REMOVED (decompress)
    STARTING → REMOVING → REMOVED (decompress during start)
    RUNNING → STOPPING → STOPPED → STARTING (restart)
    STOPPING → CRASHED (kill failed)
    CRASHED → STARTING (restart)
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from ui.core.state.base import StateMachine, Transition


class CompositeLifecycleState(str, Enum):
    """复合节点生命周期状态。"""

    CREATED = "created"  # 已创建（压缩完毕），尚未启动
    STARTING = "starting"  # 正在启动编排器
    RUNNING = "running"  # 编排器进程运行中
    STOPPING = "stopping"  # 正在停止
    STOPPED = "stopped"  # 已停止，可重启
    CRASHED = "crashed"  # 异常终止（超时 / 崩溃 / kill 失败）
    REMOVING = "removing"  # 正在解压缩清理
    REMOVED = "removed"  # 已解压缩删除


def _build_transitions() -> list[Transition]:
    """构造所有合法状态转换。"""
    return [
        # ── 创建 → 移除 ──
        Transition("decompress", CompositeLifecycleState.CREATED, CompositeLifecycleState.REMOVING),
        Transition("remove_done", CompositeLifecycleState.REMOVING, CompositeLifecycleState.REMOVED),
        # ── 启动（只能在 CREATED / STOPPED / CRASHED 状态启动）──
        Transition("start", CompositeLifecycleState.CREATED, CompositeLifecycleState.STARTING),
        Transition("start", CompositeLifecycleState.STOPPED, CompositeLifecycleState.STARTING),
        Transition("start", CompositeLifecycleState.CRASHED, CompositeLifecycleState.STARTING),
        Transition("start_ok", CompositeLifecycleState.STARTING, CompositeLifecycleState.RUNNING),
        Transition("start_timeout", CompositeLifecycleState.STARTING, CompositeLifecycleState.CRASHED),
        # ── 运行时崩溃 ──
        Transition("crash", CompositeLifecycleState.RUNNING, CompositeLifecycleState.CRASHED),
        # ── 停止（RUNNING → STOPPING → STOPPED / CRASHED）──
        Transition("stop", CompositeLifecycleState.RUNNING, CompositeLifecycleState.STOPPING),
        Transition("stop_ok", CompositeLifecycleState.STOPPING, CompositeLifecycleState.STOPPED),
        Transition("stop_fail", CompositeLifecycleState.STOPPING, CompositeLifecycleState.CRASHED),
        # ── 启动中解压缩 ──
        Transition("decompress", CompositeLifecycleState.STARTING, CompositeLifecycleState.REMOVING),
        # ── 停止后/崩溃后解压缩 ──
        Transition("decompress", CompositeLifecycleState.STOPPED, CompositeLifecycleState.REMOVING),
        Transition("decompress", CompositeLifecycleState.CRASHED, CompositeLifecycleState.REMOVING),
    ]


class CompositeLifecycleSM(StateMachine):
    """复合节点生命周期状态机。

    附属数据由外部持有者管理，状态机本身只确保转换合法性。

    用法::

        sm = CompositeLifecycleSM("composite_abc")
        sm.handle("start")
        sm.handle("start_ok")  # 编排器进程确认存活
        sm.handle("stop")
        sm.handle("stop_ok")
        sm.handle("start")  # 重启
    """

    def __init__(self, comp_id: str = ""):
        self.comp_id = comp_id
        # 附属数据（由外部设置，状态机不管理生命周期）
        self.data: dict[str, Any] = {}
        super().__init__(
            initial_state=CompositeLifecycleState.CREATED,
            transitions=_build_transitions(),
        )

    @property
    def is_active(self) -> bool:
        """是否处于活跃状态（启动中 / 运行中 / 停止中）。"""
        return self._state in (
            CompositeLifecycleState.STARTING,
            CompositeLifecycleState.RUNNING,
            CompositeLifecycleState.STOPPING,
        )

    @property
    def is_terminal(self) -> bool:
        """是否处于终态（已删除）。"""
        return self._state == CompositeLifecycleState.REMOVED

    @property
    def is_restartable(self) -> bool:
        """是否可以调用 start()。"""
        return self._state in (
            CompositeLifecycleState.CREATED,
            CompositeLifecycleState.STOPPED,
            CompositeLifecycleState.CRASHED,
        )
