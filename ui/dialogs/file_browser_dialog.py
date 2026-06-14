"""
独立文件浏览器对话框 - 用于导入导出操作（浮动窗口版本）
"""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QTreeWidgetItem, QLineEdit, QPushButton, QLabel, QSplitter,
    QMenu, QHeaderView
)
from PySide6.QtCore import Qt, QDir, QModelIndex
from PySide6.QtGui import QIcon, QFileSystemModel, QAction
from ui.core.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.logger import logger


class FileBrowserDialog(FloatingPanel):
    """独立文件浏览器对话框（浮动窗口版本）"""
    
    def __init__(self, parent=None, mode='open', file_type='node', title=None):
        """
        Args:
            parent: 父窗口
            mode: 'open' 或 'save'
            file_type: 'node' (.bnos) 或 'project' (.bnosc)
            title: 对话框标题
        """
        dialog_title = title or self._get_default_title(mode, file_type)
        super().__init__(parent, title=dialog_title)
        
        self.mode = mode
        self.file_type = file_type
        self.selected_path = None
        
        # 设置窗口样式
        self.setMinimumSize(800, 600)
        
        # 文件扩展名配置
        self.extension = '.bnos' if file_type == 'node' else '.bnosc'
        self.filter_name = 'BNOS Node' if file_type == 'node' else 'BNOS Project'
        
        # 居中显示
        if parent:
            self.move(parent.geometry().center() - self.rect().center())
        
        self._init_ui()
    
    def _get_default_title(self, mode, file_type):
        """获取默认标题"""
        if mode == 'open':
            return t("k_import_node") if file_type == 'node' else t("k_import_project")
        else:
            return t("k_export_node") if file_type == 'node' else t("k_export_project")
    
    def _init_ui(self):
        """初始化UI布局"""
        # 主布局
        main_layout = QVBoxLayout()
        
        # 顶部工具栏
        toolbar = QHBoxLayout()
        
        # 返回按钮
        self.back_btn = QPushButton('←')
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.setEnabled(False)
        toolbar.addWidget(self.back_btn)
        
        # 前进按钮
        self.forward_btn = QPushButton('→')
        self.forward_btn.clicked.connect(self._go_forward)
        self.forward_btn.setEnabled(False)
        toolbar.addWidget(self.forward_btn)
        
        # 向上按钮
        self.up_btn = QPushButton('↑')
        self.up_btn.clicked.connect(self._go_up)
        toolbar.addWidget(self.up_btn)
        
        toolbar.addSpacing(10)
        
        # 地址栏
        self.path_edit = QLineEdit()
        self.path_edit.returnPressed.connect(self._navigate_to_path)
        toolbar.addWidget(self.path_edit, 1)
        
        main_layout.addLayout(toolbar)
        
        # 分隔器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧目录树
        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderHidden(True)
        self.dir_tree.setMaximumWidth(200)
        self.dir_tree.itemClicked.connect(self._on_dir_tree_click)
        splitter.addWidget(self.dir_tree)
        
        # 右侧文件列表
        self.file_list = QTreeWidget()
        self.file_list.setColumnCount(2)
        self.file_list.setHeaderLabels([t("k_file_name"), t("k_file_size")])
        self.file_list.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_list.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.file_list.setColumnWidth(1, 100)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._show_context_menu)
        self.file_list.itemDoubleClicked.connect(self._on_file_double_click)
        splitter.addWidget(self.file_list)
        
        main_layout.addWidget(splitter, 1)
        
        # 底部状态栏和按钮
        bottom_layout = QHBoxLayout()
        
        # 状态栏信息
        self.status_label = QLabel(t("k_file_browser_status"))
        bottom_layout.addWidget(self.status_label)
        
        bottom_layout.addStretch()
        
        # 取消按钮
        cancel_btn = QPushButton(t("k_cancel"))
        cancel_btn.clicked.connect(self.close)
        bottom_layout.addWidget(cancel_btn)
        
        # 确认按钮
        self.ok_btn = QPushButton(t("k_ok"))
        self.ok_btn.clicked.connect(self._on_ok)
        self.ok_btn.setEnabled(False)
        bottom_layout.addWidget(self.ok_btn)
        
        main_layout.addLayout(bottom_layout)
        
        self.content_layout.addLayout(main_layout)
        
        # 初始化目录树
        self._init_dir_tree()
        
        # 初始化文件列表
        self._update_file_list(QDir.currentPath())
        
        # 导航历史
        self._history = []
        self._history_index = -1
    
    def _init_dir_tree(self):
        """初始化目录树"""
        # 清空现有内容
        self.dir_tree.clear()
        
        # 添加根目录
        root_item = QTreeWidgetItem(self.dir_tree)
        root_item.setText(0, t("k_computer"))
        root_item.setIcon(0, QIcon.fromTheme('computer'))
        
        # 获取系统驱动器
        drives = QDir.drives()
        for drive in drives:
            drive_path = drive.absolutePath()
            drive_item = QTreeWidgetItem(root_item)
            drive_item.setText(0, drive_path)
            drive_item.setIcon(0, QIcon.fromTheme('harddisk'))
            drive_item.setData(0, Qt.ItemDataRole.UserRole, drive_path)
            # 展开根目录
            root_item.setExpanded(True)
    
    def _update_file_list(self, path):
        """更新文件列表"""
        self.file_list.clear()
        self.current_path = path
        self.path_edit.setText(path)
        
        try:
            files = os.listdir(path)
            dirs = []
            files_list = []
            
            for f in files:
                full_path = os.path.join(path, f)
                if os.path.isdir(full_path):
                    dirs.append(f)
                elif f.endswith(self.extension):
                    files_list.append(f)
            
            # 排序
            dirs.sort(key=str.lower)
            files_list.sort(key=str.lower)
            
            # 添加目录
            for d in dirs:
                item = QTreeWidgetItem(self.file_list)
                item.setText(0, d)
                item.setText(1, '')
                item.setIcon(0, QIcon.fromTheme('folder'))
                item.setData(0, Qt.ItemDataRole.UserRole, os.path.join(path, d))
            
            # 添加文件
            for f in files_list:
                full_path = os.path.join(path, f)
                size = os.path.getsize(full_path)
                item = QTreeWidgetItem(self.file_list)
                item.setText(0, f)
                item.setText(1, self._format_size(size))
                item.setIcon(0, QIcon.fromTheme('file'))
                item.setData(0, Qt.ItemDataRole.UserRole, full_path)
            
            # 更新状态栏
            total = len(dirs) + len(files_list)
            self.status_label.setText(t("k_file_browser_status_info").format(count=total, path=path))
            
        except Exception as e:
            logger.error(f"Failed to update file list: {e}")
    
    def _format_size(self, size):
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    
    def _go_back(self):
        """返回上一级"""
        if self._history_index > 0:
            self._history_index -= 1
            path = self._history[self._history_index]
            self._update_file_list(path)
            self._update_nav_buttons()
    
    def _go_forward(self):
        """前进"""
        if self._history_index < len(self._history) - 1:
            self._history_index += 1
            path = self._history[self._history_index]
            self._update_file_list(path)
            self._update_nav_buttons()
    
    def _go_up(self):
        """向上一级目录"""
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self._navigate_to_path(parent)
    
    def _navigate_to_path(self, path=None):
        """导航到指定路径"""
        if path is None:
            path = self.path_edit.text()
        
        if os.path.isdir(path):
            # 添加到历史记录
            if self._history_index < len(self._history) - 1:
                self._history = self._history[:self._history_index + 1]
            self._history.append(path)
            self._history_index = len(self._history) - 1
            
            self._update_file_list(path)
            self._update_nav_buttons()
            self._expand_dir_tree(path)
    
    def _update_nav_buttons(self):
        """更新导航按钮状态"""
        self.back_btn.setEnabled(self._history_index > 0)
        self.forward_btn.setEnabled(self._history_index < len(self._history) - 1)
    
    def _expand_dir_tree(self, path):
        """展开目录树到指定路径"""
        # 简化实现：不展开目录树，保持简洁
    
    def _on_dir_tree_click(self, item, column):
        """目录树点击事件"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and os.path.isdir(path):
            self._navigate_to_path(path)
    
    def _on_file_double_click(self, item, column):
        """文件双击事件"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if os.path.isdir(path):
            self._navigate_to_path(path)
        else:
            self._select_file(path)
    
    def _select_file(self, path):
        """选择文件"""
        self.selected_path = path
        self.ok_btn.setEnabled(True)
    
    def _show_context_menu(self, position):
        """显示右键菜单"""
        item = self.file_list.itemAt(position)
        if not item:
            return
        
        path = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        
        if os.path.isdir(path):
            open_action = menu.addAction(t("k_open_dir"))
            open_action.triggered.connect(lambda: self._navigate_to_path(path))
        
        menu.exec(self.file_list.mapToGlobal(position))
    
    def _on_ok(self):
        """确认按钮"""
        if self.mode == 'save':
            # 保存模式：获取文件名输入
            current_path = self.path_edit.text()
            file_name = self._get_selected_file_name()
            if not file_name:
                file_name = 'untitled'
            
            # 确保有正确的扩展名
            if not file_name.endswith(self.extension):
                file_name += self.extension
            
            self.selected_path = os.path.join(current_path, file_name)
        
        self.accept()