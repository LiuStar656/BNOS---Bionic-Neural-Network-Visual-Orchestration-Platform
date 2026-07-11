"""
ui/canvas/items/composite_group_frame.py
Dashed bounding frame for expanded composite nodes.
Supports right-click context menu to collapse back.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QMenu,
    QStyleOptionGraphicsItem,
    QWidget,
)


class CompositeGroupFrame(QGraphicsRectItem):
    """Dashed bounding rectangle around expanded composite node internals.

    Right-click the frame to collapse the composite back.
    """

    BORDER_COLOR = QColor("#4ec9b0")
    FILL_COLOR = QColor(78, 201, 176, 12)
    PADDING = 30
    COLLAPSE_BTN_W = 80
    COLLAPSE_BTN_H = 22

    def __init__(self, comp_id: str, display_name: str, child_items: list, composite_manager=None, parent=None):
        super().__init__(parent)
        self._comp_id = comp_id
        self._display_name = display_name
        self._child_items = child_items
        self._composite_manager = composite_manager

        self.setZValue(5)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)

        self._pen = QPen(self.BORDER_COLOR, 2, Qt.PenStyle.DashLine)
        self._brush = QBrush(self.FILL_COLOR)
        self._label_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        self._btn_font = QFont("Segoe UI", 9)
        self._btn_hover = False
        self._refresh_bounds()

    def _refresh_bounds(self):
        """Recalculate bounds to enclose all child items."""
        if not self._child_items:
            self.setRect(0, 0, 200, 100)
            return

        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")
        for item in self._child_items:
            if not item.isVisible():
                continue
            r = item.sceneBoundingRect()
            min_x = min(min_x, r.left())
            min_y = min(min_y, r.top())
            max_x = max(max_x, r.right())
            max_y = max(max_y, r.bottom())

        if min_x == float("inf"):
            self.setRect(0, 0, 200, 100)
            return

        self.setRect(
            min_x - self.PADDING,
            min_y - self.PADDING - 25,
            max_x - min_x + self.PADDING * 2,
            max_y - min_y + self.PADDING * 2 + 25,
        )

    def _collapse_btn_rect(self) -> QRectF:
        """Button rect in top-right corner of the frame."""
        r = self.rect()
        return QRectF(r.right() - self.COLLAPSE_BTN_W - 10, r.y() + 3, self.COLLAPSE_BTN_W, self.COLLAPSE_BTN_H)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()

        # Semi-transparent fill
        painter.setBrush(self._brush)
        painter.setPen(self._pen)
        painter.drawRoundedRect(rect, 6, 6)

        # Top-left label
        label_rect = QRectF(rect.x() + 10, rect.y() + 4, rect.width() - self.COLLAPSE_BTN_W - 30, 20)
        painter.setPen(QColor("#4ec9b0"))
        painter.setFont(self._label_font)
        label_text = f"[Composite] {self._display_name or self._comp_id[:12]}"
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label_text)

        # Collapse button (top-right)
        btn_rect = self._collapse_btn_rect()
        if self._btn_hover:
            painter.setBrush(QColor("#4ec9b0"))
            painter.setPen(QPen(QColor("#3a9a8a"), 1))
        else:
            painter.setBrush(QColor(78, 201, 176, 40))
            painter.setPen(QPen(QColor("#4ec9b0"), 1))
        painter.drawRoundedRect(btn_rect, 4, 4)

        painter.setPen(QColor("#4ec9b0") if not self._btn_hover else QColor("#1e1e1e"))
        painter.setFont(self._btn_font)
        painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, "Collapse")

    # ── Interaction ──

    def shape(self):
        """Only the collapse button area is interactive.
        Clicks elsewhere pass through to items behind the frame."""
        from PySide6.QtGui import QPainterPath

        path = QPainterPath()
        path.addRect(self._collapse_btn_rect())
        return path

    def hoverMoveEvent(self, event):
        was_hover = self._btn_hover
        self._btn_hover = True  # shape ensures we only get events over the button
        if was_hover != self._btn_hover:
            self.update()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def hoverLeaveEvent(self, event):
        self._btn_hover = False
        self.update()
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._do_collapse()
            event.accept()
        else:
            super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("QMenu { background: #2b2b2b; color: #ccc; }")
        collapse_action = menu.addAction("Collapse Composite")
        collapse_action.triggered.connect(self._do_collapse)
        menu.exec(event.screenPos())

    def _do_collapse(self):
        """Collapse this expanded composite back to a single item."""
        if self._composite_manager:
            self._composite_manager.toggle_expand(self._comp_id)

    def update_for_items(self, child_items: list):
        """Update bounds when child items change."""
        self._child_items = child_items
        self._refresh_bounds()
        self.update()
