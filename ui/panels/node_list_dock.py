"""
节点列表Dock面板 - 用于QDockWidget的无标题栏版本
包含完整的节点管理功能：分组、右键菜单、拖拽等
"""
import os
import json
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
    QLabel, QMenu, QMessageBox, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont

from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.utils.dialog_utils import themed_message
from ui.core.polling_manager import polling_manager
from ui.panels.node_list_drag import NodeListDragMixin
from ui.panels.node_list_context import NodeListContextMixin
from ui.panels.node_list_ops import NodeListOperationsMixin


class NodeListDockPanel(QWidget, NodeListOperationsMixin, NodeListDragMixin, NodeListContextMixin):
    """节点列表面板（Dock版本）- 无标题栏，用于停靠"""
    
    node_double_clicked = Signal(str)
    node_right_clicked = Signal(str, object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.nodes_data = {}
        self.selected_node_ids = []

        from ui.panels.node_group_manager import NodeGroupManager
        initial_project = None
        if parent is not None and hasattr(parent, 'current_project_path'):
            initial_project = parent.current_project_path
        self.group_manager = NodeGroupManager(initial_project)
        self.group_manager.on_changed = lambda: self.update_node_list(self.nodes_data)

        # 先初始化UI，确保 path_label 等控件存在
        self._init_ui()

        # 若创建时已有项目数据，且 nodes_data 非空，直接填充一次，避免空面板
        initial_nodes = None
        if parent is not None and hasattr(parent, 'nodes_data') and parent.nodes_data:
            initial_nodes = dict(parent.nodes_data)
        if initial_project:
            # 先设置项目路径（此方法内部会加载分组）
            self.set_project_path(initial_project)
        if initial_nodes:
            # 再刷新节点列表 UI
            self.update_node_list(initial_nodes)
        
        # 订阅全局节点状态变化
        polling_manager.node_status_changed.connect(self._on_node_status_changed)
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 路径显示
        self.path_label = QLabel(t("k_node_no_project"))
        self.path_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 120); 
                font-size: 9px; 
                padding: 4px 8px;
                background-color: #252526;
                border-bottom: 1px solid #3c3c3c;
            }
        """)
        layout.addWidget(self.path_label)
        
        # 提示文本
        hint_label = QLabel(t("k_node_right_click"))
        hint_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 100); 
                font-size: 10px; 
                font-style: italic; 
                padding: 2px 8px;
                background-color: #2d2d30;
            }
        """)
        layout.addWidget(hint_label)
        
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
                background-color: #1e1e1e;
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
        """)
        layout.addWidget(self.node_tree)
    
    def update_node_list(self, nodes_data):
        """更新节点列表（树形结构，支持分组）"""
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
        
        # 显示不属于任何组的节点（直接作为根节点）
        all_grouped_nodes = set()
        for group_info in groups.values():
            all_grouped_nodes.update(group_info['nodes'])
        
        root_nodes = [name for name in nodes_data.keys() if name not in all_grouped_nodes]
        
        if root_nodes:
            for node_name in sorted(root_nodes):
                if node_name in nodes_data:
                    node_item = QTreeWidgetItem(self.node_tree)
                    self._setup_node_item(node_item, node_name, nodes_data[node_name])
                    node_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'node', 'name': node_name, 'level': 'root'})
        
        # 更新路径显示
        if self.parent_window and hasattr(self.parent_window, 'current_project_path') and self.parent_window.current_project_path:
            self.path_label.setText(f"{t('k_project')}: {os.path.basename(self.parent_window.current_project_path)}")
        else:
            self.path_label.setText(t("k_node_no_project"))
    
    def refresh(self):
        """便捷刷新方法：从 parent_window.nodes_data 重新加载节点列表"""
        if self.parent_window and hasattr(self.parent_window, 'nodes_data'):
            self.update_node_list(self.parent_window.nodes_data)

    # ===== 以下方法继承自 NodeListOperationsMixin =====
    # _setup_node_item, update_node_status, _on_node_status_changed,
    # get_selected_nodes, get_selected_groups, on_node_double_clicked,
    # add_node_to_canvas, open_node_folder, view_node_log, edit_node_config,
    # _force_stop_node_processes, _force_delete_directory,
    # _delete_node_async, delete_node, _on_delete_node_complete,
    # _cleanup_empty_groups, select_all_nodes, deselect_all_nodes,
    # create_node_group, move_node_to_group, batch_move_nodes_to_group,
    # remove_node_from_group, _get_common_group, batch_remove_nodes_from_group,
    # rename_group, delete_group, toggle_group_expansion,
    # _start_single_node, _stop_single_node, batch_add_nodes_to_canvas,
    # batch_start_nodes, batch_stop_nodes, batch_open_node_folders,
    # batch_view_node_logs, batch_edit_node_configs
    
    def batch_delete_nodes(self):
        """批量删除选中的节点（异步执行，逐个删除）"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要删除的节点", "warning")
            return
        
        reply = themed_message(self, t("k_title_confirm_batch_delete"),
            t("_k_confirm_batch_delete").format(count=len(selected_nodes)) + "\n" + "\n".join(selected_nodes[:10]) + 
            ("..." if len(selected_nodes) > 10 else ""), "question")
        
        if not reply:
            return
        
        # 异步逐个删除，每次间隔 100ms
        def delete_next(index):
            if index >= len(selected_nodes):
                # 所有节点删除完成
                if self.parent_window:
                    self.parent_window.show_toast(f"已删除 {len(selected_nodes)} 个节点", "success")
                return
            
            node_name = selected_nodes[index]
            if node_name in self.nodes_data:
                # 跳过挂载节点
                if self.nodes_data[node_name].get('mounted'):
                    QTimer.singleShot(100, lambda: delete_next(index + 1))
                    return
                
                self._delete_node_async(node_name, lambda ok, err: delete_next(index + 1))
            else:
                QTimer.singleShot(100, lambda: delete_next(index + 1))
        
        # 开始异步删除
        delete_next(0)
    
    def rename_node(self, old_name):
        """重命名节点（委托给主窗口）"""
        if self.parent_window and hasattr(self.parent_window, 'rename_node'):
            self.parent_window.rename_node(old_name)
    
    def start_group_nodes(self, group_name):
        """启动组内所有节点"""
        group_nodes = self.group_manager.get_group_nodes(group_name)
        if not group_nodes:
            if self.parent_window:
                self.parent_window.show_toast(f"组 '{group_name}' 中没有节点", "warning")
            return
        
        for node_name in group_nodes:
            if node_name in self.nodes_data and self.nodes_data[node_name].get('status') == 'stopped':
                self._start_single_node(node_name)
        
        if self.parent_window:
            self.parent_window.show_toast(f"已启动组 '{group_name}' 中的节点", "success")
    
    def stop_group_nodes(self, group_name):
        """停止组内所有节点"""
        group_nodes = self.group_manager.get_group_nodes(group_name)
        if not group_nodes:
            if self.parent_window:
                self.parent_window.show_toast(f"组 '{group_name}' 中没有节点", "warning")
            return
        
        for node_name in group_nodes:
            if node_name in self.nodes_data and self.nodes_data[node_name].get('status') in ('running', 'idle'):
                self._stop_single_node(node_name)
        
        if self.parent_window:
            self.parent_window.show_toast(f"已停止组 '{group_name}' 中的节点", "success")
    
    def set_project_path(self, path):
        """设置项目路径，重新加载分组配置并刷新节点列表UI"""
        if path:
            self.path_label.setText(f"{t('k_project')}: {os.path.basename(path)}")
        else:
            self.path_label.setText(t("k_node_no_project"))

        # 让分组管理器跟随项目加载，确保分组信息（node_groups.json）持久化可用
        if hasattr(self, 'group_manager') and self.group_manager is not None:
            try:
                self.group_manager.set_project_path(path)
            except Exception as e:
                from ui.core.logger import logger
                logger.warning("NodeListDockPanel.set_project_path 加载分组失败: %s", e)

        # 关键：在分组加载完成后，如果已有节点数据则刷新UI，确保切换到dock版能立即显示节点
        if self.nodes_data:
            self.update_node_list(self.nodes_data)