"""节点配置对话框"""
import os
import sys
import json
import subprocess
import platform
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QLineEdit, 
    QPushButton, QTextEdit, QGroupBox, QScrollArea, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QColorDialog, QSlider, QSpinBox, QComboBox,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from ui.core.logger import logger
from ui.core.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.utils.file_utils import resolve_and_open_folder
from ui.core.utils.dialog_utils import themed_message

class NodeConfigDialog(FloatingPanel):
    """节点配置对话框（双击节点打开）"""
    
    def __init__(self, node_name, config, node_path, parent_window=None):
        super().__init__(parent_window, title=f"节点配置: {node_name}")
        self.node_name = node_name
        self.config = config
        self.node_path = node_path
        
        self.resize(950, 550)
        self.setMinimumSize(700, 400)
        self._init_ui()
        
    def _init_ui(self):
        """初始化UI"""
        
        # 主水平布局：左侧JSON编辑区 + 右侧控制区
        main_h_layout = QHBoxLayout()
        main_h_layout.setSpacing(10)
        
        # ===== 左侧区域：上下两个JSON编辑器 =====
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # 上半部分：config.json 编辑器
        config_group = QGroupBox(t("k_config_edit"))
        config_layout = QVBoxLayout(config_group)
        
        self.config_text = QTextEdit()
        self.config_text.setReadOnly(False)
        self.config_text.setFont(QFont("Consolas", 10))
        self.config_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                selection-background-color: #264f78;
            }
        """)
        
        # 加载并显示 config.json 内容
        self.load_config_json()
        
        config_layout.addWidget(self.config_text)
        
        # config.json 操作按钮
        config_btn_layout = QHBoxLayout()
        
        refresh_config_btn = QPushButton("刷新配置")
        refresh_config_btn.setStyleSheet("background-color: #555555; color: white; padding: 5px 15px;")
        refresh_config_btn.clicked.connect(self.load_config_json)
        config_btn_layout.addWidget(refresh_config_btn)
        
        save_config_btn = QPushButton("保存配置")
        save_config_btn.setStyleSheet("background-color: #333333; color: white; padding: 5px 15px;")
        save_config_btn.clicked.connect(self.save_config_from_editor)
        config_btn_layout.addWidget(save_config_btn)
        
        config_layout.addLayout(config_btn_layout)
        
        left_layout.addWidget(config_group, 1)  # 上半部分占据更多空间
        
        # 下半部分：logs 日志查看器
        log_group = QGroupBox("节点日志")
        log_layout = QVBoxLayout(log_group)
        
        # 日志文件选择下拉框
        log_file_layout = QHBoxLayout()
        log_file_label = QLabel("日志文件:")
        log_file_layout.addWidget(log_file_label)
        
        self.log_file_combo = QComboBox()
        self.log_file_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.log_file_combo.currentIndexChanged.connect(self.on_log_file_changed)
        log_file_layout.addWidget(self.log_file_combo)
        
        log_layout.addLayout(log_file_layout)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)  # 日志只读
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                selection-background-color: #264f78;
            }
        """)
        
        # 加载并显示日志文件列表
        self.load_log_files()
        
        log_layout.addWidget(self.output_text)
        
        # 日志操作按钮
        log_btn_layout = QHBoxLayout()
        
        refresh_log_btn = QPushButton("刷新日志")
        refresh_log_btn.setStyleSheet("background-color: #555555; color: white; padding: 5px 15px;")
        refresh_log_btn.clicked.connect(self.refresh_log_files)
        log_btn_layout.addWidget(refresh_log_btn)
        
        clear_log_btn = QPushButton("清空日志")
        clear_log_btn.setStyleSheet("background-color: #666666; color: white; padding: 5px 15px;")
        clear_log_btn.clicked.connect(self.clear_current_log)
        log_btn_layout.addWidget(clear_log_btn)
        
        log_layout.addLayout(log_btn_layout)
        
        left_layout.addWidget(log_group, 1)  # 下半部分同样占据空间
        
        main_h_layout.addLayout(left_layout, 2)  # 左侧占2份空间
        
        # ===== 右侧区域：节点控制和工具按钮 =====
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        # 节点信息卡片
        info_group = QGroupBox("节点信息")
        info_layout = QVBoxLayout(info_group)
        
        node_name_label = QLabel(f"名称: {self.node_name}")
        node_name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(node_name_label)
        
        node_path_label = QLabel(f"路径: {self.node_path}")
        node_path_label.setFont(QFont("Arial", 9))
        node_path_label.setWordWrap(True)
        info_layout.addWidget(node_path_label)
        
        right_layout.addWidget(info_group)
        
        # 节点控制按钮组
        control_group = QGroupBox("节点控制")
        control_layout = QVBoxLayout(control_group)
        
        # 启动按钮
        start_btn = QPushButton("启动节点")
        start_btn.setStyleSheet("background-color: #333333; color: white; padding: 12px; font-weight: bold; font-size: 13px;")
        start_btn.clicked.connect(self.start_node)
        control_layout.addWidget(start_btn)
        
        # 停止按钮
        stop_btn = QPushButton("停止节点")
        stop_btn.setStyleSheet("background-color: #555555; color: white; padding: 12px; font-weight: bold; font-size: 13px;")
        stop_btn.clicked.connect(self.stop_node)
        control_layout.addWidget(stop_btn)
        
        control_layout.addSpacing(10)
        
        right_layout.addWidget(control_group)
        
        # 快捷操作按钮组
        quick_group = QGroupBox("快捷操作")
        quick_layout = QVBoxLayout(quick_group)
        
        # 打开文件夹按钮
        open_folder_btn = QPushButton("打开目录")
        open_folder_btn.setStyleSheet("background-color: #666666; color: white; padding: 10px;")
        open_folder_btn.clicked.connect(self.open_node_folder)
        quick_layout.addWidget(open_folder_btn)
        
        # 打开命令行按钮
        open_terminal_btn = QPushButton("打开终端")
        open_terminal_btn.setStyleSheet("background-color: #666666; color: white; padding: 10px;")
        open_terminal_btn.clicked.connect(self.open_terminal)
        quick_layout.addWidget(open_terminal_btn)
        
        # 打开 VSCode 工作区按钮
        open_vscode_btn = QPushButton("打开VSCode")
        open_vscode_btn.setStyleSheet("background-color: #666666; color: white; padding: 10px;")
        open_vscode_btn.clicked.connect(self.open_vscode_workspace)
        quick_layout.addWidget(open_vscode_btn)
        
        right_layout.addWidget(quick_group)
        
        right_layout.addStretch()  # 底部弹性空间
        
        main_h_layout.addLayout(right_layout, 1)  # 右侧占1份空间
        
        self.content_layout.addLayout(main_h_layout)
    
    def start_node(self):
        """启动节点"""
        if not self.parent_window:
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if node_data and node_data.get('status') == 'running':
            themed_message(self, t("k_title_info"), t("k_node_already_running"), "info")
            return
        
        try:
            # 使用主窗口的启动方法
            self.parent_window.start_selected_node_by_name(self.node_name)
            self.close()
        except Exception as e:
            themed_message(self, t("k_title_error"), f"启动节点失败: {str(e)}", "error")
    
    def stop_node(self):
        """停止节点"""
        if not self.parent_window:
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if not node_data or node_data.get('status') == 'stopped':
            themed_message(self, t("k_title_info"), t("k_node_not_running"), "info")
            return
        
        try:
            # 使用主窗口的停止方法
            self.parent_window.stop_selected_node_by_name(self.node_name)
        except Exception as e:
            themed_message(self, t("k_title_error"), f"停止节点失败: {str(e)}", "error")
    
    def open_node_folder(self):
        """打开节点文件夹"""
        from ui.core.utils.file_utils import resolve_and_open_folder
        resolve_and_open_folder(
            self.node_path,
            self.node_name,
            parent_window=self.parent_window,
            dialog_parent=self
        )
    
    def _check_vscode_installed(self):
        """检测 VSCode 是否已安装（通过 code 命令）"""
        try:
            system = platform.system()
            if system == "Windows":
                # Windows: 使用 where 命令检查
                result = subprocess.run(['where', 'code'], 
                                      capture_output=True, 
                                      timeout=3)
                return result.returncode == 0
            else:
                # macOS/Linux: 使用 which 命令检查
                result = subprocess.run(['which', 'code'], 
                                      capture_output=True, 
                                      timeout=3)
                return result.returncode == 0
        except Exception:
            return False

    def open_vscode_workspace(self):
        """打开为 VSCode 工作区"""
        try:
            # 容错：检查文件夹是否存在
            if not os.path.exists(self.node_path) or not os.path.isdir(self.node_path):
                themed_message(self, t("k_title_warning"), f"节点文件夹不存在:\n{self.node_path}", "warning")
                return
            
            # 预检测 VSCode 是否安装
            vscode_installed = self._check_vscode_installed()
            if not vscode_installed:
                reply = themed_message(self, "VSCode 未检测到", "⚠️ 未检测到 VSCode (code 命令)\n\n"
                    "是否仍要创建工作区文件？\n\n"
                    "您可以稍后手动用 VSCode 打开该文件。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No, "question")
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # 生成 .code-workspace 文件路径
            workspace_file = os.path.join(self.node_path, f"{self.node_name}.code-workspace")
            
            # 创建标准的 VSCode 工作区配置（使用相对路径）
            workspace_config = {
                "folders": [
                    {
                        "path": "."
                    }
                ],
                "settings": {
                    "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe" if platform.system() == "Windows" else "${workspaceFolder}/venv/bin/python",
                    "files.exclude": {
                        "**/__pycache__": True,
                        "**/*.pyc": True
                    }
                }
            }
            
            # 写入工作区配置文件
            with open(workspace_file, 'w', encoding='utf-8') as f:
                json.dump(workspace_config, f, indent=2, ensure_ascii=False)
            
            # 如果 VSCode 已安装，尝试自动打开
            if vscode_installed:
                system = platform.system()
                try:
                    if system == "Windows":
                        subprocess.Popen(['code', workspace_file], shell=True)
                    elif system == "Darwin":  # macOS
                        subprocess.Popen(['code', workspace_file])
                    else:  # Linux
                        subprocess.Popen(['code', workspace_file])
                    
                    themed_message(self, t("k_title_success"), f"✅ 已创建 VSCode 工作区并自动打开\n\n"
                        f"工作区文件：{workspace_file}\n"
                        f"使用相对路径配置，可安全迁移项目", "info")
                except Exception as e:
                    themed_message(self, t("k_title_workspace_created"), f"✅ VSCode 工作区文件已创建\n\n"
                        f"工作区文件：{workspace_file}\n\n"
                        f"⚠️ 自动打开失败：{str(e)}\n\n"
                        f"请手动用 VSCode 打开该文件", "info")
            else:
                themed_message(self, t("k_title_workspace_created"), f"✅ VSCode 工作区文件已创建\n\n"
                    f"工作区文件：{workspace_file}\n\n"
                    f"💡 提示：安装 VSCode 并添加 'code' 命令到 PATH 后，\n"
                    f"可以双击此文件直接用 VSCode 打开", "info")
            
        except Exception as e:
            themed_message(self, t("k_title_error"), f"创建 VSCode 工作区失败: {str(e)}", "error")
            import traceback
            traceback.print_exc()
    
    def open_terminal(self):
        """打开命令行并激活虚拟环境"""
        try:
            # 检查虚拟环境是否存在
            if platform.system() == "Windows":
                activate_script = os.path.join(self.node_path, "venv", "Scripts", "activate.bat")
            else:
                activate_script = os.path.join(self.node_path, "venv", "bin", "activate")
            
            if not os.path.exists(activate_script):
                themed_message(self, t("k_title_warning"), f"虚拟环境不存在:\n{activate_script}", "warning")
                return
            
            # 打开命令行
            system = platform.system()
            if system == "Windows":
                cmd = f'start cmd /k "cd /d {self.node_path} && call venv\\Scripts\\activate.bat && echo 已激活虚拟环境 && echo 当前目录: %CD% && echo Python路径: where python"'
                subprocess.Popen(cmd, shell=True)
            elif system == "Darwin":  # macOS
                script = f'''tell application "Terminal"
                    do script "cd '{self.node_path}' && source venv/bin/activate && echo '已激活虚拟环境' && echo '当前目录: $PWD' && echo 'Python路径: $(which python)'"
                end tell'''
                subprocess.Popen(['osascript', '-e', script])
            else:  # Linux
                # 尝试常见的终端模拟器
                terminals = ['gnome-terminal', 'konsole', 'xterm']
                for terminal in terminals:
                    try:
                        cmd = f"cd '{self.node_path}' && source venv/bin/activate && echo '已激活虚拟环境' && exec bash"
                        subprocess.Popen([terminal, '-e', f'bash -c "{cmd}"'])
                        break
                    except:
                        continue
        except Exception as e:
            themed_message(self, t("k_title_error"), f"打开命令行失败: {str(e)}", "error")
            import traceback
            traceback.print_exc()
    
    def load_config_json(self):
        """加载并显示 config.json 的内容"""
        try:
            config_path = os.path.join(self.node_path, "config.json")
            
            if not os.path.exists(config_path):
                self.config_text.setPlainText("⚠️ config.json 文件不存在")
                return
            
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                self.config_text.setPlainText("{}")
                return
            
            # 尝试格式化 JSON
            try:
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                self.config_text.setPlainText(formatted)
            except json.JSONDecodeError:
                # 如果不是有效的 JSON，直接显示原始内容
                self.config_text.setPlainText(content)
                
        except Exception as e:
            self.config_text.setPlainText(f"❌ 读取 config.json 失败:\n{str(e)}")

    def save_config_from_editor(self):
        """从编辑器保存 config.json"""
        try:
            config_path = os.path.join(self.node_path, "config.json")
            content = self.config_text.toPlainText().strip()
            
            # 验证 JSON 格式
            try:
                data = json.loads(content)
                # 格式化后保存
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
                with open(config_path, 'w', encoding='utf-8') as f:
                    f.write(formatted)
                
                # 更新内存中的数据
                if self.parent_window and self.node_name in self.parent_window.nodes_data:
                    self.parent_window.nodes_data[self.node_name]['config'] = data
                    
                    # 同步更新画布上的节点显示
                    if hasattr(self.parent_window, 'canvas'):
                        self.parent_window.canvas.sync_node_display(self.node_name)
                
                themed_message(self, t("k_title_success"), "✅ config.json 已保存", "info")
            except json.JSONDecodeError as e:
                reply = themed_message(self, t("k_title_json_error"), f"⚠️ 当前内容不是有效的 JSON 格式：\n\n{str(e)}\n\n是否仍要保存？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No, "question")
                if reply:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # 即使格式错误也尝试更新内存数据
                    if self.parent_window and self.node_name in self.parent_window.nodes_data:
                        try:
                            self.parent_window.nodes_data[self.node_name]['config'] = json.loads(content)
                        except:
                            pass
                    
                    themed_message(self, t("k_title_success"), "✅ 已保存（未格式化）", "info")
                    
        except Exception as e:
            themed_message(self, t("k_title_error"), f"❌ 保存 config.json 失败:\n{str(e)}", "error")

    def load_log_files(self):
        """加载 logs 目录下的所有 .log 文件"""
        try:
            logs_dir = os.path.join(self.node_path, "logs")
            
            if not os.path.exists(logs_dir):
                self.output_text.setPlainText("⚠️ logs 目录不存在\n\n提示：节点启动后会自动创建此目录并生成日志文件")
                self.log_file_combo.clear()
                return
            
            # 查找所有 .log 文件
            log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
            
            if not log_files:
                self.output_text.setPlainText("📭 logs 目录为空\n\n提示：节点尚未产生日志数据")
                self.log_file_combo.clear()
                return
            
            # 按文件名排序
            log_files.sort()
            
            # 填充下拉框
            self.log_file_combo.blockSignals(True)  # 阻止信号触发
            self.log_file_combo.clear()
            for log_file in log_files:
                self.log_file_combo.addItem(log_file)
            self.log_file_combo.blockSignals(False)
            
            # 加载第一个日志文件
            if log_files:
                self.load_selected_log_file(log_files[0])
                
        except Exception as e:
            self.output_text.setPlainText(f"❌ 读取 logs 目录失败:\n{str(e)}")
            self.log_file_combo.clear()
    
    def load_selected_log_file(self, log_filename):
        """加载选定的日志文件内容"""
        try:
            logs_dir = os.path.join(self.node_path, "logs")
            log_path = os.path.join(logs_dir, log_filename)
            
            if not os.path.exists(log_path):
                self.output_text.setPlainText(f"⚠️ 日志文件不存在: {log_filename}")
                return
            
            with open(log_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content:
                self.output_text.setPlainText(f"📭 日志文件为空: {log_filename}")
                return
            
            self.output_text.setPlainText(content)
            
            # 滚动到底部（显示最新日志）
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
                
        except Exception as e:
            self.output_text.setPlainText(f"❌ 读取日志文件失败:\n{str(e)}")
    
    def on_log_file_changed(self, index):
        """当日志文件选择改变时加载对应文件"""
        if index >= 0:
            log_filename = self.log_file_combo.itemText(index)
            self.load_selected_log_file(log_filename)
    
    def refresh_log_files(self):
        """刷新日志文件列表"""
        self.load_log_files()
        themed_message(self, t("k_title_success"), "✅ 日志文件列表已刷新", "info")
    
    def clear_current_log(self):
        """清空当前日志文件"""
        if self.log_file_combo.count() == 0:
            themed_message(self, t("k_title_warning"), t("k_log_no_clear"), "warning")
            return
        
        log_filename = self.log_file_combo.currentText()
        logs_dir = os.path.join(self.node_path, "logs")
        log_path = os.path.join(logs_dir, log_filename)
        
        reply = themed_message(self, t("k_title_confirm_clear"), f"确定要清空日志文件 '{log_filename}' 吗？\n\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No, "question")
        
        if reply:
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.output_text.setPlainText(f"📭 日志文件已清空: {log_filename}")
                themed_message(self, t("k_title_success"), f"✅ 日志文件 '{log_filename}' 已清空", "info")
            except Exception as e:
                themed_message(self, t("k_title_error"), f"❌ 清空日志文件失败:\n{str(e)}", "error")

