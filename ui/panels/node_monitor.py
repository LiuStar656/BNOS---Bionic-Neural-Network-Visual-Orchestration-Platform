"""
节点监测面板 - 全局实时日志查看组件（浮动版）
无边框、半透明深色背景、可拖动
父窗口 + QScrollArea + 多个 NodeLogSubPanel 子窗口
支持节点资源占用检测

与 node_monitor_dock.py 共享:
  - SystemResourceCollector: 系统+节点资源数据采集
  - NodePanelSyncMixin: 子面板同步逻辑
"""
import os
import subprocess
import psutil
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QWidget, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ui.core.i18n import t
from ui.core.floating_panel import FloatingPanel
from ui.core.utils.dialog_utils import themed_message
from ui.core.polling_manager import polling_manager
from ui.panels._shared.system_resource_collector import SystemResourceCollector
from ui.panels._shared.node_panel_sync_mixin import NodePanelSyncMixin


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NodeLogSubPanel — 浮动版
#  特有: Refresh/Clear/Dir 按钮、折叠指示符、CPU > 80% 变红
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class NodeLogSubPanel(QGroupBox):
    """单个节点的日志子面板（可折叠）— 浮动版特有 UI"""

    def __init__(self, node_name, node_path, node_status="stopped", parent=None):
        super().__init__(parent)
        self.node_name = node_name
        self.node_path = node_path
        self._collapsed = False
        self._log_file = os.path.join(node_path, "logs", "listener.log")
        self._resource_timer = None
        self._last_cpu = 0.0
        self._last_memory = 0.0

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

    # ──── UI 构建（浮动版特有）────

    def _init_ui(self, status):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

        # 标题栏（可点击折叠）
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

        # 资源占用显示
        resource_row = QHBoxLayout()
        resource_row.setSpacing(8)

        cpu_layout = QVBoxLayout()
        self._cpu_label = QLabel("CPU: 0%")
        self._cpu_label.setStyleSheet("color: #4CAF50; font-size: 9px;")
        self._cpu_bar = QProgressBar()
        self._cpu_bar.setRange(0, 100)
        self._cpu_bar.setValue(0)
        self._cpu_bar.setMaximumWidth(80)
        self._cpu_bar.setStyleSheet(self._cpu_bar_css("#4CAF50"))
        cpu_layout.addWidget(self._cpu_label)
        cpu_layout.addWidget(self._cpu_bar)
        resource_row.addLayout(cpu_layout)

        mem_layout = QVBoxLayout()
        self._mem_label = QLabel("MEM: 0 MB")
        self._mem_label.setStyleSheet("color: #2196F3; font-size: 9px;")
        self._mem_bar = QProgressBar()
        self._mem_bar.setRange(0, 100)
        self._mem_bar.setValue(0)
        self._mem_bar.setMaximumWidth(80)
        self._mem_bar.setStyleSheet(self._mem_bar_css("#2196F3"))
        mem_layout.addWidget(self._mem_label)
        mem_layout.addWidget(self._mem_bar)
        resource_row.addLayout(mem_layout)

        resource_row.addStretch()
        layout.addLayout(resource_row)

        # 日志内容区
        self._log_editor = QTextEdit()
        self._log_editor.setReadOnly(True)
        self._log_editor.setMaximumHeight(160)
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

        # 底部按钮栏（浮动版特有）
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

    @staticmethod
    def _cpu_bar_css(color):
        return f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 10);
                border-radius: 3px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """

    @staticmethod
    def _mem_bar_css(color):
        return NodeLogSubPanel._cpu_bar_css(color)

    # ──── 定时器 + 资源采集（委托给 SystemResourceCollector）────

    def _start_resource_timer(self):
        self._resource_timer = QTimer(self)
        self._resource_timer.timeout.connect(self._update_resources)
        self._resource_timer.start(2000)  # 2秒间隔

    def _update_resources(self):
        """更新节点资源占用 — 委托 SystemResourceCollector"""
        pid = SystemResourceCollector.get_node_pid(self.node_path)
        if not pid:
            self._cpu_label.setText("CPU: -")
            self._cpu_bar.setValue(0)
            self._mem_label.setText("MEM: -")
            self._mem_bar.setValue(0)
            return

        if not psutil.pid_exists(pid):
            self._cpu_label.setText("CPU: -")
            self._cpu_bar.setValue(0)
            self._mem_label.setText("MEM: -")
            self._mem_bar.setValue(0)
            return

        cpu_total, mem_mb = SystemResourceCollector.collect_process_resources(pid)
        if cpu_total is None:
            return

        mem_percent = (mem_mb * 1024 * 1024 / psutil.virtual_memory().total) * 100

        self._cpu_label.setText(f"CPU: {cpu_total:.1f}%")
        self._cpu_bar.setValue(min(int(cpu_total), 100))
        self._mem_label.setText(f"MEM: {mem_mb:.1f} MB")
        self._mem_bar.setValue(min(int(mem_percent), 100))

        # 浮动版特有：CPU > 80% 进度条变红
        if cpu_total > 80:
            self._cpu_bar.setStyleSheet(self._cpu_bar_css("#F44336"))
        else:
            self._cpu_bar.setStyleSheet(self._cpu_bar_css("#4CAF50"))

    # ──── 日志操作 ────

    def _load_log(self):
        if not os.path.exists(self._log_file):
            self._log_editor.setPlainText("# 暂无日志\n# 节点启动后将自动生成")
            return
        try:
            with open(self._log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if not content.strip():
                self._log_editor.setPlainText(t("k_log_empty"))
            else:
                self._log_editor.setPlainText(content)
            scrollbar = self._log_editor.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception as e:
            self._log_editor.setPlainText(f"# 读取失败: {e}")

    def _on_external_log_change(self, node_path, log_filename):
        if node_path == self.node_path:
            self._load_log()

    def _clear_log(self):
        reply = themed_message(self, t("k_title_confirm_clear"),
            t("_k_clear_log_confirm").format(name=self.node_name), "question")
        if not reply:
            return
        try:
            os.makedirs(os.path.dirname(self._log_file), exist_ok=True)
            with open(self._log_file, 'w', encoding='utf-8') as f:
                f.write("")
            self._log_editor.setPlainText(t("k_log_cleared"))
        except Exception as e:
            themed_message(self, t("k_title_error"),
                t("_k_clear_failed").format(err=str(e)), "error")

    def _open_folder(self):
        import platform
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(['explorer', self.node_path])
        elif system == "Darwin":
            subprocess.Popen(['open', self.node_path])
        else:
            subprocess.Popen(['xdg-open', self.node_path])

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        self._log_editor.setVisible(not self._collapsed)
        self._collapse_indicator.setText(">" if self._collapsed else "v")

    def unsubscribe_monitor(self):
        polling_manager.unwatch_log(self.node_path, "listener.log")
        if self._resource_timer:
            self._resource_timer.stop()
            self._resource_timer = None

    # ──── 状态更新（浮动版特有：三态 running/idle/stopped）────

    def update_status(self, status):
        if status == 'running':
            status_text = t("k_status_running")
            status_color = "#4CAF50"
        elif status == 'idle':
            status_text = t("k_status_idle")
            status_color = "#F0A030"
        else:
            status_text = t("k_status_stopped")
            status_color = "#999"
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NodeMonitor — 浮动版
#  使用 NodePanelSyncMixin 消除同步逻辑重复
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class NodeMonitor(FloatingPanel, NodePanelSyncMixin):
    """节点监测面板（浮动半透明悬浮窗）"""

    def __init__(self, parent=None):
        FloatingPanel.__init__(self, parent, title=t("k_info_monitor"))
        NodePanelSyncMixin.__init__(self)  # no-op but ensures proper MRO
        self._sub_panels = {}

        polling_manager.node_status_changed.connect(self._on_node_status_changed)

        self.resize(420, 600)
        self.setMinimumSize(320, 350)
        self._init_ui()

        self._list_timer = QTimer(self)
        self._list_timer.timeout.connect(self._sync_panels)
        self._list_timer.start(3000)

        self._sync_panels()

    def _create_sub_panel(self, node_name, node_path, status):
        """工厂方法 — 创建浮动版 NodeLogSubPanel"""
        return NodeLogSubPanel(node_name, node_path, status)

    def _init_ui(self):
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
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

    def _on_close(self):
        for sub in self._sub_panels.values():
            sub.unsubscribe_monitor()
        self._list_timer.stop()
        super()._on_close()
