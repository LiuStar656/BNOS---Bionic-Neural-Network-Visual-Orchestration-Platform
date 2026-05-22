"""
设置对话框 — 语言切换 + 进程隔离模式
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QComboBox, QCheckBox, QPushButton, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.core.i18n import t, set_lang, LANG
from ui.core.utils.dialog_utils import themed_message


_SET_STYLE = """
QDialog { background-color: #2d2d30; }
QGroupBox { color: #ccc; font-weight: bold; border: 1px solid #454545; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QLabel { color: #ccc; }
QComboBox { background: #3c3c3c; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 4px 8px; }
QComboBox QAbstractItemView { background: #252526; color: #ccc; }
QCheckBox { color: #ccc; }
QCheckBox::indicator { width: 16px; height: 16px; background: #3c3c3c; border: 1px solid #555; border-radius: 2px; }
QCheckBox::indicator:checked { background: #007acc; border-color: #007acc; }
"""

_BTN_OK = "QPushButton { background: #0e639c; color: white; padding: 8px 24px; border: none; border-radius: 3px; font-weight: bold; } QPushButton:hover { background: #1177bb; }"
_BTN_GREY = "QPushButton { background: #444; color: #ccc; padding: 8px 16px; border: none; border-radius: 3px; } QPushButton:hover { background: #555; }"


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowTitle(t("_k_settings_title"))
        self.setFixedSize(420, 260)
        self.setStyleSheet(_SET_STYLE)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._restart_needed = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 12, 16, 12)

        # 标题栏
        title_bar = QHBoxLayout()
        title = QLabel(t("_k_settings_title"))
        title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        title_bar.addWidget(title)
        title_bar.addStretch()
        close_lbl = QLabel("✕")
        close_lbl.setStyleSheet("color: #888; font-size: 14px; padding: 2px 6px;")
        close_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        close_lbl.mousePressEvent = lambda e: self.reject()
        title_bar.addWidget(close_lbl)
        layout.addLayout(title_bar)

        # ===== 语言设置 =====
        lang_group = QGroupBox(t("_k_settings_language"))
        lang_layout = QHBoxLayout(lang_group)
        lang_layout.addWidget(QLabel(t("_k_settings_lang_label")))
        self.lang_combo = QComboBox()
        self.lang_combo.addItem(t("_k_lang_cn"), "cn")
        self.lang_combo.addItem(t("_k_lang_en"), "en")
        # 设置当前选中
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == LANG:
                self.lang_combo.setCurrentIndex(i)
                break
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        lang_layout.addWidget(self.lang_combo, 1)
        layout.addWidget(lang_group)

        # ===== 进程隔离 =====
        proc_group = QGroupBox(t("_k_settings_process"))
        proc_layout = QVBoxLayout(proc_group)

        self.proc_check = QCheckBox(t("_k_settings_process_label"))
        self.proc_check.setChecked(self.main_window.CANVAS_PROCESS_MODE)
        self.proc_check.toggled.connect(lambda: setattr(self, '_restart_needed', True))
        proc_layout.addWidget(self.proc_check)

        proc_hint = QLabel(t("_k_settings_process_hint"))
        proc_hint.setStyleSheet("color: #888; font-size: 10px; padding-left: 20px;")
        proc_hint.setWordWrap(True)
        proc_layout.addWidget(proc_hint)
        layout.addWidget(proc_group)

        layout.addStretch()

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton(t("k_cancel"))
        cancel_btn.setStyleSheet(_BTN_GREY)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton(t("k_ok"))
        ok_btn.setStyleSheet(_BTN_OK)
        ok_btn.clicked.connect(self._apply_and_close)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

    def _on_lang_changed(self, idx):
        lang = self.lang_combo.itemData(idx)
        if lang != LANG:
            self._restart_needed = True

    def _apply_and_close(self):
        """应用设置"""
        lang = self.lang_combo.currentData()
        proc_mode = self.proc_check.isChecked()

        lang_changed = (lang != LANG)
        proc_changed = (proc_mode != self.main_window.CANVAS_PROCESS_MODE)

        if lang_changed or proc_changed:
            # 先持久化配置到磁盘
            if lang_changed:
                try:
                    self.main_window.app_config.set("language", lang)
                except Exception:
                    pass
            if proc_changed:
                self.main_window.CANVAS_PROCESS_MODE = proc_mode
                try:
                    self.main_window.app_config.set("process_mode", proc_mode)
                except Exception:
                    pass
            # 强制刷盘到磁盘
            try:
                self.main_window.app_config.save()
            except Exception:
                pass

            # 先切语言再显示提示
            if lang_changed:
                set_lang(lang)
            themed_message(self, t("_k_settings_restart_title"),
                t("_k_settings_restart_msg"), "info")
            self.accept()
            self.main_window._restart_application()
        else:
            self.accept()
