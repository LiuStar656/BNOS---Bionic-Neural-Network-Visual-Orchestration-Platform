"""
统一深色对话框工具 — 完全自绘，不依赖 Windows 原生组件
"""
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
                               QWidget, QLineEdit, QTreeWidget, QTreeWidgetItem,
                               QComboBox, QHeaderView, QTextEdit, QSplitter)
from PySide6.QtCore import Qt, QDir, QPoint, QTimer, QSize
from PySide6.QtGui import QFont, QColor
from ui.core.i18n import t


_STYLE_CONTAINER = "QWidget { background-color: rgba(30,30,30,220); border-radius: 8px; border: 1px solid rgba(255,255,255,25); }"
_STYLE_TITLE    = "color: white; font-size: 13px; font-weight: bold; background: transparent;"
_STYLE_LABEL    = "color: rgba(255,255,255,180); font-size: 12px; background: transparent;"
_STYLE_INPUT    = "background: rgba(255,255,255,10); color: #d4d4d4; border: 1px solid rgba(255,255,255,15); border-radius: 4px; padding: 6px 10px; font-size: 13px;"
_STYLE_BTN_OK   = "QPushButton { background: rgba(0,120,212,200); color: white; border: none; border-radius: 4px; padding: 6px 20px; } QPushButton:hover { background: rgba(0,140,240,220); }"
_STYLE_BTN_GREY = "QPushButton { background: rgba(255,255,255,10); color: #ccc; border: 1px solid rgba(255,255,255,15); border-radius: 4px; padding: 6px 20px; } QPushButton:hover { background: rgba(255,255,255,20); }"
_STYLE_TREE     = ("QTreeWidget { background-color: #252526; color: #cccccc; border: 1px solid rgba(255,255,255,10); border-radius: 4px; font-size: 12px; } "
                   "QTreeWidget::item { padding: 3px 4px; } QTreeWidget::item:hover { background: #2a2d2e; } "
                   "QTreeWidget::item:selected { background: #094771; } "
                   "QHeaderView::section { background: #333; color: #aaa; border: none; padding: 3px; font-size: 11px; }")


class ThemedDialogBase(QDialog):
    """
    深色主题对话框基类
    提供统一的对话框框架、样式和居中逻辑
    """
    
    def __init__(self, parent=None, title="", width=400, height=200):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(width, height)
        
        # 外部容器（半透明背景）
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        
        # 内部容器（带圆角边框）
        self._container = QWidget()
        self._container.setStyleSheet(_STYLE_CONTAINER)
        outer_layout.addWidget(self._container)
        
        # 主布局
        self._main_layout = QVBoxLayout(self._container)
        self._main_layout.setContentsMargins(14, 10, 14, 10)
        self._main_layout.setSpacing(6)
        
        # 标题栏
        self._title_bar = QHBoxLayout()
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(_STYLE_TITLE)
        self._title_bar.addWidget(self._title_label)
        self._title_bar.addStretch()
        
        # 关闭按钮
        self._close_label = QLabel("x")
        self._close_label.setStyleSheet("color: rgba(255,255,255,150); font-size: 14px; padding:0 5px; background:transparent;")
        self._close_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_label.mousePressEvent = lambda e: self.reject()
        self._title_bar.addWidget(self._close_label)
        
        self._main_layout.addLayout(self._title_bar)
    
    def get_main_layout(self):
        """获取主布局，供子类添加内容"""
        return self._main_layout
    
    def center_on_parent(self):
        """将对话框居中显示"""
        parent = self.parent()
        if parent and parent.isVisible():
            pc = parent.mapToGlobal(parent.rect().center())
            self.move(pc.x() - self.width() // 2, pc.y() - self.height() // 2)
        else:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                self.move(geo.center().x() - self.width() // 2,
                         geo.center().y() - self.height() // 2)
    
    def add_button_row(self, buttons):
        """
        添加按钮行
        buttons: 列表，包含 ("text", style, callback) 元组
        """
        br = QHBoxLayout()
        br.addStretch()
        for text, style, callback in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(style)
            btn.clicked.connect(callback)
            br.addWidget(btn)
        self._main_layout.addLayout(br)
    
    def exec(self):
        """重写 exec，自动居中"""
        self.center_on_parent()
        return super().exec()


def _get_drives():
    """获取 Windows 驱动器列表"""
    drives = []
    try:
        if os.name == 'nt':
            import string
            from ctypes import windll
            bitmap = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmap & 1:
                    p = f"{letter}:\\"
                    if os.path.exists(p):
                        label = f"{letter}:"
                        drives.append((p, label))
                bitmap >>= 1
    except Exception:
        pass
    if not drives:
        drives.append(("/", "/"))
    return drives


def _load_lazy_dir_items(parent_item, full_path, filter_ext=None):
    """加载目录的文件和子目录（支持懒加载）"""
    if not os.path.isdir(full_path):
        return
    
    try:
        dirs = []
        files = []
        for name in sorted(os.listdir(full_path)):
            sub = os.path.join(full_path, name)
            if os.path.isdir(sub) and not name.startswith('.') and not name.startswith('$'):
                dirs.append((name, sub))
            elif os.path.isfile(sub):
                is_selectable = True
                if filter_ext:
                    is_selectable = name.endswith(filter_ext)
                files.append((name, sub, is_selectable))
        
        # 添加目录
        for name, sub in dirs:
            child = QTreeWidgetItem(parent_item, [name, sub])
            child.setData(0, 1, sub)
            try:
                has_subdir = False
                for _ in sorted(os.listdir(sub)):
                    sub_full = os.path.join(sub, _)
                    if os.path.isdir(sub_full) and not _.startswith('.') and not _.startswith('$'):
                        QTreeWidgetItem(child, ["...", ""])
                        has_subdir = True
                        break
                if not has_subdir:
                    QTreeWidgetItem(child, ["...", ""])
            except Exception:
                QTreeWidgetItem(child, ["...", ""])
        
        # 添加文件
        for item in files:
            name, sub, is_selectable = item if len(item) == 3 else (item[0], item[1], True)
            child = QTreeWidgetItem(parent_item, [name, sub])
            child.setData(0, 1, sub)
            child.setData(0, 256, is_selectable)
            if not is_selectable:
                child.setForeground(0, QColor(128, 128, 128))
                
    except PermissionError:
        QTreeWidgetItem(parent_item, ["❌ 无权限", ""])


def _create_nav_bar(parent, drives, on_drive_change, on_go_up, show_path_combo=False):
    """创建导航栏（驱动器选择 + 上级按钮）"""
    nav_bar = QHBoxLayout()
    
    # 驱动器选择
    drive_combo = QComboBox()
    drive_combo.setFixedWidth(70)
    drive_combo.setStyleSheet("QComboBox { background: #3c3c3c; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 2px 4px; font-size: 11px; } QComboBox QAbstractItemView { background: #252526; color: #ccc; }")
    for p, label in drives:
        drive_combo.addItem(f"  {label}  ", p)
    nav_bar.addWidget(drive_combo)
    drive_combo.currentIndexChanged.connect(on_drive_change)
    
    # 上级按钮
    up_btn = QPushButton(f"↑ {t('_k_btn_up')}")
    up_btn.setFixedWidth(80)
    up_btn.setStyleSheet(_STYLE_BTN_GREY + "QPushButton { font-size: 11px; padding: 3px 8px; }")
    nav_bar.addWidget(up_btn)
    up_btn.clicked.connect(on_go_up)
    
    # 路径下拉（可选）
    path_combo = None
    if show_path_combo:
        path_combo = QComboBox()
        path_combo.setStyleSheet("QComboBox { background: rgba(255,255,255,10); color: #d4d4d4; border: 1px solid rgba(255,255,255,15); border-radius: 4px; padding: 4px 10px; font-size: 12px; } QComboBox QAbstractItemView { background: #252526; color: #ccc; }")
        path_combo.setEditable(True)
        nav_bar.addWidget(path_combo, 1)
    
    nav_bar.addStretch()
    return nav_bar, drive_combo, up_btn, path_combo


def pick_folder(parent, title, start=""):
    """自绘文件夹选择器 — 树形展开 + 驱动器切换"""
    dlg = ThemedDialogBase(parent, title, 620, 440)
    lay = dlg.get_main_layout()
    
    drives = _get_drives()
    sel_path = [os.path.expanduser("~")]

    def go_up():
        parent_path = os.path.dirname(sel_path[0])
        if parent_path and parent_path != sel_path[0]:
            for i in range(drive_combo.count()):
                d = drive_combo.itemData(i)
                if parent_path.lower().startswith(d.lower()):
                    drive_combo.blockSignals(True)
                    drive_combo.setCurrentIndex(i)
                    drive_combo.blockSignals(False)
                    break
            load_tree(parent_path)

    nav_bar, drive_combo, up_btn, _ = _create_nav_bar(parent, drives, lambda idx: load_tree(drive_combo.itemData(idx)), go_up)
    lay.addLayout(nav_bar)
    
    # 路径面包屑
    current = QLabel("")
    current.setStyleSheet("color: rgba(255,255,255,120); font-size: 11px; background: transparent; padding: 2px 0;")
    lay.addWidget(current)
    
    # 目录树
    tree = QTreeWidget()
    tree.setHeaderLabels([t("_k_folder_picker_header"), t("_k_folder_picker_path")])
    tree.setColumnWidth(0, 300)
    tree.header().setStretchLastSection(True)
    tree.setStyleSheet(_STYLE_TREE)
    tree.setIndentation(16)
    lay.addWidget(tree, 1)
    
    def load_tree(root_path):
        root_path = os.path.normpath(root_path)
        sel_path[0] = root_path
        current.setText(t("_k_folder_current").replace("{path}", root_path))
        tree.clear()
        if os.path.isdir(root_path):
            _load_lazy_dir_items(tree.invisibleRootItem(), root_path)
    
    def on_item_expanded(item):
        child_count = item.childCount()
        if child_count == 1 and item.child(0).text(0) == "...":
            item.removeChild(item.child(0))
            full = item.data(0, 1)
            _load_lazy_dir_items(item, full)
    
    tree.itemExpanded.connect(on_item_expanded)
    
    def on_select(item):
        if item:
            path = item.data(0, 1)
            if path and os.path.isdir(path):
                sel_path[0] = os.path.normpath(path)
                current.setText(f"📂 当前: {sel_path[0]}")
    
    tree.currentItemChanged.connect(lambda cur, prev: on_select(cur))
    
    def on_dblclick(item, col):
        path = item.data(0, 1)
        if path and os.path.isdir(path):
            sel_path[0] = os.path.normpath(path)
            current.setText(f"📂 当前: {sel_path[0]}")
            load_tree(path)
    
    tree.itemDoubleClicked.connect(on_dblclick)
    
    dlg.add_button_row([
        (t("k_cancel"), _STYLE_BTN_GREY, dlg.reject),
        (t("_k_btn_select"), _STYLE_BTN_OK, dlg.accept)
    ])
    
    # 初始加载
    initial = start or os.path.expanduser("~")
    for i in range(drive_combo.count()):
        d = drive_combo.itemData(i)
        if initial.lower().startswith(d.lower()):
            drive_combo.blockSignals(True)
            drive_combo.setCurrentIndex(i)
            drive_combo.blockSignals(False)
            break
    load_tree(initial)
    
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return os.path.normpath(sel_path[0])
    return None


def themed_input(parent, title, prompt, default=""):
    """自绘输入弹窗"""
    dlg = ThemedDialogBase(parent, title, 380, 150)
    lay = dlg.get_main_layout()
    
    lb = QLabel(prompt)
    lb.setStyleSheet(_STYLE_LABEL)
    lay.addWidget(lb)
    
    e = QLineEdit(default)
    e.setStyleSheet(_STYLE_INPUT)
    lay.addWidget(e)
    
    def on_accept():
        dlg.accept()
    
    dlg.add_button_row([
        (t("k_cancel"), _STYLE_BTN_GREY, dlg.reject),
        (t("k_ok"), _STYLE_BTN_OK, on_accept)
    ])
    
    e.returnPressed.connect(dlg.accept)
    
    return e.text().strip() if dlg.exec() == QDialog.DialogCode.Accepted else None


MSG_ACCEPT = 1   # 确定/是
MSG_REJECT = 0   # 取消/否
MSG_CANCEL = -1  # 第三个按钮


def themed_message(parent, title, text, mode="info"):
    """
    统一消息弹窗，替代 QMessageBox。
    mode: "info" | "warning" | "error" | "question" | "question3"
    question → 是/否
    question3 → 是/否/取消
    """
    dlg = ThemedDialogBase(parent, title, 440, 180)
    lay = dlg.get_main_layout()
    
    lb = QLabel(text)
    lb.setWordWrap(True)
    lb.setStyleSheet(_STYLE_LABEL)
    lay.addWidget(lb, 1)
    
    result = MSG_ACCEPT
    
    if mode in ("info", "warning", "error"):
        dlg.add_button_row([
            (t("k_ok"), _STYLE_BTN_OK, dlg.accept)
        ])
    elif mode == "question":
        dlg.add_button_row([
            (t("_k_btn_no"), _STYLE_BTN_GREY, dlg.reject),
            (t("_k_btn_yes"), _STYLE_BTN_OK, dlg.accept)
        ])
        result = MSG_REJECT
    elif mode == "question3":
        cancel_btn = QPushButton(t("k_cancel"))
        cancel_btn.setStyleSheet(_STYLE_BTN_GREY)
        no_btn = QPushButton(t("_k_btn_no"))
        no_btn.setStyleSheet(_STYLE_BTN_GREY)
        yes_btn = QPushButton(t("_k_btn_yes"))
        yes_btn.setStyleSheet(_STYLE_BTN_OK)
        
        br = QHBoxLayout()
        br.addStretch()
        br.addWidget(cancel_btn)
        br.addWidget(no_btn)
        br.addWidget(yes_btn)
        lay.addLayout(br)
        
        cancel_btn.clicked.connect(lambda: setattr(dlg, '_result', MSG_CANCEL) or dlg.reject())
        no_btn.clicked.connect(dlg.reject)
        yes_btn.clicked.connect(dlg.accept)
        result = MSG_REJECT
        dlg._result = MSG_REJECT
        
        orig_exec = dlg.exec
        def custom_exec():
            code = orig_exec()
            if hasattr(dlg, '_result') and code == 0:
                return dlg._result
            return MSG_ACCEPT if code == 1 else MSG_CANCEL
        dlg.exec = custom_exec
    
    # 点击空白处关闭（info/warning/error 模式）
    if mode in ("info", "warning", "error"):
        old_mp = dlg._container.mousePressEvent
        dlg._container.mousePressEvent = lambda e: dlg.accept()
        dlg._old_container_mp = old_mp
    
    rc = dlg.exec()
    if mode == "question3":
        return rc if isinstance(rc, int) else MSG_CANCEL
    if mode == "question":
        return True if rc == QDialog.DialogCode.Accepted else False
    return None


def pick_file(parent, title, filter_ext=None, start=""):
    """自绘文件选择器 — 树形展开 + 驱动器切换 + 文件预览"""
    dlg = ThemedDialogBase(parent, title, 800, 520)
    lay = dlg.get_main_layout()
    
    drives = _get_drives()
    sel_path = [os.path.expanduser("~")]
    selected_file = [None]

    def go_up():
        parent_path = os.path.dirname(sel_path[0])
        if parent_path and parent_path != sel_path[0]:
            for i in range(drive_combo.count()):
                d = drive_combo.itemData(i)
                if parent_path.lower().startswith(d.lower()):
                    drive_combo.blockSignals(True)
                    drive_combo.setCurrentIndex(i)
                    drive_combo.blockSignals(False)
                    break
            load_tree(parent_path)

    def load_tree(root_path):
        root_path = os.path.normpath(root_path)
        sel_path[0] = root_path
        
        if path_combo:
            path_combo.blockSignals(True)
            path_combo.clear()
            parts = []
            current = root_path
            prev_path = ""
            while current and current != prev_path and current != os.sep:
                parts.insert(0, current)
                prev_path = current
                current = os.path.dirname(current)
            if root_path and root_path not in parts:
                parts.insert(0, root_path)
            for p in parts:
                path_combo.addItem(p)
            path_combo.setCurrentText(root_path)
            path_combo.blockSignals(False)
        
        preview_info.setText(t("_k_folder_current").replace("{path}", root_path))
        tree.clear()
        if os.path.isdir(root_path):
            _load_lazy_dir_items(tree.invisibleRootItem(), root_path, filter_ext)
    
    nav_bar, drive_combo, up_btn, path_combo = _create_nav_bar(parent, drives, lambda idx: load_tree(drive_combo.itemData(idx)), go_up, show_path_combo=True)
    lay.addLayout(nav_bar)
    
    # 分割器：文件树 + 预览
    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.setStyleSheet("QSplitter::handle { background: #3c3c3c; }")
    
    # 文件列表树
    tree = QTreeWidget()
    tree.setHeaderLabels([t("_k_file_picker_header"), t("_k_file_picker_path")])
    tree.setColumnWidth(0, 300)
    tree.header().setStretchLastSection(True)
    tree.setStyleSheet(_STYLE_TREE)
    tree.setIndentation(16)
    tree.setUniformRowHeights(True)
    tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
    tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
    splitter.addWidget(tree)
    
    # 文件预览面板
    preview_panel = QWidget()
    preview_layout = QVBoxLayout(preview_panel)
    preview_layout.setContentsMargins(6, 6, 6, 6)
    
    preview_title = QLabel(t("_k_preview_title"))
    preview_title.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold; padding-bottom: 4px;")
    preview_layout.addWidget(preview_title)
    
    preview_text = QTextEdit()
    preview_text.setReadOnly(True)
    preview_text.setStyleSheet("""
        QTextEdit { background: #1e1e1e; color: #ccc; border: 1px solid rgba(255,255,255,10); 
                   border-radius: 4px; font-family: Consolas, monospace; font-size: 11px; }
    """)
    preview_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
    preview_layout.addWidget(preview_text, 1)
    
    preview_info = QLabel("")
    preview_info.setStyleSheet("color: rgba(255,255,255,100); font-size: 10px;")
    preview_layout.addWidget(preview_info)
    
    splitter.addWidget(preview_panel)
    splitter.setSizes([400, 300])
    lay.addWidget(splitter, 1)
    
    # 文件名输入
    file_name_edit = QLineEdit()
    file_name_edit.setStyleSheet(_STYLE_INPUT)
    file_name_edit.setPlaceholderText(t("_k_file_name_hint"))
    lay.addWidget(file_name_edit)
    
    def _preview_file(file_path):
        if not file_path or not os.path.isfile(file_path):
            preview_text.setPlainText("")
            preview_info.setText(t("_k_no_preview"))
            return
        
        try:
            file_size = os.path.getsize(file_path)
            if file_size > 1024 * 1024:
                preview_text.setPlainText(t("_k_file_too_large"))
                preview_info.setText(f"{os.path.basename(file_path)} - {file_size // 1024} KB")
                return
            
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(50000)
                preview_text.setPlainText(content)
                preview_info.setText(f"{os.path.basename(file_path)} - {file_size} bytes")
                
        except Exception as e:
            preview_text.setPlainText(t("_k_preview_error").format(error=str(e)))
            preview_info.setText(os.path.basename(file_path))
    
    def on_item_expanded(item):
        child_count = item.childCount()
        if child_count == 1 and item.child(0).text(0) == "...":
            item.removeChild(item.child(0))
            full = item.data(0, 1)
            _load_lazy_dir_items(item, full, filter_ext)
    
    tree.itemExpanded.connect(on_item_expanded)
    
    def on_select(item):
        if item is None:
            selected_file[0] = None
            file_name_edit.clear()
            _preview_file(None)
            return
            
        path = item.data(0, 1)
        is_selectable = item.data(0, 256) if item else True
        if path:
            if os.path.isdir(path):
                sel_path[0] = os.path.normpath(path)
                selected_file[0] = None
                file_name_edit.clear()
                _preview_file(None)
            else:
                if is_selectable:
                    selected_file[0] = os.path.normpath(path)
                    file_name_edit.setText(os.path.basename(path))
                    _preview_file(path)
                else:
                    selected_file[0] = None
                    file_name_edit.clear()
                    _preview_file(None)
    
    tree.currentItemChanged.connect(lambda cur, prev: on_select(cur))
    
    def on_dblclick(item, col):
        path = item.data(0, 1)
        is_selectable = item.data(0, 256) if item else True
        if path:
            if os.path.isdir(path):
                sel_path[0] = os.path.normpath(path)
                load_tree(path)
            else:
                if is_selectable:
                    selected_file[0] = os.path.normpath(path)
                    file_name_edit.setText(os.path.basename(path))
    
    tree.itemDoubleClicked.connect(on_dblclick)
    
    def on_confirm():
        if selected_file[0]:
            dlg.accept()
        elif file_name_edit.text().strip():
            selected_file[0] = os.path.normpath(os.path.join(sel_path[0], file_name_edit.text().strip()))
            dlg.accept()
    
    if path_combo:
        path_combo.lineEdit().returnPressed.connect(lambda: load_tree(path_combo.currentText().strip()))
        path_combo.currentIndexChanged.connect(lambda idx: load_tree(path_combo.itemText(idx)))
    
    dlg.add_button_row([
        (t("k_cancel"), _STYLE_BTN_GREY, dlg.reject),
        (t("_k_btn_select"), _STYLE_BTN_OK, on_confirm)
    ])
    
    # 初始加载
    initial = start or os.path.expanduser("~")
    for i in range(drive_combo.count()):
        d = drive_combo.itemData(i)
        if initial.lower().startswith(d.lower()):
            drive_combo.blockSignals(True)
            drive_combo.setCurrentIndex(i)
            drive_combo.blockSignals(False)
            break
    load_tree(initial)
    
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return selected_file[0]
    return None


def pick_save_file(parent, title, default_name="", filter_ext=None, start=""):
    """自绘文件保存对话框"""
    dlg = ThemedDialogBase(parent, title, 620, 440)
    lay = dlg.get_main_layout()
    
    drives = _get_drives()
    sel_path = [os.path.expanduser("~")]

    def go_up():
        parent_path = os.path.dirname(sel_path[0])
        if parent_path and parent_path != sel_path[0]:
            for i in range(drive_combo.count()):
                d = drive_combo.itemData(i)
                if parent_path.lower().startswith(d.lower()):
                    drive_combo.blockSignals(True)
                    drive_combo.setCurrentIndex(i)
                    drive_combo.blockSignals(False)
                    break
            load_tree(parent_path)

    def load_tree(root_path):
        root_path = os.path.normpath(root_path)
        sel_path[0] = root_path
        current.setText(t("_k_folder_current").replace("{path}", root_path))
        tree.clear()
        if os.path.isdir(root_path):
            _load_lazy_dir_items(tree.invisibleRootItem(), root_path, filter_ext)

    nav_bar, drive_combo, up_btn, _ = _create_nav_bar(parent, drives, lambda idx: load_tree(drive_combo.itemData(idx)), go_up)
    lay.addLayout(nav_bar)
    
    # 路径面包屑
    current = QLabel("")
    current.setStyleSheet("color: rgba(255,255,255,120); font-size: 11px; background: transparent; padding: 2px 0;")
    lay.addWidget(current)
    
    # 文件列表树
    tree = QTreeWidget()
    tree.setHeaderLabels([t("_k_file_picker_header"), t("_k_file_picker_path")])
    tree.setColumnWidth(0, 300)
    tree.header().setStretchLastSection(True)
    tree.setStyleSheet(_STYLE_TREE)
    tree.setIndentation(16)
    tree.setUniformRowHeights(True)
    tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
    tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
    lay.addWidget(tree, 1)
    
    # 文件名输入
    file_name_edit = QLineEdit(default_name)
    file_name_edit.setStyleSheet(_STYLE_INPUT)
    file_name_edit.setPlaceholderText(t("_k_file_name_hint"))
    lay.addWidget(file_name_edit)
    
    def on_item_expanded(item):
        child_count = item.childCount()
        if child_count == 1 and item.child(0).text(0) == "...":
            item.removeChild(item.child(0))
            full = item.data(0, 1)
            _load_lazy_dir_items(item, full, filter_ext)
    
    tree.itemExpanded.connect(on_item_expanded)
    
    def on_select(item):
        if item:
            path = item.data(0, 1)
            if path:
                if os.path.isdir(path):
                    sel_path[0] = os.path.normpath(path)
                else:
                    sel_path[0] = os.path.normpath(os.path.dirname(path))
                    file_name_edit.setText(os.path.basename(path))
                current.setText(f"📂 当前: {sel_path[0]}")
    
    tree.currentItemChanged.connect(lambda cur, prev: on_select(cur))
    
    def on_dblclick(item, col):
        path = item.data(0, 1)
        if path and os.path.isdir(path):
            sel_path[0] = os.path.normpath(path)
            load_tree(path)
    
    tree.itemDoubleClicked.connect(on_dblclick)
    
    def on_confirm():
        file_name = file_name_edit.text().strip()
        if file_name:
            if filter_ext and not file_name.endswith(filter_ext):
                file_name += filter_ext
            dlg.selected_path = os.path.normpath(os.path.join(sel_path[0], file_name))
            dlg.accept()
    
    dlg.add_button_row([
        (t("k_cancel"), _STYLE_BTN_GREY, dlg.reject),
        (t("_k_btn_save"), _STYLE_BTN_OK, on_confirm)
    ])
    
    # 初始加载
    initial = start or os.path.expanduser("~")
    for i in range(drive_combo.count()):
        d = drive_combo.itemData(i)
        if initial.lower().startswith(d.lower()):
            drive_combo.blockSignals(True)
            drive_combo.setCurrentIndex(i)
            drive_combo.blockSignals(False)
            break
    load_tree(initial)
    
    dlg.selected_path = None
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.selected_path
    return None


themed_question = lambda p, t, x: themed_message(p, t, x, "question")
