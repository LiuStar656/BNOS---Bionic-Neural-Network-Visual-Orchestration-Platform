"""
颜色设置（组合类）— 画布/网格/节点/连线的颜色管理
"""
import os
import json
from PySide6.QtWidgets import QColorDialog
from PySide6.QtGui import QColor, QPen, QBrush
from ui.core.logger import logger


class CanvasColors:
    """画布颜色设置（组合类，通过 self.canvas 访问画布上下文）"""

    def __init__(self, canvas):
        self.canvas = canvas

    # —— 颜色对话框方法 ——

    def change_canvas_background_color(self):
        current = QColor(self.canvas.canvas_bg_color)
        color = QColorDialog.getColor(current, self.canvas, "选择画布背景颜色")
        if color.isValid():
            self.canvas.canvas_bg_color = color.name()
            self.canvas.setBackgroundBrush(QColor(self.canvas.canvas_bg_color))
            self.canvas.repaint()
            self._save_color_settings()
            logger.info("画布背景色已更改为: %s", self.canvas.canvas_bg_color)

    def change_grid_color(self):
        current = QColor(self.canvas.grid_color)
        color = QColorDialog.getColor(current, self.canvas, "选择网格线颜色")
        if color.isValid():
            self.canvas.grid_color = color.name()
            self.canvas.viewport().update()
            self._save_color_settings()
            logger.info("网格线颜色已更改为: %s", self.canvas.grid_color)

    def change_edge_color(self):
        current = QColor(self.canvas.edge_color)
        color = QColorDialog.getColor(current, self.canvas, "选择连线颜色")
        if color.isValid():
            self.canvas.edge_color = color.name()
            for edge in self.canvas.edges:
                edge.update_edge_style()
            self._save_color_settings()
            logger.info("连线颜色已更改为: %s", self.canvas.edge_color)

    def change_node_background_color(self, node_item):
        current = QColor(self.canvas.node_bg_color)
        color = QColorDialog.getColor(current, self.canvas, f"修改节点 '{node_item.node_name}' 的背景颜色")
        if color.isValid():
            node_item.setBrush(QBrush(color))
            if self.canvas.parent_window and node_item.node_name in self.canvas.parent_window.nodes_data:
                info = self.canvas.parent_window.nodes_data[node_item.node_name]
                info['config']['custom_bg_color'] = color.name()
                self._save_node_config(info)
            logger.info("节点背景色已更改为: %s", color.name())

    def change_node_border_color(self, node_item):
        current = QColor(self.canvas.node_border_color)
        color = QColorDialog.getColor(current, self.canvas, f"修改节点 '{node_item.node_name}' 的边框颜色")
        if color.isValid():
            node_item.setPen(QPen(color, 2))
            if self.canvas.parent_window and node_item.node_name in self.canvas.parent_window.nodes_data:
                info = self.canvas.parent_window.nodes_data[node_item.node_name]
                info['config']['custom_border_color'] = color.name()
                self._save_node_config(info)
            logger.info("节点边框色已更改为: %s", color.name())

    def change_node_text_color(self, node_item):
        current = QColor(self.canvas.node_text_color)
        color = QColorDialog.getColor(current, self.canvas, f"修改节点 '{node_item.node_name}' 的文字颜色")
        if color.isValid():
            node_item.name_text.setDefaultTextColor(color)
            if self.canvas.parent_window and node_item.node_name in self.canvas.parent_window.nodes_data:
                info = self.canvas.parent_window.nodes_data[node_item.node_name]
                info['config']['custom_text_color'] = color.name()
                self._save_node_config(info)
            logger.info("节点文字色已更改为: %s", color.name())

    # —— 持久化方法 ——

    @staticmethod
    def _save_node_config(node_info):
        """保存单个节点的 config.json（静态工具方法）"""
        try:
            path = os.path.join(node_info['path'], "config.json")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(node_info['config'], f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.info("保存节点配置失败: %s", e)

    def _save_color_settings(self):
        """保存全局颜色设置到项目目录的 color_settings.json"""
        if not self.canvas.parent_window or not self.canvas.parent_window.current_project_path:
            return
        data = {
            'canvas_bg_color': self.canvas.canvas_bg_color,
            'grid_color': self.canvas.grid_color,
            'grid_opacity': self.canvas.grid_opacity,
            'edge_color': self.canvas.edge_color,
            'edge_width': self.canvas.edge_width,
            'node_bg_color': self.canvas.node_bg_color,
            'node_border_color': self.canvas.node_border_color,
            'node_text_color': self.canvas.node_text_color,
            'node_selected_color': self.canvas.node_selected_color,
            'input_anchor_color': self.canvas.input_anchor_color,
            'output_anchor_color': self.canvas.output_anchor_color,
            'toast_info_color': getattr(self.canvas, 'toast_info_color', '#323232'),
            'toast_success_color': getattr(self.canvas, 'toast_success_color', '#4caf50'),
            'toast_warning_color': getattr(self.canvas, 'toast_warning_color', '#ff9800'),
            'toast_error_color': getattr(self.canvas, 'toast_error_color', '#f44336'),
            'toast_text_color': getattr(self.canvas, 'toast_text_color', '#ffffff'),
            'toast_opacity': getattr(self.canvas, 'toast_opacity', 0.9),
            'dock_floating_border_color': getattr(self.canvas, 'dock_floating_border_color', '#007acc'),
            'dock_floating_border_inactive': getattr(self.canvas, 'dock_floating_border_inactive', '#3c3c3c'),
        }
        path = os.path.join(self.canvas.parent_window.current_project_path, "color_settings.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info("颜色设置已保存到: %s", path)
        except Exception as e:
            logger.info("保存颜色设置失败: %s", e)

    def _load_color_settings(self, project_path):
        """从项目目录加载颜色设置"""
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
        """应用 dict 形式的颜色设置（常用于加载 color_settings.json 后）"""
        self.canvas.canvas_bg_color = settings.get('canvas_bg_color', self.canvas.canvas_bg_color)
        self.canvas.grid_color = settings.get('grid_color', self.canvas.grid_color)
        self.canvas.grid_opacity = settings.get('grid_opacity', self.canvas.grid_opacity)
        self.canvas.node_bg_color = settings.get('node_bg_color', self.canvas.node_bg_color)
        self.canvas.node_border_color = settings.get('node_border_color', self.canvas.node_border_color)
        self.canvas.node_text_color = settings.get('node_text_color', self.canvas.node_text_color)
        self.canvas.node_selected_color = settings.get('node_selected_color', self.canvas.node_selected_color)
        self.canvas.input_anchor_color = settings.get('input_anchor_color', self.canvas.input_anchor_color)
        self.canvas.output_anchor_color = settings.get('output_anchor_color', self.canvas.output_anchor_color)
        self.canvas.edge_color = settings.get('edge_color', self.canvas.edge_color)
        self.canvas.edge_width = settings.get('edge_width', self.canvas.edge_width)

        # Toast 通知设置
        self.canvas.toast_info_color = settings.get('toast_info_color', '#323232')
        self.canvas.toast_success_color = settings.get('toast_success_color', '#4caf50')
        self.canvas.toast_warning_color = settings.get('toast_warning_color', '#ff9800')
        self.canvas.toast_error_color = settings.get('toast_error_color', '#f44336')
        self.canvas.toast_text_color = settings.get('toast_text_color', '#ffffff')
        self.canvas.toast_opacity = settings.get('toast_opacity', 0.9)

        # ── Dock 漂浮边框颜色 ──
        dock_active = settings.get('dock_floating_border_color', '#007acc')
        dock_inactive = settings.get('dock_floating_border_inactive', '#3c3c3c')
        self.canvas.dock_floating_border_color = dock_active
        self.canvas.dock_floating_border_inactive = dock_inactive

        from ui.core.bnos_dock import set_dock_floating_colors as set_bnos_dock_colors
        from ui.core.dock_manager import set_dock_floating_colors as set_mgr_dock_colors
        set_bnos_dock_colors(dock_active, dock_inactive)
        set_mgr_dock_colors(dock_active, dock_inactive)

        # 更新 Toast 全局配置
        from ui.core.toast.toast_notification import set_toast_config
        set_toast_config({
            'info_color': self.canvas.toast_info_color,
            'success_color': self.canvas.toast_success_color,
            'warning_color': self.canvas.toast_warning_color,
            'error_color': self.canvas.toast_error_color,
            'text_color': self.canvas.toast_text_color,
            'opacity': self.canvas.toast_opacity,
        })

        bg = QColor(self.canvas.node_bg_color)
        border_pen = QPen(QColor(self.canvas.node_border_color), 2)
        text_c = QColor(self.canvas.node_text_color)
        sel_c = QColor(self.canvas.node_selected_color)

        for node in self.canvas.nodes.values():
            node.setBrush(QBrush(bg))
            node.setPen(border_pen)
            if hasattr(node, 'name_text'):
                node.name_text.setDefaultTextColor(text_c)
            if hasattr(node, '_selection_ring') and node._selection_ring:
                node._selection_ring.setPen(QPen(sel_c, 3))

        for edge in self.canvas.edges:
            edge.update_edge_style()

        self.canvas.setBackgroundBrush(QColor(self.canvas.canvas_bg_color))
        self.canvas.repaint()
        logger.info("apply_color_settings: bg=%s", self.canvas.canvas_bg_color)
