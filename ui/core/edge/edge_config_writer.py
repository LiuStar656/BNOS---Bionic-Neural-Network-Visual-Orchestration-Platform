"""线条配置写入器（EdgeConfigWriter）。

将「创建边 / 删除边」对应的所有配置变更集中封装：
- 下游：listen_upper_file（默认端口） / port_mappings.<name>（其他端口）
- 上游：out_connections[source_port]
- 复合：input_routing / output_routing（通过 CompositeManager）

所有变更先写入 RouteCache，最后由调用方用 Transaction 包裹后一次性 flush_route_cache 原子落盘；
中途异常不写任何文件，保证一致性，杜绝「改了 listen_upper_file 但没清 out_connections」这样的半更新。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ui.core.config.config_merger import get_config_path
from ui.core.edge.edge_key import (
    ROUTING_COMPOSITE_INPUT,
    ROUTING_COMPOSITE_INTERNAL,
    ROUTING_COMPOSITE_OUTPUT,
    ROUTING_STANDALONE,
    ROUTING_STANDALONE_PORT_MAP,
    EdgeKey,
    edge_downstream_targets,
    parse_edge_key,
)
from ui.core.logger import logger
from ui.core.state.route_cache import RouteCache

# 哨兵：表示对 out_connections / port_mappings 这个 key 执行「删除该条目」
_DELETE_MARKER: Any = None


@dataclass
class PlanContext:
    """plan_create / plan_remove 需要的上下文（避免大量参数传参）。"""

    nodes_data: dict[str, dict]
    composite_manager: Any  # CompositeNode 实例或 None
    route_cache: RouteCache
    action_service: Any  # NodeStateActionService 实例或 None；优先用它的 path 解析函数


class EdgeConfigWriter:
    """集中计划并缓存所有线条相关的配置变更，不直接落盘。

    使用模式::

        writer = EdgeConfigWriter(...)
        with writer.begin_transaction(tx_owner=f"create_edge:{src}->{dst}"):
            writer.plan_create_edge(
                edge_key, src_name, dst_name, src_port=..., dst_port=..., src_anchor_port=..., dst_anchor_port=...
            )
        writer.flush_all()  # 此时 PendingWrites 被一次性 apply 到磁盘
    """

    # ── init ──

    def __init__(
        self,
        route_cache: RouteCache,
        action_service: Any = None,
        composite_manager: Any = None,
    ) -> None:
        self._cache = route_cache
        self._action = action_service
        self._comp_mgr = composite_manager
        # 调试计数器，每次 plan_* 调用后可查看
        self._call_seq: list[str] = []

    # ── 事务桥接（复用 action_service 或直接 new Transaction）──

    def begin_transaction(self, tx_owner: str):
        if self._action is not None and hasattr(self._action, "begin_transaction"):
            return self._action.begin_transaction(tx_owner)
        from ui.core.state.route_cache import Transaction

        return Transaction(self._cache, tx_owner)

    def flush_all(self):
        if self._action is not None and hasattr(self._action, "flush_route_cache"):
            return self._action.flush_route_cache(scope=None)
        # 无 action_service 时不真实落盘（返回缓存内的待写集合，便于单元测试断言）
        return self._cache.extract_all_pending()

    # ── 小工具：路径解析 ──

    def _node_cfg_path_from_name(self, ctx: PlanContext, node_name: str) -> Path | None:
        if node_name in ctx.nodes_data:
            p = ctx.nodes_data[node_name].get("path")
            if p:
                return Path(get_config_path(p))
        # Fallback via action_service
        if ctx.action_service is not None and hasattr(ctx.action_service, "_node_config_path"):
            try:
                return ctx.action_service._node_config_path(node_name)
            except Exception as e:  # noqa: BLE001
                logger.warning("[EDGE-WRITER] fallback node_cfg_path for %s failed: %s", node_name, e)
        return None

    @staticmethod
    def _internal_node_name_from_routing(target_composite: str, routing_port: str, composite_manager: Any) -> str:
        """从 composite.input port 的 source_* 字段反向解析出内部节点名（无则返回空串）。"""
        if not composite_manager or not hasattr(composite_manager, "_find_internal_by_port"):
            return ""
        try:
            name = composite_manager._find_internal_by_port(target_composite, routing_port, "input")
            if name:
                return name
        except Exception:  # noqa: BLE001
            pass
        if hasattr(composite_manager, "_find_entry_node"):
            try:
                if routing_port in {"data", "default"}:
                    name = composite_manager._find_entry_node(target_composite)
                    if name:
                        return name
            except Exception:  # noqa: BLE001
                pass
        return ""

    # ───────────────────────── plan_create_edge ─────────────────────────

    def plan_create_edge(
        self,
        edge_key: EdgeKey,
        source_node_name: str,
        target_node_name: str,
        *,
        src_port: str | None = None,
        dst_port: str | None = None,
        src_anchor_port: str = "default",
        dst_anchor_port: str = "default",
        ctx: PlanContext | None = None,
    ) -> None:
        """把「创建这条边」需要的所有配置写入写入 RouteCache（不真实落盘）。

        参数：
          src_port / dst_port：routing 里要用的真实端口（例如 composite input 的 "data"）
          src_anchor_port / dst_anchor_port：源/目标锚点的用户端口（用于 out_connections 的 key）
        """
        if ctx is None:
            ctx = PlanContext(
                nodes_data={}, composite_manager=self._comp_mgr, route_cache=self._cache, action_service=self._action
            )
        routing_type = parse_edge_key(edge_key)["routing_type"]
        self._call_seq.append(f"create[{routing_type}] {source_node_name}→{target_node_name}")
        # 上游 out_connections：除 composite_internal 外其他 4 类都要写
        if routing_type != ROUTING_COMPOSITE_INTERNAL:
            self._plan_set_source_out_connections(
                ctx,
                source_node_name,
                src_anchor_port or "default",
                self._out_conn_value_for_create(
                    routing_type, target_node_name, dst_port or dst_anchor_port or "default", ctx.composite_manager
                ),
            )
        # 下游 listen_upper_file / port_mappings / composite routing
        targets = edge_downstream_targets(edge_key, ctx.nodes_data, ctx.composite_manager)
        for tgt in targets:
            kind = tgt["kind"]
            if kind == "listen_upper_file":
                cfg_path = tgt["cfg_path"]
                value = tgt["value"]
                # 如果不是默认端口，则走 port_mappings；否则走 listen_upper_file
                # edge_downstream_targets 已根据 dst_port/端口类型分流，这里按它返回的 kind 处理
                self._cache.set_listen_upper_file(cfg_path, value)
                logger.info(
                    "[EDGE-WRITER][create] plan set listen_upper_file cfg=%s -> %r (routing=%s)",
                    cfg_path,
                    value,
                    routing_type,
                )
            elif kind == "port_mapping":
                cfg_path = tgt["cfg_path"]
                port = tgt["port"]
                value = tgt["value"]
                self._plan_set_port_mapping(cfg_path, port, value)
                logger.info(
                    "[EDGE-WRITER][create] plan set port_mapping cfg=%s port=%s -> %r (routing=%s)",
                    cfg_path,
                    port,
                    value,
                    routing_type,
                )
            elif kind == "composite_input_routing":
                comp_id = tgt["comp_id"]
                port = tgt["port"]
                route = tgt["route"]
                self._cache.set_composite_input_routing(comp_id, port, route)
                logger.info(
                    "[EDGE-WRITER][create] plan composite_input comp=%s port=%s route=%s",
                    comp_id,
                    port,
                    route,
                )
            elif kind == "composite_output_routing":
                comp_id = tgt["comp_id"]
                port = tgt["port"]
                route = tgt["route"]
                self._cache.set_composite_output_routing(comp_id, port, route)
                logger.info(
                    "[EDGE-WRITER][create] plan composite_output comp=%s port=%s route=%s",
                    comp_id,
                    port,
                    route,
                )

    # ───────────────────────── plan_remove_edge ─────────────────────────

    def plan_remove_edge(
        self,
        edge_key: EdgeKey,
        source_node_name: str,
        target_node_name: str,
        *,
        src_port: str | None = None,
        dst_port: str | None = None,
        src_anchor_port: str = "default",
        dst_anchor_port: str = "default",
        ctx: PlanContext | None = None,
    ) -> None:
        """把「删除这条边」需要的所有配置变更写入 RouteCache。"""
        if ctx is None:
            ctx = PlanContext(
                nodes_data={}, composite_manager=self._comp_mgr, route_cache=self._cache, action_service=self._action
            )
        routing_type = parse_edge_key(edge_key)["routing_type"]
        self._call_seq.append(f"remove[{routing_type}] {source_node_name}→{target_node_name}")
        # 上游 out_connections（对应创建时的写）
        if routing_type != ROUTING_COMPOSITE_INTERNAL:
            self._plan_clear_source_out_connections(ctx, source_node_name, src_anchor_port or "default")
        # 下游反向
        targets = edge_downstream_targets(edge_key, ctx.nodes_data, ctx.composite_manager)
        for tgt in targets:
            kind = tgt["kind"]
            if kind == "listen_upper_file":
                cfg_path = tgt["cfg_path"]
                self._cache.clear_listen_upper_file(cfg_path)
                logger.info(
                    "[EDGE-WRITER][remove] plan clear listen_upper_file cfg=%s (routing=%s)",
                    cfg_path,
                    routing_type,
                )
            elif kind == "port_mapping":
                cfg_path = tgt["cfg_path"]
                port = tgt["port"]
                self._plan_clear_port_mapping(cfg_path, port)
                logger.info(
                    "[EDGE-WRITER][remove] plan clear port_mapping cfg=%s port=%s (routing=%s)",
                    cfg_path,
                    port,
                    routing_type,
                )
            elif kind == "composite_input_routing":
                comp_id = tgt["comp_id"]
                port = tgt["port"]
                self._cache.clear_composite_routing(comp_id, port, direction="input")
                logger.info(
                    "[EDGE-WRITER][remove] plan clear composite_input comp=%s port=%s",
                    comp_id,
                    port,
                )
            elif kind == "composite_output_routing":
                comp_id = tgt["comp_id"]
                port = tgt["port"]
                self._cache.clear_composite_routing(comp_id, port, direction="output")
                logger.info(
                    "[EDGE-WRITER][remove] plan clear composite_output comp=%s port=%s",
                    comp_id,
                    port,
                )

    # ────────── 内部：源 out_connections / 目标 port_mappings 的缓存写入 ──────────

    def _plan_set_source_out_connections(
        self, ctx: PlanContext, source_name: str, anchor_port: str, value: str
    ) -> None:
        cfg_path = self._node_cfg_path_from_name(ctx, source_name)
        if cfg_path is None:
            logger.warning("[EDGE-WRITER] plan_set_source_out_connections skip: cfg_path for %s unknown", source_name)
            return
        self._cache.set_out_connection(str(cfg_path), anchor_port, value)

    def _plan_clear_source_out_connections(self, ctx: PlanContext, source_name: str, anchor_port: str) -> None:
        cfg_path = self._node_cfg_path_from_name(ctx, source_name)
        if cfg_path is None:
            logger.warning("[EDGE-WRITER] plan_clear_source_out_connections skip: cfg_path for %s unknown", source_name)
            return
        self._cache.clear_out_connection(str(cfg_path), anchor_port)

    @staticmethod
    def _out_conn_value_for_create(
        routing_type: str, target_node_name: str, dst_port_or_anchor: str, composite_manager: Any
    ) -> str:
        """镜像 canvas_connections 里写 out_connections 的真实格式。"""
        if routing_type in (ROUTING_STANDALONE, ROUTING_STANDALONE_PORT_MAP):
            # 普通节点→普通节点：out_connections[src_port] = f"{target}|{dst_port}"
            return f"{target_node_name}|{dst_port_or_anchor}"
        if routing_type == ROUTING_COMPOSITE_INPUT:
            # 外部→复合输入口：out_connections[src_port] = f"{internal_node}|{routing_port}"
            internal = EdgeConfigWriter._internal_node_name_from_routing(
                target_node_name, dst_port_or_anchor, composite_manager
            )
            return f"{internal or target_node_name}|{dst_port_or_anchor}"
        if routing_type == ROUTING_COMPOSITE_OUTPUT:
            # 复合输出口→外部节点：out_connections[src_port] = f"{target}|{dst_port}"（与普通一致）
            return f"{target_node_name}|{dst_port_or_anchor}"
        # composite_internal：理论不会走到这里（创建时已排除）
        return f"{target_node_name}|{dst_port_or_anchor}"

    # ────────── port_mappings 走 RouteCache 原生 set_port_mapping/clear_port_mapping 接口

    def _plan_set_port_mapping(self, cfg_path: str, port: str, value: str) -> None:
        self._cache.set_port_mapping(cfg_path, port, value)

    def _plan_clear_port_mapping(self, cfg_path: str, port: str) -> None:
        self._cache.clear_port_mapping(cfg_path, port)

    # ────────── Phase4.1 Morph：按 kind 清配置（供 composite_node morph 阶段B/前置使用）──────────

    def clear_by_kind(
        self,
        kind: str,
        cfg_path: str | None = None,
        *,
        port: str | None = None,
        comp_id: str | None = None,
    ) -> None:
        """按 kind/cfg_path/port/comp_id 原子清 1 个配置字段到 RouteCache。

        Args:
            kind: "listen_upper_file" / "port_mapping" / "composite_input_routing" / "composite_output_routing"
            cfg_path: node_config.json 或 composite.json 绝对路径
            port:     port_mapping / composite_*_routing 时的端口名
            comp_id:  composite_*_routing 时的复合节点 id（与 cfg_path 二选一即可，
                      内部会拿 RouteCache 的 comp_id 作为 primary key）
        """
        if kind == "listen_upper_file":
            if not cfg_path:
                logger.warning("[EDGE-WRITER][clear_by_kind] listen_upper_file need cfg_path")
                return
            self._cache.clear_listen_upper_file(cfg_path)
            logger.info("[EDGE-WRITER][clear_by_kind] listen_upper_file cfg=%s", cfg_path)
            return
        if kind == "port_mapping":
            if not cfg_path or not port:
                logger.warning("[EDGE-WRITER][clear_by_kind] port_mapping need cfg_path + port")
                return
            self._cache.clear_port_mapping(cfg_path, port)
            logger.info("[EDGE-WRITER][clear_by_kind] port_mapping cfg=%s port=%s", cfg_path, port)
            return
        if kind == "composite_input_routing":
            target_comp = comp_id
            if not target_comp and cfg_path:
                # cfg_path = .../composite_nodes/{comp_id}.json → 反推 comp_id
                p = Path(cfg_path)
                if p.stem.startswith("composite_"):
                    target_comp = p.stem
                else:
                    # 文件名不含前缀时，从 _LAST_SEEN_PROJECT_PATH + composite_nodes 比对
                    try:
                        from ui.core.node.composite_node import _LAST_SEEN_PROJECT_PATH

                        if _LAST_SEEN_PROJECT_PATH:
                            cdir = Path(_LAST_SEEN_PROJECT_PATH) / COMPOSITE_NODES_DIR_LOCAL
                            for f in cdir.glob("*.json"):
                                if f.resolve() == p.resolve():
                                    target_comp = f.stem
                                    break
                    except Exception:
                        pass
            if not target_comp or not port:
                logger.warning(
                    "[EDGE-WRITER][clear_by_kind] composite_input comp_id=%s port=%s invalid", target_comp, port
                )
                return
            self._cache.clear_composite_routing(target_comp, port, direction="input")
            logger.info("[EDGE-WRITER][clear_by_kind] composite_input comp=%s port=%s", target_comp, port)
            return
        if kind == "composite_output_routing":
            target_comp = comp_id
            if not target_comp and cfg_path:
                p = Path(cfg_path)
                if p.stem.startswith("composite_"):
                    target_comp = p.stem
                else:
                    try:
                        from ui.core.node.composite_node import _LAST_SEEN_PROJECT_PATH

                        if _LAST_SEEN_PROJECT_PATH:
                            cdir = Path(_LAST_SEEN_PROJECT_PATH) / COMPOSITE_NODES_DIR_LOCAL
                            for f in cdir.glob("*.json"):
                                if f.resolve() == p.resolve():
                                    target_comp = f.stem
                                    break
                    except Exception:
                        pass
            if not target_comp or not port:
                logger.warning(
                    "[EDGE-WRITER][clear_by_kind] composite_output comp=%s port=%s invalid", target_comp, port
                )
                return
            self._cache.clear_composite_routing(target_comp, port, direction="output")
            logger.info("[EDGE-WRITER][clear_by_kind] composite_output comp=%s port=%s", target_comp, port)
            return

        logger.warning("[EDGE-WRITER][clear_by_kind] unknown kind=%s", kind)


COMPOSITE_NODES_DIR_LOCAL = "composite_nodes"


# ── 全局单例：edge_config_writer（绑定到 RouteCache 全局单例）
#    外部 import 方式：from ui.core.edge.edge_config_writer import edge_config_writer
try:
    from ui.core.state.route_cache import RouteCache

    edge_config_writer: EdgeConfigWriter = EdgeConfigWriter(RouteCache.instance())
except Exception:
    edge_config_writer = EdgeConfigWriter(RouteCache())  # 兜底：本地 RouteCache 实例（通常不会走这里）
