"""
共享的节点树组件 — 供 NodeListDockPanel 和 NodeListPanel 共用
消除 ~400 行重复代码
"""
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class NodeTreeWidget(QTreeWidget):
    """节点树形组件 — 统一树渲染、状态显示、拖拽支持"""

    node_selected = pyqtSignal(str)
    node_context_menu = pyqtSignal(str)
    node_double_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setIndentation(16)
        self.itemClicked.connect(self._on_click)
        self.itemDoubleClicked.connect(self._on_double_click)

    def add_node(self, name: str, status: str = "stopped", icon=None):
        item = QTreeWidgetItem(self)
        item.setText(0, name)
        item.setData(0, Qt.ItemDataRole.UserRole, name)
        self._apply_status(item, status)
        return item

    def update_node_status(self, name: str, status: str):
        items = self.findItems(name, Qt.MatchFlag.MatchExactly, 0)
        for item in items:
            self._apply_status(item, status)

    def _apply_status(self, item: QTreeWidgetItem, status: str):
        color_map = {
            "running":  "#6a9955",
            "starting": "#dcdcaa",
            "stopping": "#ce9178",
            "stopped":  "#808080",
            "error":    "#f44747",
        }
        item.setForeground(0, QColor(color_map.get(status, "#808080")))

    def _on_click(self, item, col):
        self.node_selected.emit(item.data(0, Qt.ItemDataRole.UserRole))

    def _on_double_click(self, item, col):
        self.node_double_clicked.emit(item.data(0, Qt.ItemDataRole.UserRole))
