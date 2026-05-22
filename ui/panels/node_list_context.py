"""
节点列表右键菜单系统 Mixin — 空白/节点/组/未分组 多层菜单构建
"""
from PyQt6.QtWidgets import QMenu, QMessageBox
from PyQt6.QtCore import Qt
from ui.core.i18n import t


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
        
        create_group_action = menu.addAction("创建分组")
        create_group_action.triggered.connect(self.create_node_group)
        
        menu.addSeparator()
        
        select_all_action = menu.addAction("全选节点")
        select_all_action.triggered.connect(self.select_all_nodes)
        
        deselect_all_action = menu.addAction("取消选择")
        deselect_all_action.triggered.connect(self.deselect_all_nodes)
        
        menu.addSeparator()
        
        refresh_action = menu.addAction("刷新列表")
        refresh_action.triggered.connect(lambda: self.update_node_list(self.nodes_data))
        
        menu.exec(self.node_tree.mapToGlobal(position))

    def _show_node_context_menu(self, menu, node_name):
        """显示节点右键菜单"""
        selected_nodes = self.get_selected_nodes()
        
        if len(selected_nodes) > 1 and node_name in selected_nodes:
            # ---- 批量操作 ----
            menu.addAction(f"已选 {len(selected_nodes)} 个节点").setEnabled(False)
            menu.addSeparator()
            
            batch_add_action = menu.addAction(f"添加 {len(selected_nodes)} 个节点到画布")
            batch_add_action.triggered.connect(self.batch_add_nodes_to_canvas)
            
            menu.addSeparator()
            
            move_to_group_menu = menu.addMenu("移动分组")
            groups = self.group_manager.get_all_groups()
            if groups:
                for group_name in sorted(groups.keys()):
                    action = move_to_group_menu.addAction(group_name)
                    action.triggered.connect(lambda checked, gn=group_name: self.batch_move_nodes_to_group(gn))
            else:
                move_to_group_menu.addAction("（无可用组）").setEnabled(False)
            
            common_group = self._get_common_group(selected_nodes)
            if common_group:
                remove_from_group_action = menu.addAction(f"从组 '{common_group}' 移除选中节点")
                remove_from_group_action.triggered.connect(lambda: self.batch_remove_nodes_from_group(common_group))
            
            menu.addSeparator()
            
            batch_start_action = menu.addAction(f"启动 {len(selected_nodes)} 个节点")
            batch_start_action.triggered.connect(self.batch_start_nodes)
            
            batch_stop_action = menu.addAction(f"停止 {len(selected_nodes)} 个节点")
            batch_stop_action.triggered.connect(self.batch_stop_nodes)
            
            menu.addSeparator()
            
            batch_open_folder_action = menu.addAction(f"打开 {len(selected_nodes)} 个节点目录")
            batch_open_folder_action.triggered.connect(self.batch_open_node_folders)
            
            batch_view_log_action = menu.addAction(f"查看 {len(selected_nodes)} 个节点日志")
            batch_view_log_action.triggered.connect(self.batch_view_node_logs)
            
            menu.addSeparator()
            
            batch_edit_config_action = menu.addAction(f"编辑 {len(selected_nodes)} 个节点配置")
            batch_edit_config_action.triggered.connect(self.batch_edit_node_configs)
            
            menu.addSeparator()
            
            batch_delete_action = menu.addAction(f"删除 {len(selected_nodes)} 个节点")
            batch_delete_action.triggered.connect(self.batch_delete_nodes)
        else:
            # ---- 单节点操作 ----
            add_to_canvas_action = menu.addAction(t("k_canvas_add_to"))
            add_to_canvas_action.triggered.connect(lambda: self.add_node_to_canvas(node_name))
            
            menu.addSeparator()
            
            move_to_group_menu = menu.addMenu("移动分组")
            groups = self.group_manager.get_all_groups()
            if groups:
                for group_name in sorted(groups.keys()):
                    action = move_to_group_menu.addAction(group_name)
                    action.triggered.connect(lambda checked, gn=group_name: self.move_node_to_group(node_name, gn))
            else:
                move_to_group_menu.addAction("（无可用组）").setEnabled(False)
            
            current_group = self.group_manager.get_node_group(node_name)
            if current_group:
                remove_from_group_action = menu.addAction(f"从组 '{current_group}' 移除")
                remove_from_group_action.triggered.connect(lambda: self.remove_node_from_group(node_name))
            
            menu.addSeparator()
            
            node_info = self.nodes_data.get(node_name, {})
            if node_info.get('status') == 'running':
                stop_action = menu.addAction(t("k_node_stop"))
                stop_action.triggered.connect(lambda: self._stop_single_node(node_name))
            else:
                start_action = menu.addAction(t("k_node_start"))
                start_action.triggered.connect(lambda: self._start_single_node(node_name))
            
            menu.addSeparator()
            
            rename_action = menu.addAction(t("k_node_rename"))
            rename_action.triggered.connect(lambda: self.rename_node(node_name))
            
            menu.addSeparator()
            
            open_folder_action = menu.addAction(t("k_open_dir"))
            open_folder_action.triggered.connect(lambda: self.open_node_folder(node_name))
            
            view_log_action = menu.addAction("查看日志")
            view_log_action.triggered.connect(lambda: self.view_node_log(node_name))
            
            menu.addSeparator()
            
            edit_config_action = menu.addAction("编辑配置")
            edit_config_action.triggered.connect(lambda: self.edit_node_config(node_name))
            
            node_info = self.nodes_data.get(node_name, {})
            if node_info.get('mounted'):
                unmount_action = menu.addAction("卸载外部节点")
                unmount_action.triggered.connect(lambda: self._unmount_node(node_name))
            
            if not node_info.get('mounted'):
                delete_action = menu.addAction("删除节点")
                delete_action.triggered.connect(lambda: self.delete_node(node_name))

    def _unmount_node(self, node_name):
        """卸载外部挂载节点（委托给主窗口）"""
        if self.parent_window and hasattr(self.parent_window, 'unmount_external_node'):
            reply = QMessageBox.question(
                self, "确认卸载",
                f"确定要卸载外部节点 '{node_name}' 吗？\n节点文件夹不会被删除。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.parent_window.unmount_external_node(node_name)

    def _show_group_context_menu(self, menu, group_name):
        """显示组右键菜单"""
        group_nodes = self.group_manager.get_group_nodes(group_name)
        is_locked = self.group_manager.is_group_locked(group_name)
        
        lock_tag = "🔒 " if is_locked else ""
        menu.addAction(f"{lock_tag}组: {group_name}").setEnabled(False)
        menu.addAction(f"   节点数: {len(group_nodes)}").setEnabled(False)
        menu.addSeparator()
        
        running_count = sum(1 for n in group_nodes if self.nodes_data.get(n, {}).get('status') == 'running')
        stopped_count = len(group_nodes) - running_count
        
        if stopped_count > 0:
            start_group_action = menu.addAction(f"启动组内所有节点 ({stopped_count}个)")
            start_group_action.triggered.connect(lambda: self.start_group_nodes(group_name))
        
        if running_count > 0:
            stop_group_action = menu.addAction(f"停止组内所有节点 ({running_count}个)")
            stop_group_action.triggered.connect(lambda: self.stop_group_nodes(group_name))
        
        menu.addSeparator()
        
        if not is_locked:
            rename_group_action = menu.addAction("重命名组")
            rename_group_action.triggered.connect(lambda: self.rename_group(group_name))
        
        if not is_locked:
            delete_group_action = menu.addAction("删除组")
            delete_group_action.triggered.connect(lambda: self.delete_group(group_name))
        
        menu.addSeparator()
        
        expand_action = menu.addAction("展开折叠")
        expand_action.triggered.connect(lambda: self.toggle_group_expansion(group_name))

    def _show_ungrouped_category_menu(self, menu):
        """显示未分组类别菜单"""
        all_nodes = list(self.nodes_data.keys())
        ungrouped_nodes = self.group_manager.get_ungrouped_nodes(all_nodes)
        
        menu.addAction(f"未分组节点").setEnabled(False)
        menu.addAction(f"   数量: {len(ungrouped_nodes)}").setEnabled(False)
        menu.addSeparator()
        
        stopped_count = sum(1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get('status') == 'stopped')
        if stopped_count > 0:
            start_ungrouped_action = menu.addAction(f"启动所有未分组节点 ({stopped_count}个)")
            start_ungrouped_action.triggered.connect(self.start_ungrouped_nodes)
        
        running_count = sum(1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get('status') == 'running')
        if running_count > 0:
            stop_ungrouped_action = menu.addAction(f"停止所有未分组节点 ({running_count}个)")
            stop_ungrouped_action.triggered.connect(self.stop_ungrouped_nodes)
        
        menu.addSeparator()
        
        create_and_move_action = menu.addAction("新建分组并移入")
        create_and_move_action.triggered.connect(lambda: self.create_group_from_ungrouped(ungrouped_nodes))
