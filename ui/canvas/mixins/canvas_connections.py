"""
连线管理（组合类）— 负责连线创建/完成/取消/移除/清空的完整生命周期
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainterPath, QPen

from ui.canvas.items.edge_item import EdgeItem, TempEdgeItem
from ui.core.config.config_merger import get_config_path
from ui.core.edge.canonical_edge_resolver import get_global_mtime_cache
from ui.core.edge.edge_key import (
    ROUTING_COMPOSITE_INPUT,
    ROUTING_COMPOSITE_OUTPUT,
    ROUTING_STANDALONE,
    ROUTING_STANDALONE_PORT_MAP,
    make_edge_key,
)
from ui.core.i18n import t
from ui.core.logger import logger
from ui.core.utils.dialog_utils import themed_message


class CanvasConnections:
    """连线生命周期管理（组合类，通过 self.canvas 访问画布上下文）"""

    def __init__(self, canvas):
        self.canvas = canvas

    # ────────────── Phase3 灰度接入：节点统一状态机双写（不替换旧逻辑，只并行验证）──────────────

    def _state_mgr(self):
        """懒获取 NodeStateManager 单例。灰度阶段未初始化时返回 None，调用方静默跳过。"""
        try:
            mgr = getattr(self.canvas, "_node_state_manager", None)
            if mgr is not None:
                return mgr
            comp_mgr = getattr(self.canvas, "_composite_manager", None)
            if comp_mgr is not None:
                return getattr(comp_mgr, "_node_state_manager", None)
        except Exception:  # noqa: BLE001
            return None
        return None

    def _composite_mgr(self):
        """懒获取 CompositeNode 管理器。"""
        try:
            return getattr(self.canvas, "_composite_manager", None)
        except Exception:  # noqa: BLE001
            return None

    def _edge_writer(self):
        """懒获取 EdgeConfigWriter（阶段2原子化线条配置写器）。
        无 RouteCache 时返回 None，调用方静默跳过（旧逻辑依然会写配置）。"""
        try:
            cached = getattr(self, "_edge_writer_instance", None)
            if cached is not None:
                return cached
            mgr = self._state_mgr()
            if mgr is None:
                return None
            route_cache = getattr(mgr, "route_cache", None)
            if route_cache is None:
                return None
            action = getattr(mgr, "_action_service", None) or getattr(mgr, "action_service", None)
            from ui.core.edge.edge_config_writer import EdgeConfigWriter

            writer = EdgeConfigWriter(
                route_cache=route_cache,
                action_service=action,
                composite_manager=self._composite_mgr(),
            )
            object.__setattr__(self, "_edge_writer_instance", writer)
            return writer
        except Exception as e:  # noqa: BLE001
            logger.warning("[EDGE-WRITER] init lazy failed: %s", e)
            return None

    def _comp_id_of_child(self, node_name: str) -> str:
        """返回 node_name 所属的 composite_id；非子节点返回 ""。"""
        mgr = self._composite_mgr()
        if not mgr:
            return ""
        for cid, comp in (mgr._composites or {}).items():
            if node_name in (comp.get("nodes") or []):
                return cid
        return ""

    def _gray_ensure_registered(self, target_name: str, source_name: str) -> None:
        """幂等注册 target + source 两个节点到 NodeStateManager。

        - 独立节点 → register_standalone
        - 属于某 composite 的子节点 → register_composite_child
        - composite 本体 → register_composite

        已注册节点直接跳过。所有异常只打 warning，不影响主流程。
        """
        mgr = self._state_mgr()
        if mgr is None:
            return

        def _register_one(name: str) -> None:
            if not name or mgr.is_registered(name):
                return
            if name.startswith("composite_"):
                comp_mgr = self._composite_mgr()
                comp = (comp_mgr._composites or {}).get(name, {}) if comp_mgr else {}
                children = list(comp.get("nodes") or [])
                entry = comp.get("entry_node") or (children[0] if children else "")
                try:
                    mgr.register_composite(
                        comp_id=name,
                        child_names=children,
                        entry_node=entry,
                        initially_collapsed=not comp.get("_expanded", False),
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning("[Phase3-gray] register_composite %s failed: %s", name, e)
                return
            cid = self._comp_id_of_child(name)
            if cid:
                try:
                    comp_mgr = self._composite_mgr()
                    comp = (comp_mgr._composites or {}).get(cid, {}) if comp_mgr else {}
                    expanded = bool(comp.get("_expanded", False))
                    mgr.register_composite_child(
                        name,
                        comp_id=cid,
                        # 展开态 → 子节点可见；折叠态 → 子节点 hidden
                        initially_hidden=not expanded,
                    )
                    return
                except Exception as e:  # noqa: BLE001
                    logger.warning("[Phase3-gray] register_composite_child %s failed: %s", name, e)
                    # 失败时回退为独立节点（至少不丢事件）
            try:
                mgr.register_standalone(name)
            except Exception as e:  # noqa: BLE001
                logger.warning("[Phase3-gray] register_standalone %s failed: %s", name, e)

        _register_one(target_name)
        _register_one(source_name)

    def _gray_on_connect(
        self,
        source_name: str | None,
        target_name: str | None,
        source_anchor=None,
        target_anchor=None,
    ) -> None:
        """**create_edge 成功后**：并行调用 NodeStateManager.handle_event("connect_upstream")。

        结果只做差异比对；不影响旧逻辑。失败或不匹配只打 warning。
        """
        if not (source_name and target_name):
            return
        try:
            self._gray_ensure_registered(target_name, source_name)
            mgr = self._state_mgr()
            if mgr is None:
                return
            # 计算 source_output_path（与旧逻辑 _update_node_config_edge 对齐）
            src_output_path = ""
            if self.canvas.parent_window and source_name in (self.canvas.parent_window.nodes_data or {}):
                src_info = self.canvas.parent_window.nodes_data[source_name]
                src_path = src_info.get("path", "")
                if src_path:
                    src_output_path = str((Path(src_path) / "output.json").resolve())
            port_name = (
                target_anchor.port_name if (target_anchor and hasattr(target_anchor, "port_name")) else "default"
            )
            # 入口：composite 本体作为 target（接收）时，state machine 实际跟踪的是 entry node
            # 但此处简化：对 composite_target 不跟踪（复合端口路由由 comp manager 管理）
            if target_name.startswith("composite_"):
                logger.info(
                    "[Phase3-gray-connect OK, composite routing] %s <- %s port=%s (handled by comp._port_routing, no upstream_state tracked on composite)",
                    target_name,
                    source_name,
                    port_name,
                )
                return
            ok = mgr.handle_event(
                target_name,
                "connect_upstream",
                source_output_path=src_output_path,
                upstream_node_name=source_name,
                port_name=port_name,
            )
            if ok:
                logger.info(
                    "[Phase3-gray-connect OK] %s <- %s port=%s",
                    target_name,
                    source_name,
                    port_name,
                )
            else:
                # 不阻止主流程，只打一条差异告警
                s = mgr.get_state(target_name) if mgr.is_registered(target_name) else {}
                logger.warning(
                    "[Phase3-gray-DIFF] connect_upstream rejected for %s <- %s (state=%s/%s/%s). "
                    "Old config write still applied.",
                    target_name,
                    source_name,
                    s.get("membership"),
                    s.get("visibility"),
                    s.get("upstream_state"),
                )
        except Exception as e:  # noqa: BLE001 - 灰度必须不影响主流程
            logger.warning("[Phase3-gray] connect_upstream handle_event skip (non-fatal): %s", e)

    def _gray_on_disconnect(
        self,
        source_name: str | None,
        target_name: str | None,
        edge=None,
    ) -> None:
        """**remove_edge 成功后**：并行调用 NodeStateManager.handle_event("disconnect_upstream")。

        仅差异告警，不影响主流程。
        """
        if not target_name:
            return
        try:
            mgr = self._state_mgr()
            if mgr is None or not mgr.is_registered(target_name):
                return
            port = ""
            if edge and getattr(edge, "end_anchor", None) and hasattr(edge.end_anchor, "port_name"):
                port = edge.end_anchor.port_name
            if target_name.startswith("composite_"):
                logger.info(
                    "[Phase3-gray-disconnect OK, composite routing] %s <- %s port=%s (handled by comp._port_routing)",
                    target_name,
                    source_name,
                    port or "(default)",
                )
                return
            ok = mgr.handle_event(target_name, "disconnect_upstream", port_name=port)
            if ok:
                logger.info(
                    "[Phase3-gray-disconnect OK] %s <- %s port=%s",
                    target_name,
                    source_name,
                    port or "(default)",
                )
            else:
                s = mgr.get_state(target_name)
                logger.warning(
                    "[Phase3-gray-DIFF] disconnect_upstream rejected for %s <- %s (state=%s/%s/%s). "
                    "Old config clear still applied.",
                    target_name,
                    source_name,
                    s.get("membership"),
                    s.get("visibility"),
                    s.get("upstream_state"),
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("[Phase3-gray] disconnect_upstream handle_event skip (non-fatal): %s", e)

    # ──────────────────────────────────────────────────────────────────────────

    def _start_connection_by_name(self, node_name):
        """按节点名称开始连线（供右键菜单调用）"""
        if node_name not in self.canvas.nodes:
            return
        self.start_connection_from_output(self.canvas.nodes[node_name])

    def start_connection_from_output(self, source_node, source_anchor=None):
        """从输出锚点开始连线

        参数:
            source_node: 源节点对象
            source_anchor: 可选，具体的输出 AnchorItem。若为 None 则回退到
                           source_node.output_anchor（@property，统一返回默认输出锚点）
        """
        self.canvas.is_connecting = True
        self.canvas.connect_source = source_node
        self.canvas._connect_source_anchor = source_anchor
        logger.debug(
            "连线模式启动: source=%s, anchor=%s, is_connecting=%s",
            source_node.node_name,
            getattr(source_anchor, "port_name", None),
            self.canvas.is_connecting,
        )

        self.canvas.viewport().setCursor(Qt.CursorShape.CrossCursor)

        self.canvas.temp_edge = TempEdgeItem()
        self.canvas.temp_edge.setZValue(2)
        self.canvas.temp_edge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        pen = QPen(QColor("#4A90E2"), 2, Qt.PenStyle.DashLine)
        self.canvas.temp_edge.setPen(pen)
        self.canvas.scene.addItem(self.canvas.temp_edge)

        cursor_pos = self.canvas.mapFromGlobal(self.canvas.cursor().pos())
        scene_pos = self.canvas.mapToScene(cursor_pos)

        start_anchor = source_anchor
        if start_anchor is None:
            start_anchor = source_node.output_anchor
        anchor_center = start_anchor.boundingRect().center()
        start = start_anchor.mapToScene(anchor_center)

        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(scene_pos)
        self.canvas.temp_edge.setPath(path)

    def complete_connection_to_input(self, target_node, clicked_anchor=None):
        """完成连线到输入锚点（支持指定锚点）"""
        source_anchor = getattr(self.canvas, "_connect_source_anchor", None)
        logger.debug(
            "complete_connection_to_input: source=%s, target=%s, src_anchor=%s, target_anchor=%s, is_connecting=%s",
            self.canvas.connect_source.node_name if self.canvas.connect_source else None,
            target_node.node_name,
            getattr(source_anchor, "port_name", None),
            clicked_anchor.port_name if clicked_anchor else None,
            self.canvas.is_connecting,
        )
        if self.canvas.connect_source and self.canvas.connect_source != target_node:
            self.create_edge(
                self.canvas.connect_source,
                target_node,
                target_anchor=clicked_anchor,
                source_anchor=source_anchor,
            )

        if self.canvas.temp_edge:
            self.canvas.scene.removeItem(self.canvas.temp_edge)
            self.canvas.temp_edge = None

        self.canvas.is_connecting = False
        self.canvas.connect_source = None
        self.canvas.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def create_edge(
        self,
        source_node,
        target_node,
        target_anchor=None,
        source_anchor=None,
        *,
        _from_morph: bool = False,
        _skip_undo_push: bool = False,
        _morph_skip_config: bool = False,
    ):
        """创建连线并配置上下游关系（支持指定源锚点 + 目标锚点）。

        3 个 morph 专用 flag（阶段4 expand/collapse 互斥交接时用）：
          - _from_morph=True: 调用方是 composite_node._expand/_collapse，
            会跳过锚点独占检测的「仅统计可见边」规则（morph 期间 hide 的原边不能算）；
            也不会触发约束6的深入钩子（避免 morph 删除时递归深入到子/父内部）。
          - _skip_undo_push=True: 整个 expand/collapse 已经用 QUndoMacro.beginMacro 包裹，
            内部子命令不单独 push 到 undo stack，否则 macro 就不是原子的。
          - _morph_skip_config=True: 极个别情况下调用方已提前写好 RouteCache 待写集，
            不需要此处重复写（默认 False，正常路径配置写必须跟随 create_edge 直接做，
            不能跳过否则 4 地不同步）。
        """
        # ── 输入锚点独占检测：一个输入锚点只能连接一个输出锚点 ──
        # 只计算可见边：复合节点展开/折叠时隐藏的原边仍残留在锚点引用中，
        # 统计时必须排除它们，否则展开后断开→重连会被误判为"已连接"。
        # BUT: _from_morph=True 时跳过独占检测 —— morph 的阶段B统一删旧边后立刻阶段C建，
        # 时间窗口内旧的隐藏引用还在 _edges 集合里没被 GC，正常可见性过滤也会误判。
        if not _from_morph:
            if target_anchor and hasattr(target_anchor, "port_name"):
                visible_edge_count = sum(1 for e in target_anchor.edges if e.isVisible())
                if visible_edge_count > 0:
                    port_label = getattr(target_anchor, "port_label", "") or getattr(target_anchor, "port_name", "")
                    themed_message(
                        self.canvas,
                        "连线被拒绝",
                        f"输入端口「{port_label}」已连接，一个输入端口只能接入一条连线。",
                        "warning",
                    )
                    return
            else:
                default_input = getattr(target_node, "input_anchor", None)
                if default_input:
                    visible_edge_count = sum(1 for e in default_input.edges if e.isVisible())
                    if visible_edge_count > 0:
                        themed_message(
                            self.canvas,
                            "连线被拒绝",
                            "该节点的输入端已连接，一个输入端口只能接入一条连线。",
                            "warning",
                        )
                        return

            if target_anchor and hasattr(target_anchor, "port_name"):
                for edge in self.canvas.edges:
                    if edge.start_node == source_node and edge.end_node == target_node:
                        if hasattr(edge, "end_anchor") and edge.end_anchor:
                            if edge.end_anchor == target_anchor:
                                themed_message(self.canvas, t("k_title_info"), t("k_canvas_edge_exists"), "info")
                                return
            else:
                for edge in self.canvas.edges:
                    if edge.start_node == source_node and edge.end_node == target_node:
                        themed_message(self.canvas, t("k_title_info"), t("k_canvas_edge_exists"), "info")
                        return
        else:
            # morph 场景：只做最轻量的「完全相同端点+锚点」重复检查（不做独占，因为旧边即将被删）
            if target_anchor and hasattr(target_anchor, "port_name"):
                for edge in self.canvas.edges:
                    if edge.start_node is source_node and edge.end_node is target_node:
                        ea = getattr(edge, "end_anchor", None)
                        if ea is target_anchor:
                            logger.info(
                                "[MORPH-CREATE-SKIP] duplicate edge found during morph: src=%s tgt=%s anchor=%s",
                                getattr(source_node, "node_name", ""),
                                getattr(target_node, "node_name", ""),
                                getattr(target_anchor, "port_name", ""),
                            )
                            return

        source_name = None
        target_name = None
        for name, node in self.canvas.nodes.items():
            if node == source_node:
                source_name = name
            if node == target_node:
                target_name = name

        if not source_name or not target_name:
            return

        # Update node_config.json for real nodes (skip composite nodes which have comp_id as name)
        is_composite_source = source_name.startswith("composite_") if source_name else False
        is_composite_target = target_name.startswith("composite_") if target_name else False

        if not is_composite_source and not is_composite_target:
            self._update_node_config_edge(source_name, target_name, source_anchor, target_anchor)
        else:
            self._update_composite_config_edge(
                source_name, target_name, is_composite_source, is_composite_target, source_anchor, target_anchor
            )

        tgt_port_name = target_anchor.port_name if (target_anchor and hasattr(target_anchor, "port_name")) else None
        src_port_name = source_anchor.port_name if (source_anchor and hasattr(source_anchor, "port_name")) else None

        edge = EdgeItem(
            source_node,
            target_node,
            self.canvas,
            target_anchor,
            source_anchor,
            target_port_name=tgt_port_name,
            source_port_name=src_port_name,
        )
        self.canvas.scene.addItem(edge)
        self.canvas.edges.append(edge)
        edge.update_path()

        up_port_calc = src_port_name or "default"
        dn_port_calc = tgt_port_name or "default"
        if not is_composite_source and not is_composite_target:
            if dn_port_calc and dn_port_calc != "default":
                routing = ROUTING_STANDALONE_PORT_MAP
            else:
                routing = ROUTING_STANDALONE
        elif is_composite_source and not is_composite_target:
            routing = ROUTING_COMPOSITE_OUTPUT
        elif not is_composite_source and is_composite_target:
            routing = ROUTING_COMPOSITE_INPUT
        else:
            routing = ROUTING_COMPOSITE_OUTPUT
        edge_key_calc: tuple | None = None
        try:
            key = make_edge_key(routing, source_name, target_name, up_port_calc, dn_port_calc)
            edge_key_calc = key
            edge._edge_key = key
            state_mgr = getattr(self.canvas, "_node_state_manager", None)
            if state_mgr is not None and hasattr(state_mgr, "register_edge"):
                state_mgr.register_edge(key)
            logger.info(
                "[EDGE-KEY-ASSIGN] routing=%s up=%s[%s] dn=%s[%s] key=%s",
                routing,
                source_name,
                up_port_calc,
                target_name,
                dn_port_calc,
                key,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("[EDGE-KEY-ASSIGN] failed %s/%s: %s", source_name, target_name, e)

        edge_info_source = (
            f" (out_port: {source_anchor.port_name})" if source_anchor and hasattr(source_anchor, "port_name") else ""
        )
        edge_info_target = (
            f" (in_port: {target_anchor.port_name})" if target_anchor and hasattr(target_anchor, "port_name") else ""
        )
        logger.info("创建连线: %s%s -> %s%s", source_name, edge_info_source, target_name, edge_info_target)

        if self.canvas.parent_window and self.canvas.parent_window.current_project_path:
            self.canvas._save_timer.stop()
            self.canvas._save_timer.start(500)

        # 自动录制命令
        self.canvas._record_create_edge(source_name, target_name)

        # ── Phase3 灰度：并行调用统一状态机 connect_upstream（差异告警，不影响主流程）
        self._gray_on_connect(source_name, target_name, source_anchor, target_anchor)
        # ──

        # ── Stage2：EdgeConfigWriter 灰度双写（旧逻辑已写盘，此处再通过 RouteCache + 原子事务写一次）
        writer = self._edge_writer()
        if writer is not None and edge_key_calc is not None:
            from ui.core.edge.edge_config_writer import PlanContext

            nodes_data = self.canvas.parent_window.nodes_data if self.canvas.parent_window else {}
            ctx = PlanContext(
                nodes_data=nodes_data,
                composite_manager=self._composite_mgr(),
                route_cache=writer._cache,
                action_service=writer._action,
            )
            try:
                src_ap = getattr(source_anchor, "port_name", None) or "default"
                dst_ap = getattr(target_anchor, "port_name", None) or "default"
                with writer.begin_transaction(tx_owner=f"stage2-create:{source_name}->{target_name}"):
                    writer.plan_create_edge(
                        edge_key_calc,
                        source_name,
                        target_name,
                        src_port=up_port_calc,
                        dst_port=dn_port_calc,
                        src_anchor_port=src_ap,
                        dst_anchor_port=dst_ap,
                        ctx=ctx,
                    )
                writer.flush_all()
                logger.info(
                    "[EDGE-WRITER][stage2] create_edge parallel write done up=%s dn=%s",
                    source_name,
                    target_name,
                )
            except Exception as e:  # noqa: BLE001
                # 灰度阶段：writer 失败不影响主流程（旧逻辑已成功写盘），仅告警
                logger.warning(
                    "[EDGE-WRITER][stage2] create_edge parallel write SKIPPED (non-fatal): %s",
                    e,
                )
        # ──

    def _update_node_config_edge(self, source_name, target_name, source_anchor, target_anchor):
        """Write node_config.json for a regular node→node edge.

        Fallback priority (covers composite internal child nodes not registered in nodes_data):
        1) parent_window.nodes_data[name] → compat legacy
        2) canvas.nodes[name]._get_node_config() / save + pw.nodes_data name match
        """
        pw = getattr(self.canvas, "parent_window", None)
        nodes_data = getattr(pw, "nodes_data", {}) or {} if pw else {}

        def _resolve_info(name: str) -> dict | None:
            """Return {"config": dict, "path": str} using 3-tier fallback; log which hit."""
            # Fallback 1: pw.nodes_data (works for standalone nodes + composite child nodes if registered)
            if name in nodes_data:
                info = nodes_data[name]
                result = {"config": dict(info.get("config", {}) or {}), "path": str(info.get("path", "") or "")}
                logger.info(
                    "[RESOLVE-INFO] name=%s hit=nodes_data path=%s valid=%s",
                    name,
                    result.get("path"),
                    bool(result.get("path")),
                )
                return result if result["path"] else None
            # Fallback 2: canvas.nodes[name].node_name match → use pw.nodes_data if name is same
            item = getattr(self.canvas, "nodes", {}).get(name)
            if item is None:
                logger.warning("[RESOLVE-INFO] name=%s FAIL: not in nodes_data and canvas.nodes[name] missing", name)
                return None
            # Check if NodeItem.node_name matches (sanity)
            has_node_attr = getattr(item, "node_name", None)
            if has_node_attr and has_node_attr != name:
                logger.warning(
                    "[RESOLVE-INFO] name=%s WARNING: canvas.nodes[name].node_name=%s mismatch", name, has_node_attr
                )
            # Use NodeItem._get_node_config() (calls NodeConfigManager.get_node_config()
            # which itself depends on pw.nodes_data[name].path)
            cfg = None
            path = None
            if callable(getattr(item, "_get_node_config", None)):
                try:
                    cfg = item._get_node_config() or {}
                except Exception as exc:
                    logger.warning("[RESOLVE-INFO] name=%s _get_node_config exc=%s", name, exc)
            # Try to get path: pw.nodes_data[name].path if NodeConfigManager fallback
            if pw and name in getattr(pw, "nodes_data", {}):
                path = str(pw.nodes_data[name].get("path", "") or "")
            if not path and hasattr(item, "data"):
                try:
                    dp = item.data(1)
                    if dp:
                        path = str(dp)
                except Exception:
                    pass
            result = {"config": dict(cfg or {}), "path": path or ""}
            logger.info(
                "[RESOLVE-INFO] name=%s hit=canvas.nodes path=%s valid=%s node_name_attr=%s",
                name,
                result.get("path"),
                bool(result.get("path")),
                getattr(item, "node_name", None),
            )
            return result if result["path"] else None

        source_info = _resolve_info(source_name)
        target_info = _resolve_info(target_name)
        if target_info is None or not target_info.get("path"):
            logger.warning(
                "[CFG-WRITE-SKIPPED] target=%s could not be resolved. src_resolved=%s.",
                target_name,
                source_info is not None and bool(source_info.get("path")),
            )
            return
        source_path = (source_info or {}).get("path", "") or ""
        if not source_path:
            logger.warning("create_edge: source node %s has no path, skipping config", source_name)
            return
        source_output_path = str((Path(source_path) / "output.json").resolve())
        target_config = target_info["config"]

        if target_anchor and hasattr(target_anchor, "port_name"):
            port_name = target_anchor.port_name
            if port_name and port_name != "default":
                target_config.setdefault("port_mappings", {})[port_name] = source_output_path
                logger.info("create_edge: port mapping %s -> %s", port_name, source_output_path)
            else:
                target_config["listen_upper_file"] = source_output_path
                logger.info("create_edge: listen_upper_file=%s", source_output_path)
        else:
            target_config["listen_upper_file"] = source_output_path
            logger.info("create_edge: legacy single-anchor, listen_upper_file=%s", source_output_path)

        if source_anchor and hasattr(source_anchor, "port_name"):
            source_port_name = source_anchor.port_name
            src_cfg_obj = (source_info or {}).get("config", None)
            src_obj_path = (source_info or {}).get("path", None)
            if (
                src_cfg_obj is None
                and hasattr(self.canvas, "parent_window")
                and self.canvas.parent_window
                and source_name in nodes_data
            ):
                src_cfg_obj = nodes_data[source_name].get("config", {})
                src_obj_path = nodes_data[source_name].get("path", "")
            if src_cfg_obj is not None and src_obj_path:
                if not isinstance(src_cfg_obj, dict):
                    src_cfg_obj = {}
                src_cfg_obj.setdefault("out_connections", {})
                tgt_port = (
                    target_anchor.port_name if (target_anchor and hasattr(target_anchor, "port_name")) else "default"
                )
                src_cfg_obj["out_connections"][source_port_name] = f"{target_name}|{tgt_port}"
                try:
                    sc_path = get_config_path(src_obj_path)
                    if src_obj_path:
                        with open(sc_path, "w", encoding="utf-8") as f:
                            json.dump(src_cfg_obj, f, indent=2, ensure_ascii=False)
                        get_global_mtime_cache().invalidate(sc_path)
                        if self.canvas.parent_window and source_name in nodes_data:
                            nodes_data[source_name]["config"] = src_cfg_obj
                except Exception as e:
                    logger.error("save upstream out_connections failed: %s", e)

        config_path = get_config_path(target_info["path"])
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(target_config, f, indent=2, ensure_ascii=False)
            get_global_mtime_cache().invalidate(config_path)
            if self.canvas.parent_window and target_name in nodes_data:
                nodes_data[target_name]["config"] = target_config
            logger.info("configured %s to listen to %s", target_name, source_name)
        except Exception as e:
            logger.error("save config failed: %s", e)

    def _update_composite_config_edge(
        self, source_name, target_name, is_composite_source, is_composite_target, source_anchor, target_anchor
    ):
        """Write config for edges involving composite nodes.

        composite output → external node:
            Set target's listen_upper_file / port_mappings to internal node's output.json

        external node → composite input:
            Set internal node's listen_upper_file to external node's output.json
        """
        manager = getattr(self.canvas, "_composite_manager", None)
        if not manager:
            # 尝试懒初始化：检查 canvas_view 上的 _composite_manager 或尝试恢复
            from ui.core.node.composite_node import CompositeNode

            project_path = self.canvas.parent_window.current_project_path if self.canvas.parent_window else None
            if project_path:
                group_manager = None
                if hasattr(self.canvas.parent_window, "node_list_panel") and self.canvas.parent_window.node_list_panel:
                    group_manager = self.canvas.parent_window.node_list_panel.group_manager
                manager = CompositeNode(project_path, self.canvas, group_manager)
                self.canvas._composite_manager = manager
                logger.info("lazy-initialized composite manager for edge config update")
            else:
                logger.warning(
                    "create_edge: composite manager not available and no project path, "
                    "skipping config update for %s → %s",
                    source_name,
                    target_name,
                )
                return
        nodes_data = self.canvas.parent_window.nodes_data if self.canvas.parent_window else {}
        if not nodes_data:
            logger.warning(
                "create_edge: parent_window.nodes_data unavailable, skipping composite config update for %s → %s",
                source_name,
                target_name,
            )
            return

        if is_composite_source and not is_composite_target:
            # Composite output port → external target node
            port_name = getattr(source_anchor, "port_name", "") or "default"
            internal_name = manager._find_internal_by_port(source_name, port_name, "output")
            if not internal_name and port_name == "default":
                # 用户连接的是复合节点主输出锚点 → 直接找 DAG 出口节点
                internal_name = manager._find_exit_node(source_name)
            if not internal_name or internal_name not in nodes_data:
                logger.warning(
                    "create_edge: composite output port %s/%s not mapped to internal node "
                    "(composite=%s, available output_ports=%s)",
                    source_name,
                    port_name,
                    manager._composites.get(source_name, {}).get("output_ports", []),
                )
                return
            internal_info = nodes_data[internal_name]
            internal_path = internal_info.get("path", "")
            if not internal_path:
                logger.warning("create_edge: internal node %s has no path, composite config skipped", internal_name)
                return
            source_output_path = str((Path(internal_path) / "output.json").resolve())

            # Update external target's config
            target_info = nodes_data.get(target_name)
            if not target_info:
                logger.warning("create_edge: target %s not in nodes_data, composite config skipped", target_name)
                return
            target_config = target_info["config"]
            if target_anchor and hasattr(target_anchor, "port_name"):
                tpn = target_anchor.port_name
                if tpn and tpn != "default":
                    target_config.setdefault("port_mappings", {})[tpn] = source_output_path
                else:
                    target_config["listen_upper_file"] = source_output_path
            else:
                target_config["listen_upper_file"] = source_output_path

            config_path = get_config_path(target_info["path"])
            try:
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(target_config, f, indent=2, ensure_ascii=False)
                logger.info(
                    "composite→external: %s config updated → %s (via %s)",
                    target_name,
                    source_output_path,
                    internal_name,
                )
            except Exception as e:
                logger.error("save composite edge config failed for %s: %s", target_name, e)
                return

            # Record output routing in _port_routing (not internal node's node_config.json)
            tgt_port = target_anchor.port_name if (target_anchor and hasattr(target_anchor, "port_name")) else "default"
            manager.set_output_routing(source_name, port_name, None, target_name, tgt_port)
            logger.info("composite→external: _port_routing output[%s] → %s|%s", port_name, target_name, tgt_port)

        elif is_composite_target and not is_composite_source:
            # External source node → composite input port
            raw_port_name = getattr(target_anchor, "port_name", "") or "default"
            # 外部锚点名（通常 "default"）→ 内部路由 key（"data" 是主入口）
            port_name = raw_port_name
            internal_name = manager._find_internal_by_port(target_name, raw_port_name, "input")
            if not internal_name and raw_port_name in {"default", "data"}:
                # 用户连接的是复合节点主锚点（外部叫 "default"，内部叫 "data"）→ 直接找 DAG 入口节点
                internal_name = manager._find_entry_node(target_name)
                if internal_name:
                    # 内部路由统一使用 "data" 作为主输入端口 key（与 input_ports 定义一致）
                    # 仅当用户连的是 default/data 时才做此转换；其他具体端口名保持原样
                    port_name = "data"
            if not internal_name or internal_name not in nodes_data:
                logger.warning(
                    "create_edge: composite input port %s/%s not mapped to internal node "
                    "(composite=%s, available input_ports=%s)",
                    target_name,
                    raw_port_name,
                    target_name,
                    manager._composites.get(target_name, {}).get("input_ports", []),
                )
                return
            source_data = nodes_data.get(source_name, {})
            source_path = source_data.get("path", "")
            if not source_path:
                logger.warning("create_edge: source %s has no path, composite config skipped", source_name)
                return
            source_output_path = str((Path(source_path) / "output.json").resolve())

            # 子节点接收端口：如果用户连接的是 composite 的具体 sub-port，且 entry_port 有值 → 用 entry_port；
            # 否则主入口用 "default"（这是 expand 后要写进 child node_config.json 的端口）
            entry_port = "default"
            comp_ports = manager._composites.get(target_name, {}).get("input_ports", []) or []
            for cp in comp_ports:
                if cp.get("port_name") == port_name and cp.get("entry_port"):
                    entry_port = cp["entry_port"]
                    break

            spn = source_anchor.port_name if (source_anchor and hasattr(source_anchor, "port_name")) else "default"

            # Record input routing in _port_routing (NOT internal node's listen_upper_file)
            # This prevents the composite's input port from disappearing due to
            # _identify_ports detecting a non-empty listen_upper_file.
            manager.set_input_routing(
                target_name,
                port_name,
                source_output_path,
                target_node=internal_name,
                target_port=entry_port,
                upstream_node_id=source_name,
                upstream_out_port=spn,
            )
            logger.info(
                "external→composite: _port_routing input[%s] ← %s (anchor=%s→internal=%s entry_port=%s)",
                port_name,
                source_output_path,
                raw_port_name,
                internal_name,
                entry_port,
            )

            # Also update source node's out_connections
            source_config = source_data.get("config", {})
            source_config.setdefault("out_connections", {})
            # out_connections 格式："{target_node_name}|{target_port_name}"
            # （target 可以是普通节点也可以是 composite_id，collapse/expand 解析时统一 split("|")[0] 再判断）
            source_config["out_connections"][spn] = f"{target_name}|{port_name}"
            try:
                sc_path = get_config_path(source_path)
                with open(sc_path, "w", encoding="utf-8") as f:
                    json.dump(source_config, f, indent=2, ensure_ascii=False)
                if self.canvas.parent_window and source_name in nodes_data:
                    nodes_data[source_name]["config"] = source_config
                logger.info(
                    "external→composite: source %s out_connections[%s]=%s",
                    source_name,
                    spn,
                    source_config["out_connections"][spn],
                )
            except Exception as e:
                logger.error("save source out_connections failed: %s", e)

        elif is_composite_source and is_composite_target:
            # Composite output port → composite input port
            # Use _port_routing exclusively — no internal node node_config.json writes
            raw_src_port = getattr(source_anchor, "port_name", "") or "default"
            raw_tgt_port = getattr(target_anchor, "port_name", "") or "default"

            # 源端：default→exit node（保持 raw_src_port 原样传递给 set_output_routing，后续 morph 统一映射）
            src_port_name = raw_src_port
            src_internal = manager._find_internal_by_port(source_name, raw_src_port, "output")
            if not src_internal and raw_src_port in {"default", "node_output"}:
                src_internal = manager._find_exit_node(source_name)

            # 目标端：default/data→entry node（内部路由 key 转 "data"，保持与 input_ports 定义一致）
            tgt_port_name = raw_tgt_port
            tgt_internal = manager._find_internal_by_port(target_name, raw_tgt_port, "input")
            if not tgt_internal and raw_tgt_port in {"default", "data"}:
                tgt_internal = manager._find_entry_node(target_name)
                if tgt_internal:
                    tgt_port_name = "data"

            if not src_internal or src_internal not in nodes_data:
                logger.warning(
                    "create_edge: composite→composite source port %s/%s not mapped", source_name, raw_src_port
                )
                return
            if not tgt_internal or tgt_internal not in nodes_data:
                logger.warning(
                    "create_edge: composite→composite target port %s/%s not mapped", target_name, raw_tgt_port
                )
                return

            src_internal_info = nodes_data[src_internal]
            src_path = src_internal_info.get("path", "")
            if not src_path:
                logger.warning("create_edge: composite→composite missing source path for %s", src_internal)
                return

            src_output_path = str((Path(src_path) / "output.json").resolve())

            # 目标子节点接收端口 entry_port
            tgt_entry_port = "default"
            tgt_ports_def = manager._composites.get(target_name, {}).get("input_ports", []) or []
            for cp in tgt_ports_def:
                if cp.get("port_name") == tgt_port_name and cp.get("entry_port"):
                    tgt_entry_port = cp["entry_port"]
                    break

            # Record output routing: source composite output port → target composite + internal
            manager.set_output_routing(source_name, src_port_name, target_name, tgt_internal, tgt_port_name)

            # Record input routing: target composite input port ← source output.json
            manager.set_input_routing(
                target_name,
                tgt_port_name,
                src_output_path,
                target_node=tgt_internal,
                target_port=tgt_entry_port,
                upstream_node_id=source_name,
                upstream_out_port=src_port_name,
            )

            logger.info(
                "composite→composite: _port_routing %s output[%s] → %s input[%s] (src_internal=%s tgt_internal=%s)",
                source_name,
                src_port_name,
                target_name,
                tgt_port_name,
                src_internal,
                tgt_internal,
            )

    def remove_edge(
        self,
        edge,
        *,
        _from_morph: bool = False,
        _skip_undo_push: bool = False,
        _morph_skip_config: bool = False,
    ):
        """移除连线（支持多输入/输出端口 + morph 场景 3 flag）。

        flag 含义同 create_edge：
          - _from_morph=True: expand/collapse morph 调用，跳过约束6深入钩子（避免递归）；
          - _skip_undo_push=True: 已包在 QUndoMacro 里，单独 sub-command 不 push；
          - _morph_skip_config=True: 调用方已用 RouteCache 预写了清配置计划，此处不重复清配置。
        """
        if edge in self.canvas.edges:
            target_name = None
            source_name = None
            for name, node in self.canvas.nodes.items():
                if node == edge.end_node:
                    target_name = name
                if node == edge.start_node:
                    source_name = name

            if source_name and target_name:
                target_port = getattr(edge, "_desired_target_port_name", None)
                source_port = getattr(edge, "_desired_source_port_name", None)
                self.canvas._record_delete_edge(source_name, target_name, target_port, source_port)

            if edge not in self.canvas.edges:
                return

            # ── Clean node_config.json for composite-involved edges ──
            # _morph_skip_config=True: morph 流程已通过 RouteCache 预写清配置计划，
            # 不重复清配置，只做 UI + 4 地同步（anchor/edge_keys/ConnectionSM 会正常走）。
            if not _morph_skip_config:
                is_comp_src = source_name.startswith("composite_") if source_name else False
                is_comp_tgt = target_name.startswith("composite_") if target_name else False
                manager = getattr(self.canvas, "_composite_manager", None)
                nodes_data = self.canvas.parent_window.nodes_data if self.canvas.parent_window else {}

                if is_comp_src and not is_comp_tgt:
                    # Composite output → external: clear _port_routing (all matching downstream + immediate)
                    if manager:
                        port_name = self._resolve_comp_out_port(source_name, edge.start_anchor, manager)
                        tgt_in_port = (
                            edge.end_anchor.port_name
                            if hasattr(edge, "end_anchor") and edge.end_anchor and hasattr(edge.end_anchor, "port_name")
                            else "default"
                        ) or "default"
                        deleted = manager.clear_output_routing_all_matching(
                            source_name,
                            downstream_node_id=target_name,
                            downstream_in_port=tgt_in_port,
                            immediate=True,  # 外部→复合断开立即写盘（project_memory 约束）
                        )
                        # fallback：如果 all_matching 没命中（极端新格式），按端口精确删兜底
                        if deleted == 0 and port_name:
                            manager.clear_output_routing(source_name, port_name, immediate=True)
                        logger.info(
                            "remove composite→external: clear_output matched=%d, fallback_port=%s",
                            deleted,
                            port_name or "",
                        )
                    # Also clean external target (normal path below)
                    if target_name and target_name in nodes_data:
                        self._clean_target_config(nodes_data, target_name, edge)

                elif is_comp_tgt and not is_comp_src:
                    # External → composite input: clear _port_routing (all matching upstream + immediate)
                    # 清除所有端口下（default/data/...）匹配的条目，避免“只清了data但default残留→下次expand又读回来→自动重连”
                    if manager:
                        # 先构造上游真实 output.json 路径用于规范化比较（宽松匹配）
                        src_output_path: str | None = None
                        if source_name and source_name in nodes_data:
                            sp = (nodes_data[source_name] or {}).get("path") or ""
                            if sp:
                                try:
                                    src_output_path = str((Path(sp) / "output.json").resolve())
                                except Exception:
                                    src_output_path = str(Path(sp) / "output.json")
                        spn = (
                            edge.source_anchor.port_name
                            if hasattr(edge, "source_anchor")
                            and edge.source_anchor
                            and hasattr(edge.source_anchor, "port_name")
                            else "default"
                        ) or "default"
                        deleted = manager.clear_input_routing_all_matching(
                            target_name,
                            source_output_path=src_output_path,
                            upstream_node_id=source_name,
                            upstream_out_port=spn,
                            immediate=True,  # 项目约束：外部→复合断开立即写composite.json
                        )
                        # 兜底：精确按端口清（防止all_matching规则漏网）
                        if deleted == 0:
                            port_name = self._resolve_comp_in_port(target_name, edge.end_anchor, manager)
                            if port_name:
                                manager.clear_input_routing(target_name, port_name, immediate=True)
                        logger.info(
                            "remove external→composite: clear_input matched=%d upstream=%s:%s src=%s",
                            deleted,
                            source_name or "",
                            spn,
                            src_output_path or "",
                        )
                    # Also clean external source's out_connections (normal path below)
                    if source_name and source_name in nodes_data:
                        self._clean_source_out_connections(nodes_data, source_name, edge)

                elif is_comp_src and is_comp_tgt:
                    # Composite → composite: clear both _port_routing entries (all_matching + immediate)
                    if manager:
                        src_port = self._resolve_comp_out_port(source_name, edge.start_anchor, manager)
                        tgt_port = self._resolve_comp_in_port(target_name, edge.end_anchor, manager)
                        tgt_in_port = (
                            edge.end_anchor.port_name
                            if hasattr(edge, "end_anchor") and edge.end_anchor and hasattr(edge.end_anchor, "port_name")
                            else "default"
                        ) or "default"
                        src_sp = (
                            edge.source_anchor.port_name
                            if hasattr(edge, "source_anchor")
                            and edge.source_anchor
                            and hasattr(edge.source_anchor, "port_name")
                            else "default"
                        ) or "default"
                        del_out = manager.clear_output_routing_all_matching(
                            source_name,
                            downstream_node_id=target_name,
                            downstream_in_port=tgt_in_port,
                            immediate=True,
                        )
                        if del_out == 0 and src_port:
                            manager.clear_output_routing(source_name, src_port, immediate=True)
                        src_output_path = None
                        if src_sp and hasattr(self.canvas, "nodes"):
                            src_int = manager._find_internal_by_port(source_name, src_sp, "output")
                            if not src_int and src_sp in {"default", "node_output"}:
                                src_int = manager._find_exit_node(source_name)
                            if src_int and src_int in nodes_data:
                                p = (nodes_data[src_int] or {}).get("path") or ""
                                if p:
                                    try:
                                        src_output_path = str((Path(p) / "output.json").resolve())
                                    except Exception:
                                        src_output_path = str(Path(p) / "output.json")
                        del_inp = manager.clear_input_routing_all_matching(
                            target_name,
                            source_output_path=src_output_path,
                            upstream_node_id=source_name,
                            upstream_out_port=src_sp,
                            immediate=True,
                        )
                        if del_inp == 0 and tgt_port:
                            manager.clear_input_routing(target_name, tgt_port, immediate=True)
                        logger.info(
                            "remove composite→composite: clear_output matched=%d clear_input matched=%d",
                            del_out,
                            del_inp,
                        )

                elif not is_comp_src and not is_comp_tgt:
                    # Normal node→node edge
                    if target_name and target_name in nodes_data:
                        self._clean_target_config(nodes_data, target_name, edge)
                    if source_name and source_name in nodes_data:
                        self._clean_source_out_connections(nodes_data, source_name, edge)
            else:
                logger.info(
                    "[MORPH-SKIP-CONFIG-CLEAR] remove_edge %s->%s skipped config clear (_morph_skip_config=True)",
                    source_name or "",
                    target_name or "",
                )

            edge.remove_from_scene()
            self.canvas.edges.remove(edge)

            if self.canvas.parent_window and self.canvas.parent_window.current_project_path:
                self.canvas._save_timer.stop()
                self.canvas._save_timer.start(500)

            # ── Phase3 灰度：并行调用统一状态机 disconnect_upstream（差异告警，不影响主流程）
            self._gray_on_disconnect(source_name, target_name, edge)
            # ──

            existing_key = getattr(edge, "_edge_key", None)
            if existing_key is not None:
                try:
                    state_mgr = getattr(self.canvas, "_node_state_manager", None)
                    if state_mgr is not None and hasattr(state_mgr, "unregister_edge"):
                        state_mgr.unregister_edge(existing_key)
                    logger.info(
                        "[EDGE-KEY-UNREGISTER] key=%s up=%s dn=%s",
                        existing_key,
                        source_name or "",
                        target_name or "",
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning("[EDGE-KEY-UNREGISTER] failed %s: %s", existing_key, e)

            # ── Stage2：EdgeConfigWriter 灰度双写（旧逻辑已清盘，此处再通过 RouteCache 原子清一次）
            #    _morph_skip_config=True 时跳过 — morph 流程会统一原子 flush，不重复清。
            if not _morph_skip_config:
                writer = self._edge_writer()
                if writer is not None and existing_key is not None and source_name and target_name:
                    from ui.core.edge.edge_config_writer import PlanContext

                    ctx_nodes_data = self.canvas.parent_window.nodes_data if self.canvas.parent_window else {}
                    ctx = PlanContext(
                        nodes_data=ctx_nodes_data,
                        composite_manager=self._composite_mgr(),
                        route_cache=writer._cache,
                        action_service=writer._action,
                    )
                    try:
                        src_ap = getattr(edge.start_anchor, "port_name", None) or "default"
                        dst_ap = getattr(edge.end_anchor, "port_name", None) or "default"
                        src_real_port = getattr(edge, "_desired_source_port_name", None) or src_ap
                        dst_real_port = getattr(edge, "_desired_target_port_name", None) or dst_ap
                        with writer.begin_transaction(tx_owner=f"stage2-remove:{source_name}->{target_name}"):
                            writer.plan_remove_edge(
                                existing_key,
                                source_name,
                                target_name,
                                src_port=src_real_port,
                                dst_port=dst_real_port,
                                src_anchor_port=src_ap,
                                dst_anchor_port=dst_ap,
                                ctx=ctx,
                            )
                        writer.flush_all()
                        logger.info(
                            "[EDGE-WRITER][stage2] remove_edge parallel clear done up=%s dn=%s",
                            source_name,
                            target_name,
                        )
                    except Exception as e:  # noqa: BLE001
                        # 灰度阶段：writer 失败不影响主流程（旧逻辑已成功清盘），仅告警
                        logger.warning(
                            "[EDGE-WRITER][stage2] remove_edge parallel clear SKIPPED (non-fatal): %s",
                            e,
                        )
            # ──

            # ══════════════════════════════════════════════════════════════
            # 阶段4.2 约束6级联钩子（非 _from_morph 才执行，避免 morph 递归死循环）
            #   目标：用户手动删边时，保证「复合 C / 子成员 N」的配置 4 地同步，
            #   杜绝「删了折叠态显示的 comp→external 连线，展开态又从子配置里 ghost 回来」
            #   以及「删了展开态子→external 连线，折叠态 comp.in_port 仍残留显示 ghost 线」
            # ══════════════════════════════════════════════════════════════
            if not _from_morph and source_name and target_name:
                try:
                    self._constraint6_cascade_delete(
                        edge,
                        source_name,
                        target_name,
                        is_comp_src=bool(source_name.startswith("composite_")),
                        is_comp_tgt=bool(target_name.startswith("composite_")),
                    )
                except Exception as e_c6:  # noqa: BLE001
                    logger.warning(
                        "[CONSTRAINT6-CASCADE] exception (non-fatal) %s->%s: %s",
                        source_name,
                        target_name,
                        e_c6,
                        exc_info=True,
                    )

    # =====================================================================
    # 阶段4.2 约束6级联删除：保证手动删边时「复合端 / 子端」双方配置同时被清
    # =====================================================================

    def _constraint6_cascade_delete(
        self,
        edge,
        source_name: str,
        target_name: str,
        *,
        is_comp_src: bool,
        is_comp_tgt: bool,
    ) -> None:
        """用户手动删边（非 morph）时的级联配置清理。

        情况 A：external ↔ composite（一端是 composite_*，另一端不是）
                → 除了现有清 composite.json.in_port，还需要 cascade 到 composite
                  内部对应子节点的 listen_upper_file / port_mappings。

        情况 B：external ↔ child（child 在某 composite 内，且该 composite 当前是折叠态）
                → 除了清子节点的 listen_upper_file/port_mappings，还需要 cascade 到
                  composite.json 的对应 in_port.source_output_path，避免折叠态仍显示幽灵。
        """
        manager = self._composite_mgr()
        if manager is None:
            return
        nodes_data = self.canvas.parent_window.nodes_data if self.canvas.parent_window else {}

        # ── 情况 A：external → composite_input ──
        if is_comp_tgt and not is_comp_src:
            comp_id = target_name
            routing = manager._get_port_routing(comp_id)
            in_r = (routing.get("input", {}) or {}).copy()
            # 通过 end_anchor 找到被删的 in_port
            dst_anchor = getattr(edge, "end_anchor", None)
            port = self._resolve_comp_in_port(comp_id, dst_anchor, manager)
            if not port:
                return
            entry = in_r.get(port)
            # 找到 target_child/target_port（routing dict 结构下，或 entry 是路径字符串则反查）
            tgt_child = ""
            tgt_child_port = "default"
            if isinstance(entry, dict):
                tgt_child = entry.get("target_node", "") or ""
                tgt_child_port = entry.get("target_port", "default") or "default"
            if not tgt_child:
                # 兜底：通过 input_ports 反查 internal_node
                tgt_child = manager._find_internal_by_port(comp_id, port, "input") or ""
                if tgt_child:
                    tgt_child_port = "default"
            if tgt_child:
                # cascade: 清子节点 listen_upper_file / port_mappings
                child_cfg_path = self._node_cfg_path(tgt_child, nodes_data)
                if child_cfg_path:
                    # 实时读磁盘 + 改对应字段 + 写回（简单直接，不走 RouteCache）
                    self._cascade_clear_child_cfg(
                        child_cfg_path,
                        tgt_child_port,
                        op_name=f"constraint6-A:external→comp.in[{port}]",
                    )
                # 同时 cascade 到 out_connections[source_port] 在上游节点
                src_out_ports = [getattr(getattr(edge, "start_anchor", None), "port_name", None) or "default"]
                for src_port in src_out_ports:
                    self._cascade_clear_source_out_conn(
                        source_name, src_port, nodes_data, f"constraint6-A(src):{source_name}"
                    )
            return

        # ── 情况 A（输出向）：composite_output → external ──
        if is_comp_src and not is_comp_tgt:
            comp_id = source_name
            src_anchor = getattr(edge, "start_anchor", None)
            port = self._resolve_comp_out_port(comp_id, src_anchor, manager)
            if not port:
                return
            # 找到对应子节点 out_connections：
            child_src = manager._find_internal_by_port(comp_id, port, "output") or ""
            if not child_src and port in {"default", "node_output"}:
                child_src = manager._find_exit_node(comp_id)
            if child_src:
                # cascade: 清 child_src.out_connections[source_port] 对 target 的记录
                child_cfg_path = self._node_cfg_path(child_src, nodes_data)
                if child_cfg_path:
                    # child 端写 external 的 out_connections，需要匹配 target_name
                    self._cascade_clear_child_out_conn_to_target(
                        child_cfg_path,
                        target_name,
                        op_name=f"constraint6-A:comp.out[{port}]→external",
                    )
                # 同时 cascade 到 external 端：清 target 的 listen_upper_file/port_mappings
                tgt_cfg_path = self._node_cfg_path(target_name, nodes_data)
                if tgt_cfg_path:
                    dst_port = (
                        getattr(edge, "_desired_target_port_name", None)
                        or getattr(getattr(edge, "end_anchor", None), "port_name", None)
                        or "default"
                    )
                    self._cascade_clear_child_cfg(
                        tgt_cfg_path,
                        dst_port,
                        op_name=f"constraint6-A(tgt):{target_name} listen clear",
                    )
            return

        # ── 情况 B：external ↔ child 且 child 在复合 C 内，C 当前折叠 ──
        #    判断：source_name 或 target_name 是否是 composite_* 前缀？
        #    如果都不是 → 检查「src 是否在复合内且复合折叠」或「dst 是否在复合内且复合折叠」
        if not is_comp_src and not is_comp_tgt:
            # B1：target 是 child（在某个 comp 内且 comp 折叠）→ cascade 清 comp.input[in_port]
            tgt_comp_id = manager._find_composite_of_node(target_name)
            if tgt_comp_id:
                tgt_comp = manager._composites.get(tgt_comp_id, {})
                if not tgt_comp.get("_expanded"):
                    # comp 当前折叠 → 需要清 composite.json 中对应 target_name:target_port 的 in_port.source_output_path
                    # target_port 来自 edge end_anchor
                    dst_real_port = (
                        getattr(edge, "_desired_target_port_name", None)
                        or getattr(getattr(edge, "end_anchor", None), "port_name", None)
                        or "default"
                    )
                    self._cascade_clear_comp_inport_by_child(
                        manager,
                        tgt_comp_id,
                        target_name,
                        dst_real_port,
                        op_name=f"constraint6-B1:external→child[{target_name}] folded",
                    )
            # B2（对称）：source 是 child（在 comp 内且 comp 折叠）→ cascade 清 comp.output[out_port]
            src_comp_id = manager._find_composite_of_node(source_name)
            if src_comp_id:
                src_comp = manager._composites.get(src_comp_id, {})
                if not src_comp.get("_expanded"):
                    src_real_port = (
                        getattr(edge, "_desired_source_port_name", None)
                        or getattr(getattr(edge, "start_anchor", None), "port_name", None)
                        or "default"
                    )
                    self._cascade_clear_comp_outport_by_child(
                        manager,
                        src_comp_id,
                        source_name,
                        src_real_port,
                        op_name=f"constraint6-B2:child[{source_name}]→external folded",
                    )

    # ── cascade 小工具 ──

    def _node_cfg_path(self, node_name: str, nodes_data: dict) -> str | None:
        if node_name in nodes_data:
            p = nodes_data[node_name].get("path")
            if p:
                from ui.core.config.config_merger import get_config_path

                return str(get_config_path(p))
        # fallback：project_path/nodes/<name>/node_config.json
        if self.canvas.parent_window and getattr(self.canvas.parent_window, "current_project_path", None):
            from pathlib import Path

            from ui.core.config.config_merger import get_config_path

            cand = Path(self.canvas.parent_window.current_project_path) / "nodes" / node_name
            if cand.is_dir():
                return str(get_config_path(str(cand)))
        return None

    @staticmethod
    def _cascade_clear_child_cfg(child_cfg_path: str, target_port: str, *, op_name: str) -> None:
        """清 child_cfg 的 listen_upper_file(target_port="default") 或 port_mappings[target_port]。"""
        import json
        from pathlib import Path

        p = Path(child_cfg_path)
        try:
            if not p.is_file():
                return
            with p.open(encoding="utf-8") as f:
                cfg = json.load(f) or {}
            changed = False
            if target_port == "default":
                if cfg.get("listen_upper_file"):
                    cfg["listen_upper_file"] = ""
                    changed = True
            else:
                pm = cfg.get("port_mappings", {}) or {}
                if target_port in pm:
                    del pm[target_port]
                    cfg["port_mappings"] = pm
                    changed = True
            if changed:
                with p.open("w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                logger.info("[C6-CASCADE] %s → cleared child %s.%s", op_name, p.name, target_port)
        except Exception as e:
            logger.warning("[C6-CASCADE] %s failed child cfg: %s", op_name, e)

    @staticmethod
    def _cascade_clear_source_out_conn(source_name: str, src_port: str, nodes_data: dict, op_name: str) -> None:
        """清 source 节点 out_connections[src_port]（非端口映射的 out_connection 入口）。"""
        import json as _json
        from pathlib import Path

        # 拿 source 节点 cfg_path
        sp = None
        if source_name in nodes_data:
            sp0 = nodes_data[source_name].get("path")
            if sp0:
                from ui.core.config.config_merger import get_config_path

                sp = Path(get_config_path(sp0))
        if sp is None or not sp.is_file():
            return
        try:
            with sp.open(encoding="utf-8") as f:
                cfg = _json.load(f) or {}
            oc = cfg.get("out_connections", {}) or {}
            if src_port in oc:
                del oc[src_port]
                cfg["out_connections"] = oc
                with sp.open("w", encoding="utf-8") as f:
                    _json.dump(cfg, f, ensure_ascii=False, indent=2)
                logger.info("[C6-CASCADE] %s → cleared %s.out_connections[%s]", op_name, source_name, src_port)
        except Exception as e:
            logger.warning("[C6-CASCADE] %s failed out_conn %s: %s", op_name, source_name, e)

    @staticmethod
    def _cascade_clear_child_out_conn_to_target(child_cfg_path: str, target_node_name: str, *, op_name: str) -> None:
        """清 child 节点 out_connections 中值指向 target_node_name 的条目（即删除对子→下游的出边记录）。"""
        import json
        from pathlib import Path

        p = Path(child_cfg_path)
        try:
            if not p.is_file():
                return
            with p.open(encoding="utf-8") as f:
                cfg = json.load(f) or {}
            oc = cfg.get("out_connections", {}) or {}
            to_del = []
            for k, v in oc.items():
                if isinstance(v, str):
                    head = v.split("|", 1)[0]
                    if head == target_node_name:
                        to_del.append(k)
            if to_del:
                for k in to_del:
                    del oc[k]
                cfg["out_connections"] = oc
                with p.open("w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                logger.info(
                    "[C6-CASCADE] %s → child %s out_connections drop keys=%s (target=%s)",
                    op_name,
                    p.name,
                    to_del,
                    target_node_name,
                )
        except Exception as e:
            logger.warning("[C6-CASCADE] %s failed child out_conn: %s", op_name, e)

    @staticmethod
    def _cascade_clear_comp_inport_by_child(
        manager, comp_id: str, target_child: str, target_child_port: str, *, op_name: str
    ) -> None:
        """遍历 composite._port_routing.input，找到 target_node/target_port == (target_child, target_child_port)
        的条目，把 source_output_path 清成空。"""
        import json as _j
        from pathlib import Path

        try:
            manager._ensure_port_routing(comp_id)
            r_in = manager._composites[comp_id]["_port_routing"].get("input", {}) or {}
            cleared_ports = []
            for port, entry in r_in.items():
                t_node = ""
                t_port = "default"
                if isinstance(entry, dict):
                    t_node = entry.get("target_node", "") or ""
                    t_port = entry.get("target_port", "default") or "default"
                if t_node == target_child and t_port == target_child_port:
                    if isinstance(entry, dict):
                        entry["source_output_path"] = ""
                    else:
                        r_in[port] = {"source_output_path": "", "target_node": "", "target_port": "default"}
                    cleared_ports.append(port)
            if cleared_ports:
                manager.save()  # 先内存 comp 落盘（同步 _port_routing 到内存备份，实际 composite.json 下面写）
                # 同步 composite.json
                comp_cfg_p = Path(manager._project_path) / "composite_nodes" / f"{comp_id}.json"
                if comp_cfg_p.is_file():
                    try:
                        with comp_cfg_p.open(encoding="utf-8") as f:
                            ccfg = _j.load(f) or {}
                        ext = ccfg.get("external_connections", {}) or {}
                        ext_in = ext.get("input", {}) or {}
                        for port in cleared_ports:
                            if isinstance(ext_in.get(port), dict):
                                ext_in[port]["source_output_path"] = ""
                            else:
                                ext_in[port] = {"source_output_path": "", "target_node": "", "target_port": "default"}
                        ext["input"] = ext_in
                        ccfg["external_connections"] = ext
                        with comp_cfg_p.open("w", encoding="utf-8") as f:
                            _j.dump(ccfg, f, ensure_ascii=False, indent=2)
                        logger.info("[C6-CASCADE] %s → comp=%s cleared input ports=%s", op_name, comp_id, cleared_ports)
                    except Exception:
                        pass
                else:
                    logger.info(
                        "[C6-CASCADE] %s → comp=%s memory clear ports=%s (no composite.json)",
                        op_name,
                        comp_id,
                        cleared_ports,
                    )
        except Exception as e:
            logger.warning("[C6-CASCADE] %s comp_inport cascade failed: %s", op_name, e)

    @staticmethod
    def _cascade_clear_comp_outport_by_child(
        manager, comp_id: str, src_child: str, src_child_port: str, *, op_name: str
    ) -> None:
        """折叠态 child.src_port→external 被用户手动删 → 同步清 composite.json.output 对应端口映射。

        实现：output_ports 反查 port_name（internal_node=src_child），然后清 _port_routing.output[port]。
        """
        import json as _j
        from pathlib import Path

        try:
            comp = manager._composites.get(comp_id, {})
            out_ports = comp.get("output_ports", []) or []
            candidate_ports = []
            for p in out_ports:
                if p.get("internal_node") == src_child:
                    candidate_ports.append(p.get("port_name", ""))
            if not candidate_ports and src_child_port in {"default", "node_output"}:
                # 兜底：默认出口可能叫 {exit_node}_out
                exit_node = manager._find_exit_node(comp_id)
                if exit_node == src_child:
                    candidate_ports.append(f"{exit_node}_out")
            if not candidate_ports:
                return
            manager._ensure_port_routing(comp_id)
            r_out = manager._composites[comp_id]["_port_routing"].get("output", {}) or {}
            cleared = []
            for port in candidate_ports:
                if port in r_out:
                    # 清空该 output 条目
                    r_out[port] = {"target_composite": "", "target_node": "", "target_port": "default"}
                    cleared.append(port)
            if cleared:
                manager.save()
                comp_cfg_p = Path(manager._project_path) / "composite_nodes" / f"{comp_id}.json"
                if comp_cfg_p.is_file():
                    try:
                        with comp_cfg_p.open(encoding="utf-8") as f:
                            ccfg = _j.load(f) or {}
                        ext = ccfg.get("external_connections", {}) or {}
                        ext_out = ext.get("output", {}) or {}
                        for port in cleared:
                            ext_out[port] = {"target_composite": "", "target_node": "", "target_port": "default"}
                        ext["output"] = ext_out
                        ccfg["external_connections"] = ext
                        with comp_cfg_p.open("w", encoding="utf-8") as f:
                            _j.dump(ccfg, f, ensure_ascii=False, indent=2)
                        logger.info("[C6-CASCADE] %s → comp=%s cleared output ports=%s", op_name, comp_id, cleared)
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("[C6-CASCADE] %s comp_outport cascade failed: %s", op_name, e)

    def _resolve_comp_out_port(self, comp_id, anchor, manager):
        """对齐 create_edge「复合→外部」时的 output 端口名解析逻辑。
        仅返回要用于 clear_output_routing 的真实端口名；找不到映射则返回空串。"""
        if not manager:
            return ""
        raw = getattr(anchor, "port_name", "") if anchor else ""
        port = raw or "default"
        internal = manager._find_internal_by_port(comp_id, port, "output")
        if not internal and port == "default":
            internal = manager._find_exit_node(comp_id)
        if not internal:
            logger.warning(
                "[COMPOSITE-EDGE-REMOVE-RESOLVE] comp=%s output anchor_port=%s cannot map internal, use raw=%s",
                comp_id,
                raw,
                port,
            )
        logger.info(
            "[COMPOSITE-EDGE-REMOVE-RESOLVE] comp=%s OUTPUT anchor_port=%r → clear_port=%s",
            comp_id,
            raw,
            port,
        )
        return port

    def _resolve_comp_in_port(self, comp_id, anchor, manager):
        """对齐 create_edge「外部→复合」时的 input 端口名解析逻辑。
        关键：default 主锚点会被重写为 "data"（因为 _identify_ports / routing 存的是 data 键）。"""
        if not manager:
            return ""
        raw = getattr(anchor, "port_name", "") if anchor else ""
        port = raw or "default"
        internal = manager._find_internal_by_port(comp_id, port, "input")
        if not internal and port == "default":
            internal = manager._find_entry_node(comp_id)
            port = "data"  # 与 create_edge 保持完全一致：主锚点最终写入 routing 用 "data"
        if not internal:
            logger.warning(
                "[COMPOSITE-EDGE-REMOVE-RESOLVE] comp=%s input anchor_port=%s cannot map internal, use raw=%s",
                comp_id,
                raw,
                port,
            )
        logger.info(
            "[COMPOSITE-EDGE-REMOVE-RESOLVE] comp=%s INPUT anchor_port=%r → clear_port=%s",
            comp_id,
            raw,
            port,
        )
        return port

    def _resolve_node_info_for_clean(self, nodes_data, name: str) -> dict | None:
        """remove_edge 时兜底找 {config,path}：nodes_data → canvas.nodes[item] 级联 fallback。"""
        if name in nodes_data:
            info = nodes_data[name]
            result = {"config": dict(info.get("config", {}) or {}), "path": str(info.get("path", "") or "")}
            logger.info(
                "[RESOLVE-CLEAN] name=%s hit=nodes_data path=%s valid=%s",
                name,
                result.get("path"),
                bool(result.get("path")),
            )
            return result if result["path"] else None
        item = getattr(self.canvas, "nodes", {}).get(name)
        if item is None:
            logger.warning("[RESOLVE-CLEAN] name=%s FAIL: not in nodes_data/canvas.nodes", name)
            return None
        cfg = None
        path = None
        if callable(getattr(item, "_get_node_config", None)):
            try:
                cfg = item._get_node_config() or {}
            except Exception as exc:
                logger.warning("[RESOLVE-CLEAN] name=%s _get_node_config exc=%s", name, exc)
        pw = getattr(self.canvas, "parent_window", None)
        if pw and name in getattr(pw, "nodes_data", {}):
            path = str(pw.nodes_data[name].get("path", "") or "")
        if not path and hasattr(item, "data"):
            try:
                dp = item.data(1)
                if dp:
                    path = str(dp)
            except Exception:
                pass
        result = {"config": dict(cfg or {}), "path": path or ""}
        logger.info(
            "[RESOLVE-CLEAN] name=%s hit=canvas.nodes path=%s valid=%s node_name_attr=%s",
            name,
            result.get("path"),
            bool(result.get("path")),
            getattr(item, "node_name", None),
        )
        return result if result["path"] else None

    def _clean_target_config(self, nodes_data, target_name, edge):
        """Clear listen_upper_file / port_mappings for a target node on edge removal.

        Falls back to resolving target via canvas.nodes if target not in nodes_data
        (e.g. composite internal child during collapse morph).
        """
        info = self._resolve_node_info_for_clean(nodes_data, target_name)
        if info is None or not info.get("path"):
            logger.warning("[CLEAN-TARGET-SKIP] %s not resolvable (no path)", target_name)
            return
        target_config = info["config"]
        if not isinstance(target_config, dict):
            target_config = {}

        if edge.end_anchor and hasattr(edge.end_anchor, "port_name"):
            port_name = edge.end_anchor.port_name
            if port_name and port_name != "default":
                if "port_mappings" in target_config and port_name in target_config["port_mappings"]:
                    del target_config["port_mappings"][port_name]
                    logger.debug("已移除端口映射: %s", port_name)
            else:
                target_config["listen_upper_file"] = ""
                logger.debug("已清空 listen_upper_file")
        else:
            target_config["listen_upper_file"] = ""

        config_path = get_config_path(info["path"])
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(target_config, f, indent=2, ensure_ascii=False)
            get_global_mtime_cache().invalidate(config_path)
            if target_name in nodes_data:
                nodes_data[target_name]["config"] = target_config
            logger.info("已清空 %s 的监听配置及端口映射", target_name)
        except Exception as e:
            logger.error("保存配置失败: %s", e)

    def _clean_source_out_connections(self, nodes_data, source_name, edge):
        """Clear out_connections entry for a source node on edge removal.

        Falls back to canvas.nodes item lookup if source not in nodes_data.
        """
        info = self._resolve_node_info_for_clean(nodes_data, source_name)
        if info is None or not info.get("path"):
            logger.warning("[CLEAN-SOURCE-SKIP] %s not resolvable (no path)", source_name)
            return
        source_config = info.get("config", None) or {}
        if not isinstance(source_config, dict):
            source_config = {}
        if "out_connections" in source_config and edge.start_anchor and hasattr(edge.start_anchor, "port_name"):
            sp = edge.start_anchor.port_name
            if sp in source_config["out_connections"]:
                del source_config["out_connections"][sp]
            try:
                sc_path = get_config_path(info["path"])
                with open(sc_path, "w", encoding="utf-8") as f:
                    json.dump(source_config, f, indent=2, ensure_ascii=False)
                get_global_mtime_cache().invalidate(sc_path)
                if source_name in nodes_data:
                    nodes_data[source_name]["config"] = source_config
            except Exception as e:
                logger.error("保存上游节点出向连接配置失败: %s", e)

    def cancel_connection(self):
        """取消连线"""
        if self.canvas.temp_edge:
            self.canvas.scene.removeItem(self.canvas.temp_edge)
            self.canvas.temp_edge = None

        self.canvas.is_connecting = False
        self.canvas.connect_source = None
        self.canvas.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def clear_edges(self):
        """清空所有连线 — 跳过复合节点内部的隐藏连线"""
        for edge in self.canvas.edges[:]:
            if not edge.isVisible():
                continue  # 跳过复合节点内部隐藏边
            self.remove_edge(edge)
        self.canvas.edges = [e for e in self.canvas.edges if not e.isVisible()]

        # 清空所有可见节点所有锚点的连线引用
        for node in self.canvas.nodes.values():
            if not node.isVisible():
                continue  # 跳过复合节点内部隐藏节点
            if hasattr(node, "all_input_anchors") and callable(getattr(node, "all_input_anchors", None)):
                for anchor in node.all_input_anchors():
                    if anchor is not None:
                        anchor.clear_edges()
            elif hasattr(node, "input_anchor"):
                node.input_anchor.clear_edges()
            if hasattr(node, "all_output_anchors") and callable(getattr(node, "all_output_anchors", None)):
                for anchor in node.all_output_anchors():
                    if anchor is not None:
                        anchor.clear_edges()
            elif hasattr(node, "output_anchor"):
                node.output_anchor.clear_edges()
