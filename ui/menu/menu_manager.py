"""
BNOS 菜单管理器 - 使用统一 ActionRegistry
"""
from PyQt6.QtGui import QAction, QFont
from ui.core.i18n import t
from ui.core.actions import ActionFactory, ActionRegistry
from ui.core.actions.builtin_project_actions import register_project_actions
from ui.core.actions.builtin_node_actions import register_node_actions
from ui.core.actions.builtin_canvas_actions import register_canvas_actions
from ui.core.actions.builtin_view_actions import register_view_actions


def _shortcut(main_window, sid: str) -> str:
    """读取当前快捷键字符串"""
    if hasattr(main_window, 'shortcut_mgr') and main_window.shortcut_mgr:
        return main_window.shortcut_mgr.get(sid)
    from ui.core.shortcut_manager import DEFAULTS
    return DEFAULTS.get(sid, ("",))[0]


class MenuManager:
    """菜单管理器 — 使用统一 ActionRegistry"""

    @staticmethod
    def init_menu(main_window, menubar=None):
        if menubar is None:
            menubar = main_window.menuBar()
        sc = main_window.shortcut_mgr if hasattr(main_window, 'shortcut_mgr') else None
        actions = {}

        register_project_actions(main_window)
        register_node_actions(main_window)
        register_canvas_actions(main_window)
        register_view_actions(main_window)

        # ========== 文件菜单 ==========
        file_menu = ActionFactory.create_submenu(main_window, "k_menu_file", menubar=menubar)
        
        ActionFactory.create_action(main_window, "project.new", menu=file_menu)
        ActionFactory.create_action(main_window, "project.open", menu=file_menu)
        
        import_export_menu = ActionFactory.create_submenu(main_window, "k_import_export", parent_menu=file_menu)
        ActionFactory.create_action(main_window, "project.import_node", menu=import_export_menu)
        import_export_menu.addSeparator()
        ActionFactory.create_action(main_window, "project.export_node", menu=import_export_menu)
        ActionFactory.create_action(main_window, "project.export_project", menu=import_export_menu)
        
        file_menu.addSeparator()
        
        node_list_action = QAction(t("k_node_list_dock"), main_window)
        node_list_action.setCheckable(True)
        visibility = main_window.app_config.get('panel_visibility', {})
        is_visible = visibility.get('node_list_dock', visibility.get('node_list', False))
        node_list_action.setChecked(is_visible)
        node_list_action.setStatusTip(t("k_menu_toggle_nodes"))
        node_list_action.triggered.connect(main_window.toggle_node_list_panel)
        file_menu.addAction(node_list_action)
        main_window.toggle_nodes_action = node_list_action
        
        file_menu.addSeparator()
        
        ActionFactory.create_action(main_window, "view.color_settings", menu=file_menu)
        ActionFactory.create_action(main_window, "view.settings", menu=file_menu)
        
        file_menu.addSeparator()
        
        ActionFactory.create_action(main_window, "project.restart", menu=file_menu)
        ActionFactory.create_action(main_window, "project.exit", menu=file_menu)

        # ========== 编辑菜单 ==========
        edit_menu = ActionFactory.create_submenu(main_window, "k_menu_edit", menubar=menubar)
        
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
        
        ActionFactory.create_action(main_window, "node.refresh", menu=edit_menu)
        ActionFactory.create_action(main_window, "node.mount", menu=edit_menu)
        
        edit_menu.addSeparator()
        
        ActionFactory.create_action(main_window, "canvas.clear_connections", menu=edit_menu)
        
        edit_menu.addSeparator()
        
        ActionFactory.create_action(main_window, "node.start", menu=edit_menu)
        ActionFactory.create_action(main_window, "node.stop", menu=edit_menu)
        
        edit_menu.addSeparator()
        
        ActionFactory.create_action(main_window, "view.toggle_node_monitor", menu=edit_menu)
        ActionFactory.create_action(main_window, "view.toggle_node_list", menu=edit_menu)
        ActionFactory.create_action(main_window, "view.toggle_resource_monitor", menu=edit_menu)

        # ========== 工具菜单 ==========
        tools_menu = ActionFactory.create_submenu(main_window, "k_menu_tools", menubar=menubar)
        
        ActionFactory.create_action(main_window, "view.node_monitor", menu=tools_menu)
        ActionFactory.create_action(main_window, "view.resource_monitor", menu=tools_menu)
        ActionFactory.create_action(main_window, "view.node_list_floating", menu=tools_menu)
        
        tools_menu.addSeparator()
        
        # 添加终端菜单项
        terminal_action = QAction(t("k_view_toggle_terminal"), main_window)
        terminal_action.setCheckable(True)
        # 从配置中读取初始状态
        visibility = main_window.app_config.get('panel_visibility', {})
        is_visible = visibility.get('terminal_dock', False)
        terminal_action.setChecked(is_visible)
        terminal_action.setStatusTip(t("k_menu_toggle_terminal"))
        terminal_action.triggered.connect(main_window.toggle_terminal)
        tools_menu.addAction(terminal_action)
        main_window.toggle_terminal_action = terminal_action

        # ========== 帮助菜单 ==========
        help_menu = ActionFactory.create_submenu(main_window, "k_menu_help", menubar=menubar)
        
        ActionFactory.create_action(main_window, "view.about", menu=help_menu)

        main_window._shortcut_actions = actions

    @staticmethod
    def show_about(main_window):
        from ui.core.utils.dialog_utils import themed_message
        themed_message(main_window, t("k_title_about"), t("_k_about_text"), "info")
