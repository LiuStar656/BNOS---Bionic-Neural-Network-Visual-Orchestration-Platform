"""
画布右键菜单 Mixin — 统一使用 ActionRegistry + ActionFactory
所有菜单操作（包括节点操作、连线操作、画布设置）均通过 Action 系统分发
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
from ui.core.actions import ActionFactory, ActionContext, ActionRegistry
from ui.core.actions.builtin_node_actions import register_node_actions
from ui.core.actions.builtin_canvas_actions import register_canvas_actions
from ui.core.utils.file_utils import get_project_root, open_terminal_in_directory


class CanvasMenusMixin:
    """右键菜单 Mixin"""

    # ---- helpers ----

    def _make_ctx(self, **kwargs):
        """构建 ActionContext，自动注入 canvas 引用"""
        return ActionContext(**(kwargs | {'extra': {'canvas': self}}))

    def _dispatch(self, action_id, **kwargs):
        """通过 ActionRegistry 分发操作"""
        ActionRegistry.execute(action_id, self._make_ctx(**kwargs))

    # ---- 主入口 ----

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

        # 多节点框选
        if len(self.box_selected_nodes) > 1:
            self._show_multi_node_menu(event)
            return

        # 单节点
        if isinstance(item, NodeItem):
            self._show_single_node_menu(event, item)
            return

        # 连线
        if selected_edge is not None or isinstance(item, EdgeItem):
            edge = selected_edge if selected_edge else item
            self._show_edge_menu(event, edge)
            return

        # 空白画布
        self._show_canvas_menu(event)

    # ---- 多节点框选菜单 ----

    def _show_multi_node_menu(self, event):
        count = len(self.box_selected_nodes)
        menu = QMenu(self)

        ActionFactory.add_disabled_label(menu, "_k_selected_count".format(count=count))
        menu.addSeparator()

        ctx = ActionContext(node_list=self.box_selected_nodes)
        ActionFactory.create_action(self, "node.start", ctx, menu)
        ActionFactory.create_action(self, "node.stop", ctx, menu)
        menu.addSeparator()

        # 批量移除（动态名称）
        a = QAction(t("_k_batch_remove_selected").replace("{count}", str(count)), menu)
        a.triggered.connect(lambda: self._dispatch("canvas.batch_remove"))
        menu.addAction(a)

        menu.addSeparator()
        ActionFactory.create_action(self, "canvas.clear_listen_config", menu=menu)
        menu.addSeparator()
        ActionFactory.create_action(self, "canvas.clear_selection", menu=menu)

        menu.exec(event.globalPos())

    # ---- 单节点菜单 ----

    def _show_single_node_menu(self, event, node_item):
        menu = QMenu(self)
        node_name = node_item.node_name

        # 启动/停止（main_window 操作，无需 extra）
        if self.parent_window and node_name in self.parent_window.nodes_data:
            status = self.parent_window.nodes_data[node_name].get('status')
            ctx = ActionContext(node_name=node_name)
            if status in ('running', 'idle'):
                ActionFactory.create_action(self, "node.stop", ctx, menu)
            else:
                ActionFactory.create_action(self, "node.start", ctx, menu)
            menu.addSeparator()

        # 开始连线
        ActionFactory.create_action(self, "canvas.start_connection",
                                     self._make_ctx(node_name=node_name), menu)
        menu.addSeparator()

        # 配置节点
        ActionFactory.create_action(self, "node.config",
                                     self._make_ctx(node_name=node_name), menu)

        # 展开节点
        ActionFactory.create_action(self, "canvas.expand_node",
                                     self._make_ctx(node_name=node_name), menu)
        menu.addSeparator()

        # 样式子菜单（动态列表，保持手动构建）
        style_menu = menu.addMenu(t("k_node_style"))
        for key, cls in STYLES.items():
            st = cls()
            a = QAction(st.style_name, style_menu)
            a.triggered.connect(partial(self._switch_node_style, key, node_item))
            style_menu.addAction(a)

        menu.addSeparator()

        # 节点颜色子菜单（需要 NodeItem 引用，保持手动）
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

        # 导出
        ActionFactory.create_action(self, "node.export",
                                     ActionContext(node_name=node_name), menu)

        menu.addSeparator()

        # IDE 打开（通过 Action 系统统一管理）
        node_path = self.parent_window.nodes_data.get(node_name, {}).get('path', '') if self.parent_window else ''
        ide_ctx = ActionContext(extra={'node_name': node_name, 'node_path': node_path})
        ActionFactory.create_action(self, "node.open_vscode", ide_ctx, menu)
        ActionFactory.create_action(self, "node.open_trae_ide", ide_ctx, menu)

        menu.addSeparator()

        # 从画布移除
        ActionFactory.create_action(self, "canvas.remove_node",
                                     self._make_ctx(node_name=node_name), menu)

        menu.exec(event.globalPos())

    # ---- 连线菜单 ----

    def _show_edge_menu(self, event, edge):
        menu = QMenu(self)
        edge_ctx = ActionContext(extra={'canvas': self, 'edge': edge})

        ActionFactory.create_action(self, "canvas.delete_edge", edge_ctx, menu)
        menu.addSeparator()
        ActionFactory.create_action(self, "canvas.change_edge_color", edge_ctx, menu)
        menu.addSeparator()
        ActionFactory.create_action(self, "canvas.clear_selection", menu=menu)

        menu.exec(event.globalPos())

    # ---- 空白画布菜单 ----

    def _show_canvas_menu(self, event):
        menu = QMenu(self)

        # 新建节点（动态子菜单，使用 ActionRegistry）
        new_menu = menu.addMenu(t("k_canvas_new_node"))
        _lang_list = [
            ("k_lang_python", "Python"),
            ("k_lang_rust", "Rust"),
            ("k_lang_nodejs", "Node.js (开发中)"),
            ("k_lang_go", "Go (开发中)"),
            ("k_lang_java", "Java (开发中)"),
            ("k_lang_cpp", "C++ (开发中)"),
            ("k_lang_shell", "Shell (开发中)"),
        ]
        for i18n_k, lang_name in _lang_list:
            a = QAction(t(i18n_k), new_menu)
            a.triggered.connect(
                lambda checked, ln=lang_name: self._dispatch(f"canvas.new_node.{ln}"))
            new_menu.addAction(a)
        menu.addSeparator()

        # 节点监控
        ActionFactory.create_action(self, "canvas.monitor", self._make_ctx(), menu)

        menu.addSeparator()

        # 打开终端（平台相关，保持手动但路由到 ActionRegistry）
        terminal_menu = menu.addMenu(t("k_canvas_open_terminal"))
        if platform.system() == "Windows":
            a = QAction(t("k_canvas_open_terminal_powershell"), terminal_menu)
            a.triggered.connect(partial(self._open_project_terminal, "powershell"))
            terminal_menu.addAction(a)
            a = QAction(t("k_canvas_open_terminal_cmd"), terminal_menu)
            a.triggered.connect(partial(self._open_project_terminal, "cmd"))
            terminal_menu.addAction(a)
        else:
            a = QAction(t("k_canvas_open_terminal_default"), terminal_menu)
            a.triggered.connect(partial(self._open_project_terminal, "default"))
            terminal_menu.addAction(a)

        menu.addSeparator()

        # IDE 工作区（通过 Action 系统统一管理）
        from ui.core.utils.file_utils import get_project_root
        workspace_path = None
        if self.parent_window and hasattr(self.parent_window, 'current_project_path') and self.parent_window.current_project_path:
            workspace_path = self.parent_window.current_project_path
        else:
            workspace_path = get_project_root()
        ws_ctx = ActionContext(extra={'workspace_path': workspace_path or ''})
        ActionFactory.create_action(self, "workspace.open_vscode", ws_ctx, menu)
        ActionFactory.create_action(self, "workspace.open_trae_ide", ws_ctx, menu)

        menu.addSeparator()
        ActionFactory.create_action(self, "canvas.clear_connections", menu=menu)
        menu.addSeparator()
        ActionFactory.create_action(self, "canvas.reset_view", menu=menu)
        menu.addSeparator()

        # 绘画工具栏（动态文本）
        toolbar_visible = self.draw_layer._toolbar_visible if hasattr(self, 'draw_layer') else False
        action_text = t("k_canvas_hide_draw_toolbar") if toolbar_visible else t("k_canvas_show_draw_toolbar")
        a = QAction(action_text, menu)
        a.triggered.connect(lambda: self._dispatch("canvas.toggle_draw_toolbar"))
        menu.addAction(a)

        menu.addSeparator()

        # 画布颜色子菜单
        color_menu = menu.addMenu(t("k_canvas_color"))
        ActionFactory.create_action(self, "canvas.bg_color", self._make_ctx(), color_menu)
        ActionFactory.create_action(self, "canvas.grid_color", self._make_ctx(), color_menu)
        ActionFactory.create_action(self, "canvas.default_edge_color", self._make_ctx(), color_menu)

        menu.exec(event.globalPos())

    # ---- 终端 ----

    def _open_project_terminal(self, terminal_type="default"):
        """在项目根目录打开终端"""
        try:
            target_dir = None
            if hasattr(self.parent_window, 'current_project_path') and self.parent_window.current_project_path:
                target_dir = self.parent_window.current_project_path
            else:
                target_dir = get_project_root()
            open_terminal_in_directory(target_dir, terminal_type, self)
        except Exception:
            pass

    # ---- 节点样式切换 ----

    def _switch_node_style(self, style_key, node_item):
        from ui.canvas.items.node_style import STYLES
        cls = STYLES.get(style_key)
        if not cls:
            return
        # 关键：调用 node_item.set_style() — 它会正确清理详细版控件并使用新样式的默认尺寸
        node_item.set_style(cls())

        all_edges = set()
        if hasattr(node_item, 'output_anchor'):
            for e in node_item.output_anchor.edges[:]:
                if e and e.end_node:
                    all_edges.add(e)
        if hasattr(node_item, 'input_anchor'):
            for e in node_item.input_anchor.edges[:]:
                if e and e.start_node:
                    all_edges.add(e)
        for e in all_edges:
            e.update_path()

        if hasattr(self, '_save_timer'):
            self._save_timer.stop()
            self._save_timer.start(500)
