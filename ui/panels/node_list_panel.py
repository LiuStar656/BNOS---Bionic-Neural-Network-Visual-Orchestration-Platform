"""
节点列表面板 - 常驻半透明悬浮窗，显示项目中的所有节点
支持多选、分组管理、批量操作（所有操作通过右键菜单）
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QFileDialog, QInputDialog, QDialog, QPushButton, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.floating_panel import FloatingPanel
from ui.core.utils.dialog_utils import themed_message
from ui.core.polling_manager import polling_manager
from ui.panels.node_list_drag import NodeListDragMixin
from ui.panels.node_list_context import NodeListContextMixin
from ui.panels.node_list_ops import NodeListOperationsMixin
import subprocess
import json
import os


class NodeListPanel(FloatingPanel, NodeListOperationsMixin, NodeListDragMixin, NodeListContextMixin):
    """节点列表面板（常驻半透明悬浮窗）- 精简版
    
    设计理念：极简UI，所有操作通过右键菜单完成
    - 树形结构显示节点和组
    - 支持Ctrl/Shift多选
    - 所有功能集成到右键菜单
    - 订阅全局状态变化，保持与其他面板同步
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
        self.group_manager.on_changed = lambda: self.update_node_list(self.nodes_data)
        
        # 订阅全局节点状态变化
        polling_manager.node_status_changed.connect(self._on_node_status_changed)
        
        # init_ui 使用基类的 content_layout
        self._init_ui()
        
    def _init_ui(self):
        """初始化UI - 极简设计"""
        
        # 路径显示
        self.path_label = QLabel(t("k_node_no_project"))
        self.path_label.setStyleSheet("color: rgba(255, 255, 255, 120); font-size: 9px; padding: 2px 0;")
        self.content_layout.addWidget(self.path_label)
        
        # 提示文本
        hint_label = QLabel(t("k_node_right_click"))
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
    
    # ===== 以下方法继承自 NodeListOperationsMixin（~800行重复代码已移除）=====
    # 共享方法: _setup_node_item, update_node_status, _on_node_status_changed,
    #   get_selected_nodes, get_selected_groups, on_node_double_clicked,
    #   add_node_to_canvas, open_node_folder, view_node_log, edit_node_config,
    #   _force_stop_node_processes, _force_delete_directory,
    #   _delete_node_async, delete_node, _on_delete_node_complete,
    #   _cleanup_empty_groups, select_all_nodes, deselect_all_nodes,
    #   create_node_group, move_node_to_group, batch_move_nodes_to_group,
    #   remove_node_from_group, _get_common_group, batch_remove_nodes_from_group,
    #   rename_group, delete_group, toggle_group_expansion,
    #   _start_single_node, _stop_single_node, batch_add_nodes_to_canvas,
    #   batch_start_nodes, batch_stop_nodes, batch_open_node_folders,
    #   batch_view_node_logs, batch_edit_node_configs

    # ==================== 独有方法（实现与 Mixin 不同）====================

    def rename_node(self, old_name):
        """重命名节点"""
        if old_name not in self.nodes_data:
            return
        
        from ui.core.floating_panel import themed_input_dialog
        new_name = themed_input_dialog(self, t("k_node_rename"), t("k_node_input_new_name"), old_name)
        if not new_name:
            return
        
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', new_name):
            themed_message(self, t("k_title_warning"), t("k_node_name_invalid"), "warning")
            return
        
        if new_name != old_name and new_name in self.nodes_data:
            themed_message(self, t("k_title_warning"), t("_k_node_name_exists").format(name=new_name), "warning")
            return
        
        try:
            node_info = self.nodes_data[old_name]
            old_path = node_info['path']
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            
            if os.path.exists(new_path):
                themed_message(self, t("k_title_warning"), t("_k_folder_exists").format(name=new_name), "warning")
                return
            
            os.rename(old_path, new_path)
            
            config_path = os.path.join(new_path, "config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            config['node_name'] = new_name
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            node_info['path'] = new_path
            node_info['config'] = config
            
            current_group = self.group_manager.get_node_group(old_name)
            if current_group:
                self.group_manager.remove_nodes_from_group(current_group, [old_name])
                self.group_manager.add_nodes_to_group(current_group, [new_name])
            
            del self.nodes_data[old_name]
            self.nodes_data[new_name] = node_info
            
            if self.parent_window and self.parent_window.canvas:
                self.parent_window.canvas.rename_node_in_canvas(old_name, new_name)
                if hasattr(self.parent_window.canvas, '_save_timer'):
                    self.parent_window.canvas._save_timer.stop()
                if self.parent_window.current_project_path:
                    self.parent_window.canvas.save_layout(self.parent_window.current_project_path)
                if hasattr(self.parent_window.canvas, '_save_timer'):
                    self.parent_window.canvas._save_timer.start()
            
            if self.parent_window:
                self.parent_window.refresh_nodes()
            else:
                self.update_node_list(self.nodes_data)

            themed_message(self, t("k_title_success"), t("_k_node_renamed").format(name=new_name), "info")
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_rename_failed").format(err=str(e)), "error")
            import traceback
            traceback.print_exc()

    def batch_delete_nodes(self):
        """批量删除选中的节点（异步执行，逐个删除）"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要删除的节点", "warning")
            return
        
        reply = themed_message(self, t("k_title_confirm_batch_delete"),
            t("_k_confirm_batch_delete").format(count=len(selected_nodes))
            + "\n".join(selected_nodes[:10]) + ("..." if len(selected_nodes) > 10 else ""),
            "question")
        
        if not reply:
            return
        
        self._batch_delete_results = {'success': 0, 'failed': 0, 'failed_nodes': []}
        self._batch_delete_total = len(selected_nodes)
        
        if self.parent_window:
            self.parent_window.show_toast(f"正在删除 {len(selected_nodes)} 个节点...", "info",
                                            node_name="batch_operation", operation_type="batch_delete")
        
        def delete_next(index):
            if index >= len(selected_nodes):
                msg = f"成功删除 {self._batch_delete_results['success']} 个节点"
                if self._batch_delete_results['failed'] > 0:
                    failed_list = self._batch_delete_results['failed_nodes'][:5]
                    msg += f"\n{self._batch_delete_results['failed']} 个节点删除失败:\n" + "\n".join(failed_list)
                    if len(self._batch_delete_results['failed_nodes']) > 5:
                        msg += f"\n...等{len(self._batch_delete_results['failed_nodes'])}个"
                
                if self._batch_delete_results['success'] > 0 or self._batch_delete_results['failed'] > 0:
                    themed_message(self, t("k_title_batch_delete_result"), msg, "info")
                
                if self.parent_window:
                    self.parent_window.show_toast(f"已删除 {self._batch_delete_results['success']} 个节点", "success",
                                                    node_name="batch_operation", operation_type="batch_delete")
                return
            
            node_name = selected_nodes[index]
            if node_name not in self.nodes_data:
                self._batch_delete_results['failed'] += 1
                self._batch_delete_results['failed_nodes'].append(node_name)
                QTimer.singleShot(100, lambda: delete_next(index + 1))
                return
            
            if self.nodes_data[node_name].get('mounted'):
                QTimer.singleShot(100, lambda: delete_next(index + 1))
                return
            
            self._delete_node_async(node_name, lambda ok, err: self._on_batch_delete_node_complete(node_name, ok, err, delete_next, index))
        
        delete_next(0)

    def _on_batch_delete_node_complete(self, node_name, success, error, delete_next, index):
        """批量删除节点完成回调"""
        if success:
            self._batch_delete_results['success'] += 1
        else:
            self._batch_delete_results['failed'] += 1
            self._batch_delete_results['failed_nodes'].append(node_name)
        delete_next(index + 1)

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
                    logger.warning("启动节点 %s 失败: %s", node_name, e)
        
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
                    logger.warning("停止节点 %s 失败: %s", node_name, e)
        
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
                    logger.warning("启动节点 %s 失败: %s", node_name, e)
        
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
                    logger.warning("停止节点 %s 失败: %s", node_name, e)
        
        if self.parent_window:
            self.parent_window.show_toast(f"已停止 {success_count} 个未分组节点", "success")

    def create_group_from_ungrouped(self, ungrouped_nodes):
        """从未分组节点创建新组"""
        if not ungrouped_nodes:
            if self.parent_window:
                self.parent_window.show_toast("没有未分组的节点", "warning")
            return
        
        from ui.core.floating_panel import themed_input_dialog
        group_name = themed_input_dialog(self, t("k_group_create_new"), f"将为 {len(ungrouped_nodes)} 个未分组节点创建新组\n请输入组名称:")
        if not group_name:
            return
        
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor("#7ED321"), self, t("k_color_select_group"))
        if not color.isValid():
            color = QColor("#7ED321")
        
        if self.group_manager.create_group(group_name, color.name()):
            self.group_manager.add_nodes_to_group(group_name, ungrouped_nodes)
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已创建组 '{group_name}' 并添加 {len(ungrouped_nodes)} 个节点", "success")

    # ==================== 鼠标拖动支持（继承自 FloatingPanel 基类）====================

    def set_project_path(self, project_path):
        """设置项目路径并加载节点组配置"""
        self.group_manager.set_project_path(project_path)