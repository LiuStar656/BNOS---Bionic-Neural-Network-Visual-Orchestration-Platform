"""画布交互模式状态机。

消除 pan / connect / box-select / select 模式冲突，强化模式互斥，
新增 ESC 取消连线。

状态图::

    NORMAL ──begin_connect──▶ CONNECTING ──complete──▶ NORMAL
       │                         │ cancel (ESC/右键)
       │                         ▼
       │                       NORMAL
       │
       ├──begin_pan──▶ PANNING ──end_pan──▶ NORMAL
       │
       ├──begin_box──▶ BOX_SELECTING ──end_box──▶ NORMAL
       │
       └──click_node──▶ SINGLE_SELECT ──clear──▶ NORMAL
"""

from __future__ import annotations

from enum import Enum

from ui.core.state.base import StateMachine, Transition


class CanvasMode(str, Enum):
    """画布交互模式。"""

    NORMAL = "normal"
    CONNECTING = "connecting"  # 拖出连线中
    PANNING = "panning"  # 画布平移中
    BOX_SELECTING = "box_selecting"  # 框选中
    SINGLE_SELECT = "single_select"  # 单击选中节点


def _build_transitions() -> list[Transition]:
    """构造所有合法状态转换。只允许从 NORMAL 进入各模式。"""
    return [
        # ── 连线 ──
        Transition("begin_connect", CanvasMode.NORMAL, CanvasMode.CONNECTING),
        Transition("complete", CanvasMode.CONNECTING, CanvasMode.NORMAL),
        Transition("cancel", CanvasMode.CONNECTING, CanvasMode.NORMAL),
        # ── 平移 ──
        Transition("begin_pan", CanvasMode.NORMAL, CanvasMode.PANNING),
        Transition("end_pan", CanvasMode.PANNING, CanvasMode.NORMAL),
        # ── 框选 ──
        Transition("begin_box", CanvasMode.NORMAL, CanvasMode.BOX_SELECTING),
        Transition("end_box", CanvasMode.BOX_SELECTING, CanvasMode.NORMAL),
        # ── 单击选中 ──
        Transition("click_node", CanvasMode.NORMAL, CanvasMode.SINGLE_SELECT),
        Transition("clear", CanvasMode.SINGLE_SELECT, CanvasMode.NORMAL),
    ]


class CanvasModeSM(StateMachine):
    """画布交互模式状态机。

    模式互斥由状态图本身保证——所有模式只能从 NORMAL 进入，
    处于 CONNECTING / PANNING / BOX_SELECTING 时无法进入其他模式。
    """

    def __init__(self):
        super().__init__(
            initial_state=CanvasMode.NORMAL,
            transitions=_build_transitions(),
        )

    @property
    def is_interacting(self) -> bool:
        """是否处于非 NORMAL 的交互模式中。"""
        return self._state != CanvasMode.NORMAL

    def cancel_all(self) -> bool:
        """从任意交互模式回到 NORMAL。"""
        if self._state == CanvasMode.NORMAL:
            return False
        event_map = {
            CanvasMode.CONNECTING: "cancel",
            CanvasMode.PANNING: "end_pan",
            CanvasMode.BOX_SELECTING: "end_box",
            CanvasMode.SINGLE_SELECT: "clear",
        }
        return self.handle(event_map.get(self._state, "cancel"))
