"""配置写盘内存缓冲与事务机制。

批量操作（expand/collapse）先写入 RouteCache，成功后一次性 flush 落盘，
中途异常则通过 Transaction 快照回滚，保证事务一致性。

零业务依赖，可独立单元测试。
"""

from __future__ import annotations

import copy
import json
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

# ── 内部哨兵 & 小工具 ────────────────────────────────────────────────


class _UNSET_SENTINEL:
    pass


_UNSET = _UNSET_SENTINEL()


def _guess_composite_json_path(comp_id: str) -> Path | None:
    """通过环境变量 + 当前工作目录搜索 composite_${comp_id}.json。

    查找优先级：
      1. 环境变量 BNOS_PROJECT_ROOT / composite_nodes / {comp_id}.json
      2. 每个父进程 cwd（最近一次 BNOS 启动目录）下的 composite_nodes
      3. 递归遍历 3 层以内的 composite_nodes 子目录（避免大项目 IO 过大）

    没找到返回 None，外层会 fallback 到 CompositeManager._write_composite_config。
    """
    candidates: list[Path] = []
    # 1) BNOS_PROJECT_ROOT
    pr = os.environ.get("BNOS_PROJECT_ROOT") or os.environ.get("PROJECT_PATH")
    if pr:
        candidates.append(Path(pr) / "composite_nodes" / f"{comp_id}.json")
    # 2) 当前工作目录
    try:
        cwd = Path.cwd()
        candidates.append(cwd / "composite_nodes" / f"{comp_id}.json")
        # 2.1) cwd 上层可能是项目目录（如果 cwd 是 ui/ 等子目录）
        for up in range(3):
            parent = cwd.parents[up] if up < len(cwd.parents) else None
            if parent is None:
                break
            candidates.append(parent / "composite_nodes" / f"{comp_id}.json")
    except Exception:
        pass
    # 3) 最近一次 CompositeManager 使用过的 project_path（全局注册表）
    try:
        from ui.core.node.composite_node import _LAST_SEEN_PROJECT_PATH  # noqa: WPS433

        if _LAST_SEEN_PROJECT_PATH:
            candidates.append(Path(_LAST_SEEN_PROJECT_PATH) / "composite_nodes" / f"{comp_id}.json")
    except Exception:
        pass

    # 过滤去重并返回第一个存在的文件
    seen: set[str] = set()
    for c in candidates:
        try:
            key = str(c.resolve())
        except Exception:
            key = str(c)
        if key in seen:
            continue
        seen.add(key)
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


# 跨模块 logger 懒加载（避免循环 import）
def _get_logger():
    try:
        from ui.core.logger import logger  # noqa: WPS433

        return logger
    except Exception:
        import logging  # noqa: WPS433

        return logging.getLogger("route_cache")


logger = _get_logger()


@dataclass
class PendingWrites:
    """单次 flush 需要写盘的内容集合。

    Attributes:
        listen_upper_files:  { node_config.json 绝对路径 : 新 listen_upper_file 值 }
                              值为 "" 或 None 表示清除该字段。
        out_connections:     { node_config.json 绝对路径 : { source_port_name : value 或 None } }
                              None 表示删除该 port 条目；特殊 key "__ALL__" 表示重置整个 out_connections={}。
        port_mappings:       { node_config.json 绝对路径 : { target_port_name : value 或 None } }
                              None 表示删除该 port 条目；特殊 key "__ALL__" 表示重置整个 port_mappings={}。
        composite_routings:  { comp_id : {"input": {port: route_dict or None}, "output": {port: route_dict or None}} }
                              route_dict=None 表示 clear 该端口；每次 set/clear 都对整体 routing patch。
    """

    listen_upper_files: dict[str, str] = field(default_factory=dict)
    out_connections: dict[str, dict[str, str | None]] = field(default_factory=dict)
    port_mappings: dict[str, dict[str, str | None]] = field(default_factory=dict)
    composite_routings: dict[str, dict] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return (
            not self.listen_upper_files
            and not self.out_connections
            and not self.port_mappings
            and not self.composite_routings
        )


class RouteCache:
    """配置写盘内存缓冲。

    提供 listen_upper_file / composite_routing 的 set/clear 接口；
    extract_pending(tx_owner) 提取指定节点/复合的待写集合用于落盘。

    全局单例 + 快照栈接口（begin / flush / rollback）：供 Phase4.1 morph 三阶段分离
    「阶段B全删 + 阶段C全建」放在同一个事务内，要么全成功要么全回滚。
    """

    # ── 全局单例 + 快照栈 ──────────────────────────────────────────────

    _instance: RouteCache | None = None
    _snapshot_stack: list[dict] = []

    @classmethod
    def instance(cls) -> RouteCache:
        """获取（懒创建）全局唯一 RouteCache 实例。"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def begin(cls) -> None:
        """Phase4.1 morph 事务入口：压入当前全局缓存快照。"""
        cache = cls.instance()
        cls._snapshot_stack.append(cache.snapshot())
        logger.debug("[ROUTE-CACHE-BEGIN] depth=%d", len(cls._snapshot_stack))

    @classmethod
    def flush(cls) -> int:
        """Phase4.1 morph 事务出口：弹出快照栈，提取待写并真实落盘。

        Returns:
            成功写入的独立配置文件数量（node_config.json + composite.json 合计）。
        """
        cache = cls.instance()
        if cls._snapshot_stack:
            cls._snapshot_stack.pop()
        pw = cache.extract_all_pending()
        written = cls._write_pending_to_disk(pw)
        logger.info(
            "[ROUTE-CACHE-FLUSH] depth=%d written_files=%d (listen=%d, out_conn=%d, port_map=%d, comp=%d)",
            len(cls._snapshot_stack),
            written,
            len(pw.listen_upper_files),
            len(pw.out_connections),
            len(pw.port_mappings),
            len(pw.composite_routings),
        )
        return written

    @classmethod
    def rollback(cls) -> None:
        """Phase4.1 morph 互斥断言失败 → 恢复快照，丢弃所有待写变更。"""
        cache = cls.instance()
        if cls._snapshot_stack:
            snap = cls._snapshot_stack.pop()
            cache.restore(snap)
            logger.warning("[ROUTE-CACHE-ROLLBACK] depth=%d", len(cls._snapshot_stack))
        else:
            # 没快照，兜底清空缓存（防止泄漏脏写）
            cache.clear()
            logger.warning("[ROUTE-CACHE-ROLLBACK] no snapshot, clear all as fallback")

    @classmethod
    def _write_pending_to_disk(cls, pw: PendingWrites) -> int:
        """把 PendingWrites 逐个写入磁盘；失败时 log 但不抛（写盘幂等）。

        写策略：
          - listen_upper_files[cfg_path] = val → 读 cfg_path，写入/清空 listen_upper_file。
          - out_connections[cfg_path] = {port: val|None} → 合并/删除对应 port 键。
          - port_mappings[cfg_path] = {port: val|None} → 合并/删除对应 port 键。
          - composite_routings[comp_id] = {input:{port:r|None}, output:{port:r|None}} →
            写 composite.json 的 external_connections（按 comp_id 拼路径）。
        """
        written_files: set[str] = set()
        # ---- 1. 先按 cfg_path 聚合 node_config.json 的 3 类修改 ----
        node_paths: set[str] = set()
        node_paths.update(pw.listen_upper_files.keys())
        node_paths.update(pw.out_connections.keys())
        node_paths.update(pw.port_mappings.keys())

        for node_cfg_path in node_paths:
            p = Path(node_cfg_path)
            existing: dict = {}
            try:
                if p.is_file():
                    with p.open(encoding="utf-8") as f:
                        existing = json.load(f) or {}
            except (OSError, json.JSONDecodeError) as e:
                logger.error("[ROUTE-CACHE-FLUSH] cannot read %s: %s", p, e)
                continue
            changed = False

            # listen_upper_file
            if node_cfg_path in pw.listen_upper_files:
                val = pw.listen_upper_files[node_cfg_path] or ""
                old = existing.get("listen_upper_file", "") or ""
                if old != val:
                    existing["listen_upper_file"] = val
                    changed = True

            # out_connections
            if node_cfg_path in pw.out_connections:
                if "out_connections" not in existing or not isinstance(existing["out_connections"], dict):
                    existing["out_connections"] = {}
                oc = existing["out_connections"]
                delta = pw.out_connections[node_cfg_path]
                all_flag = delta.get("__ALL__", _UNSET)
                if all_flag is None:  # 重置哨兵
                    if oc:
                        existing["out_connections"] = {}
                        changed = True
                else:
                    for port, val in delta.items():
                        if val is None:  # 删除端口
                            if port in oc:
                                oc.pop(port, None)
                                changed = True
                        else:
                            if oc.get(port) != val:
                                oc[port] = val
                                changed = True

            # port_mappings
            if node_cfg_path in pw.port_mappings:
                if "port_mappings" not in existing or not isinstance(existing["port_mappings"], dict):
                    existing["port_mappings"] = {}
                pm = existing["port_mappings"]
                delta = pw.port_mappings[node_cfg_path]
                all_flag = delta.get("__ALL__", _UNSET)
                if all_flag is None:
                    if pm:
                        existing["port_mappings"] = {}
                        changed = True
                else:
                    for port, val in delta.items():
                        if val is None:
                            if port in pm:
                                pm.pop(port, None)
                                changed = True
                        else:
                            if pm.get(port) != val:
                                pm[port] = val
                                changed = True

            if changed:
                try:
                    with p.open("w", encoding="utf-8") as f:
                        json.dump(existing, f, ensure_ascii=False, indent=2)
                    written_files.add(node_cfg_path)
                except OSError as e:
                    logger.error("[ROUTE-CACHE-FLUSH] write %s failed: %s", p, e)

        # ---- 2. composite.json：写 external_connections ----
        for comp_id, routing in pw.composite_routings.items():
            # 推导 project_path 兜底：从 route_cache.py 所在包反向取 project_root（通常由外层注入更好）
            # 这里采用「从调用 CompositeManager 保存的 COMPOSITE_NODES_DIR 环境变量 + 最近 comp_id 路径搜索」
            comp_json_path = _guess_composite_json_path(comp_id)
            if comp_json_path is None:
                logger.warning("[ROUTE-CACHE-FLUSH] skip comp=%s (cannot guess composite.json path)", comp_id)
                continue
            existing: dict = {}
            try:
                if comp_json_path.is_file():
                    with comp_json_path.open(encoding="utf-8") as f:
                        existing = json.load(f) or {}
            except (OSError, json.JSONDecodeError) as e:
                logger.error("[ROUTE-CACHE-FLUSH] read comp=%s failed: %s", comp_id, e)
                continue
            cur = existing.get("external_connections", {}) or {}
            if "input" not in cur or not isinstance(cur["input"], dict):
                cur["input"] = {}
            if "output" not in cur or not isinstance(cur["output"], dict):
                cur["output"] = {}

            changed = False
            for direction in ("input", "output"):
                delta_dir = routing.get(direction, {}) or {}
                for port, val in delta_dir.items():
                    if val is None:
                        if port in cur[direction]:
                            cur[direction].pop(port, None)
                            changed = True
                    else:
                        if cur[direction].get(port) != val:
                            cur[direction][port] = dict(val) if isinstance(val, dict) else val
                            changed = True
            if changed:
                existing["external_connections"] = cur
                try:
                    with comp_json_path.open("w", encoding="utf-8") as f:
                        json.dump(existing, f, ensure_ascii=False, indent=2)
                    written_files.add(str(comp_json_path))
                except OSError as e:
                    logger.error("[ROUTE-CACHE-FLUSH] write comp=%s failed: %s", comp_id, e)
        return len(written_files)

    def __init__(self) -> None:
        # {node_cfg_path: value or ""}
        self._listen_upper: dict[str, str] = {}
        # {node_cfg_path: {port_name: value or None}}
        self._out_connections: dict[str, dict[str, str | None]] = {}
        # {node_cfg_path: {port_name: value or None}}
        self._port_mappings: dict[str, dict[str, str | None]] = {}
        # {comp_id: {"input": {port: {...} or None}, "output": {port: {...} or None}}}
        self._routings: dict[str, dict] = {}

    # ── listen_upper_file ──

    def set_listen_upper_file(self, node_cfg_path: str, value: str) -> None:
        """设置某节点配置文件的 listen_upper_file。"""
        self._listen_upper[node_cfg_path] = value

    def clear_listen_upper_file(self, node_cfg_path: str) -> None:
        """标记为清除（写入空字符串）。"""
        self._listen_upper[node_cfg_path] = ""

    # ── out_connections (源节点的出边记录，key=source_port_name) ──

    def _ensure_out_conn_map(self, node_cfg_path: str) -> dict[str, str | None]:
        if node_cfg_path not in self._out_connections:
            self._out_connections[node_cfg_path] = {}
        return self._out_connections[node_cfg_path]

    def set_out_connection(self, node_cfg_path: str, source_port_name: str, value: str) -> None:
        """设置源节点某个输出端口对应的 out_connections 条目。"""
        mapping = self._ensure_out_conn_map(node_cfg_path)
        mapping[source_port_name] = value

    def clear_out_connection(self, node_cfg_path: str, source_port_name: str) -> None:
        """标记清除源节点某端口的 out_connections 条目（flush 时会 pop）。"""
        mapping = self._ensure_out_conn_map(node_cfg_path)
        mapping[source_port_name] = None

    def clear_all_out_connections(self, node_cfg_path: str) -> None:
        """标记清除源节点所有端口的 out_connections（flush 时会清空整层 out_connections 字典）。"""
        mapping = self._ensure_out_conn_map(node_cfg_path)
        # 特殊哨兵 "__ALL__" = 重置整个 out_connections 为 {}
        mapping["__ALL__"] = None

    # ── port_mappings (目标节点的多输入口映射，key=target_port_name) ──

    def _ensure_port_map(self, node_cfg_path: str) -> dict[str, str | None]:
        if node_cfg_path not in self._port_mappings:
            self._port_mappings[node_cfg_path] = {}
        return self._port_mappings[node_cfg_path]

    def set_port_mapping(self, node_cfg_path: str, target_port_name: str, value: str) -> None:
        mapping = self._ensure_port_map(node_cfg_path)
        mapping[target_port_name] = value

    def clear_port_mapping(self, node_cfg_path: str, target_port_name: str) -> None:
        mapping = self._ensure_port_map(node_cfg_path)
        mapping[target_port_name] = None

    def clear_all_port_mappings(self, node_cfg_path: str) -> None:
        mapping = self._ensure_port_map(node_cfg_path)
        mapping["__ALL__"] = None

    # ── composite routing ──

    def _ensure_routing(self, comp_id: str) -> dict:
        if comp_id not in self._routings:
            self._routings[comp_id] = {"input": {}, "output": {}}
        for key in ("input", "output"):
            if key not in self._routings[comp_id]:
                self._routings[comp_id][key] = {}
        return self._routings[comp_id]

    def set_composite_routing(
        self,
        comp_id: str,
        direction: str,
        port: str,
        route: dict,
    ) -> None:
        routing = self._ensure_routing(comp_id)
        routing[direction][port] = dict(route)

    def set_composite_input_routing(self, comp_id: str, port: str, route: dict) -> None:
        self.set_composite_routing(comp_id, "input", port, route)

    def set_composite_output_routing(self, comp_id: str, port: str, route: dict) -> None:
        self.set_composite_routing(comp_id, "output", port, route)

    def clear_composite_routing(self, comp_id: str, port: str, direction: str | None = None) -> None:
        """清除某端口的路由。direction=None 同时清除 input+output。"""
        routing = self._routings.get(comp_id)
        if not routing:
            return
        directions = (direction,) if direction else ("input", "output")
        for d in directions:
            if d in routing and port in routing[d]:
                # 标记为 None 表示清除（由 flush 层解释）
                routing[d][port] = None

    # ── 整体清理 ──

    def clear(self, owner_scope: str | Iterable[str] | None = None) -> None:
        """清空缓存。

        Args:
            owner_scope: None=清空全部；str=只清该 comp_id / node_prefix；iterable=多个。
        """
        if owner_scope is None:
            self._listen_upper.clear()
            self._out_connections.clear()
            self._port_mappings.clear()
            self._routings.clear()
            return
        if isinstance(owner_scope, str):
            owners = {owner_scope}
        else:
            owners = set(owner_scope)
        # 按 comp_id 清 routing
        for c in list(self._routings.keys()):
            if c in owners:
                del self._routings[c]
        # listen_upper / out_connections / port_mappings 按路径前缀匹配（粗糙），通常由外层直接 extract 后调用方自己清
        for p in list(self._listen_upper.keys()):
            for o in owners:
                if o and o in p:
                    del self._listen_upper[p]
                    break
        for p in list(self._out_connections.keys()):
            for o in owners:
                if o and o in p:
                    del self._out_connections[p]
                    break
        for p in list(self._port_mappings.keys()):
            for o in owners:
                if o and o in p:
                    del self._port_mappings[p]
                    break

    # ── 快照 / 恢复（事务用）──

    def snapshot(self, owner_scope: str | Iterable[str] | None = None) -> dict:
        """对当前缓存做深拷贝快照，用于事务回滚。"""
        data = {
            "_listen_upper": copy.deepcopy(self._listen_upper),
            "_out_connections": copy.deepcopy(self._out_connections),
            "_port_mappings": copy.deepcopy(self._port_mappings),
            "_routings": copy.deepcopy(self._routings),
        }
        # owner_scope 留作调试信息，实际回滚时恢复全量（深拷贝性能消耗与子节点数正相关，N=1000 内可接受）
        return data

    def restore(self, snapshot: dict) -> None:
        """从快照恢复。"""
        self._listen_upper = copy.deepcopy(snapshot["_listen_upper"])
        self._out_connections = copy.deepcopy(snapshot["_out_connections"])
        self._port_mappings = copy.deepcopy(snapshot["_port_mappings"])
        self._routings = copy.deepcopy(snapshot["_routings"])

    # ── 提取待写盘内容 ──

    def extract_pending(
        self,
        comp_ids: Iterable[str] | None = None,
        node_cfg_paths: Iterable[str] | None = None,
    ) -> PendingWrites:
        """提取缓存中指定范围的待写内容，并从缓存中移除（消费语义）。

        返回的 PendingWrites 交给外层（通常是 CompositeManager 或配置写盘函数）真正落盘。
        """
        pw = PendingWrites()

        if comp_ids is not None:
            for c in comp_ids:
                if c in self._routings:
                    pw.composite_routings[c] = self._routings.pop(c)

        if node_cfg_paths is not None:
            for p in node_cfg_paths:
                if p in self._listen_upper:
                    pw.listen_upper_files[p] = self._listen_upper.pop(p)
                if p in self._out_connections:
                    pw.out_connections[p] = self._out_connections.pop(p)
                if p in self._port_mappings:
                    pw.port_mappings[p] = self._port_mappings.pop(p)

        return pw

    def extract_all_pending(self) -> PendingWrites:
        """一次性提取并清空所有缓存。"""
        pw = PendingWrites(
            listen_upper_files=dict(self._listen_upper),
            out_connections=copy.deepcopy(self._out_connections),
            port_mappings=copy.deepcopy(self._port_mappings),
            composite_routings=copy.deepcopy(self._routings),
        )
        self._listen_upper.clear()
        self._out_connections.clear()
        self._port_mappings.clear()
        self._routings.clear()
        return pw


class Transaction:
    """RouteCache 事务上下文。

    用法::

        tx = Transaction(cache, "comp_abc123")
        try:
            # 对 cache 做批量 set/clear
            tx.commit()
        except Exception:
            tx.rollback()
    """

    def __init__(self, cache: RouteCache, tx_owner: str = ""):
        self._cache = cache
        self._tx_owner = tx_owner
        self._snapshot = cache.snapshot(tx_owner)
        self._committed = False
        self._rolled_back = False

    @property
    def owner(self) -> str:
        return self._tx_owner

    def commit(self) -> None:
        """标记事务 OK；外层调用方随后对 RouteCache 执行 flush。"""
        if self._rolled_back:
            raise RuntimeError("Transaction already rolled back, cannot commit")
        self._committed = True

    def rollback(self) -> None:
        """中途异常 → 恢复快照，丢弃所有缓存变更。"""
        if self._committed:
            raise RuntimeError("Transaction already committed, cannot rollback")
        self._cache.restore(self._snapshot)
        self._rolled_back = True

    # ── Context Manager ──

    def __enter__(self) -> Transaction:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None and not self._rolled_back:
            if not self._committed:
                # 正常退出未显式 commit，自动提交
                self.commit()
            return True
        # 异常时自动回滚
        if not self._rolled_back and not self._committed:
            self.rollback()
        return False  # 不吞异常，向外继续抛出
