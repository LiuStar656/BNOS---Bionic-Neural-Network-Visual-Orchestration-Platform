"""预设节点库对话框 — 使用浮动面板统一UI风格"""
import os
import json
import shutil
import tempfile
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton,
    QTextEdit, QGroupBox, QSplitter, QWidget, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from ui.core.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.utils.dialog_utils import themed_message


class PresetLibraryDialog(FloatingPanel):
    """预设节点库对话框"""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, title=t("k_preset_library"))
        self.setMinimumSize(600, 450)
        self.resize(700, 500)

        self._main_window = parent
        self._presets = {}  # {base_name: {.bnos path, .json data}}
        self._selected_name = None
        self._init_ui()
        self._load_presets()

    def _preset_dir(self):
        return os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))), "node_templates")

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(8, 0, 8, 0)
        top_layout.addStretch()

        refresh_btn = QPushButton(t("k_refresh"))
        refresh_btn.clicked.connect(self._load_presets)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,10);
                color: rgba(255,255,255,150);
                border: 1px solid rgba(255,255,255,20);
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,20);
            }
        """)
        top_layout.addWidget(refresh_btn)

        main_layout.addLayout(top_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: rgba(255,255,255,15);
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: rgba(255,255,255,30);
            }
        """)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._preset_list = QListWidget()
        self._preset_list.setStyleSheet("""
            QListWidget {
                background-color: rgba(255,255,255,5);
                color: #b0b0b0;
                border: none;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 3px;
            }
            QListWidget::item:hover {
                background-color: rgba(255,255,255,10);
            }
            QListWidget::item:selected {
                background-color: rgba(0, 122, 204, 50);
                color: white;
            }
        """)
        self._preset_list.itemClicked.connect(self._on_preset_selected)
        self._preset_list.itemDoubleClicked.connect(self._on_preset_double_clicked)
        left_layout.addWidget(self._preset_list)

        splitter.addWidget(left_widget)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        info_group = QGroupBox(t("k_preset_info"))
        info_group.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(255,255,255,15);
                border-radius: 4px;
                margin-top: 6px;
                color: rgba(255,255,255,150);
                font-size: 11px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(8, 8, 8, 8)

        self._name_label = QLabel("")
        self._name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
        info_layout.addWidget(self._name_label)

        self._desc_edit = QTextEdit()
        self._desc_edit.setReadOnly(True)
        self._desc_edit.setMaximumHeight(120)
        self._desc_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255,255,255,5);
                color: #b0b0b0;
                font-size: 11px;
                border: none;
            }
        """)
        info_layout.addWidget(self._desc_edit)

        details_label = QLabel(t("k_preset_details"))
        details_label.setStyleSheet("color: rgba(255,255,255,120); font-size: 10px;")
        info_layout.addWidget(details_label)

        self._details_label = QLabel("")
        self._details_label.setWordWrap(True)
        self._details_label.setStyleSheet("color: rgba(255,255,255,100); font-size: 10px;")
        info_layout.addWidget(self._details_label)

        right_layout.addWidget(info_group)
        right_layout.addStretch()
        splitter.addWidget(right_widget)
        splitter.setSizes([250, 400])

        main_layout.addWidget(splitter)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(8, 0, 8, 0)
        button_layout.addStretch()

        delete_btn = QPushButton(t("k_delete"))
        delete_btn.clicked.connect(self._delete_preset)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(244, 67, 54, 30);
                color: #F44336;
                border: 1px solid rgba(244, 67, 54, 50);
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: rgba(244, 67, 54, 50);
            }
        """)
        delete_btn.setEnabled(False)
        self._delete_btn = delete_btn
        button_layout.addWidget(delete_btn)

        close_btn = QPushButton(t("k_cancel"))
        close_btn.clicked.connect(self._on_close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,10);
                color: rgba(255,255,255,150);
                border: 1px solid rgba(255,255,255,20);
                border-radius: 4px;
                padding: 4px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,20);
            }
        """)
        button_layout.addWidget(close_btn)

        self._import_btn = QPushButton(t("k_import_to_project"))
        self._import_btn.clicked.connect(self._import_preset)
        self._import_btn.setEnabled(False)
        self._import_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1a8cff;
            }
            QPushButton:disabled {
                background-color: rgba(0, 122, 204, 50);
                color: rgba(255,255,255,80);
            }
        """)
        button_layout.addWidget(self._import_btn)

        main_layout.addLayout(button_layout)
        self.content_layout.addLayout(main_layout)

    def _load_presets(self):
        self._presets.clear()
        self._preset_list.clear()
        preset_dir = self._preset_dir()

        if not os.path.isdir(preset_dir):
            return

        for fname in sorted(os.listdir(preset_dir)):
            if not fname.endswith(".json"):
                continue
            json_path = os.path.join(preset_dir, fname)
            base_name = fname[:-5]  # remove .json
            bnos_path = os.path.join(preset_dir, base_name + ".bnos")
            if not os.path.exists(bnos_path):
                continue

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {"name": base_name, "description": ""}

            self._presets[base_name] = {
                "bnos_path": bnos_path,
                "json_path": json_path,
                "data": data,
            }

            display = data.get("name", base_name)
            desc = data.get("description", "")
            if desc:
                display += f"  —  {desc[:40]}"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, base_name)
            self._preset_list.addItem(item)

    def _on_preset_selected(self, item):
        base_name = item.data(Qt.ItemDataRole.UserRole)
        self._selected_name = base_name

        preset = self._presets.get(base_name)
        if not preset:
            return

        data = preset["data"]
        self._name_label.setText(data.get("name", base_name))
        self._desc_edit.setText(data.get("description", t("k_no_description")))

        details = []
        if data.get("saved_at"):
            details.append(f"{t('k_saved_at')}: {data['saved_at'][:19]}")
        if data.get("source_project"):
            details.append(f"{t('k_source_project')}: {data['source_project']}")
        bnos_size = os.path.getsize(preset["bnos_path"])
        details.append(f"{t('k_size')}: {bnos_size / 1024:.1f} KB")
        self._details_label.setText("\n".join(details))

        self._import_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)

    def _on_preset_double_clicked(self, item):
        self._on_preset_selected(item)
        self._import_preset()

    def _import_preset(self):
        if not self._selected_name:
            themed_message(self, t("k_title_warning"), t("k_select_preset_first"), "warning")
            return

        preset = self._presets.get(self._selected_name)
        if not preset:
            return

        main_window = self._main_window
        if not main_window or not getattr(main_window, "current_project_path", ""):
            themed_message(self, t("k_title_warning"), t("k_project_no_project"), "warning")
            return

        nodes_dir = os.path.join(main_window.current_project_path, "nodes")
        os.makedirs(nodes_dir, exist_ok=True)

        base_name = self._selected_name
        target_path = os.path.join(nodes_dir, base_name)

        if os.path.exists(target_path):
            reply = QMessageBox.question(
                self, t("k_title_warning"),
                f"Node '{base_name}' already exists, overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                counter = 1
                while os.path.exists(target_path):
                    target_path = os.path.join(nodes_dir, f"{base_name}_{counter}")
                    counter += 1
            else:
                shutil.rmtree(target_path)

        try:
            temp_dir = tempfile.mkdtemp()
            extracted_dir = Packager.extract_package(preset["bnos_path"], temp_dir)

            if not extracted_dir:
                shutil.rmtree(temp_dir)
                themed_message(self, t("k_title_error"), "Failed to extract preset", "error")
                return

            shutil.move(extracted_dir, target_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            from ui.core.import_export_manager import _repair_portable_venv
            _repair_portable_venv(target_path)

            main_window.refresh_nodes()
            themed_message(self, t("k_title_success"),
                           t("_k_preset_imported").format(name=base_name), "info")
            self._on_close()
        except Exception as e:
            themed_message(self, t("k_title_error"),
                           f"Import failed: {e}", "error")

    def _delete_preset(self):
        if not self._selected_name:
            return

        preset = self._presets.get(self._selected_name)
        if not preset:
            return

        reply = QMessageBox.question(
            self, t("k_title_confirm"),
            f"Delete preset '{self._selected_name}' from library?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            os.remove(preset["bnos_path"])
            os.remove(preset["json_path"])
        except Exception as e:
            themed_message(self, t("k_title_error"), f"Delete failed: {e}", "error")
            return

        self._selected_name = None
        self._name_label.setText("")
        self._desc_edit.setText("")
        self._details_label.setText("")
        self._import_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._load_presets()

    def _on_close(self):
        self.closed.emit()
        super()._on_close()


from ui.core.packager import Packager
