"""
绘图管理层 — 统一管理图形渲染/选中/拖拽/撤销重做，Alt 键切换编辑模式

注入到 NodeCanvas，作为绘图层 (z=0) 在节点层下方。
"""
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsItem
from ui.canvas.graphic_items import (
    RectGraphic, RoundRectGraphic, PolygonGraphic, ArrowGraphic, TextGraphic,
    GraphicBase, C_STROKE, C_FILL, STROKE_W
)
from ui.canvas.draw_toolbar import DrawToolbar
from ui.core.logger import logger


class DrawLayer:
    """绘图层管理器，嵌入 NodeCanvas"""

    MAX_UNDO = 50

    def __init__(self, canvas):
        self.canvas = canvas
        self.graphics = []         # 所有图形
        self._current = None       # 正在拖拽创建的图形
        self._tool = ""            # 当前工具
        self._locked = False       # 图层锁定
        self._visible = True       # 图层可见
        self._alt_mode = False     # Alt 编辑模式

        self._undo_stack = []
        self._redo_stack = []
        self._drag_start = None
        self._dragging_handle = -1
        self._dragging_graphic = None

        # 样式缓存
        self._stroke = C_STROKE
        self._fill = C_FILL
        self._stroke_w = STROKE_W

        self.toolbar = None

    def attach_toolbar(self):
        """创建并挂载绘图工具栏到画布左侧"""
        if self.toolbar:
            return self.toolbar
        view = self.canvas.viewport()
        self.toolbar = DrawToolbar(view)
        self.toolbar.setParent(view)
        self.toolbar.setGeometry(0, 0, 36, view.height())
        self.toolbar.show()
        self.toolbar.tool_changed.connect(self.set_tool)
        self.toolbar.style_changed.connect(self._on_style)
        self.toolbar.layer_locked.connect(self.set_locked)
        self.toolbar.layer_visible.connect(self.set_visible)
        self.toolbar.undo_requested.connect(self.undo)
        self.toolbar.redo_requested.connect(self.redo)
        self.toolbar.delete_requested.connect(self.delete_selected)
        self.toolbar.clear_requested.connect(self.clear_all)
        return self.toolbar

    # ── 工具/样式/图层控制 ──

    def set_tool(self, tool):
        self._tool = tool
        view = self.canvas.viewport()
        cursor = Qt.CursorShape.ArrowCursor
        if tool in ("rect", "round_rect", "arrow"):
            cursor = Qt.CursorShape.CrossCursor
        elif tool == "polygon":
            cursor = Qt.CursorShape.PointingHandCursor
        elif tool == "text":
            cursor = Qt.CursorShape.IBeamCursor
        view.setCursor(cursor)
        # 取消当前正在创建的图形
        self._current = None
        self._dragging_graphic = None

    def _on_style(self, key, value):
        if key == "stroke":
            self._stroke = value
        elif key == "fill":
            self._fill = value

    def set_locked(self, locked):
        self._locked = locked

    def set_visible(self, vis):
        self._visible = vis
        for g in self.graphics:
            g.setVisible(vis)

    # ── 键盘事件 ──

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Alt:
            self._alt_mode = True
            view = self.canvas.viewport()
            view.setCursor(Qt.CursorShape.CrossCursor)
            return True
        return False

    def key_release(self, event):
        if event.key() == Qt.Key.Key_Alt:
            self._alt_mode = False
            self.canvas.viewport().setCursor(Qt.CursorShape.ArrowCursor)
            return True
        return False

    # ── 鼠标事件（从 canvas_view 调用）──

    def mouse_press(self, event):
        if self._locked:
            return False
        pos = self.canvas.mapToScene(event.pos())

        # 右键 → 删除图形
        if event.button() == Qt.MouseButton.RightButton:
            item = self.canvas.scene.itemAt(pos, self.canvas.transform())
            while item:
                if isinstance(item, (GraphicBase, TextGraphic)) and item in self.graphics:
                    self._save_undo()
                    self.canvas.scene.removeItem(item)
                    self.graphics.remove(item)
                    self.canvas._save_timer.start(500)
                    return True
                item = item.parentItem()
            return False

        # 已有图形 → 拖拽控制点或移动
        if self._alt_mode or (not self._tool):
            item = self.canvas.scene.itemAt(pos, self.canvas.transform())
            while item:
                if isinstance(item, GraphicBase) and item in self.graphics:
                    idx = item.hit_handle(pos)
                    if idx >= 0:
                        self._save_undo()
                        self._dragging_graphic = item
                        self._dragging_handle = idx
                        return True
                    self._save_undo()
                    self._dragging_graphic = item
                    self._drag_start = pos
                    return True
                if isinstance(item, TextGraphic) and item in self.graphics:
                    self._save_undo()
                    self._dragging_graphic = item
                    self._drag_start = pos
                    return True
                item = item.parentItem()

        # 创建新图形
        if self._tool == "polygon":
            return self._polygon_click(event, pos)
        elif self._tool:
            return self._start_create(event, pos)
        return False

    def mouse_move(self, event):
        if self._locked:
            return False
        pos = self.canvas.mapToScene(event.pos())

        if self._dragging_handle >= 0 and self._dragging_graphic:
            self._dragging_graphic.move_handle(self._dragging_handle, pos)
            return True

        if self._dragging_graphic and self._drag_start:
            delta = pos - self._drag_start
            self._dragging_graphic.moveBy(delta.x(), delta.y())
            self._drag_start = pos
            return True

        if self._current and self._tool in ("rect", "round_rect", "arrow"):
            self._current._points[1] = (pos.x(), pos.y())
            self._current.prepareGeometryChange()
            self._current._after_edit()
            return True

        return False

    def mouse_release(self, event):
        if self._dragging_graphic and self._dragging_handle >= 0:
            self._dragging_handle = -1
            self._dragging_graphic = None
            self.canvas._save_timer.start(500)
            return True

        if self._dragging_graphic:
            self._dragging_graphic = None
            self._drag_start = None
            self.canvas._save_timer.start(500)
            return True

        if self._current and self._tool in ("rect", "round_rect", "arrow"):
            self._current = None
            self.canvas._save_timer.start(500)
            return True
        return False

    def mouse_double_click(self, event):
        """双击闭合多边形"""
        if self._tool == "polygon" and self._current:
            if len(self._current._points) >= 2:
                self._current._points.pop()  # 移除最后的临时点
            if self._current.isFinished():
                self._current.update()
                self.canvas._save_timer.start(500)
            self._current = None
            return True
        return False

    # ── 创建逻辑 ──

    def _start_create(self, event, pos):
        self._save_undo()
        if self._tool == "rect":
            g = RectGraphic([(pos.x(), pos.y()), (pos.x(), pos.y())])
        elif self._tool == "round_rect":
            g = RoundRectGraphic([(pos.x(), pos.y()), (pos.x(), pos.y())])
        elif self._tool == "arrow":
            g = ArrowGraphic([(pos.x(), pos.y()), (pos.x(), pos.y())])
        elif self._tool == "text":
            from PyQt6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self.canvas, "文本", "输入文字:")
            if not ok or not text.strip():
                return False
            g = TextGraphic(text.strip(), pos.x(), pos.y())
            g.set_style(stroke_color=self._stroke, fill_color=self._fill)
            self.canvas.scene.addItem(g)
            self.graphics.append(g)
            self.canvas._save_timer.start(500)
            return True
        else:
            return False

        g.set_style(stroke_color=self._stroke, fill_color=self._fill)
        self.canvas.scene.addItem(g)
        self.graphics.append(g)
        self._current = g
        return True

    def _polygon_click(self, event, pos):
        if not self._current:
            self._save_undo()
            g = PolygonGraphic()
            g.add_point(pos.x(), pos.y())
            g.add_point(pos.x(), pos.y())  # 临时第二点，跟随鼠标
            g.set_style(stroke_color=self._stroke, fill_color=self._fill)
            self.canvas.scene.addItem(g)
            self.graphics.append(g)
            self._current = g
        else:
            self._current._points[-1] = (pos.x(), pos.y())  # 固定临时点
            self._current.add_point(pos.x(), pos.y())        # 新的临时点
            self._current.prepareGeometryChange()
        return True

    # ── 撤销/重做 ──

    def _save_undo(self):
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > self.MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        self._restore(self._undo_stack.pop())

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        self._restore(self._redo_stack.pop())

    def _snapshot(self):
        return [g.to_dict() for g in self.graphics]

    def _restore(self, data):
        for g in self.graphics:
            self.canvas.scene.removeItem(g)
        self.graphics.clear()
        for d in data:
            g = GraphicBase.from_dict(d)
            self.canvas.scene.addItem(g)
            self.graphics.append(g)

    # ── 持久化 ──

    def to_json(self):
        return [g.to_dict() for g in self.graphics]

    def from_json(self, data):
        for g in self.graphics:
            self.canvas.scene.removeItem(g)
        self.graphics.clear()
        for d in (data or []):
            g = GraphicBase.from_dict(d)
            self.canvas.scene.addItem(g)
            self.graphics.append(g)

    # ── 删除选中图形 ──

    def delete_selected(self):
        self._save_undo()
        for g in list(self.graphics):
            if g.isSelected():
                self.canvas.scene.removeItem(g)
                self.graphics.remove(g)
        self.canvas._save_timer.start(500)

    def clear_all(self):
        self._save_undo()
        for g in self.graphics:
            self.canvas.scene.removeItem(g)
        self.graphics.clear()
        self.canvas._save_timer.start(500)

    def resize_toolbar(self):
        if self.toolbar and self.toolbar.isVisible():
            self.toolbar.setGeometry(0, 0, 36, self.canvas.viewport().height())
