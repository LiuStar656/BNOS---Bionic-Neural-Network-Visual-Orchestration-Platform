"""
画布右键菜单 Mixin
"""
from functools import partial
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsItem
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.node_style import STYLES


class CanvasMenusMixin:
    """右键菜单 Mixin"""

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        probe = item
        while probe is not None:
            if isinstance(probe, NodeItem):
                item = probe
                break
            probe = probe.parentItem()

        if len(self.box_selected_nodes) > 1:
            menu = QMenu(self)
            count = len(self.box_selected_nodes)
            menu.addAction(f"已选 {count} 个节点").setEnabled(False)
            menu.addSeparator()
            a = QAction(f"启动已选节点 ({count})", menu); a.triggered.connect(self.batch_start_selected_nodes); menu.addAction(a)
            a = QAction(f"停止已选节点 ({count})", menu); a.triggered.connect(self.batch_stop_selected_nodes); menu.addAction(a)
            menu.addSeparator()
            a = QAction(f"移除已选节点 ({count})", menu); a.triggered.connect(self.batch_remove_nodes_from_canvas); menu.addAction(a)
            menu.addSeparator()
            a = QAction("清除连线配置", menu); a.triggered.connect(self.batch_clear_listen_config); menu.addAction(a)
            menu.addSeparator()
            a = QAction("清除选择", menu); a.triggered.connect(self.clear_box_selection); menu.addAction(a)
            menu.exec(event.globalPos())
            return

        if isinstance(item, NodeItem):
            node_item = item
            menu = QMenu(self)
            node_name = node_item.node_name

            if self.parent_window and node_name in self.parent_window.nodes_data:
                if self.parent_window.nodes_data[node_name].get('status') == 'running':
                    a = QAction("停止节点", menu); a.triggered.connect(partial(self.stop_single_node, node_name)); menu.addAction(a)
                else:
                    a = QAction("启动节点", menu); a.triggered.connect(partial(self.start_single_node, node_name)); menu.addAction(a)
                menu.addSeparator()

            a = QAction("开始连线", menu); a.triggered.connect(partial(self._start_connection_by_name, node_name)); menu.addAction(a)
            menu.addSeparator()

            a = QAction("节点配置", menu); a.triggered.connect(partial(self.open_node_config, node_name)); menu.addAction(a)
            a = QAction("展开节点", menu); a.triggered.connect(partial(self.on_node_expand_requested, node_name)); menu.addAction(a)
            menu.addSeparator()

            # 样式切换
            style_menu = menu.addMenu("样式")
            for key, cls in STYLES.items():
                st = cls()
                a = QAction(st.style_name, style_menu); a.triggered.connect(partial(self._switch_node_style, key, node_item)); style_menu.addAction(a)

            menu.addSeparator()

            color_menu = menu.addMenu("节点颜色")
            a = QAction("背景颜色", color_menu); a.triggered.connect(partial(self.change_node_background_color, node_item)); color_menu.addAction(a)
            a = QAction("边框颜色", color_menu); a.triggered.connect(partial(self.change_node_border_color, node_item)); color_menu.addAction(a)
            a = QAction("文字颜色", color_menu); a.triggered.connect(partial(self.change_node_text_color, node_item)); color_menu.addAction(a)

            menu.addSeparator()
            a = QAction("从画布删除", menu); a.triggered.connect(partial(self.remove_node_with_cleanup, node_name)); menu.addAction(a)
            menu.exec(event.globalPos())
        else:
            menu = QMenu(self)
            new_menu = menu.addMenu("新建节点")
            for lang in ["Python", "Node.js", "Go", "Java", "C++", "Rust", "Shell"]:
                a = QAction(lang, self)
                a.triggered.connect(partial(self.parent_window.create_new_node_with_language, lang))
                new_menu.addAction(a)
            menu.addSeparator()
            a = QAction("节点监测", menu); a.triggered.connect(lambda: self.parent_window.show_node_monitor()); menu.addAction(a)
            menu.addSeparator()
            a = QAction("清空连线", menu); a.triggered.connect(self.clear_edges); menu.addAction(a)
            menu.addSeparator()
            a = QAction("重置视图", menu); a.triggered.connect(self.reset_view); menu.addAction(a)
            menu.addSeparator()
            color_menu = menu.addMenu("画布颜色")
            a = QAction("背景颜色", color_menu); a.triggered.connect(self.change_canvas_background_color); color_menu.addAction(a)
            a = QAction("网格颜色", color_menu); a.triggered.connect(self.change_grid_color); color_menu.addAction(a)
            a = QAction("连线颜色", color_menu); a.triggered.connect(self.change_edge_color); color_menu.addAction(a)
            menu.exec(event.globalPos())

    def _switch_node_style(self, style_key, node_item):
        from ui.canvas.items.node_style import STYLES
        cls = STYLES.get(style_key)
        if not cls:
            return
        new_style = cls()
        node_item._style = new_style
        new_style.node_width = node_item.rect().width()
        new_style.node_height = node_item.rect().height()
        node_item.setCacheMode(QGraphicsItem.CacheMode.NoCache)
        new_style.apply(node_item)
        new_style.apply_status(node_item, node_item.status)
        node_item._update_selection_ring(node_item.isSelected())
        node_item.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        node_item.update()
        # 触发自动保存，持久化样式变更
        if hasattr(self, '_save_timer'):
            self._save_timer.stop()
            self._save_timer.start(500)
