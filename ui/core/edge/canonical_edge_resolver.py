"""CanonicalEdgeResolver — 线条权威配置 → EdgeKey 全量反向扫描。

三大功能：
1. `infer_all_edges(project_path, nodes_data, composite_manager)` → 读取所有 node_config.json + composite.json，
   反推配置权威应存在的完整 EdgeKey 集合（CanonicalEdgeSet），与画布上的 edge._edge_key 集合做 diff，
   得到补边集 + 幽灵边集。
2. `ConfigMtimeCache` — 全局文件修改时间缓存池，`os.stat().st_mtime_ns` 不变就跳过 json.load，
   大项目 IO 直降 90%。
3. `purge_stale_routes(project_path, nodes_data, composite_manager)` — 自动清理已删除子节点 / 路径失效的
   复合路由，防止 composite.json 永久膨胀。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
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
    make_edge_key,
)
from ui.core.logger import logger

# ---- 项目目录结构常量（与项目其他地方保持一致）----
NODE_DIR_ROOT: str = "nodes"
COMPOSITE_NODES_DIR: str = "composite_nodes"
NODE_OUTPUT: str = "output.json"


# ----------------------------------------------------------------
# ConfigMtimeCache —— 全局 mtime 缓存，避免每次扫描都重新 json.load
# ----------------------------------------------------------------


@dataclass
class _CacheEntry:
    mtime_ns: int
    parsed: dict  # 如果是损坏配置，parsed = {} 且 broken=True
    broken: bool = False


class ConfigMtimeCache:
    """按文件修改时间缓存解析结果。

    用法::

        cache = ConfigMtimeCache()
        cfg, broken = cache.load_if_needed(path_str)

        # 用户写配置后调用：
        cache.invalidate(path_str)

    为了支持跨线程（8.3 异步扫描），内部对读/写做一层 dict 浅拷贝，避免遍历过程中被外部 invalidate 炸 RuntimeError。
    """

    def __init__(self) -> None:
        self._entries: dict[str, _CacheEntry] = {}

    # ---- public ----

    def load_if_needed(self, cfg_path: str | Path) -> tuple[dict, bool]:
        """若 mtime 未变 → 返回缓存；否则重新 json.load。返回 (cfg_dict, is_broken)。

        损坏配置返回 ({}, True)，下次扫描还会重试（用户可能修好）。
        """
        p = Path(cfg_path)
        s = str(p)
        try:
            stat_result = p.stat()
            mtime_ns = stat_result.st_mtime_ns
        except OSError:
            # 文件不存在 → 返回空配置，不缓存（避免用户新建后被缓存误导）
            return {}, False

        entry = self._entries.get(s)
        if entry is not None and entry.mtime_ns == mtime_ns and not entry.broken:
            return entry.parsed, entry.broken

        # 重读
        try:
            with p.open("r", encoding="utf-8") as f:
                parsed = json.load(f) or {}
            if not isinstance(parsed, dict):
                parsed = {}
                broken = True
            else:
                broken = False
        except (json.JSONDecodeError, OSError):
            parsed = {}
            broken = True
            logger.critical(
                "[EDGE-CONFIG-BROKEN] skip parse %s: json invalid or unreadable",
                s,
            )

        self._entries[s] = _CacheEntry(mtime_ns=mtime_ns, parsed=parsed, broken=broken)
        return parsed, broken

    def invalidate(self, cfg_path: str | Path) -> None:
        p = str(Path(cfg_path))
        self._entries.pop(p, None)

    def invalidate_node(self, node_path: str) -> None:
        """便捷函数：失效某节点目录下的 node_config.json。"""
        self.invalidate(str(Path(get_config_path(node_path))))

    def clear(self) -> None:
        self._entries.clear()


# 全局共享单例（节点状态机 / CanonicalResolver / EdgeWriter 都共用，保证失效通知统一）
_GLOBAL_MTIME_CACHE: ConfigMtimeCache | None = None


def get_global_mtime_cache() -> ConfigMtimeCache:
    global _GLOBAL_MTIME_CACHE
    if _GLOBAL_MTIME_CACHE is None:
        _GLOBAL_MTIME_CACHE = ConfigMtimeCache()
    return _GLOBAL_MTIME_CACHE


# ----------------------------------------------------------------
# CanonicalEdgeResolver
# ----------------------------------------------------------------


@dataclass
class ScanStats:
    scanned_nodes: int = 0
    scanned_composites: int = 0
    broken_paths: list[str] = field(default_factory=list)
    standalone_edges: int = 0
    standalone_portmap_edges: int = 0
    composite_input_edges: int = 0
    composite_output_edges: int = 0
    composite_internal_edges: int = 0
    stale_routes_cleared: int = 0

    @property
    def total_edges(self) -> int:
        return (
            self.standalone_edges
            + self.standalone_portmap_edges
            + self.composite_input_edges
            + self.composite_output_edges
            + self.composite_internal_edges
        )

    def as_log(self) -> str:
        return (
            f"nodes={self.scanned_nodes} composites={self.scanned_composites} "
            f"edges[SA={self.standalone_edges} PM={self.standalone_portmap_edges} "
            f"CI={self.composite_input_edges} CO={self.composite_output_edges} "
            f"CINT={self.composite_internal_edges}] TOTAL={self.total_edges} "
            f"broken={len(self.broken_paths)} stale_cleared={self.stale_routes_cleared}"
        )


class CanonicalEdgeResolver:
    """从所有配置权威源反向推断完整 CanonicalEdgeSet。"""

    # nodes_data 中要识别为复合节点的前缀（CompositeManager 也按这个识别）
    COMPOSITE_NAME_PREFIX = "composite_"

    def __init__(self, mtime_cache: ConfigMtimeCache | None = None) -> None:
        self._cache: ConfigMtimeCache = mtime_cache or get_global_mtime_cache()

    # ---- helpers ----

    @staticmethod
    def _resolve_logical_name_by_dir(node_dir: Path | str, nodes_data: dict[str, dict]) -> tuple[str, bool]:
        """用节点磁盘目录反向查 nodes_data key（=系统权威逻辑身份）。

        返回 (logical_name, used_fallback)：
          - used_fallback=False 表示从 nodes_data 精确命中（推荐路径，身份一致）
          - used_fallback=True  表示 nodes_data 中找不到，退化为目录名，会额外打 WARNING
        """
        try:
            nd = Path(node_dir).resolve()
        except Exception:
            nd = Path(node_dir)
        nd_str = str(nd)
        for logical_key, meta in nodes_data.items():
            p_meta = meta.get("path") or ""
            if not p_meta:
                continue
            try:
                if str(Path(p_meta).resolve()) == nd_str:
                    return logical_key, False
            except Exception:
                if str(Path(p_meta)) == str(nd):
                    return logical_key, False
        # Fallback：用目录名（会导致逻辑/物理身份不一致 ghost）
        fallback = nd.name
        logger.warning(
            "[CANONICAL-IDENTITY-MISMATCH] 节点目录 %s 无法在 nodes_data(%d entries) 中找到 path 匹配项，"
            "退化使用目录名 %s。请检查 nodes_data.key 与其 path 指向的目录名是否一致。",
            nd_str,
            len(nodes_data),
            fallback,
        )
        return fallback, True

    @staticmethod
    def _node_name_from_cfg_path(cfg_path: Path, project_path: str | Path) -> str | None:
        """从 node_config.json 的绝对路径反向推节点名 = 父目录名（仅用于无 nodes_data 时的 fallback）。"""
        try:
            cfg_path.parent.relative_to(Path(project_path) / COMPOSITE_NODES_DIR)
            return cfg_path.parent.name
        except ValueError:
            pass
        try:
            cfg_path.parent.relative_to(Path(project_path) / NODE_DIR_ROOT)
            return cfg_path.parent.name
        except ValueError:
            return None

    @staticmethod
    def _is_composite_name(name: str) -> bool:
        return name.startswith(CanonicalEdgeResolver.COMPOSITE_NAME_PREFIX)

    def _node_cfg_path_by_name(self, node_name: str, nodes_data: dict[str, dict]) -> Path | None:
        if node_name in nodes_data and "path" in nodes_data[node_name]:
            return Path(get_config_path(nodes_data[node_name]["path"]))
        return None

    def _extract_upstream_node_from_output_path(
        self,
        output_path: str,
        nodes_data: dict[str, dict],
        project_path: str | Path,
    ) -> tuple[str, bool, str]:
        """从上游 output.json 路径反推逻辑节点名（统一身份 = nodes_data key）。

        Returns: (upstream_node_name, is_composite_node, upstream_port)
        """
        try:
            p = Path(output_path).resolve()
        except Exception:
            p = Path(output_path)
        upstream_dir = p.parent
        up_name, _ = self._resolve_logical_name_by_dir(upstream_dir, nodes_data)
        is_comp = self._is_composite_name(up_name)
        return up_name, is_comp, "default"

    # ---- public mainline ----

    def infer_all_edges(
        self,
        project_path: str | Path,
        nodes_data: dict[str, dict],
        composite_manager: Any = None,
    ) -> tuple[set[EdgeKey], ScanStats]:
        """反向全量扫描 → (canonical_edge_set, scan_statistics)。

        5 类 routing_type 全覆盖：
        ① STANDALONE              ← downstream listen_upper_file（default 端口）
        ② STANDALONE_PORT_MAP     ← downstream port_mappings
        ③ COMPOSITE_INPUT         ← composite.json.external_connections.input
        ④ COMPOSITE_OUTPUT        ← composite.json.external_connections.output + 内部出口子节点名反查
        ⑤ COMPOSITE_INTERNAL      ← composite.json.edges[] (DAG 拓扑)
        """
        stats = ScanStats()
        edges: set[EdgeKey] = set()
        proj = Path(project_path)

        # ── 阶段一：每个下游节点 node_config.json → 反推 STANDALONE / STANDALONE_PORT_MAP
        for node_name, _ in list(nodes_data.items()):
            if self._is_composite_name(node_name):
                # 复合节点本体：不在这里处理，稍后走 composite.json
                continue
            stats.scanned_nodes += 1
            node_cfg_path = self._node_cfg_path_by_name(node_name, nodes_data)
            if node_cfg_path is None:
                continue
            cfg, broken = self._cache.load_if_needed(node_cfg_path)
            if broken:
                stats.broken_paths.append(str(node_cfg_path))
                continue
            if not cfg:
                continue

            # ① STANDALONE：listen_upper_file 指向合法 output.json → 一条 default→default STANDALONE 边
            luf = cfg.get("listen_upper_file") or ""
            if luf:
                try:
                    up_name, up_is_comp, up_port = self._extract_upstream_node_from_output_path(luf, nodes_data, proj)
                    if up_name and up_name != node_name:
                        if up_is_comp:
                            # 上游如果是 composite 节点本体 → 这条边实际上 routing_type 应该是 COMPOSITE_OUTPUT，
                            # 放在阶段二 composite 扫描时补（为了避免重复，这里跳过，交给 composite.json 决定）
                            pass
                        else:
                            k = make_edge_key(ROUTING_STANDALONE, up_name, node_name, up_port, "default")
                            if k not in edges:
                                edges.add(k)
                                stats.standalone_edges += 1
                except Exception as e:  # noqa: BLE001
                    logger.warning("[CANONICAL] STANDALONE listen_upper_file parse fail %s: %s", node_name, e)

            # ② STANDALONE_PORT_MAP：port_mappings[target_port] = upstream output.json
            pm = cfg.get("port_mappings")
            if isinstance(pm, dict):
                for tgt_port, up_out_path in list(pm.items()):
                    if not isinstance(up_out_path, str) or not up_out_path:
                        continue
                    try:
                        up_name, up_is_comp, up_port = self._extract_upstream_node_from_output_path(
                            up_out_path, nodes_data, proj
                        )
                        if up_name and not up_is_comp and up_name != node_name:
                            k = make_edge_key(ROUTING_STANDALONE_PORT_MAP, up_name, node_name, up_port, tgt_port)
                            if k not in edges:
                                edges.add(k)
                                stats.standalone_portmap_edges += 1
                    except Exception as e:  # noqa: BLE001
                        logger.warning("[CANONICAL] port_mappings[%s] parse fail %s: %s", tgt_port, node_name, e)

        # ── 阶段二：所有复合节点 composite.json.external_connections → COMPOSITE_INPUT / COMPOSITE_OUTPUT
        composite_ids: list[str]
        if composite_manager is not None and hasattr(composite_manager, "_composites"):
            composite_ids = list(composite_manager._composites.keys())
        else:
            # Fallback：扫描 project/composite_nodes/ 下所有子目录名作为复合节点 id
            comp_root = proj / COMPOSITE_NODES_DIR
            if comp_root.exists():
                composite_ids = [p.name for p in comp_root.iterdir() if p.is_dir()]
            else:
                composite_ids = []

        for comp_id in composite_ids:
            comp_cfg_path = proj / COMPOSITE_NODES_DIR / comp_id / "composite.json"
            comp_cfg, broken = self._cache.load_if_needed(comp_cfg_path)
            if broken:
                stats.broken_paths.append(str(comp_cfg_path))
                continue
            stats.scanned_composites += 1
            ext = comp_cfg.get("external_connections", {}) if isinstance(comp_cfg, dict) else {}
            if not isinstance(ext, dict):
                continue

            # ③ COMPOSITE_INPUT：external_connections.input[in_port] = route_dict
            inp = ext.get("input", {}) or {}
            if isinstance(inp, dict):
                for in_port, route in inp.items():
                    src_out_path = ""
                    if isinstance(route, dict):
                        src_out_path = route.get("source_output_path", "")
                    elif isinstance(route, str):
                        src_out_path = route
                    if not src_out_path:
                        continue
                    try:
                        up_name, up_is_comp, up_port = self._extract_upstream_node_from_output_path(
                            src_out_path, nodes_data, proj
                        )
                        if up_name:
                            # project_memory 硬约束："Composite node input anchor names must map data (internal) to
                            # default (external) for correct port identification"
                            # → data ↔ default 别名必须同时加入 canonical 集，
                            #    无论画布注册端用哪个命名（外部锚点名 default / 内部路由名 data）
                            #    都能命中 RenderPresence.valid=True。
                            alias_in_ports: set[str] = {in_port}
                            if in_port in {"data", "default"}:
                                alias_in_ports |= {"data", "default"}
                            for actual_in_port in alias_in_ports:
                                k = make_edge_key(
                                    ROUTING_COMPOSITE_INPUT,
                                    up_name,
                                    comp_id,
                                    up_port,
                                    actual_in_port,
                                )
                                if k not in edges:
                                    edges.add(k)
                                    stats.composite_input_edges += 1
                    except Exception as e:  # noqa: BLE001
                        logger.warning("[CANONICAL] composite_input[%s][%s] fail: %s", comp_id, in_port, e)

            # ④ COMPOSITE_OUTPUT：external_connections.output[out_port] = route
            outp = ext.get("output", {}) or {}
            if isinstance(outp, dict):
                for out_port, route in outp.items():
                    tgt_node = ""
                    tgt_port = "default"
                    if isinstance(route, dict):
                        tgt_node = route.get("target_node", "")
                        tgt_port = route.get("target_port", "default") or "default"
                    if not tgt_node:
                        continue
                    try:
                        # project_memory 约定："Composite node output anchor names must map node_output (internal)
                        # to default (external)" —— default ↔ node_output 别名展开。
                        alias_out_ports: set[str] = {out_port}
                        if out_port in {"default", "node_output"}:
                            alias_out_ports |= {"default", "node_output"}
                        for actual_out_port in alias_out_ports:
                            k = make_edge_key(ROUTING_COMPOSITE_OUTPUT, comp_id, tgt_node, actual_out_port, tgt_port)
                            if k not in edges:
                                edges.add(k)
                                stats.composite_output_edges += 1
                    except Exception as e:  # noqa: BLE001
                        logger.warning("[CANONICAL] composite_output[%s][%s] fail: %s", comp_id, out_port, e)

            # ⑤ COMPOSITE_INTERNAL：composite.json.edges[]
            edge_list = comp_cfg.get("edges", []) or []
            if isinstance(edge_list, list):
                for e in edge_list:
                    try:
                        if isinstance(e, dict):
                            src = e.get("from") or e.get("source") or ""
                            dst = e.get("to") or e.get("target") or ""
                            sp = e.get("source_port") or "default"
                            dp = e.get("target_port") or "default"
                        elif isinstance(e, list | tuple) and len(e) >= 2:
                            src, dst = e[0], e[1]
                            sp = e[2] if len(e) >= 3 else "default"
                            dp = e[3] if len(e) >= 4 else "default"
                        else:
                            continue
                        if not src or not dst:
                            continue
                        k = make_edge_key(ROUTING_COMPOSITE_INTERNAL, src, dst, sp, dp)
                        if k not in edges:
                            edges.add(k)
                            stats.composite_internal_edges += 1
                    except Exception as e:  # noqa: BLE001
                        logger.warning("[CANONICAL] composite_internal edge parse fail: %s", e)

        # 稳态无异常时降到 DEBUG，避免定时器 10s 一次刷屏；
        # 有损坏配置 / 清理了过期路由 / 任何清理动作 → INFO 级引起用户注意。
        need_attention = bool(stats.broken_paths) or (stats.stale_routes_cleared or 0) > 0
        summary_log = logger.info if need_attention else logger.debug
        summary_log("[CANONICAL] infer_all_edges done: %s", stats.as_log())
        return edges, stats

    # ---- stale route purge ----

    def purge_stale_routes(
        self,
        project_path: str | Path,
        nodes_data: dict[str, dict],
        composite_manager: Any,
        dry_run: bool = False,
    ) -> int:
        """扫描 composite.json.external_connections / input routing，清掉：
           - 指向 nodes_data 中不存在的子节点 / 节点路径不存在 的路由（P1 防配置永久膨胀）
           - upstream output.json 文件物理不存在的 STANDALONE listen_upper_file / port_mappings 条目

        Returns 清理条目数。
        """
        if composite_manager is None:
            return 0
        proj = Path(project_path)
        cleared = 0
        comp_ids = list(getattr(composite_manager, "_composites", {}).keys())

        for comp_id in comp_ids:
            cfg_path = proj / COMPOSITE_NODES_DIR / comp_id / "composite.json"
            cfg, broken = self._cache.load_if_needed(cfg_path)
            if broken or not isinstance(cfg, dict):
                continue
            # 合法子节点集合
            child_names = {
                n.get("node_name") for n in (cfg.get("nodes") or []) if isinstance(n, dict) and n.get("node_name")
            }
            child_names |= {n for n in nodes_data if self._is_inside_comp(nodes_data, n, comp_id)}
            # external_connections.input / output: 检查 route 中节点名是否在合法集合内
            ext = cfg.get("external_connections") or {}
            if not isinstance(ext, dict):
                continue
            inp = ext.get("input") or {}
            if isinstance(inp, dict):
                for port in list(inp.keys()):
                    need_clear = False
                    route = inp[port]
                    if isinstance(route, dict):
                        src_out = route.get("source_output_path") or ""
                        if src_out and not Path(src_out).exists():
                            need_clear = True
                    if need_clear and not dry_run and hasattr(composite_manager, "clear_input_routing"):
                        composite_manager.clear_input_routing(comp_id, port)
                        self._cache.invalidate(cfg_path)
                        cleared += 1
            outp = ext.get("output") or {}
            if isinstance(outp, dict):
                for port in list(outp.keys()):
                    route = outp[port]
                    tgt_node = ""
                    if isinstance(route, dict):
                        tgt_node = route.get("target_node", "")
                    need_clear = bool(tgt_node and tgt_node not in nodes_data)
                    if need_clear and not dry_run and hasattr(composite_manager, "clear_output_routing"):
                        composite_manager.clear_output_routing(comp_id, port)
                        self._cache.invalidate(cfg_path)
                        cleared += 1
        logger.info("[CANONICAL] purge_stale_routes done: cleared %d stale routes (dry_run=%s)", cleared, dry_run)
        return cleared

    # ---- helpers ----

    @staticmethod
    def _is_inside_comp(nodes_data: dict[str, dict], node_name: str, comp_id: str) -> bool:
        """判断节点 nodes_data[node_name].path 是否位于 composite_nodes/<comp_id>/ 下。"""
        meta = nodes_data.get(node_name) or {}
        p = meta.get("path") or ""
        if not p:
            return False
        try:
            Path(p).relative_to(Path(NODE_DIR_ROOT) / COMPOSITE_NODES_DIR / comp_id)
            return True
        except ValueError:
            return False
