"""
节点监测面板 - Dock版本（无标题栏）
全局实时日志查看组件，支持节点资源占用检测
"""
import os
import subprocess
import psutil
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QWidget, QScrollArea, QProgressBar
)
from ui.core.i18n import t
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.core.utils.dialog_utils import themed_message
from ui.core.polling_manager import polling_manager


class NodeLogSubPanel(QGroupBox):
    """单个节点的日志子面板（可折叠）"""

    def __init__(self, node_name, node_path, node_status="stopped", parent=None):
        super().__init__(parent)
        self.node_name = node_name
        self.node_path = node_path
        self._collapsed = False
        self._log_file = os.path.join(node_path, "logs", "listener.log")
        self._resource_timer = None
        self._last_cpu = 0
        self._last_memory = 0

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

        polling_manager.watch_log(node_path, "listener.log")
        polling_manager.log_file_changed.connect(self._on_external_log_change)

        self._start_resource_timer()

    def _init_ui(self, status):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

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
                color: {status_color};
            }}
        """)
        self._title_btn.clicked.connect(self._toggle_collapse)
        title_row.addWidget(self._title_btn)

        # 资源占用指示器
        self._cpu_bar = QProgressBar()
        self._cpu_bar.setRange(0, 100)
        self._cpu_bar.setValue(0)
        self._cpu_bar.setTextVisible(False)
        self._cpu_bar.setFixedWidth(40)
        self._cpu_bar.setStyleSheet("""
            QProgressBar {
                height: 8px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 10);
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        self._cpu_label = QLabel("CPU: 0%")
        self._cpu_label.setStyleSheet("color: rgba(255,255,255,100); font-size: 9px;")
        self._cpu_label.setFixedWidth(50)

        self._mem_bar = QProgressBar()
        self._mem_bar.setRange(0, 100)
        self._mem_bar.setValue(0)
        self._mem_bar.setTextVisible(False)
        self._mem_bar.setFixedWidth(40)
        self._mem_bar.setStyleSheet("""
            QProgressBar {
                height: 8px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 10);
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 4px;
            }
        """)
        self._mem_label = QLabel("MEM: 0MB")
        self._mem_label.setStyleSheet("color: rgba(255,255,255,100); font-size: 9px;")
        self._mem_label.setFixedWidth(60)

        title_row.addStretch()
        title_row.addWidget(self._cpu_label)
        title_row.addWidget(self._cpu_bar)
        title_row.addWidget(self._mem_label)
        title_row.addWidget(self._mem_bar)

        layout.addLayout(title_row)

        # 日志区域
        self._log_area = QTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setStyleSheet("""
            QTextEdit {
                background-color: rgba(0, 0, 0, 40);
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 3px;
                color: rgba(255, 255, 255, 180);
                font-size: 10px;
                font-family: Consolas, monospace;
            }
        """)
        self._log_area.setFixedHeight(80)
        layout.addWidget(self._log_area)

    def _toggle_collapse(self):
        """切换折叠状态"""
        self._collapsed = not self._collapsed
        self._log_area.setVisible(not self._collapsed)
        if self._collapsed:
            self.setFixedHeight(30)
        else:
            self.setFixedHeight(120)

    def _load_log(self):
        """加载日志文件"""
        if not os.path.exists(self._log_file):
            self._log_area.setPlainText("# 暂无日志\n# 节点启动后将自动生成")
            return

        try:
            with open(self._log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                # 只显示最后1000字符
                if len(content) > 1000:
                    content = "..." + content[-1000:]
                if not content.strip():
                    self._log_area.setPlainText("# 暂无日志\n# 节点启动后将自动生成")
                else:
                    self._log_area.setPlainText(content)
                # 滚动到底部
                self._log_area.verticalScrollBar().setValue(
                    self._log_area.verticalScrollBar().maximum()
                )
        except Exception as e:
            self._log_area.setPlainText(f"# 读取失败: {e}")

    def _on_external_log_change(self, node_path, log_filename):
        """polling_manager 信号：日志文件被外部修改"""
        if node_path == self.node_path:
            self._load_log()

    def _start_resource_timer(self):
        """启动资源监测定时器"""
        self._resource_timer = QTimer(self)
        self._resource_timer.timeout.connect(self._update_resource_usage)
        self._resource_timer.start(1000)

    def _update_resource_usage(self):
        """更新资源占用"""
        cpu_percent = 0
        memory_mb = 0
        is_running = False

        try:
            # 优先尝试 .pid 文件（与资源监测面板保持一致）
            node_pid_file = os.path.join(self.node_path, '.pid')
            if not os.path.exists(node_pid_file):
                # 也支持不带点的 pid 文件
                node_pid_file = os.path.join(self.node_path, 'pid')
            if os.path.exists(node_pid_file):
                with open(node_pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    cpu_percent = process.cpu_percent()
                    memory_mb = process.memory_info().rss / (1024 * 1024)
                    is_running = True

                    for child in process.children(recursive=True):
                        try:
                            cpu_percent += child.cpu_percent()
                            memory_mb += child.memory_info().rss / (1024 * 1024)
                        except:
                            pass
        except Exception:
            pass

        self._last_cpu = cpu_percent
        self._last_memory = memory_mb

        # 更新状态显示（根据进程实际状态）
        self.update_status('running' if is_running else 'stopped')

        self._cpu_bar.setValue(min(int(cpu_percent), 100))
        self._cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
        self._mem_bar.setValue(min(int(memory_mb / 10), 100))
        self._mem_label.setText(f"MEM: {memory_mb:.1f}MB")

    def update_status(self, status):
        """更新节点状态显示"""
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
        """)

    def unsubscribe_monitor(self):
        """取消订阅日志监测"""
        if self._resource_timer:
            self._resource_timer.stop()


class NodeMonitorDock(QWidget):
    """节点监测面板（Dock版本 - 无标题栏）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._sub_panels = {}

        self.setMinimumSize(320, 350)
        self._init_ui()

        self._list_timer = QTimer(self)
        self._list_timer.timeout.connect(self._sync_panels)
        self._list_timer.start(3000)

        self._sync_panels()

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea {
                background: #1e1e1e;
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
        self._panel_layout.setContentsMargins(8, 8, 8, 8)
        self._panel_layout.setSpacing(4)
        self._panel_layout.addStretch()

        self._scroll.setWidget(self._panel_widget)
        layout.addWidget(self._scroll)

    def _sync_panels(self):
        """同步子面板列表与画布节点"""
        if not self.parent_window:
            return

        canvas = getattr(self.parent_window, 'canvas', None)
        if not canvas:
            return

        canvas_nodes = set(canvas.nodes.keys())
        current_nodes = set(self._sub_panels.keys())

        removed = current_nodes - canvas_nodes
        for name in removed:
            self._remove_sub_panel(name)

        added = canvas_nodes - current_nodes
        for name in added:
            if hasattr(self.parent_window, 'nodes_data') and name in self.parent_window.nodes_data:
                node_info = self.parent_window.nodes_data[name]
                self._add_sub_panel(name, node_info.get('path', ''),
                                    node_info.get('status', 'stopped'))

        for name in self._sub_panels:
            if hasattr(self.parent_window, 'nodes_data') and name in self.parent_window.nodes_data:
                status = self.parent_window.nodes_data[name].get('status', 'stopped')
                self._sub_panels[name].update_status(status)

    def _add_sub_panel(self, node_name, node_path, status):
        """添加一个节点日志子面板"""
        sub = NodeLogSubPanel(node_name, node_path, status)
        self._panel_layout.insertWidget(self._panel_layout.count() - 1, sub)
        self._sub_panels[node_name] = sub

    def _remove_sub_panel(self, node_name):
        """移除节点日志子面板"""
        if node_name in self._sub_panels:
            sub = self._sub_panels[node_name]
            sub.unsubscribe_monitor()
            self._panel_layout.removeWidget(sub)
            sub.deleteLater()
            del self._sub_panels[node_name]

    def closeEvent(self, event):
        """关闭事件"""
        for sub in self._sub_panels.values():
            sub.unsubscribe_monitor()
        self._list_timer.stop()
        super().closeEvent(event)