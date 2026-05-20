"""
BNOS 菜单栏重构测试程序
测试将工具栏功能整合到菜单栏的设计
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QLabel, QMenuBar, QMenu, QMessageBox,
    QInputDialog, QLineEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction


class TestMenuBarWindow(QMainWindow):
    """测试菜单栏窗口"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化UI
        self.init_ui()
        self.init_menu()
        
        # 设置窗口属性
        self.setWindowTitle("BNOS 菜单栏测试")
        self.setGeometry(100, 100, 800, 600)
        
    def init_ui(self):
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # 显示区域
        info_label = QLabel("菜单栏功能测试区域\n\n请测试各个菜单项的功能")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setFont(QFont("Arial", 14))
        layout.addWidget(info_label)
        
        # 状态显示
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.status_label)
        
    def init_menu(self):
        """初始化菜单栏 - 新的设计方案"""
        menubar = self.menuBar()
        
        # ========== 文件菜单 ==========
        file_menu = menubar.addMenu("文件(&F)")
        
        # 新建项目
        new_project_action = QAction("📁 新建项目", self)
        new_project_action.setShortcut("Ctrl+N")
        new_project_action.setStatusTip("创建新的神经网络项目")
        new_project_action.triggered.connect(self.test_new_project)
        file_menu.addAction(new_project_action)
        
        # 打开项目
        open_project_action = QAction("📂 打开项目", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.setStatusTip("打开现有的神经网络项目")
        open_project_action.triggered.connect(self.test_open_project)
        file_menu.addAction(open_project_action)
        
        file_menu.addSeparator()
        
        # 节点列表开关
        toggle_nodes_action = QAction("📋 节点列表", self)
        toggle_nodes_action.setCheckable(True)
        toggle_nodes_action.setChecked(True)
        toggle_nodes_action.setStatusTip("显示/隐藏节点列表面板")
        toggle_nodes_action.triggered.connect(self.test_toggle_node_list)
        file_menu.addAction(toggle_nodes_action)
        
        file_menu.addSeparator()
        
        # 颜色设置
        color_settings_action = QAction("🎨 颜色设置", self)
        color_settings_action.setStatusTip("自定义画布和节点颜色")
        color_settings_action.triggered.connect(self.test_color_settings)
        file_menu.addAction(color_settings_action)
        
        file_menu.addSeparator()
        
        # 退出
        exit_action = QAction("❌ 退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("退出应用程序")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # ========== 编辑菜单 ==========
        edit_menu = menubar.addMenu("编辑(&E)")
        
        # 新建节点子菜单
        new_node_menu = edit_menu.addMenu("➕ 新建节点")
        
        # 为每种语言添加子菜单项
        languages = ["Python", "Node.js", "Go", "Java", "C++", "Rust", "Shell"]
        for lang in languages:
            action = QAction(lang, self)
            action.setStatusTip(f"创建新的 {lang} 节点")
            action.triggered.connect(lambda checked, l=lang: self.test_create_node(l))
            new_node_menu.addAction(action)
        
        edit_menu.addSeparator()
        
        # 刷新节点
        refresh_action = QAction("🔄 刷新节点", self)
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip("刷新节点列表")
        refresh_action.triggered.connect(self.test_refresh_nodes)
        edit_menu.addAction(refresh_action)
        
        # 清空连线
        clear_connections_action = QAction("🗑️ 清空连线", self)
        clear_connections_action.setStatusTip("清空所有节点连线")
        clear_connections_action.triggered.connect(self.test_clear_connections)
        edit_menu.addAction(clear_connections_action)
        
        edit_menu.addSeparator()
        
        # 启动节点
        start_node_action = QAction("▶️ 启动节点", self)
        start_node_action.setShortcut("Ctrl+Shift+S")
        start_node_action.setStatusTip("启动选中的节点")
        start_node_action.triggered.connect(self.test_start_node)
        edit_menu.addAction(start_node_action)
        
        # 停止节点
        stop_node_action = QAction("⏹️ 停止节点", self)
        stop_node_action.setShortcut("Ctrl+Shift+X")
        stop_node_action.setStatusTip("停止选中的节点")
        stop_node_action.triggered.connect(self.test_stop_node)
        edit_menu.addAction(stop_node_action)
        
        # ========== 帮助菜单 ==========
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = help_menu.addAction("ℹ️ 关于")
        about_action.setStatusTip("显示关于信息")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def update_status(self, message):
        """更新状态显示"""
        self.status_label.setText(message)
        print(f"[状态] {message}")
    
    # ========== 测试方法 ==========
    
    def test_new_project(self):
        """测试新建项目"""
        self.update_status("✅ 触发：新建项目")
        QMessageBox.information(self, "测试", "新建项目功能已触发")
    
    def test_open_project(self):
        """测试打开项目"""
        self.update_status("✅ 触发：打开项目")
        QMessageBox.information(self, "测试", "打开项目功能已触发")
    
    def test_toggle_node_list(self, checked):
        """测试节点列表开关"""
        status = "显示" if checked else "隐藏"
        self.update_status(f"✅ 触发：节点列表{status}")
        QMessageBox.information(self, "测试", f"节点列表面板已{status}")
    
    def test_color_settings(self):
        """测试颜色设置"""
        self.update_status("✅ 触发：颜色设置")
        QMessageBox.information(self, "测试", "颜色设置对话框应打开")
    
    def test_create_node(self, language):
        """测试创建节点"""
        self.update_status(f"✅ 触发：创建 {language} 节点")
        
        # 模拟输入节点名称
        node_name, ok = QInputDialog.getText(
            self, "新建节点", 
            f"请输入节点名称（{language}）:",
            QLineEdit.EchoMode.Normal
        )
        
        if ok and node_name:
            QMessageBox.information(self, "测试", f"准备创建 {language} 节点: {node_name}")
        else:
            self.update_status("❌ 取消创建节点")
    
    def test_refresh_nodes(self):
        """测试刷新节点"""
        self.update_status("✅ 触发：刷新节点")
        QMessageBox.information(self, "测试", "节点列表已刷新")
    
    def test_clear_connections(self):
        """测试清空连线"""
        self.update_status("✅ 触发：清空连线")
        reply = QMessageBox.question(
            self, "确认", 
            "确定要清空所有连线吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "测试", "所有连线已清空")
        else:
            self.update_status("❌ 取消清空连线")
    
    def test_start_node(self):
        """测试启动节点"""
        self.update_status("✅ 触发：启动节点")
        QMessageBox.information(self, "测试", "节点启动功能已触发")
    
    def test_stop_node(self):
        """测试停止节点"""
        self.update_status("✅ 触发：停止节点")
        QMessageBox.information(self, "测试", "节点停止功能已触发")
    
    def show_about(self):
        """显示关于信息"""
        QMessageBox.about(self, "关于", 
            "BNOS 菜单栏重构测试\n\n"
            "版本: 1.0.0-test\n"
            "测试目标: 将工具栏功能整合到菜单栏\n\n"
            "设计特点:\n"
            "• 文件菜单: 项目管理 + 视图控制 + 颜色设置\n"
            "• 编辑菜单: 节点操作（新建、刷新、启停）\n"
            "• 快捷键支持: Ctrl+N, Ctrl+O, F5, Ctrl+Shift+S/X\n"
            "• Emoji图标增强可读性"
        )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion风格，跨平台一致
    
    window = TestMenuBarWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
