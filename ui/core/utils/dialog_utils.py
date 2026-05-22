"""
统一深色对话框工具 — 完全自绘，不依赖 Windows 原生组件
"""
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
                               QWidget, QLineEdit, QTreeWidget, QTreeWidgetItem,
                               QComboBox, QHeaderView)
from PyQt6.QtCore import Qt, QDir, QTimer
from PyQt6.QtGui import QFont


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
    return dlg, lay


def _get_drives():
    """获取 Windows 驱动器列表"""
    drives = []
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
    if not drives:
        drives.append(("/", "根"))
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
    nav_bar = QHBoxLayout()
    drive_combo = QComboBox()
    drive_combo.setFixedWidth(70)
    drive_combo.setStyleSheet("QComboBox { background: #3c3c3c; color: #ccc; border: 1px solid #555; border-radius: 3px; padding: 2px 4px; font-size: 11px; } QComboBox QAbstractItemView { background: #252526; color: #ccc; }")
    for p, label in drives:
        drive_combo.addItem(f"  {label}  ", p)
    nav_bar.addWidget(drive_combo)
    up_btn = QPushButton("↑ 上级")
    up_btn.setFixedWidth(60)
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
    tree.setHeaderLabels(["📁 文件夹", "路径"])
    tree.setColumnWidth(0, 300)
    tree.header().setStretchLastSection(True)
    tree.setStyleSheet(_STYLE_TREE)
    tree.setIndentation(16)
    lay.addWidget(tree, 1)

    # 按钮
    br = QHBoxLayout(); br.addStretch()
    cancel = QPushButton("取消"); cancel.setStyleSheet(_STYLE_BTN_GREY)
    confirm = QPushButton("选择此文件夹"); confirm.setStyleSheet(_STYLE_BTN_OK)
    br.addWidget(cancel); br.addWidget(confirm); lay.addLayout(br)
    cancel.clicked.connect(dlg.reject)

    sel_path = [os.path.expanduser("~")]

    def load_tree(root_path):
        root_path = os.path.normpath(root_path)
        sel_path[0] = root_path
        current.setText(f"📂 当前: {root_path}")
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
    if parent:
        dlg.move(parent.geometry().center() - dlg.rect().center())

    if dlg.exec() == QDialog.DialogCode.Accepted:
        return os.path.normpath(sel_path[0])
    return None


def themed_input(parent, title, prompt, default=""):
    """自绘输入弹窗"""
    dlg, lay = _make_dialog(parent, title, 380, 150)
    lb = QLabel(prompt); lb.setStyleSheet(_STYLE_LABEL); lay.addWidget(lb)
    e = QLineEdit(default); e.setStyleSheet(_STYLE_INPUT); lay.addWidget(e)
    br = QHBoxLayout(); br.addStretch()
    ob = QPushButton("确定"); ob.setStyleSheet(_STYLE_BTN_OK)
    cb = QPushButton("取消"); cb.setStyleSheet(_STYLE_BTN_GREY)
    br.addWidget(ob); br.addWidget(cb); lay.addLayout(br)
    ob.clicked.connect(dlg.accept); cb.clicked.connect(dlg.reject); e.returnPressed.connect(dlg.accept)
    if parent: dlg.move(parent.geometry().center() - dlg.rect().center())
    return e.text().strip() if dlg.exec() == QDialog.DialogCode.Accepted else None


def themed_question(parent, title, text):
    """自绘确认弹窗（是/否）"""
    dlg, lay = _make_dialog(parent, title, 420, 160)
    lb = QLabel(text); lb.setWordWrap(True); lb.setStyleSheet(_STYLE_LABEL); lay.addWidget(lb)
    br = QHBoxLayout(); br.addStretch()
    no = QPushButton("否"); no.setStyleSheet(_STYLE_BTN_GREY)
    yes = QPushButton("是"); yes.setStyleSheet(_STYLE_BTN_OK)
    br.addWidget(no); br.addWidget(yes); lay.addLayout(br)
    no.clicked.connect(dlg.reject); yes.clicked.connect(dlg.accept)
    if parent: dlg.move(parent.geometry().center() - dlg.rect().center())
    return True if dlg.exec() == QDialog.DialogCode.Accepted else False
