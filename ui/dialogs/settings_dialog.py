"""
设置对话框 — 语言切换 + 进程隔离模式
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QComboBox, QCheckBox, QPushButton, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.core.i18n import t, set_lang, get_lang
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

# 语言名始终用自身语言，不翻译
_LANG_NAMES = {"cn": "中文", "en": "English"}


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self._orig_lang = get_lang()
        self._restart_needed = False
        self.setWindowTitle(t("_k_settings_title"))
        self.setFixedSize(420, 280)
        self.setStyleSheet(_SET_STYLE)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
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
        lang_layout = QVBoxLayout(lang_group)
        lang_layout.setSpacing(6)

        # 当前语言只读显示
        cur_row = QHBoxLayout()
        cur_row.addWidget(QLabel(t("_k_settings_lang_label")))
        self._cur_lang_label = QLabel(_LANG_NAMES.get(self._orig_lang, self._orig_lang))
        self._cur_lang_label.setStyleSheet("color: #4fc3f7; font-weight: bold;")
        cur_row.addWidget(self._cur_lang_label)
        cur_row.addStretch()
        lang_layout.addLayout(cur_row)

        # 切换下拉
        switch_row = QHBoxLayout()
        switch_row.addWidget(QLabel(t("_k_settings_switch_lang")))
        self.lang_combo = QComboBox()
        for code, name in _LANG_NAMES.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(1 if self._orig_lang == "en" else 0)
        self.lang_combo.currentIndexChanged.connect(self._on_lang_changed)
        switch_row.addWidget(self.lang_combo, 1)
        lang_layout.addLayout(switch_row)

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

        self.ok_btn = QPushButton(t("k_ok"))
        self.ok_btn.setStyleSheet(_BTN_OK)
        self.ok_btn.clicked.connect(self._apply_and_close)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def _on_lang_changed(self, idx):
        lang = self.lang_combo.itemData(idx)
        if lang != self._orig_lang:
            self._restart_needed = True

    def _apply_and_close(self):
        """应用设置"""
        lang = self.lang_combo.currentData()
        proc_mode = self.proc_check.isChecked()

        lang_changed = (lang != self._orig_lang)
        proc_changed = (proc_mode != self.main_window.CANVAS_PROCESS_MODE)

        if not lang_changed and not proc_changed:
            # 无变更，直接关闭
            self.accept()
            return

        # 有变更：持久化配置
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
        try:
            self.main_window.app_config.save()
        except Exception:
            pass

        # 显示重启提示（用当前语言，因为还没重启）
        themed_message(self, t("_k_settings_restart_title"),
            t("_k_settings_restart_msg"), "info")
        self.accept()
        self.main_window._restart_application()
