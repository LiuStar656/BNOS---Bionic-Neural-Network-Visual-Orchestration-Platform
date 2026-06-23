"""
节点监测面板 - Dock版本（无标题栏）
全局实时日志查看组件，支持节点资源占用检测

与 node_monitor.py 共享:
  - SystemResourceCollector: 系统+节点资源数据采集
  - NodePanelSyncMixin: 子面板同步逻辑
"""
import os
import psutil
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QWidget, QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt, QTimer
from ui.core.i18n import t
from ui.core.polling_manager import polling_manager
from ui.panels._shared.system_resource_collector import SystemResourceCollector
from ui.panels._shared.node_panel_sync_mixin import NodePanelSyncMixin
from ui.core.dock_panel_base import DockPanelBase


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NodeLogSubPanel — Dock版
#  特有: 内联 CPU/MEM 进度条在标题栏、无 Refresh/Clear/Dir 按钮
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class NodeLogSubPanel(QGroupBox):
    """单个节点的日志子面板（可折叠）— Dock版特有 UI"""

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
        self.destroyed.connect(self.unsubscribe_monitor)

    # ──── UI 构建（Dock版特有：内联资源条在标题栏）────

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

        # Dock版特有：内联资源占用指示器在标题栏
        self._cpu_bar = QProgressBar()
        self._cpu_bar.setRange(0, 100)
        self._cpu_bar.setValue(0)
        self._cpu_bar.setTextVisible(False)
        self._cpu_bar.setFixedWidth(40)
        self._cpu_bar.setStyleSheet(self._bar_css("#4CAF50"))
        self._cpu_label = QLabel("CPU: 0%")
        self._cpu_label.setStyleSheet("color: rgba(255,255,255,100); font-size: 9px;")
        self._cpu_label.setFixedWidth(50)

        self._mem_bar = QProgressBar()
        self._mem_bar.setRange(0, 100)
        self._mem_bar.setValue(0)
        self._mem_bar.setTextVisible(False)
        self._mem_bar.setFixedWidth(40)
        self._mem_bar.setStyleSheet(self._bar_css("#2196F3"))
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

    @staticmethod
    def _bar_css(color):
        return f"""
            QProgressBar {{
                height: 8px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 10);
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """

    # ──── 定时器 + 资源采集（委托给 SystemResourceCollector）────

    def _start_resource_timer(self):
        from ui.core.update_scheduler import update_scheduler
        update_scheduler.subscribe(self, 1000, self._update_resource_usage)

    def _update_resource_usage(self):
        """更新资源占用 — 委托 SystemResourceCollector"""
        pid = SystemResourceCollector.get_node_pid(self.node_path)
        cpu_percent, memory_mb = SystemResourceCollector.collect_process_resources(pid) if pid else (None, None)

        self._last_cpu = cpu_percent or 0.0
        self._last_memory = memory_mb or 0.0
        is_running = cpu_percent is not None

        self.update_status('running' if is_running else 'stopped')

        self._cpu_bar.setValue(min(int(self._last_cpu), 100))
        self._cpu_label.setText(f"CPU: {self._last_cpu:.1f}%")
        self._mem_bar.setValue(min(int(self._last_memory / 10), 100))
        self._mem_label.setText(f"MEM: {self._last_memory:.1f}MB")

    # ──── 日志操作 ────

    def _load_log(self):
        if not os.path.exists(self._log_file):
            self._log_area.setPlainText("# 暂无日志\n# 节点启动后将自动生成")
            return
        try:
            with open(self._log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                if len(content) > 1000:
                    content = "..." + content[-1000:]
                if not content.strip():
                    self._log_area.setPlainText("# 暂无日志\n# 节点启动后将自动生成")
                else:
                    self._log_area.setPlainText(content)
                self._log_area.verticalScrollBar().setValue(
                    self._log_area.verticalScrollBar().maximum()
                )
        except Exception as e:
            self._log_area.setPlainText(f"# 读取失败: {e}")

    def _on_external_log_change(self, node_path, log_filename):
        if node_path == self.node_path:
            self._load_log()

    def _toggle_collapse(self):
        self._collapsed = not self._collapsed
        self._log_area.setVisible(not self._collapsed)
        if self._collapsed:
            self.setFixedHeight(30)
        else:
            self.setFixedHeight(120)

    def unsubscribe_monitor(self):
        from ui.core.update_scheduler import update_scheduler
        update_scheduler.unsubscribe(self)

    # ──── 状态更新（Dock版：仅 running/stopped）────

    def update_status(self, status):
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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NodeMonitorDock — Dock版
#  使用 NodePanelSyncMixin 消除同步逻辑重复
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class NodeMonitorDock(DockPanelBase, NodePanelSyncMixin):
    """节点监测面板（Dock版本）"""

    def __init__(self, parent=None):
        DockPanelBase.__init__(self, parent)
        NodePanelSyncMixin.__init__(self)
        self.parent_window = parent
        self._sub_panels = {}

        polling_manager.node_status_changed.connect(self._on_node_status_changed)

        self.setMinimumSize(320, 350)
        self._init_ui()

        self._schedule_update(3000, self._sync_panels)

        self._sync_panels()

    def _create_sub_panel(self, node_name, node_path, status):
        """工厂方法 — 创建 Dock版 NodeLogSubPanel"""
        return NodeLogSubPanel(node_name, node_path, status)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { background: #1e1e1e; border: none; }
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

    def dispose(self):
        """面板销毁时清理"""
        if self._disposed:
            return
        for panel in self._sub_panels.values():
            panel.unsubscribe_monitor()
        self._sub_panels.clear()
        super().dispose()
