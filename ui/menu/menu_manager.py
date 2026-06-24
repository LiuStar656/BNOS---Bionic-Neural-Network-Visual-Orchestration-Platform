"""
BNOS 菜单管理器 — 所有菜单项均通过 ActionRegistry + ActionFactory 构建
"""
from ui.core.i18n import t
from ui.core.actions import ActionFactory
from ui.core.actions.builtin_project_actions import register_project_actions
from ui.core.actions.builtin_node_actions import register_node_actions
from ui.core.actions.builtin_canvas_actions import register_canvas_actions
from ui.core.actions.builtin_view_actions import register_view_actions


class MenuManager:
    """菜单管理器 — 统一使用 ActionRegistry + ActionFactory"""

    @staticmethod
    def init_menu(main_window, menubar=None):
        if menubar is None:
            menubar = main_window.menuBar()

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

        ActionFactory.create_action(main_window, "view.color_settings", menu=file_menu)
        ActionFactory.create_action(main_window, "view.settings", menu=file_menu)

        file_menu.addSeparator()

        ActionFactory.create_action(main_window, "project.restart", menu=file_menu)
        ActionFactory.create_action(main_window, "project.exit", menu=file_menu)

        # ========== 编辑菜单 ==========
        edit_menu = ActionFactory.create_submenu(main_window, "k_menu_edit", menubar=menubar)

        new_node_menu = edit_menu.addMenu(t("k_node_create"))
        _lang_list = [
            ("k_lang_python", "Python"),
            ("k_lang_rust", "Rust"),
            ("k_lang_nodejs", "Node.js (开发中)"),
            ("k_lang_go", "Go (开发中)"),
            ("k_lang_java", "Java (开发中)"),
            ("k_lang_cpp", "C++ (开发中)"),
            ("k_lang_shell", "Shell (开发中)"),
        ]
        for i18n_key, lang_name in _lang_list:
            ActionFactory.create_action(main_window, f"canvas.new_node.{lang_name}", menu=new_node_menu)

        edit_menu.addSeparator()

        ActionFactory.create_action(main_window, "node.refresh", menu=edit_menu)
        ActionFactory.create_action(main_window, "node.mount", menu=edit_menu)

        edit_menu.addSeparator()

        ActionFactory.create_action(main_window, "canvas.clear_connections", menu=edit_menu)

        edit_menu.addSeparator()

        ActionFactory.create_action(main_window, "node.start", menu=edit_menu)
        ActionFactory.create_action(main_window, "node.stop", menu=edit_menu)

        # ========== 工具菜单 ==========
        tools_menu = ActionFactory.create_submenu(main_window, "k_menu_tools", menubar=menubar)

        ActionFactory.create_action(main_window, "view.history_panel", menu=tools_menu)

        tools_menu.addSeparator()

        ActionFactory.create_action(main_window, "view.performance_panel", menu=tools_menu)
        ActionFactory.create_action(main_window, "view.template_selector", menu=tools_menu)

        tools_menu.addSeparator()

        # 终端 — ActionFactory，保留 setCheckable + 状态持久化（canvas_host 引用了 toggle_terminal_action）
        terminal_action = ActionFactory.create_action(main_window, "view.toggle_terminal", menu=tools_menu)
        if terminal_action:
            main_window.toggle_terminal_action = terminal_action

        tools_menu.addSeparator()

        ActionFactory.create_action(main_window, "view.toggle_node_list", menu=tools_menu)
        ActionFactory.create_action(main_window, "view.toggle_node_monitor", menu=tools_menu)
        ActionFactory.create_action(main_window, "view.toggle_resource_monitor", menu=tools_menu)

        # ========== 帮助菜单 ==========
        help_menu = ActionFactory.create_submenu(main_window, "k_menu_help", menubar=menubar)

        ActionFactory.create_action(main_window, "view.changelog", menu=help_menu)
        help_menu.addSeparator()
        ActionFactory.create_action(main_window, "view.about", menu=help_menu)

    @staticmethod
    def show_about(main_window):
        from ui.core.utils.dialog_utils import themed_message
        themed_message(main_window, t("k_title_about"), t("_k_about_text"), "info")
