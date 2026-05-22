"""
BNOS 菜单管理器 - 纯菜单栏设计（无工具栏）
负责初始化和管理主窗口的菜单栏
"""
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from ui.core.logger import logger
from ui.core.i18n import t


class MenuManager:
    """菜单管理器 - 将所有功能整合到菜单栏"""
    
    @staticmethod
    def init_menu(main_window, menubar=None):
        """初始化菜单栏
        
        Args:
            main_window: BNOSMainWindow实例
            menubar: 要添加菜单的 QMenuBar（None 则使用窗口默认）
        """
        if menubar is None:
            menubar = main_window.menuBar()
        
        # ========== 文件菜单 ==========
        file_menu = menubar.addMenu(t("k_menu_file"))

        # 新建项目
        new_project_action = QAction(t("k_project_new"), main_window)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.setStatusTip(t("k_node_create_desc"))
        new_project_action.triggered.connect(main_window.new_project)
        file_menu.addAction(new_project_action)

        # 打开项目
        open_project_action = QAction(t("k_project_open"), main_window)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.setStatusTip(t("k_menu_open_project_desc"))
        open_project_action.triggered.connect(main_window.open_project)
        file_menu.addAction(open_project_action)

        file_menu.addSeparator()

        # 节点列表开关
        toggle_nodes_action = QAction(t("k_node_list"), main_window)
        toggle_nodes_action.setCheckable(True)
        toggle_nodes_action.setChecked(True)
        toggle_nodes_action.setStatusTip(t("k_menu_toggle_nodes"))
        toggle_nodes_action.triggered.connect(main_window.toggle_node_list_panel)
        file_menu.addAction(toggle_nodes_action)
        main_window.toggle_nodes_action = toggle_nodes_action

        file_menu.addSeparator()

        # 颜色设置
        color_settings_action = QAction(t("k_color_settings"), main_window)
        color_settings_action.setStatusTip(t("k_color_settings_desc"))
        color_settings_action.triggered.connect(main_window.open_color_settings)
        file_menu.addAction(color_settings_action)

        # 设置
        settings_action = QAction(t("_k_settings_title"), main_window)
        settings_action.setShortcut("Ctrl+,")
        settings_action.setStatusTip(t("_k_settings_title"))
        settings_action.triggered.connect(main_window.open_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        # 重启
        restart_action = QAction(t("k_menu_restart"), main_window)
        restart_action.setShortcut("Ctrl+R")
        restart_action.setStatusTip(t("k_menu_restart_desc"))
        restart_action.triggered.connect(main_window._restart_application)
        file_menu.addAction(restart_action)

        # 退出
        exit_action = QAction(t("k_menu_exit"), main_window)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip(t("k_menu_exit_desc"))
        exit_action.triggered.connect(main_window.close)
        file_menu.addAction(exit_action)

        # ========== 编辑菜单 ==========
        edit_menu = menubar.addMenu(t("k_menu_edit"))

        new_node_menu = edit_menu.addMenu(t("k_node_create"))

        language_keys = [
            ("k_lang_python", "Python"),
            ("k_lang_rust", "Rust"),
            ("k_lang_nodejs", "Node.js"),
            ("k_lang_go", "Go"),
            ("k_lang_java", "Java"),
            ("k_lang_cpp", "C++"),
            ("k_lang_shell", "Shell"),
        ]
        for k, lang in language_keys:
            label = t(k)
            action = QAction(label, main_window)
            action.setStatusTip(t("k_node_enter_name").replace("{lang}", lang))
            action.triggered.connect(
                lambda checked=None, language=lang: main_window.create_new_node_with_language(language)
            )
            new_node_menu.addAction(action)

        edit_menu.addSeparator()

        # 刷新节点
        refresh_action = QAction(t("k_node_refresh"), main_window)
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip(t("k_node_refresh_list"))
        refresh_action.triggered.connect(main_window.refresh_nodes)
        edit_menu.addAction(refresh_action)

        # 挂载外部节点
        mount_action = QAction(t("k_node_mount"), main_window)
        mount_action.setShortcut("Ctrl+Shift+O")
        mount_action.setStatusTip(t("k_node_mount_help"))
        mount_action.triggered.connect(main_window.mount_external_node)
        edit_menu.addAction(mount_action)

        edit_menu.addSeparator()

        # 清空连线
        clear_connections_action = QAction(t("k_canvas_clear_connections"), main_window)
        clear_connections_action.setStatusTip(t("k_canvas_clear_connections_desc"))
        clear_connections_action.triggered.connect(main_window.clear_connections)
        edit_menu.addAction(clear_connections_action)

        edit_menu.addSeparator()

        # 启动节点
        start_node_action = QAction(t("k_node_start"), main_window)
        start_node_action.setShortcut("Ctrl+Shift+S")
        start_node_action.setStatusTip(t("_k_start_node_tip"))
        start_node_action.triggered.connect(main_window.start_selected_node)
        edit_menu.addAction(start_node_action)

        # 停止节点
        stop_node_action = QAction(t("k_node_stop"), main_window)
        stop_node_action.setShortcut("Ctrl+Shift+X")
        stop_node_action.setStatusTip(t("_k_stop_node_tip"))
        stop_node_action.triggered.connect(main_window.stop_selected_node)
        edit_menu.addAction(stop_node_action)

        # ========== 工具菜单 ==========
        tools_menu = menubar.addMenu(t("k_menu_tools"))

        monitor_action = QAction(t("k_node_monitor"), main_window)
        monitor_action.setShortcut("Ctrl+Shift+M")
        monitor_action.setStatusTip(t("k_menu_monitor"))
        monitor_action.triggered.connect(main_window.show_node_monitor)
        tools_menu.addAction(monitor_action)

        # ========== 帮助菜单 ==========
        help_menu = menubar.addMenu(t("k_menu_help"))

        about_action = QAction(t("k_menu_about"), main_window)
        about_action.setStatusTip(t("k_menu_about_desc"))
        about_action.triggered.connect(main_window.show_about)
        help_menu.addAction(about_action)
    
    @staticmethod
    def show_about(main_window):
        """显示关于对话框
        
        Args:
            main_window: BNOSMainWindow实例
        """
        from ui.core.utils.dialog_utils import themed_message
        themed_message(main_window, t("k_title_about"), t("_k_about_text"), "info")
