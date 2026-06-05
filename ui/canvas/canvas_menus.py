"""
画布右键菜单 Mixin
"""
from functools import partial
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsItem
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.edge_item import EdgeItem
from ui.canvas.items.node_style import STYLES
from ui.core.i18n import t


class CanvasMenusMixin:
    """右键菜单 Mixin"""

    def contextMenuEvent(self, event):
        item = self.itemAt(event.pos())
        probe = item
        while probe is not None:
            if isinstance(probe, NodeItem):
                item = probe
                break
            if isinstance(probe, EdgeItem):
                item = probe
                break
            probe = probe.parentItem()

        # 检查是否有选中的连线（EdgeItem 右键时已自动选中）
        selected_edge = None
        for sel in self.scene.selectedItems():
            if isinstance(sel, EdgeItem):
                selected_edge = sel
                break

        if len(self.box_selected_nodes) > 1:
            menu = QMenu(self)
            count = len(self.box_selected_nodes)
            menu.addAction(f"已选 {count} 个节点").setEnabled(False)
            menu.addSeparator()
            a = QAction(t("_k_batch_start_selected").replace("{count}", str(count)), menu); a.triggered.connect(self.batch_start_selected_nodes); menu.addAction(a)
            a = QAction(t("_k_batch_stop_selected").replace("{count}", str(count)), menu); a.triggered.connect(self.batch_stop_selected_nodes); menu.addAction(a)
            menu.addSeparator()
            a = QAction(t("_k_batch_remove_selected").replace("{count}", str(count)), menu); a.triggered.connect(self.batch_remove_nodes_from_canvas); menu.addAction(a)
            menu.addSeparator()
            a = QAction(t("k_canvas_clear_config"), menu); a.triggered.connect(self.batch_clear_listen_config); menu.addAction(a)
            menu.addSeparator()
            a = QAction(t("k_select_clear"), menu); a.triggered.connect(self.clear_box_selection); menu.addAction(a)
            menu.exec(event.globalPos())
            return

        if isinstance(item, NodeItem):
            node_item = item
            menu = QMenu(self)
            node_name = node_item.node_name

            if self.parent_window and node_name in self.parent_window.nodes_data:
                if self.parent_window.nodes_data[node_name].get('status') in ('running', 'idle'):
                    a = QAction(t("k_node_stop"), menu); a.triggered.connect(partial(self.stop_single_node, node_name)); menu.addAction(a)
                else:
                    a = QAction(t("k_node_start"), menu); a.triggered.connect(partial(self.start_single_node, node_name)); menu.addAction(a)
                menu.addSeparator()

            a = QAction(t("k_canvas_start_connection"), menu); a.triggered.connect(partial(self._start_connection_by_name, node_name)); menu.addAction(a)
            menu.addSeparator()

            a = QAction(t("k_node_config"), menu); a.triggered.connect(partial(self.open_node_config, node_name)); menu.addAction(a)
            a = QAction(t("k_node_expand"), menu); a.triggered.connect(partial(self.on_node_expand_requested, node_name)); menu.addAction(a)
            menu.addSeparator()

            # 样式切换
            style_menu = menu.addMenu(t("k_node_style"))
            for key, cls in STYLES.items():
                st = cls()
                a = QAction(st.style_name, style_menu); a.triggered.connect(partial(self._switch_node_style, key, node_item)); style_menu.addAction(a)

            menu.addSeparator()

            color_menu = menu.addMenu(t("k_node_color"))
            a = QAction(t("k_node_bg_color"), color_menu); a.triggered.connect(partial(self.change_node_background_color, node_item)); color_menu.addAction(a)
            a = QAction(t("k_node_border_color"), color_menu); a.triggered.connect(partial(self.change_node_border_color, node_item)); color_menu.addAction(a)
            a = QAction(t("k_node_text_color"), color_menu); a.triggered.connect(partial(self.change_node_text_color, node_item)); color_menu.addAction(a)

            menu.addSeparator()
            
            # 导出节点
            a = QAction(t("k_export_node"), menu)
            a.triggered.connect(partial(self.export_node_from_canvas, node_name))
            menu.addAction(a)
            
            menu.addSeparator()
            a = QAction(t("k_canvas_remove_from"), menu); a.triggered.connect(partial(self.remove_node_with_cleanup, node_name)); menu.addAction(a)
            menu.exec(event.globalPos())

        elif selected_edge is not None or isinstance(item, EdgeItem):
            # 右键连线菜单
            edge = selected_edge if selected_edge else item
            menu = QMenu(self)

            a = QAction(t("k_canvas_delete_edge"), menu)
            a.triggered.connect(lambda: self.remove_edge(edge))
            menu.addAction(a)

            menu.addSeparator()

            a = QAction(t("k_canvas_change_edge_color"), menu)
            a.triggered.connect(lambda: edge.change_edge_color())
            menu.addAction(a)

            menu.addSeparator()
            a = QAction(t("k_select_clear"), menu)
            a.triggered.connect(lambda: self.scene.clearSelection())
            menu.addAction(a)

            menu.exec(event.globalPos())

        else:
            menu = QMenu(self)
            new_menu = menu.addMenu(t("k_canvas_new_node"))
            for k, lang in [("k_lang_python","Python"), ("k_lang_rust","Rust"), ("k_lang_nodejs","Node.js"), ("k_lang_go","Go"), ("k_lang_java","Java"), ("k_lang_cpp","C++"), ("k_lang_shell","Shell")]:
                a = QAction(t(k), self)
                a.triggered.connect(partial(self.parent_window.create_new_node_with_language, lang))
                new_menu.addAction(a)
            menu.addSeparator()
            a = QAction(t("k_canvas_monitor"), menu); a.triggered.connect(lambda: self.parent_window.show_node_monitor()); menu.addAction(a)
            menu.addSeparator()
            a = QAction(t("k_canvas_clear_connections"), menu); a.triggered.connect(self.clear_edges); menu.addAction(a)
            menu.addSeparator()
            a = QAction(t("k_canvas_reset_view"), menu); a.triggered.connect(self.reset_view); menu.addAction(a)
            menu.addSeparator()
            # 绘图工具栏切换
            toolbar_visible = self.draw_layer._toolbar_visible if hasattr(self, 'draw_layer') else False
            action_text = t("k_canvas_hide_draw_toolbar") if toolbar_visible else t("k_canvas_show_draw_toolbar")
            a = QAction(action_text, menu)
            a.triggered.connect(self._toggle_draw_toolbar)
            menu.addAction(a)
            menu.addSeparator()
            color_menu = menu.addMenu(t("k_canvas_color"))
            a = QAction(t("k_canvas_bg_color"), color_menu); a.triggered.connect(self.change_canvas_background_color); color_menu.addAction(a)
            a = QAction(t("k_canvas_grid_color"), color_menu); a.triggered.connect(self.change_grid_color); color_menu.addAction(a)
            a = QAction(t("k_canvas_edge_color"), color_menu); a.triggered.connect(self.change_edge_color); color_menu.addAction(a)
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
        
        # 更新所有连接到该节点的连线路径（样式切换会改变锚点位置）
        all_edges = set()
        if hasattr(node_item, 'output_anchor'):
            for edge in node_item.output_anchor.edges[:]:
                if edge and edge.end_node:
                    all_edges.add(edge)
        if hasattr(node_item, 'input_anchor'):
            for edge in node_item.input_anchor.edges[:]:
                if edge and edge.start_node:
                    all_edges.add(edge)
        for edge in all_edges:
            edge.update_path()
        
        # 触发自动保存，持久化样式变更
        if hasattr(self, '_save_timer'):
            self._save_timer.stop()
            self._save_timer.start(500)