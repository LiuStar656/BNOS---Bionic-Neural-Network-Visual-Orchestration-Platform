"""
BNOS 菜单管理器 - 纯菜单栏设计（无工具栏）
负责初始化和管理主窗口的菜单栏
"""
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt


class MenuManager:
    """菜单管理器 - 将所有功能整合到菜单栏"""
    
    @staticmethod
    def init_menu(main_window):
        """初始化菜单栏
        
        Args:
            main_window: BNOSMainWindow实例
        """
        menubar = main_window.menuBar()
        
        # ========== 文件菜单 ==========
        file_menu = menubar.addMenu("文件(&F)")
        
        # 新建项目
        new_project_action = QAction("新建项目", main_window)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.setStatusTip("创建新的神经网络项目")
        new_project_action.triggered.connect(main_window.new_project)
        file_menu.addAction(new_project_action)
        
        # 打开项目
        open_project_action = QAction("打开项目", main_window)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.setStatusTip("打开现有的神经网络项目")
        open_project_action.triggered.connect(main_window.open_project)
        file_menu.addAction(open_project_action)
        
        file_menu.addSeparator()
        
        # 节点列表开关
        toggle_nodes_action = QAction("节点列表", main_window)
        toggle_nodes_action.setCheckable(True)
        toggle_nodes_action.setChecked(True)
        toggle_nodes_action.setStatusTip("显示/隐藏节点列表面板")
        toggle_nodes_action.triggered.connect(main_window.toggle_node_list_panel)
        file_menu.addAction(toggle_nodes_action)
        main_window.toggle_nodes_action = toggle_nodes_action
        
        file_menu.addSeparator()
        
        # 颜色设置
        color_settings_action = QAction("颜色设置", main_window)
        color_settings_action.setStatusTip("自定义画布和节点颜色")
        color_settings_action.triggered.connect(main_window.open_color_settings)
        file_menu.addAction(color_settings_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("退出", main_window)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("退出应用程序")
        exit_action.triggered.connect(main_window.close)
        file_menu.addAction(exit_action)
        
        # ========== 编辑菜单 ==========
        edit_menu = menubar.addMenu("编辑(&E)")
        
        new_node_menu = edit_menu.addMenu("新建节点")
        
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
        refresh_action = QAction("刷新节点", main_window)
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip("刷新节点列表")
        refresh_action.triggered.connect(main_window.refresh_nodes)
        edit_menu.addAction(refresh_action)
        
        # 清空连线
        clear_connections_action = QAction("清空连线", main_window)
        clear_connections_action.setStatusTip("清空所有节点连线")
        clear_connections_action.triggered.connect(main_window.clear_connections)
        edit_menu.addAction(clear_connections_action)
        
        edit_menu.addSeparator()
        
        # 启动节点
        start_node_action = QAction("启动节点", main_window)
        start_node_action.setShortcut("Ctrl+Shift+S")
        start_node_action.setStatusTip("启动选中的节点")
        start_node_action.triggered.connect(main_window.start_selected_node)
        edit_menu.addAction(start_node_action)
        
        # 停止节点
        stop_node_action = QAction("停止节点", main_window)
        stop_node_action.setShortcut("Ctrl+Shift+X")
        stop_node_action.setStatusTip("停止选中的节点")
        stop_node_action.triggered.connect(main_window.stop_selected_node)
        edit_menu.addAction(stop_node_action)
        
        # ========== 帮助菜单 ==========
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于", main_window)
        about_action.setStatusTip("显示关于信息")
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
            main_window.show_toast("请先打开或新建项目", "warning")
            return
        
        # 弹出对话框输入节点名称
        node_name, ok = QInputDialog.getText(
            main_window, "新建节点", 
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
            print(f"未注册的语言创建器: {lang_key}")
            print(f"   当前支持: {main_window.node_creator.get_supported_languages()}")
            return
        
        # 启动异步创建流程
        main_window._start_async_node_creation(node_name, lang_key, language)
    
    @staticmethod
    def show_about(main_window):
        """显示关于对话框
        
        Args:
            main_window: BNOSMainWindow实例
        """
        QMessageBox.about(main_window, "关于 BNOS", 
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
