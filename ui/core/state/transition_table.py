"""数据驱动 TRANSITION_TABLE（阶段二完整）。

覆盖：standalone/child_visible/child_hidden 的上下游 connect/disconnect；
expand/collapse 单节点与 composite 批量；
compress/decompress 成员角色切换；
switch_entry_node 复合入口切换。

运行时保护由 Guard 函数承担。
"""

from __future__ import annotations

from collections.abc import Callable

from ui.core.state.orthogonal.node_connection import UpstreamState
from ui.core.state.orthogonal.node_membership import NodeMembership
from ui.core.state.orthogonal.node_visibility import NodeVisibility

# Guard: Callable[[state_dict], bool]  返回 False 表示拦截
GuardFn = Callable[[dict], bool]
# Action 名: str，交给 NodeStateActionService.invoke(name) 分发
ActionName = str

TransitionRule = dict
# 单条 rule 的标准结构:
# {
#     "guard": [GuardFn, ...],
#     "transition": {
#         "membership":   (from_value, to_value),    # 可选
#         "visibility":   (from_value, to_value),    # 可选
#         "upstream":     (from_value, to_value),    # 可选（ConnectionSM 上游）
#     },
#     "action": ActionName,
#     "transaction": bool,                 # expand/collapse 批量场景 True
#     "immediate_flush": bool,             # disconnect 类立即落盘
# }

_RUNTIME_RUNNING_LIKE = {"starting", "running", "idle", "stopping"}


# ───────────── Guard 函数集合 ─────────────


def guard_not_running(state: dict) -> bool:
    """通用：非运行态才允许结构/连接变更。"""
    rt = state.get("runtime")
    return rt not in _RUNTIME_RUNNING_LIKE


def guard_composite_children_not_running(state: dict) -> bool:
    """对 COMPOSITE 节点：要求自身 + 所有子节点都非运行态。

    注意：state_dict 里仅携带本节点 runtime，子节点运行状态需要外部
    通过 state.get("_children_runtimes", {}) 注入；没有注入时默认放行。
    """
    rt = state.get("runtime")
    if rt in _RUNTIME_RUNNING_LIKE:
        return False
    child_rts = state.get("_children_runtimes", {}) or {}
    for v in child_rts.values():
        if v in _RUNTIME_RUNNING_LIKE:
            return False
    return True


# ───────────── key 匹配辅助函数 ─────────────


def _s(s: dict) -> tuple[str, str, str, str]:
    """从 state_dict 提取四元组 (membership, visibility, upstream, downstream)。"""
    return (
        str(s.get("membership", "")),
        str(s.get("visibility", "")),
        str(s.get("upstream_state", "")),
        str(s.get("downstream_state", "")),
    )


def match_transition_key(state: dict, event: str) -> str:
    """基于当前状态 + 事件，生成匹配 TRANSITION_TABLE 的查找 key。

    命名约定（从粗到细，层级依次降级；找不到时可由上层再尝试粗 key）：
      1. {membership}.{visibility}.{upstream_state}.{event}   最细
      2. {membership}.{visibility}.{event}                    中等
      3. {membership}.{event}                                 较粗
      4. global.{event}                                       兜底（极少用）
    """
    m, v, up, _ = _s(state)
    # 依次按精度从高到低返回；上层对 key 使用 dict.get 多轮查找
    if up:
        return f"{m}.{v}.{up}.{event}"
    return f"{m}.{v}.{event}"


def candidate_keys(state: dict, event: str) -> list[str]:
    """生成从细到粗的候选 key 序列，供 Manager 多轮查找。"""
    m = str(state.get("membership", ""))
    v = str(state.get("visibility", ""))
    up = str(state.get("upstream_state", ""))
    keys: list[str] = []
    if up:
        keys.append(f"{m}.{v}.{up}.{event}")
    keys.append(f"{m}.{v}.{event}")
    keys.append(f"{m}.{event}")
    keys.append(f"global.{event}")
    return keys


# ───────────── TRANSITION_TABLE（阶段二完整矩阵）─────────────


TRANSITION_TABLE: dict[str, TransitionRule] = {
    # ═══════════════════ STANDALONE ═══════════════════
    # ── 独立节点 connect_upstream ──
    f"{NodeMembership.STANDALONE}.{NodeVisibility.VISIBLE}.{UpstreamState.DISCONNECTED}.connect_upstream": {
        "guard": [guard_not_running],
        "transition": {
            "upstream": (UpstreamState.DISCONNECTED, UpstreamState.CONNECTED),
        },
        "action": "action_standalone_connect_upstream",
        "transaction": False,
        "immediate_flush": False,
    },
    # ── 独立节点 disconnect_upstream ──
    f"{NodeMembership.STANDALONE}.{NodeVisibility.VISIBLE}.{UpstreamState.CONNECTED}.disconnect_upstream": {
        "guard": [guard_not_running],
        "transition": {
            "upstream": (UpstreamState.CONNECTED, UpstreamState.DISCONNECTED),
        },
        "action": "action_standalone_disconnect_upstream",
        "transaction": False,
        "immediate_flush": True,
    },
    # ═══════════════════ COMPOSITE_CHILD (visible = expanded) ═══════════════════
    # ── 子节点（展开+未连）connect_upstream ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.{UpstreamState.DISCONNECTED}.connect_upstream": {
        "guard": [guard_not_running],
        "transition": {
            "upstream": (UpstreamState.DISCONNECTED, UpstreamState.CONNECTED),
        },
        "action": "action_child_visible_connect_upstream",
        "transaction": False,
        "immediate_flush": True,
    },
    # ── 子节点（展开+已连）disconnect_upstream ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.{UpstreamState.CONNECTED}.disconnect_upstream": {
        "guard": [guard_not_running],
        "transition": {
            "upstream": (UpstreamState.CONNECTED, UpstreamState.DISCONNECTED),
        },
        "action": "action_child_visible_disconnect_upstream",
        "transaction": False,
        "immediate_flush": True,
    },
    # ── 子节点（展开+已连）collapse → HIDDEN ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.{UpstreamState.CONNECTED}.collapse": {
        "guard": [],
        "transition": {
            "visibility": (NodeVisibility.VISIBLE, NodeVisibility.HIDDEN_COLLAPSED),
        },
        "action": "action_child_collapse_with_connection",
        "transaction": False,
        "immediate_flush": True,
    },
    # ── 子节点（展开+未连）collapse ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.{UpstreamState.DISCONNECTED}.collapse": {
        "guard": [],
        "transition": {
            "visibility": (NodeVisibility.VISIBLE, NodeVisibility.HIDDEN_COLLAPSED),
        },
        "action": "action_child_collapse_no_connection",
        "transaction": False,
        "immediate_flush": False,
    },
    # ═══════════════════ COMPOSITE_CHILD (hidden = collapsed) ═══════════════════
    # ── 子节点（折叠+未连）connect_upstream ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.{UpstreamState.DISCONNECTED}.connect_upstream": {
        "guard": [guard_not_running],
        "transition": {
            "upstream": (UpstreamState.DISCONNECTED, UpstreamState.CONNECTED),
        },
        "action": "action_child_hidden_connect_upstream",
        "transaction": False,
        "immediate_flush": True,
    },
    # ── 子节点（折叠+已连）disconnect_upstream ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.{UpstreamState.CONNECTED}.disconnect_upstream": {
        "guard": [guard_not_running],
        "transition": {
            "upstream": (UpstreamState.CONNECTED, UpstreamState.DISCONNECTED),
        },
        "action": "action_child_hidden_disconnect_upstream",
        "transaction": False,
        "immediate_flush": True,
    },
    # ── 子节点（折叠+已连）expand → VISIBLE ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.{UpstreamState.CONNECTED}.expand": {
        "guard": [],
        "transition": {
            "visibility": (NodeVisibility.HIDDEN_COLLAPSED, NodeVisibility.VISIBLE),
        },
        "action": "action_child_expand_with_connection",
        "transaction": False,
        "immediate_flush": False,
    },
    # ── 子节点（折叠+未连）expand ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.{UpstreamState.DISCONNECTED}.expand": {
        "guard": [],
        "transition": {
            "visibility": (NodeVisibility.HIDDEN_COLLAPSED, NodeVisibility.VISIBLE),
        },
        "action": "action_child_expand_no_connection",
        "transaction": False,
        "immediate_flush": False,
    },
    # ═══════════════════ COMPOSITE (整体) ═══════════════════
    # ── 复合节点整体 expand（事务批量）──
    f"{NodeMembership.COMPOSITE}.{NodeVisibility.COLLAPSED_MODE}.expand": {
        "guard": [guard_composite_children_not_running],
        "transition": {
            "visibility": (NodeVisibility.COLLAPSED_MODE, NodeVisibility.EXPANDED_MODE),
        },
        "action": "action_composite_expand_batch",
        "transaction": True,
        "immediate_flush": True,
    },
    # ── 复合节点整体 collapse（事务批量）──
    f"{NodeMembership.COMPOSITE}.{NodeVisibility.EXPANDED_MODE}.collapse": {
        "guard": [guard_composite_children_not_running],
        "transition": {
            "visibility": (NodeVisibility.EXPANDED_MODE, NodeVisibility.COLLAPSED_MODE),
        },
        "action": "action_composite_collapse_batch",
        "transaction": True,
        "immediate_flush": True,
    },
    # ── 复合节点切换入口节点 (两种可见性模式都允许) ──
    f"{NodeMembership.COMPOSITE}.{NodeVisibility.EXPANDED_MODE}.switch_entry_node": {
        "guard": [guard_not_running],
        "transition": {},
        "action": "action_composite_switch_entry",
        "transaction": False,
        "immediate_flush": True,
    },
    f"{NodeMembership.COMPOSITE}.{NodeVisibility.COLLAPSED_MODE}.switch_entry_node": {
        "guard": [guard_not_running],
        "transition": {},
        "action": "action_composite_switch_entry",
        "transaction": False,
        "immediate_flush": True,
    },
    # ═══════════════════ Membership 动态转换 (compress / decompress) ═══════════════════
    # ── STANDALONE → COMPOSITE_CHILD (compress_into_composite)  无论 upstream 状态 ──
    #    粗粒度 key: membership + event（从细到粗查找；未连上的 CONNECTED 变体也会落到粗 key）
    f"{NodeMembership.STANDALONE}.compress_into_composite": {
        "guard": [guard_not_running],
        "transition": {
            "membership": (NodeMembership.STANDALONE, NodeMembership.COMPOSITE_CHILD),
        },
        "action": "action_compress_into_composite",
        "transaction": False,
        "immediate_flush": True,
    },
    # ── COMPOSITE_CHILD (VISIBLE, any upstream) → STANDALONE (decompress) ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.decompress_from_composite": {
        "guard": [guard_not_running],
        "transition": {
            "membership": (NodeMembership.COMPOSITE_CHILD, NodeMembership.STANDALONE),
            # Membership 切换后，可见性必须由 HIDDEN/VISIBLE → VISIBLE (STANDALONE 不变量)
            "visibility": (NodeVisibility.VISIBLE, NodeVisibility.VISIBLE),
        },
        "action": "action_decompress_preserve_connection",
        "transaction": False,
        "immediate_flush": True,
    },
    # ── COMPOSITE_CHILD (HIDDEN_COLLAPSED, any upstream) → STANDALONE ──
    f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.decompress_from_composite": {
        "guard": [guard_not_running],
        "transition": {
            "membership": (NodeMembership.COMPOSITE_CHILD, NodeMembership.STANDALONE),
            # Decompress 后独立节点必须是可见的
            "visibility": (NodeVisibility.HIDDEN_COLLAPSED, NodeVisibility.VISIBLE),
        },
        "action": "action_decompress_preserve_connection",
        "transaction": False,
        "immediate_flush": True,
    },
}
