"""
节点列表面板 - 左侧面板，显示项目中的所有节点
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMenu, QMessageBox, QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
import subprocess
import json
import os


class NodeListPanel(QWidget):
    """节点列表面板"""
    
    # 信号
    node_double_clicked = pyqtSignal(str)  # 节点双击信号
    node_right_clicked = pyqtSignal(str, object)  # 节点右键信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.nodes_data = {}
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title_label = QLabel("当前项目节点列表")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 路径显示
        self.path_label = QLabel("未打开项目")
        self.path_label.setStyleSheet("color: gray; font-size: 9px;")
        layout.addWidget(self.path_label)
        
        # 节点列表
        self.node_list = QListWidget()
        self.node_list.itemDoubleClicked.connect(self.on_node_double_clicked)
        self.node_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.node_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.node_list)
        
    def update_node_list(self, nodes_data):
        """更新节点列表"""
        self.nodes_data = nodes_data
        
        # 清空列表
        self.node_list.clear()
        
        # 添加节点
        for node_name, node_info in sorted(nodes_data.items()):
            item = QListWidgetItem(node_name)
            
            # 设置状态指示器
            status = node_info.get('status', 'stopped')
            if status == 'running':
                item.setForeground(QColor("green"))
                item.setText(f"● {node_name}")
            else:
                item.setForeground(QColor("gray"))
                item.setText(f"○ {node_name}")
            
            self.node_list.addItem(item)
        
        # 更新路径显示
        if self.parent_window and self.parent_window.current_project_path:
            self.path_label.setText(f"项目: {self.parent_window.current_project_path}")
        else:
            self.path_label.setText("未打开项目")
            
    def update_node_status(self, node_name, status):
        """更新节点状态"""
        for i in range(self.node_list.count()):
            item = self.node_list.item(i)
            if item.text().endswith(node_name):
                if status == 'running':
                    item.setForeground(QColor("green"))
                    item.setText(f"● {node_name}")
                else:
                    item.setForeground(QColor("gray"))
                    item.setText(f"○ {node_name}")
                break
                
    def get_selected_node(self):
        """获取选中的节点名称"""
        current_item = self.node_list.currentItem()
        if not current_item:
            return None
        
        text = current_item.text()
        # 提取节点名称（去掉状态前缀）
        if text.startswith("● ") or text.startswith("○ "):
            return text[2:]
        return text
        
    def on_node_double_clicked(self, item):
        """节点双击事件 - 打开配置对话框"""
        node_name = self.get_selected_node()
        if node_name and self.parent_window:
            # 获取节点信息
            if node_name in self.parent_window.nodes_data:
                node_info = self.parent_window.nodes_data[node_name]
                config = node_info['config']
                node_path = node_info['path']
                
                # 打开配置对话框
                from ui.property_panel import NodeConfigDialog
                dialog = NodeConfigDialog(node_name, config, node_path, self.parent_window)
                dialog.exec()

    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.node_list.itemAt(position)
        if not item:
            return
        
        node_name = self.get_selected_node()
        if not node_name:
            return
        
        menu = QMenu(self)
        
        # 添加到画布
        add_to_canvas_action = menu.addAction("➕ 添加到画布")
        add_to_canvas_action.triggered.connect(lambda: self.add_node_to_canvas(node_name))
        
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
        
        menu.exec(self.node_list.mapToGlobal(position))
    
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
        import subprocess
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
                        # Windows: 先尝试优雅终止
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
                        # Linux/Mac: 终止整个进程组
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
            
            # 4. 从nodes_data中移除旧键，添加新键
            del self.nodes_data[old_name]
            self.nodes_data[new_name] = node_info
            
            # 5. 更新画布上的节点
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
            
            # 6. 刷新父窗口的节点数据（重新从磁盘加载）
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


# 需要导入os
import os
