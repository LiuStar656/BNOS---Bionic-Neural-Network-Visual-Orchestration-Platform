"""Phase 2: CompositeLifecycleSM 单元测试 (10 项)。"""

from PySide6.QtWidgets import QApplication

from ui.core.state.composite_lifecycle import CompositeLifecycleSM, CompositeLifecycleState

_app = QApplication.instance() or QApplication([])

S = CompositeLifecycleState  # 简写


def _go_running(sm: CompositeLifecycleSM):
    """辅助：CREATED → RUNNING。"""
    sm.handle("start")
    sm.handle("start_ok")
    assert sm.state == S.RUNNING


# ======================================================================
# T2.1 正常生命周期
# ======================================================================


def test_normal_lifecycle():
    sm = CompositeLifecycleSM()
    assert sm.state == S.CREATED

    sm.handle("start")
    assert sm.state == S.STARTING

    sm.handle("start_ok")
    assert sm.state == S.RUNNING

    sm.handle("stop")
    assert sm.state == S.STOPPING

    sm.handle("stop_ok")
    assert sm.state == S.STOPPED


# ======================================================================
# T2.2 启动超时 → CRASHED
# ======================================================================


def test_start_timeout():
    sm = CompositeLifecycleSM()
    sm.handle("start")
    assert sm.handle("start_timeout") is True
    assert sm.state == S.CRASHED


# ======================================================================
# T2.3 运行时 crash
# ======================================================================


def test_crash_while_running():
    sm = CompositeLifecycleSM()
    _go_running(sm)
    assert sm.handle("crash") is True
    assert sm.state == S.CRASHED


# ======================================================================
# T2.4 停止失败 → CRASHED
# ======================================================================


def test_stop_fail():
    sm = CompositeLifecycleSM()
    _go_running(sm)
    sm.handle("stop")
    assert sm.state == S.STOPPING
    assert sm.handle("stop_fail") is True
    assert sm.state == S.CRASHED


# ======================================================================
# T2.5 TOCTOU 防护：重复 start
# ======================================================================


def test_no_duplicate_start():
    sm = CompositeLifecycleSM()
    sm.handle("start")
    assert sm.state == S.STARTING

    # 第二次 start 被拒绝（不在 STOPPED/CRASHED/CREATED）
    assert sm.handle("start") is False
    assert sm.state == S.STARTING

    sm.handle("start_ok")
    assert sm.state == S.RUNNING

    # RUNNING 时 start 被拒绝
    assert sm.handle("start") is False
    assert sm.state == S.RUNNING


# ======================================================================
# T2.6 TOCTOU 防护：同时 stop
# ======================================================================


def test_no_duplicate_stop():
    sm = CompositeLifecycleSM()
    _go_running(sm)

    sm.handle("stop")
    assert sm.state == S.STOPPING

    # 第二次 stop 被拒绝
    assert sm.handle("stop") is False
    assert sm.state == S.STOPPING


# ======================================================================
# T2.7 CRASHED 后 restart
# ======================================================================


def test_restart_after_crash():
    sm = CompositeLifecycleSM()
    _go_running(sm)
    sm.handle("crash")
    assert sm.state == S.CRASHED

    assert sm.handle("start") is True
    assert sm.state == S.STARTING


# ======================================================================
# T2.8 decompress 从 CREATED
# ======================================================================


def test_decompress_from_created():
    sm = CompositeLifecycleSM()
    assert sm.handle("decompress") is True
    assert sm.state == S.REMOVING
    assert sm.handle("remove_done") is True
    assert sm.state == S.REMOVED


# ======================================================================
# T2.9 decompress 时正处于 STARTING
# ======================================================================


def test_decompress_during_start():
    sm = CompositeLifecycleSM()
    sm.handle("start")
    assert sm.state == S.STARTING

    assert sm.handle("decompress") is True
    assert sm.state == S.REMOVING


# ======================================================================
# T2.10 is_active / is_restartable / is_terminal
# ======================================================================


def test_properties():
    sm = CompositeLifecycleSM()
    assert sm.is_active is False
    assert sm.is_restartable is True
    assert sm.is_terminal is False

    sm.handle("start")
    assert sm.is_active is True
    assert sm.is_restartable is False

    sm.handle("start_ok")
    assert sm.is_active is True

    sm.handle("stop")
    assert sm.is_active is True

    sm.handle("stop_ok")
    assert sm.is_active is False
    assert sm.is_restartable is True

    sm.handle("decompress")
    sm.handle("remove_done")
    assert sm.is_terminal is True
    assert sm.is_restartable is False
