"""Phase 1: NodeRuntimeSM 单元测试 (13 项)。"""

from PySide6.QtWidgets import QApplication

from ui.core.state.node_runtime import NodeRuntimeSM, NodeRuntimeState

_app = QApplication.instance() or QApplication([])


# ======================================================================
# T1.1 正常启动流程
# ======================================================================


def test_normal_start_lifecycle():
    sm = NodeRuntimeSM()
    assert sm.state == NodeRuntimeState.STOPPED

    assert sm.handle("start") is True
    assert sm.state == NodeRuntimeState.STARTING

    assert sm.handle("start_ok") is True
    assert sm.state == NodeRuntimeState.RUNNING


# ======================================================================
# T1.2 启动失败
# ======================================================================


def test_start_fail():
    sm = NodeRuntimeSM()
    sm.handle("start")
    assert sm.handle("start_fail") is True
    assert sm.state == NodeRuntimeState.CRASHED


# ======================================================================
# T1.3 运行中 crash
# ======================================================================


def test_crash_from_running():
    sm = NodeRuntimeSM()
    sm.handle("start")
    sm.handle("start_ok")
    assert sm.state == NodeRuntimeState.RUNNING

    assert sm.handle("crash") is True
    assert sm.state == NodeRuntimeState.CRASHED


# ======================================================================
# T1.4 child_idle / child_resume 互转
# ======================================================================


def test_idle_resume_cycle():
    sm = NodeRuntimeSM()
    sm.handle("start")
    sm.handle("start_ok")

    assert sm.handle("child_idle") is True
    assert sm.state == NodeRuntimeState.IDLE

    assert sm.handle("child_resume") is True
    assert sm.state == NodeRuntimeState.RUNNING


# ======================================================================
# T1.5 正常停止
# ======================================================================


def test_normal_stop():
    sm = NodeRuntimeSM()
    sm.handle("start")
    sm.handle("start_ok")

    assert sm.handle("stop") is True
    assert sm.state == NodeRuntimeState.STOPPING

    assert sm.handle("stop_ok") is True
    assert sm.state == NodeRuntimeState.STOPPED


# ======================================================================
# T1.6 停止失败 → CRASHED
# ======================================================================


def test_stop_fail():
    sm = NodeRuntimeSM()
    sm.handle("start")
    sm.handle("start_ok")
    sm.handle("stop")
    assert sm.state == NodeRuntimeState.STOPPING

    assert sm.handle("stop_fail") is True
    assert sm.state == NodeRuntimeState.CRASHED


# ======================================================================
# T1.7 crash 后重试
# ======================================================================


def test_retry_after_crash():
    sm = NodeRuntimeSM()
    sm.handle("start")
    sm.handle("start_fail")
    assert sm.state == NodeRuntimeState.CRASHED

    assert sm.handle("retry") is True
    assert sm.state == NodeRuntimeState.STARTING


# ======================================================================
# T1.8 crash 后手动关停
# ======================================================================


def test_direct_stop_after_crash():
    sm = NodeRuntimeSM()
    sm.handle("start")
    sm.handle("start_fail")
    assert sm.state == NodeRuntimeState.CRASHED

    assert sm.handle("direct_stop") is True
    assert sm.state == NodeRuntimeState.STOPPED


# ======================================================================
# T1.9 不能从 STOPPED 直接到 RUNNING
# ======================================================================


def test_cannot_skip_states():
    sm = NodeRuntimeSM()
    assert sm.handle("start_ok") is False
    assert sm.state == NodeRuntimeState.STOPPED

    assert sm.handle("child_idle") is False
    assert sm.state == NodeRuntimeState.STOPPED


# ======================================================================
# T1.10 不能从 RUNNING 再 start
# ======================================================================


def test_cannot_start_while_running():
    sm = NodeRuntimeSM()
    sm.handle("start")
    sm.handle("start_ok")
    assert sm.state == NodeRuntimeState.RUNNING

    assert sm.handle("start") is False
    assert sm.state == NodeRuntimeState.RUNNING


# ======================================================================
# T1.11 state_changed 信号 emit
# ======================================================================


def test_signal_emission():
    sm = NodeRuntimeSM()
    received: list[tuple[str, str]] = []
    sm.state_changed.connect(lambda old, new: received.append((old, new)))

    sm.handle("start")
    sm.handle("start_ok")
    sm.handle("stop")
    sm.handle("stop_ok")

    assert received == [
        (NodeRuntimeState.STOPPED, NodeRuntimeState.STARTING),
        (NodeRuntimeState.STARTING, NodeRuntimeState.RUNNING),
        (NodeRuntimeState.RUNNING, NodeRuntimeState.STOPPING),
        (NodeRuntimeState.STOPPING, NodeRuntimeState.STOPPED),
    ]


# ======================================================================
# T1.12 兼容层：字符串值兼容
# ======================================================================


def test_string_compatibility():
    """NodeRuntimeState 继承 str，可用 == 比较裸字符串。"""
    assert NodeRuntimeState.STOPPED == "stopped"
    assert NodeRuntimeState.RUNNING == "running"
    assert NodeRuntimeState.CRASHED == "crashed"

    # 状态机 state 属性也是 str 兼容
    sm = NodeRuntimeSM()
    assert sm.state == "stopped"
    sm.handle("start")
    assert sm.state == "starting"


# ======================================================================
# T1.13 快速连续 start/stop 不产生非法状态
# ======================================================================


def test_rapid_start_stop():
    sm = NodeRuntimeSM()

    # 第一次 start
    assert sm.handle("start") is True
    assert sm.state == NodeRuntimeState.STARTING
    # 重复 start 被拒绝
    assert sm.handle("start") is False
    assert sm.state == NodeRuntimeState.STARTING

    # 正常完成启动
    sm.handle("start_ok")
    assert sm.state == NodeRuntimeState.RUNNING

    # stop
    sm.handle("stop")
    assert sm.state == NodeRuntimeState.STOPPING
    # 重复 stop 被拒绝
    assert sm.handle("stop") is False
    assert sm.state == NodeRuntimeState.STOPPING

    # 完成停止
    sm.handle("stop_ok")
    assert sm.state == NodeRuntimeState.STOPPED
