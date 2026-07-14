"""L1 成员角色状态机。

描述节点在项目中的角色类型，三种互斥值：
- STANDALONE       独立节点（普通节点）
- COMPOSITE_CHILD  复合节点内部子节点
- COMPOSITE        复合节点（作为整体存在于画布上）
"""

from __future__ import annotations

from enum import StrEnum

from ui.core.state.base import StateMachine, Transition


class NodeMembership(StrEnum):
    """节点成员角色枚举。"""

    STANDALONE = "standalone"
    COMPOSITE_CHILD = "composite_child"
    COMPOSITE = "composite"


def _build_transitions() -> list[Transition]:
    """构造允许的角色动态转换。

    注意：COMPOSITE 角色由 create_composite / delete_composite 操作直接
    创建/销毁，不存在与其他角色的动态转换。
    """

    return [
        Transition(
            "compress_into_composite",
            NodeMembership.STANDALONE,
            NodeMembership.COMPOSITE_CHILD,
        ),
        Transition(
            "decompress_from_composite",
            NodeMembership.COMPOSITE_CHILD,
            NodeMembership.STANDALONE,
        ),
    ]


class MembershipSM(StateMachine):
    """成员角色状态机。

    Attributes:
        comp_id:          复合节点 ID（COMPOSITE_CHILD / COMPOSITE 类型有效）。
        child_node_names: 子节点名称列表（仅 COMPOSITE 类型有效）。
        entry_node:       入口节点名称（仅 COMPOSITE 类型有效）。
    """

    def __init__(
        self,
        node_name: str,
        initial: NodeMembership = NodeMembership.STANDALONE,
        comp_id: str = "",
        child_node_names: list[str] | None = None,
        entry_node: str = "",
    ):
        self.node_name = node_name
        self.comp_id = comp_id
        self.child_node_names = list(child_node_names) if child_node_names else []
        self.entry_node = entry_node
        super().__init__(
            initial_state=initial,
            transitions=_build_transitions(),
        )
