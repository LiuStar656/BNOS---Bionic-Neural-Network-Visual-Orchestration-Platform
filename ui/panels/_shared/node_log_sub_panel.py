"""
节点日志子面板共享基类 — 消除 node_monitor.py 与 node_monitor_dock.py 中的重复定义

BaseNodeLogSubPanel 包含以下共享逻辑:
  - 日志文件加载（_load_log）
  - polling_manager 日志变更订阅
  - 资源监测定时器 + PID 检测 + 进程树遍历
  - 折叠/展开切换
  - 状态更新接口（支持 running/idle/stopped 三态）
  - 取消订阅清理

子类负责:
  - _build_title_bar() — 标题栏 UI（浮动版有 3 按钮 + 折叠指示符，Dock 版内联资源条）
  - _build_resource_row() — 资源显示 UI
  - _build_log_area() — 日志内容区 UI
  - 特有功能（如 _clear_log, _open_folder）
"""
import os
import subprocess
import psutil
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QProgressBar, QWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ui.core.i18n import t
from ui.core.polling_manager import polling_manager
from ui.core.utils.dialog_utils import themed_message
from ui.panels._shared.system_resource_collector import SystemResourceCollector
from ui.core.logger import logger


class BaseNodeLogSubPanel(QGroupBox):
    """节点日志子面板共享基类（可折叠）"""

    def __init__(self, node_name: str, node_path: str, node_status: str = "stopped", parent=None):
        super().__init__(parent)
        self.node_name = node_name
        self.node_path = node_path
        self._collapsed = False
        self._log_file = os.path.join(node_path, "logs", "listener.log")
        self._resource_timer: QTimer | None = None
        self._last_cpu = 0.0
        self._last_memory = 0.0

        self.setObjectName(f"node_log_{node_name}")

        # 子类由 _build_ui() 构建
        self._build_ui(node_status)
        self._load_log()

        # 订阅 polling_manager 日志变更信号
        polling_manager.watch_log(node_path, "listener.log")
        polling_manager.log_file_changed.connect(self._on_external_log_change)

        # 启动资源监测定时器
        self._start_resource_timer()

    # ──── 子类必须覆盖的方法 ────

    def _build_ui(self, status: str):
        """总 UI 构建入口 — 子类覆盖此方法实现自己的布局"""
        raise NotImplementedError("子类必须实现 _build_ui()")

    def _build_title_content(self, status: str) -> QPushButton:
        """构建标题按钮（公共辅助方法）"""
        status_text = t("k_status_running") if status == 'running' else t("k_status_stopped")
        status_color = "#4CAF50" if status == 'running' else "#999"
        btn = QPushButton(f"{self.node_name}  [{status_text}]")
        btn.setStyleSheet(f"""
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
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._toggle_collapse)
        self._title_btn = btn
        return btn

    # ──── 共享逻辑 ────

    def _start_resource_timer(self):
        """启动资源监测定时器"""
        self._resource_timer = QTimer(self)
        self._resource_timer.timeout.connect(self._update_resource_usage)
        self._resource_timer.start(1000)

    def _update_resource_usage(self):
        """更新资源占用（采集数据 + 更新 UI）"""
        pid = SystemResourceCollector.get_node_pid(self.node_path)
        cpu, memory = SystemResourceCollector.collect_process_resources(pid) if pid else (None, None)

        self._last_cpu = cpu or 0.0
        self._last_memory = memory or 0.0

        # 子类覆盖此方法实现自己的 UI 更新
        self._on_resource_updated(cpu, memory)

    def _on_resource_updated(self, cpu: float | None, memory: float | None):
        """资源数据更新后的 UI 刷新 — 子类覆盖"""
        raise NotImplementedError("子类必须实现 _on_resource_updated()")

    def _load_log(self):
        """加载日志文件内容"""
        if not os.path.exists(self._log_file):
            self._set_log_text("# 暂无日志\n# 节点启动后将自动生成")
            return

        try:
            with open(self._log_file, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if not content.strip():
                self._set_log_text(t("k_log_empty"))
            else:
                self._set_log_text(content)
            self._scroll_log_to_bottom()
        except Exception as e:
            self._set_log_text(f"# 读取失败: {e}")

    def _set_log_text(self, text: str):
        """设置日志文本 — 子类覆盖"""
        raise NotImplementedError("子类必须实现 _set_log_text()")

    def _scroll_log_to_bottom(self):
        """滚动日志到底部 — 子类覆盖"""
        pass

    def _on_external_log_change(self, node_path, log_filename):
        """polling_manager 信号：日志文件被外部修改"""
        if node_path == self.node_path:
            self._load_log()

    def _toggle_collapse(self):
        """切换展开/折叠"""
        self._collapsed = not self._collapsed
        self._on_collapse_changed(self._collapsed)

    def _on_collapse_changed(self, collapsed: bool):
        """折叠状态改变 — 子类覆盖"""
        raise NotImplementedError("子类必须实现 _on_collapse_changed()")

    # ──── 公共 API ────

    def update_status(self, status: str):
        """外部更新状态显示（支持 running/idle/stopped 三态）"""
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

    def unsubscribe_monitor(self):
        """取消订阅 polling_manager（面板移除时调用）"""
        polling_manager.unwatch_log(self.node_path, "listener.log")
        if self._resource_timer:
            self._resource_timer.stop()
            self._resource_timer = None

    # ──── 可选的扩展功能（子类按需覆盖）────

    def _clear_log(self, parent_widget=None):
        """清空日志文件（需要确认对话框）"""
        reply = themed_message(
            parent_widget or self, t("k_title_confirm_clear"),
            t("_k_clear_log_confirm").format(name=self.node_name), "question"
        )
        if not reply:
            return
        try:
            os.makedirs(os.path.dirname(self._log_file), exist_ok=True)
            with open(self._log_file, 'w', encoding='utf-8') as f:
                f.write("")
            self._set_log_text(t("k_log_cleared"))
        except Exception as e:
            themed_message(
                parent_widget or self, t("k_title_error"),
                t("_k_clear_failed").format(err=str(e)), "error"
            )

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
