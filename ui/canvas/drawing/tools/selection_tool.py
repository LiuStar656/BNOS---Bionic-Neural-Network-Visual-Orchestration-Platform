"""
选择工具 — 负责图形的选择、移动、控制点编辑、多选、框选
"""
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QColor, QBrush
from PySide6.QtWidgets import QGraphicsItem

from .tool_base import ToolBase, ToolResult
from ui.canvas.drawing.graphic_items import GraphicBase, TextGraphic


class SelectionTool(ToolBase):
    """选择工具：选中、移动、控制点编辑、多选、框选"""

    def __init__(self, draw_layer):
        super().__init__(draw_layer, "select")
        self._drag_start = None
        self._dragging_handle = -1
        self._dragging_graphic = None
        self._marquee = None          # 框选矩形
        self._marquee_start = None

    def on_activate(self):
        self.canvas.viewport().setCursor(Qt.CursorShape.ArrowCursor)

    def mouse_press(self, event, scene_pos: QPointF) -> ToolResult:
        modifiers = event.modifiers()
        item = self.canvas.scene.itemAt(scene_pos, self.canvas.transform())

        # 查找点击的图形
        graphic = None
        while item:
            if isinstance(item, (GraphicBase, TextGraphic)) and item in self.draw_layer.graphics:
                graphic = item
                break
            item = item.parentItem()

        if graphic:
            # Ctrl+点击：切换多选状态
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                if graphic in self.draw_layer.selected_graphics():
                    self.draw_layer.deselect_graphic(graphic)
                else:
                    self.draw_layer.select_graphic(graphic, append=True)
                return ToolResult.HANDLED

            # 命中控制点
            if isinstance(graphic, GraphicBase):
                idx = graphic.hit_handle(scene_pos)
                if idx >= 0:
                    self.draw_layer._save_undo()
                    self._dragging_graphic = graphic
                    self._dragging_handle = idx
                    # 单选该图形
                    self.draw_layer.select_graphic(graphic)
                    return ToolResult.HANDLED

            # 开始拖拽图形
            self.draw_layer._save_undo()
            self._dragging_graphic = graphic
            self._drag_start = scene_pos
            self.draw_layer.select_graphic(graphic)
            return ToolResult.HANDLED

        # 空白处点击：开始框选或取消选择
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Ctrl+空白：保持现有选择，开始框选加选
            pass
        else:
            # 空白点击：取消所有选择
            self.draw_layer.deselect_all()

        self._marquee_start = scene_pos
        self._create_marquee(scene_pos)
        return ToolResult.HANDLED

    def mouse_move(self, event, scene_pos: QPointF) -> ToolResult:
        # 控制点拖拽
        if self._dragging_handle >= 0 and self._dragging_graphic:
            self._dragging_graphic.move_handle(self._dragging_handle, scene_pos)
            return ToolResult.HANDLED

        # 图形拖拽
        if self._dragging_graphic and self._drag_start:
            delta = scene_pos - self._drag_start
            self._dragging_graphic.moveBy(delta.x(), delta.y())
            self._drag_start = scene_pos
            return ToolResult.HANDLED

        # 框选
        if self._marquee_start and self._marquee:
            self._update_marquee(scene_pos)
            return ToolResult.HANDLED

        # Hover 效果：光标变化
        item = self.canvas.scene.itemAt(scene_pos, self.canvas.transform())
        graphic = None
        while item:
            if isinstance(item, (GraphicBase, TextGraphic)) and item in self.draw_layer.graphics:
                graphic = item
                break
            item = item.parentItem()

        if graphic and isinstance(graphic, GraphicBase) and graphic.hit_handle(scene_pos) >= 0:
            self.canvas.viewport().setCursor(Qt.CursorShape.SizeAllCursor)
        elif graphic:
            self.canvas.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.canvas.viewport().setCursor(Qt.CursorShape.ArrowCursor)

        return ToolResult.IGNORED

    def mouse_release(self, event, scene_pos: QPointF) -> ToolResult:
        # 控制点释放
        if self._dragging_graphic and self._dragging_handle >= 0:
            self._dragging_handle = -1
            self._dragging_graphic = None
            self.canvas._save_timer.start(500)
            return ToolResult.HANDLED

        # 图形拖拽释放
        if self._dragging_graphic:
            self._dragging_graphic = None
            self._drag_start = None
            self.canvas._save_timer.start(500)
            return ToolResult.HANDLED

        # 框选结束
        if self._marquee_start and self._marquee:
            self._finish_marquee(scene_pos, event.modifiers())
            return ToolResult.HANDLED

        return ToolResult.IGNORED

    def mouse_double_click(self, event, scene_pos: QPointF) -> ToolResult:
        """双击进入文本编辑"""
        item = self.canvas.scene.itemAt(scene_pos, self.canvas.transform())
        while item:
            if isinstance(item, TextGraphic) and item in self.draw_layer.graphics:
                self.draw_layer.start_text_editing(item)
                return ToolResult.HANDLED
            item = item.parentItem()
        return ToolResult.IGNORED

    def key_press(self, event) -> ToolResult:
        key = event.key()

        # Delete：删除选中
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected = self.draw_layer.selected_graphics()
            if selected:
                self.draw_layer._save_undo()
                self.draw_layer.delete_graphics(selected)
                return ToolResult.HANDLED

        # 方向键：微调位置
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            selected = self.draw_layer.selected_graphics()
            if not selected:
                return ToolResult.IGNORED
            step = 10 if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else 1
            dx = dy = 0
            if key == Qt.Key.Key_Left: dx = -step
            elif key == Qt.Key.Key_Right: dx = step
            elif key == Qt.Key.Key_Up: dy = -step
            elif key == Qt.Key.Key_Down: dy = step
            self.draw_layer._save_undo()
            for g in selected:
                g.moveBy(dx, dy)
            self.canvas._save_timer.start(500)
            return ToolResult.HANDLED

        # Ctrl+A：全选
        if key == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.draw_layer.select_all()
            return ToolResult.HANDLED

        # Ctrl+D：取消选择
        if key == Qt.Key.Key_D and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.draw_layer.deselect_all()
            return ToolResult.HANDLED

        return ToolResult.IGNORED

    # ── 框选辅助 ──

    def _create_marquee(self, pos: QPointF):
        """创建框选矩形"""
        from PySide6.QtWidgets import QGraphicsRectItem
        pen = QPen(QColor("#00AAFF"), 1, Qt.PenStyle.DashLine)
        brush = QBrush(QColor(0, 170, 255, 30))
        self._marquee = QGraphicsRectItem(0, 0, 0, 0)
        self._marquee.setPen(pen)
        self._marquee.setBrush(brush)
        self._marquee.setPos(pos)
        self._marquee.setZValue(9999)
        self.canvas.scene.addItem(self._marquee)

    def _update_marquee(self, pos: QPointF):
        """更新框选矩形大小"""
        if not self._marquee or not self._marquee_start:
            return
        x = min(self._marquee_start.x(), pos.x())
        y = min(self._marquee_start.y(), pos.y())
        w = abs(pos.x() - self._marquee_start.x())
        h = abs(pos.y() - self._marquee_start.y())
        self._marquee.setRect(0, 0, w, h)
        self._marquee.setPos(x, y)

    def _finish_marquee(self, pos: QPointF, modifiers):
        """结束框选，选中框内图形"""
        if not self._marquee:
            return

        rect = self._marquee.rect().translated(self._marquee.pos())
        append = bool(modifiers & Qt.KeyboardModifier.ControlModifier)

        for g in self.draw_layer.graphics:
            if rect.intersects(g.sceneBoundingRect()):
                self.draw_layer.select_graphic(g, append=append)
                append = True  # 第一个之后都追加

        self.canvas.scene.removeItem(self._marquee)
        self._marquee = None
        self._marquee_start = None
