"""节点运行时状态机。

统一 node_process.py / node_control_service.py / node_startup_queue.py 中 3 套矛盾的状态值。

状态图::

    STOPPED → STARTING → RUNNING ⇄ IDLE
                                 ↓ crash
                              CRASHED
    STARTING → CRASHED (timeout)
    RUNNING → STOPPING → STOPPED
    STOPPING → CRASHED (kill failed)
    STOPPING → STOPPED (ok)
    CRASHED → STARTING (retry / restart)
"""

from __future__ import annotations

from enum import Enum

from ui.core.state.base import StateMachine, Transition


class NodeRuntimeState(str, Enum):
    """节点运行时状态枚举。

    继承 str，可直接与旧代码中的裸字符串比较/赋值。
    """

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    STOPPING = "stopping"
    CRASHED = "crashed"


def _build_transitions() -> list[Transition]:
    """构造所有合法状态转换。"""
    return [
        # ── 启动 ──
        Transition("start", NodeRuntimeState.STOPPED, NodeRuntimeState.STARTING),
        Transition("start_ok", NodeRuntimeState.STARTING, NodeRuntimeState.RUNNING),
        Transition("start_fail", NodeRuntimeState.STARTING, NodeRuntimeState.CRASHED),
        # ── idle 与 running 互转 ──
        Transition("child_idle", NodeRuntimeState.RUNNING, NodeRuntimeState.IDLE),
        Transition("child_resume", NodeRuntimeState.IDLE, NodeRuntimeState.RUNNING),
        # ── 停止 ──
        Transition("stop", NodeRuntimeState.RUNNING, NodeRuntimeState.STOPPING),
        Transition("stop", NodeRuntimeState.IDLE, NodeRuntimeState.STOPPING),
        Transition("stop_ok", NodeRuntimeState.STOPPING, NodeRuntimeState.STOPPED),
        Transition("stop_fail", NodeRuntimeState.STOPPING, NodeRuntimeState.CRASHED),
        # ── 崩溃 ──
        Transition("crash", NodeRuntimeState.RUNNING, NodeRuntimeState.CRASHED),
        Transition("crash", NodeRuntimeState.IDLE, NodeRuntimeState.CRASHED),
        # ── 恢复 ──
        Transition("retry", NodeRuntimeState.CRASHED, NodeRuntimeState.STARTING),
        Transition("direct_stop", NodeRuntimeState.CRASHED, NodeRuntimeState.STOPPED),
    ]


class NodeRuntimeSM(StateMachine):
    """节点运行时状态机。

    用法::

        sm = NodeRuntimeSM("node_python_1")
        sm.handle("start")  # STOPPED → STARTING
        sm.handle("start_ok")  # STARTING → RUNNING
        sm.handle("stop")  # RUNNING → STOPPING
        sm.handle("stop_ok")  # STOPPING → STOPPED
    """

    def __init__(self, node_name: str = ""):
        self.node_name = node_name
        super().__init__(
            initial_state=NodeRuntimeState.STOPPED,
            transitions=_build_transitions(),
        )
