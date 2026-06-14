"""
节点列表右键菜单系统 Mixin — 统一使用 ActionRegistry + ActionFactory
所有操作通过 Action 系统分发，菜单与菜单栏共用同一套功能注册表
"""
from PySide6.QtWidgets import QMenu
from ui.core.utils.dialog_utils import themed_message
from PySide6.QtCore import Qt
from ui.core.i18n import t
from ui.core.actions import ActionFactory, ActionContext, ActionRegistry
from ui.core.actions.builtin_node_actions import register_node_actions


class NodeListContextMixin:
    """节点列表右键菜单（Mixin 注入到 NodeListPanel）"""

    # ---- helpers ----

    def _make_ctx(self, **kwargs):
        """构建 ActionContext，自动注入 panel 引用"""
        return ActionContext(**(kwargs | {'extra': {'panel': self}}))

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
        if data.get('type') == 'node':
            self._show_node_context_menu(menu, data['name'])
        elif data.get('type') == 'group':
            self._show_group_context_menu(menu, data['name'])

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
        ActionFactory.create_action(self, "node.add_to_canvas",
                                     self._make_ctx(node_name=node_name), menu)
        menu.addSeparator()

        # 移动到组子菜单
        move_menu = menu.addMenu(t("k_group_move"))
        groups = self.group_manager.get_all_groups()
        if groups:
            for gn in sorted(groups.keys()):
                action = move_menu.addAction(gn)
                action.triggered.connect(
                    lambda checked, gn=gn: self._dispatch("group.move_to",
                                                          node_name=node_name, group_name=gn))
        else:
            move_menu.addAction(t("k_group_no_available")).setEnabled(False)

        # 从组中移除
        current_group = self.group_manager.get_node_group(node_name)
        if current_group:
            action = menu.addAction(
                t("_k_group_remove_from").format(group=current_group))
            action.triggered.connect(
                lambda: self._dispatch("group.remove_from", node_name=node_name))

        menu.addSeparator()

        # 启动 / 停止
        node_info = self.nodes_data.get(node_name, {})
        if node_info.get('status') in ('running', 'idle'):
            ActionFactory.create_action(self, "node.stop", ctx, menu)
        else:
            ActionFactory.create_action(self, "node.start", ctx, menu)

        menu.addSeparator()

        # 重命名
        ActionFactory.create_action(self, "node.rename",
                                     self._make_ctx(node_name=node_name), menu)
        menu.addSeparator()

        # 打开文件夹 / 查看日志 / 编辑配置
        node_ctx = self._make_ctx(node_name=node_name)
        ActionFactory.create_action(self, "node.open_folder", node_ctx, menu)
        ActionFactory.create_action(self, "node.view_log", node_ctx, menu)
        menu.addSeparator()
        ActionFactory.create_action(self, "node.edit_config", node_ctx, menu)

        # 挂载 / 卸载 / 删除
        node_info = self.nodes_data.get(node_name, {})
        if node_info.get('mounted'):
            ActionFactory.create_action(self, "node.unmount", node_ctx, menu)
        if not node_info.get('mounted'):
            ActionFactory.create_action(self, "node.delete", node_ctx, menu)

        menu.addSeparator()

        ActionFactory.create_action(self, "node.export", ctx, menu)

    def _show_batch_node_menu(self, menu, selected_nodes):
        """批量选中节点右键菜单"""
        n = len(selected_nodes)
        ctx = self._make_ctx(node_list=selected_nodes)

        # 批量标签
        ActionFactory.add_disabled_label(menu, "_k_selected_count".format(count=n))
        menu.addSeparator()

        # 批量添加画布（动态名称，手动创建 action 但走 ActionRegistry）
        batch_add = menu.addAction(t("_k_add_n_to_canvas").format(count=n))
        batch_add.triggered.connect(lambda: self._dispatch("node.batch_add_to_canvas"))
        menu.addSeparator()

        # 移动到组子菜单
        move_menu = menu.addMenu(t("k_group_move"))
        groups = self.group_manager.get_all_groups()
        if groups:
            for gn in sorted(groups.keys()):
                action = move_menu.addAction(gn)
                action.triggered.connect(
                    lambda checked, gn=gn: self._dispatch("group.batch_move_to",
                                                          group_name=gn))
        else:
            move_menu.addAction(t("k_group_no_available")).setEnabled(False)

        # 从共同组中批量移除
        common_group = self._get_common_group(selected_nodes)
        if common_group:
            action = menu.addAction(
                t("_k_group_remove_from").format(group=common_group))
            action.triggered.connect(
                lambda: self._dispatch("group.batch_remove_from",
                                       group_name=common_group))

        menu.addSeparator()

        # 批量启动 / 停止（通过 ActionFactory，使用 node_list context）
        ActionFactory.create_action(self, "node.start", ctx, menu)
        ActionFactory.create_action(self, "node.stop", ctx, menu)

        menu.addSeparator()

        # 批量打开文件夹 / 查看日志
        batch_open = menu.addAction(t("_k_open_n_dirs").format(count=n))
        batch_open.triggered.connect(lambda: self._dispatch("node.batch_open_folders"))

        batch_log = menu.addAction(t("_k_view_n_logs").format(count=n))
        batch_log.triggered.connect(lambda: self._dispatch("node.batch_view_logs"))

        menu.addSeparator()

        # 批量编辑配置
        batch_edit = menu.addAction(t("_k_edit_n_configs").format(count=n))
        batch_edit.triggered.connect(lambda: self._dispatch("node.batch_edit_configs"))

        menu.addSeparator()

        # 批量删除
        batch_del = menu.addAction(t("_k_delete_n_nodes").format(count=n))
        batch_del.triggered.connect(lambda: self._dispatch("node.batch_delete"))

    def export_single_node(self, node_name):
        """导出单个节点（委托给主窗口）"""
        if self.parent_window and hasattr(self.parent_window, 'export_node'):
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

        active_count = sum(1 for n in group_nodes
                           if self.nodes_data.get(n, {}).get('status') in ('running', 'idle'))
        stopped_count = len(group_nodes) - active_count

        # 启动 / 停止组节点（动态名称，手动创建但走 Registry）
        group_ctx = self._make_ctx(group_name=group_name)
        if stopped_count > 0:
            action = menu.addAction(t("_k_start_group_nodes").format(count=stopped_count))
            action.triggered.connect(lambda: self._dispatch("group.start", group_name=group_name))
        if active_count > 0:
            action = menu.addAction(t("_k_stop_group_nodes").format(count=active_count))
            action.triggered.connect(lambda: self._dispatch("group.stop", group_name=group_name))

        menu.addSeparator()

        if not is_locked:
            ActionFactory.create_action(self, "group.rename", group_ctx, menu)
        if not is_locked:
            ActionFactory.create_action(self, "group.delete", group_ctx, menu)

        menu.addSeparator()

        ActionFactory.create_action(self, "group.toggle_expand", group_ctx, menu)

    # ---- 未分组类别菜单 ----

    def _show_ungrouped_category_menu(self, menu):
        """显示未分组类别菜单"""
        all_nodes = list(self.nodes_data.keys())
        ungrouped_nodes = self.group_manager.get_ungrouped_nodes(all_nodes)

        menu.addAction(t("_k_ungrouped_nodes")).setEnabled(False)
        menu.addAction(t("_k_ungrouped_count").format(count=len(ungrouped_nodes))).setEnabled(False)
        menu.addSeparator()

        stopped_count = sum(1 for n in ungrouped_nodes
                            if self.nodes_data.get(n, {}).get('status') == 'stopped')
        if stopped_count > 0:
            action = menu.addAction(t("_k_start_ungrouped").format(count=stopped_count))
            action.triggered.connect(lambda: self._dispatch("ungrouped.start"))

        active_count = sum(1 for n in ungrouped_nodes
                           if self.nodes_data.get(n, {}).get('status') in ('running', 'idle'))
        if active_count > 0:
            action = menu.addAction(t("_k_stop_ungrouped").format(count=active_count))
            action.triggered.connect(lambda: self._dispatch("ungrouped.stop"))

        menu.addSeparator()

        create_and_move = menu.addAction(t("k_group_new_and_move"))
        create_and_move.triggered.connect(lambda: self.create_group_from_ungrouped(ungrouped_nodes))

    # ---- 挂载 ----

    def _unmount_node(self, node_name):
        """卸载外部挂载节点（委托给主窗口）"""
        if self.parent_window and hasattr(self.parent_window, 'unmount_external_node'):
            reply = themed_message(self, t("k_title_confirm_unmount"),
                t("_k_confirm_unmount").format(name=node_name), "question")
            if reply:
                self.parent_window.unmount_external_node(node_name)
