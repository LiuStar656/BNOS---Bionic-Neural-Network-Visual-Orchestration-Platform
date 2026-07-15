"""
节点列表右键菜单系统 Mixin — 统一使用 ActionRegistry + ActionFactory
所有操作通过 Action 系统分发，菜单与菜单栏共用同一套功能注册表
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

from ui.core.actions import ActionContext, ActionFactory, ActionRegistry
from ui.core.actions.builtin_node_actions import register_node_actions
from ui.core.i18n import t
from ui.core.node.composite_node import CompositeNode
from ui.core.utils.dialog_utils import themed_message


class NodeListContextMixin:
    """节点列表右键菜单（Mixin 注入到 NodeListPanel）"""

    # ---- helpers ----

    def _make_ctx(self, **kwargs):
        """构建 ActionContext，自动注入 panel 引用"""
        return ActionContext(**(kwargs | {"extra": {"panel": self}}))

    def _dispatch(self, action_id, **kwargs):
        """通过 ActionRegistry 分发操作"""
        ActionRegistry.execute(action_id, self._make_ctx(**kwargs))

    # ---- 主入口 ----

    def show_context_menu(self, position):
        """显示右键菜单 — 所有功能的统一入口"""
        item = self.node_tree.itemAt(position)
        if not item:
            self._show_global_context_menu(position)
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        if self.parent_window:
            register_node_actions(self.parent_window)

        menu = QMenu(self)
        if data.get("type") == "node":
            self._show_node_context_menu(menu, data.get("name", ""))
        elif data.get("type") == "group":
            composite = data.get("composite", False)
            if composite:
                self._show_composite_group_context_menu(menu, data.get("name", ""))
            else:
                self._show_group_context_menu(menu, data.get("name", ""))

        menu.exec(self.node_tree.mapToGlobal(position))

    # ---- 全局右键菜单 ----

    def _show_global_context_menu(self, position):
        menu = QMenu(self)

        ActionFactory.create_action(self, "group.create", self._make_ctx(), menu)

        menu.addSeparator()

        ActionFactory.create_action(self, "node.select_all", self._make_ctx(), menu)
        ActionFactory.create_action(self, "node.deselect_all", self._make_ctx(), menu)

        menu.addSeparator()

        ActionFactory.create_action(self, "node.refresh", menu=menu)

        menu.exec(self.node_tree.mapToGlobal(position))

    # ---- 节点右键菜单 ----

    def _show_node_context_menu(self, menu, node_name):
        selected_nodes = self.get_selected_nodes()
        ctx = self._make_ctx()

        if len(selected_nodes) > 1 and node_name in selected_nodes:
            self._show_batch_node_menu(menu, selected_nodes)
        else:
            self._show_single_node_menu(menu, node_name, ctx)

    def _show_single_node_menu(self, menu, node_name, ctx):
        """单个节点右键菜单"""
        # 添加到画布
        ActionFactory.create_action(self, "node.add_to_canvas", self._make_ctx(node_name=node_name), menu)
        menu.addSeparator()

        # 移动到组子菜单
        move_menu = menu.addMenu(t("k_group_move"))
        groups = self.group_manager.get_all_groups()
        if groups:
            for gn in sorted(groups.keys()):
                action = move_menu.addAction(gn)
                action.triggered.connect(
                    lambda checked, gn=gn: self._dispatch("group.move_to", node_name=node_name, group_name=gn)
                )
        else:
            move_menu.addAction(t("k_group_no_available")).setEnabled(False)

        # 从组中移除
        current_group = self.group_manager.get_node_group(node_name)
        if current_group:
            action = menu.addAction(t("_k_group_remove_from").format(group=current_group))
            action.triggered.connect(lambda: self._dispatch("group.remove_from", node_name=node_name))

        menu.addSeparator()

        # 启动 / 停止
        node_info = self.nodes_data.get(node_name, {})
        if node_info.get("status") in ("running", "idle"):
            ActionFactory.create_action(self, "node.stop", ctx, menu)
        else:
            ActionFactory.create_action(self, "node.start", ctx, menu)

        menu.addSeparator()

        # 重命名
        ActionFactory.create_action(self, "node.rename", self._make_ctx(node_name=node_name), menu)
        menu.addSeparator()

        # 打开文件夹 / 查看日志 / 编辑配置
        node_ctx = self._make_ctx(node_name=node_name)
        ActionFactory.create_action(self, "node.open_folder", node_ctx, menu)
        ActionFactory.create_action(self, "node.view_log", node_ctx, menu)
        menu.addSeparator()
        ActionFactory.create_action(self, "node.edit_config", node_ctx, menu)

        # 挂载 / 卸载 / 删除
        node_info = self.nodes_data.get(node_name, {})
        if node_info.get("mounted"):
            ActionFactory.create_action(self, "node.unmount", node_ctx, menu)
        if not node_info.get("mounted"):
            ActionFactory.create_action(self, "node.delete", node_ctx, menu)

        menu.addSeparator()

        ActionFactory.create_action(self, "node.export", ctx, menu)

    def _show_batch_node_menu(self, menu, selected_nodes):
        """批量选中节点右键菜单"""
        n = len(selected_nodes)
        ctx = self._make_ctx(node_list=selected_nodes)

        # 批量标签
        ActionFactory.add_disabled_label(menu, t("_k_selected_count").format(count=n))
        menu.addSeparator()

        # 批量添加画布
        ActionFactory.create_action(
            self,
            "node.batch_add_to_canvas",
            ctx,
            menu,
            label=t("_k_add_n_to_canvas").format(count=n),
        )
        menu.addSeparator()

        # 移动到组子菜单
        move_menu = menu.addMenu(t("k_group_move"))
        groups = self.group_manager.get_all_groups()
        if groups:
            for gn in sorted(groups.keys()):
                move_ctx = self._make_ctx(node_list=selected_nodes, group_name=gn)
                ActionFactory.create_action(
                    self,
                    "group.batch_move_to",
                    move_ctx,
                    move_menu,
                    label=gn,
                )
        else:
            move_menu.addAction(t("k_group_no_available")).setEnabled(False)

        # 从共同组中批量移除
        common_group = self._get_common_group(selected_nodes)
        if common_group:
            remove_ctx = self._make_ctx(node_list=selected_nodes, group_name=common_group)
            ActionFactory.create_action(
                self,
                "group.batch_remove_from",
                remove_ctx,
                menu,
                label=t("_k_group_remove_from").format(group=common_group),
            )

        menu.addSeparator()

        # 批量启动 / 停止（通过 ActionFactory，使用 node_list context）
        ActionFactory.create_action(self, "node.start", ctx, menu)
        ActionFactory.create_action(self, "node.stop", ctx, menu)

        menu.addSeparator()

        # 批量打开文件夹 / 查看日志 / 编辑配置 / 删除
        ActionFactory.create_action(
            self,
            "node.batch_open_folders",
            ctx,
            menu,
            label=t("_k_open_n_dirs").format(count=n),
        )

        ActionFactory.create_action(
            self,
            "node.batch_view_logs",
            ctx,
            menu,
            label=t("_k_view_n_logs").format(count=n),
        )

        menu.addSeparator()

        ActionFactory.create_action(
            self,
            "node.batch_edit_configs",
            ctx,
            menu,
            label=t("_k_edit_n_configs").format(count=n),
        )

        menu.addSeparator()

        ActionFactory.create_action(
            self,
            "node.batch_delete",
            ctx,
            menu,
            label=t("_k_delete_n_nodes").format(count=n),
        )

    def export_single_node(self, node_name):
        """导出单个节点（委托给主窗口）"""
        if self.parent_window and hasattr(self.parent_window, "export_node"):
            self.parent_window.export_node(node_name)

    # ---- 组右键菜单 ----

    def _show_group_context_menu(self, menu, group_name):
        """显示组右键菜单"""
        group_nodes = self.group_manager.get_group_nodes(group_name)
        is_locked = self.group_manager.is_group_locked(group_name)

        lock_tag = "🔒 " if is_locked else ""
        menu.addAction(t("_k_group_info").format(lock=lock_tag, name=group_name)).setEnabled(False)
        menu.addAction(t("_k_group_node_count").format(count=len(group_nodes))).setEnabled(False)
        menu.addSeparator()

        active_count = sum(1 for n in group_nodes if self.nodes_data.get(n, {}).get("status") in ("running", "idle"))
        stopped_count = len(group_nodes) - active_count

        # 启动 / 停止组节点
        group_ctx = self._make_ctx(group_name=group_name)
        if stopped_count > 0:
            ActionFactory.create_action(
                self,
                "group.start",
                group_ctx,
                menu,
                label=t("_k_start_group_nodes").format(count=stopped_count),
            )
        if active_count > 0:
            ActionFactory.create_action(
                self,
                "group.stop",
                group_ctx,
                menu,
                label=t("_k_stop_group_nodes").format(count=active_count),
            )

        menu.addSeparator()

        if not is_locked:
            ActionFactory.create_action(self, "group.rename", group_ctx, menu)
        if not is_locked:
            ActionFactory.create_action(self, "group.delete", group_ctx, menu)

        menu.addSeparator()

        ActionFactory.create_action(self, "group.toggle_expand", group_ctx, menu)

    # ---- 复合节点组右键菜单 ----

    def _show_composite_group_context_menu(self, menu, group_name):
        """显示复合节点组专用右键菜单（不显示 rename/delete/lock 等普通组操作）"""
        group_nodes = self.group_manager.get_group_nodes(group_name)

        menu.addAction(f"\u229e \u590d\u5408\u8282\u70b9\u7ec4: {len(group_nodes)} \u4e2a\u8282\u70b9").setEnabled(
            False
        )
        menu.addSeparator()

        # 重命名
        rename_action = menu.addAction("\u91cd\u547d\u540d\u590d\u5408\u8282\u70b9")
        rename_action.triggered.connect(lambda: self._rename_composite_group(group_name))

        menu.addSeparator()

        # 解耦
        decompress_action = menu.addAction("\u89e3\u8026\u4e3a\u72ec\u7acb\u8282\u70b9")
        decompress_action.triggered.connect(lambda: self._decompress_composite_group(group_name))

        menu.addSeparator()

        active_count = sum(1 for n in group_nodes if self.nodes_data.get(n, {}).get("status") in ("running", "idle"))
        stopped_count = len(group_nodes) - active_count

        if stopped_count > 0:
            action = menu.addAction(f"\u542f\u52a8\u590d\u5408\u8282\u70b9 ({stopped_count})")
            action.triggered.connect(lambda: self._start_composite_group(group_name))
        if active_count > 0:
            action = menu.addAction(f"\u505c\u6b62\u590d\u5408\u8282\u70b9 ({active_count})")
            action.triggered.connect(lambda: self._stop_composite_group(group_name))

        menu.addSeparator()

        ActionFactory.create_action(self, "group.toggle_expand", self._make_ctx(group_name=group_name), menu)

    def _rename_composite_group(self, group_name):
        """重命名复合节点的展示名称（保护 composite_ 前缀）。"""
        parent = self.parent_window
        if not parent:
            return

        comp_id = (
            group_name[len(CompositeNode.GROUP_PREFIX) :]
            if group_name.startswith(CompositeNode.GROUP_PREFIX)
            else group_name
        )

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QLineEdit,
            QPushButton,
            QSizePolicy,
            QSpacerItem,
            QVBoxLayout,
        )

        from ui.core.utils.dialog_utils import themed_message
        from ui.panels.node_list_panel import NodeListPanel

        canvas = self._get_canvas(parent)
        if not canvas:
            return
        project_path = getattr(parent, "current_project_path", None)
        if not project_path:
            return
        group_mgr = self.group_manager

        mgr = getattr(canvas, "_composite_manager", None)
        if not mgr:
            mgr = CompositeNode(project_path, canvas, group_mgr)
            canvas._composite_manager = mgr

        # 运行态保护
        if mgr.is_running(comp_id):
            if parent:
                parent.show_toast("复合节点正在运行中，请先停止后再重命名", "warning")
            return

        current_display = mgr._composites.get(comp_id, {}).get("display_name", "")
        old_name = current_display or comp_id
        prefix, suffix, read_only_prefix = NodeListPanel._split_protected_prefix(old_name)

        if not current_display:
            if comp_id.startswith("composite_"):
                prefix = "composite_"
                suffix = comp_id[len("composite_") :]
                read_only_prefix = True
            else:
                prefix = ""
                suffix = old_name
                read_only_prefix = False

        dlg = QDialog(self)
        dlg.setWindowTitle("重命名复合节点")
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        dlg.setMinimumWidth(380)
        if self.styleSheet():
            dlg.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(16, 14, 16, 10)
        layout.setSpacing(8)

        title_label = QLabel("重命名复合节点")
        title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #ccc;")
        layout.addWidget(title_label)

        layout.addWidget(QLabel("请输入新的展示名称（留空则恢复 hex ID 显示）："))

        row = QHBoxLayout()
        row.setSpacing(4)
        if read_only_prefix:
            prefix_label = QLabel(prefix)
            prefix_label.setStyleSheet(
                "color: #888; background: #2a2a2a; border: 1px solid #444; "
                "border-right: none; border-radius: 3px 0 0 3px; padding: 4px 8px;"
            )
            row.addWidget(prefix_label)

        line_edit = QLineEdit(suffix)
        line_edit.selectAll()
        if read_only_prefix:
            line_edit.setStyleSheet("border: 1px solid #444; border-radius: 0 3px 3px 0; padding: 4px 8px;")
        else:
            line_edit.setStyleSheet("border: 1px solid #444; border-radius: 3px; padding: 4px 8px;")
        row.addWidget(line_edit, 1)
        layout.addLayout(row)

        btn_layout = QHBoxLayout()
        btn_layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedWidth(70)
        cancel_btn.clicked.connect(dlg.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("确定")
        ok_btn.setFixedWidth(70)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(dlg.accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

        ok = dlg.exec() == QDialog.DialogCode.Accepted
        if not ok:
            return

        suffix_input = line_edit.text().strip()
        import re

        if suffix_input and not re.match(r"^[a-zA-Z0-9_-]+$", suffix_input):
            themed_message(self, "警告", "名称只能包含字母、数字、下划线和短横线", "warning")
            return

        new_name = (prefix + suffix_input) if read_only_prefix else suffix_input

        try:
            mgr.rename(comp_id, new_name)
        except ValueError as e:
            if parent:
                parent.show_toast(str(e), "error")
            return

        # 刷新节点列表
        self.update_node_list(self.nodes_data)

        themed_message(self, "成功", f"复合节点已重命名为：{new_name}", "info")

    def _decompress_composite_group(self, group_name):
        """从节点列表解耦复合节点。"""
        parent = self.parent_window
        if not parent:
            return
        canvas = self._get_canvas(parent)
        if not canvas:
            return
        mgr = getattr(canvas, "_composite_manager", None)
        if not mgr:
            project_path = getattr(parent, "current_project_path", None)
            if not project_path:
                return
            group_mgr = self.group_manager
            mgr = CompositeNode(project_path, canvas, group_mgr)
            canvas._composite_manager = mgr

        # 从组名提取 comp_id
        comp_id = (
            group_name[len(CompositeNode.GROUP_PREFIX) :]
            if group_name.startswith(CompositeNode.GROUP_PREFIX)
            else group_name
        )
        mgr.decompress(comp_id)

    def _start_composite_group(self, group_name):
        """从节点列表启动复合节点 - 通过启动队列。"""
        parent = self.parent_window
        if not parent:
            return
        comp_id = (
            group_name[len(CompositeNode.GROUP_PREFIX) :]
            if group_name.startswith(CompositeNode.GROUP_PREFIX)
            else group_name
        )
        from ui.core.node.node_startup_queue import startup_queue

        startup_queue.enqueue(comp_id)
        if parent:
            parent.show_toast(f"复合节点 {comp_id} 已加入启动队列", "info")

    def _stop_composite_group(self, group_name):
        """从节点列表停止复合节点。"""
        parent = self.parent_window
        if not parent:
            return
        canvas = self._get_canvas(parent)
        if not canvas:
            return
        mgr = self._ensure_composite_manager(canvas)
        if not mgr:
            return
        comp_id = (
            group_name[len(CompositeNode.GROUP_PREFIX) :]
            if group_name.startswith(CompositeNode.GROUP_PREFIX)
            else group_name
        )
        mgr.stop_composite(comp_id)

    def _get_canvas(self, parent):
        """从主窗口获取画布引用。"""
        if hasattr(parent, "canvas"):
            return parent.canvas
        if hasattr(parent, "centralWidget"):
            cw = parent.centralWidget()
            if hasattr(cw, "canvas"):
                return cw.canvas
        return None

    def _ensure_composite_manager(self, canvas):
        """确保复合节点管理器存在。"""
        if hasattr(canvas, "_composite_manager") and canvas._composite_manager:
            return canvas._composite_manager
        parent = self.parent_window
        if not parent:
            return None
        project_path = getattr(parent, "current_project_path", None)
        if not project_path:
            return None
        canvas._composite_manager = CompositeNode(project_path, canvas, self.group_manager)
        return canvas._composite_manager

    # ---- 未分组类别菜单 ----

    def _show_ungrouped_category_menu(self, menu):
        """显示未分组类别菜单"""
        all_nodes = list(self.nodes_data.keys())
        ungrouped_nodes = self.group_manager.get_ungrouped_nodes(all_nodes)

        menu.addAction(t("_k_ungrouped_nodes")).setEnabled(False)
        menu.addAction(t("_k_ungrouped_count").format(count=len(ungrouped_nodes))).setEnabled(False)
        menu.addSeparator()

        stopped_count = sum(1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get("status") == "stopped")
        if stopped_count > 0:
            action = menu.addAction(t("_k_start_ungrouped").format(count=stopped_count))
            action.triggered.connect(lambda: self._dispatch("ungrouped.start"))

        active_count = sum(
            1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get("status") in ("running", "idle")
        )
        if active_count > 0:
            action = menu.addAction(t("_k_stop_ungrouped").format(count=active_count))
            action.triggered.connect(lambda: self._dispatch("ungrouped.stop"))

        menu.addSeparator()

        create_and_move = menu.addAction(t("k_group_new_and_move"))
        create_and_move.triggered.connect(lambda: self.create_group_from_ungrouped(ungrouped_nodes))

    # ---- 挂载 ----

    def _unmount_node(self, node_name):
        """卸载外部挂载节点（委托给主窗口）"""
        if self.parent_window and hasattr(self.parent_window, "unmount_external_node"):
            reply = themed_message(
                self, t("k_title_confirm_unmount"), t("_k_confirm_unmount").format(name=node_name), "question"
            )
            if reply:
                self.parent_window.unmount_external_node(node_name)
