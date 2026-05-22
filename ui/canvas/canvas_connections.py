"""
连线条统 Mixin — 连线创建/完成/取消/移除/清空生命周期管理
"""
import os
import json
from PyQt6.QtWidgets import QGraphicsPathItem, QMessageBox
from ui.core.utils.dialog_utils import themed_message
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor, QPainterPath
from ui.core.logger import logger
from ui.core.i18n import t
from ui.canvas.items.edge_item import EdgeItem


class CanvasConnectionsMixin:
    """连线生命周期管理（Mixin 注入到 NodeCanvas）"""

    def _start_connection_by_name(self, node_name):
        """按节点名称开始连线（供右键菜单调用）"""
        if node_name not in self.nodes:
            return
        self.start_connection_from_output(self.nodes[node_name])

    def start_connection_from_output(self, source_node):
        """从输出锚点开始连线"""
        self.is_connecting = True
        self.connect_source = source_node
        logger.debug("连线模式启动: source=%s, is_connecting=%s", source_node.node_name, self.is_connecting)

        self.viewport().setCursor(Qt.CursorShape.CrossCursor)

        self.temp_edge = QGraphicsPathItem()
        self.temp_edge.setZValue(2)
        self.temp_edge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        pen = QPen(QColor("#4A90E2"), 2, Qt.PenStyle.DashLine)
        self.temp_edge.setPen(pen)
        self.scene.addItem(self.temp_edge)

        cursor_pos = self.mapFromGlobal(self.cursor().pos())
        scene_pos = self.mapToScene(cursor_pos)
        start = source_node.output_anchor.sceneBoundingRect().center()

        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(scene_pos)
        self.temp_edge.setPath(path)

    def complete_connection_to_input(self, target_node):
        """完成连线到输入锚点"""
        logger.debug("complete_connection_to_input: source=%s, target=%s, is_connecting=%s",
                     self.connect_source.node_name if self.connect_source else None,
                     target_node.node_name, self.is_connecting)
        if self.connect_source and self.connect_source != target_node:
            self.create_edge(self.connect_source, target_node)

        if self.temp_edge:
            self.scene.removeItem(self.temp_edge)
            self.temp_edge = None

        self.is_connecting = False
        self.connect_source = None
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def create_edge(self, source_node, target_node):
        """创建连线并配置上下游关系"""
        for edge in self.edges:
            if edge.start_node == source_node and edge.end_node == target_node:
                themed_message(self, t("k_title_info"), t("k_canvas_edge_exists"), "info")
                return

        source_name = None
        target_name = None
        for name, node in self.nodes.items():
            if node == source_node:
                source_name = name
            if node == target_node:
                target_name = name

        if not source_name or not target_name:
            return

        if self.parent_window and target_name in self.parent_window.nodes_data:
            target_info = self.parent_window.nodes_data[target_name]
            source_path = self.parent_window.nodes_data[source_name]['path']
            source_output_path = os.path.abspath(os.path.join(source_path, "output.json"))

            target_config = target_info['config']
            target_config['listen_upper_file'] = source_output_path

            config_path = os.path.join(target_info['path'], "config.json")
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(target_config, f, indent=2, ensure_ascii=False)
                logger.info("已配置 %s 监听 %s 的输出", target_name, source_name)
                logger.debug("   listen_upper_file: %s", source_output_path)
            except Exception as e:
                logger.error("保存配置失败: %s", e)

        edge = EdgeItem(source_node, target_node, self)
        self.scene.addItem(edge)
        self.edges.append(edge)
        edge.update_path()

        logger.info("创建连线: %s -> %s", source_name, target_name)

        if self.parent_window and self.parent_window.current_project_path:
            self._save_timer.stop()
            self._save_timer.start(500)

    def remove_edge(self, edge):
        """移除连线"""
        if edge in self.edges:
            target_name = None
            for name, node in self.nodes.items():
                if node == edge.end_node:
                    target_name = name
                    break

            if target_name and self.parent_window and target_name in self.parent_window.nodes_data:
                target_info = self.parent_window.nodes_data[target_name]
                target_config = target_info['config']
                target_config['listen_upper_file'] = ""

                config_path = os.path.join(target_info['path'], "config.json")
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(target_config, f, indent=2, ensure_ascii=False)
                    logger.info("已清空 %s 的监听配置", target_name)
                except Exception as e:
                    logger.error("保存配置失败: %s", e)

            edge.remove_from_scene()
            self.edges.remove(edge)

            if self.parent_window and self.parent_window.current_project_path:
                self._save_timer.stop()
                self._save_timer.start(500)

    def cancel_connection(self):
        """取消连线"""
        if self.temp_edge:
            self.scene.removeItem(self.temp_edge)
            self.temp_edge = None

        self.is_connecting = False
        self.connect_source = None
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def clear_edges(self):
        """清空所有连线"""
        for edge in self.edges[:]:
            self.remove_edge(edge)
        self.edges.clear()
