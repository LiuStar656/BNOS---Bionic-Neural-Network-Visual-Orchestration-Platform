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

        file_menu.addSeparator()

        # 退出
        exit_action = QAction(t("k_menu_exit"), main_window)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip(t("k_menu_exit_desc"))
        exit_action.triggered.connect(main_window.close)
        file_menu.addAction(exit_action)

        # ========== 编辑菜单 ==========
        edit_menu = menubar.addMenu(t("k_menu_edit"))

        new_node_menu = edit_menu.addMenu(t("k_node_create"))

        # 为每种语言添加子菜单项
        languages = ["Python", "Node.js", "Go", "Java", "C++", "Rust", "Shell"]
        for lang in languages:
            action = QAction(lang, main_window)
            action.setStatusTip(f"创建新的 {lang} 节点")
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
        start_node_action.setStatusTip("启动选中的节点")
        start_node_action.triggered.connect(main_window.start_selected_node)
        edit_menu.addAction(start_node_action)

        # 停止节点
        stop_node_action = QAction(t("k_node_stop"), main_window)
        stop_node_action.setShortcut("Ctrl+Shift+X")
        stop_node_action.setStatusTip("停止选中的节点")
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
    def create_new_node_with_language(main_window, language):
        """使用指定语言创建新节点
        
        Args:
            main_window: BNOSMainWindow实例
            language: 编程语言名称
        """
        if not main_window.current_project_path:
            main_window.show_toast(t("k_project_no_project"), "warning")
            return

        # 弹出对话框输入节点名称
        node_name, ok = QInputDialog.getText(
            main_window, t("k_node_create"),
            f"请输入节点名称（{language}）:",
            QLineEdit.EchoMode.Normal
        )
        
        if not ok or not node_name:
            return
        
        # 映射语言标识
        lang_map = {
            "Python": "python",
            "Node.js": "nodejs",
            "Go": "go",
            "Java": "java",
            "C++": "cpp",
            "Rust": "rust",
            "Shell": "shell"
        }
        
        lang_key = lang_map.get(language, language.lower())
        
        # 检查是否支持该语言
        if not main_window.node_creator.has_creator(lang_key):
            main_window.show_toast(f"暂不支持创建 {language} 节点", "warning")
            logger.warning("未注册的语言创建器: %s", lang_key)
            logger.info("   当前支持: %s", main_window.node_creator.get_supported_languages())
            return
        
        # 启动异步创建流程
        main_window._start_async_node_creation(node_name, lang_key, language)
    
    @staticmethod
    def show_about(main_window):
        """显示关于对话框
        
        Args:
            main_window: BNOSMainWindow实例
        """
        QMessageBox.about(main_window, t("k_title_about"), 
            "BNOS - Bionic Neural Network Program Operating System\n\n"
            "版本: 1.0.0\n"
            "仿生神经网络程序操作系统\n\n"
            "一款基于 PyQt6 的纯桌面端可视化节点编排平台。\n\n"
            "核心特性:\n"
            "• 项目管理：仿 VSCode 模式，打开文件夹即项目\n"
            "• 可视化编排：无限平移画布，拖拽节点，智能连线\n"
            "• 多语言支持：Python、Node.js、Go、Java、C++、Rust、Shell\n"
            "• 环境隔离：每个节点拥有独立虚拟环境\n"
            "• 配置编辑：图形化编辑 config.json\n"
            "• 实时监控：状态指示灯，实时日志查看\n"
            "• 状态持久化：自动保存布局，重启完整恢复"
        )
