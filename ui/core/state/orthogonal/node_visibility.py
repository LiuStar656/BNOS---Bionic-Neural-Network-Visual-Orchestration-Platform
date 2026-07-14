"""L2 可见性状态机。

描述节点在画布上的显示状态。

注意：不同成员角色的合法可见性集合不同：
- STANDALONE       只能是 VISIBLE（不可变）
- COMPOSITE_CHILD  VISIBLE / HIDDEN_COLLAPSED，跟随父复合节点 expand/collapse
- COMPOSITE        EXPANDED_MODE / COLLAPSED_MODE（复合自身折叠/展开模式）
"""

from __future__ import annotations

from enum import StrEnum

from ui.core.state.base import StateMachine, Transition


class NodeVisibility(StrEnum):
    """节点可见性枚举。"""

    VISIBLE = "visible"
    HIDDEN_COLLAPSED = "hidden_collapsed"
    EXPANDED_MODE = "expanded_mode"
    COLLAPSED_MODE = "collapsed_mode"


def _build_transitions() -> list[Transition]:
    """构造可见性转换。

    不同角色合法转换：
    - COMPOSITE_CHILD : VISIBLE <-> HIDDEN_COLLAPSED
    - COMPOSITE       : EXPANDED_MODE <-> COLLAPSED_MODE
    - STANDALONE      : 仅 VISIBLE，无动态转换
    """

    return [
        Transition("expand", NodeVisibility.HIDDEN_COLLAPSED, NodeVisibility.VISIBLE),
        Transition("collapse", NodeVisibility.VISIBLE, NodeVisibility.HIDDEN_COLLAPSED),
        Transition("expand", NodeVisibility.COLLAPSED_MODE, NodeVisibility.EXPANDED_MODE),
        Transition("collapse", NodeVisibility.EXPANDED_MODE, NodeVisibility.COLLAPSED_MODE),
    ]


class VisibilitySM(StateMachine):
    """可见性状态机。"""

    def __init__(
        self,
        node_name: str,
        initial: NodeVisibility = NodeVisibility.VISIBLE,
    ):
        self.node_name = node_name
        super().__init__(
            initial_state=initial,
            transitions=_build_transitions(),
        )
