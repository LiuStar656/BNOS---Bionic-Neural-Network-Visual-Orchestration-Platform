"""
独立文件浏览器对话框 - 用于导入导出操作
"""
import os
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
    QTreeWidgetItem, QLineEdit, QPushButton, QLabel, QSplitter,
    QMenu, QHeaderView
)
from PyQt6.QtCore import Qt, QDir, QModelIndex
from PyQt6.QtGui import QIcon, QFileSystemModel, QAction
from ui.core.i18n import t
from ui.core.logger import logger


class FileBrowserDialog(QDialog):
    """独立文件浏览器对话框"""
    
    def __init__(self, parent=None, mode='open', file_type='node', title=None):
        """
        Args:
            parent: 父窗口
            mode: 'open' 或 'save'
            file_type: 'node' (.bnos) 或 'project' (.bnosc)
            title: 对话框标题
        """
        super().__init__(parent)
        
        self.mode = mode
        self.file_type = file_type
        self.selected_path = None
        
        # 设置窗口样式
        self.setWindowTitle(title or self._get_default_title())
        self.setMinimumSize(800, 600)
        
        # 文件扩展名配置
        self.extension = '.bnos' if file_type == 'node' else '.bnosc'
        self.filter_name = 'BNOS Node' if file_type == 'node' else 'BNOS Project'
        
        self._init_ui()
    
    def _get_default_title(self):
        """获取默认标题"""
        if self.mode == 'open':
            return t("k_import_node") if self.file_type == 'node' else t("k_import_project")
        else:
            return t("k_export_node") if self.file_type == 'node' else t("k_export_project")
    
    def _init_ui(self):
        """初始化UI布局"""
        main_layout = QVBoxLayout(self)
        
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
        
        # 主区域：左侧目录树 + 右侧文件列表
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧目录树
        self.dir_tree = QTreeWidget()
        self.dir_tree.setHeaderLabel(t("k_explorer"))
        self.dir_tree.setMinimumWidth(200)
        self.dir_tree.itemClicked.connect(self._on_dir_tree_click)
        splitter.addWidget(self.dir_tree)
        
        # 右侧文件列表
        self.file_list = QTreeWidget()
        self.file_list.setColumnCount(4)
        self.file_list.setHeaderLabels([t("k_name"), t("k_type"), t("k_size"), t("k_date")])
        self.file_list.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.file_list.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.file_list.doubleClicked.connect(self._on_file_double_click)
        self.file_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._show_file_context_menu)
        splitter.addWidget(self.file_list)
        
        main_layout.addWidget(splitter)
        
        # 底部状态栏和按钮
        bottom_layout = QHBoxLayout()
        
        # 状态栏
        self.status_label = QLabel(t("k_folder_current").format(path=""))
        bottom_layout.addWidget(self.status_label)
        
        bottom_layout.addStretch()
        
        # 取消按钮
        self.cancel_btn = QPushButton(t("k_cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(self.cancel_btn)
        
        # 确认按钮
        self.ok_btn = QPushButton(t("k_ok"))
        self.ok_btn.clicked.connect(self._on_ok)
        self.ok_btn.setEnabled(False)
        bottom_layout.addWidget(self.ok_btn)
        
        main_layout.addLayout(bottom_layout)
        
        # 导航历史
        self.history = []
        self.history_index = -1
        
        # 加载目录树
        self._load_dir_tree()
        
        # 加载当前目录
        self._load_current_directory(os.path.expanduser("~"))
    
    def _load_dir_tree(self):
        """加载目录树"""
        self.dir_tree.clear()
        
        # 添加根目录
        root_item = QTreeWidgetItem(self.dir_tree, ['Desktop'])
        root_item.setData(0, Qt.ItemDataRole.UserRole, os.path.expanduser("~/Desktop"))
        root_item.setIcon(0, QIcon.fromTheme('user-desktop'))
        
        documents_item = QTreeWidgetItem(self.dir_tree, ['Documents'])
        documents_item.setData(0, Qt.ItemDataRole.UserRole, os.path.expanduser("~/Documents"))
        documents_item.setIcon(0, QIcon.fromTheme('folder-documents'))
        
        downloads_item = QTreeWidgetItem(self.dir_tree, ['Downloads'])
        downloads_item.setData(0, Qt.ItemDataRole.UserRole, os.path.expanduser("~/Downloads"))
        downloads_item.setIcon(0, QIcon.fromTheme('folder-download'))
        
        # 添加磁盘驱动器（Windows）
        try:
            import win32api
            drives = win32api.GetLogicalDriveStrings()
            drives = drives.split('\x00')[:-1]
            for drive in drives:
                drive_item = QTreeWidgetItem(self.dir_tree, [drive])
                drive_item.setData(0, Qt.ItemDataRole.UserRole, drive)
                drive_item.setIcon(0, QIcon.fromTheme('harddisk'))
        except ImportError:
            pass
        
        self.dir_tree.expandAll()
    
    def _load_current_directory(self, path):
        """加载当前目录内容"""
        try:
            # 更新地址栏
            self.path_edit.setText(path)
            self.status_label.setText(t("k_folder_current").format(path=path))
            
            # 清空文件列表
            self.file_list.clear()
            
            # 获取目录内容
            items = []
            try:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    is_dir = os.path.isdir(item_path)
                    if is_dir:
                        items.append((item, 'folder', '', ''))
                    else:
                        # 过滤文件类型
                        if self.mode == 'open':
                            if item.endswith(self.extension):
                                size = os.path.getsize(item_path)
                                items.append((item, 'file', self._format_size(size), ''))
                        else:
                            size = os.path.getsize(item_path)
                            items.append((item, 'file', self._format_size(size), ''))
            except PermissionError:
                logger.warning(f"无法访问目录: {path}")
                return
            
            # 排序：文件夹在前，按名称排序
            items.sort(key=lambda x: (x[1] != 'folder', x[0].lower()))
            
            # 添加到列表
            for name, item_type, size, date in items:
                item = QTreeWidgetItem([name, item_type, size, date])
                item.setData(0, Qt.ItemDataRole.UserRole, os.path.join(path, name))
                if item_type == 'folder':
                    item.setIcon(0, QIcon.fromTheme('folder'))
                else:
                    item.setIcon(0, QIcon.fromTheme('file'))
                self.file_list.addTopLevelItem(item)
            
            # 更新导航历史
            self._update_history(path)
            
        except Exception as e:
            logger.error(f"加载目录失败: {e}")
    
    def _update_history(self, path):
        """更新导航历史"""
        # 如果当前路径已在历史中，截断后面的历史
        if path in self.history:
            idx = self.history.index(path)
            self.history = self.history[:idx + 1]
            self.history_index = idx
        else:
            # 添加新路径到历史
            self.history = self.history[:self.history_index + 1]
            self.history.append(path)
            self.history_index = len(self.history) - 1
        
        # 更新按钮状态
        self.back_btn.setEnabled(self.history_index > 0)
        self.forward_btn.setEnabled(self.history_index < len(self.history) - 1)
    
    def _go_back(self):
        """后退"""
        if self.history_index > 0:
            self.history_index -= 1
            self._load_current_directory(self.history[self.history_index])
    
    def _go_forward(self):
        """前进"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._load_current_directory(self.history[self.history_index])
    
    def _go_up(self):
        """返回上级目录"""
        current_path = self.path_edit.text()
        parent_path = os.path.dirname(current_path)
        if parent_path and parent_path != current_path:
            self._load_current_directory(parent_path)
    
    def _navigate_to_path(self):
        """导航到地址栏输入的路径"""
        path = self.path_edit.text()
        if os.path.exists(path):
            self._load_current_directory(path)
    
    def _on_dir_tree_click(self, item, column):
        """点击目录树"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and os.path.isdir(path):
            self._load_current_directory(path)
    
    def _on_file_double_click(self, index):
        """双击文件/文件夹"""
        item = self.file_list.itemFromIndex(index)
        path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if os.path.isdir(path):
            self._load_current_directory(path)
        elif self.mode == 'open':
            self.selected_path = path
            self.accept()
    
    def _show_file_context_menu(self, position):
        """显示文件右键菜单"""
        item = self.file_list.itemAt(position)
        if not item:
            return
        
        path = item.data(0, Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        
        if os.path.isdir(path):
            open_action = menu.addAction(t("k_open_dir"))
            open_action.triggered.connect(lambda: self._load_current_directory(path))
        
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
    
    def _get_selected_file_name(self):
        """获取选中的文件名"""
        selected_items = self.file_list.selectedItems()
        if selected_items:
            return selected_items[0].text(0)
        return None
    
    def _format_size(self, size):
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    
    def get_selected_path(self):
        """获取选中的路径"""
        return self.selected_path
    
    @staticmethod
    def get_open_path(parent=None, file_type='node'):
        """静态方法：打开文件选择对话框"""
        dialog = FileBrowserDialog(parent, mode='open', file_type=file_type)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selected_path()
        return None
    
    @staticmethod
    def get_save_path(parent=None, file_type='node', default_name=None):
        """静态方法：打开保存文件对话框"""
        dialog = FileBrowserDialog(parent, mode='save', file_type=file_type)
        if default_name:
            dialog.path_edit.setText(os.path.dirname(os.path.expanduser("~")))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return dialog.get_selected_path()
        return None