"""
节点监测面板 - 全局实时日志查看组件
参照 NodeListPanel 样式：无边框、半透明深色背景、可拖动
父窗口 + QScrollArea + 多个 NodeLogSubPanel 子窗口
"""
import os
import subprocess
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QWidget, QScrollArea, QMessageBox
)
from ui.core.i18n import t
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.core.floating_panel import FloatingPanel


class NodeLogSubPanel(QGroupBox):
    """单个节点的日志子面板（可折叠）"""

    def __init__(self, node_name, node_path, node_status="stopped", parent=None):
        super().__init__(parent)
        self.node_name = node_name
        self.node_path = node_path
        self._collapsed = False
        self._last_mtime = 0
        self._log_file = os.path.join(node_path, "logs", "listener.log")

        self.setStyleSheet("""
            QGroupBox {
                color: rgba(255, 255, 255, 200);
                font-size: 11px;
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)

        self._init_ui(node_status)
        self._load_log()
        self._start_timer()

    def _init_ui(self, status):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

        # ---- 标题栏（可点击折叠）----
        title_row = QHBoxLayout()
        status_text = t("k_status_running") if status == 'running' else t("k_status_stopped")
        status_color = "#4CAF50" if status == 'running' else "#999"
        self._title_btn = QPushButton(f"{self.node_name}  [{status_text}]")
        self._title_btn.setStyleSheet(f"""
            QPushButton {{
                color: {status_color};
                background: transparent;
                border: none;
                font-size: 11px;
                font-weight: bold;
                text-align: left;
                padding: 2px;
            }}
            QPushButton:hover {{
                color: white;
            }}
        """)
        self._title_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._title_btn.clicked.connect(self._toggle_collapse)
        title_row.addWidget(self._title_btn)
        title_row.addStretch()

        # 折叠指示符
        self._collapse_indicator = QLabel("v")
        self._collapse_indicator.setStyleSheet("color: rgba(255, 255, 255, 150); font-size: 10px;")
        title_row.addWidget(self._collapse_indicator)
        layout.addLayout(title_row)

        # 日志内容区
        self._log_editor = QTextEdit()
        self._log_editor.setReadOnly(True)
        self._log_editor.setMaximumHeight(180)
        self._log_editor.setFont(QFont("Consolas", 8))
        self._log_editor.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                color: #b0b0b0;
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self._log_editor)

        # 底部按钮栏
        btn_row = QHBoxLayout()
        btn_style = (
            "background-color: #444444; color: white; padding: 2px 8px; "
            "font-size: 9px; border: none; border-radius: 3px;"
        )

        refresh_btn = QPushButton(t("k_action_refresh"))
        refresh_btn.setStyleSheet(btn_style)
        refresh_btn.clicked.connect(self._load_log)
        btn_row.addWidget(refresh_btn)

        clear_btn = QPushButton(t("k_action_clear"))
        clear_btn.setStyleSheet(btn_style)
        clear_btn.clicked.connect(self._clear_log)
        btn_row.addWidget(clear_btn)

        open_dir_btn = QPushButton(t("k_action_dir"))
        open_dir_btn.setStyleSheet(btn_style)
        open_dir_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(open_dir_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    # ==================== 功能 ====================

    def _load_log(self):
        """加载日志文件内容（完整读取，有 mtime 变化才刷新）"""
        if not os.path.exists(self._log_file):
            self._log_editor.setPlainText("# 暂无日志\n# 节点启动后将自动生成")
            self._last_mtime = 0
            return

        try:
            self._last_mtime = os.path.getmtime(self._log_file)
            with open(self._log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if not content.strip():
                self._log_editor.setPlainText(t("k_log_empty"))
            else:
                self._log_editor.setPlainText(content)
            # 滚动到底部
            scrollbar = self._log_editor.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            self._log_editor.setPlainText(f"# 读取失败: {e}")

    def _check_and_refresh(self):
        """定时器回调：只在文件变化时重新加载"""
        if not os.path.exists(self._log_file):
            return
        try:
            current_mtime = os.path.getmtime(self._log_file)
        except OSError:
            return
        if current_mtime > self._last_mtime:
            self._load_log()

    def _clear_log(self):
        """清空日志文件"""
        reply = themed_message(self, t("k_title_confirm_clear"), f"确定要清空 {self.node_name} 的日志文件吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, "question")
        if not reply:
            return
        try:
            os.makedirs(os.path.dirname(self._log_file), exist_ok=True)
            with open(self._log_file, 'w', encoding='utf-8') as f:
                f.write("")
            self._log_editor.setPlainText(t("k_log_cleared"))
            self._last_mtime = os.path.getmtime(self._log_file)
        except Exception as e:
            themed_message(self, t("k_title_error"), f"清空失败: {e}", "error")

    def _open_folder(self):
        """打开节点目录"""
        import platform
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(['explorer', self.node_path])
        elif system == "Darwin":
            subprocess.Popen(['open', self.node_path])
        else:
            subprocess.Popen(['xdg-open', self.node_path])

    def _toggle_collapse(self):
        """切换展开/折叠"""
        self._collapsed = not self._collapsed
        self._log_editor.setVisible(not self._collapsed)
        self._collapse_indicator.setText(">" if self._collapsed else "v")

    # ==================== 定时器 ====================

    def _start_timer(self):
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._refresh_timer.timeout.connect(self._check_and_refresh)
        self._refresh_timer.start(2000)

    def stop_timer(self):
        """外部停止定时器"""
        if hasattr(self, '_refresh_timer'):
            self._refresh_timer.stop()

    # ==================== 状态更新 ====================

    def update_status(self, status):
        """外部更新状态显示"""
        status_text = t("k_status_running") if status == 'running' else t("k_status_stopped")
        status_color = "#4CAF50" if status == 'running' else "#999"
        self._title_btn.setText(f"{self.node_name}  [{status_text}]")
        self._title_btn.setStyleSheet(f"""
            QPushButton {{
                color: {status_color};
                background: transparent;
                border: none;
                font-size: 11px;
                font-weight: bold;
                text-align: left;
                padding: 2px;
            }}
            QPushButton:hover {{
                color: white;
            }}
        """)


class NodeMonitor(FloatingPanel):
    """节点监测面板（浮动半透明悬浮窗）"""

    def __init__(self, parent=None):
        super().__init__(parent, title=t("k_info_monitor"))
        self._sub_panels = {}

        self.resize(420, 600)
        self.setMinimumSize(320, 350)
        self._init_ui()

        # 定时刷新子面板列表（每 3 秒检查画布节点变化）
        self._list_timer = QTimer(self)
        self._list_timer.timeout.connect(self._sync_panels)
        self._list_timer.start(3000)

        self._sync_panels()

    def _init_ui(self):
        """初始化UI"""
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(255, 255, 255, 5);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 40);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self._panel_widget = QWidget()
        self._panel_layout = QVBoxLayout(self._panel_widget)
        self._panel_layout.setContentsMargins(0, 0, 0, 0)
        self._panel_layout.setSpacing(4)
        self._panel_layout.addStretch()

        self._scroll.setWidget(self._panel_widget)
        self.content_layout.addWidget(self._scroll, 1)

        self.hint(t("k_info_monitor_hint"))

    # ==================== 同步逻辑 ====================

    def _sync_panels(self):
        """同步子面板列表与画布节点"""
        if not self.parent_window:
            return

        canvas = getattr(self.parent_window, 'canvas', None)
        if not canvas:
            return

        canvas_nodes = set(canvas.nodes.keys())
        current_nodes = set(self._sub_panels.keys())

        # 移除已不在画布上的节点子面板
        removed = current_nodes - canvas_nodes
        for name in removed:
            self._remove_sub_panel(name)

        # 添加新节点子面板
        added = canvas_nodes - current_nodes
        for name in added:
            if name in self.parent_window.nodes_data:
                node_info = self.parent_window.nodes_data[name]
                self._add_sub_panel(name, node_info.get('path', ''),
                                    node_info.get('status', 'stopped'))

        # 更新状态
        for name in self._sub_panels:
            if name in self.parent_window.nodes_data:
                status = self.parent_window.nodes_data[name].get('status', 'stopped')
                self._sub_panels[name].update_status(status)

    def _add_sub_panel(self, node_name, node_path, status):
        """添加一个节点日志子面板"""
        sub = NodeLogSubPanel(node_name, node_path, status)
        # 插入到 stretch 之前
        self._panel_layout.insertWidget(self._panel_layout.count() - 1, sub)
        self._sub_panels[node_name] = sub

    def _remove_sub_panel(self, node_name):
        """移除节点日志子面板"""
        if node_name in self._sub_panels:
            sub = self._sub_panels[node_name]
            sub.stop_timer()
            self._panel_layout.removeWidget(sub)
            sub.deleteLater()
            del self._sub_panels[node_name]

    # ==================== 拖动（继承自 FloatingPanel 基类）====================

    # ==================== 生命周期 ====================

    def _on_close(self):
        for sub in self._sub_panels.values():
            sub.stop_timer()
        self._list_timer.stop()
        super()._on_close()
