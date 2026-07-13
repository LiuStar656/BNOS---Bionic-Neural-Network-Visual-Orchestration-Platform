"""
NodeDetailPanel - 统一的节点详情面板

合并了原来的 NodeConfigDialog 和 NodeExpandPanel，支持普通节点和复合节点。

左侧：标签页（配置 | 输出 | 日志）+ 复合节点专属标签页
右侧：节点信息 + 控制 + 快捷操作
"""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
)

from ui.core.dock.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.logger import logger
from ui.core.system.polling_manager import polling_manager
from ui.core.utils.dialog_utils import themed_message
from ui.core.utils.file_utils import resolve_and_open_folder

from .json_sync_editor import JsonSyncEditor
from .log_viewer_widget import LogViewerWidget
from .node_control_widget import NodeControlWidget
from .node_data_provider import CompositeNodeProvider, RegularNodeProvider


class NodeDetailPanel(FloatingPanel):
    """统一的节点详情面板"""

    _PRIORITY_OPTIONS: list[str] = ["low", "below_normal", "normal", "above_normal", "high"]

    def __init__(self, provider, parent_window=None):
        self._provider = provider
        node_name = provider.get_node_name()
        display_name = provider.get_display_name() if hasattr(provider, "get_display_name") else node_name
        title = f"{t('k_detail_panel')}: {display_name}"
        super().__init__(parent_window, title)

        self._node_name = node_name
        self._is_composite = provider.is_composite()

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(2000)
        self._status_timer.timeout.connect(self._update_status)

        self.resize(950, 600)
        self.setMinimumSize(700, 450)
        self._init_ui()
        self._status_timer.start()

        polling_manager.node_status_changed.connect(self._on_node_status_changed)

    def _init_ui(self):
        try:
            main_h_layout = QHBoxLayout()
            main_h_layout.setSpacing(10)

            left_layout = QVBoxLayout()
            self._tab_widget = QTabWidget()
            self._tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    border: 1px solid #3c3c3c;
                    background-color: #1e1e1e;
                    border-radius: 3px;
                }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #d4d4d4;
                    padding: 6px 15px;
                    border: 1px solid #3c3c3c;
                    border-bottom: none;
                    border-top-left-radius: 3px;
                    border-top-right-radius: 3px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #1e1e1e;
                    color: white;
                    border-bottom: 1px solid #1e1e1e;
                }
            """)

            self._config_editor = JsonSyncEditor(str(self._provider.get_config_path()))
            self._tab_widget.addTab(self._config_editor, t("k_detail_panel_config"))

            self._output_editor = JsonSyncEditor(str(self._provider.get_output_path()))
            self._tab_widget.addTab(self._output_editor, t("k_detail_panel_output"))

            self._log_viewer = LogViewerWidget(str(self._provider.get_log_dir()))
            self._tab_widget.addTab(self._log_viewer, t("k_detail_panel_logs"))

            if self._is_composite:
                self._comp_config_editor = JsonSyncEditor(str(self._provider.get_composite_config_path()))
                self._tab_widget.addTab(self._comp_config_editor, t("k_detail_panel_composite"))

                pipeline_path = self._provider.get_pipeline_path()
                if pipeline_path:
                    self._pipeline_editor = JsonSyncEditor(str(pipeline_path))
                    self._pipeline_editor._editor.setReadOnly(True)
                    self._tab_widget.addTab(self._pipeline_editor, t("k_detail_panel_pipeline"))

                self._dag_status_widget = self._create_dag_status_widget()
                self._tab_widget.addTab(self._dag_status_widget, t("k_detail_panel_dag_status"))

            left_layout.addWidget(self._tab_widget, 1)
            main_h_layout.addLayout(left_layout, 2)

            right_layout = QVBoxLayout()
            right_layout.setSpacing(10)

            info_group = QGroupBox(t("k_node_info"))
            info_layout = QVBoxLayout(info_group)

            display_name = (
                self._provider.get_display_name() if hasattr(self._provider, "get_display_name") else self._node_name
            )
            node_name_label = QLabel(f"{t('k_name')}: {display_name}")
            node_name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            info_layout.addWidget(node_name_label)

            node_type_label = QLabel(
                f"{t('k_type')}: {t('k_detail_type_composite') if self._is_composite else t('k_detail_type_regular')}"
            )
            node_type_label.setFont(QFont("Arial", 9))
            info_layout.addWidget(node_type_label)

            if self._is_composite:
                sub_nodes = self._provider.get_sub_nodes()
                sub_nodes_label = QLabel(f"{t('k_detail_sub_nodes')}{len(sub_nodes)}")
                sub_nodes_label.setFont(QFont("Arial", 9))
                info_layout.addWidget(sub_nodes_label)

            node_path_label = QLabel(f"{t('k_detail_path')}{self._provider.get_node_path()}")
            node_path_label.setFont(QFont("Arial", 9))
            node_path_label.setWordWrap(True)
            info_layout.addWidget(node_path_label)

            right_layout.addWidget(info_group)

            self._control_widget = NodeControlWidget()
            self._control_widget.set_provider(self._provider)
            self._control_widget.set_node_name(self._node_name)
            self._control_widget.update_status()
            right_layout.addWidget(self._control_widget)

            if not self._is_composite:
                right_layout.addWidget(self._create_resource_limit_group())

            quick_group = QGroupBox(t("k_quick_actions"))
            quick_layout = QVBoxLayout(quick_group)

            open_folder_btn = QPushButton(t("k_open_dir"))
            open_folder_btn.setStyleSheet("background-color: #666666; color: white; padding: 10px;")
            open_folder_btn.clicked.connect(self.open_node_folder)
            quick_layout.addWidget(open_folder_btn)

            open_terminal_btn = QPushButton(t("k_open_terminal"))
            open_terminal_btn.setStyleSheet("background-color: #666666; color: white; padding: 10px;")
            open_terminal_btn.clicked.connect(self.open_terminal)
            quick_layout.addWidget(open_terminal_btn)

            from ui.core.node.ide_scanner import ide_scanner

            ide_scanner._app_config = (
                self.parent_window.app_config
                if self.parent_window and hasattr(self.parent_window, "app_config")
                else None
            )
            ide_scanner.add_buttons_to_layout(quick_layout, self._node_name, str(self._provider.get_node_path()))

            right_layout.addWidget(quick_group)
            right_layout.addStretch()

            main_h_layout.addLayout(right_layout, 1)

            self.content_layout.addLayout(main_h_layout)

            if not self._is_composite:
                self._load_resource_limit_from_config()
        except Exception as e:
            logger.error(f"NodeDetailPanel _init_ui error: {e}", exc_info=True)
            themed_message(self, t("k_title_error"), f"Failed to initialize panel: {str(e)}", "error")

    def _create_resource_limit_group(self) -> QGroupBox:
        group = QGroupBox(t("k_resource_limits"))
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        style_line = "QSpinBox { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; border-radius: 3px; padding: 2px; }"

        row_prio = QHBoxLayout()
        row_prio.addWidget(QLabel(t("k_rl_priority")))
        self._rl_priority = QComboBox()
        self._rl_priority.setStyleSheet("""
            QComboBox { background: #2d2d2d; color: #d4d4d4; border: 1px solid #3c3c3c; border-radius: 3px; padding: 3px; }
            QComboBox::drop-down { border: none; }
        """)
        for value in self._PRIORITY_OPTIONS:
            label_key = f"k_rl_priority_{value}"
            self._rl_priority.addItem(t(label_key), value)
        self._rl_priority.setCurrentIndex(2)
        row_prio.addWidget(self._rl_priority)
        layout.addLayout(row_prio)

        row_cpu = QHBoxLayout()
        row_cpu.addWidget(QLabel(t("k_rl_cpu_limit")))
        self._rl_cpu = QSpinBox()
        self._rl_cpu.setRange(0, 10000)
        self._rl_cpu.setSuffix(" %")
        self._rl_cpu.setSpecialValueText(t("k_rl_unlimited"))
        self._rl_cpu.setStyleSheet(style_line)
        self._rl_cpu.setToolTip(t("k_rl_cpu_tooltip"))
        row_cpu.addWidget(self._rl_cpu)
        layout.addLayout(row_cpu)

        row_mem = QHBoxLayout()
        row_mem.addWidget(QLabel(t("k_rl_memory_limit")))
        self._rl_memory = QSpinBox()
        self._rl_memory.setRange(0, 1048576)
        self._rl_memory.setSuffix(" MB")
        self._rl_memory.setSingleStep(128)
        self._rl_memory.setSpecialValueText(t("k_rl_unlimited"))
        self._rl_memory.setStyleSheet(style_line)
        self._rl_memory.setToolTip(t("k_rl_memory_tooltip"))
        row_mem.addWidget(self._rl_memory)
        layout.addLayout(row_mem)

        row_aff = QHBoxLayout()
        row_aff.addWidget(QLabel(t("k_rl_cpu_cores")))
        self._rl_affinity = QLabel(t("k_rl_all_cores"))
        self._rl_affinity.setStyleSheet("color: #888888; font-size: 11px;")
        self._rl_affinity.setToolTip(t("k_rl_affinity_tooltip"))
        row_aff.addWidget(self._rl_affinity)
        row_aff.addStretch()
        layout.addLayout(row_aff)

        self._rl_apply_btn = QPushButton(t("k_rl_apply"))
        self._rl_apply_btn.setStyleSheet("background-color: #3a6bc5; color: white; padding: 8px; font-weight: bold;")
        self._rl_apply_btn.clicked.connect(self._apply_resource_limits)
        layout.addWidget(self._rl_apply_btn)

        self._rl_status = QLabel("")
        self._rl_status.setStyleSheet("color: #888888; font-size: 10px; padding-top: 2px;")
        self._rl_status.setWordWrap(True)
        layout.addWidget(self._rl_status)

        return group

    def _load_resource_limit_from_config(self) -> None:
        rl = self._provider.get_resource_limits()
        if not rl:
            self._rl_priority.setCurrentIndex(2)
            self._rl_cpu.setValue(0)
            self._rl_memory.setValue(0)
            self._rl_affinity.setText(t("k_rl_all_cores"))
            return

        priority = rl.get("priority", "normal")
        idx = self._rl_priority.findData(priority)
        if idx >= 0:
            self._rl_priority.setCurrentIndex(idx)
        else:
            self._rl_priority.setCurrentIndex(2)

        self._rl_cpu.setValue(rl.get("cpu_percent", 0))
        self._rl_memory.setValue(rl.get("memory_mb", 0))

        affinity = rl.get("cpu_affinity")
        if affinity and isinstance(affinity, list):
            self._rl_affinity.setText(", ".join(str(c) for c in affinity))
        else:
            self._rl_affinity.setText(t("k_rl_all_cores"))

    def _apply_resource_limits(self) -> None:
        priority = self._rl_priority.currentData()
        cpu = self._rl_cpu.value()
        memory = self._rl_memory.value()

        has_any = priority != "normal" or cpu > 0 or memory > 0

        config_content = self._config_editor.get_content()
        try:
            config = {} if not config_content.strip() else __import__("json").loads(config_content)
        except Exception:
            config = {}

        if not has_any:
            if "resource_limit" in config:
                del config["resource_limit"]
            self._rl_status.setText(t("k_rl_cleared"))
            self._rl_status.setStyleSheet("color: #888888; font-size: 10px;")
        else:
            resource_limit = {"priority": priority}
            if cpu > 0:
                resource_limit["cpu_percent"] = cpu
            if memory > 0:
                resource_limit["memory_mb"] = memory
            config["resource_limit"] = resource_limit
            self._rl_status.setText(t("k_rl_applied"))
            self._rl_status.setStyleSheet("color: #4CAF50; font-size: 10px;")

        import json as _json

        formatted = _json.dumps(config, indent=2, ensure_ascii=False)
        self._config_editor.set_content(formatted)
        self._config_editor._write_to_file()

    def _create_dag_status_widget(self):
        from PySide6.QtWidgets import QTextEdit, QWidget

        widget = QWidget()
        layout = QVBoxLayout(widget)

        refresh_btn = QPushButton(t("k_detail_refresh_status"))
        refresh_btn.setStyleSheet("background-color: #555555; color: white; padding: 5px 10px; font-size: 10px;")
        refresh_btn.clicked.connect(self._refresh_dag_status)
        layout.addWidget(refresh_btn)

        self._dag_status_text = QTextEdit()
        self._dag_status_text.setReadOnly(True)
        self._dag_status_text.setFont(QFont("Consolas", 10))
        self._dag_status_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self._dag_status_text, 1)

        self._refresh_dag_status()
        return widget

    def _refresh_dag_status(self):
        status = self._provider.get_dag_status()
        if status:
            import json as _json

            formatted = _json.dumps(status, indent=2, ensure_ascii=False)
            self._dag_status_text.setPlainText(formatted)
        else:
            self._dag_status_text.setPlainText(t("k_detail_no_dag_status"))

    def _update_status(self):
        self._control_widget.update_status()
        if self._is_composite:
            self._refresh_dag_status()

    def _on_node_status_changed(self, node_name, new_status):
        if node_name == self._node_name:
            self._update_status()

    def open_node_folder(self):
        resolve_and_open_folder(
            str(self._provider.get_node_path()), self._node_name, parent_window=self.parent_window, dialog_parent=self
        )

    def open_terminal(self):
        try:
            activate_path = (
                Path(self._provider.get_node_path()) / "venv" / "Scripts" / "activate.bat"
                if platform.system() == "Windows"
                else Path(self._provider.get_node_path()) / "venv" / "bin" / "activate"
            )

            if not activate_path.exists():
                themed_message(
                    self, t("k_title_warning"), t("_k_venv_not_exist").format(path=str(activate_path)), "warning"
                )
                return

            system = platform.system()
            if system == "Windows":
                cmd = f'start cmd /k "cd /d {self._provider.get_node_path()} && call venv\\Scripts\\activate.bat && echo Virtual environment activated"'
                subprocess.Popen(cmd, shell=True)
            elif system == "Darwin":
                script = f"""tell application "Terminal"
                    do script "cd '{self._provider.get_node_path()}' && source venv/bin/activate && echo 'Virtual environment activated'"
                end tell"""
                subprocess.Popen(["osascript", "-e", script])
            else:
                terminals = ["gnome-terminal", "konsole", "xterm"]
                for terminal in terminals:
                    try:
                        cmd = f"cd '{self._provider.get_node_path()}' && source venv/bin/activate && exec bash"
                        subprocess.Popen([terminal, "-e", f'bash -c "{cmd}"'])
                        break
                    except Exception:
                        continue
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_terminal_open_fail").format(err=str(e)), "error")

    def closeEvent(self, event):
        self._status_timer.stop()
        polling_manager.node_status_changed.disconnect(self._on_node_status_changed)
        super().closeEvent(event)

    @staticmethod
    def create_for_node(node_name: str, parent_window) -> NodeDetailPanel:
        """为节点创建详情面板（自动判断普通节点还是复合节点）"""
        if node_name.startswith("composite_"):
            provider = CompositeNodeProvider(node_name, parent_window)
        else:
            node_info = parent_window.nodes_data.get(node_name, {}) if parent_window else {}
            provider = RegularNodeProvider(node_name, node_info, parent_window)
        return NodeDetailPanel(provider, parent_window)
