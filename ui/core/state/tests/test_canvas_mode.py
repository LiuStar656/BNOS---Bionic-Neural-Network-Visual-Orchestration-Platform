"""Phase 3: CanvasModeSM 单元测试 (10 项)。"""

from PySide6.QtWidgets import QApplication

from ui.core.state.canvas_mode import CanvasMode, CanvasModeSM

_app = QApplication.instance() or QApplication([])


# ======================================================================
# T3.1 所有模式从 NORMAL 进入
# ======================================================================


def test_all_mode_entries():
    sm = CanvasModeSM()
    # CONNECTING
    assert sm.handle("begin_connect") is True
    assert sm.state == CanvasMode.CONNECTING
    sm.handle("cancel")

    # PANNING
    assert sm.handle("begin_pan") is True
    assert sm.state == CanvasMode.PANNING
    sm.handle("end_pan")

    # BOX_SELECTING
    assert sm.handle("begin_box") is True
    assert sm.state == CanvasMode.BOX_SELECTING
    sm.handle("end_box")

    # SINGLE_SELECT
    assert sm.handle("click_node") is True
    assert sm.state == CanvasMode.SINGLE_SELECT
    sm.handle("clear")

    assert sm.state == CanvasMode.NORMAL


# ======================================================================
# T3.2 所有模式回到 NORMAL
# ======================================================================


def test_all_mode_exits():
    sm = CanvasModeSM()
    for event in ("begin_connect", "begin_pan", "begin_box", "click_node"):
        sm.reset()
        assert sm.handle(event) is True
        # cancel_all 回到 NORMAL
        ok = sm.cancel_all()
        assert ok is True
        assert sm.state == CanvasMode.NORMAL


# ======================================================================
# T3.3 模式互斥：CONNECTING 中 → begin_pan 无效
# ======================================================================


def test_connecting_blocks_pan():
    sm = CanvasModeSM()
    sm.handle("begin_connect")
    assert sm.handle("begin_pan") is False
    assert sm.state == CanvasMode.CONNECTING


# ======================================================================
# T3.4 模式互斥：PANNING 中 → begin_connect 无效
# ======================================================================


def test_panning_blocks_connect():
    sm = CanvasModeSM()
    sm.handle("begin_pan")
    assert sm.handle("begin_connect") is False
    assert sm.state == CanvasMode.PANNING


# ======================================================================
# T3.5 模式互斥：BOX_SELECTING 中 → begin_connect 无效
# ======================================================================


def test_box_blocks_connect():
    sm = CanvasModeSM()
    sm.handle("begin_box")
    assert sm.handle("begin_connect") is False
    assert sm.state == CanvasMode.BOX_SELECTING


# ======================================================================
# T3.6 ESC 取消连线
# ======================================================================


def test_cancel_connect():
    sm = CanvasModeSM()
    sm.handle("begin_connect")
    assert sm.handle("cancel") is True
    assert sm.state == CanvasMode.NORMAL


# ======================================================================
# T3.7 complete 完成连线
# ======================================================================


def test_complete_connect():
    sm = CanvasModeSM()
    sm.handle("begin_connect")
    assert sm.handle("complete") is True
    assert sm.state == CanvasMode.NORMAL


# ======================================================================
# T3.8 快速切换：connect→cancel×100
# ======================================================================


def test_rapid_toggle():
    sm = CanvasModeSM()
    for _ in range(100):
        assert sm.handle("begin_connect") is True
        assert sm.state == CanvasMode.CONNECTING
        assert sm.handle("cancel") is True
        assert sm.state == CanvasMode.NORMAL


# ======================================================================
# T3.9 entry/exit action 副作用（通过 signal+manual 验证）
# ======================================================================


def test_mode_changed_signal():
    sm = CanvasModeSM()
    events: list[tuple[str, str]] = []
    sm.state_changed.connect(lambda old, new: events.append((old, new)))

    sm.handle("begin_connect")
    sm.handle("cancel")
    sm.handle("begin_pan")
    sm.handle("end_pan")

    assert events == [
        (CanvasMode.NORMAL, CanvasMode.CONNECTING),
        (CanvasMode.CONNECTING, CanvasMode.NORMAL),
        (CanvasMode.NORMAL, CanvasMode.PANNING),
        (CanvasMode.PANNING, CanvasMode.NORMAL),
    ]


# ======================================================================
# T3.10 is_interacting 属性
# ======================================================================


def test_is_interacting():
    sm = CanvasModeSM()
    assert sm.is_interacting is False

    sm.handle("begin_connect")
    assert sm.is_interacting is True

    sm.handle("cancel")
    assert sm.is_interacting is False
