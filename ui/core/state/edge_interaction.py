"""边交互状态机。

消除 edge_item.py 中 8 个状态变量的碎片化，修复长按定时器泄漏，
用单个状态枚举替代 _hovered_handle / _hovered_wp / _drag_wp_index
/ _drag_is_new / _press_pos / _press_on_handle / _long_press_fired
/ _long_press_timer。

状态图::

    IDLE ──hover_handle──▶ HOVERING_HANDLE ──leave──▶ IDLE
       │
       ├──hover_wp──▶ HOVERING_WP ──leave──▶ IDLE
       │
       ├──press_handle──▶ HOLDING_HANDLE ──long_press──▶ DRAGGING_NEW_WP ──release──▶ IDLE
       │                      │ leave                        │
       │                      ▼                              │
       │                    IDLE                            │
       │                                                    │
       └──press_wp──▶ DRAGGING_WP ──release──▶ IDLE
"""

from __future__ import annotations

from enum import Enum

from ui.core.state.base import StateMachine, Transition


class EdgeInteractionState(str, Enum):
    """边交互状态。"""

    IDLE = "idle"
    HOVERING_HANDLE = "hovering_handle"  # 鼠标悬停在控制柄上
    HOVERING_WP = "hovering_wp"  # 鼠标悬停在 waypoint 上
    HOLDING_HANDLE = "holding_handle"  # 按住控制柄（等待长按）
    DRAGGING_NEW_WP = "dragging_new_wp"  # 拖动新创建的 waypoint
    DRAGGING_WP = "dragging_wp"  # 拖动已有 waypoint


def _build_transitions() -> list[Transition]:
    """构造所有合法状态转换。"""
    return [
        # ── hover 进入 ──
        Transition("hover_handle", EdgeInteractionState.IDLE, EdgeInteractionState.HOVERING_HANDLE),
        Transition("hover_wp", EdgeInteractionState.IDLE, EdgeInteractionState.HOVERING_WP),
        # ── hover 退出 ──
        Transition("leave", EdgeInteractionState.HOVERING_HANDLE, EdgeInteractionState.IDLE),
        Transition("leave", EdgeInteractionState.HOVERING_WP, EdgeInteractionState.IDLE),
        # ── 按下控制柄 → 等待长按 ──
        Transition("press_handle", EdgeInteractionState.IDLE, EdgeInteractionState.HOLDING_HANDLE),
        Transition("press_handle", EdgeInteractionState.HOVERING_HANDLE, EdgeInteractionState.HOLDING_HANDLE),
        # ── 长按触发 → 开始拖动新 waypoint ──
        Transition("long_press", EdgeInteractionState.HOLDING_HANDLE, EdgeInteractionState.DRAGGING_NEW_WP),
        # ── 短按 release（不够 250ms）→ 回到 IDLE（不创建 waypoint）──
        Transition("release", EdgeInteractionState.HOLDING_HANDLE, EdgeInteractionState.IDLE),
        # ── 拖动 waypoint ──
        Transition("press_wp", EdgeInteractionState.IDLE, EdgeInteractionState.DRAGGING_WP),
        Transition("press_wp", EdgeInteractionState.HOVERING_WP, EdgeInteractionState.DRAGGING_WP),
        # ── release 结束拖动 ──
        Transition("release", EdgeInteractionState.DRAGGING_NEW_WP, EdgeInteractionState.IDLE),
        Transition("release", EdgeInteractionState.DRAGGING_WP, EdgeInteractionState.IDLE),
        # ── leave 取消等待 ──
        Transition("leave", EdgeInteractionState.HOLDING_HANDLE, EdgeInteractionState.IDLE),
    ]


class EdgeInteractionSM(StateMachine):
    """边交互状态机。

    替代 edge_item.py 中原有的 8 个独立状态变量。
    """

    def __init__(self):
        super().__init__(
            initial_state=EdgeInteractionState.IDLE,
            transitions=_build_transitions(),
        )
