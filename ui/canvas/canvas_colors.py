"""
画布颜色管理 Mixin — 从 canvas_view.py 提取
"""
import os
import json
from PyQt6.QtWidgets import QColorDialog
from PyQt6.QtGui import QColor, QPen, QBrush
from ui.core.logger import logger


class CanvasColorsMixin:
    """画布颜色设置 Mixin（混入 NodeCanvas）"""

    def change_canvas_background_color(self):
        current = QColor(self.canvas_bg_color)
        color = QColorDialog.getColor(current, self, "选择画布背景颜色")
        if color.isValid():
            self.canvas_bg_color = color.name()
            self.setBackgroundBrush(QColor(self.canvas_bg_color))
            self.viewport().repaint()
            self._save_color_settings()
            logger.info("画布背景色已更改为: %s", self.canvas_bg_color)

    def change_grid_color(self):
        current = QColor(self.grid_color)
        color = QColorDialog.getColor(current, self, "选择网格线颜色")
        if color.isValid():
            self.grid_color = color.name()
            self.viewport().update()
            self._save_color_settings()
            logger.info("网格线颜色已更改为: %s", self.grid_color)

    def change_edge_color(self):
        current = QColor(self.edge_color)
        color = QColorDialog.getColor(current, self, "选择连线颜色")
        if color.isValid():
            self.edge_color = color.name()
            for edge in self.edges:
                edge.update_edge_style()
            self._save_color_settings()
            logger.info("连线颜色已更改为: %s", self.edge_color)

    def change_node_background_color(self, node_item):
        current = QColor(self.node_bg_color)
        color = QColorDialog.getColor(current, self, f"修改节点 '{node_item.node_name}' 的背景颜色")
        if color.isValid():
            node_item.setBrush(QBrush(color))
            if self.parent_window and node_item.node_name in self.parent_window.nodes_data:
                info = self.parent_window.nodes_data[node_item.node_name]
                info['config']['custom_bg_color'] = color.name()
                self._save_node_config(info)
            logger.info("节点背景色已更改为: %s", color.name())

    def change_node_border_color(self, node_item):
        current = QColor(self.node_border_color)
        color = QColorDialog.getColor(current, self, f"修改节点 '{node_item.node_name}' 的边框颜色")
        if color.isValid():
            node_item.setPen(QPen(color, 2))
            if self.parent_window and node_item.node_name in self.parent_window.nodes_data:
                info = self.parent_window.nodes_data[node_item.node_name]
                info['config']['custom_border_color'] = color.name()
                self._save_node_config(info)
            logger.info("节点边框色已更改为: %s", color.name())

    def change_node_text_color(self, node_item):
        current = QColor(self.node_text_color)
        color = QColorDialog.getColor(current, self, f"修改节点 '{node_item.node_name}' 的文字颜色")
        if color.isValid():
            node_item.name_text.setDefaultTextColor(color)
            if self.parent_window and node_item.node_name in self.parent_window.nodes_data:
                info = self.parent_window.nodes_data[node_item.node_name]
                info['config']['custom_text_color'] = color.name()
                self._save_node_config(info)
            logger.info("节点文字色已更改为: %s", color.name())

    @staticmethod
    def _save_node_config(node_info):
        try:
            path = os.path.join(node_info['path'], "config.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(node_info['config'], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.info("保存节点配置失败: %s", e)

    def _save_color_settings(self):
        if not self.parent_window or not self.parent_window.current_project_path:
            return
        data = {
            'canvas_bg_color': self.canvas_bg_color,
            'grid_color': self.grid_color,
            'grid_opacity': self.grid_opacity,
            'edge_color': self.edge_color,
            'edge_width': self.edge_width,
            'node_bg_color': self.node_bg_color,
            'node_border_color': self.node_border_color,
            'node_text_color': self.node_text_color,
            'node_selected_color': self.node_selected_color,
            'input_anchor_color': self.input_anchor_color,
            'output_anchor_color': self.output_anchor_color,
        }
        path = os.path.join(self.parent_window.current_project_path, "color_settings.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("颜色设置已保存到: %s", path)
        except Exception as e:
            logger.info("保存颜色设置失败: %s", e)

    def _load_color_settings(self, project_path):
        if not project_path:
            return
        path = os.path.join(project_path, "color_settings.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            self.apply_color_settings(settings)
            logger.info("颜色设置已从 %s 加载", path)
        except Exception as e:
            logger.info("加载颜色设置失败: %s", e)

    def apply_color_settings(self, settings):
        self.canvas_bg_color = settings.get('canvas_bg_color', self.canvas_bg_color)
        self.grid_color = settings.get('grid_color', self.grid_color)
        self.grid_opacity = settings.get('grid_opacity', self.grid_opacity)
        self.node_bg_color = settings.get('node_bg_color', self.node_bg_color)
        self.node_border_color = settings.get('node_border_color', self.node_border_color)
        self.node_text_color = settings.get('node_text_color', self.node_text_color)
        self.node_selected_color = settings.get('node_selected_color', self.node_selected_color)
        self.input_anchor_color = settings.get('input_anchor_color', self.input_anchor_color)
        self.output_anchor_color = settings.get('output_anchor_color', self.output_anchor_color)
        self.edge_color = settings.get('edge_color', self.edge_color)
        self.edge_width = settings.get('edge_width', self.edge_width)

        # 画布背景 — 强制重设刷子并立即重绘
        self.setBackgroundBrush(QColor(self.canvas_bg_color))
        self.viewport().repaint()

        # 刷新所有现有节点颜色
        bg = QColor(self.node_bg_color)
        border_pen = QPen(QColor(self.node_border_color), 2)
        text_c = QColor(self.node_text_color)
        sel_c = QColor(self.node_selected_color)
        for node in self.nodes.values():
            node.setBrush(QBrush(bg))
            node.setPen(border_pen)
            if hasattr(node, 'name_text'):
                node.name_text.setDefaultTextColor(text_c)
            # 更新选中边框色（如果有_selection_ring）
            if hasattr(node, '_selection_ring') and node._selection_ring:
                node._selection_ring.setPen(QPen(sel_c, 3))

        # 刷新所有现有连线
        for edge in self.edges:
            edge.update_edge_style()

        self.scene.update()
        self.viewport().update()
