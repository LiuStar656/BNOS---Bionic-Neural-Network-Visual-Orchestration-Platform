"""Phase 4: EdgeInteractionSM 单元测试 (8 项)。"""

from PySide6.QtWidgets import QApplication

from ui.core.state.edge_interaction import EdgeInteractionSM, EdgeInteractionState

_app = QApplication.instance() or QApplication([])

S = EdgeInteractionState


# ======================================================================
# T4.1 hover handle 进入/退出
# ======================================================================


def test_hover_handle():
    sm = EdgeInteractionSM()
    assert sm.handle("hover_handle") is True
    assert sm.state == S.HOVERING_HANDLE

    assert sm.handle("leave") is True
    assert sm.state == S.IDLE


# ======================================================================
# T4.2 hover waypoint 进入/退出
# ======================================================================


def test_hover_wp():
    sm = EdgeInteractionSM()
    assert sm.handle("hover_wp") is True
    assert sm.state == S.HOVERING_WP

    assert sm.handle("leave") is True
    assert sm.state == S.IDLE


# ======================================================================
# T4.3 press → 250ms long_press → drag new WP → release
# ======================================================================


def test_full_long_press_create_wp():
    sm = EdgeInteractionSM()
    assert sm.handle("press_handle") is True
    assert sm.state == S.HOLDING_HANDLE

    assert sm.handle("long_press") is True
    assert sm.state == S.DRAGGING_NEW_WP

    assert sm.handle("release") is True
    assert sm.state == S.IDLE


# ======================================================================
# T4.4 press → leave 在 250ms 内 → 取消
# ======================================================================


def test_leave_cancels_hold():
    sm = EdgeInteractionSM()
    sm.handle("press_handle")
    assert sm.state == S.HOLDING_HANDLE

    assert sm.handle("leave") is True
    assert sm.state == S.IDLE


# ======================================================================
# T4.5 press waypoint → drag → release
# ======================================================================


def test_drag_existing_wp():
    sm = EdgeInteractionSM()
    assert sm.handle("press_wp") is True
    assert sm.state == S.DRAGGING_WP

    assert sm.handle("release") is True
    assert sm.state == S.IDLE


# ======================================================================
# T4.6 leave 从 HOVERING_WP 清除
# ======================================================================


def test_leave_from_hover_wp():
    sm = EdgeInteractionSM()
    sm.handle("hover_wp")
    assert sm.state == S.HOVERING_WP

    sm.handle("leave")
    assert sm.state == S.IDLE


# ======================================================================
# T4.7 模式互斥：HOVERING_HANDLE 时不能 press_wp
# ======================================================================


def test_mode_exclusion():
    sm = EdgeInteractionSM()
    sm.handle("hover_handle")
    assert sm.handle("press_wp") is False
    assert sm.state == S.HOVERING_HANDLE


# ======================================================================
# T4.8 快速短按（<250ms）→ release 直接回到 IDLE
# ======================================================================


def test_quick_press_no_long_press():
    sm = EdgeInteractionSM()
    sm.handle("press_handle")
    assert sm.state == S.HOLDING_HANDLE

    # 没有 long_press，直接 release → IDLE
    assert sm.handle("release") is True
    assert sm.state == S.IDLE
