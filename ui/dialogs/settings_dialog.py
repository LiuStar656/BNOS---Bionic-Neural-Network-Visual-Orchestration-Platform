"""
设置对话框 — 语言/进程隔离 + 快捷键管理（浮动窗口版本）
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QComboBox, QCheckBox, QPushButton, QGroupBox,
                              QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence
from ui.core.floating_panel import FloatingPanel
from ui.core.i18n import t, set_lang, get_lang
from ui.core.utils.dialog_utils import themed_message

_SET_STYLE = """
QGroupBox { color: #ccc; font-weight: bold; border: 1px solid #454545; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QLabel { color: #ccc; }
QComboBox { background: #3c3c3c; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 4px 8px; }
QComboBox QAbstractItemView { background: #252526; color: #ccc; }
QCheckBox { color: #ccc; }
QCheckBox::indicator { width: 16px; height: 16px; background: #3c3c3c; border: 1px solid #555; border-radius: 2px; }
QCheckBox::indicator:checked { background: #007acc; border-color: #007acc; }
QTabWidget::pane { border: 1px solid #454545; background: #2d2d30; }
QTabBar::tab { background: #3c3c3c; color: #aaa; padding: 6px 16px; border: 1px solid #454545; border-bottom: none; }
QTabBar::tab:selected { background: #2d2d30; color: #fff; }
QTableWidget { background: #252526; color: #ccc; border: 1px solid #454545; gridline-color: #3e3e42; font-size: 11px; }
QTableWidget::item { padding: 3px 6px; }
QTableWidget::item:selected { background: #094771; }
QHeaderView::section { background: #333; color: #aaa; border: none; padding: 4px; font-size: 11px; }
"""
_BTN_OK = "QPushButton { background: #0e639c; color: white; padding: 8px 24px; border: none; border-radius: 3px; font-weight: bold; } QPushButton:hover { background: #1177bb; }"
_BTN_GREY = "QPushButton { background: #444; color: #ccc; padding: 8px 16px; border: none; border-radius: 3px; } QPushButton:hover { background: #555; }"
_BTN_SMALL = "QPushButton { background: #555; color: #ccc; padding: 2px 8px; border: none; border-radius: 2px; font-size: 10px; } QPushButton:hover { background: #777; }"

_LANG_NAMES = {"cn": "中文", "en": "English"}


class SettingsDialog(FloatingPanel):
    """设置对话框（常规 + 快捷键标签页）— 浮动窗口版本"""

    def __init__(self, main_window, parent=None):
        super().__init__(parent, title=t("_k_settings_title"))
        self.main_window = main_window
        self._orig_lang = get_lang()
        self._shortcut_changes = {}  # sid → new_keystr
        self._editing_row = -1
        
        self.resize(580, 440)
        self.setStyleSheet(_SET_STYLE)
        
        # 居中显示
        if parent:
            self.move(parent.geometry().center() - self.rect().center())

        self.init_ui()

    def init_ui(self):
        # 标签页
        tabs = QTabWidget()
        tabs.addTab(self._make_general_tab(), t("_k_settings_tab_general"))
        tabs.addTab(self._make_shortcuts_tab(), t("_k_settings_tab_shortcuts"))
        self.content_layout.addWidget(tabs, 1)

        # 底部按钮
        btn = QHBoxLayout()
        btn.addStretch()
        cb = QPushButton(t("k_cancel"))
        cb.setStyleSheet(_BTN_GREY)
        cb.clicked.connect(self.close)
        btn.addWidget(cb)
        ob = QPushButton(t("k_ok"))
        ob.setStyleSheet(_BTN_OK)
        ob.clicked.connect(self._apply_and_close)
        btn.addWidget(ob)
        self.content_layout.addLayout(btn)

    # ─── 常规标签页 ───
    def _make_general_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(10)

        # 语言
        lg = QGroupBox(t("_k_settings_language"))
        ll = QVBoxLayout(lg)
        ll.setSpacing(6)
        cr = QHBoxLayout()
        cr.addWidget(QLabel(t("_k_settings_lang_label")))
        self._cur_lang = QLabel(_LANG_NAMES.get(self._orig_lang, self._orig_lang))
        self._cur_lang.setStyleSheet("color: #4fc3f7; font-weight: bold;")
        cr.addWidget(self._cur_lang)
        cr.addStretch()
        ll.addLayout(cr)
        sr = QHBoxLayout()
        sr.addWidget(QLabel(t("_k_settings_switch_lang")))
        self.lang_combo = QComboBox()
        for code, name in _LANG_NAMES.items():
            self.lang_combo.addItem(name, code)
        self.lang_combo.setCurrentIndex(1 if self._orig_lang == "en" else 0)
        sr.addWidget(self.lang_combo, 1)
        ll.addLayout(sr)
        l.addWidget(lg)

        # 进程隔离
        pg = QGroupBox(t("_k_settings_process"))
        pl = QVBoxLayout(pg)
        self.proc_check = QCheckBox(t("_k_settings_process_label"))
        self.proc_check.setChecked(self.main_window.CANVAS_PROCESS_MODE)
        pl.addWidget(self.proc_check)
        ph = QLabel(t("_k_settings_process_hint"))
        ph.setStyleSheet("color: #888; font-size: 10px; padding-left: 20px;")
        ph.setWordWrap(True)
        pl.addWidget(ph)
        l.addWidget(pg)

        l.addStretch()
        return w

    # ─── 快捷键标签页 ───
    def _make_shortcuts_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(6)
        l.setContentsMargins(4, 4, 4, 4)

        hint = QLabel(t("_k_settings_shortcut_hint"))
        hint.setStyleSheet("color: #888; font-size: 10px;")
        hint.setWordWrap(True)
        l.addWidget(hint)

        self._sc_table = QTableWidget(0, 3)
        self._sc_table.setHorizontalHeaderLabels(
            [t("_k_settings_sc_action"), t("_k_settings_sc_current"), t("_k_settings_sc_default")])
        self._sc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._sc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._sc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._sc_table.setColumnWidth(1, 120)
        self._sc_table.setColumnWidth(2, 120)
        self._sc_table.verticalHeader().setVisible(False)
        self._sc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._sc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._sc_table.cellDoubleClicked.connect(self._on_sc_dbl_click)
        l.addWidget(self._sc_table, 1)

        # 按钮
        rl = QHBoxLayout()
        rb = QPushButton(t("_k_settings_sc_reset_all"))
        rb.setStyleSheet(_BTN_SMALL)
        rb.clicked.connect(self._reset_all_sc)
        rl.addWidget(rb)
        rl.addStretch()
        l.addLayout(rl)

        self._populate_sc_table()
        return w

    def _populate_sc_table(self):
        mgr = self.main_window.shortcut_mgr
        self._sc_table.setRowCount(0)
        for sid, dk, cur, default in mgr.all_items():
            row = self._sc_table.rowCount()
            self._sc_table.insertRow(row)
            self._sc_table.setItem(row, 0, QTableWidgetItem(dk))
            changed = sid in self._shortcut_changes
            txt = self._shortcut_changes.get(sid, cur)
            if not txt:
                txt = "—"
            item = QTableWidgetItem(txt)
            if changed:
                item.setForeground(Qt.GlobalColor.yellow)
            self._sc_table.setItem(row, 1, item)
            def_txt = default if default else "—"
            self._sc_table.setItem(row, 2, QTableWidgetItem(def_txt))

    def _on_sc_dbl_click(self, row, col):
        sid = list(self.main_window.shortcut_mgr.all_items())[row][0]
        self._editing_row = row
        # 弹出按键捕获对话框
        dlg = ShortcutCaptureDialog(sid, self)
        if dlg.exec() == True and dlg._keystr is not None:
            self._shortcut_changes[sid] = dlg._keystr
            self._populate_sc_table()

    def _reset_all_sc(self):
        self._shortcut_changes.clear()
        self._populate_sc_table()

    # ─── 应用 ───
    def _apply_and_close(self):
        lang = self.lang_combo.currentData()
        proc_mode = self.proc_check.isChecked()
        lang_changed = (lang != self._orig_lang)
        proc_changed = (proc_mode != self.main_window.CANVAS_PROCESS_MODE)

        # 快捷键变更
        sc_changed = bool(self._shortcut_changes)
        if sc_changed:
            mgr = self.main_window.shortcut_mgr
            for sid, ks in self._shortcut_changes.items():
                mgr.set(sid, ks)
            mgr.save()
            mgr.apply_all(self.main_window)

        if lang_changed or proc_changed:
            if lang_changed:
                try: self.main_window.app_config.set("language", lang)
                except: pass
            if proc_changed:
                self.main_window.CANVAS_PROCESS_MODE = proc_mode
                try: self.main_window.app_config.set("process_mode", proc_mode)
                except: pass
            try: self.main_window.app_config.save()
            except: pass
            themed_message(self, t("_k_settings_restart_title"),
                t("_k_settings_restart_msg"), "info")
            self.close()
            self.main_window._restart_application()
        else:
            self.close()


# ─── 快捷键捕获弹出框 ───
class ShortcutCaptureDialog(FloatingPanel):
    """双击捕获按键（浮动窗口版本）"""

    def __init__(self, sid, parent=None):
        super().__init__(parent, title=t("_k_settings_sc_capture"))
        self._keystr = None
        
        self.resize(340, 140)
        self.setStyleSheet(_SET_STYLE)

        from ui.core.shortcut_manager import DEFAULTS
        self._sid = sid
        default = DEFAULTS.get(sid, ("",))[0]
        mgr = parent.main_window.shortcut_mgr
        cur = mgr.get(sid)

        info = QLabel(t("_k_settings_sc_capture_info").format(action=t(DEFAULTS[sid][1])))
        info.setStyleSheet("color: #ccc; font-size: 11px;")
        info.setWordWrap(True)
        self.content_layout.addWidget(info)

        self._display = QLabel(cur if cur else t("_k_settings_sc_empty"))
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setStyleSheet("color: #4fc3f7; font-size: 18px; font-weight: bold; padding: 10px; background: #1e1e1e; border-radius: 4px;")
        self.content_layout.addWidget(self._display)

        default_lbl = QLabel(t("_k_settings_sc_default_label") + (": " + default if default else ": —"))
        default_lbl.setStyleSheet("color: #888; font-size: 10px;")
        self.content_layout.addWidget(default_lbl)

        btn = QHBoxLayout()
        btn.addStretch()
        rb = QPushButton(t("_k_settings_sc_reset"))
        rb.setStyleSheet(_BTN_GREY)
        rb.clicked.connect(self._reset)
        btn.addWidget(rb)
        ob = QPushButton(t("k_ok"))
        ob.setStyleSheet(_BTN_OK)
        ob.clicked.connect(self.accept)
        btn.addWidget(ob)
        cb = QPushButton(t("k_cancel"))
        cb.setStyleSheet(_BTN_GREY)
        cb.clicked.connect(self.close)
        btn.addWidget(cb)
        self.content_layout.addLayout(btn)

    def _reset(self):
        self._keystr = ""
        self._display.setText(t("_k_settings_sc_empty"))

    def keyPressEvent(self, event):
        mods = int(event.modifiers().value)
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
            return super().keyPressEvent(event)
        parts = []
        if mods & Qt.KeyboardModifier.ControlModifier.value: parts.append("Ctrl")
        if mods & Qt.KeyboardModifier.ShiftModifier.value: parts.append("Shift")
        if mods & Qt.KeyboardModifier.AltModifier.value: parts.append("Alt")
        k = QKeySequence(key).toString()
        if k: parts.append(k)
        self._keystr = "+".join(parts) if parts else ""
        self._display.setText(self._keystr or t("_k_settings_sc_empty"))