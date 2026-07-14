"""节点状态副作用调度器（阶段二完整实现）。

承担 TRANSITION_TABLE['action'] 的注册与调用；
持有 RouteCache 并提供 begin_transaction / flush_route_cache。

真实副作用包括：
- 读写节点 node_config.json 中的 listen_upper_file / out_connections
- 通过 CompositeNodeManager 更新 node_clusters.json 里 comp['_port_routing']
  并同步写入 composite.json (external_connections)
- expand/collapse 批量遍历子节点做配置双向同步
- compress/decompress 时保留 / 迁移外部连接配置
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ui.core.state.route_cache import PendingWrites, RouteCache, Transaction

logger = logging.getLogger(__name__)


ActionFn = Callable[[str, ...], None]  # (node_name, **kwargs) -> None


# port_name aliases for entry-node main port: internal "data" <-> external "default"
_MAIN_PORT_ALIASES = {"data", "default"}


# ───────────── small helpers (keep file-local) ─────────────


def _extract_node_from_path(file_path: str) -> str | None:
    """Extract node name from paths like .../nodes/<name>/output.json or ../../<name>/output.json."""
    if not file_path:
        return None
    normalized = file_path.replace("\\", "/")
    m = re.search(r"/nodes/([^/]+)", normalized)
    if m:
        return m.group(1)
    m = re.search(r"\.\./([^/]+)/output\.json", normalized)
    if m:
        return m.group(1)
    return None


def _is_relative_external(listen_value: str, internal_set: set[str]) -> bool:
    """Return True if listen_value points to a node that is NOT one of the internals."""
    if not listen_value:
        return False
    upstream = _extract_node_from_path(listen_value)
    return bool(upstream and upstream not in internal_set)


class NodeStateActionService:
    """Node state action dispatcher."""

    def __init__(
        self,
        state_manager,
        composite_manager_ref: Any = None,
    ):
        self._mgr = state_manager
        self._composite_mgr = composite_manager_ref
        # 可选：由 NodeCanvas（或 BNOS 主窗口）在启动时注入，用于解析 node_config.json / project_path
        # 灰度阶段 composite_manager_ref 可能尚未创建（仅 NodeCanvas.__init__ 提前挂单例），
        # 此时通过 _parent_window_ref 也能定位 nodes_data 和 project_path。
        self._parent_window_ref: Any = None
        self._actions: dict[str, ActionFn] = {}
        # Shared RouteCache instance with manager
        self._cache: RouteCache = state_manager.route_cache
        self._register_default_actions()

    # ─────────────────────────────────────────────
    # Project path / filesystem helpers
    # ─────────────────────────────────────────────

    @property
    def project_path(self) -> Path | None:
        # 优先级 1：composite_manager 持有（composite_node_manager 懒创建后设置）
        if self._composite_mgr is not None:
            try:
                pp = getattr(self._composite_mgr, "_project_path", None)
                if pp:
                    return Path(pp)
            except Exception:  # noqa: BLE001
                pass
        # 优先级 2：NodeCanvas/parent_window 注入（早期单例初始化场景）
        if self._parent_window_ref is not None:
            try:
                pp = getattr(self._parent_window_ref, "current_project_path", None)
                if pp:
                    return Path(pp)
            except Exception:  # noqa: BLE001
                pass
        return None

    def _node_config_dir(self, node_name: str) -> Path | None:
        """Resolve node folder (nodes/<name>) — children of composites live in nodes/ too."""
        # 优先级 1：从 parent_window.nodes_data 的 path 直接拿（最准，不依赖目录扫描）
        if self._parent_window_ref is not None:
            try:
                nodes_data = getattr(self._parent_window_ref, "nodes_data", None) or {}
                info = nodes_data.get(node_name) or {}
                p = info.get("path") or ""
                if p:
                    return Path(p)
            except Exception:  # noqa: BLE001
                pass
        root = self.project_path
        if not root:
            return None
        for base in ("nodes", "composite_nodes"):
            candidate = root / base / node_name
            if candidate.is_dir():
                return candidate
        return root / "nodes" / node_name  # optimistic fallback for newly created nodes

    def _node_config_path(self, node_name: str) -> Path | None:
        d = self._node_config_dir(node_name)
        return None if d is None else d / "node_config.json"

    def _read_node_config(self, node_name: str) -> dict:
        p = self._node_config_path(node_name)
        if p is None or not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8")) or {}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("read_node_config %s failed: %s", node_name, e)
            return {}

    def _write_node_config(self, node_name: str, cfg: dict) -> None:
        p = self._node_config_path(node_name)
        if p is None:
            # 灰度阶段：找不到路径不抛异常，仅告警 + 跳过写（旧逻辑已先写，不回滚主状态推进）
            logger.warning(
                "[Phase3-gray] action skip write_node_config for %s: cannot resolve config path. "
                "Old config logic still applied (non-fatal).",
                node_name,
            )
            return
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps(cfg, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError as e:
            # 灰度阶段：写入失败仅告警（不 raise，避免主状态推进被回滚）
            logger.warning(
                "[Phase3-gray] action write_node_config for %s failed (non-fatal, skip rollback): %s",
                node_name,
                e,
            )

    # ─────────────────────────────────────────────
    # Composite metadata / port maps (read from live comp dict)
    # ─────────────────────────────────────────────

    def _comp(self, comp_id: str) -> dict:
        if self._composite_mgr is None:
            return {}
        return self._composite_mgr._composites.get(comp_id, {})

    def _build_port_to_internal(self, comp_id: str) -> dict[str, str]:
        comp = self._comp(comp_id)
        mapping: dict[str, str] = {}
        for p in comp.get("input_ports", []):
            name = p.get("port_name") or p.get("name")
            intern = p.get("internal_node") or p.get("target_node")
            if name and intern:
                mapping[name] = intern
                if name in _MAIN_PORT_ALIASES:
                    mapping["default"] = intern
                    mapping["data"] = intern
        for p in comp.get("output_ports", []):
            name = p.get("port_name") or p.get("name")
            intern = p.get("internal_node") or p.get("source_node")
            if name and intern:
                mapping[name] = intern
        return mapping

    def _build_internal_to_input_port(self, comp_id: str) -> dict[str, str]:
        comp = self._comp(comp_id)
        rev: dict[str, str] = {}
        for p in comp.get("input_ports", []):
            name = p.get("port_name") or p.get("name")
            intern = p.get("internal_node") or p.get("target_node")
            if name and intern and intern not in rev:
                rev[intern] = name
        return rev

    def _entry_node(self, comp_id: str) -> str:
        mgr_sm = self._mgr._membership_sms.get(comp_id)
        if mgr_sm and mgr_sm.entry_node:
            return mgr_sm.entry_node
        return self._comp(comp_id).get("entry_node", "")

    def _child_names(self, comp_id: str) -> list[str]:
        mgr_sm = self._mgr._membership_sms.get(comp_id)
        if mgr_sm and mgr_sm.child_node_names:
            return list(mgr_sm.child_node_names)
        return list(self._comp(comp_id).get("nodes", []))

    # ─────────────────────────────────────────────
    # Composite routing → via composite_manager API (real writes)
    # ─────────────────────────────────────────────

    def _set_composite_input_routing(self, comp_id: str, port_name: str, source_output_path: str) -> None:
        if self._composite_mgr is None:
            return
        self._composite_mgr.set_input_routing(comp_id, port_name, source_output_path)

    def _clear_composite_input_routing(self, comp_id: str, port_name: str) -> None:
        if self._composite_mgr is None:
            return
        self._composite_mgr.clear_input_routing(comp_id, port_name)

    def _sync_routing_now(self, comp_id: str) -> None:
        """Force immediate flush: save node_clusters.json + composite.json."""
        if self._composite_mgr is None:
            return
        try:
            save = getattr(self._composite_mgr, "save", None)
            if callable(save):
                save()
        except Exception as e:  # noqa: BLE001
            logger.warning("force save composite manager failed: %s", e)
        try:
            fn = getattr(self._composite_mgr, "_sync_routing_to_config", None)
            if callable(fn):
                fn(comp_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("sync_routing_to_config %s failed: %s", comp_id, e)

    # ─────────────────────────────────────────────
    # RouteCache → real flush (materialize PendingWrites)
    # ─────────────────────────────────────────────

    def begin_transaction(self, tx_owner: str) -> Transaction:
        return Transaction(self._cache, tx_owner)

    def flush_route_cache(self, scope: str | None = None) -> PendingWrites:
        """Extract pending writes and apply them atomically: listen_upper_file → disk, composite_routing → manager."""
        if scope is None:
            pw = self._cache.extract_all_pending()
        else:
            comp_ids = (
                [scope] if scope in (self._mgr._membership_sms and self._mgr.membership_of(scope) or scope) else []
            )
            pw = self._cache.extract_pending(
                comp_ids=comp_ids,
            )
            # If scope is a node name rather than comp_id, flush its listen_upper writes too
            node_paths = [str(p) for p in [self._node_config_path(scope)] if p is not None]
            extra = self._cache.extract_pending(node_cfg_paths=node_paths)
            for k, v in extra.listen_upper_files.items():
                pw.listen_upper_files.setdefault(k, v)
        self._materialize(pw)
        return pw

    def _materialize(self, pw: PendingWrites) -> None:
        # 0) 单文件级缓存：path_str -> cfg dict，避免同一 node_config.json 多次 open/close
        cfg_store: dict[str, dict] = {}

        def _load_cfg(path_str: str) -> dict:
            if path_str in cfg_store:
                return cfg_store[path_str]
            p = Path(path_str)
            if p.exists():
                try:
                    cfg = json.loads(p.read_text(encoding="utf-8")) or {}
                except (json.JSONDecodeError, OSError):
                    cfg = {}
            else:
                cfg = {}
                p.parent.mkdir(parents=True, exist_ok=True)
            cfg_store[path_str] = cfg
            return cfg

        def _flush_cfgs() -> None:
            for path_str, cfg in cfg_store.items():
                p = Path(path_str)
                try:
                    p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
                except OSError as e:
                    logger.warning("[Phase3-materialize] write %s failed (non-fatal): %s", path_str, e)
            cfg_store.clear()

        # 1) listen_upper_file writes
        for path_str, value in (pw.listen_upper_files or {}).items():
            new_value = "" if (value is None or value == "") else value
            cfg = _load_cfg(path_str)
            if cfg.get("listen_upper_file") != new_value:
                cfg["listen_upper_file"] = new_value

        # 2) out_connections writes (source-side port → target|port)
        for path_str, portmap in (pw.out_connections or {}).items():
            if not isinstance(portmap, dict):
                continue
            cfg = _load_cfg(path_str)
            if "__ALL__" in portmap:
                cfg["out_connections"] = {}
            else:
                current = cfg.get("out_connections")
                if not isinstance(current, dict):
                    current = {}
                    cfg["out_connections"] = current
                for port_name, value in portmap.items():
                    if value is None:
                        current.pop(port_name, None)
                    else:
                        current[port_name] = value
                # 如果 out_connections 清空了，移除 key 避免空对象留着
                if not current:
                    cfg.pop("out_connections", None)

        # 3) port_mappings writes (target-side port → upstream output.json)
        for path_str, portmap in (pw.port_mappings or {}).items():
            if not isinstance(portmap, dict):
                continue
            cfg = _load_cfg(path_str)
            if "__ALL__" in portmap:
                cfg.pop("port_mappings", None)
            else:
                current = cfg.get("port_mappings")
                if not isinstance(current, dict):
                    if not portmap:
                        continue
                    current = {}
                    cfg["port_mappings"] = current
                for port_name, value in portmap.items():
                    if value is None:
                        current.pop(port_name, None)
                    else:
                        current[port_name] = value
                if not current:
                    cfg.pop("port_mappings", None)

        # 1~3 都走了 cfg_store，现在一次性把所有被改过的文件落盘
        _flush_cfgs()

        # 4) composite routings → delegate to composite manager API
        for comp_id, routing in (pw.composite_routings or {}).items():
            for direction, ports in routing.items():
                if direction == "input":
                    for port, route in ports.items():
                        if route is None:
                            self._clear_composite_input_routing(comp_id, port)
                        else:
                            src = route.get("source_output_path", "") if isinstance(route, dict) else str(route)
                            self._set_composite_input_routing(comp_id, port, src)
                elif direction == "output":
                    if self._composite_mgr is None:
                        continue
                    for port, route in ports.items():
                        if route is None:
                            self._composite_mgr.clear_output_routing(comp_id, port)
                        elif isinstance(route, dict):
                            self._composite_mgr.set_output_routing(
                                comp_id,
                                port,
                                route.get("target_composite"),
                                route.get("target_node", ""),
                                route.get("target_port", "default"),
                            )
            # Force flush after each comp to ensure no debounce delay
            self._sync_routing_now(comp_id)

    # ─────────────────────────────────────────────
    # Action registry
    # ─────────────────────────────────────────────

    def register_action(self, name: str, fn: ActionFn) -> None:
        self._actions[name] = fn

    def invoke(self, name: str, node_name: str, **kwargs) -> None:
        fn = self._actions.get(name)
        if fn is None:
            logger.debug("unknown action name %r — ignored", name)
            return
        fn(node_name, **kwargs)

    # ─────────────────────────────────────────────
    # 15 default action implementations
    # ─────────────────────────────────────────────

    # ── STANDALONE upstreams ──

    def _action_standalone_connect_upstream(self, node_name: str, **kwargs) -> None:
        src_path = kwargs.get("source_output_path") or ""
        src_node = kwargs.get("upstream_node_name") or _extract_node_from_path(src_path) or ""
        port = kwargs.get("port_name") or "default"
        # write listen_upper_file directly (simple standalone → no route cache detour)
        cfg = self._read_node_config(node_name)
        if cfg.get("listen_upper_file") != src_path:
            cfg["listen_upper_file"] = src_path
            self._write_node_config(node_name, cfg)
        # update ConnectionSM metadata for inspection / state_validator
        cs = self._mgr._connection_sms.get(node_name)
        if cs is not None:
            cs.upstream_port = port
            cs.upstream_node_name = src_node
            cs.upstream_output_path = src_path

    def _action_standalone_disconnect_upstream(self, node_name: str, **kwargs) -> None:  # noqa: ARG002
        cfg = self._read_node_config(node_name)
        if cfg.get("listen_upper_file"):
            cfg["listen_upper_file"] = ""
            self._write_node_config(node_name, cfg)
        cs = self._mgr._connection_sms.get(node_name)
        if cs is not None:
            cs.clear_upstream_meta()

    # ── CHILD visible (expanded) upstreams ──

    def _action_child_visible_connect_upstream(self, node_name: str, **kwargs) -> None:
        src_path = kwargs.get("source_output_path") or ""
        src_node = kwargs.get("upstream_node_name") or _extract_node_from_path(src_path) or ""
        port = kwargs.get("port_name") or "default"

        # Step A: write the child node's listen_upper_file
        cfg = self._read_node_config(node_name)
        if cfg.get("listen_upper_file") != src_path:
            cfg["listen_upper_file"] = src_path
            self._write_node_config(node_name, cfg)

        # Step B: propagate to parent composite's _port_routing
        msm = self._mgr._membership_sms.get(node_name)
        comp_id = msm.comp_id if msm is not None else ""
        if comp_id:
            # map child → external input port
            internal_to_input = self._build_internal_to_input_port(comp_id)
            input_port = port if self._is_external_port(comp_id, port) else internal_to_input.get(node_name, "default")
            # "data" (entry port) is exposed externally as "default"
            if input_port == "data":
                input_port = "default"
            self._cache.set_composite_input_routing(
                comp_id,
                input_port,
                {"source_output_path": src_path},
            )
            # Force immediate persist per spec (immediate_flush rule)
            self._materialize(self._cache.extract_pending(comp_ids=[comp_id]))
            self._sync_routing_now(comp_id)

        cs = self._mgr._connection_sms.get(node_name)
        if cs is not None:
            cs.upstream_port = port
            cs.upstream_node_name = src_node
            cs.upstream_output_path = src_path

    def _is_external_port(self, comp_id: str, port_name: str) -> bool:
        """Return True if port_name is one of the composite's declared input port names."""
        ports = self._comp(comp_id).get("input_ports", [])
        declared = {p.get("port_name") or p.get("name") for p in ports}
        return port_name in declared

    def _action_child_visible_disconnect_upstream(self, node_name: str, **kwargs) -> None:
        port = kwargs.get("port_name") or ""

        # Step A: clear child listen_upper_file
        cfg = self._read_node_config(node_name)
        if cfg.get("listen_upper_file"):
            cfg["listen_upper_file"] = ""
            self._write_node_config(node_name, cfg)

        # Step B: drop parent composite's routing entry
        msm = self._mgr._membership_sms.get(node_name)
        comp_id = msm.comp_id if msm is not None else ""
        if comp_id:
            internal_to_input = self._build_internal_to_input_port(comp_id)
            input_port = port if self._is_external_port(comp_id, port) else internal_to_input.get(node_name, "")
            if not input_port:
                input_port = self._build_internal_to_input_port(comp_id).get(node_name, "")
            # alias: data/default may be used interchangeably
            if not input_port and self._entry_node(comp_id) == node_name:
                input_port = "default"
            if input_port:
                self._cache.set_composite_input_routing(comp_id, input_port, None)
                self._materialize(self._cache.extract_pending(comp_ids=[comp_id]))
                self._sync_routing_now(comp_id)

        cs = self._mgr._connection_sms.get(node_name)
        if cs is not None:
            cs.clear_upstream_meta()

    # ── CHILD hidden (collapsed) upstreams ──

    def _action_child_hidden_connect_upstream(self, node_name: str, **kwargs) -> None:
        src_path = kwargs.get("source_output_path") or ""
        src_node = kwargs.get("upstream_node_name") or _extract_node_from_path(src_path) or ""
        port = kwargs.get("port_name") or "default"
        # Do NOT write child listen_upper_file yet — will be synced on expand
        msm = self._mgr._membership_sms.get(node_name)
        comp_id = msm.comp_id if msm is not None else ""
        if comp_id:
            # Use external port name directly; fallback via mapping
            use_port = (
                port
                if self._is_external_port(comp_id, port)
                else self._build_internal_to_input_port(comp_id).get(node_name, "default")
            )
            if use_port == "data":
                use_port = "default"
            self._cache.set_composite_input_routing(
                comp_id,
                use_port,
                {"source_output_path": src_path},
            )
            self._materialize(self._cache.extract_pending(comp_ids=[comp_id]))
            self._sync_routing_now(comp_id)
        cs = self._mgr._connection_sms.get(node_name)
        if cs is not None:
            cs.upstream_port = port
            cs.upstream_node_name = src_node
            cs.upstream_output_path = src_path

    def _action_child_hidden_disconnect_upstream(self, node_name: str, **kwargs) -> None:
        port = kwargs.get("port_name") or ""
        msm = self._mgr._membership_sms.get(node_name)
        comp_id = msm.comp_id if msm is not None else ""
        if comp_id:
            use_port = (
                port
                if self._is_external_port(comp_id, port)
                else self._build_internal_to_input_port(comp_id).get(node_name, "")
            )
            if not use_port and self._entry_node(comp_id) == node_name:
                use_port = "default"
            if use_port:
                self._cache.set_composite_input_routing(comp_id, use_port, None)
                self._materialize(self._cache.extract_pending(comp_ids=[comp_id]))
                self._sync_routing_now(comp_id)
        cs = self._mgr._connection_sms.get(node_name)
        if cs is not None:
            cs.clear_upstream_meta()

    # ── Expand / Collapse per child ──

    def _action_child_expand_with_connection(self, node_name: str, **kwargs) -> None:  # noqa: ARG002
        """Parent composite is EXPANDING. Sync parent _port_routing → child's listen_upper_file."""
        msm = self._mgr._membership_sms.get(node_name)
        comp_id = msm.comp_id if msm is not None else ""
        if not comp_id:
            return
        p2i = self._build_port_to_internal(comp_id)
        i2p = self._build_internal_to_input_port(comp_id)
        routing = self._composite_mgr._get_port_routing(comp_id) if self._composite_mgr else {}
        input_routes = routing.get("input", {}) if isinstance(routing, dict) else {}

        # For this specific child, find all input ports that route to it
        target_port_in_parent = i2p.get(node_name, "")
        # If the child is the entry node, include "data" → "default" alias too
        if self._entry_node(comp_id) == node_name and not target_port_in_parent:
            target_port_in_parent = "default"

        src_path = ""
        for pname, route in input_routes.items():
            matched = False
            if target_port_in_parent and pname == target_port_in_parent:
                matched = True
            elif pname in _MAIN_PORT_ALIASES and self._entry_node(comp_id) == node_name:
                matched = True
            else:
                if p2i.get(pname) == node_name:
                    matched = True
            if matched and isinstance(route, dict):
                src_path = route.get("source_output_path", "")
                break
        # Write to child's listen_upper_file
        if src_path:
            cfg = self._read_node_config(node_name)
            if cfg.get("listen_upper_file") != src_path:
                cfg["listen_upper_file"] = src_path
                self._write_node_config(node_name, cfg)
            # keep connection_sm in sync
            cs = self._mgr._connection_sms.get(node_name)
            if cs is not None:
                cs.upstream_port = target_port_in_parent or "default"
                cs.upstream_node_name = _extract_node_from_path(src_path) or ""
                cs.upstream_output_path = src_path

    def _action_child_collapse_with_connection(self, node_name: str, **kwargs) -> None:  # noqa: ARG002
        """Parent composite is COLLAPSING. child.listen_upper_file → parent _port_routing, then clear child."""
        cfg = self._read_node_config(node_name)
        listen = cfg.get("listen_upper_file", "") or ""
        msm = self._mgr._membership_sms.get(node_name)
        comp_id = msm.comp_id if msm is not None else ""
        if not comp_id or not listen:
            return
        # Only external listen paths matter — if it points to an internal sibling, leave as-is (internal connection)
        child_set = set(self._child_names(comp_id))
        if not _is_relative_external(listen, child_set):
            # It's an internal upstream, just keep in listen, don't propagate
            return
        i2p = self._build_internal_to_input_port(comp_id)
        port_name = i2p.get(node_name, "")
        if not port_name and self._entry_node(comp_id) == node_name:
            port_name = "default"
        # entry node main port alias: internal port "data" → external "default"
        use_port = "default" if port_name == "data" else (port_name or "default")
        self._cache.set_composite_input_routing(
            comp_id,
            use_port,
            {"source_output_path": listen},
        )
        # Materialize + sync composite.json
        self._materialize(self._cache.extract_pending(comp_ids=[comp_id]))
        self._sync_routing_now(comp_id)
        # Clear child listen_upper_file per collapse spec (prevents stale leftover + double-source on re-expand)
        cfg["listen_upper_file"] = ""
        self._write_node_config(node_name, cfg)

    def _action_child_collapse_no_connection(self, node_name: str, **kwargs) -> None:  # noqa: ARG002
        """Just ensure visibility state applies; no-op for configs."""
        return None

    def _action_child_expand_no_connection(self, node_name: str, **kwargs) -> None:  # noqa: ARG002
        return None

    # ── Composite batch expand / collapse ──

    def _action_composite_expand_batch(self, comp_id: str, **kwargs) -> None:  # noqa: ARG002
        """Iterate children; for each dispatch per-child actions based on state."""
        child_names = self._child_names(comp_id)
        # 1. Switch child visibility state (apply events, triggers visibility SM transitions)
        for child in child_names:
            if not self._mgr.is_registered(child):
                continue
            vs = self._mgr.visibility_of(child)
            if vs == "hidden_collapsed":
                evt = "expand"
                # Invoke the child-level action directly (state switch already done by caller for composite, but children are not auto-transitioned because the manager handle_event is per-node).
                # Instead we re-dispatch through the manager so audit + signals fire per child.
                self._mgr.handle_event(child, evt)
        # RouteCache commit scope: per-child actions queued writes into the same transaction buffer that manager opened for us → flush at the end
        self.flush_route_cache(comp_id)

    def _action_composite_collapse_batch(self, comp_id: str, **kwargs) -> None:  # noqa: ARG002
        child_names = self._child_names(comp_id)
        for child in child_names:
            if not self._mgr.is_registered(child):
                continue
            vs = self._mgr.visibility_of(child)
            if vs == "visible":
                self._mgr.handle_event(child, "collapse")
        self.flush_route_cache(comp_id)

    # ── Compress / Decompress ──

    def _action_compress_into_composite(self, node_name: str, **kwargs) -> None:
        """STANDALONE → COMPOSITE_CHILD after "compress into composite".

        Keep listen_upper_file in node config for the moment — it will be migrated to
        the parent composite's _port_routing only on first collapse, keeping UI
        connection lines intact during expanded mode.
        """
        # Nothing mandatory here. Could optionally pre-populate comp routing immediately.
        return None

    def _action_decompress_preserve_connection(self, node_name: str, **kwargs) -> None:  # noqa: ARG002
        """COMPOSITE_CHILD → STANDALONE. If the composite has an upstream routing entry for this child, migrate it to listen_upper_file."""
        msm = self._mgr._membership_sms.get(node_name)
        comp_id = msm.comp_id if msm is not None else ""
        if not comp_id:
            return
        i2p = self._build_internal_to_input_port(comp_id)
        routing = self._composite_mgr._get_port_routing(comp_id) if self._composite_mgr else {}
        input_routes = routing.get("input", {}) if isinstance(routing, dict) else {}
        # Find routing entry bound to this child → adopt its source_output_path
        src_path = ""
        pname_used = ""
        p2i = self._build_port_to_internal(comp_id)
        # candidate port names
        candidates = [i2p.get(node_name, "")]
        if self._entry_node(comp_id) == node_name:
            candidates.extend(["default", "data"])
        for pname in [p for p in candidates if p]:
            if pname in input_routes:
                r = input_routes[pname]
                if isinstance(r, dict):
                    src_path = r.get("source_output_path", "")
                    pname_used = pname
                    break
        if not src_path:
            # fall back scan
            for pname, r in input_routes.items():
                if isinstance(r, dict) and p2i.get(pname) == node_name:
                    src_path = r.get("source_output_path", "")
                    pname_used = pname
                    break
        if src_path:
            cfg = self._read_node_config(node_name)
            if cfg.get("listen_upper_file") != src_path:
                cfg["listen_upper_file"] = src_path
                self._write_node_config(node_name, cfg)
            # Clear parent composite routing entry (child is now standalone owning the upstream)
            if pname_used:
                self._cache.set_composite_input_routing(comp_id, pname_used, None)
                # Alias cleanup for entry node
                if self._entry_node(comp_id) == node_name:
                    for alias in _MAIN_PORT_ALIASES:
                        if alias in input_routes:
                            self._cache.set_composite_input_routing(comp_id, alias, None)
                self._materialize(self._cache.extract_pending(comp_ids=[comp_id]))
                self._sync_routing_now(comp_id)
        cs = self._mgr._connection_sms.get(node_name)
        if cs is not None and src_path:
            cs.upstream_port = i2p.get(node_name, "default")
            cs.upstream_node_name = _extract_node_from_path(src_path) or ""
            cs.upstream_output_path = src_path
        # Also: ensure child visibility becomes VISIBLE after decompress — the
        # membership transition is handled by manager already.

    def _action_composite_switch_entry(self, comp_id: str, **kwargs) -> None:
        """Set new entry node name → persist in composites data + MembershipSM.entry_node."""
        new_entry = kwargs.get("new_entry", "") or kwargs.get("entry_node", "")
        if not new_entry:
            raise ValueError("action_composite_switch_entry requires new_entry kwarg")
        msm = self._mgr._membership_sms.get(comp_id)
        if msm is not None:
            msm.entry_node = new_entry
        if self._composite_mgr is not None:
            comp = self._composite_mgr._composites.get(comp_id)
            if comp is not None:
                comp["entry_node"] = new_entry
                # Rebuild input_ports inheritance from new entry node config
                rebuilder = getattr(self._composite_mgr, "_rebuild_input_ports_for_entry", None)
                if callable(rebuilder):
                    rebuilder(comp_id, new_entry)
            try:
                save = getattr(self._composite_mgr, "save", None)
                if callable(save):
                    save()
            except Exception as e:  # noqa: BLE001
                logger.warning("save after switch_entry failed: %s", e)

    # ─────────────────────────────────────────────

    def _register_default_actions(self) -> None:
        mapping = {
            "action_standalone_connect_upstream": self._action_standalone_connect_upstream,
            "action_standalone_disconnect_upstream": self._action_standalone_disconnect_upstream,
            "action_child_visible_connect_upstream": self._action_child_visible_connect_upstream,
            "action_child_visible_disconnect_upstream": self._action_child_visible_disconnect_upstream,
            "action_child_hidden_connect_upstream": self._action_child_hidden_connect_upstream,
            "action_child_hidden_disconnect_upstream": self._action_child_hidden_disconnect_upstream,
            "action_child_expand_with_connection": self._action_child_expand_with_connection,
            "action_child_collapse_with_connection": self._action_child_collapse_with_connection,
            "action_child_collapse_no_connection": self._action_child_collapse_no_connection,
            "action_child_expand_no_connection": self._action_child_expand_no_connection,
            "action_composite_expand_batch": self._action_composite_expand_batch,
            "action_composite_collapse_batch": self._action_composite_collapse_batch,
            "action_compress_into_composite": self._action_compress_into_composite,
            "action_decompress_preserve_connection": self._action_decompress_preserve_connection,
            "action_composite_switch_entry": self._action_composite_switch_entry,
        }
        for name, fn in mapping.items():
            self.register_action(name, fn)
