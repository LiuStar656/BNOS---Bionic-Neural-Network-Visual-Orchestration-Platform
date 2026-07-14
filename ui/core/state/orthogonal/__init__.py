"""正交状态机子包（L1-L3）。

纯状态 + 最小附属数据，零文件 I/O，零画布依赖，极易单元测试。

分层::

    L1  node_membership.py  成员角色：STANDALONE / COMPOSITE_CHILD / COMPOSITE
    L2  node_visibility.py  可见性：VISIBLE / HIDDEN_COLLAPSED / EXPANDED_MODE / COLLAPSED_MODE
    L3  node_connection.py  连接状态：上游 DISCONNECTED/CONNECTED；下游 NO_OUTPUTS/HAS_OUTPUTS
"""

from ui.core.state.orthogonal.node_connection import (
    ConnectionSM,
    DownstreamState,
    UpstreamState,
)
from ui.core.state.orthogonal.node_membership import (
    MembershipSM,
    NodeMembership,
)
from ui.core.state.orthogonal.node_visibility import (
    NodeVisibility,
    VisibilitySM,
)

__all__ = [
    "MembershipSM",
    "NodeMembership",
    "VisibilitySM",
    "NodeVisibility",
    "ConnectionSM",
    "UpstreamState",
    "DownstreamState",
]
