"""
统一深色对话框工具 — 完全自绘，不依赖 Windows 原生组件
"""
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
                               QWidget, QLineEdit, QTreeWidget, QTreeWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QFont, QIcon


_STYLE_CONTAINER = "QWidget { background-color: rgba(30,30,30,220); border-radius: 8px; border: 1px solid rgba(255,255,255,25); }"
_STYLE_TITLE    = "color: white; font-size: 13px; font-weight: bold; background: transparent;"
_STYLE_LABEL    = "color: rgba(255,255,255,180); font-size: 12px; background: transparent;"
_STYLE_INPUT    = "background: rgba(255,255,255,10); color: #d4d4d4; border: 1px solid rgba(255,255,255,15); border-radius: 4px; padding: 6px 10px; font-size: 13px;"
_STYLE_BTN_OK   = "QPushButton { background: rgba(0,120,212,200); color: white; border: none; border-radius: 4px; padding: 6px 20px; } QPushButton:hover { background: rgba(0,140,240,220); }"
_STYLE_BTN_GREY = "QPushButton { background: rgba(255,255,255,10); color: #ccc; border: 1px solid rgba(255,255,255,15); border-radius: 4px; padding: 6px 20px; } QPushButton:hover { background: rgba(255,255,255,20); }"


def _make_dialog(parent, title, width, height):
    dlg = QDialog(parent)
    dlg.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
    dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dlg.resize(width, height)
    outer = QVBoxLayout(dlg); outer.setContentsMargins(0,0,0,0)
    c = QWidget(); c.setStyleSheet(_STYLE_CONTAINER); outer.addWidget(c)
    lay = QVBoxLayout(c); lay.setContentsMargins(14,10,14,10); lay.setSpacing(6)
    bar = QHBoxLayout()
    tl = QLabel(title); tl.setStyleSheet(_STYLE_TITLE); bar.addWidget(tl); bar.addStretch()
    xl = QLabel("x"); xl.setStyleSheet("color: rgba(255,255,255,150); font-size: 14px; padding:0 5px; background:transparent;"); xl.setCursor(Qt.CursorShape.PointingHandCursor)
    xl.mousePressEvent = lambda e: dlg.reject(); bar.addWidget(xl); lay.addLayout(bar)
    return dlg, lay


def pick_folder(parent, title, start=""):
    """自绘文件夹选择器"""
    dlg, lay = _make_dialog(parent, title, 600, 420)
    # 路径快捷
    path_bar = QHBoxLayout()
    current = QLabel(start or os.path.expanduser("~"))
    current.setStyleSheet("color: rgba(255,255,255,120); font-size: 11px; background: transparent;")
    path_bar.addWidget(current)
    up_btn = QPushButton("↑ 上级"); up_btn.setStyleSheet(_STYLE_BTN_GREY)
    path_bar.addWidget(up_btn)
    lay.addLayout(path_bar)
    # 目录树
    tree = QTreeWidget()
    tree.setHeaderLabels(["名称", "修改时间"])
    tree.setColumnWidth(0, 400)
    tree.header().setStretchLastSection(True)
    tree.setStyleSheet("QTreeWidget { background-color: #252526; color: #cccccc; border: 1px solid rgba(255,255,255,10); border-radius: 4px; } QTreeWidget::item { padding: 3px; } QTreeWidget::item:hover { background: #2a2d2e; } QTreeWidget::item:selected { background: #094771; } QHeaderView::section { background: #333; color: #aaa; border: none; padding: 3px; }")
    lay.addWidget(tree, 1)
    # 按钮
    br = QHBoxLayout(); br.addStretch()
    cancel = QPushButton("取消"); cancel.setStyleSheet(_STYLE_BTN_GREY)
    confirm = QPushButton("选择"); confirm.setStyleSheet(_STYLE_BTN_OK)
    br.addWidget(cancel); br.addWidget(confirm); lay.addLayout(br)
    cancel.clicked.connect(dlg.reject); confirm.clicked.connect(dlg.accept)
    tree.itemDoubleClicked.connect(dlg.accept)

    def load_dir(path):
        current.setText(path)
        tree.clear()
        try:
            tree.addTopLevelItem(_make_item("📁 ..", os.path.dirname(path), True))
            items = sorted(os.listdir(path))
            dirs, files = [], []
            for n in items:
                p = os.path.join(path, n)
                if os.path.isdir(p) and not n.startswith('.'): dirs.append(n)
                elif os.path.isfile(p) and not n.startswith('.'): files.append(n)
            for name in dirs:
                tree.addTopLevelItem(_make_item(f"📁 {name}", os.path.join(path, name), True))
            for name in files:
                tree.addTopLevelItem(_make_item(f"📄 {name}", os.path.join(path, name), False))
        except PermissionError:
            tree.addTopLevelItem(QTreeWidgetItem(["❌ 无权限", ""]))

    def _make_item(text, full, is_dir):
        item = QTreeWidgetItem([text, ""])
        item.setData(0, 1, full)
        item.setData(0, 2, is_dir)
        return item

    up_btn.clicked.connect(lambda: load_dir(os.path.dirname(current.text())))

    def on_select_item(item, col):
        path = item.data(0, 1)
        is_dir = item.data(0, 2)
        if is_dir:
            load_dir(path)

    tree.itemClicked.connect(on_select_item)

    sel_path = [start or os.path.expanduser("~")]
    def on_confirm():
        item = tree.currentItem()
        if item:
            p = item.data(0, 1)
            if item.data(0, 2):
                sel_path[0] = os.path.normpath(p)
            else:
                sel_path[0] = os.path.normpath(os.path.dirname(p))
        dlg.accept()

    confirm.clicked.disconnect()
    confirm.clicked.connect(on_confirm)
    tree.itemDoubleClicked.disconnect()
    tree.itemDoubleClicked.connect(on_confirm)

    load_dir(start or os.path.expanduser("~"))
    dlg.move(parent.geometry().center() - dlg.rect().center()) if parent else None
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
