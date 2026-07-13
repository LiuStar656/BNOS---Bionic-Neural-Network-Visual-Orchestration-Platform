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
from ui.core.i18n import t
from ui.core.logger import logger
from ui.core.utils.dialog_utils import themed_message


class CanvasConnections:
    """连线生命周期管理（组合类，通过 self.canvas 访问画布上下文）"""

    def __init__(self, canvas):
        self.canvas = canvas

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

    def create_edge(self, source_node, target_node, target_anchor=None, source_anchor=None):
        """创建连线并配置上下游关系（支持指定源锚点 + 目标锚点）"""
        # ── 输入锚点独占检测：一个输入锚点只能连接一个输出锚点 ──
        if target_anchor and hasattr(target_anchor, "port_name"):
            # 检查该目标输入锚点是否已有连线
            if target_anchor.edges:
                port_label = getattr(target_anchor, "port_label", "") or getattr(target_anchor, "port_name", "")
                themed_message(
                    self.canvas,
                    "连线被拒绝",
                    f"输入端口「{port_label}」已连接，一个输入端口只能接入一条连线。",
                    "warning",
                )
                return
        else:
            # 无指定锚点时，检查目标节点默认输入锚点是否已有连线
            default_input = getattr(target_node, "input_anchor", None)
            if default_input and default_input.edges:
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

        source_name = None
        target_name = None
        for name, node in self.canvas.nodes.items():
            if node == source_node:
                source_name = name
            if node == target_node:
                target_name = name

        if not source_name or not target_name:
            return

        # Update config.json for real nodes (skip composite nodes which have comp_id as name)
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

    def _update_node_config_edge(self, source_name, target_name, source_anchor, target_anchor):
        """Write config.json for a regular node→node edge."""
        if not (self.canvas.parent_window and target_name in self.canvas.parent_window.nodes_data):
            return
        target_info = self.canvas.parent_window.nodes_data[target_name]
        source_data = self.canvas.parent_window.nodes_data.get(source_name, {})
        source_path = source_data.get("path", "")
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
            if source_name in self.canvas.parent_window.nodes_data:
                source_info = self.canvas.parent_window.nodes_data[source_name]
                source_config = source_info.get("config", {})
                source_config.setdefault("out_connections", {})
                tgt_port = (
                    target_anchor.port_name if (target_anchor and hasattr(target_anchor, "port_name")) else "default"
                )
                source_config["out_connections"][source_port_name] = f"{target_name}|{tgt_port}"
                try:
                    sc_path = get_config_path(source_info.get("path", ""))
                    if source_info.get("path"):
                        with open(sc_path, "w", encoding="utf-8") as f:
                            json.dump(source_config, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.error("save upstream out_connections failed: %s", e)

        config_path = get_config_path(target_info["path"])
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(target_config, f, indent=2, ensure_ascii=False)
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

            # Record output routing in _port_routing (not internal node's config.json)
            tgt_port = target_anchor.port_name if (target_anchor and hasattr(target_anchor, "port_name")) else "default"
            manager.set_output_routing(source_name, port_name, None, target_name, tgt_port)
            logger.info("composite→external: _port_routing output[%s] → %s|%s", port_name, target_name, tgt_port)

        elif is_composite_target and not is_composite_source:
            # External source node → composite input port
            port_name = getattr(target_anchor, "port_name", "") or "default"
            internal_name = manager._find_internal_by_port(target_name, port_name, "input")
            if not internal_name or internal_name not in nodes_data:
                logger.warning(
                    "create_edge: composite input port %s/%s not mapped to internal node "
                    "(composite=%s, available input_ports=%s)",
                    target_name,
                    port_name,
                    manager._composites.get(target_name, {}).get("input_ports", []),
                )
                return
            source_data = nodes_data.get(source_name, {})
            source_path = source_data.get("path", "")
            if not source_path:
                logger.warning("create_edge: source %s has no path, composite config skipped", source_name)
                return
            source_output_path = str((Path(source_path) / "output.json").resolve())

            # Record input routing in _port_routing (NOT internal node's listen_upper_file)
            # This prevents the composite's input port from disappearing due to
            # _identify_ports detecting a non-empty listen_upper_file.
            manager.set_input_routing(target_name, port_name, source_output_path)
            logger.info("external→composite: _port_routing input[%s] ← %s", port_name, source_output_path)

            # Also update source node's out_connections
            spn = source_anchor.port_name if (source_anchor and hasattr(source_anchor, "port_name")) else "default"
            source_config = source_data.get("config", {})
            source_config.setdefault("out_connections", {})
            source_config["out_connections"][spn] = f"{internal_name}|{port_name}"
            try:
                sc_path = get_config_path(source_path)
                with open(sc_path, "w", encoding="utf-8") as f:
                    json.dump(source_config, f, indent=2, ensure_ascii=False)
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
            # Use _port_routing exclusively — no internal node config.json writes
            src_port_name = getattr(source_anchor, "port_name", "") or "default"
            tgt_port_name = getattr(target_anchor, "port_name", "") or "default"

            src_internal = manager._find_internal_by_port(source_name, src_port_name, "output")
            tgt_internal = manager._find_internal_by_port(target_name, tgt_port_name, "input")

            if not src_internal or src_internal not in nodes_data:
                logger.warning(
                    "create_edge: composite→composite source port %s/%s not mapped", source_name, src_port_name
                )
                return
            if not tgt_internal or tgt_internal not in nodes_data:
                logger.warning(
                    "create_edge: composite→composite target port %s/%s not mapped", target_name, tgt_port_name
                )
                return

            src_internal_info = nodes_data[src_internal]
            src_path = src_internal_info.get("path", "")
            if not src_path:
                logger.warning("create_edge: composite→composite missing source path for %s", src_internal)
                return

            src_output_path = str((Path(src_path) / "output.json").resolve())

            # Record output routing: source composite output port → target internal node
            manager.set_output_routing(source_name, src_port_name, target_name, tgt_internal, tgt_port_name)

            # Record input routing: target composite input port ← source output.json
            manager.set_input_routing(target_name, tgt_port_name, src_output_path)

            logger.info(
                "composite→composite: _port_routing %s output[%s] → %s input[%s]",
                source_name,
                src_port_name,
                target_name,
                tgt_port_name,
            )

    def remove_edge(self, edge):
        """移除连线（支持多输入/输出端口）"""
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

            # ── Clean config.json for composite-involved edges ──
            is_comp_src = source_name.startswith("composite_") if source_name else False
            is_comp_tgt = target_name.startswith("composite_") if target_name else False
            manager = getattr(self.canvas, "_composite_manager", None)
            nodes_data = self.canvas.parent_window.nodes_data if self.canvas.parent_window else {}

            if is_comp_src and not is_comp_tgt:
                # Composite output → external: clear _port_routing
                if manager and edge.start_anchor:
                    port_name = getattr(edge.start_anchor, "port_name", "")
                    if port_name:
                        manager.clear_output_routing(source_name, port_name)
                        logger.info("remove composite→external: cleared _port_routing output[%s]", port_name)
                # Also clean external target (normal path below)
                if target_name and target_name in nodes_data:
                    self._clean_target_config(nodes_data, target_name, edge)

            elif is_comp_tgt and not is_comp_src:
                # External → composite input: clear _port_routing
                if manager and edge.end_anchor:
                    port_name = getattr(edge.end_anchor, "port_name", "")
                    if port_name:
                        manager.clear_input_routing(target_name, port_name)
                        logger.info("remove external→composite: cleared _port_routing input[%s]", port_name)
                # Also clean external source's out_connections (normal path below)
                if source_name and source_name in nodes_data:
                    self._clean_source_out_connections(nodes_data, source_name, edge)

            elif is_comp_src and is_comp_tgt:
                # Composite → composite: clear both _port_routing entries
                if manager:
                    src_port = getattr(edge.start_anchor, "port_name", "")
                    tgt_port = getattr(edge.end_anchor, "port_name", "")
                    if src_port:
                        manager.clear_output_routing(source_name, src_port)
                    if tgt_port:
                        manager.clear_input_routing(target_name, tgt_port)
                    logger.info(
                        "remove composite→composite: cleared _port_routing %s output[%s] and %s input[%s]",
                        source_name,
                        src_port,
                        target_name,
                        tgt_port,
                    )

            elif not is_comp_src and not is_comp_tgt:
                # Normal node→node edge
                if target_name and target_name in nodes_data:
                    self._clean_target_config(nodes_data, target_name, edge)
                if source_name and source_name in nodes_data:
                    self._clean_source_out_connections(nodes_data, source_name, edge)

            edge.remove_from_scene()
            self.canvas.edges.remove(edge)

            if self.canvas.parent_window and self.canvas.parent_window.current_project_path:
                self.canvas._save_timer.stop()
                self.canvas._save_timer.start(500)

    def _clean_target_config(self, nodes_data, target_name, edge):
        """Clear listen_upper_file / port_mappings for a target node on edge removal."""
        target_info = nodes_data[target_name]
        target_config = target_info["config"]

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

        config_path = get_config_path(target_info["path"])
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(target_config, f, indent=2, ensure_ascii=False)
            logger.info("已清空 %s 的监听配置及端口映射", target_name)
        except Exception as e:
            logger.error("保存配置失败: %s", e)

    def _clean_source_out_connections(self, nodes_data, source_name, edge):
        """Clear out_connections entry for a source node on edge removal."""
        source_info = nodes_data[source_name]
        source_config = source_info.get("config", {})
        if "out_connections" in source_config and edge.start_anchor and hasattr(edge.start_anchor, "port_name"):
            sp = edge.start_anchor.port_name
            if sp in source_config["out_connections"]:
                del source_config["out_connections"][sp]
            try:
                sc_path = get_config_path(source_info["path"])
                with open(sc_path, "w", encoding="utf-8") as f:
                    json.dump(source_config, f, indent=2, ensure_ascii=False)
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
