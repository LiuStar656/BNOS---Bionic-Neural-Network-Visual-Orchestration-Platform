"""
全局快捷键管理器 — 集中定义、持久化、统一应用
"""
from PyQt6.QtGui import QKeySequence

# 默认快捷键定义: id → (default_keystr, i18n_display_key)
DEFAULTS = {
    "new_project":     ("Ctrl+N",        "k_project_new"),
    "open_project":    ("Ctrl+O",        "k_project_open"),
    "settings":        ("Ctrl+,",        "_k_settings_title"),
    "restart":         ("Ctrl+R",        "k_menu_restart"),
    "exit_app":        ("Ctrl+Q",        "k_menu_exit"),
    "refresh_nodes":   ("F5",            "k_node_refresh"),
    "mount_external":  ("Ctrl+Shift+O",  "k_node_mount"),
    "clear_connections":("",             "k_canvas_clear_connections"),
    "start_node":      ("Ctrl+Shift+S",  "k_node_start"),
    "stop_node":       ("Ctrl+Shift+X",  "k_node_stop"),
    "node_monitor":    ("Ctrl+Shift+M",  "k_node_monitor"),
    "resource_monitor":("Ctrl+Shift+R",  "k_resource_monitor"),
    "new_canvas_tab":  ("Ctrl+T",        "k_new_canvas_tab"),
}

# 需要 QAction.setShortcut(hotkey) 处理空快捷键
EMPTY_AS_DISABLED = True


class ShortcutManager:
    """快捷键注册表 — 从 app_config 加载/保存，运行时 string→QKeySequence"""

    def __init__(self, app_config):
        self._cfg = app_config
        self._overrides = self._cfg.get("shortcuts", {})

    def get(self, sid: str) -> str:
        """返回当前快捷键字符串（如 Ctrl+N），优先级: 用户覆盖 > 默认"""
        return self._overrides.get(sid) or DEFAULTS[sid][0]

    def get_qkey(self, sid: str) -> QKeySequence:
        return QKeySequence(self.get(sid))

    def set(self, sid: str, keystr: str):
        if sid not in DEFAULTS:
            raise KeyError(sid)
        self._overrides[sid] = keystr

    def reset(self, sid: str = None):
        if sid:
            self._overrides.pop(sid, None)
        else:
            self._overrides.clear()

    def save(self):
        self._cfg.set("shortcuts", self._overrides)
        self._cfg.save()

    def all_items(self):
        """返回 [(sid, display_key, current_str, default_str)]"""
        from ui.core.i18n import t
        for sid, (default, dk) in DEFAULTS.items():
            yield (sid, t(dk), self.get(sid), default)

    def apply_all(self, main_window):
        """将当前快捷键应用到主窗口所有已注册 QAction"""
        # 重新加载菜单以应用新快捷键
        from ui.menu.menu_manager import MenuManager
        bar = main_window._inline_menubar
        bar.clear()
        MenuManager.init_menu(main_window, bar)