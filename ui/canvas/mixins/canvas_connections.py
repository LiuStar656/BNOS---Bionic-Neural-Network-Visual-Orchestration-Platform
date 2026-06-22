"""
连线管理（组合类）— 负责连线创建/完成/取消/移除/清空的完整生命周期
"""
import os
import json
from PySide6.QtWidgets import QGraphicsPathItem
from ui.core.utils.dialog_utils import themed_message
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QColor, QPainterPath
from ui.core.logger import logger
from ui.core.i18n import t
from ui.canvas.items.edge_item import EdgeItem, TempEdgeItem


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
        source_anchor = getattr(self.canvas, '_connect_source_anchor', None)
        logger.debug("complete_connection_to_input: source=%s, target=%s, src_anchor=%s, target_anchor=%s, is_connecting=%s",
                     self.canvas.connect_source.node_name if self.canvas.connect_source else None,
                     target_node.node_name,
                     getattr(source_anchor, 'port_name', None),
                     clicked_anchor.port_name if clicked_anchor else None,
                     self.canvas.is_connecting)
        if self.canvas.connect_source and self.canvas.connect_source != target_node:
            self.create_edge(
                self.canvas.connect_source, target_node,
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
        if target_anchor and hasattr(target_anchor, 'port_name'):
            for edge in self.canvas.edges:
                if edge.start_node == source_node and edge.end_node == target_node:
                    if hasattr(edge, 'end_anchor') and edge.end_anchor:
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

        if self.canvas.parent_window and target_name in self.canvas.parent_window.nodes_data:
            target_info = self.canvas.parent_window.nodes_data[target_name]
            source_path = self.canvas.parent_window.nodes_data[source_name]['path']
            source_output_path = os.path.abspath(os.path.join(source_path, "output.json"))

            target_config = target_info['config']

            if target_anchor and hasattr(target_anchor, 'port_name'):
                port_name = target_anchor.port_name
                if port_name and port_name != "default":
                    if 'port_mappings' not in target_config:
                        target_config['port_mappings'] = {}
                    target_config['port_mappings'][port_name] = source_output_path
                    logger.info("create_edge: 配置端口映射 %s -> %s", port_name, source_output_path)
                else:
                    target_config['listen_upper_file'] = source_output_path
                    logger.info("create_edge: listen_upper_file=%s", source_output_path)
            else:
                target_config['listen_upper_file'] = source_output_path
                logger.info("create_edge: 使用旧版单锚点逻辑，listen_upper_file=%s", source_output_path)

            if source_anchor and hasattr(source_anchor, 'port_name'):
                source_port_name = source_anchor.port_name
                if source_name in self.canvas.parent_window.nodes_data:
                    source_info = self.canvas.parent_window.nodes_data[source_name]
                    source_config = source_info.get('config', {})
                    if 'out_connections' not in source_config:
                        source_config['out_connections'] = {}
                    source_config['out_connections'][source_port_name] = f"{target_name}|{target_anchor.port_name if target_anchor and hasattr(target_anchor, 'port_name') else 'default'}"
                    try:
                        sc_path = os.path.join(source_info['path'], "config.json")
                        with open(sc_path, 'w', encoding='utf-8') as f:
                            json.dump(source_config, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        logger.error("保存上游节点出向连接配置失败: %s", e)

            config_path = os.path.join(target_info['path'], "config.json")
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(target_config, f, indent=2, ensure_ascii=False)
                logger.info("已配置 %s 监听 %s 的输出", target_name, source_name)
                logger.debug("   listen_upper_file: %s", source_output_path)
            except Exception as e:
                logger.error("保存配置失败: %s", e)

        tgt_port_name = target_anchor.port_name if (target_anchor and hasattr(target_anchor, 'port_name')) else None
        src_port_name = source_anchor.port_name if (source_anchor and hasattr(source_anchor, 'port_name')) else None

        edge = EdgeItem(source_node, target_node, self.canvas, target_anchor, source_anchor,
                        target_port_name=tgt_port_name, source_port_name=src_port_name)
        self.canvas.scene.addItem(edge)
        self.canvas.edges.append(edge)
        edge.update_path()

        edge_info_source = f" (out_port: {source_anchor.port_name})" if source_anchor and hasattr(source_anchor, 'port_name') else ""
        edge_info_target = f" (in_port: {target_anchor.port_name})" if target_anchor and hasattr(target_anchor, 'port_name') else ""
        logger.info("创建连线: %s%s -> %s%s", source_name, edge_info_source, target_name, edge_info_target)

        if self.canvas.parent_window and self.canvas.parent_window.current_project_path:
            self.canvas._save_timer.stop()
            self.canvas._save_timer.start(500)

        # 自动录制命令
        self.canvas._record_create_edge(source_name, target_name)

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
                target_port = getattr(edge, '_desired_target_port_name', None)
                source_port = getattr(edge, '_desired_source_port_name', None)
                self.canvas._record_delete_edge(source_name, target_name, target_port, source_port)

            if edge not in self.canvas.edges:
                return

            if target_name and self.canvas.parent_window and target_name in self.canvas.parent_window.nodes_data:
                target_info = self.canvas.parent_window.nodes_data[target_name]
                target_config = target_info['config']

                if edge.end_anchor and hasattr(edge.end_anchor, 'port_name'):
                    port_name = edge.end_anchor.port_name
                    if port_name and port_name != "default":
                        if 'port_mappings' in target_config and port_name in target_config['port_mappings']:
                            del target_config['port_mappings'][port_name]
                            logger.debug("已移除端口映射: %s", port_name)
                    else:
                        target_config['listen_upper_file'] = ""
                        logger.debug("已清空 listen_upper_file")
                else:
                    target_config['listen_upper_file'] = ""

                config_path = os.path.join(target_info['path'], "config.json")
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(target_config, f, indent=2, ensure_ascii=False)
                    logger.info("已清空 %s 的监听配置及端口映射", target_name)
                except Exception as e:
                    logger.error("保存配置失败: %s", e)

            if source_name and self.canvas.parent_window and source_name in self.canvas.parent_window.nodes_data:
                source_info = self.canvas.parent_window.nodes_data[source_name]
                source_config = source_info.get('config', {})
                if 'out_connections' in source_config and edge.start_anchor and hasattr(edge.start_anchor, 'port_name'):
                    sp = edge.start_anchor.port_name
                    if sp in source_config['out_connections']:
                        del source_config['out_connections'][sp]
                    try:
                        sc_path = os.path.join(source_info['path'], "config.json")
                        with open(sc_path, 'w', encoding='utf-8') as f:
                            json.dump(source_config, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        logger.error("保存上游节点出向连接配置失败: %s", e)

            edge.remove_from_scene()
            self.canvas.edges.remove(edge)

            if self.canvas.parent_window and self.canvas.parent_window.current_project_path:
                self.canvas._save_timer.stop()
                self.canvas._save_timer.start(500)

    def cancel_connection(self):
        """取消连线"""
        if self.canvas.temp_edge:
            self.canvas.scene.removeItem(self.canvas.temp_edge)
            self.canvas.temp_edge = None

        self.canvas.is_connecting = False
        self.canvas.connect_source = None
        self.canvas.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def clear_edges(self):
        """清空所有连线 — 遍历所有锚点（包括多输入锚点）"""
        for edge in self.canvas.edges[:]:
            self.remove_edge(edge)
        self.canvas.edges.clear()

        # 清空所有节点所有锚点的连线引用
        for node in self.canvas.nodes.values():
            if hasattr(node, 'all_input_anchors') and callable(getattr(node, 'all_input_anchors', None)):
                for anchor in node.all_input_anchors():
                    if anchor is not None:
                        anchor.clear_edges()
            elif hasattr(node, 'input_anchor'):
                node.input_anchor.clear_edges()
            if hasattr(node, 'all_output_anchors') and callable(getattr(node, 'all_output_anchors', None)):
                for anchor in node.all_output_anchors():
                    if anchor is not None:
                        anchor.clear_edges()
            elif hasattr(node, 'output_anchor'):
                node.output_anchor.clear_edges()
