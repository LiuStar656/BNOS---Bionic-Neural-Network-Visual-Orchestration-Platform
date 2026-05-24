"""
BNOS 菜单管理器 - 快捷键由 ShortcutManager 统一管理
"""
from PyQt6.QtGui import QAction, QFont
from ui.core.i18n import t
from ui.icons import get_icon, get_icon_font


def _shortcut(main_window, sid: str) -> str:
    """读取当前快捷键字符串"""
    if hasattr(main_window, 'shortcut_mgr') and main_window.shortcut_mgr:
        return main_window.shortcut_mgr.get(sid)
    from ui.core.shortcut_manager import DEFAULTS
    return DEFAULTS.get(sid, ("",))[0]


class MenuManager:
    """菜单管理器 — 集中创建所有菜单"""

    @staticmethod
    def init_menu(main_window, menubar=None):
        if menubar is None:
            menubar = main_window.menuBar()
        sc = main_window.shortcut_mgr if hasattr(main_window, 'shortcut_mgr') else None
        actions = {}  # sid → QAction 注册表
        


        # ========== 文件 ==========
        file_menu = menubar.addMenu(t("k_menu_file"))

        a = QAction(t("k_project_new"), main_window)
        a.setShortcut(_shortcut(main_window, "new_project"))
        a.setStatusTip(t("k_node_create_desc"))
        a.triggered.connect(main_window.new_project)
        file_menu.addAction(a)
        actions["new_project"] = a

        a = QAction(t("k_project_open"), main_window)
        a.setShortcut(_shortcut(main_window, "open_project"))
        a.setStatusTip(t("k_menu_open_project_desc"))
        a.triggered.connect(main_window.open_project)
        file_menu.addAction(a)
        actions["open_project"] = a

        file_menu.addSeparator()

        a = QAction(t("k_node_list_dock"), main_window)
        a.setCheckable(True)
        # 从配置读取初始状态，而不是硬编码为 True
        visibility = main_window.app_config.get('panel_visibility', {})
        is_visible = visibility.get('node_list_dock', visibility.get('node_list', False))
        a.setChecked(is_visible)
        a.setStatusTip(t("k_menu_toggle_nodes"))
        a.triggered.connect(main_window.toggle_node_list_panel)
        file_menu.addAction(a)
        main_window.toggle_nodes_action = a

        file_menu.addSeparator()

        a = QAction(t("k_color_settings"), main_window)
        a.setStatusTip(t("k_color_settings_desc"))
        a.triggered.connect(main_window.open_color_settings)
        file_menu.addAction(a)

        a = QAction(t("_k_settings_title"), main_window)
        a.setShortcut(_shortcut(main_window, "settings"))
        a.setStatusTip(t("_k_settings_title"))
        a.triggered.connect(main_window.open_settings)
        file_menu.addAction(a)
        actions["settings"] = a

        file_menu.addSeparator()

        a = QAction(t("k_menu_restart"), main_window)
        a.setShortcut(_shortcut(main_window, "restart"))
        a.setStatusTip(t("k_menu_restart_desc"))
        a.triggered.connect(main_window._restart_application)
        file_menu.addAction(a)
        actions["restart"] = a

        a = QAction(t("k_menu_exit"), main_window)
        a.setShortcut(_shortcut(main_window, "exit_app"))
        a.setStatusTip(t("k_menu_exit_desc"))
        a.triggered.connect(main_window.close)
        file_menu.addAction(a)
        actions["exit_app"] = a

        # ========== 编辑 ==========
        edit_menu = menubar.addMenu(t("k_menu_edit"))

        new_node_menu = edit_menu.addMenu(t("k_node_create"))
        for k, lang in [("k_lang_python","Python"),("k_lang_rust","Rust"),
                         ("k_lang_nodejs","Node.js"),("k_lang_go","Go"),
                         ("k_lang_java","Java"),("k_lang_cpp","C++"),
                         ("k_lang_shell","Shell")]:
            a = QAction(t(k), main_window)
            a.setStatusTip(t("k_node_enter_name").replace("{lang}", lang))
            a.triggered.connect(lambda chk=None, l=lang: main_window.create_new_node_with_language(l))
            new_node_menu.addAction(a)

        edit_menu.addSeparator()

        a = QAction(t("k_node_refresh"), main_window)
        a.setShortcut(_shortcut(main_window, "refresh_nodes"))
        a.setStatusTip(t("k_node_refresh_list"))
        a.triggered.connect(main_window.refresh_nodes)
        edit_menu.addAction(a)
        actions["refresh_nodes"] = a

        a = QAction(t("k_node_mount"), main_window)
        a.setShortcut(_shortcut(main_window, "mount_external"))
        a.setStatusTip(t("k_node_mount_help"))
        a.triggered.connect(main_window.mount_external_node)
        edit_menu.addAction(a)
        actions["mount_external"] = a

        edit_menu.addSeparator()

        a = QAction(t("k_canvas_clear_connections"), main_window)
        a.setShortcut(_shortcut(main_window, "clear_connections"))
        a.setStatusTip(t("k_canvas_clear_connections_desc"))
        a.triggered.connect(main_window.clear_connections)
        edit_menu.addAction(a)
        actions["clear_connections"] = a

        edit_menu.addSeparator()

        a = QAction(t("k_node_start"), main_window)
        a.setShortcut(_shortcut(main_window, "start_node"))
        a.setStatusTip(t("_k_start_node_tip"))
        a.triggered.connect(main_window.start_selected_node)
        edit_menu.addAction(a)
        actions["start_node"] = a

        a = QAction(t("k_node_stop"), main_window)
        a.setShortcut(_shortcut(main_window, "stop_node"))
        a.setStatusTip(t("_k_stop_node_tip"))
        a.triggered.connect(main_window.stop_selected_node)
        edit_menu.addAction(a)
        actions["stop_node"] = a

        edit_menu.addSeparator()

        a = QAction(t("k_node_monitor_dock"), main_window)
        a.setStatusTip(t("k_node_monitor_dock_desc"))
        a.triggered.connect(main_window.show_node_monitor_dock)
        edit_menu.addAction(a)
        actions["node_monitor_dock"] = a

        a = QAction(t("k_node_list_dock"), main_window)
        a.setStatusTip(t("k_menu_toggle_nodes"))
        a.triggered.connect(lambda: main_window.toggle_node_list_panel(True))
        edit_menu.addAction(a)
        actions["node_list_dock"] = a

        a = QAction(t("k_resource_monitor_dock"), main_window)
        a.setStatusTip(t("k_resource_monitor_desc"))
        a.triggered.connect(main_window.show_resource_monitor_dock)
        edit_menu.addAction(a)
        actions["resource_monitor_dock"] = a

        # ========== 工具 ==========
        tools_menu = menubar.addMenu(t("k_menu_tools"))

        a = QAction(t("k_node_monitor"), main_window)
        a.setShortcut(_shortcut(main_window, "node_monitor"))
        a.setStatusTip(t("k_menu_monitor"))
        a.triggered.connect(main_window.show_node_monitor)
        tools_menu.addAction(a)
        actions["node_monitor"] = a

        a = QAction(t("k_resource_monitor"), main_window)
        a.setShortcut(_shortcut(main_window, "resource_monitor"))
        a.setStatusTip(t("k_resource_monitor_desc"))
        a.triggered.connect(main_window.show_resource_monitor)
        tools_menu.addAction(a)
        actions["resource_monitor"] = a

        a = QAction(t("k_node_list"), main_window)
        a.setStatusTip(t("k_menu_toggle_nodes"))
        a.triggered.connect(main_window.show_node_list_floating)
        tools_menu.addAction(a)
        actions["node_list_floating"] = a

        # ========== 帮助 ==========
        help_menu = menubar.addMenu(t("k_menu_help"))

        a = QAction(t("k_menu_about"), main_window)
        a.setStatusTip(t("k_menu_about_desc"))
        a.triggered.connect(main_window.show_about)
        help_menu.addAction(a)

        # 注册到主窗口以便后续热更新
        main_window._shortcut_actions = actions

    @staticmethod
    def show_about(main_window):
        from ui.core.utils.dialog_utils import themed_message
        themed_message(main_window, t("k_title_about"), t("_k_about_text"), "info")