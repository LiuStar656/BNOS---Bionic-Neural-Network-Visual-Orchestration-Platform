"""节点配置对话框 — 配置编辑器双向同步 + 日志动态刷新"""
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
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.core.logger import logger
from ui.core.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.utils.file_utils import resolve_and_open_folder
from ui.core.utils.dialog_utils import themed_message
from ui.core.polling_manager import polling_manager

class NodeConfigDialog(FloatingPanel):
    """节点配置对话框（双击节点打开）— 配置双向同步 + 日志动态刷新"""
    
    def __init__(self, node_name, config, node_path, parent_window=None):
        super().__init__(parent_window, title=f"节点配置: {node_name}")
        self.node_name = node_name
        self.config = config
        self.node_path = node_path

        # ---- 配置编辑器双向同步状态 ----
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._write_config_to_file)
        self._last_config_content = ""
        self._ignore_external = False

        # ---- 日志自动刷新状态 ----
        self._current_log_file = ""

        self.resize(950, 550)
        self.setMinimumSize(700, 400)
        self._init_ui()

        # ---- 订阅 polling_manager 信号（替代独立定时器）----
        polling_manager.config_file_changed.connect(self._on_config_external_change)
        polling_manager.log_file_changed.connect(self._on_log_external_change)
        polling_manager.node_status_changed.connect(self._on_node_status_changed)
        polling_manager.watch_config(self.node_path)
        
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

        # 工具栏：状态指示
        tool_row = QHBoxLayout()
        self._config_status = QLabel("")
        self._config_status.setStyleSheet("color: rgba(255,255,255,120); font-size: 10px; background: transparent;")
        tool_row.addWidget(self._config_status)
        tool_row.addStretch()
        config_layout.addLayout(tool_row)
        
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
        # 用户编辑文本 → 启动防抖保存
        self.config_text.textChanged.connect(self._on_config_edit)
        
        # 加载并显示 config.json 内容
        self.load_config_json()
        
        config_layout.addWidget(self.config_text)
        
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
        log_file_layout.addStretch()
        
        # 清空日志按钮
        self.clear_log_btn = QPushButton("清空日志")
        self.clear_log_btn.setStyleSheet("background-color: #666666; color: white; padding: 5px 15px;")
        self.clear_log_btn.clicked.connect(self.clear_current_log)
        log_file_layout.addWidget(self.clear_log_btn)
        
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
        
        # 状态显示标签
        self._status_label = QLabel("状态: 检测中...")
        self._status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(self._status_label)
        
        node_path_label = QLabel(f"路径: {self.node_path}")
        node_path_label.setFont(QFont("Arial", 9))
        node_path_label.setWordWrap(True)
        info_layout.addWidget(node_path_label)
        
        right_layout.addWidget(info_group)
        
        # 初始化状态显示
        self._update_status_display()
        
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
        
        # IDE 打开按钮（统一由 IDEScanner 构建，无外部硬编码）
        from ui.core.ide_scanner import ide_scanner
        ide_scanner._app_config = self.parent_window.app_config if self.parent_window and hasattr(self.parent_window, 'app_config') else None
        ide_scanner.add_buttons_to_layout(quick_layout, self.node_name, self.node_path)
        
        right_layout.addWidget(quick_group)
        
        right_layout.addStretch()  # 底部弹性空间
        
        main_h_layout.addLayout(right_layout, 1)  # 右侧占1份空间
        
        self.content_layout.addLayout(main_h_layout)
    
    def _update_status_display(self):
        """更新状态显示标签"""
        if not self.parent_window:
            self._status_label.setText("状态: 未知")
            self._status_label.setStyleSheet("color: gray;")
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if not node_data:
            self._status_label.setText("状态: 未找到")
            self._status_label.setStyleSheet("color: gray;")
            return
        
        status = node_data.get('status', 'unknown')
        if status == 'running':
            self._status_label.setText("状态: ● 运行中")
            self._status_label.setStyleSheet("color: #FF4444;")  # 红色
        elif status == 'idle':
            self._status_label.setText("状态: ● 空闲")
            self._status_label.setStyleSheet("color: #44FF44;")  # 绿色
        else:
            self._status_label.setText("状态: ○ 已停止")
            self._status_label.setStyleSheet("color: gray;")
    
    def _on_node_status_changed(self, node_name, new_status):
        """polling_manager 信号：节点状态变更"""
        if node_name == self.node_name:
            self._update_status_display()
    
    def start_node(self):
        """启动节点（对话框保持打开）"""
        if not self.parent_window:
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if node_data and node_data.get('status') in ('running', 'idle'):
            themed_message(self, t("k_title_info"), t("k_node_already_running"), "info")
            return
        
        try:
            # 使用主窗口的启动方法
            self.parent_window.start_selected_node_by_name(self.node_name)
            # 启动后更新状态显示（对话框保持打开）
            self._update_status_display()
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_node_start_fail_prop").format(err=str(e)), "error")
    
    def stop_node(self):
        """停止节点（对话框保持打开）"""
        if not self.parent_window:
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if not node_data or node_data.get('status') == 'stopped':
            themed_message(self, t("k_title_info"), t("k_node_not_running"), "info")
            return
        
        try:
            # 使用主窗口的停止方法
            self.parent_window.stop_selected_node_by_name(self.node_name)
            # 停止后更新状态显示（对话框保持打开）
            self._update_status_display()
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_node_stop_fail_prop").format(err=str(e)), "error")
    
    def open_node_folder(self):
        """打开节点文件夹"""
        from ui.core.utils.file_utils import resolve_and_open_folder
        resolve_and_open_folder(
            self.node_path,
            self.node_name,
            parent_window=self.parent_window,
            dialog_parent=self
        )
    
    def open_terminal(self):
        """打开命令行并激活虚拟环境"""
        try:
            # 检查虚拟环境是否存在
            if platform.system() == "Windows":
                activate_script = os.path.join(self.node_path, "venv", "Scripts", "activate.bat")
            else:
                activate_script = os.path.join(self.node_path, "venv", "bin", "activate")
            
            if not os.path.exists(activate_script):
                themed_message(self, t("k_title_warning"), t("_k_venv_not_exist").format(path=activate_script), "warning")
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
                    except Exception:
                        continue
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_terminal_open_fail").format(err=str(e)), "error")
            import traceback
            traceback.print_exc()
    
    # ==================== config.json 双向同步（参照 node_expand_panel）====================

    def load_config_json(self):
        """从文件加载 config.json 到编辑器（不触发 textChanged 保存）"""
        config_path = os.path.join(self.node_path, "config.json")
        try:
            if not os.path.exists(config_path):
                self.config_text.blockSignals(True)
                self.config_text.setPlainText("{}")
                self.config_text.blockSignals(False)
                self._last_config_content = "{}"
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                raw = f.read()

            if not raw.strip():
                formatted = "{}"
            else:
                try:
                    data = json.loads(raw)
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    formatted = raw

            self._last_config_content = formatted
            self.config_text.blockSignals(True)
            self.config_text.setPlainText(formatted)
            self.config_text.blockSignals(False)

        except Exception:
            self._last_config_content = ""

    def _on_config_edit(self):
        """用户编辑 → 启动防抖保存"""
        self._save_timer.start(800)

    def _write_config_to_file(self):
        """将编辑器内容写入 config.json（防抖保存）"""
        if self._ignore_external:
            return

        config_path = os.path.join(self.node_path, "config.json")
        content = self.config_text.toPlainText().strip()

        if not content:
            return

        try:
            # 尝试格式化 JSON
            try:
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                # JSON 不合法时直接写入原始内容
                formatted = content

            self._last_config_content = formatted
            self._ignore_external = True

            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(formatted)

            # 编辑器同步为格式化后的内容（阻止回环）
            self.config_text.blockSignals(True)
            self.config_text.setPlainText(formatted)
            self.config_text.blockSignals(False)

            # 更新内存数据
            if self.parent_window and self.node_name in self.parent_window.nodes_data:
                try:
                    self.parent_window.nodes_data[self.node_name]['config'] = data
                except Exception:
                    pass
                if hasattr(self.parent_window, 'canvas'):
                    self.parent_window.canvas.sync_node_display(self.node_name)

            self._config_status.setText(t("k_status_saved"))
            self._config_status.setStyleSheet("color: #4CAF50; font-size: 10px; background: transparent;")

            QTimer.singleShot(500, self._reset_ignore_flag)

        except Exception as e:
            self._config_status.setText(t("k_status_save_failed"))
            self._config_status.setStyleSheet("color: #F44336; font-size: 10px; background: transparent;")
            logger.error("保存 config.json 失败: %s", e)

    def _reset_ignore_flag(self):
        self._ignore_external = False

    def _on_config_external_change(self, node_path):
        """polling_manager 信号：config.json 被外部修改"""
        if node_path != self.node_path or self._ignore_external:
            return
        # 外部变更 → 刷新编辑器
        self.load_config_json()
        self._config_status.setText(t("k_status_updated"))
        self._config_status.setStyleSheet("color: #2196F3; font-size: 10px; background: transparent;")

    # ==================== 日志动态刷新 ====================

    def _on_log_external_change(self, node_path, log_filename):
        """polling_manager 信号：日志文件被外部修改"""
        if node_path != self.node_path or not self._current_log_file:
            return
        if log_filename == self._current_log_file:
            self._load_log_content(log_filename)

    def _load_log_content(self, log_filename):
        """加载日志文件到编辑器"""
        log_path = os.path.join(self.node_path, "logs", log_filename)
        try:
            if not os.path.exists(log_path):
                self.output_text.setPlainText(f"# 日志文件不存在: {log_filename}")
                return

            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if not content.strip():
                self.output_text.setPlainText(t("k_log_empty"))
            else:
                self.output_text.setPlainText(content)
            # 滚动到底部
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass

    def load_log_files(self):
        """加载 logs 目录下的所有 .log 文件"""
        try:
            logs_dir = os.path.join(self.node_path, "logs")
            
            if not os.path.exists(logs_dir):
                self.output_text.setPlainText("# logs 目录不存在\n# 提示：节点启动后会自动创建此目录并生成日志文件")
                self._current_log_file = ""
                self.log_file_combo.blockSignals(True)
                self.log_file_combo.clear()
                self.log_file_combo.blockSignals(False)
                return
            
            # 查找所有 .log 文件
            log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith('.log')])
            
            # 更新下拉框（保留当前选中项）
            self.log_file_combo.blockSignals(True)
            old_current = self.log_file_combo.currentText() if self.log_file_combo.count() > 0 else ""
            self.log_file_combo.clear()
            for log_file in log_files:
                self.log_file_combo.addItem(log_file)
            # 恢复选择
            if old_current and old_current in log_files:
                idx = log_files.index(old_current)
                self.log_file_combo.setCurrentIndex(idx)
            elif log_files:
                self.log_file_combo.setCurrentIndex(0)
            self.log_file_combo.blockSignals(False)
            
            # 加载当前选中的日志并订阅
            if log_files:
                self._current_log_file = self.log_file_combo.currentText()
                polling_manager.watch_log(self.node_path, self._current_log_file)
                self._load_log_content(self._current_log_file)
                
        except Exception:
            pass
    
    def on_log_file_changed(self, index):
        """当日志文件选择改变时加载对应文件"""
        if index >= 0:
            # 取消旧日志订阅
            if self._current_log_file:
                polling_manager.unwatch_log(self.node_path, self._current_log_file)
            log_filename = self.log_file_combo.itemText(index)
            self._current_log_file = log_filename
            polling_manager.watch_log(self.node_path, log_filename)
            self._load_log_content(log_filename)
    
    def clear_current_log(self):
        """清空当前日志文件"""
        if self.log_file_combo.count() == 0:
            themed_message(self, t("k_title_warning"), t("k_log_no_clear"), "warning")
            return
        
        log_filename = self.log_file_combo.currentText()
        logs_dir = os.path.join(self.node_path, "logs")
        log_path = os.path.join(logs_dir, log_filename)
        
        reply = themed_message(self, t("k_title_confirm_clear"), t("_k_clear_log_file_confirm").format(name=log_filename),
            "question")
        
        if reply:
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self._last_log_mtime = os.path.getmtime(log_path)
                self.output_text.setPlainText(t("k_log_cleared"))
            except Exception as e:
                themed_message(self, t("k_title_error"), t("_k_log_file_clear_fail").format(err=str(e)), "error")