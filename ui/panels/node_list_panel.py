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
from ui.core.utils.dialog_utils import themed_message
from ui.core.polling_manager import polling_manager
from ui.panels.node_list_drag import NodeListDragMixin
from ui.panels.node_list_context import NodeListContextMixin
import subprocess
import json
import os


class NodeListPanel(FloatingPanel, NodeListDragMixin, NodeListContextMixin):
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

    def _on_node_status_changed(self, node_name, new_status):
        """处理全局节点状态变化信号"""
        self.update_node_status(node_name, new_status)
    
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
            if self.parent_window.canvas and node_name in self.parent_window.canvas.nodes:
                self.parent_window.show_toast(t("_k_node_canvas_exists").format(name=node_name), "warning")
                return
            
            # 添加到画布
            self.add_node_to_canvas(node_name)
    
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
                self.parent_window.show_toast(t("_k_auto_deleted_groups").format(count=len(empty_groups)), "info")
            
            logger.debug("✅ 自动删除空节点组: {', '.join(empty_groups)}")
            return True
        
        return False
    
    def add_node_to_canvas(self, node_name):
        """添加节点到画布"""
        if self.parent_window:
            if self.parent_window.canvas:
                self.parent_window.canvas.add_node_to_canvas(node_name)

    def open_node_folder(self, node_name):
        """打开节点文件夹"""
        if node_name not in self.nodes_data:
            themed_message(self, t("k_title_warning"), t("_k_node_not_found").format(name=node_name), "warning")
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
            themed_message(self, t("k_title_info"), t("k_node_no_log"), "info")
            return
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            from ui.core.utils.log_viewer import show_log_dialog
            show_log_dialog(self, f"节点日志 - {node_name}", log_content)
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_log_read_fail").format(err=str(e)), "error")
            
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
        
        reply = themed_message(self, t("k_title_confirm_delete"), t("_k_confirm_delete_node").format(name=node_name),
            "question")
        
        if not reply:
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
            if self.parent_window and self.parent_window.canvas:
                self.parent_window.canvas.remove_node_from_canvas(node_name)
            
            # 刷新列表
            self.update_node_list(self.nodes_data)
            
            # 通知主窗口刷新所有面板
            if self.parent_window and hasattr(self.parent_window, '_refresh_panels'):
                self.parent_window._refresh_panels()
            
            themed_message(self, t("k_title_success"), t("_k_node_deleted").format(name=node_name), "info")
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_node_delete_failed").format(err=str(e)), "error")
    
    def rename_node(self, old_name):
        """重命名节点"""
        if old_name not in self.nodes_data:
            return
        
        # 输入新名称
        from ui.core.floating_panel import themed_input_dialog
        new_name = themed_input_dialog(self, t("k_node_rename"), t("k_node_input_new_name"), old_name)
        if not new_name:
            return
        
        # 验证名称格式
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', new_name):
            themed_message(self, t("k_title_warning"), t("k_node_name_invalid"), "warning")
            return
        
        # 检查名称是否已存在
        if new_name != old_name and new_name in self.nodes_data:
            themed_message(self, t("k_title_warning"), t("_k_node_name_exists").format(name=new_name), "warning")
            return
        
        try:
            node_info = self.nodes_data[old_name]
            old_path = node_info['path']
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            
            # 1. 重命名文件夹
            if os.path.exists(new_path):
                themed_message(self, t("k_title_warning"), t("_k_folder_exists").format(name=new_name), "warning")
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
            
            if self.parent_window and self.parent_window.canvas:
                self.parent_window.canvas.rename_node_in_canvas(old_name, new_name)
                if hasattr(self.parent_window.canvas, '_save_timer'):
                    self.parent_window.canvas._save_timer.stop()
                if self.parent_window.current_project_path:
                    self.parent_window.canvas.save_layout(self.parent_window.current_project_path)
                if hasattr(self.parent_window.canvas, '_save_timer'):
                    self.parent_window.canvas._save_timer.start()
            
            # 7. 刷新父窗口的节点数据（重新从磁盘加载）
            if self.parent_window:
                self.parent_window.refresh_nodes()
            else:
                # 如果没有父窗口，只更新本地列表
                self.update_node_list(self.nodes_data)

            themed_message(self, t("k_title_success"), t("_k_node_renamed").format(name=new_name), "info")
            
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_rename_failed").format(err=str(e)), "error")
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
        from ui.core.floating_panel import themed_input_dialog
        group_name = themed_input_dialog(self, t("k_group_create_group"), t("k_node_input_new_group_name"))
        if not group_name:
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
                reply = themed_message(self, t("k_title_add_to_group"), t("_k_add_to_group_prompt").format(count=len(selected_nodes), name=group_name),
                    "question")
                
                if reply:
                    self.group_manager.add_nodes_to_group(group_name, selected_nodes)
            
            # 刷新列表
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已创建组: {group_name}", "success")
    
    def move_node_to_group(self, node_name, group_name):
        """移动节点到指定组"""
        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("禁止将节点移入挂载组", "warning")
            return
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
        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("禁止将节点移入挂载组", "warning")
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
        from ui.core.floating_panel import themed_input_dialog
        new_name = themed_input_dialog(self, t("k_group_rename"), t("k_group_input_new_name"), group_name)
        if not new_name:
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
        reply = themed_message(self, t("k_title_confirm_delete"), t("_k_confirm_delete_group").format(name=group_name),
            "question")
        
        if not reply:
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
        reply = themed_message(self, t("k_title_confirm_batch_delete"),
            t("_k_confirm_batch_delete").format(count=len(selected_nodes))
            + "\n".join(selected_nodes[:10]) + ("..." if len(selected_nodes) > 10 else ""),
            "question")
        
        if not reply:
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
                if self.parent_window and self.parent_window.canvas:
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
        
        # 通知主窗口刷新所有面板
        if self.parent_window and hasattr(self.parent_window, '_refresh_panels'):
            self.parent_window._refresh_panels()
        
        # 显示结果
        msg = f"成功删除 {success_count} 个节点"
        if fail_count > 0:
            msg += f"\n{fail_count} 个节点删除失败:\n" + "\n".join(failed_nodes[:5])
            if len(failed_nodes) > 5:
                msg += f"\n...等{len(failed_nodes)}个"
        
        themed_message(self, t("k_title_batch_delete_result"), msg, "info")
        
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
            if self.parent_window.canvas and node_name in self.parent_window.canvas.nodes:
                skip_count += 1
                continue
            
            if self.parent_window.canvas:
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
        
        from ui.core.utils.file_utils import resolve_and_open_folder
        
        for node_name in selected_nodes:
            if node_name in self.nodes_data:
                node_path = self.nodes_data[node_name]['path']
                resolve_and_open_folder(node_path, node_name, self.parent_window, dialog_parent=self)
        
        if self.parent_window:
            self.parent_window.show_toast(f"已打开 {len(selected_nodes)} 个节点文件夹", "success")
    
    def batch_view_node_logs(self):
        """批量查看选中的节点日志"""
        selected_nodes = self.get_selected_nodes()
        
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要查看日志的节点", "warning")
            return
        
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
                logger.warning("读取节点 %s 日志失败: %s", node_name, e)
        
        if not all_logs:
            themed_message(self, t("k_title_info"), t("k_node_no_log_available"), "info")
            return
        
        from ui.core.utils.log_viewer import show_log_dialog
        show_log_dialog(self, f"批量日志查看 - {len(selected_nodes)} 个节点", "\n".join(all_logs), width=900, height=700)
    
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
        reply = themed_message(self, t("_k_batch_edit_config"), t("_k_batch_edit_config_prompt").format(count=len(selected_nodes)),
            "question")
        
        if not reply:
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

        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("挂载组内的节点禁止移出", "warning")
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
        
        from ui.core.floating_panel import themed_input_dialog
        group_name = themed_input_dialog(self, t("k_group_create_new"), f"将为 {len(ungrouped_nodes)} 个未分组节点创建新组\n请输入组名称:")
        if not group_name:
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