"""
属性配置面板 - 右侧面板，显示和编辑节点配置
"""
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
        config_group = QGroupBox("配置编辑")
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
            QMessageBox.information(self, "提示", "节点已在运行中")
            return
        
        try:
            # 使用主窗口的启动方法
            self.parent_window.start_selected_node_by_name(self.node_name)
            self.close()
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
            import platform
            
            # 详细调试：打印所有路径相关信息
            logger.debug("[NodeConfigDialog] 打开节点文件夹")
            logger.debug("节点名称: %s", self.node_name)
            logger.debug("原始节点路径: %s", self.node_path)
            logger.debug("路径类型: %s", type(self.node_path))
            
            # 关键修复：确保路径是绝对路径且规范化
            original_path = self.node_path
            corrected_path = os.path.abspath(original_path)
            corrected_path = os.path.normpath(corrected_path)
            
            if original_path != corrected_path:
                logger.debug("路径已修正: 原始=%s, 修正=%s", original_path, corrected_path)
                self.node_path = corrected_path
            
            logger.debug("最终节点路径: %s", self.node_path)
            logger.debug("路径是否存在: %s", os.path.exists(self.node_path))
            logger.debug("是否为目录: %s", os.path.isdir(self.node_path) if os.path.exists(self.node_path) else 'N/A')
            logger.debug("父目录: %s", os.path.dirname(self.node_path))
            logger.debug("文件夹名称: %s", os.path.basename(self.node_path))
            logger.debug("当前工作目录: %s", os.getcwd())
            
            # 检查路径是否包含预期的节点名称
            expected_folder = self.node_name
            actual_folder = os.path.basename(self.node_path)
            logger.debug("期望的文件夹名: %s, 实际的文件夹名: %s, 匹配: %s",
                         expected_folder, actual_folder, expected_folder == actual_folder)
            
            if not os.path.exists(self.node_path):
                logger.warning("路径不存在: %s", self.node_path)
                
                # 尝试从父窗口获取正确路径
                if self.parent_window and hasattr(self.parent_window, 'nodes_data'):
                    node_info = self.parent_window.nodes_data.get(self.node_name)
                    if node_info and 'path' in node_info:
                        correct_path = node_info['path']
                        correct_path = os.path.abspath(correct_path)
                        correct_path = os.path.normpath(correct_path)
                        
                        logger.debug("尝试从 nodes_data 获取路径: %s", correct_path)
                        
                        if os.path.exists(correct_path):
                            logger.debug("找到正确路径，使用此路径")
                            self.node_path = correct_path
                        else:
                            logger.warning("备用路径也不存在: %s", correct_path)
                
                if not os.path.exists(self.node_path):
                    QMessageBox.warning(
                        self, 
                        "警告", 
                        f"⚠️ 节点文件夹不存在！\n\n路径: {self.node_path}\n\n"
                        f"可能原因：\n"
                        f"1. 节点已被删除\n"
                        f"2. 项目路径已更改\n"
                        f"3. 节点数据未正确加载\n\n"
                        f"请尝试刷新节点列表。"
                    )
                    return
            
            system = platform.system()
            if system == "Windows":
                subprocess.Popen(['explorer', self.node_path])
            elif system == "Darwin":  # macOS
                subprocess.Popen(['open', self.node_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', self.node_path])
                
            logger.debug("已打开节点文件夹: %s", self.node_path)
        except Exception as e:
            logger.error("打开文件夹异常: %s", e)
            QMessageBox.critical(self, "错误", f"打开文件夹失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
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
                QMessageBox.warning(self, "警告", f"节点文件夹不存在:\n{self.node_path}")
                return
            
            # 预检测 VSCode 是否安装
            vscode_installed = self._check_vscode_installed()
            if not vscode_installed:
                reply = QMessageBox.question(
                    self,
                    "VSCode 未检测到",
                    "⚠️ 未检测到 VSCode (code 命令)\n\n"
                    "是否仍要创建工作区文件？\n\n"
                    "您可以稍后手动用 VSCode 打开该文件。",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
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
                    
                    QMessageBox.information(self, "成功", 
                        f"✅ 已创建 VSCode 工作区并自动打开\n\n"
                        f"工作区文件：{workspace_file}\n"
                        f"使用相对路径配置，可安全迁移项目")
                except Exception as e:
                    QMessageBox.information(self, "工作区已创建", 
                        f"✅ VSCode 工作区文件已创建\n\n"
                        f"工作区文件：{workspace_file}\n\n"
                        f"⚠️ 自动打开失败：{str(e)}\n\n"
                        f"请手动用 VSCode 打开该文件")
            else:
                QMessageBox.information(self, "工作区已创建", 
                    f"✅ VSCode 工作区文件已创建\n\n"
                    f"工作区文件：{workspace_file}\n\n"
                    f"💡 提示：安装 VSCode 并添加 'code' 命令到 PATH 后，\n"
                    f"可以双击此文件直接用 VSCode 打开")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建 VSCode 工作区失败: {str(e)}")
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
                QMessageBox.warning(self, "警告", f"虚拟环境不存在:\n{activate_script}")
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
            QMessageBox.critical(self, "错误", f"打开命令行失败: {str(e)}")
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
                
                QMessageBox.information(self, "成功", "✅ config.json 已保存")
            except json.JSONDecodeError as e:
                reply = QMessageBox.question(
                    self, 
                    "JSON 格式错误",
                    f"⚠️ 当前内容不是有效的 JSON 格式：\n\n{str(e)}\n\n是否仍要保存？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    # 即使格式错误也尝试更新内存数据
                    if self.parent_window and self.node_name in self.parent_window.nodes_data:
                        try:
                            self.parent_window.nodes_data[self.node_name]['config'] = json.loads(content)
                        except:
                            pass
                    
                    QMessageBox.information(self, "成功", "✅ 已保存（未格式化）")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"❌ 保存 config.json 失败:\n{str(e)}")

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
        QMessageBox.information(self, "成功", "✅ 日志文件列表已刷新")
    
    def clear_current_log(self):
        """清空当前日志文件"""
        if self.log_file_combo.count() == 0:
            QMessageBox.warning(self, "警告", "没有可清空的日志文件")
            return
        
        log_filename = self.log_file_combo.currentText()
        logs_dir = os.path.join(self.node_path, "logs")
        log_path = os.path.join(logs_dir, log_filename)
        
        reply = QMessageBox.question(
            self, 
            "确认清空",
            f"确定要清空日志文件 '{log_filename}' 吗？\n\n此操作不可恢复！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self.output_text.setPlainText(f"📭 日志文件已清空: {log_filename}")
                QMessageBox.information(self, "成功", f"✅ 日志文件 '{log_filename}' 已清空")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"❌ 清空日志文件失败:\n{str(e)}")

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
        start_btn = QPushButton("启动节点")
        start_btn.setStyleSheet("background-color: #333333; color: white; padding: 8px; font-weight: bold;")
        start_btn.clicked.connect(self.start_node)
        btn_row_layout.addWidget(start_btn)
        
        # 停止按钮
        stop_btn = QPushButton("停止节点")
        stop_btn.setStyleSheet("background-color: #555555; color: white; padding: 8px; font-weight: bold;")
        stop_btn.clicked.connect(self.stop_node)
        btn_row_layout.addWidget(stop_btn)
        
        control_layout.addLayout(btn_row_layout)
        self.content_layout.addWidget(control_group)
        
        # 保存按钮
        save_btn = QPushButton("保存配置")
        save_btn.setStyleSheet("background-color: #333333; color: white; padding: 10px; font-weight: bold;")
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
            
            # 确定启动脚本路径
            if sys.platform == "win32":
                start_script = os.path.join(self.current_node_path, "start.bat")
            else:
                start_script = os.path.join(self.current_node_path, "start.sh")
            
            if not os.path.exists(start_script):
                QMessageBox.critical(self, "错误", f"启动脚本不存在: {start_script}")
                return
            
            # 启动节点进程 - 使用启动脚本
            if sys.platform == "win32":
                # Windows: 直接执行 bat 文件，传入 --no-pause 参数避免pause
                process = subprocess.Popen(
                    [start_script, "--no-pause"],
                    cwd=self.current_node_path,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                # Linux/Mac: 赋予执行权限并执行 shell 脚本，传入 --no-pause 参数
                os.chmod(start_script, 0o755)
                process = subprocess.Popen(
                    ["/bin/bash", start_script, "--no-pause"],
                    cwd=self.current_node_path,
                    start_new_session=True
                )
            
            # 更新状态
            self.parent_window.update_node_status(self.current_node_name, 'running')
            
            QMessageBox.information(self, "成功", f"节点 '{self.current_node_name}' 已启动")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动节点失败: {str(e)}")
            
    def stop_node(self):
        """停止节点 - 强制关闭进程"""
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
            # ✅ 强制杀死进程
            process = node_data['process']
            if process.poll() is None:  # 进程仍在运行
                try:
                    # 直接强制终止进程
                    process.kill()
                    process.wait(timeout=3)
                except Exception as e:
                    logger.error("强制终止进程时出错: %s", e)
                    # 如果 kill 失败，尝试 terminate
                    try:
                        process.terminate()
                        process.wait(timeout=3)
                    except:
                        pass
            
            # 清理进程引用
            node_data['process'] = None
            node_data['status'] = 'stopped'
            
            # 更新状态
            self.parent_window.update_node_status(self.current_node_name, 'stopped')
            
            QMessageBox.information(self, "成功", f"节点 '{self.current_node_name}' 已强制停止")
            
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
        self.setWindowTitle("颜色设置")
        self.setGeometry(300, 200, 500, 600)
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("自定义外观")
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
        canvas_group = QGroupBox("画布背景")
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
        node_group = QGroupBox("节点样式")
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
        anchor_group = QGroupBox("锚点样式")
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
        edge_group = QGroupBox("连线样式")
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
        theme_group = QGroupBox("快速主题")
        theme_layout = QVBoxLayout(theme_group)
        
        theme_btn_layout = QVBoxLayout()
        
        # 浅色主题
        light_theme_btn = QPushButton("浅色主题")
        light_theme_btn.clicked.connect(lambda: self.apply_preset_theme('light'))
        theme_btn_layout.addWidget(light_theme_btn)
        
        # 深色主题
        dark_theme_btn = QPushButton("深色主题")
        dark_theme_btn.clicked.connect(lambda: self.apply_preset_theme('dark'))
        theme_btn_layout.addWidget(dark_theme_btn)
        
        # 蓝色科技主题
        blue_theme_btn = QPushButton("蓝色科技")
        blue_theme_btn.clicked.connect(lambda: self.apply_preset_theme('blue'))
        theme_btn_layout.addWidget(blue_theme_btn)
        
        # 绿色自然主题
        green_theme_btn = QPushButton("绿色自然")
        green_theme_btn.clicked.connect(lambda: self.apply_preset_theme('green'))
        theme_btn_layout.addWidget(green_theme_btn)
        
        theme_layout.addLayout(theme_btn_layout)
        
        content_layout.addWidget(theme_group)
        
        # 按钮区域
        button_layout = QVBoxLayout()
        
        # 应用按钮
        apply_btn = QPushButton("应用更改")
        apply_btn.setStyleSheet("background-color: #333333; color: white; padding: 10px; font-weight: bold;")
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)
        
        # 重置按钮
        reset_btn = QPushButton("恢复默认")
        reset_btn.setStyleSheet("background-color: #666666; color: white; padding: 10px;")
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
            
            QMessageBox.information(self, "成功", "颜色设置已应用")
            self.close()
            
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
        
        QMessageBox.information(self, "提示", "已恢复默认颜色设置")
