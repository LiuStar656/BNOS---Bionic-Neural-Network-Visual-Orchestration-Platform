"""
节点列表右键菜单系统 Mixin — 使用统一 ActionRegistry
"""
from PyQt6.QtWidgets import QMenu, QMessageBox
from ui.core.utils.dialog_utils import themed_message
from PyQt6.QtCore import Qt
from ui.core.i18n import t
from ui.core.actions import ActionFactory, ActionContext
from ui.core.actions.builtin_node_actions import register_node_actions


class NodeListContextMixin:
    """节点列表右键菜单（Mixin 注入到 NodeListPanel）"""

    def show_context_menu(self, position):
        """显示右键菜单 - 所有功能的统一入口"""
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
            node_name = data['name']
            self._show_node_context_menu(menu, node_name)
        elif data.get('type') == 'group':
            group_name = data['name']
            self._show_group_context_menu(menu, group_name)
        
        menu.exec(self.node_tree.mapToGlobal(position))

    def _show_global_context_menu(self, position):
        """显示全局右键菜单（空白处）"""
        menu = QMenu(self)
        
        create_group_action = menu.addAction(t("k_group_create"))
        create_group_action.triggered.connect(self.create_node_group)
        
        menu.addSeparator()
        
        select_all_action = menu.addAction(t("k_select_all"))
        select_all_action.triggered.connect(self.select_all_nodes)
        
        deselect_all_action = menu.addAction(t("k_select_cancel"))
        deselect_all_action.triggered.connect(self.deselect_all_nodes)
        
        menu.addSeparator()
        
        ActionFactory.create_action(self, "node.refresh", menu)
        
        menu.exec(self.node_tree.mapToGlobal(position))

    def _show_node_context_menu(self, menu, node_name):
        """显示节点右键菜单"""
        selected_nodes = self.get_selected_nodes()
        
        if len(selected_nodes) > 1 and node_name in selected_nodes:
            n = len(selected_nodes)
            ActionFactory.add_disabled_label(menu, "_k_selected_count".format(count=n))
            menu.addSeparator()
            
            batch_add_action = menu.addAction(t("_k_add_n_to_canvas").format(count=n))
            batch_add_action.triggered.connect(self.batch_add_nodes_to_canvas)
            
            menu.addSeparator()
            
            move_to_group_menu = menu.addMenu(t("k_group_move"))
            groups = self.group_manager.get_all_groups()
            if groups:
                for group_name in sorted(groups.keys()):
                    action = move_to_group_menu.addAction(group_name)
                    action.triggered.connect(lambda checked, gn=group_name: self.batch_move_nodes_to_group(gn))
            else:
                move_to_group_menu.addAction(t("k_group_no_available")).setEnabled(False)
            
            common_group = self._get_common_group(selected_nodes)
            if common_group:
                remove_from_group_action = menu.addAction(
                    t("_k_group_remove_from").format(group=common_group))
                remove_from_group_action.triggered.connect(lambda: self.batch_remove_nodes_from_group(common_group))
            
            menu.addSeparator()
            
            ctx = ActionContext(node_list=selected_nodes)
            ActionFactory.create_action(self, "node.start", ctx, menu)
            ActionFactory.create_action(self, "node.stop", ctx, menu)
            
            menu.addSeparator()
            
            batch_open_folder_action = menu.addAction(t("_k_open_n_dirs").format(count=n))
            batch_open_folder_action.triggered.connect(self.batch_open_node_folders)
            
            batch_view_log_action = menu.addAction(t("_k_view_n_logs").format(count=n))
            batch_view_log_action.triggered.connect(self.batch_view_node_logs)
            
            menu.addSeparator()
            
            batch_edit_config_action = menu.addAction(t("_k_edit_n_configs").format(count=n))
            batch_edit_config_action.triggered.connect(self.batch_edit_node_configs)
            
            menu.addSeparator()
            
            batch_delete_action = menu.addAction(t("_k_delete_n_nodes").format(count=n))
            batch_delete_action.triggered.connect(self.batch_delete_nodes)
        else:
            add_to_canvas_action = menu.addAction(t("k_canvas_add_to"))
            add_to_canvas_action.triggered.connect(lambda: self.add_node_to_canvas(node_name))
            
            menu.addSeparator()
            
            move_to_group_menu = menu.addMenu(t("k_group_move"))
            groups = self.group_manager.get_all_groups()
            if groups:
                for group_name in sorted(groups.keys()):
                    action = move_to_group_menu.addAction(group_name)
                    action.triggered.connect(lambda checked, gn=group_name: self.move_node_to_group(node_name, gn))
            else:
                move_to_group_menu.addAction(t("k_group_no_available")).setEnabled(False)
            
            current_group = self.group_manager.get_node_group(node_name)
            if current_group:
                remove_from_group_action = menu.addAction(
                    t("_k_group_remove_from").format(group=current_group))
                remove_from_group_action.triggered.connect(lambda: self.remove_node_from_group(node_name))
            
            menu.addSeparator()
            
            ctx = ActionContext(node_name=node_name)
            node_info = self.nodes_data.get(node_name, {})
            if node_info.get('status') in ('running', 'idle'):
                ActionFactory.create_action(self, "node.stop", ctx, menu)
            else:
                ActionFactory.create_action(self, "node.start", ctx, menu)
            
            menu.addSeparator()
            
            rename_action = menu.addAction(t("k_node_rename"))
            rename_action.triggered.connect(lambda: self.rename_node(node_name))
            
            menu.addSeparator()
            
            open_folder_action = menu.addAction(t("k_open_dir"))
            open_folder_action.triggered.connect(lambda: self.open_node_folder(node_name))
            
            view_log_action = menu.addAction(t("k_view_log"))
            view_log_action.triggered.connect(lambda: self.view_node_log(node_name))
            
            menu.addSeparator()
            
            edit_config_action = menu.addAction(t("k_edit_config"))
            edit_config_action.triggered.connect(lambda: self.edit_node_config(node_name))
            
            node_info = self.nodes_data.get(node_name, {})
            if node_info.get('mounted'):
                unmount_action = menu.addAction(t("k_node_unmount"))
                unmount_action.triggered.connect(lambda: self._unmount_node(node_name))
            
            if not node_info.get('mounted'):
                delete_action = menu.addAction(t("k_node_delete"))
                delete_action.triggered.connect(lambda: self.delete_node(node_name))
            
            menu.addSeparator()
            
            ActionFactory.create_action(self, "node.export", ctx, menu)

    def export_single_node(self, node_name):
        """导出单个节点（委托给主窗口）"""
        if self.parent_window and hasattr(self.parent_window, 'export_node'):
            self.parent_window.export_node(node_name)

    def _unmount_node(self, node_name):
        """卸载外部挂载节点（委托给主窗口）"""
        if self.parent_window and hasattr(self.parent_window, 'unmount_external_node'):
            reply = themed_message(self, t("k_title_confirm_unmount"),
                t("_k_confirm_unmount").format(name=node_name),
                "question")
            if reply:
                self.parent_window.unmount_external_node(node_name)

    def _show_group_context_menu(self, menu, group_name):
        """显示组右键菜单"""
        group_nodes = self.group_manager.get_group_nodes(group_name)
        is_locked = self.group_manager.is_group_locked(group_name)
        
        lock_tag = "🔒 " if is_locked else ""
        menu.addAction(t("_k_group_info").format(lock=lock_tag, name=group_name)).setEnabled(False)
        menu.addAction(t("_k_group_node_count").format(count=len(group_nodes))).setEnabled(False)
        menu.addSeparator()
        
        active_count = sum(1 for n in group_nodes if self.nodes_data.get(n, {}).get('status') in ('running', 'idle'))
        stopped_count = len(group_nodes) - active_count
        
        if stopped_count > 0:
            start_group_action = menu.addAction(t("_k_start_group_nodes").format(count=stopped_count))
            start_group_action.triggered.connect(lambda: self.start_group_nodes(group_name))
        
        if active_count > 0:
            stop_group_action = menu.addAction(t("_k_stop_group_nodes").format(count=active_count))
            stop_group_action.triggered.connect(lambda: self.stop_group_nodes(group_name))
        
        menu.addSeparator()
        
        if not is_locked:
            rename_group_action = menu.addAction(t("k_group_rename"))
            rename_group_action.triggered.connect(lambda: self.rename_group(group_name))
        
        if not is_locked:
            delete_group_action = menu.addAction(t("k_group_delete"))
            delete_group_action.triggered.connect(lambda: self.delete_group(group_name))
        
        menu.addSeparator()
        
        expand_action = menu.addAction(t("k_group_expand_collapse"))
        expand_action.triggered.connect(lambda: self.toggle_group_expansion(group_name))

    def _show_ungrouped_category_menu(self, menu):
        """显示未分组类别菜单"""
        all_nodes = list(self.nodes_data.keys())
        ungrouped_nodes = self.group_manager.get_ungrouped_nodes(all_nodes)
        
        menu.addAction(t("_k_ungrouped_nodes")).setEnabled(False)
        menu.addAction(t("_k_ungrouped_count").format(count=len(ungrouped_nodes))).setEnabled(False)
        menu.addSeparator()
        
        stopped_count = sum(1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get('status') == 'stopped')
        if stopped_count > 0:
            start_ungrouped_action = menu.addAction(t("_k_start_ungrouped").format(count=stopped_count))
            start_ungrouped_action.triggered.connect(self.start_ungrouped_nodes)
        
        active_count = sum(1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get('status') in ('running', 'idle'))
        if active_count > 0:
            stop_ungrouped_action = menu.addAction(t("_k_stop_ungrouped").format(count=active_count))
            stop_ungrouped_action.triggered.connect(self.stop_ungrouped_nodes)
        
        menu.addSeparator()
        
        create_and_move_action = menu.addAction(t("k_group_new_and_move"))
        create_and_move_action.triggered.connect(lambda: self.create_group_from_ungrouped(ungrouped_nodes))
