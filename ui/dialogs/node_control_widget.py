"""
NodeControlWidget - 节点控制组件

封装了启动/停止按钮和状态显示，可复用在普通节点和复合节点的控制场景。
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.core.i18n import t
from ui.core.utils.dialog_utils import themed_message


class NodeControlWidget(QWidget):
    """节点控制组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._node_name = ""
        self._status = "stopped"
        self._parent_window = parent
        self._provider = None
        self._operation_in_progress = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        self._status_label = QLabel(t("k_status") + ": detecting...")
        self._status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(self._status_label)

        control_group = QGroupBox(t("k_node_control"))
        control_layout = QVBoxLayout(control_group)

        self._start_btn = QPushButton(t("k_node_start"))
        self._start_btn.setStyleSheet(
            "background-color: #333333; color: white; padding: 12px; font-weight: bold; font-size: 13px;"
        )
        self._start_btn.clicked.connect(self.start_node)
        control_layout.addWidget(self._start_btn)

        self._stop_btn = QPushButton(t("k_node_stop"))
        self._stop_btn.setStyleSheet(
            "background-color: #555555; color: white; padding: 12px; font-weight: bold; font-size: 13px;"
        )
        self._stop_btn.clicked.connect(self.stop_node)
        control_layout.addWidget(self._stop_btn)

        layout.addWidget(control_group)

    def set_provider(self, provider):
        """设置数据提供者"""
        self._provider = provider

    def set_node_name(self, node_name: str):
        """设置节点名称"""
        self._node_name = node_name

    def update_status(self):
        """更新状态显示"""
        if self._provider:
            self._status = self._provider.get_status()
        else:
            self._status = "stopped"

        if self._status == "running":
            self._status_label.setText(t("k_status") + ": " + t("k_status_running"))
            self._status_label.setStyleSheet("color: #FF4444;")
            self._start_btn.setEnabled(False)
            self._start_btn.setStyleSheet(
                "background-color: #3a3a3a; color: #888; padding: 12px; font-weight: bold; font-size: 13px;"
            )
            self._stop_btn.setEnabled(not self._operation_in_progress)
            self._stop_btn.setStyleSheet(
                "background-color: #555555; color: white; padding: 12px; font-weight: bold; font-size: 13px;"
            )
        elif self._status == "idle":
            self._status_label.setText(t("k_status") + ": " + t("k_status_idle"))
            self._status_label.setStyleSheet("color: #44FF44;")
            self._start_btn.setEnabled(False)
            self._start_btn.setStyleSheet(
                "background-color: #3a3a3a; color: #888; padding: 12px; font-weight: bold; font-size: 13px;"
            )
            self._stop_btn.setEnabled(not self._operation_in_progress)
            self._stop_btn.setStyleSheet(
                "background-color: #555555; color: white; padding: 12px; font-weight: bold; font-size: 13px;"
            )
        else:
            self._status_label.setText(t("k_status") + ": " + t("k_status_stopped"))
            self._status_label.setStyleSheet("color: gray;")
            self._start_btn.setEnabled(not self._operation_in_progress)
            self._start_btn.setStyleSheet(
                "background-color: #333333; color: white; padding: 12px; font-weight: bold; font-size: 13px;"
            )
            self._stop_btn.setEnabled(False)
            self._stop_btn.setStyleSheet(
                "background-color: #3a3a3a; color: #888; padding: 12px; font-weight: bold; font-size: 13px;"
            )

    def start_node(self):
        """启动节点"""
        if self._operation_in_progress or not self._provider:
            return

        self._operation_in_progress = True
        self.update_status()

        try:
            self._provider.start()
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_node_start_fail_prop").format(err=str(e)), "error")
        finally:
            self._operation_in_progress = False
            self.update_status()

    def stop_node(self):
        """停止节点"""
        if self._operation_in_progress or not self._provider:
            return

        self._operation_in_progress = True
        self.update_status()

        try:
            self._provider.stop()
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_node_stop_fail_prop").format(err=str(e)), "error")
        finally:
            self._operation_in_progress = False
            self.update_status()
