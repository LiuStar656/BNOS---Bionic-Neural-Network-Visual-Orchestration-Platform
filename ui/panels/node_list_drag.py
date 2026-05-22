"""
节点列表拖放系统 Mixin — 处理节点在组之间、组与根级别之间的拖拽移动
"""
from PyQt6.QtCore import Qt
from ui.core.logger import logger
from ui.core.i18n import t


class NodeListDragMixin:
    """节点列表拖放处理（Mixin 注入到 NodeListPanel）"""

    def _intercept_drop_event(self, event, original_drop_event):
        """拦截拖放事件，智能处理节点拖拽
        
        规则：
        - 允许：节点 → 组（正常移动到指定组）
        - 允许：节点 → 根级别（移出组，成为独立节点）
        - 智能转换：节点 → 组内节点（直接融入该节点所在的组）
        - 智能转换：节点 → 根级别节点（创建新组包含两个节点）
        
        注意：所有拖拽操作都在这里处理，不依赖 rowsMoved 信号
        """
        try:
            dragged_nodes = self._get_dragged_nodes_from_event(event)
            if not dragged_nodes:
                logger.debug("⚠️ 未获取到被拖拽的节点")
                original_drop_event(event)
                return
            
            target_item = self.node_tree.itemAt(event.position().toPoint())
            
            if target_item:
                target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
                
                if target_data and target_data.get('type') == 'node':
                    logger.debug("🔄 检测到节点拖拽到节点上，智能处理")
                    
                    target_node = target_data['name']
                    
                    if target_node not in dragged_nodes:
                        target_group = self.group_manager.get_node_group(target_node)
                        
                        # 锁定组边界检查
                        dragged_locked_roots = set()
                        for n in dragged_nodes:
                            g = self.group_manager.get_node_group(n)
                            if g and self.group_manager.is_group_locked(g):
                                dragged_locked_roots.add(g)

                        # 目标组是锁定组 → 禁止移入（无论被拖节点来源）
                        if target_group and self.group_manager.is_group_locked(target_group):
                            if not dragged_locked_roots:
                                if self.parent_window:
                                    self.parent_window.show_toast("禁止将节点移入挂载组", "warning")
                            elif target_group not in dragged_locked_roots:
                                if self.parent_window:
                                    self.parent_window.show_toast("不同根目录的挂载节点组之间禁止移动", "warning")
                            event.accept()
                            return

                        # 被拖节点来自锁定组 → 禁止移出
                        if dragged_locked_roots and (not target_group or target_group not in dragged_locked_roots):
                            if self.parent_window:
                                self.parent_window.show_toast("挂载组内的节点禁止移出组", "warning")
                            event.accept()
                            return
                        
                        if target_group:
                            logger.debug("✅ 目标节点 '%s' 在组 '%s' 中，直接融入", target_node, target_group)
                            self.group_manager.add_nodes_to_group(target_group, dragged_nodes)
                            self.update_node_list(self.nodes_data)
                            if self.parent_window:
                                self.parent_window.show_toast(
                                    f"✅ 已将 {len(dragged_nodes)} 个节点加入组 '{target_group}'", 
                                    "success"
                                )
                            event.accept()
                            return
                        else:
                            logger.info("🆕 目标节点 '%s' 不在组中，创建新组", target_node)
                            all_nodes = dragged_nodes + [target_node]
                            self._create_group_for_dragged_nodes(all_nodes)
                            event.accept()
                            return
            
            elif not target_item:
                # 拖到根级别（空白处）
                for n in dragged_nodes:
                    g = self.group_manager.get_node_group(n)
                    if g and self.group_manager.is_group_locked(g):
                        if self.parent_window:
                            self.parent_window.show_toast("挂载组内的节点禁止移出组", "warning")
                        event.accept()
                        return
                logger.debug("✅ 拖到根级别，将 %d 个节点移出组", len(dragged_nodes))
                self._move_nodes_to_ungrouped(dragged_nodes)
                event.accept()
                return
            
            original_drop_event(event)
            
        except Exception as e:
            logger.warning("⚠️ 拦截拖放事件失败: %s", e)
            import traceback
            traceback.print_exc()
            original_drop_event(event)

    def _get_dragged_nodes_from_event(self, event):
        """从拖拽事件中获取被拖拽的节点名称列表"""
        try:
            selected_items = self.node_tree.selectedItems()
            nodes = []
            for item in selected_items:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('type') == 'node':
                    nodes.append(data['name'])
            return nodes if nodes else None
        except Exception as e:
            logger.warning("⚠️ 获取拖拽节点失败: %s", e)
            return None

    def _create_group_for_dragged_nodes(self, node_names):
        """为拖拽涉及的节点创建新组"""
        if not node_names or len(node_names) < 2:
            return
        
        groups = self.group_manager.get_all_groups()
        
        base_name = f"Group_{len(groups) + 1}"
        new_group_name = base_name
        counter = 1
        while new_group_name in groups:
            new_group_name = f"{base_name}_{counter}"
            counter += 1
        
        import random
        color = f"#{random.randint(0x400000, 0xFFFFFF):06X}"
        self.group_manager.create_group(new_group_name, color)
        self.group_manager.add_nodes_to_group(new_group_name, node_names)
        
        self.update_node_list(self.nodes_data)
        
        if self.parent_window:
            self.parent_window.show_toast(
                f"✅ 已创建组 '{new_group_name}'，包含 {len(node_names)} 个节点", 
                "success"
            )
        
        logger.info("✅ 自动创建节点组: %s (包含 %s)", new_group_name, ", ".join(node_names))

    def on_nodes_moved(self, parent_index, start, end, destination_index, row):
        """节点拖拽移动事件处理"""
        try:
            moved_items = []
            for i in range(start, end + 1):
                item = self.node_tree.topLevelItem(parent_index.row()).child(i) if parent_index.isValid() else self.node_tree.topLevelItem(i)
                if item:
                    data = item.data(0, Qt.ItemDataRole.UserRole)
                    if data and data.get('type') == 'node':
                        moved_items.append(data['name'])
            
            if not moved_items:
                logger.debug("⚠️ 未找到被移动的节点")
                return
            
            logger.debug("📦 检测到节点移动: %s", moved_items)
            
            target_item = None
            if destination_index.isValid():
                target_item = self.node_tree.itemFromIndex(destination_index)
                if target_item:
                    target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
                    logger.debug("🎯 目标类型: %s", target_data.get('type') if target_data else 'None')
            
            if not target_item:
                logger.debug("✅ 移动到根级别，调用 _move_nodes_to_ungrouped")
                self._move_nodes_to_ungrouped(moved_items)
                return
            
            target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
            
            if target_data and target_data.get('type') == 'group':
                target_group = target_data['name']
                logger.debug("✅ 移动到组 '%s'，调用 _move_nodes_to_group", target_group)
                self._move_nodes_to_group(moved_items, target_group)
            
            elif target_data and target_data.get('type') == 'node':
                logger.debug("⚠️ 检测到节点到节点的移动（不应该到达这里）")
        
        except Exception as e:
            logger.warning("⚠️ 处理节点移动失败: %s", e)
            import traceback
            traceback.print_exc()

    def _move_nodes_to_group(self, node_names, group_name):
        """将节点移动到指定组"""
        # 检查锁定组边界
        if self.group_manager.is_group_locked(group_name):
            for node_name in node_names:
                current_group = self.group_manager.get_node_group(node_name)
                if not current_group or not self.group_manager.is_group_locked(current_group):
                    if self.parent_window:
                        self.parent_window.show_toast("禁止将节点移入挂载组", "warning")
                    return
        
        dragged_locked_groups = set()
        for node_name in node_names:
            g = self.group_manager.get_node_group(node_name)
            if g and self.group_manager.is_group_locked(g):
                dragged_locked_groups.add(g)
        if dragged_locked_groups:
            for locked_g in dragged_locked_groups:
                if locked_g != group_name:
                    if self.parent_window:
                        self.parent_window.show_toast(f"挂载组'{locked_g}'内的节点禁止移入其他组", "warning")
                    return
        
        if self.group_manager.add_nodes_to_group(group_name, node_names):
            self._cleanup_empty_groups(refresh=False)
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已将 {len(node_names)} 个节点移动到组 '{group_name}'", "success")

    def _move_nodes_to_ungrouped(self, node_names):
        """将节点移动到未分组状态"""
        for node_name in node_names:
            current_group = self.group_manager.get_node_group(node_name)
            if current_group and self.group_manager.is_group_locked(current_group):
                if self.parent_window:
                    self.parent_window.show_toast("挂载组内的节点禁止移出组", "warning")
                return
        
        removed_count = 0
        for node_name in node_names:
            current_group = self.group_manager.get_node_group(node_name)
            if current_group:
                self.group_manager.remove_nodes_from_group(current_group, [node_name])
                removed_count += 1
        
        empty_groups_deleted = self._cleanup_empty_groups(refresh=True)
        
        if removed_count > 0 and not empty_groups_deleted:
             self.update_node_list(self.nodes_data)
        
        if self.parent_window:
            if removed_count > 0:
                self.parent_window.show_toast(f"已将 {removed_count} 个节点移出组", "success")
            else:
                self.parent_window.show_toast("选中的节点未在组中", "info")
