"""
画布右键菜单 Mixin — 使用统一 ActionRegistry
"""
import os
import platform
from functools import partial
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGraphicsItem
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.edge_item import EdgeItem
from ui.canvas.items.node_style import STYLES
from ui.core.i18n import t
from ui.core.actions import ActionFactory, ActionContext
from ui.core.actions.builtin_node_actions import register_node_actions
from ui.core.actions.builtin_canvas_actions import register_canvas_actions
from ui.core.utils.file_utils import get_project_root, open_terminal_in_directory


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

        selected_edge = None
        for sel in self.scene.selectedItems():
            if isinstance(sel, EdgeItem):
                selected_edge = sel
                break

        if self.parent_window:
            register_node_actions(self.parent_window)
            register_canvas_actions(self.parent_window)

        if len(self.box_selected_nodes) > 1:
            menu = QMenu(self)
            count = len(self.box_selected_nodes)
            ActionFactory.add_disabled_label(menu, "_k_selected_count".format(count=count))
            menu.addSeparator()
            
            ctx = ActionContext(node_list=self.box_selected_nodes)
            ActionFactory.create_action(self, "node.start", ctx, menu)
            ActionFactory.create_action(self, "node.stop", ctx, menu)
            menu.addSeparator()
            
            a = QAction(t("_k_batch_remove_selected").replace("{count}", str(count)), menu)
            a.triggered.connect(self.batch_remove_nodes_from_canvas)
            menu.addAction(a)
            
            menu.addSeparator()
            ActionFactory.create_action(self, "canvas.clear_listen_config", menu)
            menu.addSeparator()
            ActionFactory.create_action(self, "canvas.clear_selection", menu)
            
            menu.exec(event.globalPos())
            return

        if isinstance(item, NodeItem):
            node_item = item
            menu = QMenu(self)
            node_name = node_item.node_name
            ctx = ActionContext(node_name=node_name)

            if self.parent_window and node_name in self.parent_window.nodes_data:
                status = self.parent_window.nodes_data[node_name].get('status')
                if status in ('running', 'idle'):
                    ActionFactory.create_action(self, "node.stop", ctx, menu)
                else:
                    ActionFactory.create_action(self, "node.start", ctx, menu)
                menu.addSeparator()

            ActionFactory.create_action(self, "canvas.start_connection", ctx, menu)
            menu.addSeparator()

            ActionFactory.create_action(self, "node.config", ctx, menu)
            
            a = QAction(t("k_node_expand"), menu)
            a.triggered.connect(partial(self.on_node_expand_requested, node_name))
            menu.addAction(a)
            menu.addSeparator()

            style_menu = menu.addMenu(t("k_node_style"))
            for key, cls in STYLES.items():
                st = cls()
                a = QAction(st.style_name, style_menu)
                a.triggered.connect(partial(self._switch_node_style, key, node_item))
                style_menu.addAction(a)

            menu.addSeparator()

            color_menu = menu.addMenu(t("k_node_color"))
            a = QAction(t("k_node_bg_color"), color_menu)
            a.triggered.connect(partial(self.change_node_background_color, node_item))
            color_menu.addAction(a)
            a = QAction(t("k_node_border_color"), color_menu)
            a.triggered.connect(partial(self.change_node_border_color, node_item))
            color_menu.addAction(a)
            a = QAction(t("k_node_text_color"), color_menu)
            a.triggered.connect(partial(self.change_node_text_color, node_item))
            color_menu.addAction(a)

            menu.addSeparator()
            
            ActionFactory.create_action(self, "node.export", ctx, menu)
            
            menu.addSeparator()
            a = QAction(t("k_canvas_remove_from"), menu)
            a.triggered.connect(partial(self.remove_node_with_cleanup, node_name))
            menu.addAction(a)
            menu.exec(event.globalPos())

        elif selected_edge is not None or isinstance(item, EdgeItem):
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
            ActionFactory.create_action(self, "canvas.clear_selection", menu)

            menu.exec(event.globalPos())

        else:
            menu = QMenu(self)
            new_menu = menu.addMenu(t("k_canvas_new_node"))
            for k, lang in [("k_lang_python","Python"), ("k_lang_rust","Rust"), 
                           ("k_lang_nodejs","Node.js (开发中)"), ("k_lang_go","Go (开发中)"), 
                           ("k_lang_java","Java (开发中)"), ("k_lang_cpp","C++ (开发中)"), 
                           ("k_lang_shell","Shell (开发中)")]:
                a = QAction(t(k), self)
                a.triggered.connect(partial(self.parent_window.create_new_node_with_language, lang))
                new_menu.addAction(a)
            menu.addSeparator()
            a = QAction(t("k_canvas_monitor"), self)
            a.triggered.connect(lambda: self.parent_window.show_node_monitor())
            menu.addAction(a)
            menu.addSeparator()
            
            # 添加在命令行中打开项目根目录的功能
            terminal_menu = menu.addMenu(t("k_canvas_open_terminal"))
            if platform.system() == "Windows":
                # Windows 平台：提供 PowerShell 和 Cmd 选项
                a = QAction(t("k_canvas_open_terminal_powershell"), terminal_menu)
                a.triggered.connect(partial(self._open_project_terminal, "powershell"))
                terminal_menu.addAction(a)
                a = QAction(t("k_canvas_open_terminal_cmd"), terminal_menu)
                a.triggered.connect(partial(self._open_project_terminal, "cmd"))
                terminal_menu.addAction(a)
            else:
                # 非 Windows 平台：只提供默认终端选项
                a = QAction(t("k_canvas_open_terminal_default"), terminal_menu)
                a.triggered.connect(partial(self._open_project_terminal, "default"))
                terminal_menu.addAction(a)
            
            menu.addSeparator()
            ActionFactory.create_action(self, "canvas.clear_connections", menu)
            menu.addSeparator()
            ActionFactory.create_action(self, "canvas.reset_view", menu)
            menu.addSeparator()
            
            toolbar_visible = self.draw_layer._toolbar_visible if hasattr(self, 'draw_layer') else False
            action_text = t("k_canvas_hide_draw_toolbar") if toolbar_visible else t("k_canvas_show_draw_toolbar")
            a = QAction(action_text, self)
            a.triggered.connect(self._toggle_draw_toolbar)
            menu.addAction(a)
            
            menu.addSeparator()
            color_menu = menu.addMenu(t("k_canvas_color"))
            a = QAction(t("k_canvas_bg_color"), color_menu)
            a.triggered.connect(self.change_canvas_background_color)
            color_menu.addAction(a)
            a = QAction(t("k_canvas_grid_color"), color_menu)
            a.triggered.connect(self.change_grid_color)
            color_menu.addAction(a)
            a = QAction(t("k_canvas_edge_color"), color_menu)
            a.triggered.connect(self.change_edge_color)
            color_menu.addAction(a)
            menu.exec(event.globalPos())
    
    def _open_project_terminal(self, terminal_type="default"):
        """在项目根目录打开终端
        
        Args:
            terminal_type: 终端类型（"default", "powershell", "cmd"）
        """
        try:
            # 优先使用当前打开的工作项目目录
            target_dir = None
            if hasattr(self.parent_window, 'current_project_path') and self.parent_window.current_project_path:
                target_dir = self.parent_window.current_project_path
            else:
                # 如果没有打开工作项目，回退到 BNOS 软件项目目录
                target_dir = get_project_root()
            
            open_terminal_in_directory(target_dir, terminal_type, self)
        except Exception as e:
            pass

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
        
        if hasattr(self, '_save_timer'):
            self._save_timer.stop()
            self._save_timer.start(500)
