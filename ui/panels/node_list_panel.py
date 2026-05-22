"""
节点列表面板 - 常驻半透明悬浮窗，显示项目中的所有节点
支持多选、分组管理、批量操作（所有操作通过右键菜单）
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QFileDialog, QInputDialog, QDialog, QPushButton, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.floating_panel import FloatingPanel
import subprocess
import json
import os


class NodeListPanel(FloatingPanel):
    """节点列表面板（常驻半透明悬浮窗）- 精简版
    
    设计理念：极简UI，所有操作通过右键菜单完成
    - 树形结构显示节点和组
    - 支持Ctrl/Shift多选
    - 所有功能集成到右键菜单
    """
    
    # 信号
    node_double_clicked = pyqtSignal(str)  # 节点双击信号（添加到画布）
    node_right_clicked = pyqtSignal(str, object)  # 节点右键信号
    
    def __init__(self, parent=None):
        super().__init__(parent, title=t("k_node_list"))
        self.nodes_data = {}
        
        # 初始化节点组管理器
        from ui.panels.node_group_manager import NodeGroupManager
        self.group_manager = NodeGroupManager()
        
        # init_ui 使用基类的 content_layout
        self._init_ui()
        
    def _init_ui(self):
        """初始化UI - 极简设计"""
        
        # 路径显示
        self.path_label = QLabel(t("k_node_no_project"))
        self.path_label.setStyleSheet("color: rgba(255, 255, 255, 120); font-size: 9px; padding: 2px 0;")
        self.content_layout.addWidget(self.path_label)
        
        # 提示文本
        hint_label = QLabel("右键查看操作")
        hint_label.setStyleSheet("color: rgba(255, 255, 255, 100); font-size: 10px; font-style: italic; padding: 2px 0;")
        self.content_layout.addWidget(hint_label)
        
        # 节点树形列表（支持分组显示、多选和拖拽）
        self.node_tree = QTreeWidget()
        self.node_tree.setHeaderHidden(True)
        self.node_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.node_tree.setDragEnabled(True)
        self.node_tree.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.node_tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.node_tree.setAcceptDrops(True)
        self.node_tree.itemDoubleClicked.connect(self.on_node_double_clicked)
        self.node_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.node_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # 重写dropEvent以完全控制拖放行为，防止节点嵌套
        original_drop_event = self.node_tree.dropEvent
        def custom_drop_event(event):
            self._intercept_drop_event(event, original_drop_event)
        self.node_tree.dropEvent = custom_drop_event
        
        # 连接拖拽信号
        self.node_tree.model().rowsMoved.connect(self.on_nodes_moved)
        
        self.node_tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                color: rgba(255, 255, 255, 200);
                font-size: 12px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 5px;
                border-radius: 4px;
            }
            QTreeWidget::item:hover {
                background-color: rgba(255, 255, 255, 30);
            }
            QTreeWidget::item:selected {
                background-color: rgba(0, 102, 255, 100);
            }
            QTreeWidget::branch:selected {
                background-color: rgba(0, 102, 255, 100);
            }
        """)
        self.content_layout.addWidget(self.node_tree)
        
        # 设置初始大小
        self.resize(280, 500)
    
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
            # 获取被拖拽的节点
            dragged_nodes = self._get_dragged_nodes_from_event(event)
            if not dragged_nodes:
                logger.debug("⚠️ 未获取到被拖拽的节点")
                original_drop_event(event)
                return
            
            # 获取目标位置
            target_item = self.node_tree.itemAt(event.position().toPoint())
            
            if target_item:
                target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
                
                # 如果目标是节点，需要智能判断
                if target_data and target_data.get('type') == 'node':
                    logger.debug("🔄 检测到节点拖拽到节点上，智能处理")
                    
                    target_node = target_data['name']
                    
                    if target_node not in dragged_nodes:
                        # 检查目标节点是否在某个组中
                        target_group = self.group_manager.get_node_group(target_node)
                        
                        # 检查锁定组边界：所有被拖拽节点是否来自锁定组
                        dragged_has_locked = any(
                            self.group_manager.is_group_locked(self.group_manager.get_node_group(n))
                            for n in dragged_nodes if self.group_manager.get_node_group(n)
                        )
                        target_has_locked = self.group_manager.is_group_locked(target_group) if target_group else False
                        # 不同锁定域之间禁止跨越（locked↔non-locked, locked_A↔locked_B）
                        dragged_locked_roots = set()
                        for n in dragged_nodes:
                            g = self.group_manager.get_node_group(n)
                            if g and self.group_manager.is_group_locked(g):
                                dragged_locked_roots.add(g)
                        if dragged_locked_roots and target_group not in dragged_locked_roots:
                            if target_group and self.group_manager.is_group_locked(target_group):
                                # locked组之间禁止互通
                                if self.parent_window:
                                    self.parent_window.show_toast("不同根目录的挂载节点组之间禁止移动", "warning")
                                event.accept()
                                return
                            if target_group and not self.group_manager.is_group_locked(target_group):
                                # 从locked组移出到普通组，禁止
                                if self.parent_window:
                                    self.parent_window.show_toast("挂载组内的节点禁止移出", "warning")
                                event.accept()
                                return
                        if not dragged_locked_roots and target_has_locked:
                            # 从普通组移入locked组，禁止
                            if self.parent_window:
                                self.parent_window.show_toast("禁止将节点移入挂载组", "warning")
                            event.accept()
                            return
                        
                        if target_group:
                            # 目标节点在某个组中，直接将拖拽的节点加入该组
                            logger.debug("✅ 目标节点 '%target_node' 在组 '%target_group' 中，直接融入")
                            
                            # 将拖拽的节点添加到目标组
                            self.group_manager.add_nodes_to_group(target_group, dragged_nodes)
                            
                            # 刷新列表
                            self.update_node_list(self.nodes_data)
                            
                            # 显示提示
                            if self.parent_window:
                                self.parent_window.show_toast(
                                    f"✅ 已将 {len(dragged_nodes)} 个节点加入组 '{target_group}'", 
                                    "success"
                                )
                            
                            # 拒绝原始拖放操作
                            event.accept()
                            return
                        else:
                            # 目标节点不在任何组中（根级别节点），创建新组
                            logger.info("🆕 目标节点 '%target_node' 不在组中，创建新组")
                            
                            # 将所有涉及的节点合并
                            all_nodes = dragged_nodes + [target_node]
                            
                            # 创建新组
                            self._create_group_for_dragged_nodes(all_nodes)
                            
                            # 拒绝原始拖放操作
                            event.accept()
                            return
            
            elif not target_item:
                # 拖到根级别（空白处）- 将节点移出所有组
                # 检查是否有锁定组内的节点
                for n in dragged_nodes:
                    g = self.group_manager.get_node_group(n)
                    if g and self.group_manager.is_group_locked(g):
                        if self.parent_window:
                            self.parent_window.show_toast("挂载组内的节点禁止移出组", "warning")
                        event.accept()
                        return
                logger.debug("✅ 拖到根级别，将 {len(dragged_nodes)} 个节点移出组")
                self._move_nodes_to_ungrouped(dragged_nodes)
                event.accept()
                return
            
            # 其他情况（拖入组标题），允许正常拖放
            original_drop_event(event)
            
        except Exception as e:
            logger.warning("⚠️ 拦截拖放事件失败: %e")
            import traceback
            traceback.print_exc()
            # 出错时允许默认行为
            original_drop_event(event)
    
    def _get_dragged_nodes_from_event(self, event):
        """从拖拽事件中获取被拖拽的节点名称列表
        
        Args:
            event: 拖拽事件对象
            
        Returns:
            节点名称列表
        """
        try:
            # 获取选中的项
            selected_items = self.node_tree.selectedItems()
            nodes = []
            
            for item in selected_items:
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('type') == 'node':
                    nodes.append(data['name'])
            
            return nodes if nodes else None
            
        except Exception as e:
            logger.warning("⚠️ 获取拖拽节点失败: %e")
            return None
    
    def _create_group_for_dragged_nodes(self, node_names):
        """为拖拽涉及的节点创建新组
        
        Args:
            node_names: 节点名称列表
        """
        if not node_names or len(node_names) < 2:
            return
        
        group_manager = self.group_manager
        groups = group_manager.get_all_groups()
        
        # 生成新组名
        base_name = f"Group_{len(groups) + 1}"
        new_group_name = base_name
        counter = 1
        while new_group_name in groups:
            new_group_name = f"{base_name}_{counter}"
            counter += 1
        
        # 创建新组（随机颜色）
        import random
        color = f"#{random.randint(0x400000, 0xFFFFFF):06X}"
        group_manager.create_group(new_group_name, color)
        
        # 将所有节点添加到新组
        group_manager.add_nodes_to_group(new_group_name, node_names)
        
        # 刷新列表
        self.update_node_list(self.nodes_data)
        
        # 显示提示
        if self.parent_window:
            self.parent_window.show_toast(
                f"✅ 已创建组 '{new_group_name}'，包含 {len(node_names)} 个节点", 
                "success"
            )
        
        logger.info("✅ 自动创建节点组: %new_group_name (包含 {', '.join(node_names)})")
    
    def update_node_list(self, nodes_data):
        """更新节点列表（树形结构，支持分组）
        
        注意：
        - 节点组之间是平行关系，没有嵌套（类似PS图层组）
        - 不再显示"未分组节点"分类，所有节点都明确属于某个组或根层级
        """
        self.nodes_data = nodes_data
        
        # 清空树
        self.node_tree.clear()
        
        # 按组组织节点
        groups = self.group_manager.get_all_groups()
        
        # 添加各个组（平行关系，无嵌套）
        for group_name, group_info in sorted(groups.items()):
            group_item = QTreeWidgetItem(self.node_tree)
            # 锁定的组显示 🔒 标记
            lock_indicator = "🔒 " if self.group_manager.is_group_locked(group_name) else ""
            group_item.setText(0, f"{lock_indicator}{group_name} ({len(group_info['nodes'])})")
            group_item.setForeground(0, QColor(group_info.get('color', '#4A90E2')))
            group_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            
            # 标记为组节点（含锁定状态）
            group_item.setData(0, Qt.ItemDataRole.UserRole, {
                'type': 'group',
                'name': group_name,
                'locked': self.group_manager.is_group_locked(group_name)
            })
            
            # 添加组内节点
            for node_name in sorted(group_info['nodes']):
                if node_name in nodes_data:
                    node_item = QTreeWidgetItem(group_item)
                    self._setup_node_item(node_item, node_name, nodes_data[node_name])
            
            group_item.setExpanded(True)
        
        # 显示不属于任何组的节点（直接作为根节点，不归类为"未分组"）
        all_grouped_nodes = set()
        for group_info in groups.values():
            all_grouped_nodes.update(group_info['nodes'])
        
        root_nodes = [name for name in nodes_data.keys() if name not in all_grouped_nodes]
        
        if root_nodes:
            # 直接添加为根级别的节点项，不放在任何分类下
            for node_name in sorted(root_nodes):
                if node_name in nodes_data:
                    node_item = QTreeWidgetItem(self.node_tree)
                    self._setup_node_item(node_item, node_name, nodes_data[node_name])
                    # 标记为根级别节点
                    node_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'node', 'name': node_name, 'level': 'root'})
        
        # 更新路径显示
        if self.parent_window and self.parent_window.current_project_path:
            self.path_label.setText(f"项目: {os.path.basename(self.parent_window.current_project_path)}")
        else:
            self.path_label.setText(t("k_node_no_project"))
    
    def _setup_node_item(self, item, node_name, node_info):
        """配置节点项"""
        status = node_info.get('status', 'stopped')
        if status == 'running':
            item.setText(0, f"● {node_name}")
            item.setForeground(0, QColor("green"))
        else:
            item.setText(0, f"○ {node_name}")
            item.setForeground(0, QColor("gray"))
        
        # 存储节点信息
        item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'node', 'name': node_name})
    
    def update_node_status(self, node_name, status):
        """更新节点状态"""
        # 遍历所有项查找节点
        root = self.node_tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                node_item = group_item.child(j)
                data = node_item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('type') == 'node' and data.get('name') == node_name:
                    if status == 'running':
                        node_item.setText(0, f"● {node_name}")
                        node_item.setForeground(0, QColor("green"))
                    else:
                        node_item.setText(0, f"○ {node_name}")
                        node_item.setForeground(0, QColor("gray"))
                    return
    
    def get_selected_nodes(self):
        """获取所有选中的节点名称"""
        selected_items = self.node_tree.selectedItems()
        nodes = []
        
        for item in selected_items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'node':
                nodes.append(data['name'])
        
        return nodes
    
    def get_selected_groups(self):
        """获取所有选中的组名称"""
        selected_items = self.node_tree.selectedItems()
        groups = []
        
        for item in selected_items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'group':
                groups.append(data['name'])
        
        return groups
    
    def on_node_double_clicked(self, item, column):
        """节点双击事件 - 添加到画布"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'node':
            return
        
        node_name = data['name']
        if self.parent_window:
            # 检查节点是否已在画布上
            if node_name in self.parent_window.canvas.nodes:
                self.parent_window.show_toast(f"节点 {node_name} 已在画布上", "warning")
                return
            
            # 添加到画布
            self.add_node_to_canvas(node_name)
    
    def show_context_menu(self, position):
        """显示右键菜单 - 所有功能的统一入口"""
        item = self.node_tree.itemAt(position)
        if not item:
            # 空白处右键 - 显示全局菜单
            self._show_global_context_menu(position)
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        menu = QMenu(self)
        
        if data.get('type') == 'node':
            # 节点右键菜单
            node_name = data['name']
            self._show_node_context_menu(menu, node_name)
        
        elif data.get('type') == 'group':
            # 组右键菜单
            group_name = data['name']
            self._show_group_context_menu(menu, group_name)
        
        # 注意：不再处理"未分组类别"，因为已经移除了该分类
        
        menu.exec(self.node_tree.mapToGlobal(position))
    
    def on_nodes_moved(self, parent_index, start, end, destination_index, row):
        """节点拖拽移动事件处理
        
        Args:
            parent_index: 父项索引
            start: 起始行
            end: 结束行
            destination_index: 目标父项索引
            row: 目标行
        
        注意：
        - 节点组之间是平行关系，没有嵌套（类似PS图层组）
        - 非法的节点嵌套已在_intercept_drop_event中被阻止
        - 只处理合法的移动：节点→组、节点→根级别
        """
        try:
            # 获取被移动的节点项
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
            
            logger.debug("📦 检测到节点移动: %moved_items")
            
            # 获取目标位置
            target_item = None
            if destination_index.isValid():
                target_item = self.node_tree.itemFromIndex(destination_index)
                if target_item:
                    target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
                    logger.debug("🎯 目标类型: {target_data.get('type') if target_data else 'None'}")
            
            if not target_item:
                # 移动到根级别 - 将节点移出所有组，成为独立节点
                logger.debug("✅ 移动到根级别，调用 _move_nodes_to_ungrouped")
                self._move_nodes_to_ungrouped(moved_items)
                return
            
            target_data = target_item.data(0, Qt.ItemDataRole.UserRole)
            
            if target_data and target_data.get('type') == 'group':
                # 移动到某个节点组 - 正常操作
                target_group = target_data['name']
                logger.debug("✅ 移动到组 '%target_group'，调用 _move_nodes_to_group")
                self._move_nodes_to_group(moved_items, target_group)
            
            elif target_data and target_data.get('type') == 'node':
                # 这个情况应该在_intercept_drop_event中已经被处理了
                logger.debug("⚠️ 检测到节点到节点的移动（不应该到达这里）")
        
        except Exception as e:
            logger.warning("⚠️ 处理节点移动失败: %e")
            import traceback
            traceback.print_exc()
    
    def _move_nodes_to_group(self, node_names, group_name):
        """将节点移动到指定组
        
        Args:
            node_names: 节点名称列表
            group_name: 目标组名称
        """
        # 检查锁定组边界
        if self.group_manager.is_group_locked(group_name):
            # 目标组被锁定，禁止移入
            for node_name in node_names:
                current_group = self.group_manager.get_node_group(node_name)
                if not current_group or not self.group_manager.is_group_locked(current_group):
                    if self.parent_window:
                        self.parent_window.show_toast("禁止将节点移入挂载组", "warning")
                    return
        
        # 检查被拖拽节点是否来自锁定组（不同锁定组之间禁止移动）
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
            # 清理空组（不刷新列表）
            self._cleanup_empty_groups(refresh=False)
            
            # 统一刷新一次列表
            self.update_node_list(self.nodes_data)
            
            # 显示提示
            if self.parent_window:
                self.parent_window.show_toast(f"已将 {len(node_names)} 个节点移动到组 '{group_name}'", "success")
    
    def _move_nodes_to_ungrouped(self, node_names):
        """将节点移动到未分组状态
        
        Args:
            node_names: 节点名称列表
        """
        # 不允许从锁定组移出节点
        for node_name in node_names:
            current_group = self.group_manager.get_node_group(node_name)
            if current_group and self.group_manager.is_group_locked(current_group):
                if self.parent_window:
                    self.parent_window.show_toast("挂载组内的节点禁止移出组", "warning")
                return
        
        # 从当前组中移除（如果节点在某个组中）
        removed_count = 0
        for node_name in node_names:
            current_group = self.group_manager.get_node_group(node_name)
            if current_group:
                self.group_manager.remove_nodes_from_group(current_group, [node_name])
                removed_count += 1
        
        # 清理空组并刷新列表
        empty_groups_deleted = self._cleanup_empty_groups(refresh=True)
        
        # 如果没有删除空组且移除了节点，可能需要手动刷新（如果 cleanup 没做的话）
        # 但 cleanup 已经处理了 refresh=True 的情况
        if removed_count > 0 and not empty_groups_deleted:
             self.update_node_list(self.nodes_data)
        
        # 显示提示
        if self.parent_window:
            if removed_count > 0:
                self.parent_window.show_toast(f"已将 {removed_count} 个节点移出组", "success")
            else:
                self.parent_window.show_toast("选中的节点未在组中", "info")
    
    def _cleanup_empty_groups(self, refresh=True):
        """清理空的节点组（自动删除，无需确认）
        注意：锁定的组（挂载组）不会被自动清理
        
        Args:
            refresh: 是否刷新列表，默认为True
            
        Returns:
            bool: 是否删除了空组
        """
        groups = self.group_manager.get_all_groups()
        empty_groups = []
        
        for group_name, group_info in groups.items():
            if len(group_info['nodes']) == 0:
                # 锁定的组（挂载组）不自动删除
                if not self.group_manager.is_group_locked(group_name):
                    empty_groups.append(group_name)
        
        if empty_groups:
            # 自动删除所有空组，无需用户确认
            for group_name in empty_groups:
                self.group_manager.delete_group(group_name)
            
            # 根据参数决定是否刷新列表
            if refresh:
                self.update_node_list(self.nodes_data)
            
            if self.parent_window and refresh:
                self.parent_window.show_toast(f"已自动删除 {len(empty_groups)} 个空节点组", "info")
            
            logger.debug("✅ 自动删除空节点组: {', '.join(empty_groups)}")
            return True
        
        return False
    
    def _show_global_context_menu(self, position):
        """显示全局右键菜单（空白处）"""
        menu = QMenu(self)
        
        # 创建新组
        create_group_action = menu.addAction("创建分组")
        create_group_action.triggered.connect(self.create_node_group)
        
        menu.addSeparator()
        
        # 全选
        select_all_action = menu.addAction("全选节点")
        select_all_action.triggered.connect(self.select_all_nodes)
        
        # 取消选择
        deselect_all_action = menu.addAction("取消选择")
        deselect_all_action.triggered.connect(self.deselect_all_nodes)
        
        menu.addSeparator()
        
        refresh_action = menu.addAction("刷新列表")
        refresh_action.triggered.connect(lambda: self.update_node_list(self.nodes_data))
        
        menu.exec(self.node_tree.mapToGlobal(position))
    
    def _show_node_context_menu(self, menu, node_name):
        """显示节点右键菜单"""
        selected_nodes = self.get_selected_nodes()
        
        # 如果选中了多个节点，只显示批量操作菜单
        if len(selected_nodes) > 1 and node_name in selected_nodes:
            menu.addAction(f"已选 {len(selected_nodes)} 个节点").setEnabled(False)
            menu.addSeparator()
            
            # 批量添加到画布
            batch_add_action = menu.addAction(f"添加 {len(selected_nodes)} 个节点到画布")
            batch_add_action.triggered.connect(self.batch_add_nodes_to_canvas)
            
            menu.addSeparator()
            
            # 批量移动到组
            move_to_group_menu = menu.addMenu("移动分组")
            groups = self.group_manager.get_all_groups()
            if groups:
                for group_name in sorted(groups.keys()):
                    action = move_to_group_menu.addAction(group_name)
                    action.triggered.connect(lambda checked, gn=group_name: self.batch_move_nodes_to_group(gn))
            else:
                move_to_group_menu.addAction("（无可用组）").setEnabled(False)
            
            # 从组移除（如果选中的节点都在同一个组）
            common_group = self._get_common_group(selected_nodes)
            if common_group:
                remove_from_group_action = menu.addAction(f"从组 '{common_group}' 移除选中节点")
                remove_from_group_action.triggered.connect(lambda: self.batch_remove_nodes_from_group(common_group))
            
            menu.addSeparator()
            
            # 批量启动
            batch_start_action = menu.addAction(f"启动 {len(selected_nodes)} 个节点")
            batch_start_action.triggered.connect(self.batch_start_nodes)
            
            # 批量停止
            batch_stop_action = menu.addAction(f"停止 {len(selected_nodes)} 个节点")
            batch_stop_action.triggered.connect(self.batch_stop_nodes)
            
            menu.addSeparator()
            
            # 批量打开文件夹
            batch_open_folder_action = menu.addAction(f"打开 {len(selected_nodes)} 个节点目录")
            batch_open_folder_action.triggered.connect(self.batch_open_node_folders)
            
            # 批量查看日志
            batch_view_log_action = menu.addAction(f"查看 {len(selected_nodes)} 个节点日志")
            batch_view_log_action.triggered.connect(self.batch_view_node_logs)
            
            menu.addSeparator()
            
            # 批量编辑配置
            batch_edit_config_action = menu.addAction(f"编辑 {len(selected_nodes)} 个节点配置")
            batch_edit_config_action.triggered.connect(self.batch_edit_node_configs)
            
            menu.addSeparator()
            
            # 批量删除
            batch_delete_action = menu.addAction(f"删除 {len(selected_nodes)} 个节点")
            batch_delete_action.triggered.connect(self.batch_delete_nodes)
        
        else:
            # 单个节点操作
            add_to_canvas_action = menu.addAction(t("k_canvas_add_to"))
            add_to_canvas_action.triggered.connect(lambda: self.add_node_to_canvas(node_name))
            
            menu.addSeparator()
            
            # 移动到组
            move_to_group_menu = menu.addMenu("移动分组")
            groups = self.group_manager.get_all_groups()
            if groups:
                for group_name in sorted(groups.keys()):
                    action = move_to_group_menu.addAction(group_name)
                    action.triggered.connect(lambda checked, gn=group_name: self.move_node_to_group(node_name, gn))
            else:
                move_to_group_menu.addAction("（无可用组）").setEnabled(False)
            
            # 从组移除
            current_group = self.group_manager.get_node_group(node_name)
            if current_group:
                remove_from_group_action = menu.addAction(f"从组 '{current_group}' 移除")
                remove_from_group_action.triggered.connect(lambda: self.remove_node_from_group(node_name))
            
            menu.addSeparator()
            
            # 启动/停止
            node_info = self.nodes_data.get(node_name, {})
            if node_info.get('status') == 'running':
                stop_action = menu.addAction(t("k_node_stop"))
                stop_action.triggered.connect(lambda: self._stop_single_node(node_name))
            else:
                start_action = menu.addAction(t("k_node_start"))
                start_action.triggered.connect(lambda: self._start_single_node(node_name))
            
            menu.addSeparator()
            
            # 重命名节点
            rename_action = menu.addAction(t("k_node_rename"))
            rename_action.triggered.connect(lambda: self.rename_node(node_name))
            
            menu.addSeparator()
            
            # 打开节点文件夹
            open_folder_action = menu.addAction(t("k_open_dir"))
            open_folder_action.triggered.connect(lambda: self.open_node_folder(node_name))
            
            # 查看日志
            view_log_action = menu.addAction("查看日志")
            view_log_action.triggered.connect(lambda: self.view_node_log(node_name))
            
            menu.addSeparator()
            
            # 编辑配置
            edit_config_action = menu.addAction("编辑配置")
            edit_config_action.triggered.connect(lambda: self.edit_node_config(node_name))
            
            # 卸载外部节点（仅挂载节点显示）
            node_info = self.nodes_data.get(node_name, {})
            if node_info.get('mounted'):
                unmount_action = menu.addAction("卸载外部节点")
                unmount_action.triggered.connect(lambda: self._unmount_node(node_name))
            
            # 删除节点（挂载节点不可删除）
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
        
        # 组信息
        lock_tag = "🔒 " if is_locked else ""
        menu.addAction(f"{lock_tag}组: {group_name}").setEnabled(False)
        menu.addAction(f"   节点数: {len(group_nodes)}").setEnabled(False)
        menu.addSeparator()
        
        # 启动组内所有节点
        running_count = sum(1 for n in group_nodes if self.nodes_data.get(n, {}).get('status') == 'running')
        stopped_count = len(group_nodes) - running_count
        
        if stopped_count > 0:
            start_group_action = menu.addAction(f"启动组内所有节点 ({stopped_count}个)")
            start_group_action.triggered.connect(lambda: self.start_group_nodes(group_name))
        
        if running_count > 0:
            stop_group_action = menu.addAction(f"停止组内所有节点 ({running_count}个)")
            stop_group_action.triggered.connect(lambda: self.stop_group_nodes(group_name))
        
        menu.addSeparator()
        
        # 重命名组（锁定组不可重命名）
        if not is_locked:
            rename_group_action = menu.addAction("重命名组")
            rename_group_action.triggered.connect(lambda: self.rename_group(group_name))
        
        # 删除组（锁定组不可删除）
        if not is_locked:
            delete_group_action = menu.addAction("删除组")
            delete_group_action.triggered.connect(lambda: self.delete_group(group_name))
        
        menu.addSeparator()
        
        # 展开/折叠
        expand_action = menu.addAction("展开折叠")
        expand_action.triggered.connect(lambda: self.toggle_group_expansion(group_name))
    
    def _show_ungrouped_category_menu(self, menu):
        """显示未分组类别菜单"""
        all_nodes = list(self.nodes_data.keys())
        ungrouped_nodes = self.group_manager.get_ungrouped_nodes(all_nodes)
        
        menu.addAction(f"未分组节点").setEnabled(False)
        menu.addAction(f"   数量: {len(ungrouped_nodes)}").setEnabled(False)
        menu.addSeparator()
        
        # 批量启动未分组节点
        stopped_count = sum(1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get('status') == 'stopped')
        if stopped_count > 0:
            start_ungrouped_action = menu.addAction(f"启动所有未分组节点 ({stopped_count}个)")
            start_ungrouped_action.triggered.connect(self.start_ungrouped_nodes)
        
        # 批量停止未分组节点
        running_count = sum(1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get('status') == 'running')
        if running_count > 0:
            stop_ungrouped_action = menu.addAction(f"停止所有未分组节点 ({running_count}个)")
            stop_ungrouped_action.triggered.connect(self.stop_ungrouped_nodes)
        
        menu.addSeparator()
        
        # 创建新组并移动
        create_and_move_action = menu.addAction("新建分组并移入")
        create_and_move_action.triggered.connect(lambda: self.create_group_from_ungrouped(ungrouped_nodes))
    
    def add_node_to_canvas(self, node_name):
        """添加节点到画布"""
        if self.parent_window:
            self.parent_window.canvas.add_node_to_canvas(node_name)

    def open_node_folder(self, node_name):
        """打开节点文件夹"""
        if node_name not in self.nodes_data:
            QMessageBox.warning(self, t("k_title_warning"), f"⚠️ 节点 '{node_name}' 未找到！")
            return

        from ui.core.utils.file_utils import resolve_and_open_folder
        resolve_and_open_folder(
            self.nodes_data[node_name]['path'],
            node_name,
            parent_window=self.parent_window,
            dialog_parent=self
        )
        logger.debug("{'='*60}\n")
    def view_node_log(self, node_name):
        """查看节点日志"""
        if node_name not in self.nodes_data:
            return
        
        node_path = self.nodes_data[node_name]['path']
        log_file = os.path.join(node_path, "logs", "listener.log")
        
        if not os.path.exists(log_file):
            QMessageBox.information(self, t("k_title_info"), t("k_node_no_log"))
            return
        
        # 读取日志内容
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # 显示日志对话框
            from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
            
            dialog = QDialog(self)
            dialog.setWindowTitle(f"节点日志 - {node_name}")
            dialog.setGeometry(200, 200, 800, 600)
            
            layout = QVBoxLayout(dialog)
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setText(log_content)
            layout.addWidget(text_edit)
            
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.close)
            layout.addWidget(close_button)
            
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, t("k_title_error"), f"读取日志失败: {str(e)}")
            
    def edit_node_config(self, node_name):
        """编辑节点配置"""
        if node_name not in self.nodes_data:
            return
        
        node_info = self.nodes_data[node_name]
        config = node_info['config']
        node_path = node_info['path']
        
        # 打开配置对话框
        from ui.panels.property_panel import NodeConfigDialog
        dialog = NodeConfigDialog(node_name, config, node_path, self.parent_window)
        dialog.exec()

    def delete_node(self, node_name):
        """删除节点"""
        if node_name not in self.nodes_data:
            return
        
        # 挂载节点不允许删除（只能卸载）
        if self.nodes_data[node_name].get('mounted'):
            if self.parent_window:
                self.parent_window.show_toast("外部挂载节点请使用「卸载」功能，禁止删除", "warning")
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除节点 '{node_name}' 吗？\n这将删除整个节点文件夹！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        node_path = self.nodes_data[node_name]['path']
        
        try:
            # 停止节点进程（如果在运行）
            node_info = self.nodes_data[node_name]
            if node_info['process']:
                process = node_info['process']
                try:
                    if os.name == 'nt':
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            import signal
                            process.send_signal(signal.CTRL_BREAK_EVENT)
                            try:
                                process.wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                    else:
                        import signal
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                            process.wait(timeout=5)
                        except (ProcessLookupError, subprocess.TimeoutExpired):
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            process.wait()
                except Exception as e:
                    logger.warning("停止节点时出错: %e")
                    try:
                        process.kill()
                        process.wait()
                    except:
                        pass
            
            # 删除文件夹
            import shutil
            shutil.rmtree(node_path)
            
            # 从节点组中移除
            current_group = self.group_manager.get_node_group(node_name)
            if current_group:
                self.group_manager.remove_nodes_from_group(current_group, [node_name])
            
            # 从数据中移除
            del self.nodes_data[node_name]
            
            # 从节点注册表中注销
            try:
                if self.parent_window and hasattr(self.parent_window, 'current_project_path') and self.parent_window.current_project_path:
                    from ui.core.node_registry import NodeRegistry
                    registry = NodeRegistry(self.parent_window.current_project_path)
                    registry.load()
                    registry.unregister_node(node_name)
                    registry.save()
            except Exception:
                pass
            
            # 从画布中移除
            if self.parent_window:
                self.parent_window.canvas.remove_node_from_canvas(node_name)
            
            # 刷新列表
            self.update_node_list(self.nodes_data)
            
            QMessageBox.information(self, t("k_title_success"), f"节点 {node_name} 已删除")
        except Exception as e:
            QMessageBox.critical(self, t("k_title_error"), f"删除节点失败: {str(e)}")
    
    def rename_node(self, old_name):
        """重命名节点"""
        if old_name not in self.nodes_data:
            return
        
        # 输入新名称
        new_name, ok = QInputDialog.getText(
            self, t("k_node_rename"),
            ft("k_node_input_new_name"),
            text=old_name
        )
        
        if not ok or not new_name:
            return
        
        # 验证名称格式
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', new_name):
            QMessageBox.warning(self, t("k_title_warning"), t("k_node_name_invalid"))
            return
        
        # 检查名称是否已存在
        if new_name != old_name and new_name in self.nodes_data:
            QMessageBox.warning(self, t("k_title_warning"), f"节点名称 '{new_name}' 已存在")
            return
        
        try:
            node_info = self.nodes_data[old_name]
            old_path = node_info['path']
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            
            # 1. 重命名文件夹
            if os.path.exists(new_path):
                QMessageBox.warning(self, t("k_title_warning"), f"文件夹 '{new_name}' 已存在")
                return
            
            os.rename(old_path, new_path)
            
            # 2. 更新config.json中的node_name
            config_path = os.path.join(new_path, "config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            config['node_name'] = new_name
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 3. 更新内存中的数据
            node_info['path'] = new_path
            node_info['config'] = config
            
            # 4. 更新节点组中的引用
            current_group = self.group_manager.get_node_group(old_name)
            if current_group:
                self.group_manager.remove_nodes_from_group(current_group, [old_name])
                self.group_manager.add_nodes_to_group(current_group, [new_name])
            
            # 5. 从nodes_data中移除旧键，添加新键
            del self.nodes_data[old_name]
            self.nodes_data[new_name] = node_info
            
            # 6. 更新画布上的节点
            if self.parent_window:
                self.parent_window.canvas.rename_node_in_canvas(old_name, new_name)
                
                # 停止自动保存定时器（防止竞态条件）
                if hasattr(self.parent_window.canvas, '_save_timer'):
                    self.parent_window.canvas._save_timer.stop()
                
                # 手动保存布局
                if self.parent_window.current_project_path:
                    self.parent_window.canvas.save_layout(self.parent_window.current_project_path)
                
                # 恢复自动保存
                if hasattr(self.parent_window.canvas, '_save_timer'):
                    self.parent_window.canvas._save_timer.start()
            
            # 7. 刷新父窗口的节点数据（重新从磁盘加载）
            if self.parent_window:
                self.parent_window.refresh_nodes()
            else:
                # 如果没有父窗口，只更新本地列表
                self.update_node_list(self.nodes_data)

            QMessageBox.information(self, t("k_title_success"), f"节点已重命名为: {new_name}")
            
        except Exception as e:
            QMessageBox.critical(self, t("k_title_error"), f"重命名失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # ==================== 多选和批量操作 ====================
    
    def select_all_nodes(self):
        """全选所有节点"""
        self.node_tree.selectAll()
    
    def deselect_all_nodes(self):
        """取消全选"""
        self.node_tree.clearSelection()
    
    def create_node_group(self):
        """创建新的节点组"""
        group_name, ok = QInputDialog.getText(
            self, t("k_group_create_group"),
            t("k_node_input_new_group_name")
        )
        
        if not ok or not group_name:
            return
        
        # 选择颜色
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor("#4A90E2"), self, t("k_color_select_group"))
        
        if not color.isValid():
            color = QColor("#4A90E2")
        
        # 创建组
        if self.group_manager.create_group(group_name, color.name()):
            # 如果有选中的节点，询问是否添加到新组
            selected_nodes = self.get_selected_nodes()
            if selected_nodes:
                reply = QMessageBox.question(
                    self, "添加到组",
                    f"是否将选中的 {len(selected_nodes)} 个节点添加到新组 '{group_name}'？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.group_manager.add_nodes_to_group(group_name, selected_nodes)
            
            # 刷新列表
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已创建组: {group_name}", "success")
    
    def move_node_to_group(self, node_name, group_name):
        """移动节点到指定组"""
        if self.group_manager.add_nodes_to_group(group_name, [node_name]):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已将 {node_name} 移动到组 {group_name}", "success")
    
    def batch_move_nodes_to_group(self, group_name):
        """批量移动选中的节点到组"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要移动的节点", "warning")
            return
        
        if self.group_manager.add_nodes_to_group(group_name, selected_nodes):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已将 {len(selected_nodes)} 个节点移动到组 {group_name}", "success")
    
    def remove_node_from_group(self, node_name):
        """从组中移除节点"""
        current_group = self.group_manager.get_node_group(node_name)
        if current_group:
            if self.group_manager.is_group_locked(current_group):
                if self.parent_window:
                    self.parent_window.show_toast("挂载组内的节点禁止移出", "warning")
                return
            if self.group_manager.remove_nodes_from_group(current_group, [node_name]):
                self.update_node_list(self.nodes_data)
                if self.parent_window:
                    self.parent_window.show_toast(f"已将 {node_name} 从组 {current_group} 移除", "success")
    
    def rename_group(self, group_name):
        """重命名组"""
        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("挂载组禁止重命名", "warning")
            return
        new_name, ok = QInputDialog.getText(
            self, "重命名组",
            ft("k_group_input_new_name"),
            text=group_name
        )
        
        if not ok or not new_name:
            return
        
        if new_name == group_name:
            return
        
        if self.group_manager.rename_group(group_name, new_name):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"组已重命名: {group_name} -> {new_name}", "success")
    
    def delete_group(self, group_name):
        """删除组（保留节点）"""
        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("挂载组禁止删除，请先卸载外部节点", "warning")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除组 '{group_name}' 吗？\n组内节点不会被删除。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        if self.group_manager.delete_group(group_name):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已删除组: {group_name}", "success")
    
    def toggle_group_expansion(self, group_name):
        """切换组的展开/折叠状态"""
        root = self.node_tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            data = group_item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'group' and data.get('name') == group_name:
                group_item.setExpanded(not group_item.isExpanded())
                break
    
    def batch_start_nodes(self):
        """批量启动选中的节点"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要启动的节点", "warning")
            return
        
        success_count = 0
        fail_count = 0
        
        for node_name in selected_nodes:
            if node_name in self.nodes_data:
                if self.nodes_data[node_name]['status'] == 'stopped':
                    try:
                        self._start_single_node(node_name)
                        success_count += 1
                    except Exception as e:
                        logger.warning("启动节点 %node_name 失败: %e")
                        fail_count += 1
        
        msg = f"已启动 {success_count} 个节点"
        if fail_count > 0:
            msg += f"，{fail_count} 个失败"
        
        if self.parent_window:
            self.parent_window.show_toast(msg, "success")
    
    def batch_stop_nodes(self):
        """批量停止选中的节点"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要停止的节点", "warning")
            return
        
        success_count = 0
        for node_name in selected_nodes:
            if node_name in self.nodes_data:
                if self.nodes_data[node_name]['status'] == 'running':
                    try:
                        self._stop_single_node(node_name)
                        success_count += 1
                    except Exception as e:
                        logger.warning("停止节点 %node_name 失败: %e")
        
        if self.parent_window:
            self.parent_window.show_toast(f"已停止 {success_count} 个节点", "success")
    
    def batch_delete_nodes(self):
        """批量删除选中的节点"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要删除的节点", "warning")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self, t("k_title_confirm_batch_delete"),
            f"确定要删除选中的 {len(selected_nodes)} 个节点吗？\n这将删除所有选中节点的文件夹！\n\n节点列表:\n" + "\n".join(selected_nodes[:10]) + ("..." if len(selected_nodes) > 10 else ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        success_count = 0
        fail_count = 0
        failed_nodes = []
        
        # 预加载节点注册表，批量注销后统一保存
        registry = None
        if self.parent_window and hasattr(self.parent_window, 'current_project_path') and self.parent_window.current_project_path:
            try:
                from ui.core.node_registry import NodeRegistry
                registry = NodeRegistry(self.parent_window.current_project_path)
                registry.load()
            except Exception:
                registry = None
        
        for node_name in selected_nodes:
            if node_name not in self.nodes_data:
                fail_count += 1
                failed_nodes.append(node_name)
                continue
            
            try:
                node_info = self.nodes_data[node_name]
                node_path = node_info['path']
                
                # 停止节点进程（如果在运行）
                if node_info['process']:
                    process = node_info['process']
                    try:
                        if os.name == 'nt':
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                import signal
                                process.send_signal(signal.CTRL_BREAK_EVENT)
                                try:
                                    process.wait(timeout=3)
                                except subprocess.TimeoutExpired:
                                    process.kill()
                                    process.wait()
                        else:
                            import signal
                            try:
                                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                                process.wait(timeout=5)
                            except (ProcessLookupError, subprocess.TimeoutExpired):
                                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                                process.wait()
                    except Exception as e:
                        logger.warning("停止节点时出错: %e")
                        try:
                            process.kill()
                            process.wait()
                        except:
                            pass
                
                # 删除文件夹
                import shutil
                shutil.rmtree(node_path)
                
                # 从节点组中移除
                current_group = self.group_manager.get_node_group(node_name)
                if current_group:
                    self.group_manager.remove_nodes_from_group(current_group, [node_name])
                
                # 从数据中移除
                del self.nodes_data[node_name]
                
                # 从节点注册表中注销
                if registry:
                    registry.unregister_node(node_name)
                
                # 从画布中移除
                if self.parent_window:
                    self.parent_window.canvas.remove_node_from_canvas(node_name)
                
                success_count += 1
                
            except Exception as e:
                logger.warning("删除节点 %node_name 失败: %e")
                fail_count += 1
                failed_nodes.append(node_name)
        
        # 保存注册表变更
        if registry:
            try:
                registry.save()
            except Exception:
                pass
        
        # 刷新列表
        self.update_node_list(self.nodes_data)
        
        # 显示结果
        msg = f"成功删除 {success_count} 个节点"
        if fail_count > 0:
            msg += f"\n{fail_count} 个节点删除失败:\n" + "\n".join(failed_nodes[:5])
            if len(failed_nodes) > 5:
                msg += f"\n...等{len(failed_nodes)}个"
        
        QMessageBox.information(self, t("k_title_batch_delete_result"), msg)
        
        if self.parent_window:
            self.parent_window.show_toast(f"已删除 {success_count} 个节点", "success")
    
    def batch_add_nodes_to_canvas(self):
        """批量添加选中的节点到画布"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要添加的节点", "warning")
            return
        
        if not self.parent_window:
            return
        
        success_count = 0
        skip_count = 0
        
        for node_name in selected_nodes:
            # 检查节点是否已在画布上
            if node_name in self.parent_window.canvas.nodes:
                skip_count += 1
                continue
            
            # 添加到画布
            self.parent_window.canvas.add_node_to_canvas(node_name)
            success_count += 1
        
        msg = f"已添加 {success_count} 个节点到画布"
        if skip_count > 0:
            msg += f"，{skip_count} 个节点已在画布上"
        
        self.parent_window.show_toast(msg, "success")
    
    def batch_open_node_folders(self):
        """批量打开选中的节点文件夹"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要打开的节点", "warning")
            return
        
        import platform
        
        for node_name in selected_nodes:
            if node_name in self.nodes_data:
                node_path = self.nodes_data[node_name]['path']
                
                system = platform.system()
                if system == "Windows":
                    subprocess.Popen(['explorer', node_path])
                elif system == "Darwin":  # macOS
                    subprocess.Popen(['open', node_path])
                else:  # Linux
                    subprocess.Popen(['xdg-open', node_path])
        
        if self.parent_window:
            self.parent_window.show_toast(f"已打开 {len(selected_nodes)} 个节点文件夹", "success")
    
    def batch_view_node_logs(self):
        """批量查看选中的节点日志"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要查看日志的节点", "warning")
            return
        
        # 收集所有日志内容
        all_logs = []
        missing_logs = []
        
        for node_name in selected_nodes:
            if node_name not in self.nodes_data:
                continue
            
            node_path = self.nodes_data[node_name]['path']
            log_file = os.path.join(node_path, "logs", "listener.log")
            
            if not os.path.exists(log_file):
                missing_logs.append(node_name)
                continue
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                
                all_logs.append(f"{'='*60}\n节点: {node_name}\n{'='*60}\n{log_content}\n")
            except Exception as e:
                logger.warning("读取节点 %node_name 日志失败: %e")
        
        if not all_logs:
            QMessageBox.information(self, t("k_title_info"), t("k_node_no_log_available"))
            return
        
        # 显示合并的日志内容
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"批量日志查看 - {len(selected_nodes)} 个节点")
        dialog.setGeometry(200, 200, 900, 700)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText("\n".join(all_logs))
        layout.addWidget(text_edit)
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.exec()
    
    def batch_edit_node_configs(self):
        """批量编辑选中的节点配置"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要编辑配置的节点", "warning")
            return
        
        # 如果只有一个节点，直接打开配置对话框
        if len(selected_nodes) == 1:
            node_name = selected_nodes[0]
            self.edit_node_config(node_name)
            return
        
        # 多个节点时，显示确认对话框
        reply = QMessageBox.question(
            self, "批量编辑配置",
            f"您选中了 {len(selected_nodes)} 个节点。\n\n"
            f"将依次打开每个节点的配置对话框。\n"
            f"是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 依次打开每个节点的配置对话框
        for node_name in selected_nodes:
            if node_name in self.nodes_data:
                node_info = self.nodes_data[node_name]
                config = node_info['config']
                node_path = node_info['path']
                
                from ui.panels.property_panel import NodeConfigDialog
                dialog = NodeConfigDialog(node_name, config, node_path, self.parent_window)
                dialog.exec()
    
    def _get_common_group(self, node_names):
        """获取多个节点的共同组（如果都在同一个组）"""
        if not node_names:
            return None
        
        groups = set()
        for node_name in node_names:
            group = self.group_manager.get_node_group(node_name)
            if group:
                groups.add(group)
            else:
                return None  # 如果有节点不在任何组，返回None
        
        # 如果所有节点都在同一个组，返回该组名
        if len(groups) == 1:
            return groups.pop()
        
        return None
    
    def batch_remove_nodes_from_group(self, group_name):
        """批量从组中移除选中的节点"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要移除的节点", "warning")
            return
        
        if self.group_manager.remove_nodes_from_group(group_name, selected_nodes):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已将 {len(selected_nodes)} 个节点从组 {group_name} 移除", "success")
    
    def start_group_nodes(self, group_name):
        """启动组内所有节点"""
        group_nodes = self.group_manager.get_group_nodes(group_name)
        
        if not group_nodes:
            if self.parent_window:
                self.parent_window.show_toast(f"组 '{group_name}' 中没有节点", "warning")
            return
        
        success_count = 0
        for node_name in group_nodes:
            if node_name in self.nodes_data and self.nodes_data[node_name]['status'] == 'stopped':
                try:
                    self._start_single_node(node_name)
                    success_count += 1
                except Exception as e:
                    logger.warning("启动节点 %node_name 失败: %e")
        
        if self.parent_window:
            self.parent_window.show_toast(f"已启动组 '{group_name}' 中的 {success_count} 个节点", "success")
    
    def stop_group_nodes(self, group_name):
        """停止组内所有节点"""
        group_nodes = self.group_manager.get_group_nodes(group_name)
        
        if not group_nodes:
            if self.parent_window:
                self.parent_window.show_toast(f"组 '{group_name}' 中没有节点", "warning")
            return
        
        success_count = 0
        for node_name in group_nodes:
            if node_name in self.nodes_data and self.nodes_data[node_name]['status'] == 'running':
                try:
                    self._stop_single_node(node_name)
                    success_count += 1
                except Exception as e:
                    logger.warning("停止节点 %node_name 失败: %e")
        
        if self.parent_window:
            self.parent_window.show_toast(f"已停止组 '{group_name}' 中的 {success_count} 个节点", "success")
    
    def start_ungrouped_nodes(self):
        """启动所有未分组节点"""
        all_nodes = list(self.nodes_data.keys())
        ungrouped_nodes = self.group_manager.get_ungrouped_nodes(all_nodes)
        
        if not ungrouped_nodes:
            if self.parent_window:
                self.parent_window.show_toast("没有未分组的节点", "warning")
            return
        
        success_count = 0
        for node_name in ungrouped_nodes:
            if self.nodes_data[node_name]['status'] == 'stopped':
                try:
                    self._start_single_node(node_name)
                    success_count += 1
                except Exception as e:
                    logger.warning("启动节点 %node_name 失败: %e")
        
        if self.parent_window:
            self.parent_window.show_toast(f"已启动 {success_count} 个未分组节点", "success")
    
    def stop_ungrouped_nodes(self):
        """停止所有未分组节点"""
        all_nodes = list(self.nodes_data.keys())
        ungrouped_nodes = self.group_manager.get_ungrouped_nodes(all_nodes)
        
        if not ungrouped_nodes:
            if self.parent_window:
                self.parent_window.show_toast("没有未分组的节点", "warning")
            return
        
        success_count = 0
        for node_name in ungrouped_nodes:
            if self.nodes_data[node_name]['status'] == 'running':
                try:
                    self._stop_single_node(node_name)
                    success_count += 1
                except Exception as e:
                    logger.warning("停止节点 %node_name 失败: %e")
        
        if self.parent_window:
            self.parent_window.show_toast(f"已停止 {success_count} 个未分组节点", "success")
    
    def create_group_from_ungrouped(self, ungrouped_nodes):
        """从未分组节点创建新组"""
        if not ungrouped_nodes:
            if self.parent_window:
                self.parent_window.show_toast("没有未分组的节点", "warning")
            return
        
        group_name, ok = QInputDialog.getText(
            self, t("k_group_create_new"),
            f"将为 {len(ungrouped_nodes)} 个未分组节点创建新组\n请输入组名称:"
        )
        
        if not ok or not group_name:
            return
        
        # 选择颜色
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor("#7ED321"), self, t("k_color_select_group"))
        
        if not color.isValid():
            color = QColor("#7ED321")
        
        # 创建组并添加节点
        if self.group_manager.create_group(group_name, color.name()):
            self.group_manager.add_nodes_to_group(group_name, ungrouped_nodes)
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已创建组 '{group_name}' 并添加 {len(ungrouped_nodes)} 个节点", "success")
    
    def _start_single_node(self, node_name):
        """启动单个节点（调用父窗口的方法）"""
        if self.parent_window:
            self.parent_window.start_selected_node_by_name(node_name)
    
    def _stop_single_node(self, node_name):
        """停止单个节点（调用父窗口的方法）"""
        if self.parent_window:
            self.parent_window.stop_selected_node_by_name(node_name)
    
    # ==================== 鼠标拖动支持（继承自 FloatingPanel 基类）====================

    def set_project_path(self, project_path):
        """设置项目路径并加载节点组配置"""
        self.group_manager.set_project_path(project_path)

