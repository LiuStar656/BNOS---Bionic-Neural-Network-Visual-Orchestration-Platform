"""
画布右键菜单 Mixin — 统一使用 ActionRegistry + ActionFactory
所有菜单操作（包括节点操作、连线操作、画布设置）均通过 Action 系统分发
"""

from __future__ import annotations

import platform
from functools import partial

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from ui.canvas.items.composite_node_item import CompositeNodeItem
from ui.canvas.items.edge_item import EdgeItem
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.styles import StyleRegistry
from ui.core.actions import ActionContext, ActionFactory, ActionRegistry
from ui.core.actions.builtin_canvas_actions import register_canvas_actions
from ui.core.actions.builtin_node_actions import register_node_actions
from ui.core.i18n import t
from ui.core.i18n.translation_keys import TK
from ui.core.node.composite_node import CompositeNode
from ui.core.utils.dialog_utils import themed_input, themed_message
from ui.core.utils.file_utils import get_project_root, open_terminal_in_directory


class CanvasMenu:
    """画布菜单（组合类，通过 self.canvas 访问画布上下文）"""

    def __init__(self, canvas):
        self.canvas = canvas

    # ---- helpers ----

    def _make_ctx(self, **kwargs):
        """构建 ActionContext，自动注入 canvas 引用"""
        return ActionContext(**(kwargs | {"extra": {"canvas": self.canvas}}))

    def _dispatch(self, action_id, **kwargs):
        """通过 ActionRegistry 分发操作"""
        ActionRegistry.execute(action_id, self._make_ctx(**kwargs))

    # ---- 主入口 ----

    def contextMenuEvent(self, event):
        all_items = self.canvas.items(event.pos())
        item = None

        for probe in all_items:
            if isinstance(probe, NodeItem):
                item = probe
                break
            elif isinstance(probe, CompositeNodeItem):
                item = probe
                break
            elif isinstance(probe, EdgeItem) and item is None:
                item = probe

        if item is None and all_items:
            item = all_items[0]

        selected_edge = None
        for sel in self.canvas.scene.selectedItems():
            if isinstance(sel, EdgeItem):
                selected_edge = sel
                break

        if self.canvas.parent_window:
            register_node_actions(self.canvas.parent_window)
            register_canvas_actions(self.canvas.parent_window)

        # 多节点框选
        if len(self.canvas.box_selected_nodes) > 1:
            self._show_multi_node_menu(event)
            return

        # 复合节点
        if isinstance(item, CompositeNodeItem):
            self._show_composite_node_menu(event, item)
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
        count = len(self.canvas.box_selected_nodes)
        menu = QMenu(self.canvas)

        ActionFactory.add_disabled_label(menu, t("_k_selected_count").format(count=count))
        menu.addSeparator()

        ctx = ActionContext(node_list=self.canvas.box_selected_nodes)
        ActionFactory.create_action(self.canvas, "node.start", ctx, menu)
        ActionFactory.create_action(self.canvas, "node.stop", ctx, menu)
        menu.addSeparator()

        # 批量移除
        ActionFactory.create_action(
            self.canvas,
            "canvas.batch_remove",
            ctx,
            menu,
            label=t("_k_batch_remove_selected").replace("{count}", str(count)),
        )

        menu.addSeparator()

        # ── 复合节点操作 ──
        compress_ctx = ActionContext(
            node_list=self.canvas.box_selected_nodes,
            extra={"canvas": self.canvas},
        )
        ActionFactory.create_action(
            self.canvas,
            "canvas.compress_to_composite",
            compress_ctx,
            menu,
            label=f"\u229e \u538b\u7f29\u4e3a\u590d\u5408\u8282\u70b9 ({count})",
        )

        # 如果所有选中节点已在某复合节点中，显示"解耦"
        if hasattr(self.canvas, "_composite_manager") and self.canvas._composite_manager:
            mgr = self.canvas._composite_manager
            comp_ids = set()
            for n in self.canvas.box_selected_nodes:
                cid = mgr._find_composite_of_node(n)
                if cid:
                    comp_ids.add(cid)
            if comp_ids:
                for cid in comp_ids:
                    decomp_ctx = ActionContext(
                        node_name=cid,
                        extra={"canvas": self.canvas, "comp_id": cid},
                    )
                    ActionFactory.create_action(
                        self.canvas,
                        "canvas.decompress_composite",
                        decomp_ctx,
                        menu,
                        label=f"\u293a \u89e3\u8026\u590d\u5408\u8282\u70b9 {cid}",
                    )

        menu.addSeparator()
        ActionFactory.create_action(self.canvas, "canvas.clear_listen_config", menu=menu)
        menu.addSeparator()
        ActionFactory.create_action(self.canvas, "canvas.clear_selection", menu=menu)

        menu.exec(event.globalPos())

    # ---- 单节点菜单 ----

    def _show_single_node_menu(self, event, node_item):
        menu = QMenu(self.canvas)
        node_name = node_item.node_name

        # 启动/停止
        if self.canvas.parent_window and node_name in self.canvas.parent_window.nodes_data:
            status = self.canvas.parent_window.nodes_data[node_name].get("status")
            ctx = ActionContext(node_name=node_name)
            if status in ("running", "idle"):
                ActionFactory.create_action(self.canvas, "node.stop", ctx, menu)
            else:
                ActionFactory.create_action(self.canvas, "node.start", ctx, menu)
            menu.addSeparator()

        # 重命名
        rename_ctx = self._make_ctx(node_name=node_name)
        ActionFactory.create_action(self.canvas, "node.rename", rename_ctx, menu)
        menu.addSeparator()

        # 开始连线
        ActionFactory.create_action(self.canvas, "canvas.start_connection", self._make_ctx(node_name=node_name), menu)
        menu.addSeparator()

        # 配置 / 展开节点
        ActionFactory.create_action(self.canvas, "node.config", self._make_ctx(node_name=node_name), menu)
        ActionFactory.create_action(self.canvas, "canvas.expand_node", self._make_ctx(node_name=node_name), menu)
        menu.addSeparator()

        # 样式子菜单（动态从 StyleRegistry 构建，通过 Action 系统分发）
        style_menu = menu.addMenu(t("k_node_style"))
        for key in StyleRegistry.keys():
            cls = StyleRegistry.get(key)
            st = cls()
            ActionFactory.create_action(
                self.canvas,
                "node.change_style",
                ActionContext(extra={"canvas": self.canvas, "node_item": node_item, "style_key": key}),
                style_menu,
            )
            # 用样式名覆盖 label（ActionFactory 用的是 i18n key，这里需要动态名称）
            last_action = style_menu.actions()[-1] if style_menu.actions() else None
            if last_action and not last_action.isSeparator():
                last_action.setText(t(st.style_name))

        menu.addSeparator()

        # 节点颜色子菜单（通过 Action 系统分发）
        color_menu = menu.addMenu(t("k_node_color"))
        color_ctx = ActionContext(extra={"canvas": self.canvas, "node_item": node_item})
        ActionFactory.create_action(self.canvas, "node.change_bg_color", color_ctx, color_menu)
        ActionFactory.create_action(self.canvas, "node.change_border_color", color_ctx, color_menu)
        ActionFactory.create_action(self.canvas, "node.change_text_color", color_ctx, color_menu)

        menu.addSeparator()

        # 导出
        ActionFactory.create_action(self.canvas, "node.export", ActionContext(node_name=node_name), menu)

        # 保存为模板
        ActionFactory.create_action(self.canvas, "node.save_as_template", self._make_ctx(node_name=node_name), menu)

        menu.addSeparator()

        # IDE 打开（通过 Action 系统统一管理）
        node_path = (
            self.canvas.parent_window.nodes_data.get(node_name, {}).get("path", "") if self.canvas.parent_window else ""
        )
        ide_ctx = ActionContext(extra={"node_name": node_name, "node_path": node_path})
        ActionFactory.create_action(self.canvas, "node.open_vscode", ide_ctx, menu)
        ActionFactory.create_action(self.canvas, "node.open_trae_ide", ide_ctx, menu)

        menu.addSeparator()

        # 从画布移除
        ActionFactory.create_action(self.canvas, "canvas.remove_node", self._make_ctx(node_name=node_name), menu)

        menu.exec(event.globalPos())

    # ---- 连线菜单 ----

    def _show_edge_menu(self, event, edge):
        menu = QMenu(self.canvas)
        edge_ctx = ActionContext(extra={"canvas": self.canvas, "edge": edge})

        ActionFactory.create_action(self.canvas, "canvas.delete_edge", edge_ctx, menu)
        menu.addSeparator()
        ActionFactory.create_action(self.canvas, "canvas.change_edge_color", edge_ctx, menu)
        menu.addSeparator()
        ActionFactory.create_action(self.canvas, "canvas.clear_selection", menu=menu)

        menu.exec(event.globalPos())

    # ---- 空白画布菜单 ----

    def rename_node(self, old_name):
        """画布节点重命名 — 委托给主窗口"""
        parent_win = getattr(self.canvas, "parent_window", None)
        if parent_win and hasattr(parent_win, "rename_node"):
            parent_win.rename_node(old_name)

    def _show_canvas_menu(self, event):
        menu = QMenu(self.canvas)

        # 新建节点（通过 ActionFactory）
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
        for _i18n_key, lang_name in _lang_list:
            ActionFactory.create_action(self.canvas, f"canvas.new_node.{lang_name}", self._make_ctx(), menu=new_menu)
        menu.addSeparator()

        # 节点监控
        ActionFactory.create_action(self.canvas, "canvas.monitor", self._make_ctx(), menu)

        menu.addSeparator()

        # 打开终端（平台相关 — 动态菜单，保留手动构建）
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
        workspace_path = None
        if (
            self.canvas.parent_window
            and hasattr(self.canvas.parent_window, "current_project_path")
            and self.canvas.parent_window.current_project_path
        ):
            workspace_path = self.canvas.parent_window.current_project_path
        else:
            workspace_path = get_project_root()
        ws_ctx = ActionContext(extra={"workspace_path": workspace_path or ""})
        ActionFactory.create_action(self.canvas, "workspace.open_vscode", ws_ctx, menu)
        ActionFactory.create_action(self.canvas, "workspace.open_trae_ide", ws_ctx, menu)

        menu.addSeparator()
        ActionFactory.create_action(self.canvas, "canvas.clear_connections", menu=menu)
        menu.addSeparator()

        # 连线吸附开关
        snap_enabled = getattr(self.canvas, "edge_snap_enabled", True)
        snap_text = t("k_canvas_edge_snap_on") if snap_enabled else t("k_canvas_edge_snap_off")
        a_snap = QAction(snap_text, menu)
        a_snap.setCheckable(True)
        a_snap.setChecked(snap_enabled)
        a_snap.triggered.connect(self._toggle_edge_snap)
        menu.addAction(a_snap)

        ActionFactory.create_action(self.canvas, "canvas.reset_view", menu=menu)
        menu.addSeparator()

        # 绘画工具栏
        toolbar_visible = self.canvas.draw_layer._toolbar_visible if hasattr(self.canvas, "draw_layer") else False
        draw_label = t("k_canvas_hide_draw_toolbar") if toolbar_visible else t("k_canvas_show_draw_toolbar")
        ActionFactory.create_action(
            self.canvas,
            "canvas.toggle_draw_toolbar",
            self._make_ctx(),
            menu,
            label=draw_label,
        )

        menu.addSeparator()

        # 画布颜色子菜单
        color_menu = menu.addMenu(t("k_canvas_color"))
        ActionFactory.create_action(self.canvas, "canvas.bg_color", self._make_ctx(), color_menu)
        ActionFactory.create_action(self.canvas, "canvas.grid_color", self._make_ctx(), color_menu)
        ActionFactory.create_action(self.canvas, "canvas.default_edge_color", self._make_ctx(), color_menu)

        menu.exec(event.globalPos())

    # ---- 终端 ----

    def _toggle_edge_snap(self, checked: bool):
        """切换连线正交吸附"""
        self.canvas.edge_snap_enabled = checked

    def _open_project_terminal(self, terminal_type="default"):
        """在项目根目录打开终端"""
        try:
            target_dir = None
            if (
                hasattr(self.canvas.parent_window, "current_project_path")
                and self.canvas.parent_window.current_project_path
            ):
                target_dir = self.canvas.parent_window.current_project_path
            else:
                target_dir = get_project_root()
            open_terminal_in_directory(target_dir, terminal_type, self.canvas)
        except RuntimeError:
            pass

    # ---- 节点样式切换 ----

    def _switch_node_style(self, style_key, node_item):
        from ui.canvas.items.styles import StyleRegistry

        cls = StyleRegistry.get(style_key)
        if not cls:
            return
        node_item.set_style(cls())

        all_edges = set()
        if hasattr(node_item, "output_anchor"):
            for e in node_item.output_anchor.edges[:]:
                if e and e.end_node:
                    all_edges.add(e)
        if hasattr(node_item, "input_anchor"):
            for e in node_item.input_anchor.edges[:]:
                if e and e.start_node:
                    all_edges.add(e)
        for e in all_edges:
            e.update_path()

        if hasattr(self.canvas, "_save_timer"):
            self.canvas._save_timer.stop()
            self.canvas._save_timer.start(500)

    # ---- 复合节点菜单 ----

    def _show_composite_node_menu(self, event, comp_item):
        """复合节点右键菜单。"""
        menu = QMenu(self.canvas)
        comp_id = comp_item.comp_id

        mgr = self._ensure_composite_manager()
        if not mgr:
            menu.exec(event.globalPos())
            return

        is_running = mgr.is_running(comp_id)
        comp_data = mgr._composites.get(comp_id, {})
        is_expanded = comp_data.get("_expanded", False)

        # ── 启动 / 停止（互斥显示）──
        if is_running:
            stop_action = menu.addAction("\u505c\u6b62\u590d\u5408\u8282\u70b9")
            stop_action.triggered.connect(lambda: mgr.stop_composite(comp_id))
        else:
            start_action = menu.addAction("\u542f\u52a8\u590d\u5408\u8282\u70b9")
            start_action.triggered.connect(lambda: self._composite_start(mgr, comp_id))

        menu.addSeparator()

        # ── 展开 / 折叠（运行时禁止）──
        if is_expanded:
            expand_action = menu.addAction("\u6298\u53e0")
        else:
            expand_action = menu.addAction("\u5c55\u5f00")
        if is_running:
            expand_action.setEnabled(False)
            expand_action.setToolTip("复合节点运行中，请先停止")
        expand_action.triggered.connect(lambda: self._on_toggle_expand(mgr, comp_id))

        menu.addSeparator()

        # 运行时模式
        runtime_menu = menu.addMenu("\u8fd0\u884c\u65f6\u6a21\u5f0f")
        mgr.get_runtime(comp_id) or "inprocess"

        proc_action = runtime_menu.addAction("\u72ec\u7acb\u8fdb\u7a0b (process)")
        inproc_action = runtime_menu.addAction("\u5355\u8fdb\u7a0b (inprocess)")
        proc_action.triggered.connect(lambda: mgr.set_runtime(comp_id, "process"))
        inproc_action.triggered.connect(lambda: mgr.set_runtime(comp_id, "inprocess"))

        menu.addSeparator()

        # ── 解耦（最底层，运行时禁止）──
        decompress_action = menu.addAction("\u89e3\u8026\u4e3a\u72ec\u7acb\u8282\u70b9")
        if is_running:
            decompress_action.setEnabled(False)
            decompress_action.setToolTip("复合节点运行中，请先停止")
        decompress_action.triggered.connect(lambda: self._on_decompress_composite(mgr, comp_id, comp_item.node_count))

        menu.exec(event.globalPos())

    def _ensure_composite_manager(self):
        """懒初始化复合节点管理器。"""
        if hasattr(self.canvas, "_composite_manager") and self.canvas._composite_manager:
            return self.canvas._composite_manager

        if not self.canvas.parent_window:
            return None

        project_path = None
        if hasattr(self.canvas.parent_window, "current_project_path"):
            project_path = self.canvas.parent_window.current_project_path
        if not project_path:
            return None

        group_manager = None
        if hasattr(self.canvas.parent_window, "node_list_panel") and self.canvas.parent_window.node_list_panel:
            group_manager = self.canvas.parent_window.node_list_panel.group_manager

        self.canvas._composite_manager = CompositeNode(project_path, self.canvas, group_manager)
        return self.canvas._composite_manager

    def _on_compress_to_composite(self, node_names):
        """多选节点 → 命名后压缩为复合节点。"""
        mgr = self._ensure_composite_manager()
        if not mgr:
            return

        # 弹出命名对话框（主题统一）
        name = themed_input(None, t(TK.COMPOSITE_NAME_DIALOG_TITLE), t(TK.COMPOSITE_NAME_PROMPT), default="")
        if name is None:
            return  # 用户取消

        # 确认对话框
        n = len(node_names)
        confirm = themed_message(
            None, t(TK.COMPOSITE_CONFIRM_TITLE), t(TK.COMPOSITE_CONFIRM_TEXT).format(n=n), "question"
        )
        if not confirm:
            return

        ok, msg, comp_id = mgr.compress(node_names, name)
        if not ok:
            themed_message(None, t(TK.COMPOSITE_COMPRESS_FAILED), msg, "warning")

    def _on_decompress_composite(self, mgr, comp_id, node_count):
        """解耦确认对话框。"""
        reply = themed_message(
            None,
            t(TK.COMPOSITE_DECOMPRESS_CONFIRM_TITLE),
            t(TK.COMPOSITE_DECOMPRESS_CONFIRM_TEXT).format(n=node_count),
            "question",
        )
        if not reply:
            return
        mgr.decompress(comp_id)

    def _composite_start(self, mgr, comp_id):
        """启动复合节点。"""
        runtime = mgr.get_runtime(comp_id) or "inprocess"
        if runtime == "inprocess":
            ok, msg = mgr.start_inprocess(comp_id)
        else:
            ok, msg = mgr.start_process_mode(comp_id)
        if not ok:
            themed_message(None, t("k_title_error"), msg, "error")

    def _on_toggle_expand(self, mgr, comp_id):
        """展开/折叠复合节点，带运行状态检查。"""
        if mgr.is_running(comp_id):
            themed_message(
                None,
                t("k_title_warning"),
                "复合节点正在运行中，请先停止后再展开/折叠",
                "warning",
            )
            return
        mgr.toggle_expand(comp_id)
