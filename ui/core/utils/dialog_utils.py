"""
统一深色对话框工具 — 完全自绘，不依赖 Windows 原生组件
"""
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
                               QWidget, QLineEdit, QTreeWidget, QTreeWidgetItem,
                               QComboBox, QHeaderView, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt, QDir, QPoint, QTimer, QSize
from PyQt6.QtGui import QFont, QColor
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


def _make_dialog(parent, title, w, h):
    dlg = QDialog(parent)
    dlg.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
    dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dlg.resize(w, h)
    outer = QVBoxLayout(dlg); outer.setContentsMargins(0,0,0,0)
    c = QWidget(); c.setStyleSheet(_STYLE_CONTAINER); outer.addWidget(c)
    lay = QVBoxLayout(c); lay.setContentsMargins(14,10,14,10); lay.setSpacing(6)
    bar = QHBoxLayout()
    tl = QLabel(title); tl.setStyleSheet(_STYLE_TITLE); bar.addWidget(tl); bar.addStretch()
    xl = QLabel("x"); xl.setStyleSheet("color: rgba(255,255,255,150); font-size: 14px; padding:0 5px; background:transparent;"); xl.setCursor(Qt.CursorShape.PointingHandCursor)
    xl.mousePressEvent = lambda e: dlg.reject(); bar.addWidget(xl); lay.addLayout(bar)
    dlg._container = c  # 供 themed_message 使用
    return dlg, lay


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


def _add_dir_items(parent_item, path, depth=0, max_depth=3):
    """递归添加子目录（限制深度）"""
    if depth >= max_depth:
        return
    try:
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isdir(full) and not name.startswith('.') and not name.startswith('$'):
                child = QTreeWidgetItem(parent_item, [name, full])
                if depth < max_depth - 1:
                    # 只预展开前几个子目录
                    _add_dir_items(child, full, depth + 1, 2 if depth == 0 else 1)
    except (PermissionError, OSError):
        pass


def pick_folder(parent, title, start=""):
    """自绘文件夹选择器 — 树形展开 + 驱动器切换"""
    dlg, lay = _make_dialog(parent, title, 620, 440)

    # 驱动器选择 + 上级按钮
    drives = _get_drives()
    nav_bar = QHBoxLayout()
    drive_combo = QComboBox()
    drive_combo.setFixedWidth(70)
    drive_combo.setStyleSheet("QComboBox { background: #3c3c3c; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 2px 4px; font-size: 11px; } QComboBox QAbstractItemView { background: #252526; color: #ccc; }")
    for p, label in drives:
        drive_combo.addItem(f"  {label}  ", p)
    nav_bar.addWidget(drive_combo)
    up_btn = QPushButton(f"↑ {t('_k_btn_up')}")
    up_btn.setFixedWidth(80)
    up_btn.setStyleSheet(_STYLE_BTN_GREY + "QPushButton { font-size: 11px; padding: 3px 8px; }")
    nav_bar.addWidget(up_btn)
    nav_bar.addStretch()
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

    # 按钮
    br = QHBoxLayout(); br.addStretch()
    cancel = QPushButton(t("k_cancel")); cancel.setStyleSheet(_STYLE_BTN_GREY)
    confirm = QPushButton(t("_k_btn_select")); confirm.setStyleSheet(_STYLE_BTN_OK)
    br.addWidget(cancel); br.addWidget(confirm); lay.addLayout(br)
    cancel.clicked.connect(dlg.reject)

    sel_path = [os.path.expanduser("~")]

    def load_tree(root_path):
        root_path = os.path.normpath(root_path)
        sel_path[0] = root_path
        current.setText(t("_k_folder_current").replace("{path}", root_path))
        tree.clear()
        if os.path.isdir(root_path):
            _load_children(tree.invisibleRootItem(), root_path)

    def on_drive_change(idx):
        path = drive_combo.itemData(idx)
        load_tree(path)

    drive_combo.currentIndexChanged.connect(on_drive_change)

    def on_item_expanded(item):
        """展开时延迟加载子目录（支持无限层级）"""
        child_count = item.childCount()
        # 如果有 placeholder 子项，清掉后加载真实内容
        if child_count == 1 and item.child(0).text(0) == "...":
            item.removeChild(item.child(0))
            full = item.data(0, 1)
            _load_children(item, full)

    def _load_children(parent_item, full_path):
        """加载目录的子目录（每层带 lazy placeholder）"""
        if not os.path.isdir(full_path):
            return
        try:
            items = []
            for name in sorted(os.listdir(full_path)):
                sub = os.path.join(full_path, name)
                if os.path.isdir(sub) and not name.startswith('.') and not name.startswith('$'):
                    child = QTreeWidgetItem(parent_item, [name, sub])
                    child.setData(0, 1, sub)
                    items.append(child)
            # 为每个子目录添加 lazy placeholder（展开时触发加载）
            for child in items:
                try:
                    for _ in sorted(os.listdir(child.data(0, 1))):
                        sub_full = os.path.join(child.data(0, 1), _)
                        if os.path.isdir(sub_full) and not _.startswith('.') and not _.startswith('$'):
                            QTreeWidgetItem(child, ["...", ""])
                            break
                except:
                    pass
        except PermissionError:
            QTreeWidgetItem(parent_item, ["❌ 无权限", ""])

    tree.itemExpanded.connect(on_item_expanded)

    def on_select(item):
        path = item.data(0, 1)
        if path and os.path.isdir(path):
            sel_path[0] = os.path.normpath(path)
            current.setText(f"📂 当前: {sel_path[0]}")

    tree.currentItemChanged.connect(lambda cur, prev: on_select(cur) if cur else None)

    # 双击进入文件夹
    def on_dblclick(item, col):
        path = item.data(0, 1)
        if path and os.path.isdir(path):
            sel_path[0] = os.path.normpath(path)
            current.setText(f"📂 当前: {sel_path[0]}")
            load_tree(path)

    tree.itemDoubleClicked.connect(on_dblclick)

    confirm.clicked.connect(dlg.accept)

    # 上级按钮
    def go_up():
        parent_path = os.path.dirname(sel_path[0])
        if parent_path and parent_path != sel_path[0]:
            # 跨驱动器时更新 combo
            for i in range(drive_combo.count()):
                d = drive_combo.itemData(i)
                if parent_path.lower().startswith(d.lower()):
                    drive_combo.blockSignals(True)
                    drive_combo.setCurrentIndex(i)
                    drive_combo.blockSignals(False)
                    break
            load_tree(parent_path)

    up_btn.clicked.connect(go_up)

    # 初始加载
    initial = start or os.path.expanduser("~")
    # 匹配驱动器
    for i in range(drive_combo.count()):
        d = drive_combo.itemData(i)
        if initial.lower().startswith(d.lower()):
            drive_combo.blockSignals(True)
            drive_combo.setCurrentIndex(i)
            drive_combo.blockSignals(False)
            break
    load_tree(initial)
    if parent and parent.isVisible():
        pc = parent.mapToGlobal(parent.rect().center())
        dlg.move(pc - dlg.rect().center())

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return os.path.normpath(sel_path[0])
    return None


def themed_input(parent, title, prompt, default=""):
    """自绘输入弹窗"""
    dlg, lay = _make_dialog(parent, title, 380, 150)
    lb = QLabel(prompt); lb.setStyleSheet(_STYLE_LABEL); lay.addWidget(lb)
    e = QLineEdit(default); e.setStyleSheet(_STYLE_INPUT); lay.addWidget(e)
    br = QHBoxLayout(); br.addStretch()
    ob = QPushButton(t("k_ok")); ob.setStyleSheet(_STYLE_BTN_OK)
    cb = QPushButton(t("k_cancel")); cb.setStyleSheet(_STYLE_BTN_GREY)
    br.addWidget(ob); br.addWidget(cb); lay.addLayout(br)
    ob.clicked.connect(dlg.accept); cb.clicked.connect(dlg.reject); e.returnPressed.connect(dlg.accept)
    if parent and parent.isVisible():
        pc = parent.mapToGlobal(parent.rect().center())
        dlg.move(pc - dlg.rect().center())
    return e.text().strip() if dlg.exec() == QDialog.DialogCode.Accepted else None


# 返回值常量
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
    dlg, lay = _make_dialog(parent, title, 440, 180)
    lb = QLabel(text); lb.setWordWrap(True); lb.setStyleSheet(_STYLE_LABEL)
    lay.addWidget(lb, 1)
    br = QHBoxLayout(); br.addStretch()
    result = MSG_ACCEPT

    if mode in ("info", "warning", "error"):
        ok = QPushButton(t("k_ok")); ok.setStyleSheet(_STYLE_BTN_OK)
        br.addWidget(ok); ok.clicked.connect(dlg.accept)
    elif mode == "question":
        no = QPushButton(t("_k_btn_no")); no.setStyleSheet(_STYLE_BTN_GREY)
        yes = QPushButton(t("_k_btn_yes")); yes.setStyleSheet(_STYLE_BTN_OK)
        br.addWidget(no); br.addWidget(yes)
        no.clicked.connect(dlg.reject)
        yes.clicked.connect(dlg.accept)
        result = MSG_REJECT  # default to no
    elif mode == "question3":
        cancel = QPushButton(t("k_cancel")); cancel.setStyleSheet(_STYLE_BTN_GREY)
        no = QPushButton(t("_k_btn_no")); no.setStyleSheet(_STYLE_BTN_GREY)
        yes = QPushButton(t("_k_btn_yes")); yes.setStyleSheet(_STYLE_BTN_OK)
        br.addWidget(cancel); br.addWidget(no); br.addWidget(yes)
        cancel.clicked.connect(lambda: setattr(dlg, '_result', MSG_CANCEL) or dlg.reject())
        no.clicked.connect(dlg.reject)
        yes.clicked.connect(dlg.accept)
        result = MSG_REJECT
        dlg._result = MSG_REJECT
        # Override exec to return custom codes
        orig_exec = dlg.exec
        def custom_exec():
            code = orig_exec()
            if hasattr(dlg, '_result') and code == 0:
                return dlg._result
            return MSG_ACCEPT if code == 1 else MSG_CANCEL
        dlg.exec = custom_exec

    lay.addLayout(br)

    # --- 居中 ---
    if parent and parent.isVisible():
        pc = parent.mapToGlobal(parent.rect().center())
        dlg.move(pc.x() - dlg.width() // 2, pc.y() - dlg.height() // 2)
    else:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            dlg.move(geo.center().x() - dlg.width() // 2,
                     geo.center().y() - dlg.height() // 2)

    # --- 点击空白处关闭（info/warning/error 模式）---
    if mode in ("info", "warning", "error"):
        c = dlg._container
        # 覆写容器的 mousePressEvent：容器填满整个对话框，
        # 但没有子控件的地方（布局间距、空白区）事件会落入容器本身
        old_mp = c.mousePressEvent
        c.mousePressEvent = lambda e: dlg.accept()
        dlg._old_container_mp = old_mp  # 保持引用防止 GC

    rc = dlg.exec()
    if mode == "question3":
        return rc if isinstance(rc, int) else MSG_CANCEL
    if mode == "question":
        return True if rc == QDialog.DialogCode.Accepted else False
    return None


def pick_file(parent, title, filter_ext=None, start=""):
    """自绘文件选择器 — 树形展开 + 驱动器切换 + 文件预览"""
    dlg, lay = _make_dialog(parent, title, 800, 520)

    # 驱动器选择 + 上级按钮 + 路径下拉
    drives = _get_drives()
    nav_bar = QHBoxLayout()
    
    # 驱动器选择
    drive_combo = QComboBox()
    drive_combo.setFixedWidth(70)
    drive_combo.setStyleSheet("QComboBox { background: #3c3c3c; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 2px 4px; font-size: 11px; } QComboBox QAbstractItemView { background: #252526; color: #ccc; }")
    for p, label in drives:
        drive_combo.addItem(f"  {label}  ", p)
    nav_bar.addWidget(drive_combo)
    
    # 上级按钮
    up_btn = QPushButton(f"↑ {t('_k_btn_up')}")
    up_btn.setFixedWidth(80)
    up_btn.setStyleSheet(_STYLE_BTN_GREY + "QPushButton { font-size: 11px; padding: 3px 8px; }")
    nav_bar.addWidget(up_btn)
    
    # 路径下拉浏览
    path_combo = QComboBox()
    path_combo.setStyleSheet("QComboBox { background: rgba(255,255,255,10); color: #d4d4d4; border: 1px solid rgba(255,255,255,15); border-radius: 4px; padding: 4px 10px; font-size: 12px; } QComboBox QAbstractItemView { background: #252526; color: #ccc; }")
    path_combo.setEditable(True)
    path_combo.lineEdit().returnPressed.connect(lambda: load_tree(path_combo.currentText().strip()))
    nav_bar.addWidget(path_combo, 1)
    
    nav_bar.addStretch()
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
    # 设置选择行为，确保点击行的任意部分都能选择整个行
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

    # 文件名输入（保存模式）
    file_name_edit = QLineEdit()
    file_name_edit.setStyleSheet(_STYLE_INPUT)
    file_name_edit.setPlaceholderText(t("_k_file_name_hint"))
    lay.addWidget(file_name_edit)

    # 按钮
    br = QHBoxLayout(); br.addStretch()
    cancel = QPushButton(t("k_cancel")); cancel.setStyleSheet(_STYLE_BTN_GREY)
    confirm = QPushButton(t("_k_btn_select")); confirm.setStyleSheet(_STYLE_BTN_OK)
    br.addWidget(cancel); br.addWidget(confirm); lay.addLayout(br)
    cancel.clicked.connect(dlg.reject)

    sel_path = [os.path.expanduser("~")]
    selected_file = [None]

    def load_tree(root_path):
        root_path = os.path.normpath(root_path)
        sel_path[0] = root_path
        
        # 更新路径下拉
        path_combo.blockSignals(True)
        path_combo.clear()
        # 添加路径面包屑到下拉
        parts = []
        current = root_path
        prev_path = ""
        while current and current != prev_path and current != os.sep:
            parts.insert(0, current)
            prev_path = current
            current = os.path.dirname(current)
        # 确保根目录也被添加
        if root_path and root_path not in parts:
            parts.insert(0, root_path)
        for p in parts:
            path_combo.addItem(p)
        path_combo.setCurrentText(root_path)
        path_combo.blockSignals(False)
        
        preview_info.setText(t("_k_folder_current").replace("{path}", root_path))
        tree.clear()
        if os.path.isdir(root_path):
            _load_files_and_dirs(tree.invisibleRootItem(), root_path)

    def _load_files_and_dirs(parent_item, full_path):
        """加载目录的文件和子目录"""
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
                    # 始终显示所有文件，但标记是否可选择
                    is_selectable = True
                    if filter_ext:
                        is_selectable = name.endswith(filter_ext)
                    files.append((name, sub, is_selectable))
            
            # 先添加目录
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
                except:
                    QTreeWidgetItem(child, ["...", ""])
            
            # 再添加文件
            for item in files:
                name, sub, is_selectable = item if len(item) == 3 else (item[0], item[1], True)
                child = QTreeWidgetItem(parent_item, [name, sub])
                child.setData(0, 1, sub)
                # 标记是否可选择，不可选择的文件灰色显示
                child.setData(0, 256, is_selectable)  # Qt.UserRole
                if not is_selectable:
                    child.setForeground(0, QColor(128, 128, 128))
                
        except PermissionError:
            QTreeWidgetItem(parent_item, ["❌ 无权限", ""])

    def _preview_file(file_path):
        """预览文本文件内容"""
        if not file_path or not os.path.isfile(file_path):
            preview_text.setPlainText("")
            preview_info.setText(t("_k_no_preview"))
            return
        
        try:
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 只预览文本文件且小于1MB
            if file_size > 1024 * 1024:
                preview_text.setPlainText(t("_k_file_too_large"))
                preview_info.setText(f"{os.path.basename(file_path)} - {file_size // 1024} KB")
                return
            
            # 尝试以文本方式读取
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(50000)  # 最多读取50KB
                preview_text.setPlainText(content)
                preview_info.setText(f"{os.path.basename(file_path)} - {file_size} bytes")
                
        except Exception as e:
            preview_text.setPlainText(t("_k_preview_error").format(error=str(e)))
            preview_info.setText(os.path.basename(file_path))

    def on_drive_change(idx):
        path = drive_combo.itemData(idx)
        load_tree(path)

    drive_combo.currentIndexChanged.connect(on_drive_change)

    def on_item_expanded(item):
        """展开时延迟加载子目录和文件"""
        child_count = item.childCount()
        if child_count == 1 and item.child(0).text(0) == "...":
            item.removeChild(item.child(0))
            full = item.data(0, 1)
            _load_files_and_dirs(item, full)

    tree.itemExpanded.connect(on_item_expanded)

    def on_select(item):
        if item is None:
            # 当没有项目被选中时，清除选择
            selected_file[0] = None
            file_name_edit.clear()
            _preview_file(None)
            return
            
        path = item.data(0, 1)
        is_selectable = item.data(0, 256) if item else True  # Qt.UserRole
        if path:
            if os.path.isdir(path):
                sel_path[0] = os.path.normpath(path)
                selected_file[0] = None
                file_name_edit.clear()
                _preview_file(None)
            else:
                # 只有可选择的文件才能被选中
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
        is_selectable = item.data(0, 256) if item else True  # Qt.UserRole
        if path:
            if os.path.isdir(path):
                sel_path[0] = os.path.normpath(path)
                load_tree(path)
            else:
                # 只有可选择的文件才能被双击选中
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

    confirm.clicked.connect(on_confirm)

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

    up_btn.clicked.connect(go_up)

    # 路径下拉选择
    def on_path_combo_select(idx):
        path = path_combo.itemText(idx)
        if path and os.path.isdir(path):
            load_tree(path)

    path_combo.currentIndexChanged.connect(on_path_combo_select)

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
    if parent and parent.isVisible():
        pc = parent.mapToGlobal(parent.rect().center())
        dlg.move(pc - dlg.rect().center())

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return selected_file[0]
    return None


def pick_save_file(parent, title, default_name="", filter_ext=None, start=""):
    """自绘文件保存对话框"""
    dlg, lay = _make_dialog(parent, title, 620, 440)

    # 驱动器选择 + 上级按钮
    drives = _get_drives()
    nav_bar = QHBoxLayout()
    drive_combo = QComboBox()
    drive_combo.setFixedWidth(70)
    drive_combo.setStyleSheet("QComboBox { background: #3c3c3c; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 2px 4px; font-size: 11px; } QComboBox QAbstractItemView { background: #252526; color: #ccc; }")
    for p, label in drives:
        drive_combo.addItem(f"  {label}  ", p)
    nav_bar.addWidget(drive_combo)
    up_btn = QPushButton(f"↑ {t('_k_btn_up')}")
    up_btn.setFixedWidth(80)
    up_btn.setStyleSheet(_STYLE_BTN_GREY + "QPushButton { font-size: 11px; padding: 3px 8px; }")
    nav_bar.addWidget(up_btn)
    nav_bar.addStretch()
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
    # 设置选择行为，确保点击行的任意部分都能选择整个行
    tree.setUniformRowHeights(True)
    tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
    tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
    lay.addWidget(tree, 1)

    # 文件名输入
    file_name_edit = QLineEdit(default_name)
    file_name_edit.setStyleSheet(_STYLE_INPUT)
    file_name_edit.setPlaceholderText(t("_k_file_name_hint"))
    lay.addWidget(file_name_edit)

    # 按钮
    br = QHBoxLayout(); br.addStretch()
    cancel = QPushButton(t("k_cancel")); cancel.setStyleSheet(_STYLE_BTN_GREY)
    confirm = QPushButton(t("_k_btn_save")); confirm.setStyleSheet(_STYLE_BTN_OK)
    br.addWidget(cancel); br.addWidget(confirm); lay.addLayout(br)
    cancel.clicked.connect(dlg.reject)

    sel_path = [os.path.expanduser("~")]

    def load_tree(root_path):
        root_path = os.path.normpath(root_path)
        sel_path[0] = root_path
        current.setText(t("_k_folder_current").replace("{path}", root_path))
        tree.clear()
        if os.path.isdir(root_path):
            _load_files_and_dirs(root_path)

    def _load_files_and_dirs(full_path, parent_item=None):
        """加载目录的文件和子目录"""
        if not os.path.isdir(full_path):
            return
        # 如果没有指定父项，使用树的根项
        if parent_item is None:
            parent_item = tree.invisibleRootItem()
        try:
            dirs = []
            files = []
            for name in sorted(os.listdir(full_path)):
                sub = os.path.join(full_path, name)
                if os.path.isdir(sub) and not name.startswith('.') and not name.startswith('$'):
                    dirs.append((name, sub))
                elif os.path.isfile(sub):
                    # 始终显示所有文件，但标记是否可选择
                    is_selectable = True
                    if filter_ext:
                        is_selectable = name.endswith(filter_ext)
                    files.append((name, sub, is_selectable))
            
            # 先添加目录
            for name, sub in dirs:
                child = QTreeWidgetItem(parent_item, [name, sub])
                child.setData(0, 1, sub)
                try:
                    for _ in sorted(os.listdir(sub)):
                        sub_full = os.path.join(sub, _)
                        if os.path.isdir(sub_full) and not _.startswith('.') and not _.startswith('$'):
                            QTreeWidgetItem(child, ["...", ""])
                            break
                except:
                    QTreeWidgetItem(child, ["...", ""])
            
            # 再添加文件
            for item in files:
                name, sub, is_selectable = item if len(item) == 3 else (item[0], item[1], True)
                child = QTreeWidgetItem(parent_item, [name, sub])
                child.setData(0, 1, sub)
                # 标记是否可选择，不可选择的文件灰色显示
                child.setData(0, 256, is_selectable)  # Qt.UserRole
                if not is_selectable:
                    child.setForeground(0, QColor(128, 128, 128))
                
        except PermissionError:
            QTreeWidgetItem(parent_item, ["❌ 无权限", ""])

    def on_drive_change(idx):
        path = drive_combo.itemData(idx)
        load_tree(path)

    drive_combo.currentIndexChanged.connect(on_drive_change)

    def on_item_expanded(item):
        """展开时延迟加载子目录和文件"""
        child_count = item.childCount()
        if child_count == 1 and item.child(0).text(0) == "...":
            item.removeChild(item.child(0))
            full = item.data(0, 1)
            _load_files_and_dirs(full, item)

    tree.itemExpanded.connect(on_item_expanded)

    def on_select(item):
        path = item.data(0, 1)
        if path:
            if os.path.isdir(path):
                sel_path[0] = os.path.normpath(path)
            else:
                sel_path[0] = os.path.normpath(os.path.dirname(path))
                file_name_edit.setText(os.path.basename(path))
            current.setText(f"📂 当前: {sel_path[0]}")

    tree.currentItemChanged.connect(lambda cur, prev: on_select(cur) if cur else None)

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

    confirm.clicked.connect(on_confirm)

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

    up_btn.clicked.connect(go_up)

    initial = start or os.path.expanduser("~")
    for i in range(drive_combo.count()):
        d = drive_combo.itemData(i)
        if initial.lower().startswith(d.lower()):
            drive_combo.blockSignals(True)
            drive_combo.setCurrentIndex(i)
            drive_combo.blockSignals(False)
            break
    load_tree(initial)
    if parent and parent.isVisible():
        pc = parent.mapToGlobal(parent.rect().center())
        dlg.move(pc - dlg.rect().center())

    dlg.selected_path = None
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.selected_path
    return None


# 向后兼容
themed_question = lambda p, t, x: themed_message(p, t, x, "question")