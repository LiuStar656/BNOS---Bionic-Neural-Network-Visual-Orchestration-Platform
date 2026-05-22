"""
统一深色对话框工具 — 确保非原生 Qt 渲染
"""
from PyQt6.QtWidgets import (QFileDialog, QDialog, QVBoxLayout, QLabel,
                               QPushButton, QHBoxLayout, QWidget, QLineEdit)
from PyQt6.QtCore import Qt


def pick_folder(parent, title, start=""):
    """选择文件夹 — 强制非原生 Qt 渲染"""
    dlg = QFileDialog(parent, title, start)
    dlg.setFileMode(QFileDialog.FileMode.Directory)
    dlg.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dlg.setOption(QFileDialog.Option.ShowDirsOnly, True)
    dlg.setStyleSheet("QFileDialog { background-color: #252526; } QFileDialog QLabel, QFileDialog QTreeView, QFileDialog QListView { color: #cccccc; background-color: #252526; } QFileDialog QPushButton { background: #0e639c; color: white; border: none; padding: 6px 14px; border-radius: 3px; } QFileDialog QPushButton:hover { background: #1177bb; }")
    if dlg.exec() == QDialog.DialogCode.Accepted:
        files = dlg.selectedFiles()
        return files[0] if files else None
    return None


def themed_question(parent, title, text):
    """深色确认对话框 — 替代 QMessageBox.question"""
    dlg = QDialog(parent)
    dlg.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
    dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dlg.resize(420, 160)
    outer = QVBoxLayout(dlg); outer.setContentsMargins(0,0,0,0)
    c = QWidget(); c.setStyleSheet("QWidget { background-color: rgba(30,30,30,220); border-radius: 8px; border: 1px solid rgba(255,255,255,25); }")
    outer.addWidget(c)
    lay = QVBoxLayout(c); lay.setContentsMargins(16,12,16,12); lay.setSpacing(10)
    tl = QLabel(title); tl.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent;")
    lay.addWidget(tl)
    lb = QLabel(text); lb.setWordWrap(True); lb.setStyleSheet("color: rgba(255,255,255,180); font-size: 12px; background: transparent;")
    lay.addWidget(lb)
    br = QHBoxLayout(); br.addStretch()
    no = QPushButton("否"); no.setStyleSheet("QPushButton { background: rgba(255,255,255,10); color: #ccc; border: 1px solid rgba(255,255,255,15); border-radius: 4px; padding: 6px 20px; } QPushButton:hover { background: rgba(255,255,255,20); }")
    yes = QPushButton("是"); yes.setStyleSheet("QPushButton { background: rgba(0,120,212,200); color: white; border: none; border-radius: 4px; padding: 6px 20px; } QPushButton:hover { background: rgba(0,140,240,220); }")
    br.addWidget(no); br.addWidget(yes); lay.addLayout(br)
    no.clicked.connect(dlg.reject); yes.clicked.connect(dlg.accept)
    if parent: dlg.move(parent.geometry().center() - dlg.rect().center())
    return True if dlg.exec() == QDialog.DialogCode.Accepted else False
