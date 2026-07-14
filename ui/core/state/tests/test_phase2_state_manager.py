"""Phase 2: NodeStateManager + TRANSITION_TABLE + Guard 验证。

本测试用例专注于：
 1) NodeStateManager 注册接口（standalone / composite_child / composite）
 2) TRANSITION_TABLE 匹配与事件处理（connect / disconnect / expand / collapse / compress / decompress / switch_entry）
 3) 运行时 Guard 拦截（节点 running 时，结构/连接变更应被拒绝）
 4) state_validator 非法状态组合检测

零真实文件系统 IO；CompositeManager 接口以简易 stub 代替。
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.core.state.node_state_action_service import NodeStateActionService
from ui.core.state.node_state_manager import NodeStateManager
from ui.core.state.orthogonal.node_connection import UpstreamState
from ui.core.state.orthogonal.node_membership import NodeMembership
from ui.core.state.orthogonal.node_visibility import NodeVisibility
from ui.core.state.state_validator import is_valid_combined_state
from ui.core.state.transition_table import TRANSITION_TABLE, guard_not_running

_app = QApplication.instance() or QApplication([])


# ───────────── CompositeManager Stub (只实现 ActionService 反射调用的几个方法) ─────────────


class _DummyCompositeMgr:
    """极简 stub：保存 composites 字典 + 端口路由字典；落盘方法空实现。"""

    def __init__(self) -> None:
        self._composites: dict[str, dict] = {}
        self._routings: dict[str, dict] = {}
        self._project_path: str = ""
        self.saves_called: int = 0

    # ---- 由 action_service 通过 getattr 反射调用的方法 ----

    def _get_port_routing(self, comp_id: str) -> dict:
        return self._routings.setdefault(comp_id, {"input": {}, "output": {}})

    def set_input_routing(self, comp_id: str, port_name: str, source_output_path: str) -> None:
        routing = self._routings.setdefault(comp_id, {"input": {}, "output": {}})
        routing.setdefault("input", {})
        if source_output_path == "" or source_output_path is None:
            routing["input"].pop(port_name, None)
        else:
            routing["input"][port_name] = {"source_output_path": source_output_path}

    def clear_input_routing(self, comp_id: str, port_name: str) -> None:
        routing = self._routings.setdefault(comp_id, {"input": {}, "output": {}})
        routing.setdefault("input", {}).pop(port_name, None)

    def set_output_routing(
        self,
        comp_id: str,
        port_name: str,
        target_composite: str,
        target_node: str = "",
        target_port: str = "default",
    ) -> None:  # pragma: no cover - 当前 action 未触发 output 路由
        routing = self._routings.setdefault(comp_id, {"input": {}, "output": {}})
        routing.setdefault("output", {})[port_name] = {
            "target_composite": target_composite,
            "target_node": target_node,
            "target_port": target_port,
        }

    def clear_output_routing(self, comp_id: str, port_name: str) -> None:  # pragma: no cover
        routing = self._routings.setdefault(comp_id, {"input": {}, "output": {}})
        routing.setdefault("output", {}).pop(port_name, None)

    def save(self) -> None:
        self.saves_called += 1

    def _sync_routing_to_config(self, comp_id: str) -> None:  # noqa: ARG002 - 签名需要
        # 空实现：仅保证不会抛异常
        return None


def _build_stack() -> tuple[NodeStateManager, NodeStateActionService, _DummyCompositeMgr]:
    """构建 manager + action_service + 伪 composite_manager。"""
    mgr = NodeStateManager()
    comp_mgr = _DummyCompositeMgr()
    mgr._composite_mgr = comp_mgr  # 方便 guard_composite_children_not_running 调试（实际未使用）
    svc = NodeStateActionService(mgr, composite_manager_ref=comp_mgr)
    mgr._action_svc = svc
    return mgr, svc, comp_mgr


# ══════════════════════════════════════════════════════════
# T-P2.1 注册接口 + 初始状态查询
# ══════════════════════════════════════════════════════════


def test_register_and_initial_state():
    mgr, _, _ = _build_stack()

    mgr.register_standalone("node_python_1")
    mgr.register_composite_child("entry_a", comp_id="comp_abc")
    mgr.register_composite_child("proc_b", comp_id="comp_abc")
    mgr.register_composite(
        comp_id="comp_abc",
        child_names=["entry_a", "proc_b"],
        entry_node="entry_a",
        initially_collapsed=True,
    )

    # standalone 查询
    s = mgr.get_state("node_python_1")
    assert s["membership"] == NodeMembership.STANDALONE
    assert s["visibility"] == NodeVisibility.VISIBLE
    assert s["upstream_state"] == UpstreamState.DISCONNECTED

    # child 查询
    s = mgr.get_state("entry_a")
    assert s["membership"] == NodeMembership.COMPOSITE_CHILD
    assert s["visibility"] == NodeVisibility.HIDDEN_COLLAPSED
    assert s["comp_id"] == "comp_abc"

    # composite 查询
    s = mgr.get_state("comp_abc")
    assert s["membership"] == NodeMembership.COMPOSITE
    assert s["visibility"] == NodeVisibility.COLLAPSED_MODE
    assert s["entry_node"] == "entry_a"
    assert set(s["child_node_names"]) == {"entry_a", "proc_b"}

    # 全量合法性校验
    bad = mgr.validate_all()
    assert bad == [], f"unexpected illegal states: {bad}"


# ══════════════════════════════════════════════════════════
# T-P2.2 STANDALONE connect → disconnect 流程
# ══════════════════════════════════════════════════════════


def test_standalone_connect_disconnect_flow():
    mgr, _, _ = _build_stack()
    mgr.register_standalone("node_python_1")

    # connect 应成功
    ok = mgr.handle_event(
        "node_python_1",
        "connect_upstream",
        source_output_path="/project/nodes/node_python_0/output.json",
        upstream_node_name="node_python_0",
        port_name="default",
    )
    assert ok is True
    s = mgr.get_state("node_python_1")
    assert s["upstream_state"] == UpstreamState.CONNECTED
    assert s["upstream_node_name"] == "node_python_0"
    assert s["upstream_output_path"].endswith("output.json")

    # disconnect 应成功
    ok = mgr.handle_event("node_python_1", "disconnect_upstream")
    assert ok is True
    s = mgr.get_state("node_python_1")
    assert s["upstream_state"] == UpstreamState.DISCONNECTED
    assert s["upstream_output_path"] == ""


# ══════════════════════════════════════════════════════════
# T-P2.3 运行态 Guard 拦截 connect / disconnect / compress / decompress
# ══════════════════════════════════════════════════════════


def _inject_runtime(mgr: NodeStateManager, node_name: str, runtime_state: str) -> None:
    """给节点挂一个伪 runtime SM（只有 state 属性）。"""

    class _R:
        def __init__(self, s: str) -> None:
            self.state = s

    mgr.set_runtime_sm(node_name, _R(runtime_state))


def test_guard_not_running_blocks_structural_events():
    # 先纯函数校验 guard
    assert guard_not_running({"runtime": None}) is True
    assert guard_not_running({"runtime": "stopped"}) is True
    assert guard_not_running({"runtime": "created"}) is True
    for bad in ("starting", "running", "idle", "stopping"):
        assert guard_not_running({"runtime": bad}) is False, f"should block runtime={bad}"

    # 再通过 Manager 做一次端到端验证
    mgr, _, _ = _build_stack()
    mgr.register_standalone("node_python_1")
    _inject_runtime(mgr, "node_python_1", "running")

    ok = mgr.handle_event(
        "node_python_1",
        "connect_upstream",
        source_output_path="/x/y.json",
    )
    # 运行态 connect 应被 guard 拦截
    assert ok is False
    assert mgr.upstream_of("node_python_1") == UpstreamState.DISCONNECTED


# ══════════════════════════════════════════════════════════
# T-P2.4 Compress (STANDALONE → COMPOSITE_CHILD) & Decompress 回返
# ══════════════════════════════════════════════════════════


def test_compress_and_decompress_membership():
    mgr, svc, comp_mgr = _build_stack()

    # 先把 composite 注册好（压缩时目标复合节点已经存在）
    comp_mgr._composites["comp_abc"] = {
        "nodes": ["entry_a"],
        "entry_node": "entry_a",
        "input_ports": [
            {"port_name": "default", "internal_node": "entry_a"},
        ],
        "output_ports": [],
    }

    mgr.register_standalone("node_python_1")
    mgr.register_composite_child("entry_a", comp_id="comp_abc", initially_hidden=True)
    mgr.register_composite(
        comp_id="comp_abc",
        child_names=["entry_a"],
        entry_node="entry_a",
        initially_collapsed=True,
    )

    # Compress: node_python_1 从 STANDALONE → COMPOSITE_CHILD
    # 注意：需要把 MembershipSM.comp_id 预设置好（实际压缩逻辑应由外层在事件触发前设置）
    msm = mgr._membership_sms["node_python_1"]
    msm.comp_id = "comp_abc"
    # 把 child_node_names 也加入到 composite 的 MembershipSM
    comp_msm = mgr._membership_sms["comp_abc"]
    if "node_python_1" not in comp_msm.child_node_names:
        comp_msm.child_node_names.append("node_python_1")

    ok = mgr.handle_event("node_python_1", "compress_into_composite")
    assert ok is True
    assert mgr.membership_of("node_python_1") == NodeMembership.COMPOSITE_CHILD
    # 新复合子节点保持 VISIBLE（展开态）
    assert mgr.visibility_of("node_python_1") == NodeVisibility.VISIBLE

    # Decompress: COMPOSITE_CHILD → STANDALONE
    ok = mgr.handle_event("node_python_1", "decompress_from_composite")
    assert ok is True
    assert mgr.membership_of("node_python_1") == NodeMembership.STANDALONE
    assert mgr.visibility_of("node_python_1") == NodeVisibility.VISIBLE


# ══════════════════════════════════════════════════════════
# T-P2.5 switch_entry_node 触发 action_composite_switch_entry
# ══════════════════════════════════════════════════════════


def test_switch_entry_updates_comp_state():
    mgr, svc, comp_mgr = _build_stack()
    comp_mgr._composites["comp_abc"] = {
        "nodes": ["entry_a", "proc_b"],
        "entry_node": "entry_a",
        "input_ports": [],
        "output_ports": [],
    }
    mgr.register_composite_child("entry_a", comp_id="comp_abc", initially_hidden=False)
    mgr.register_composite_child("proc_b", comp_id="comp_abc", initially_hidden=False)
    mgr.register_composite(
        comp_id="comp_abc",
        child_names=["entry_a", "proc_b"],
        entry_node="entry_a",
        initially_collapsed=False,  # EXPANDED_MODE
    )

    ok = mgr.handle_event("comp_abc", "switch_entry_node", new_entry="proc_b")
    assert ok is True

    # 内存 SM entry_node 被更新
    assert mgr._membership_sms["comp_abc"].entry_node == "proc_b"
    # composite manager 数据结构也被更新
    assert comp_mgr._composites["comp_abc"]["entry_node"] == "proc_b"


# ══════════════════════════════════════════════════════════
# T-P2.6 TRANSITION_TABLE 关键条目存在性校验（避免未来重构丢失）
# ══════════════════════════════════════════════════════════


def test_transition_table_key_coverage():
    required_keys = [
        # standalone 基础
        f"{NodeMembership.STANDALONE}.{NodeVisibility.VISIBLE}.{UpstreamState.DISCONNECTED}.connect_upstream",
        f"{NodeMembership.STANDALONE}.{NodeVisibility.VISIBLE}.{UpstreamState.CONNECTED}.disconnect_upstream",
        # child visible
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.{UpstreamState.DISCONNECTED}.connect_upstream",
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.{UpstreamState.CONNECTED}.disconnect_upstream",
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.{UpstreamState.CONNECTED}.collapse",
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.{UpstreamState.DISCONNECTED}.collapse",
        # child hidden
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.{UpstreamState.DISCONNECTED}.connect_upstream",
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.{UpstreamState.CONNECTED}.disconnect_upstream",
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.{UpstreamState.CONNECTED}.expand",
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.{UpstreamState.DISCONNECTED}.expand",
        # composite bulk
        f"{NodeMembership.COMPOSITE}.{NodeVisibility.COLLAPSED_MODE}.expand",
        f"{NodeMembership.COMPOSITE}.{NodeVisibility.EXPANDED_MODE}.collapse",
        f"{NodeMembership.COMPOSITE}.{NodeVisibility.EXPANDED_MODE}.switch_entry_node",
        f"{NodeMembership.COMPOSITE}.{NodeVisibility.COLLAPSED_MODE}.switch_entry_node",
        # membership 转换
        f"{NodeMembership.STANDALONE}.compress_into_composite",
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.VISIBLE}.decompress_from_composite",
        f"{NodeMembership.COMPOSITE_CHILD}.{NodeVisibility.HIDDEN_COLLAPSED}.decompress_from_composite",
    ]
    missing = [k for k in required_keys if k not in TRANSITION_TABLE]
    assert not missing, f"Missing TRANSITION_TABLE keys: {missing}"


# ══════════════════════════════════════════════════════════
# T-P2.7 state_validator 非法状态组合检测
# ══════════════════════════════════════════════════════════


def test_state_validator_illegal_combos():
    # 独立节点必须 VISIBLE
    ok, reason = is_valid_combined_state(
        {
            "membership": NodeMembership.STANDALONE,
            "visibility": NodeVisibility.HIDDEN_COLLAPSED,
        }
    )
    assert ok is False and "STANDALONE node visibility" in reason

    # COMPOSITE_CHILD 不可用 EXPANDED_MODE
    ok, reason = is_valid_combined_state(
        {
            "membership": NodeMembership.COMPOSITE_CHILD,
            "visibility": NodeVisibility.EXPANDED_MODE,
        }
    )
    assert ok is False and "EXPANDED_MODE/COLLAPSED_MODE" in reason

    # COMPOSITE 本体不可用 VISIBLE
    ok, reason = is_valid_combined_state(
        {
            "membership": NodeMembership.COMPOSITE,
            "visibility": NodeVisibility.VISIBLE,
        }
    )
    assert ok is False and "COMPOSITE must use" in reason

    # CONNECTED 必须有 upstream_output_path
    ok, reason = is_valid_combined_state(
        {
            "membership": NodeMembership.STANDALONE,
            "visibility": NodeVisibility.VISIBLE,
            "upstream_state": UpstreamState.CONNECTED,
            "upstream_output_path": "",
        }
    )
    assert ok is False and "upstream_output_path is empty" in reason

    # downstream_count 不能为负
    ok, reason = is_valid_combined_state(
        {
            "membership": NodeMembership.STANDALONE,
            "visibility": NodeVisibility.VISIBLE,
            "downstream_count": -1,
        }
    )
    assert ok is False and "downstream_count cannot be negative" in reason

    # 合法示例
    ok, _ = is_valid_combined_state(
        {
            "membership": NodeMembership.STANDALONE,
            "visibility": NodeVisibility.VISIBLE,
            "upstream_state": UpstreamState.CONNECTED,
            "upstream_output_path": "/a/b.json",
            "downstream_count": 0,
        }
    )
    assert ok is True


# ══════════════════════════════════════════════════════════
# T-P2.8 未知/非法事件不会崩溃，返回 False
# ══════════════════════════════════════════════════════════


def test_unknown_event_returns_false_gracefully():
    mgr, _, _ = _build_stack()
    mgr.register_standalone("node_python_1")
    # 完全未知的事件
    ok = mgr.handle_event("node_python_1", "totally_made_up_event_xyz")
    assert ok is False
    # 未注册节点
    ok = mgr.handle_event("ghost_node_999", "connect_upstream")
    assert ok is False
    # audit log 中记录了非法事件
    audit = mgr.get_audit_log(limit=10)
    assert any(not e["ok"] for e in audit), "illegal events should be recorded in audit"
