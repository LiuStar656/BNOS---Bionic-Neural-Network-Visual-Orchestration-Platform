"""统一节点状态管理器（阶段一骨架）。

只做：注册/注销、并发锁、事件防抖、Guard + 状态切换、信号广播、
调试观测接口（dump_all / audit_log / validate_all）。
真正的文件 I/O 与子节点遍历由 NodeStateActionService 承担。
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from PySide6.QtCore import QObject, Signal

from ui.core.state.orthogonal.node_connection import (
    ConnectionSM,
    DownstreamState,
    UpstreamState,
)
from ui.core.state.orthogonal.node_membership import (
    MembershipSM,
    NodeMembership,
)
from ui.core.state.orthogonal.node_visibility import (
    NodeVisibility,
    VisibilitySM,
)
from ui.core.state.route_cache import RouteCache
from ui.core.state.state_validator import is_valid_combined_state, validate_all_states
from ui.core.state.transition_table import (
    TRANSITION_TABLE,
    candidate_keys,
)

# 不同事件的防抖时间窗（毫秒）
DEFAULT_DEBOUNCE_MS: dict[str, int] = {
    "expand": 150,
    "collapse": 150,
    "start": 300,
    "stop": 300,
    "switch_entry_node": 200,
    "compress_into_composite": 200,
    "decompress_from_composite": 200,
}

# 审计流水环形缓冲上限
_AUDIT_RING_LIMIT = 5000


class NodeStateManager(QObject):
    """统一节点状态管理器。"""

    # node_name, old_state_dict, new_state_dict
    state_changed = Signal(str, dict, dict)
    # node_name, event, reason
    illegal_event = Signal(str, str, str)

    def __init__(self, composite_manager_ref: Any = None, action_service_ref: Any = None):
        super().__init__()
        self._composite_mgr = composite_manager_ref
        self._action_svc = action_service_ref

        self._membership_sms: dict[str, MembershipSM] = {}
        self._visibility_sms: dict[str, VisibilitySM] = {}
        self._connection_sms: dict[str, ConnectionSM] = {}
        self._runtime_sms: dict[str, Any] = {}

        self._locks: dict[str, threading.Lock] = {}
        self._debounce_ms: dict[str, int] = dict(DEFAULT_DEBOUNCE_MS)
        self._last_event_at: dict[tuple[str, str], float] = {}

        self._audit: deque[dict] = deque(maxlen=_AUDIT_RING_LIMIT)
        self._last_event: dict[str, str] = {}

        self.route_cache = RouteCache()

        self._edge_keys: set[tuple[str, str, str, str, str]] = set()

    # ───────────── 线条注册 / 注销（EdgeKey 权威集合）─────────────
    def register_edge(self, key: tuple[str, str, str, str, str]) -> bool:
        if not isinstance(key, tuple | list) or len(key) != 5:
            return False
        try:
            immutable = tuple(str(x) for x in key)
        except Exception:  # noqa: BLE001
            return False
        self._edge_keys.add(immutable)
        return True

    def unregister_edge(self, key: tuple[str, str, str, str, str]) -> bool:
        try:
            immutable = tuple(str(x) for x in key)
        except Exception:  # noqa: BLE001
            return False
        if immutable in self._edge_keys:
            self._edge_keys.discard(immutable)
            return True
        return False

    def is_edge_registered(self, key: tuple[str, str, str, str, str]) -> bool:
        try:
            immutable = tuple(str(x) for x in key)
        except Exception:  # noqa: BLE001
            return False
        return immutable in self._edge_keys

    def get_all_edges(self) -> set[tuple[str, str, str, str, str]]:
        return set(self._edge_keys)

    # ───────────── 渲染门：权威边集判定 ─────────────

    @staticmethod
    def _edge_key_tuple(edge_key_or_tuple: Any) -> tuple[str, str, str, str, str] | None:
        """归一化 EdgeKey(namedtuple) / 5-tuple → 5 元组（字符串）。非法则返回 None。"""
        if edge_key_or_tuple is None:
            return None
        # namedtuple / tuple
        if hasattr(edge_key_or_tuple, "_fields") and len(edge_key_or_tuple._fields) >= 5:
            seq = tuple(edge_key_or_tuple)[:5]
        elif isinstance(edge_key_or_tuple, tuple | list):
            seq = tuple(edge_key_or_tuple[:5]) if len(edge_key_or_tuple) >= 5 else None
        else:
            return None
        if seq is None:
            return None
        try:
            return tuple(str(s) if s is not None else "" for s in seq)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _port_alias_equal(routing_type: str, a_port: str, b_port: str, *, is_upstream_pos: bool) -> bool:
        """复合节点端口别名等价比较（不区分大小写规范化后判定）。

        project_memory 硬约束（复合节点锚点名↔内部路由名映射）：
          - COMPOSITE_INPUT 位置（下游侧 5 元组第 5 位 tgt_port）: data ↔ default
          - COMPOSITE_OUTPUT 位置（上游侧 5 元组第 4 位 src_port）: default ↔ node_output
        """
        if a_port == b_port:
            return True
        ap = (a_port or "").strip().lower()
        bp = (b_port or "").strip().lower()
        if ap == bp:
            return True
        if routing_type == "COMPOSITE_INPUT" and not is_upstream_pos:
            # 下游侧接收端口（comp in_port）：data ↔ default
            if ap in {"data", "default"} and bp in {"data", "default"}:
                return True
        if routing_type == "COMPOSITE_OUTPUT" and is_upstream_pos:
            # 上游侧发送端口（comp out_port）：default ↔ node_output
            if ap in {"default", "node_output"} and bp in {"default", "node_output"}:
                return True
        return False

    @staticmethod
    def is_edge_valid_static(
        edge_key_or_tuple: Any,
        canonical_edge_set: set | frozenset | None,
    ) -> bool:
        """渲染门核心判定：给定 UI 边的 EdgeKey，判断它是否存在于配置权威的 CanonicalEdgeSet。

        为了兼容两种容器，本函数会把 canonical 中的项统一转为 5 元组比较：
        - canonical 里的元素是 EdgeKey（namedtuple，可 hash）
        - canvas 里的 edge._edge_key 也是 EdgeKey

        端口别名映射（project_memory 约束）：
        - COMPOSITE_INPUT (tgt_port, 5元组末位)：data ↔ default
        - COMPOSITE_OUTPUT (src_port, 5元组第4位)：default ↔ node_output
        除精确相等外，别名等价也算命中（解决虚线问题）。
        """
        key = NodeStateManager._edge_key_tuple(edge_key_or_tuple)
        if key is None:
            # 没 EdgeKey → 旧边 / 临时边，放行，避免老项目突然不能用
            return True
        if not canonical_edge_set:
            # 没跑过 Canonical 扫描 → 放行（灰度期保守策略）
            return True
        # 5元组 = (routing_type, src, tgt, src_port, tgt_port)
        rt, k_src, k_tgt, k_sp, k_tp = key
        # canonical_set 内的元素可能是 EdgeKey（namedtuple），也归一化到 5 元组比较
        for cand in canonical_edge_set:
            ct = NodeStateManager._edge_key_tuple(cand)
            if ct is None:
                continue
            crt, c_src, c_tgt, c_sp, c_tp = ct
            # routing_type + src/tgt 必须完全相等
            if crt != rt or c_src != k_src or c_tgt != k_tgt:
                continue
            # 第 4 位（src_port，上游发送端口位置）别名比较
            if not NodeStateManager._port_alias_equal(rt, k_sp, c_sp, is_upstream_pos=True):
                continue
            # 第 5 位（tgt_port，下游接收端口位置）别名比较
            if not NodeStateManager._port_alias_equal(rt, k_tp, c_tp, is_upstream_pos=False):
                continue
            return True
        return False

    def is_edge_valid(self, edge_key_or_tuple: Any, canonical_edge_set: set | None = None) -> bool:
        """实例方法，先走内存内的 _edge_keys（更轻）；没有再走外部 canonical_set。"""
        key = NodeStateManager._edge_key_tuple(edge_key_or_tuple)
        if key is None:
            return True
        if key in self._edge_keys:
            return True
        return NodeStateManager.is_edge_valid_static(edge_key_or_tuple, canonical_edge_set)

    # ───────────── 注册 / 注销 ─────────────

    def register_standalone(self, node_name: str, runtime_sm: Any = None) -> None:
        """注册独立节点。"""
        if node_name in self._membership_sms:
            raise ValueError(f"Node already registered: {node_name}")
        self._membership_sms[node_name] = MembershipSM(node_name, initial=NodeMembership.STANDALONE)
        self._visibility_sms[node_name] = VisibilitySM(node_name, initial=NodeVisibility.VISIBLE)
        self._connection_sms[node_name] = ConnectionSM(node_name)
        if runtime_sm is not None:
            self._runtime_sms[node_name] = runtime_sm
        self._locks[node_name] = threading.Lock()
        self._last_event[node_name] = ""

    def register_composite_child(
        self,
        node_name: str,
        comp_id: str,
        runtime_sm: Any = None,
        initially_hidden: bool = True,
    ) -> None:
        """注册复合节点内部子节点。"""
        if node_name in self._membership_sms:
            raise ValueError(f"Node already registered: {node_name}")
        self._membership_sms[node_name] = MembershipSM(
            node_name,
            initial=NodeMembership.COMPOSITE_CHILD,
            comp_id=comp_id,
        )
        vis = NodeVisibility.HIDDEN_COLLAPSED if initially_hidden else NodeVisibility.VISIBLE
        self._visibility_sms[node_name] = VisibilitySM(node_name, initial=vis)
        self._connection_sms[node_name] = ConnectionSM(node_name)
        if runtime_sm is not None:
            self._runtime_sms[node_name] = runtime_sm
        self._locks[node_name] = threading.Lock()
        self._last_event[node_name] = ""

    def register_composite(
        self,
        comp_id: str,
        child_names: list[str],
        entry_node: str,
        initially_collapsed: bool = True,
        runtime_sm: Any = None,
    ) -> None:
        """注册复合节点本体。"""
        if comp_id in self._membership_sms:
            raise ValueError(f"Composite already registered: {comp_id}")
        mode = NodeVisibility.COLLAPSED_MODE if initially_collapsed else NodeVisibility.EXPANDED_MODE
        self._membership_sms[comp_id] = MembershipSM(
            comp_id,
            initial=NodeMembership.COMPOSITE,
            comp_id=comp_id,
            child_node_names=list(child_names),
            entry_node=entry_node,
        )
        self._visibility_sms[comp_id] = VisibilitySM(comp_id, initial=mode)
        self._connection_sms[comp_id] = ConnectionSM(comp_id)
        if runtime_sm is not None:
            self._runtime_sms[comp_id] = runtime_sm
        self._locks[comp_id] = threading.Lock()
        self._last_event[comp_id] = ""

    def unregister(self, node_name: str) -> None:
        if node_name not in self._membership_sms:
            return
        with self._acquire_lock(node_name):
            self._membership_sms.pop(node_name, None)
            self._visibility_sms.pop(node_name, None)
            self._connection_sms.pop(node_name, None)
            self._runtime_sms.pop(node_name, None)
            self._last_event.pop(node_name, None)
            self.route_cache.clear(node_name)
        self._locks.pop(node_name, None)
        self._last_event_at = {k: v for k, v in self._last_event_at.items() if k[0] != node_name}
        to_remove = []
        for key in list(self._edge_keys):
            if len(key) >= 3 and (key[1] == node_name or key[2] == node_name):
                to_remove.append(key)
        for key in to_remove:
            self._edge_keys.discard(key)

    def is_registered(self, node_name: str) -> bool:
        return node_name in self._membership_sms

    # ───────────── 并发 / 防抖 ─────────────

    def _acquire_lock(self, node_name: str) -> threading.Lock:
        if node_name not in self._locks:
            self._locks[node_name] = threading.Lock()
        lock = self._locks[node_name]
        lock.acquire()
        return lock  # 由调用方在 try/finally 中 release

    def _is_debounced(self, node_name: str, event: str) -> bool:
        window_ms = self._debounce_ms.get(event)
        if not window_ms:
            return False
        now = time.monotonic()
        key = (node_name, event)
        last = self._last_event_at.get(key, 0.0)
        if (now - last) * 1000 < window_ms:
            return True
        self._last_event_at[key] = now
        return False

    # ───────────── 状态查询 ─────────────

    def get_state(self, node_name: str) -> dict:
        """获取完整状态五元组快照（用于比较前后变化 + 校验）。"""
        if not self.is_registered(node_name):
            return {}
        m_sm = self._membership_sms[node_name]
        v_sm = self._visibility_sms[node_name]
        c_sm = self._connection_sms[node_name]
        r_sm = self._runtime_sms.get(node_name)
        return {
            "membership": m_sm.state,
            "visibility": v_sm.state,
            "upstream_state": c_sm.state,
            "downstream_state": c_sm.downstream_state,
            "downstream_count": c_sm.downstream_count,
            "upstream_port": c_sm.upstream_port,
            "upstream_node_name": c_sm.upstream_node_name,
            "upstream_output_path": c_sm.upstream_output_path,
            "runtime": getattr(r_sm, "state", None),
            "comp_id": m_sm.comp_id,
            "entry_node": m_sm.entry_node,
            "child_node_names": list(m_sm.child_node_names),
            "last_event": self._last_event.get(node_name, ""),
        }

    def dump_all_node_states(self) -> dict[str, dict]:
        """一键全量快照（可 JSON 序列化）。"""
        return {name: self.get_state(name) for name in list(self._membership_sms.keys())}

    # ───────────── 合法性校验 ─────────────

    def validate_one(self, node_name: str) -> tuple[bool, str]:
        state = self.get_state(node_name)
        if not state:
            return False, f"node {node_name!r} not registered"
        return is_valid_combined_state(state)

    def validate_all(self) -> list[tuple[str, str]]:
        return validate_all_states(self.dump_all_node_states())

    # ───────────── 审计流水 ─────────────

    def get_audit_log(self, limit: int = 1000) -> list[dict]:
        if limit <= 0:
            return list(self._audit)
        return list(self._audit)[-limit:]

    def _append_audit(
        self, node_name: str, event: str, old: dict, new: dict, ok: bool, reason: str = "", elapsed_ms: float = 0.0
    ) -> None:
        self._audit.append(
            {
                "ts": time.time(),
                "node": node_name,
                "event": event,
                "ok": ok,
                "reason": reason,
                "old": old,
                "new": new,
                "elapsed_ms": elapsed_ms,
            }
        )

    # ───────────── 事件入口（核心）─────────────

    def _emit_illegal(self, node_name: str, event: str, reason: str) -> None:
        self.illegal_event.emit(node_name, event, reason)

    def _match_rule(self, node_name: str, event: str):
        """从细到粗查找 TRANSITION_TABLE 匹配规则。"""
        state = self.get_state(node_name)
        for key in candidate_keys(state, event):
            if key in TRANSITION_TABLE:
                return key, TRANSITION_TABLE[key], state
        return None, None, state

    def _apply_transitions(self, node_name: str, rule: dict) -> None:
        """按 rule['transition'] 分别在各正交 SM 上切换状态。"""
        for dim, (from_val, to_val) in rule.get("transition", {}).items():
            if dim == "membership":
                sm = self._membership_sms[node_name]
                if sm.state != from_val:
                    raise RuntimeError(f"[{node_name}] membership {sm.state} != from {from_val}")
                # MembershipSM 提供 compress/decompress 事件名
                if to_val == NodeMembership.COMPOSITE_CHILD:
                    sm.handle("compress_into_composite")
                elif to_val == NodeMembership.STANDALONE:
                    sm.handle("decompress_from_composite")
            elif dim == "visibility":
                sm = self._visibility_sms[node_name]
                if sm.state != from_val:
                    raise RuntimeError(f"[{node_name}] visibility {sm.state} != from {from_val}")
                if to_val in (NodeVisibility.VISIBLE, NodeVisibility.EXPANDED_MODE):
                    sm.handle("expand")
                elif to_val in (
                    NodeVisibility.HIDDEN_COLLAPSED,
                    NodeVisibility.COLLAPSED_MODE,
                ):
                    sm.handle("collapse")
            elif dim == "upstream":
                sm = self._connection_sms[node_name]
                if sm.state != from_val:
                    raise RuntimeError(f"[{node_name}] upstream {sm.state} != from {from_val}")
                if to_val == UpstreamState.CONNECTED:
                    sm.handle("connect_upstream")
                elif to_val == UpstreamState.DISCONNECTED:
                    sm.handle("disconnect_upstream")
                    sm.clear_upstream_meta()

    def _rollback_transitions(self, node_name: str, transition_spec: dict, old_state: dict) -> None:
        """动作失败时，把正交 SM 恢复到 old_state 对应值（内存级回滚）。

        注意：MembershipSM 内部只支持 STANDALONE<->COMPOSITE_CHILD，若失败是复合节点
        结构类变更，此处仅尽力而为；真正的数据一致性由 RouteCache Transaction 承担。
        """
        for dim, (_, _) in transition_spec.items():
            if dim == "membership":
                self._membership_sms[node_name]._state = old_state["membership"]
            elif dim == "visibility":
                self._visibility_sms[node_name]._state = old_state["visibility"]
            elif dim == "upstream":
                self._connection_sms[node_name]._state = old_state["upstream_state"]

    def handle_event(self, node_name: str, event: str, **kwargs) -> bool:
        """统一事件入口。

        返回 True 表示事件成功处理；False 表示非法/失败/被拒绝。
        """
        t0 = time.monotonic()
        lock = self._acquire_lock(node_name)
        try:
            # 1. 防抖
            if self._is_debounced(node_name, event):
                reason = "debounced duplicate"
                self._emit_illegal(node_name, event, reason)
                self._append_audit(
                    node_name,
                    event,
                    {},
                    {},
                    False,
                    reason,
                    (time.monotonic() - t0) * 1000,
                )
                return False

            # 2. 已注册？
            if not self.is_registered(node_name):
                reason = "node not registered"
                self._emit_illegal(node_name, event, reason)
                self._append_audit(
                    node_name,
                    event,
                    {},
                    {},
                    False,
                    reason,
                    (time.monotonic() - t0) * 1000,
                )
                return False

            # 3. 查找规则
            key, rule, old_state = self._match_rule(node_name, event)
            if rule is None:
                reason = f"no transition rule matched (event={event}, state={old_state.get('membership')}/{old_state.get('visibility')}/{old_state.get('upstream_state')})"
                self._emit_illegal(node_name, event, reason)
                self._append_audit(
                    node_name,
                    event,
                    old_state,
                    {},
                    False,
                    reason,
                    (time.monotonic() - t0) * 1000,
                )
                return False

            # 4. Guard 校验
            for guard in rule.get("guard", []) or []:
                if not guard(old_state):
                    reason = f"guard failed: {guard}"
                    self._emit_illegal(node_name, event, reason)
                    self._append_audit(
                        node_name,
                        event,
                        old_state,
                        {},
                        False,
                        reason,
                        (time.monotonic() - t0) * 1000,
                    )
                    return False

            # 5. 状态切换（纯内存）
            transition_spec = rule.get("transition", {})
            try:
                self._apply_transitions(node_name, rule)
            except Exception as ex:
                reason = f"apply_transitions failed: {ex}"
                self._emit_illegal(node_name, event, reason)
                self._append_audit(
                    node_name,
                    event,
                    old_state,
                    {},
                    False,
                    reason,
                    (time.monotonic() - t0) * 1000,
                )
                return False

            _new_state_before_action = self.get_state(node_name)

            # 6. 副作用调度（调用 ActionService）
            action_name: str = rule.get("action", "")
            transaction: bool = bool(rule.get("transaction", False))
            immediate_flush: bool = bool(rule.get("immediate_flush", False))

            action_ok = True
            action_reason = ""
            if action_name and self._action_svc is not None:
                try:
                    if transaction:
                        tx = self._action_svc.begin_transaction(node_name)
                        try:
                            self._action_svc.invoke(action_name, node_name, **kwargs)
                            tx.commit()
                        except Exception as ex:
                            tx.rollback()
                            self._rollback_transitions(node_name, transition_spec, old_state)
                            action_ok = False
                            action_reason = f"action {action_name} exception: {ex}"
                    else:
                        self._action_svc.invoke(action_name, node_name, **kwargs)
                        if immediate_flush:
                            self._action_svc.flush_route_cache(node_name)
                except Exception as ex:
                    action_ok = False
                    action_reason = f"action {action_name} invoke exception: {ex}"
                    self._rollback_transitions(node_name, transition_spec, old_state)

            if not action_ok:
                self._emit_illegal(node_name, event, action_reason)
                self._append_audit(
                    node_name,
                    event,
                    old_state,
                    {},
                    False,
                    action_reason,
                    (time.monotonic() - t0) * 1000,
                )
                return False

            # 7. 记录最近事件（用于 state_validator）
            self._last_event[node_name] = event
            final_state = self.get_state(node_name)

            # 8. 审计 + 广播
            self._append_audit(
                node_name,
                event,
                old_state,
                final_state,
                True,
                "",
                (time.monotonic() - t0) * 1000,
            )
            self.state_changed.emit(node_name, old_state, final_state)
            return True
        finally:
            lock.release()

    # ───────────── 便捷访问 ─────────────

    def membership_of(self, node_name: str) -> NodeMembership | None:
        sm = self._membership_sms.get(node_name)
        return sm.state if sm else None

    def visibility_of(self, node_name: str) -> NodeVisibility | None:
        sm = self._visibility_sms.get(node_name)
        return sm.state if sm else None

    def upstream_of(self, node_name: str) -> UpstreamState | None:
        sm = self._connection_sms.get(node_name)
        return sm.state if sm else None

    def downstream_of(self, node_name: str) -> DownstreamState | None:
        sm = self._connection_sms.get(node_name)
        return sm.downstream_state if sm else None

    # ───────────── 下游计数快捷接口（由 CanvasConnections 调用）─────────────

    def add_downstream(self, node_name: str) -> None:
        if node_name in self._connection_sms:
            self._connection_sms[node_name].add_downstream()

    def remove_downstream(self, node_name: str) -> None:
        if node_name in self._connection_sms:
            self._connection_sms[node_name].remove_downstream()

    def set_runtime_sm(self, node_name: str, runtime_sm: Any) -> None:
        """挂接运行状态机（STANDALONE/CHILD 使用 NodeRuntimeSM；COMPOSITE 使用 CompositeLifecycleSM）。"""
        if node_name in self._locks:
            with self._acquire_lock(node_name):
                self._runtime_sms[node_name] = runtime_sm
        else:
            self._runtime_sms[node_name] = runtime_sm
