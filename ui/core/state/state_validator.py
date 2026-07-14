"""全局状态合法性校验器。

基于「非法状态组合」规则集合，快速识别不可接受的五元组，
用于开发期调试与生产期告警。零业务依赖。
"""

from __future__ import annotations

from collections.abc import Callable

from ui.core.state.orthogonal.node_connection import UpstreamState
from ui.core.state.orthogonal.node_membership import NodeMembership
from ui.core.state.orthogonal.node_visibility import NodeVisibility

# 每条规则: Callable[[state_dict], (is_hit: bool, reason: str)]
# 约定: 返回 (True, reason) 表示命中非法组合。
RuleFn = Callable[[dict], tuple[bool, str]]

# 运行态字符串集合（用于 guard 快速判断，不直接依赖 node_runtime 防止循环导入）
_RUNTIME_RUNNING_LIKE = {"starting", "running", "idle", "stopping"}


# ───────────── 非法组合规则集合 ─────────────


def _rule_standalone_must_visible(s: dict) -> tuple[bool, str]:
    """独立节点必须始终 VISIBLE。"""
    if s.get("membership") == NodeMembership.STANDALONE and s.get("visibility") != NodeVisibility.VISIBLE:
        return True, (f"STANDALONE node visibility must always be VISIBLE, got {s.get('visibility')!r}")
    return False, ""


def _rule_composite_child_may_not_be_mode(s: dict) -> tuple[bool, str]:
    """COMPOSITE_CHILD 不可出现 EXPANDED_MODE / COLLAPSED_MODE。"""
    if s.get("membership") == NodeMembership.COMPOSITE_CHILD and s.get("visibility") in (
        NodeVisibility.EXPANDED_MODE,
        NodeVisibility.COLLAPSED_MODE,
    ):
        return True, "COMPOSITE_CHILD cannot use EXPANDED_MODE/COLLAPSED_MODE visibility"
    return False, ""


def _rule_composite_may_not_be_hidden(s: dict) -> tuple[bool, str]:
    """COMPOSITE 本体不可为 VISIBLE / HIDDEN_COLLAPSED（应为 *_MODE）。"""
    if s.get("membership") == NodeMembership.COMPOSITE and s.get("visibility") in (
        NodeVisibility.VISIBLE,
        NodeVisibility.HIDDEN_COLLAPSED,
    ):
        return True, "COMPOSITE must use EXPANDED_MODE/COLLAPSED_MODE visibility"
    return False, ""


def _rule_connected_must_have_upstream_path(s: dict) -> tuple[bool, str]:
    """CONNECTED 时必须有合法的 upstream_output_path。"""
    if s.get("upstream_state") == UpstreamState.CONNECTED and not s.get("upstream_output_path"):
        return True, "Upstream state == CONNECTED but upstream_output_path is empty"
    return False, ""


def _rule_child_compress_decompress_runtime_protection(s: dict) -> tuple[bool, str]:
    """运行中 COMPOSITE_CHILD 不可切换成员（compress/decompress 非法结果）。"""
    if s.get("membership") == NodeMembership.COMPOSITE_CHILD and s.get("last_event") == "decompress_from_composite":
        rt = s.get("runtime")
        if rt in _RUNTIME_RUNNING_LIKE:
            return True, f"Cannot decompress child while runtime == {rt}"
    if s.get("membership") == NodeMembership.COMPOSITE_CHILD and s.get("last_event") == "compress_into_composite":
        rt = s.get("runtime")
        if rt in _RUNTIME_RUNNING_LIKE:
            return True, f"Cannot compress into composite while runtime == {rt}"
    return False, ""


def _rule_composite_struct_modify_running(s: dict) -> tuple[bool, str]:
    """运行中的 COMPOSITE 不可执行结构变更类事件（增删子节点/切入口）。"""
    if s.get("membership") == NodeMembership.COMPOSITE:
        rt = s.get("runtime")
        evt = s.get("last_event")
        if rt in _RUNTIME_RUNNING_LIKE and evt in (
            "add_child_node",
            "remove_child_node",
            "switch_entry_node",
        ):
            return True, f"COMPOSITE runtime == {rt}, illegal structural event == {evt}"
    return False, ""


def _rule_downstream_count_nonnegative(s: dict) -> tuple[bool, str]:
    """下游连接计数不可为负。"""
    dc = s.get("downstream_count", 0)
    if isinstance(dc, int) and dc < 0:
        return True, f"downstream_count cannot be negative, got {dc}"
    return False, ""


ILLEGAL_COMBINATIONS: list[RuleFn] = [
    _rule_standalone_must_visible,
    _rule_composite_child_may_not_be_mode,
    _rule_composite_may_not_be_hidden,
    _rule_connected_must_have_upstream_path,
    _rule_child_compress_decompress_runtime_protection,
    _rule_composite_struct_modify_running,
    _rule_downstream_count_nonnegative,
]


# ───────────── 公开 API ─────────────


def is_valid_combined_state(state: dict) -> tuple[bool, str]:
    """校验单一节点的完整状态。

    Returns:
        (True, "")  合法。
        (False, reason) 非法，给出首个命中的原因。
    """
    for rule in ILLEGAL_COMBINATIONS:
        hit, reason = rule(state)
        if hit:
            return False, reason
    return True, ""


def validate_all_states(states: dict[str, dict]) -> list[tuple[str, str]]:
    """批量校验多个节点。

    Args:
        states: {node_name_or_comp_id: state_dict}

    Returns:
        [(node_name, reason), ...] 非法条目列表。
    """
    bad: list[tuple[str, str]] = []
    for name, s in states.items():
        ok, reason = is_valid_combined_state(s)
        if not ok:
            bad.append((name, reason))
    return bad
