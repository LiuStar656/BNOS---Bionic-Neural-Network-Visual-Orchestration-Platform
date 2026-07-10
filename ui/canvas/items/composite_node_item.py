"""
ui/canvas/items/composite_node_item.py
复合节点的画布元素。
外观：虚线边框 + 青绿配色 + 内部节点数标记 + ⊞ 图标。

继承 QGraphicsRectItem，与 NodeItem 平级作为画布可拖拽元素。
"""
import os

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPen, QBrush, QPainter, QFont
from PySide6.QtWidgets import (
    QGraphicsRectItem, QGraphicsItem, QStyleOptionGraphicsItem, QWidget,
    QMenu, QMessageBox,
)


class CompositeNodeItem(QGraphicsRectItem):
    """复合节点画布元素。"""

    WIDTH = 180
    HEIGHT = 85
    BORDER_COLOR = QColor("#4ec9b0")
    FILL_COLOR = QColor("#1e3a3a")
    SELECTED_BORDER = QColor("#6ee9d0")

    def __init__(self, comp_id: str, node_count: int, node_names: list,
                 canvas=None, parent=None):
        super().__init__(parent)
        self.comp_id = comp_id
        self.node_count = node_count
        self.node_names = node_names
        self._canvas = canvas

        self.setRect(0, 0, self.WIDTH, self.HEIGHT)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(10)

        self._pen = QPen(self.BORDER_COLOR, 2, Qt.PenStyle.DashLine)
        self._brush = QBrush(self.FILL_COLOR)
        self._font_bold = QFont("Segoe UI", 11, QFont.Weight.Bold)
        self._font_small = QFont("Segoe UI", 9)

    # ── S14: 拖拽位置持久化 ──

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._canvas and hasattr(self._canvas, '_composite_manager'):
                mgr = self._canvas._composite_manager
                comp = mgr._composites.get(self.comp_id)
                if comp:
                    comp["canvas_position"] = {"x": value.x(), "y": value.y()}
                    mgr.save()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()

        # 背景
        painter.setBrush(self._brush)
        if self.isSelected():
            painter.setPen(QPen(self.SELECTED_BORDER, 2.5, Qt.PenStyle.DashLine))
        else:
            painter.setPen(self._pen)
        painter.drawRoundedRect(rect, 8, 8)

        # 图标区域（左侧 ⊞）
        icon_rect = QRectF(rect.x() + 8, rect.y() + 12, 28, 28)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4ec9b0"))
        painter.drawRoundedRect(icon_rect, 4, 4)

        painter.setPen(QColor("#1e1e1e"))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "\u229e")

        # 名称
        name_rect = QRectF(icon_rect.right() + 8, rect.y() + 10,
                           rect.width() - icon_rect.right() - 16, 22)
        painter.setPen(QColor("#4ec9b0"))
        painter.setFont(self._font_bold)
        short_id = self.comp_id.replace("composite_", "")[:6]
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                         f"\u590d\u5408\u8282\u70b9 {short_id}")

        # 节点数 + 运行时模式
        sub_rect = QRectF(name_rect.x(), name_rect.bottom() + 2, name_rect.width(), 20)
        painter.setPen(QColor("#888"))
        painter.setFont(self._font_small)

        runtime = "inprocess"
        if self._canvas and hasattr(self._canvas, '_composite_manager'):
            runtime = self._canvas._composite_manager.get_runtime(self.comp_id) or "inprocess"

        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignLeft,
                         f"{self.node_count} \u4e2a\u8282\u70b9 \u00b7 {runtime}")

        # 底部节点名列表（缩略）
        detail_rect = QRectF(rect.x() + 8, sub_rect.bottom() + 2,
                             rect.width() - 16, 18)
        painter.setPen(QColor("#666"))
        painter.setFont(QFont("Segoe UI", 8))
        names = ", ".join(self.node_names[:3])
        if len(self.node_names) > 3:
            names += f" +{len(self.node_names) - 3}"
        painter.drawText(detail_rect, Qt.AlignmentFlag.AlignLeft, names)

    # ── 右键菜单 ──

    def contextMenuEvent(self, event):
        """复合节点右键菜单。"""
        menu = QMenu()
        menu.setStyleSheet("QMenu { background: #2b2b2b; color: #ccc; }")

        decompress_action = menu.addAction("\u89e3\u8026\u4e3a\u72ec\u7acb\u8282\u70b9")
        decompress_action.triggered.connect(self._decompress)

        menu.addSeparator()

        runtime_menu = menu.addMenu("\u8fd0\u884c\u65f6\u6a21\u5f0f")

        mgr = self._get_manager()
        current_runtime = mgr.get_runtime(self.comp_id) if mgr else "inprocess"

        proc_action = runtime_menu.addAction("\u72ec\u7acb\u8fdb\u7a0b (process)")
        inproc_action = runtime_menu.addAction("\u5355\u8fdb\u7a0b (inprocess)")
        proc_action.setCheckable(True)
        inproc_action.setCheckable(True)
        if current_runtime == "process":
            proc_action.setChecked(True)
        else:
            inproc_action.setChecked(True)
        proc_action.triggered.connect(lambda: self._set_runtime("process"))
        inproc_action.triggered.connect(lambda: self._set_runtime("inprocess"))

        menu.addSeparator()

        start_action = menu.addAction("\u542f\u52a8\u590d\u5408\u8282\u70b9")
        stop_action = menu.addAction("\u505c\u6b62\u590d\u5408\u8282\u70b9")
        start_action.triggered.connect(self._start)
        stop_action.triggered.connect(self._stop)

        menu.exec(event.screenPos())

    def _get_manager(self):
        if self._canvas and hasattr(self._canvas, '_composite_manager'):
            return self._canvas._composite_manager
        return None

    def _decompress(self):
        reply = QMessageBox.question(
            None, "\u786e\u8ba4\u89e3\u8026",
            f"\u5c06\u590d\u5408\u8282\u70b9\u8fd8\u539f\u4e3a {self.node_count} \u4e2a\u72ec\u7acb\u8282\u70b9\uff0c\n\u786e\u5b9a\u8981\u7ee7\u7eed\u5417\uff1f",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        mgr = self._get_manager()
        if mgr:
            ok, msg = mgr.decompress(self.comp_id)
            if not ok:
                QMessageBox.warning(None, "\u89e3\u8026\u5931\u8d25", msg)

    def _set_runtime(self, mode):
        mgr = self._get_manager()
        if mgr:
            mgr.set_runtime(self.comp_id, mode)
            self.update()

    def _start(self):
        mgr = self._get_manager()
        if not mgr:
            return
        runtime = mgr.get_runtime(self.comp_id) or "inprocess"
        if runtime == "inprocess":
            ok, msg = mgr.start_inprocess(self.comp_id)
        else:
            ok, msg = mgr.start_process_mode(self.comp_id)
        if not ok:
            QMessageBox.warning(None, "\u542f\u52a8\u5931\u8d25", msg)

    def _stop(self):
        mgr = self._get_manager()
        if mgr:
            mgr.stop_composite(self.comp_id)
