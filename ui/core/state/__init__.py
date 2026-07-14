"""状态机模块 - 独立组件。

提供通用 StateMachine 基类、各领域专用状态机、以及节点统一状态管理器。
"""

from ui.core.state.base import StateMachine, Transition
from ui.core.state.node_state_action_service import NodeStateActionService
from ui.core.state.node_state_manager import NodeStateManager
from ui.core.state.orthogonal import (
    ConnectionSM,
    DownstreamState,
    MembershipSM,
    NodeMembership,
    NodeVisibility,
    UpstreamState,
    VisibilitySM,
)
from ui.core.state.route_cache import PendingWrites, RouteCache, Transaction
from ui.core.state.state_validator import (
    ILLEGAL_COMBINATIONS,
    is_valid_combined_state,
    validate_all_states,
)
from ui.core.state.transition_table import (
    TRANSITION_TABLE,
    candidate_keys,
    match_transition_key,
)

__all__ = [
    # base
    "StateMachine",
    "Transition",
    # orthogonal: membership
    "MembershipSM",
    "NodeMembership",
    # orthogonal: visibility
    "VisibilitySM",
    "NodeVisibility",
    # orthogonal: connection
    "ConnectionSM",
    "UpstreamState",
    "DownstreamState",
    # transaction / cache
    "RouteCache",
    "Transaction",
    "PendingWrites",
    # validator
    "ILLEGAL_COMBINATIONS",
    "is_valid_combined_state",
    "validate_all_states",
    # transition table
    "TRANSITION_TABLE",
    "match_transition_key",
    "candidate_keys",
    # manager + action
    "NodeStateManager",
    "NodeStateActionService",
]
