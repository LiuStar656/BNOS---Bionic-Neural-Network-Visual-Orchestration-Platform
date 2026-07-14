"""L3 连接状态机。

管理节点的上游和下游连接状态，分别独立维护：
- 上游（Upstream）  : DISCONNECTED / CONNECTED
- 下游（Downstream）: NO_OUTPUTS / HAS_OUTPUTS

继承 StateMachine 管理上游状态；下游作为独立计数器+子状态在本类内维护。
"""

from __future__ import annotations

from enum import StrEnum

from ui.core.state.base import StateMachine, Transition


class UpstreamState(StrEnum):
    """上游输入连接状态。"""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"


class DownstreamState(StrEnum):
    """下游输出连接状态。"""

    NO_OUTPUTS = "no_outputs"
    HAS_OUTPUTS = "has_outputs"


def _build_upstream_transitions() -> list[Transition]:
    """上游连接转换：DISCONNECTED <-> CONNECTED。"""

    return [
        Transition("connect_upstream", UpstreamState.DISCONNECTED, UpstreamState.CONNECTED),
        Transition("disconnect_upstream", UpstreamState.CONNECTED, UpstreamState.DISCONNECTED),
    ]


class ConnectionSM(StateMachine):
    """连接状态机。

    上游状态通过 StateMachine.handle("connect_upstream"/"disconnect_upstream") 切换；
    下游状态通过 downstream_count 增减自动切换，无需 StateMachine 事件驱动。

    Attributes:
        upstream_port:        CONNECTED 时，本节点的输入端口名。
        upstream_node_name:   CONNECTED 时，上游节点名称。
        upstream_output_path: CONNECTED 时，上游 output.json 绝对路径。
        downstream_count:     下游输出连线数量；>0 时下游状态 = HAS_OUTPUTS。
    """

    def __init__(self, node_name: str):
        self.node_name = node_name
        self.upstream_port: str = ""
        self.upstream_node_name: str = ""
        self.upstream_output_path: str = ""
        self.downstream_count: int = 0
        super().__init__(
            initial_state=UpstreamState.DISCONNECTED,
            transitions=_build_upstream_transitions(),
        )

    # ── 下游状态操作 ──

    @property
    def downstream_state(self) -> DownstreamState:
        return DownstreamState.HAS_OUTPUTS if self.downstream_count > 0 else DownstreamState.NO_OUTPUTS

    def add_downstream(self) -> None:
        """下游连接 +1（由 CanvasConnections 在创建出边时调用）。"""
        self.downstream_count += 1

    def remove_downstream(self) -> None:
        """下游连接 -1；不会低于 0。"""
        if self.downstream_count > 0:
            self.downstream_count -= 1

    def reset_downstream(self) -> None:
        """清空下游计数（节点销毁时）。"""
        self.downstream_count = 0

    # ── 上游连接附属数据清理 ──

    def clear_upstream_meta(self) -> None:
        """清除上游连接附属字段（在 disconnect_upstream 之后调用）。"""
        self.upstream_port = ""
        self.upstream_node_name = ""
        self.upstream_output_path = ""
