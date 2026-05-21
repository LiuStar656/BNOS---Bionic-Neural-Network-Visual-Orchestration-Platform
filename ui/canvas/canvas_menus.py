"""
画布右键菜单 Mixin — 从 canvas_view.py 提取
"""
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from ui.canvas.items.node_item import NodeItem


class CanvasMenusMixin:
    """右键菜单 Mixin"""

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        
        if len(self.box_selected_nodes) > 0:
            menu = QMenu(self)
            count = len(self.box_selected_nodes)
            menu.addAction(f"已选 {count} 个节点").setEnabled(False)
            menu.addSeparator()
            a = menu.addAction(f"启动已选节点 ({count})"); a.triggered.connect(self.batch_start_selected_nodes)
            a = menu.addAction(f"停止已选节点 ({count})"); a.triggered.connect(self.batch_stop_selected_nodes)
            menu.addSeparator()
            a = menu.addAction(f"移除已选节点 ({count})"); a.triggered.connect(self.batch_remove_nodes_from_canvas)
            menu.addSeparator()
            a = menu.addAction("清除连线配置"); a.triggered.connect(self.batch_clear_listen_config)
            menu.addSeparator()
            a = menu.addAction("清除选择"); a.triggered.connect(self.clear_box_selection)
            menu.exec(event.globalPos())
            return

        if isinstance(item, NodeItem):
            node_item = item
            menu = QMenu(self)
            node_name = node_item.node_name
            if self.parent_window and node_name in self.parent_window.nodes_data:
                if self.parent_window.nodes_data[node_name].get('status') == 'running':
                    a = menu.addAction("停止节点"); a.triggered.connect(lambda n=node_name: self.stop_single_node(n))
                else:
                    a = menu.addAction("启动节点"); a.triggered.connect(lambda n=node_name: self.start_single_node(n))
                menu.addSeparator()
            a = menu.addAction("从画布删除"); a.triggered.connect(lambda n=node_name: self.remove_node_with_cleanup(n))
            menu.addSeparator()
            a = menu.addAction("节点配置"); a.triggered.connect(lambda n=node_name: self.open_node_config(n))
            a = menu.addAction("展开节点"); a.triggered.connect(lambda n=node_name: self.on_node_expand_requested(n))
            menu.addSeparator()
            color_menu = menu.addMenu("节点颜色")
            a = color_menu.addAction("背景颜色"); a.triggered.connect(lambda nd=node_item: self.change_node_background_color(nd))
            a = color_menu.addAction("边框颜色"); a.triggered.connect(lambda nd=node_item: self.change_node_border_color(nd))
            a = color_menu.addAction("文字颜色"); a.triggered.connect(lambda nd=node_item: self.change_node_text_color(nd))
            menu.exec(event.globalPos())
        else:
            menu = QMenu(self)
            new_menu = menu.addMenu("新建节点")
            for lang in ["Python", "Node.js", "Go", "Java", "C++", "Rust", "Shell"]:
                a = QAction(lang, self)
                a.triggered.connect(lambda checked=None, language=lang: self.parent_window.create_new_node_with_language(language))
                new_menu.addAction(a)
            menu.addSeparator()
            a = menu.addAction("节点监测"); a.triggered.connect(lambda: self.parent_window.show_node_monitor() if self.parent_window else None)
            menu.addSeparator()
            a = menu.addAction("清空连线"); a.triggered.connect(self.clear_edges)
            menu.addSeparator()
            a = menu.addAction("重置视图"); a.triggered.connect(self.reset_view)
            menu.addSeparator()
            color_menu = menu.addMenu("画布颜色")
            a = color_menu.addAction("背景颜色"); a.triggered.connect(self.change_canvas_background_color)
            a = color_menu.addAction("网格颜色"); a.triggered.connect(self.change_grid_color)
            a = color_menu.addAction("连线颜色"); a.triggered.connect(self.change_edge_color)
            menu.exec(event.globalPos())
