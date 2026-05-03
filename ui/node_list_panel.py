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
import subprocess
import json
import os


class NodeListPanel(QDialog):
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
        super().__init__(parent)
        self.parent_window = parent
        self.nodes_data = {}
        
        # 初始化节点组管理器
        from ui.node_group_manager import NodeGroupManager
        self.group_manager = NodeGroupManager()
        
        # 设置窗口标志：工具窗口、置顶、无边框
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI - 极简设计"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建容器widget用于半透明背景
        container = QWidget(self)
        container.setObjectName("container")
        container.setStyleSheet("""
            QWidget#container {
                background-color: rgba(30, 30, 30, 200);
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 标题栏（可拖动）
        title_layout = QHBoxLayout()
        title_label = QLabel("📋 节点列表")
        title_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # 最小化按钮
        minimize_btn = QLabel("─")
        minimize_btn.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 150);
                font-size: 16px;
                padding: 0px 5px;
            }
            QLabel:hover {
                color: white;
                background-color: rgba(255, 255, 255, 30);
                border-radius: 3px;
            }
        """)
        minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        minimize_btn.mousePressEvent = lambda e: self.showMinimized()
        title_layout.addWidget(minimize_btn)
        
        layout.addLayout(title_layout)
        
        # 路径显示
        self.path_label = QLabel("未打开项目")
        self.path_label.setStyleSheet("color: rgba(255, 255, 255, 120); font-size: 9px; padding: 2px 0;")
        layout.addWidget(self.path_label)
        
        # 提示文本
        hint_label = QLabel("💡 右键查看更多操作")
        hint_label.setStyleSheet("color: rgba(255, 255, 255, 100); font-size: 10px; font-style: italic; padding: 2px 0;")
        layout.addWidget(hint_label)
        
        # 节点树形列表（支持分组显示和多选）
        self.node_tree = QTreeWidget()
        self.node_tree.setHeaderHidden(True)
        self.node_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)  # 支持多选
        self.node_tree.itemDoubleClicked.connect(self.on_node_double_clicked)
        self.node_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.node_tree.customContextMenuRequested.connect(self.show_context_menu)
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
        layout.addWidget(self.node_tree)
        
        main_layout.addWidget(container)
        
        # 设置初始大小
        self.resize(280, 500)
    
    def update_node_list(self, nodes_data):
        """更新节点列表（树形结构，支持分组）"""
        self.nodes_data = nodes_data
        
        # 清空树
        self.node_tree.clear()
        
        # 按组组织节点
        groups = self.group_manager.get_all_groups()
        ungrouped_nodes = self.group_manager.get_ungrouped_nodes(list(nodes_data.keys()))
        
        # 添加各个组
        for group_name, group_info in sorted(groups.items()):
            group_item = QTreeWidgetItem(self.node_tree)
            group_item.setText(0, f"📁 {group_name} ({len(group_info['nodes'])})")
            group_item.setForeground(0, QColor(group_info.get('color', '#4A90E2')))
            group_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            
            # 标记为组节点
            group_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'group', 'name': group_name})
            
            # 添加组内节点
            for node_name in sorted(group_info['nodes']):
                if node_name in nodes_data:
                    node_item = QTreeWidgetItem(group_item)
                    self._setup_node_item(node_item, node_name, nodes_data[node_name])
            
            group_item.setExpanded(True)
        
        # 添加未分组的节点
        if ungrouped_nodes:
            ungrouped_item = QTreeWidgetItem(self.node_tree)
            ungrouped_item.setText(0, f"📄 未分组节点 ({len(ungrouped_nodes)})")
            ungrouped_item.setForeground(0, QColor("#9B9B9B"))
            ungrouped_item.setFont(0, QFont("Arial", 10, QFont.Weight.Bold))
            
            # 标记为未分组类别
            ungrouped_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'category', 'name': 'ungrouped'})
            
            # 添加未分组节点
            for node_name in sorted(ungrouped_nodes):
                if node_name in nodes_data:
                    node_item = QTreeWidgetItem(ungrouped_item)
                    self._setup_node_item(node_item, node_name, nodes_data[node_name])
            
            ungrouped_item.setExpanded(True)
        
        # 更新路径显示
        if self.parent_window and self.parent_window.current_project_path:
            self.path_label.setText(f"项目: {os.path.basename(self.parent_window.current_project_path)}")
        else:
            self.path_label.setText("未打开项目")
    
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
        
        elif data.get('type') == 'category' and data.get('name') == 'ungrouped':
            # 未分组类别菜单
            self._show_ungrouped_category_menu(menu)
        
        menu.exec(self.node_tree.mapToGlobal(position))
    
    def _show_global_context_menu(self, position):
        """显示全局右键菜单（空白处）"""
        menu = QMenu(self)
        
        # 创建新组
        create_group_action = menu.addAction("➕ 创建新组")
        create_group_action.triggered.connect(self.create_node_group)
        
        menu.addSeparator()
        
        # 全选
        select_all_action = menu.addAction("☑️ 全选节点")
        select_all_action.triggered.connect(self.select_all_nodes)
        
        # 取消选择
        deselect_all_action = menu.addAction("⬜ 取消选择")
        deselect_all_action.triggered.connect(self.deselect_all_nodes)
        
        menu.addSeparator()
        
        # 刷新列表
        refresh_action = menu.addAction("🔄 刷新列表")
        refresh_action.triggered.connect(lambda: self.update_node_list(self.nodes_data))
        
        menu.exec(self.node_tree.mapToGlobal(position))
    
    def _show_node_context_menu(self, menu, node_name):
        """显示节点右键菜单"""
        selected_nodes = self.get_selected_nodes()
        
        # 如果选中了多个节点，显示批量操作
        if len(selected_nodes) > 1 and node_name in selected_nodes:
            menu.addAction(f"📌 已选中 {len(selected_nodes)} 个节点").setEnabled(False)
            menu.addSeparator()
            
            # 批量启动
            batch_start_action = menu.addAction(f"▶️ 启动选中的 {len(selected_nodes)} 个节点")
            batch_start_action.triggered.connect(self.batch_start_nodes)
            
            # 批量停止
            batch_stop_action = menu.addAction(f"⏹️ 停止选中的 {len(selected_nodes)} 个节点")
            batch_stop_action.triggered.connect(self.batch_stop_nodes)
            
            menu.addSeparator()
            
            # 批量移动到组
            move_to_group_menu = menu.addMenu("📁 批量移动到组")
            groups = self.group_manager.get_all_groups()
            if groups:
                for group_name in sorted(groups.keys()):
                    action = move_to_group_menu.addAction(group_name)
                    action.triggered.connect(lambda checked, gn=group_name: self.batch_move_nodes_to_group(gn))
            else:
                move_to_group_menu.addAction("（无可用组）").setEnabled(False)
            
            menu.addSeparator()
        
        # 单个节点操作
        add_to_canvas_action = menu.addAction("➕ 添加到画布")
        add_to_canvas_action.triggered.connect(lambda: self.add_node_to_canvas(node_name))
        
        menu.addSeparator()
        
        # 移动到组
        move_to_group_menu = menu.addMenu("📁 移动到组")
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
            remove_from_group_action = menu.addAction(f"❌ 从组 '{current_group}' 移除")
            remove_from_group_action.triggered.connect(lambda: self.remove_node_from_group(node_name))
        
        menu.addSeparator()
        
        # 启动/停止
        node_info = self.nodes_data.get(node_name, {})
        if node_info.get('status') == 'running':
            stop_action = menu.addAction("⏹️ 停止节点")
            stop_action.triggered.connect(lambda: self._stop_single_node(node_name))
        else:
            start_action = menu.addAction("▶️ 启动节点")
            start_action.triggered.connect(lambda: self._start_single_node(node_name))
        
        menu.addSeparator()
        
        # 重命名节点
        rename_action = menu.addAction("✏️ 重命名节点")
        rename_action.triggered.connect(lambda: self.rename_node(node_name))
        
        menu.addSeparator()
        
        # 打开节点文件夹
        open_folder_action = menu.addAction("📁 打开节点文件夹")
        open_folder_action.triggered.connect(lambda: self.open_node_folder(node_name))
        
        # 查看日志
        view_log_action = menu.addAction("📄 查看日志")
        view_log_action.triggered.connect(lambda: self.view_node_log(node_name))
        
        menu.addSeparator()
        
        # 编辑配置
        edit_config_action = menu.addAction("⚙️ 编辑配置")
        edit_config_action.triggered.connect(lambda: self.edit_node_config(node_name))
        
        # 删除节点
        delete_action = menu.addAction("🗑️ 删除节点")
        delete_action.triggered.connect(lambda: self.delete_node(node_name))
    
    def _show_group_context_menu(self, menu, group_name):
        """显示组右键菜单"""
        group_nodes = self.group_manager.get_group_nodes(group_name)
        
        # 组信息
        menu.addAction(f"📁 组: {group_name}").setEnabled(False)
        menu.addAction(f"   节点数: {len(group_nodes)}").setEnabled(False)
        menu.addSeparator()
        
        # 启动组内所有节点
        running_count = sum(1 for n in group_nodes if self.nodes_data.get(n, {}).get('status') == 'running')
        stopped_count = len(group_nodes) - running_count
        
        if stopped_count > 0:
            start_group_action = menu.addAction(f"▶️ 启动组内所有节点 ({stopped_count}个)")
            start_group_action.triggered.connect(lambda: self.start_group_nodes(group_name))
        
        if running_count > 0:
            stop_group_action = menu.addAction(f"⏹️ 停止组内所有节点 ({running_count}个)")
            stop_group_action.triggered.connect(lambda: self.stop_group_nodes(group_name))
        
        menu.addSeparator()
        
        # 重命名组
        rename_group_action = menu.addAction("✏️ 重命名组")
        rename_group_action.triggered.connect(lambda: self.rename_group(group_name))
        
        # 删除组
        delete_group_action = menu.addAction("🗑️ 删除组（保留节点）")
        delete_group_action.triggered.connect(lambda: self.delete_group(group_name))
        
        menu.addSeparator()
        
        # 展开/折叠
        expand_action = menu.addAction("📂 展开/折叠")
        expand_action.triggered.connect(lambda: self.toggle_group_expansion(group_name))
    
    def _show_ungrouped_category_menu(self, menu):
        """显示未分组类别菜单"""
        all_nodes = list(self.nodes_data.keys())
        ungrouped_nodes = self.group_manager.get_ungrouped_nodes(all_nodes)
        
        menu.addAction(f"📄 未分组节点").setEnabled(False)
        menu.addAction(f"   数量: {len(ungrouped_nodes)}").setEnabled(False)
        menu.addSeparator()
        
        # 批量启动未分组节点
        stopped_count = sum(1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get('status') == 'stopped')
        if stopped_count > 0:
            start_ungrouped_action = menu.addAction(f"▶️ 启动所有未分组节点 ({stopped_count}个)")
            start_ungrouped_action.triggered.connect(self.start_ungrouped_nodes)
        
        # 批量停止未分组节点
        running_count = sum(1 for n in ungrouped_nodes if self.nodes_data.get(n, {}).get('status') == 'running')
        if running_count > 0:
            stop_ungrouped_action = menu.addAction(f"⏹️ 停止所有未分组节点 ({running_count}个)")
            stop_ungrouped_action.triggered.connect(self.stop_ungrouped_nodes)
        
        menu.addSeparator()
        
        # 创建新组并移动
        create_and_move_action = menu.addAction("➕ 创建新组并移动这些节点")
        create_and_move_action.triggered.connect(lambda: self.create_group_from_ungrouped(ungrouped_nodes))
    
    def add_node_to_canvas(self, node_name):
        """添加节点到画布"""
        if self.parent_window:
            self.parent_window.canvas.add_node_to_canvas(node_name)

    def open_node_folder(self, node_name):
        """打开节点文件夹"""
        if node_name not in self.nodes_data:
            return
        
        node_path = self.nodes_data[node_name]['path']
        
        # 使用系统默认文件管理器打开
        import platform
        
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(['explorer', node_path])
        elif system == "Darwin":  # macOS
            subprocess.Popen(['open', node_path])
        else:  # Linux
            subprocess.Popen(['xdg-open', node_path])
            
    def view_node_log(self, node_name):
        """查看节点日志"""
        if node_name not in self.nodes_data:
            return
        
        node_path = self.nodes_data[node_name]['path']
        log_file = os.path.join(node_path, "logs", "listener.log")
        
        if not os.path.exists(log_file):
            QMessageBox.information(self, "提示", "日志文件不存在")
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
            QMessageBox.critical(self, "错误", f"读取日志失败: {str(e)}")
            
    def edit_node_config(self, node_name):
        """编辑节点配置"""
        if node_name not in self.nodes_data:
            return
        
        node_info = self.nodes_data[node_name]
        config = node_info['config']
        node_path = node_info['path']
        
        # 打开配置对话框
        from ui.property_panel import NodeConfigDialog
        dialog = NodeConfigDialog(node_name, config, node_path, self.parent_window)
        dialog.exec()

    def delete_node(self, node_name):
        """删除节点"""
        if node_name not in self.nodes_data:
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
                    print(f"停止节点时出错: {e}")
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
            
            # 从画布中移除
            if self.parent_window:
                self.parent_window.canvas.remove_node_from_canvas(node_name)
            
            # 刷新列表
            self.update_node_list(self.nodes_data)
            
            QMessageBox.information(self, "成功", f"节点 {node_name} 已删除")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"删除节点失败: {str(e)}")
    
    def rename_node(self, old_name):
        """重命名节点"""
        if old_name not in self.nodes_data:
            return
        
        # 输入新名称
        new_name, ok = QInputDialog.getText(
            self, "重命名节点",
            f"请输入新的节点名称:",
            text=old_name
        )
        
        if not ok or not new_name:
            return
        
        # 验证名称格式
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', new_name):
            QMessageBox.warning(self, "警告", "节点名称只能包含字母、数字、下划线和连字符")
            return
        
        # 检查名称是否已存在
        if new_name != old_name and new_name in self.nodes_data:
            QMessageBox.warning(self, "警告", f"节点名称 '{new_name}' 已存在")
            return
        
        try:
            node_info = self.nodes_data[old_name]
            old_path = node_info['path']
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            
            # 1. 重命名文件夹
            if os.path.exists(new_path):
                QMessageBox.warning(self, "警告", f"文件夹 '{new_name}' 已存在")
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

            QMessageBox.information(self, "成功", f"节点已重命名为: {new_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"重命名失败: {str(e)}")
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
            self, "创建节点组",
            "请输入组名称:"
        )
        
        if not ok or not group_name:
            return
        
        # 选择颜色
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor("#4A90E2"), self, "选择组颜色")
        
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
            if self.group_manager.remove_nodes_from_group(current_group, [node_name]):
                self.update_node_list(self.nodes_data)
                if self.parent_window:
                    self.parent_window.show_toast(f"已将 {node_name} 从组 {current_group} 移除", "success")
    
    def rename_group(self, group_name):
        """重命名组"""
        new_name, ok = QInputDialog.getText(
            self, "重命名组",
            f"请输入新的组名称:",
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
                        print(f"启动节点 {node_name} 失败: {e}")
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
                        print(f"停止节点 {node_name} 失败: {e}")
        
        if self.parent_window:
            self.parent_window.show_toast(f"已停止 {success_count} 个节点", "success")
    
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
                    print(f"启动节点 {node_name} 失败: {e}")
        
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
                    print(f"停止节点 {node_name} 失败: {e}")
        
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
                    print(f"启动节点 {node_name} 失败: {e}")
        
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
                    print(f"停止节点 {node_name} 失败: {e}")
        
        if self.parent_window:
            self.parent_window.show_toast(f"已停止 {success_count} 个未分组节点", "success")
    
    def create_group_from_ungrouped(self, ungrouped_nodes):
        """从未分组节点创建新组"""
        if not ungrouped_nodes:
            if self.parent_window:
                self.parent_window.show_toast("没有未分组的节点", "warning")
            return
        
        group_name, ok = QInputDialog.getText(
            self, "创建新组",
            f"将为 {len(ungrouped_nodes)} 个未分组节点创建新组\n请输入组名称:"
        )
        
        if not ok or not group_name:
            return
        
        # 选择颜色
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor("#7ED321"), self, "选择组颜色")
        
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
    
    # ==================== 鼠标拖动支持 ====================
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 开始拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 拖动窗口"""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, 'drag_position'):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def set_project_path(self, project_path):
        """设置项目路径并加载节点组配置"""
        self.group_manager.set_project_path(project_path)


# 需要导入os
import os
