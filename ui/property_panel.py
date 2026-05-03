"""
属性配置面板 - 右侧面板，显示和编辑节点配置
"""
import os
import json
import subprocess
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit, 
    QPushButton, QTextEdit, QGroupBox, QScrollArea, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QDialogButtonBox, QColorDialog, QSlider, QSpinBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


class NodeConfigDialog(QDialog):
    """节点配置对话框（双击节点打开）"""
    
    def __init__(self, node_name, config, node_path, parent_window=None):
        super().__init__(parent_window)
        self.node_name = node_name
        self.config = config
        self.node_path = node_path
        self.parent_window = parent_window
        
        self.setWindowTitle(f"节点配置: {node_name}")
        self.setGeometry(200, 200, 600, 700)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # 节点名称标题
        title = QLabel(f"节点: {self.node_name}")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        content_layout.addWidget(title)
        
        # 基本配置
        form_group = QGroupBox("基本配置")
        form_layout = QFormLayout(form_group)
        
        # node_name（只读）
        node_name_edit = QLineEdit(self.config.get('node_name', ''))
        node_name_edit.setReadOnly(True)
        form_layout.addRow("节点名称:", node_name_edit)
        
        # listen_upper_file
        self.listen_file_edit = QLineEdit(self.config.get('listen_upper_file', ''))
        form_layout.addRow("监听文件:", self.listen_file_edit)
        
        # output_file（只读）
        output_file_edit = QLineEdit(self.config.get('output_file', './output.json'))
        output_file_edit.setReadOnly(True)
        form_layout.addRow("输出文件:", output_file_edit)
        
        # output_type
        self.output_type_edit = QLineEdit(self.config.get('output_type', ''))
        form_layout.addRow("输出类型:", self.output_type_edit)
        
        content_layout.addWidget(form_group)
        
        # Filter配置
        filter_group = QGroupBox("Filter注意力规则")
        filter_layout = QVBoxLayout(filter_group)
        
        self.filter_table = QTableWidget()
        self.filter_table.setColumnCount(2)
        self.filter_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.filter_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        filter_data = self.config.get('filter', {})
        self.filter_table.setRowCount(len(filter_data))
        for i, (key, value) in enumerate(filter_data.items()):
            self.filter_table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.filter_table.setItem(i, 1, QTableWidgetItem(str(value)))
        
        filter_layout.addWidget(self.filter_table)
        
        # 添加/删除按钮
        btn_layout = QVBoxLayout()
        add_btn = QPushButton("添加规则")
        add_btn.clicked.connect(self.add_filter_rule)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(self.delete_filter_rule)
        btn_layout.addWidget(del_btn)
        
        filter_layout.addLayout(btn_layout)
        
        content_layout.addWidget(filter_group)
        
        # Output.json 内容显示
        output_group = QGroupBox("📄 输出数据 (output.json)")
        output_layout = QVBoxLayout(output_group)
        
        # 创建可编辑的文本编辑器显示/编辑 output.json 内容
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(False)  # 设置为可编辑
        self.output_text.setFont(QFont("Consolas", 9))
        self.output_text.setMaximumHeight(200)
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                selection-background-color: #264f78;
            }
        """)
        
        # 加载并显示 output.json 内容
        self.load_output_json()
        
        output_layout.addWidget(self.output_text)
        
        # 按钮布局
        output_btn_layout = QVBoxLayout()
        
        # 刷新按钮
        refresh_output_btn = QPushButton("🔄 刷新输出数据")
        refresh_output_btn.setStyleSheet("background-color: #9C27B0; color: white; padding: 5px;")
        refresh_output_btn.clicked.connect(self.load_output_json)
        output_btn_layout.addWidget(refresh_output_btn)
        
        # 保存按钮
        save_output_btn = QPushButton("💾 保存修改")
        save_output_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px;")
        save_output_btn.clicked.connect(self.save_output_json)
        output_btn_layout.addWidget(save_output_btn)
        
        output_layout.addLayout(output_btn_layout)
        
        content_layout.addWidget(output_group)
        
        # 节点控制按钮组
        control_group = QGroupBox("节点控制")
        control_layout = QVBoxLayout(control_group)
        
        # 启动按钮
        start_btn = QPushButton("▶ 启动节点")
        start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        start_btn.clicked.connect(self.start_node)
        control_layout.addWidget(start_btn)
        
        # 停止按钮
        stop_btn = QPushButton("⏹ 停止节点")
        stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px; font-weight: bold;")
        stop_btn.clicked.connect(self.stop_node)
        control_layout.addWidget(stop_btn)
        
        # 打开文件夹按钮
        open_folder_btn = QPushButton("📁 打开节点文件夹")
        open_folder_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 8px;")
        open_folder_btn.clicked.connect(self.open_node_folder)
        control_layout.addWidget(open_folder_btn)
        
        # 打开命令行按钮
        open_terminal_btn = QPushButton("💻 打开命令行（虚拟环境）")
        open_terminal_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 8px;")
        open_terminal_btn.clicked.connect(self.open_terminal)
        control_layout.addWidget(open_terminal_btn)
        
        content_layout.addWidget(control_group)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存配置")
        save_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; font-weight: bold;")
        save_btn.clicked.connect(self.save_config)
        content_layout.addWidget(save_btn)
        
        # 关闭按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def add_filter_rule(self):
        """添加filter规则"""
        row = self.filter_table.rowCount()
        self.filter_table.insertRow(row)
        self.filter_table.setItem(row, 0, QTableWidgetItem(""))
        self.filter_table.setItem(row, 1, QTableWidgetItem(""))
        
    def delete_filter_rule(self):
        """删除选中的filter规则"""
        current_row = self.filter_table.currentRow()
        if current_row >= 0:
            self.filter_table.removeRow(current_row)
    
    def start_node(self):
        """启动节点"""
        if not self.parent_window:
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if node_data and node_data.get('status') == 'running':
            QMessageBox.information(self, "提示", "节点已在运行中")
            return
        
        try:
            # 使用主窗口的启动方法
            self.parent_window.start_selected_node_by_name(self.node_name)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动节点失败: {str(e)}")
    
    def stop_node(self):
        """停止节点"""
        if not self.parent_window:
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if not node_data or node_data.get('status') == 'stopped':
            QMessageBox.information(self, "提示", "节点未在运行")
            return
        
        try:
            # 使用主窗口的停止方法
            self.parent_window.stop_selected_node_by_name(self.node_name)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止节点失败: {str(e)}")
    
    def open_node_folder(self):
        """打开节点文件夹"""
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.Popen(['explorer', self.node_path])
            elif system == "Darwin":  # macOS
                subprocess.Popen(['open', self.node_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', self.node_path])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件夹失败: {str(e)}")
    
    def open_terminal(self):
        """打开命令行并激活虚拟环境"""
        try:
            # 检查虚拟环境是否存在
            if platform.system() == "Windows":
                activate_script = os.path.join(self.node_path, "venv", "Scripts", "activate.bat")
            else:
                activate_script = os.path.join(self.node_path, "venv", "bin", "activate")
            
            if not os.path.exists(activate_script):
                QMessageBox.warning(self, "警告", f"虚拟环境不存在:\n{activate_script}")
                return
            
            # 打开命令行
            system = platform.system()
            if system == "Windows":
                cmd = f'start cmd /k "cd /d {self.node_path} && call venv\\Scripts\\activate.bat && echo ✅ 已激活虚拟环境 && echo 📍 当前目录: %CD% && echo 🐍 Python路径: where python"'
                subprocess.Popen(cmd, shell=True)
            elif system == "Darwin":  # macOS
                script = f'''tell application "Terminal"
                    do script "cd '{self.node_path}' && source venv/bin/activate && echo '✅ 已激活虚拟环境' && echo '📍 当前目录: $PWD' && echo '🐍 Python路径: $(which python)'"
                end tell'''
                subprocess.Popen(['osascript', '-e', script])
            else:  # Linux
                # 尝试常见的终端模拟器
                terminals = ['gnome-terminal', 'konsole', 'xterm']
                for terminal in terminals:
                    try:
                        cmd = f"cd '{self.node_path}' && source venv/bin/activate && echo '✅ 已激活虚拟环境' && exec bash"
                        subprocess.Popen([terminal, '-e', f'bash -c "{cmd}"'])
                        break
                    except:
                        continue
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开命令行失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def load_output_json(self):
        """加载并显示 output.json 的内容"""
        try:
            output_path = os.path.join(self.node_path, "output.json")
            
            if not os.path.exists(output_path):
                self.output_text.setPlainText("⚠️ output.json 文件不存在\n\n提示：节点启动并处理数据后会自动生成此文件")
                return
            
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                self.output_text.setPlainText("📭 output.json 文件为空\n\n提示：节点尚未产生输出数据")
                return
            
            # 尝试格式化 JSON
            try:
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                self.output_text.setPlainText(formatted)
            except json.JSONDecodeError:
                # 如果不是有效的 JSON，直接显示原始内容
                self.output_text.setPlainText(content)
                
        except Exception as e:
            self.output_text.setPlainText(f"❌ 读取 output.json 失败:\n{str(e)}")
    
    def save_output_json(self):
        """保存编辑后的 output.json 内容"""
        try:
            output_path = os.path.join(self.node_path, "output.json")
            content = self.output_text.toPlainText().strip()
            
            # 验证 JSON 格式
            try:
                data = json.loads(content)
                # 格式化后保存
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(formatted)
                QMessageBox.information(self, "成功", "✅ output.json 已保存")
            except json.JSONDecodeError as e:
                reply = QMessageBox.question(
                    self, 
                    "JSON 格式错误",
                    f"⚠️ 当前内容不是有效的 JSON 格式：\n\n{str(e)}\n\n是否仍要保存？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    QMessageBox.information(self, "成功", "✅ 已保存（未格式化）")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"❌ 保存 output.json 失败:\n{str(e)}")
            
    def save_config(self):
        """保存配置"""
        try:
            config_path = os.path.join(self.node_path, "config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新配置
            config['listen_upper_file'] = self.listen_file_edit.text()
            config['output_type'] = self.output_type_edit.text()
            
            # 更新filter
            filter_data = {}
            for row in range(self.filter_table.rowCount()):
                key_item = self.filter_table.item(row, 0)
                value_item = self.filter_table.item(row, 1)
                if key_item and value_item:
                    key = key_item.text().strip()
                    value = value_item.text().strip()
                    if key:
                        filter_data[key] = value
            
            config['filter'] = filter_data
            
            # 写入文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 更新内存中的数据
            if self.parent_window and self.node_name in self.parent_window.nodes_data:
                self.parent_window.nodes_data[self.node_name]['config'] = config
                
                # 同步更新画布上的节点显示
                if hasattr(self.parent_window, 'canvas'):
                    self.parent_window.canvas.sync_node_display(self.node_name)
            
            QMessageBox.information(self, "成功", "配置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")

class PropertyPanel(QWidget):
    """属性配置面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.current_node_name = None
        self.current_node_path = None
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title_label = QLabel("属性配置")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 内容部件
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(10)
        
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
        
        # 默认提示信息
        self.show_default_info()
        
    def show_default_info(self):
        """显示默认信息"""
        self.clear_content()
        
        info_label = QLabel("未选中任何元素")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: gray; padding: 20px;")
        self.content_layout.addWidget(info_label)
        
        if self.parent_window and self.parent_window.current_project_path:
            project_info = QLabel(
                f"项目路径: {self.parent_window.current_project_path}\n"
                f"节点总数: {len(self.parent_window.nodes_data)}\n"
                f"运行中: {sum(1 for n in self.parent_window.nodes_data.values() if n['status'] == 'running')}"
            )
            project_info.setStyleSheet("padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
            self.content_layout.addWidget(project_info)
            
    def clear_content(self):
        """清空内容"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
    def load_node_config(self, node_name, config, node_path):
        """加载节点配置"""
        self.clear_content()
        self.current_node_name = node_name
        self.current_node_path = node_path
        
        # 节点名称标题
        title = QLabel(f"节点: {node_name}")
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.content_layout.addWidget(title)
        
        # 配置表单
        form_group = QGroupBox("基本配置")
        form_layout = QFormLayout(form_group)
        
        # node_name（只读）
        node_name_edit = QLineEdit(config.get('node_name', ''))
        node_name_edit.setReadOnly(True)
        form_layout.addRow("节点名称:", node_name_edit)
        
        # listen_upper_file
        self.listen_file_edit = QLineEdit(config.get('listen_upper_file', ''))
        form_layout.addRow("监听文件:", self.listen_file_edit)
        
        # output_file（只读）
        output_file_edit = QLineEdit(config.get('output_file', './output.json'))
        output_file_edit.setReadOnly(True)
        form_layout.addRow("输出文件:", output_file_edit)
        
        # output_type
        self.output_type_edit = QLineEdit(config.get('output_type', ''))
        form_layout.addRow("输出类型:", self.output_type_edit)
        
        self.content_layout.addWidget(form_group)
        
        # Filter配置
        filter_group = QGroupBox("Filter注意力规则")
        filter_layout = QVBoxLayout(filter_group)
        
        # 使用表格显示filter
        self.filter_table = QTableWidget()
        self.filter_table.setColumnCount(2)
        self.filter_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.filter_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # 填充filter数据
        filter_data = config.get('filter', {})
        self.filter_table.setRowCount(len(filter_data))
        for i, (key, value) in enumerate(filter_data.items()):
            self.filter_table.setItem(i, 0, QTableWidgetItem(str(key)))
            self.filter_table.setItem(i, 1, QTableWidgetItem(str(value)))
        
        filter_layout.addWidget(self.filter_table)
        
        # 添加/删除按钮
        btn_layout = QVBoxLayout()
        add_btn = QPushButton("添加规则")
        add_btn.clicked.connect(self.add_filter_rule)
        btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton("删除选中")
        del_btn.clicked.connect(self.delete_filter_rule)
        btn_layout.addWidget(del_btn)
        
        filter_layout.addLayout(btn_layout)
        
        self.content_layout.addWidget(filter_group)
        
        # 节点控制按钮组
        control_group = QGroupBox("节点控制")
        control_layout = QVBoxLayout(control_group)
        
        btn_row_layout = QVBoxLayout()
        
        # 启动按钮
        start_btn = QPushButton("▶ 启动节点")
        start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px; font-weight: bold;")
        start_btn.clicked.connect(self.start_node)
        btn_row_layout.addWidget(start_btn)
        
        # 停止按钮
        stop_btn = QPushButton("⏹ 停止节点")
        stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px; font-weight: bold;")
        stop_btn.clicked.connect(self.stop_node)
        btn_row_layout.addWidget(stop_btn)
        
        control_layout.addLayout(btn_row_layout)
        self.content_layout.addWidget(control_group)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存配置")
        save_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 10px; font-weight: bold;")
        save_btn.clicked.connect(self.save_config)
        self.content_layout.addWidget(save_btn)
        
        # 添加弹性空间
        self.content_layout.addStretch()
        
    def start_node(self):
        """启动节点"""
        if not self.current_node_name or not self.current_node_path:
            QMessageBox.warning(self, "警告", "请先选择一个节点")
            return
        
        if not self.parent_window:
            return
        
        # 检查节点是否已在运行
        node_data = self.parent_window.nodes_data.get(self.current_node_name)
        if node_data and node_data.get('process'):
            QMessageBox.information(self, "提示", "节点已在运行中")
            return
        
        try:
            import subprocess
            import sys
            
            # 确定Python解释器路径
            if sys.platform == "win32":
                py_path = os.path.join(self.current_node_path, "venv", "Scripts", "python.exe")
            else:
                py_path = os.path.join(self.current_node_path, "venv", "bin", "python")
            
            # 启动节点进程
            main_py = os.path.join(self.current_node_path, "main.py")
            process = subprocess.Popen(
                [py_path, main_py],
                cwd=self.current_node_path,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
            )
            
            # 更新状态
            self.parent_window.update_node_status(self.current_node_name, 'running')
            
            QMessageBox.information(self, "成功", f"节点 '{self.current_node_name}' 已启动")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动节点失败: {str(e)}")
            
    def stop_node(self):
        """停止节点"""
        if not self.current_node_name or not self.current_node_path:
            QMessageBox.warning(self, "警告", "请先选择一个节点")
            return
        
        if not self.parent_window:
            return
        
        # 检查节点是否在运行
        node_data = self.parent_window.nodes_data.get(self.current_node_name)
        if not node_data or not node_data.get('process'):
            QMessageBox.information(self, "提示", "节点未在运行")
            return
        
        try:
            # 终止进程
            process = node_data['process']
            if process.poll() is None:  # 进程仍在运行
                process.terminate()
                process.wait(timeout=5)
            
            # 更新状态
            self.parent_window.update_node_status(self.current_node_name, 'stopped')
            
            QMessageBox.information(self, "成功", f"节点 '{self.current_node_name}' 已停止")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止节点失败: {str(e)}")

    def add_filter_rule(self):
        """添加filter规则"""
        row = self.filter_table.rowCount()
        self.filter_table.insertRow(row)
        self.filter_table.setItem(row, 0, QTableWidgetItem(""))
        self.filter_table.setItem(row, 1, QTableWidgetItem(""))
        
    def delete_filter_rule(self):
        """删除选中的filter规则"""
        current_row = self.filter_table.currentRow()
        if current_row >= 0:
            self.filter_table.removeRow(current_row)
            
    def save_config(self):
        """保存配置"""
        if not self.current_node_name or not self.current_node_path:
            return
        
        try:
            # 读取当前配置
            config_path = os.path.join(self.current_node_path, "config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新配置
            config['listen_upper_file'] = self.listen_file_edit.text()
            config['output_type'] = self.output_type_edit.text()
            
            # 更新filter
            filter_data = {}
            for row in range(self.filter_table.rowCount()):
                key_item = self.filter_table.item(row, 0)
                value_item = self.filter_table.item(row, 1)
                if key_item and value_item:
                    key = key_item.text().strip()
                    value = value_item.text().strip()
                    if key:  # 只保存非空key
                        filter_data[key] = value
            
            config['filter'] = filter_data
            
            # 写入文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 更新内存中的数据
            if self.parent_window and self.current_node_name in self.parent_window.nodes_data:
                self.parent_window.nodes_data[self.current_node_name]['config'] = config
                
                # 同步更新画布上的节点显示
                if hasattr(self.parent_window, 'canvas'):
                    self.parent_window.canvas.sync_node_display(self.current_node_name)
            
            QMessageBox.information(self, "成功", "配置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")
            
    def load_connection_info(self, source_name, target_name, source_output_path):
        """加载连线配置信息"""
        self.clear_content()
        self.current_node_name = None
        self.current_node_path = None
        
        # 标题
        title = QLabel(f"连线配置")
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.content_layout.addWidget(title)
        
        # 连线信息
        info_group = QGroupBox("连线详情")
        info_layout = QFormLayout(info_group)
        
        upstream_label = QLabel(source_name)
        info_layout.addRow("上游节点:", upstream_label)
        
        downstream_label = QLabel(target_name)
        info_layout.addRow("下游节点:", downstream_label)
        
        path_label = QLabel(source_output_path)
        path_label.setWordWrap(True)
        info_layout.addRow("上游输出路径:", path_label)
        
        self.content_layout.addWidget(info_group)
        
        # 说明文本
        note = QLabel(
            "说明:\n"
            "- 上游节点的 output.json 路径已自动配置到下游节点\n"
            "- 删除连线将清空下游节点的 listen_upper_file 配置"
        )
        note.setStyleSheet("padding: 10px; background-color: #fff3cd; border-radius: 5px;")
        note.setWordWrap(True)
        self.content_layout.addWidget(note)
        
        # 添加弹性空间
        self.content_layout.addStretch()


class ColorSettingsDialog(QDialog):
    """画布和节点颜色设置对话框"""
    
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setWindowTitle("🎨 画布与节点颜色设置")
        self.setGeometry(300, 200, 500, 600)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("🎨 自定义画布和节点外观")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # ===== 画布背景色设置 =====
        canvas_group = QGroupBox("🖼️ 画布背景")
        canvas_layout = QFormLayout(canvas_group)
        
        # 画布背景色
        self.canvas_color_btn = QPushButton("选择颜色")
        self.canvas_color_btn.setStyleSheet(f"background-color: {self.canvas.canvas_bg_color}; min-height: 30px;")
        self.canvas_color_btn.clicked.connect(lambda: self.choose_color('canvas'))
        canvas_layout.addRow("背景颜色:", self.canvas_color_btn)
        
        # 网格线颜色
        self.grid_color_btn = QPushButton("选择颜色")
        self.grid_color_btn.setStyleSheet(f"background-color: {self.canvas.grid_color}; min-height: 30px;")
        self.grid_color_btn.clicked.connect(lambda: self.choose_color('grid'))
        canvas_layout.addRow("网格线颜色:", self.grid_color_btn)
        
        # 网格线透明度
        self.grid_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.grid_opacity_slider.setRange(0, 100)
        self.grid_opacity_slider.setValue(int(self.canvas.grid_opacity * 100))
        self.grid_opacity_slider.valueChanged.connect(self.update_grid_opacity_label)
        self.grid_opacity_label = QLabel(f"{int(self.canvas.grid_opacity * 100)}%")
        grid_opacity_layout = QVBoxLayout()
        grid_opacity_layout.addWidget(self.grid_opacity_slider)
        grid_opacity_layout.addWidget(self.grid_opacity_label)
        canvas_layout.addRow("网格线透明度:", grid_opacity_layout)
        
        content_layout.addWidget(canvas_group)
        
        # ===== 节点样式设置 =====
        node_group = QGroupBox("📦 节点样式")
        node_layout = QFormLayout(node_group)
        
        # 节点背景色
        self.node_bg_btn = QPushButton("选择颜色")
        self.node_bg_btn.setStyleSheet(f"background-color: {self.canvas.node_bg_color}; min-height: 30px;")
        self.node_bg_btn.clicked.connect(lambda: self.choose_color('node_bg'))
        node_layout.addRow("节点背景:", self.node_bg_btn)
        
        # 节点边框色
        self.node_border_btn = QPushButton("选择颜色")
        self.node_border_btn.setStyleSheet(f"background-color: {self.canvas.node_border_color}; min-height: 30px;")
        self.node_border_btn.clicked.connect(lambda: self.choose_color('node_border'))
        node_layout.addRow("节点边框:", self.node_border_btn)
        
        # 节点文字颜色
        self.node_text_btn = QPushButton("选择颜色")
        self.node_text_btn.setStyleSheet(f"background-color: {self.canvas.node_text_color}; min-height: 30px;")
        self.node_text_btn.clicked.connect(lambda: self.choose_color('node_text'))
        node_layout.addRow("节点文字:", self.node_text_btn)
        
        # 选中节点边框色
        self.node_selected_btn = QPushButton("选择颜色")
        self.node_selected_btn.setStyleSheet(f"background-color: {self.canvas.node_selected_color}; min-height: 30px;")
        self.node_selected_btn.clicked.connect(lambda: self.choose_color('node_selected'))
        node_layout.addRow("选中边框:", self.node_selected_btn)
        
        content_layout.addWidget(node_group)
        
        # ===== 锚点样式设置 =====
        anchor_group = QGroupBox("🔘 锚点样式")
        anchor_layout = QFormLayout(anchor_group)
        
        # 输入锚点颜色
        self.input_anchor_btn = QPushButton("选择颜色")
        self.input_anchor_btn.setStyleSheet(f"background-color: {self.canvas.input_anchor_color}; min-height: 30px;")
        self.input_anchor_btn.clicked.connect(lambda: self.choose_color('input_anchor'))
        anchor_layout.addRow("输入锚点 (IN):", self.input_anchor_btn)
        
        # 输出锚点颜色
        self.output_anchor_btn = QPushButton("选择颜色")
        self.output_anchor_btn.setStyleSheet(f"background-color: {self.canvas.output_anchor_color}; min-height: 30px;")
        self.output_anchor_btn.clicked.connect(lambda: self.choose_color('output_anchor'))
        anchor_layout.addRow("输出锚点 (OUT):", self.output_anchor_btn)
        
        content_layout.addWidget(anchor_group)
        
        # ===== 连线样式设置 =====
        edge_group = QGroupBox("🔗 连线样式")
        edge_layout = QFormLayout(edge_group)
        
        # 连线颜色
        self.edge_color_btn = QPushButton("选择颜色")
        self.edge_color_btn.setStyleSheet(f"background-color: {self.canvas.edge_color}; min-height: 30px;")
        self.edge_color_btn.clicked.connect(lambda: self.choose_color('edge'))
        edge_layout.addRow("连线颜色:", self.edge_color_btn)
        
        # 连线宽度
        self.edge_width_spinbox = QSpinBox()
        self.edge_width_spinbox.setRange(1, 10)
        self.edge_width_spinbox.setValue(self.canvas.edge_width)
        edge_layout.addRow("连线宽度:", self.edge_width_spinbox)
        
        content_layout.addWidget(edge_group)
        
        # ===== 预设主题 =====
        theme_group = QGroupBox("🎭 快速主题")
        theme_layout = QVBoxLayout(theme_group)
        
        theme_btn_layout = QVBoxLayout()
        
        # 浅色主题
        light_theme_btn = QPushButton("☀️ 浅色主题")
        light_theme_btn.clicked.connect(lambda: self.apply_preset_theme('light'))
        theme_btn_layout.addWidget(light_theme_btn)
        
        # 深色主题
        dark_theme_btn = QPushButton("🌙 深色主题")
        dark_theme_btn.clicked.connect(lambda: self.apply_preset_theme('dark'))
        theme_btn_layout.addWidget(dark_theme_btn)
        
        # 蓝色科技主题
        blue_theme_btn = QPushButton("💙 蓝色科技")
        blue_theme_btn.clicked.connect(lambda: self.apply_preset_theme('blue'))
        theme_btn_layout.addWidget(blue_theme_btn)
        
        # 绿色自然主题
        green_theme_btn = QPushButton("💚 绿色自然")
        green_theme_btn.clicked.connect(lambda: self.apply_preset_theme('green'))
        theme_btn_layout.addWidget(green_theme_btn)
        
        theme_layout.addLayout(theme_btn_layout)
        
        content_layout.addWidget(theme_group)
        
        # 按钮区域
        button_layout = QVBoxLayout()
        
        # 应用按钮
        apply_btn = QPushButton("✅ 应用更改")
        apply_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)
        
        # 重置按钮
        reset_btn = QPushButton("🔄 恢复默认")
        reset_btn.setStyleSheet("background-color: #FF9800; color: white; padding: 10px;")
        reset_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(reset_btn)
        
        content_layout.addLayout(button_layout)
        
        # 关闭按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def update_grid_opacity_label(self, value):
        """更新网格线透明度标签"""
        self.grid_opacity_label.setText(f"{value}%")
        
    def choose_color(self, target):
        """选择颜色"""
        from PyQt6.QtWidgets import QColorDialog
        
        # 获取当前颜色
        current_colors = {
            'canvas': self.canvas.canvas_bg_color,
            'grid': self.canvas.grid_color,
            'node_bg': self.canvas.node_bg_color,
            'node_border': self.canvas.node_border_color,
            'node_text': self.canvas.node_text_color,
            'node_selected': self.canvas.node_selected_color,
            'input_anchor': self.canvas.input_anchor_color,
            'output_anchor': self.canvas.output_anchor_color,
            'edge': self.canvas.edge_color
        }
        
        current_color = QColor(current_colors[target])
        new_color = QColorDialog.getColor(current_color, self, "选择颜色")
        
        if new_color.isValid():
            color_hex = new_color.name()
            
            # 更新按钮显示
            btn_map = {
                'canvas': self.canvas_color_btn,
                'grid': self.grid_color_btn,
                'node_bg': self.node_bg_btn,
                'node_border': self.node_border_btn,
                'node_text': self.node_text_btn,
                'node_selected': self.node_selected_btn,
                'input_anchor': self.input_anchor_btn,
                'output_anchor': self.output_anchor_btn,
                'edge': self.edge_color_btn
            }
            
            btn_map[target].setStyleSheet(f"background-color: {color_hex}; min-height: 30px;")
            
            # 临时存储新颜色
            setattr(self, f'temp_{target}_color', color_hex)
            
    def apply_preset_theme(self, theme_name):
        """应用预设主题"""
        themes = {
            'light': {
                'canvas_bg_color': '#ffffff',
                'grid_color': '#e0e0e0',
                'grid_opacity': 0.5,
                'node_bg_color': '#f8f9fa',
                'node_border_color': '#dee2e6',
                'node_text_color': '#333333',
                'node_selected_color': '#2196F3',
                'input_anchor_color': '#4CAF50',
                'output_anchor_color': '#2196F3',
                'edge_color': '#666666',
                'edge_width': 2
            },
            'dark': {
                'canvas_bg_color': '#1e1e1e',
                'grid_color': '#3c3c3c',
                'grid_opacity': 0.3,
                'node_bg_color': '#2d2d2d',
                'node_border_color': '#404040',
                'node_text_color': '#d4d4d4',
                'node_selected_color': '#4FC3F7',
                'input_anchor_color': '#66BB6A',
                'output_anchor_color': '#42A5F5',
                'edge_color': '#888888',
                'edge_width': 2
            },
            'blue': {
                'canvas_bg_color': '#0a1929',
                'grid_color': '#1e3a5f',
                'grid_opacity': 0.4,
                'node_bg_color': '#1a3a5c',
                'node_border_color': '#2e5a7c',
                'node_text_color': '#e0f0ff',
                'node_selected_color': '#00bcd4',
                'input_anchor_color': '#00e676',
                'output_anchor_color': '#00bcd4',
                'edge_color': '#4fc3f7',
                'edge_width': 2
            },
            'green': {
                'canvas_bg_color': '#f1f8e9',
                'grid_color': '#c5e1a5',
                'grid_opacity': 0.5,
                'node_bg_color': '#ffffff',
                'node_border_color': '#aed581',
                'node_text_color': '#33691e',
                'node_selected_color': '#4CAF50',
                'input_anchor_color': '#66BB6A',
                'output_anchor_color': '#8BC34A',
                'edge_color': '#7CB342',
                'edge_width': 2
            }
        }
        
        theme = themes.get(theme_name)
        if theme:
            # 应用主题到临时变量
            for key, value in theme.items():
                setattr(self, f'temp_{key}', value)
                
            # 更新按钮显示
            self.canvas_color_btn.setStyleSheet(f"background-color: {theme['canvas_bg_color']}; min-height: 30px;")
            self.grid_color_btn.setStyleSheet(f"background-color: {theme['grid_color']}; min-height: 30px;")
            self.grid_opacity_slider.setValue(int(theme['grid_opacity'] * 100))
            self.grid_opacity_label.setText(f"{int(theme['grid_opacity'] * 100)}%")
            self.node_bg_btn.setStyleSheet(f"background-color: {theme['node_bg_color']}; min-height: 30px;")
            self.node_border_btn.setStyleSheet(f"background-color: {theme['node_border_color']}; min-height: 30px;")
            self.node_text_btn.setStyleSheet(f"background-color: {theme['node_text_color']}; min-height: 30px;")
            self.node_selected_btn.setStyleSheet(f"background-color: {theme['node_selected_color']}; min-height: 30px;")
            self.input_anchor_btn.setStyleSheet(f"background-color: {theme['input_anchor_color']}; min-height: 30px;")
            self.output_anchor_btn.setStyleSheet(f"background-color: {theme['output_anchor_color']}; min-height: 30px;")
            self.edge_color_btn.setStyleSheet(f"background-color: {theme['edge_color']}; min-height: 30px;")
            self.edge_width_spinbox.setValue(theme['edge_width'])
            
    def apply_settings(self):
        """应用颜色设置"""
        try:
            # 收集所有颜色设置
            settings = {
                'canvas_bg_color': getattr(self, 'temp_canvas_bg_color', self.canvas.canvas_bg_color),
                'grid_color': getattr(self, 'temp_grid_color', self.canvas.grid_color),
                'grid_opacity': self.grid_opacity_slider.value() / 100.0,
                'node_bg_color': getattr(self, 'temp_node_bg_color', self.canvas.node_bg_color),
                'node_border_color': getattr(self, 'temp_node_border_color', self.canvas.node_border_color),
                'node_text_color': getattr(self, 'temp_node_text_color', self.canvas.node_text_color),
                'node_selected_color': getattr(self, 'temp_node_selected_color', self.canvas.node_selected_color),
                'input_anchor_color': getattr(self, 'temp_input_anchor_color', self.canvas.input_anchor_color),
                'output_anchor_color': getattr(self, 'temp_output_anchor_color', self.canvas.output_anchor_color),
                'edge_color': getattr(self, 'temp_edge_color', self.canvas.edge_color),
                'edge_width': self.edge_width_spinbox.value()
            }
            
            # 应用到画布
            self.canvas.apply_color_settings(settings)
            
            QMessageBox.information(self, "成功", "✅ 颜色设置已应用")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"应用设置失败: {str(e)}")
            
    def reset_to_default(self):
        """恢复到默认颜色"""
        default_settings = {
            'canvas_bg_color': '#ffffff',
            'grid_color': '#e0e0e0',
            'grid_opacity': 0.5,
            'node_bg_color': '#f8f9fa',
            'node_border_color': '#dee2e6',
            'node_text_color': '#333333',
            'node_selected_color': '#2196F3',
            'input_anchor_color': '#4CAF50',
            'output_anchor_color': '#2196F3',
            'edge_color': '#666666',
            'edge_width': 2
        }
        
        # 应用默认设置
        for key, value in default_settings.items():
            setattr(self, f'temp_{key}', value)
        
        # 更新UI显示
        self.canvas_color_btn.setStyleSheet(f"background-color: {default_settings['canvas_bg_color']}; min-height: 30px;")
        self.grid_color_btn.setStyleSheet(f"background-color: {default_settings['grid_color']}; min-height: 30px;")
        self.grid_opacity_slider.setValue(int(default_settings['grid_opacity'] * 100))
        self.grid_opacity_label.setText(f"{int(default_settings['grid_opacity'] * 100)}%")
        self.node_bg_btn.setStyleSheet(f"background-color: {default_settings['node_bg_color']}; min-height: 30px;")
        self.node_border_btn.setStyleSheet(f"background-color: {default_settings['node_border_color']}; min-height: 30px;")
        self.node_text_btn.setStyleSheet(f"background-color: {default_settings['node_text_color']}; min-height: 30px;")
        self.node_selected_btn.setStyleSheet(f"background-color: {default_settings['node_selected_color']}; min-height: 30px;")
        self.input_anchor_btn.setStyleSheet(f"background-color: {default_settings['input_anchor_color']}; min-height: 30px;")
        self.output_anchor_btn.setStyleSheet(f"background-color: {default_settings['output_anchor_color']}; min-height: 30px;")
        self.edge_color_btn.setStyleSheet(f"background-color: {default_settings['edge_color']}; min-height: 30px;")
        self.edge_width_spinbox.setValue(default_settings['edge_width'])
        
        QMessageBox.information(self, "提示", "🔄 已恢复默认颜色设置")
