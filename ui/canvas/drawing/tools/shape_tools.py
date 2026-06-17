"""
形状工具组 — 矩形、圆角矩形、椭圆、多边形、箭头
"""
from PySide6.QtCore import Qt, QPointF

from .tool_base import ToolBase, ToolResult
from ui.canvas.drawing.graphic_items import (
    RectGraphic, RoundRectGraphic, PolygonGraphic, ArrowGraphic,
)


class _ShapeCreateTool(ToolBase):
    """形状创建工具基类"""

    def __init__(self, draw_layer, tool_id: str, graphic_cls):
        super().__init__(draw_layer, tool_id)
        self.graphic_cls = graphic_cls
        self._current = None
        self._creating = False

    def on_activate(self):
        self.canvas.viewport().setCursor(Qt.CursorShape.CrossCursor)

    def mouse_press(self, event, scene_pos: QPointF) -> ToolResult:
        if event.button() != Qt.MouseButton.LeftButton:
            return ToolResult.IGNORED
        self._save_undo()
        g = self.graphic_cls([(scene_pos.x(), scene_pos.y()), (scene_pos.x(), scene_pos.y())])
        g.set_style(stroke_color=self._get_stroke(), fill_color=self._get_fill())
        self.canvas.scene.addItem(g)
        self.draw_layer.graphics.append(g)
        self._current = g
        self._creating = True
        return ToolResult.HANDLED

    def mouse_move(self, event, scene_pos: QPointF) -> ToolResult:
        if self._current and self._creating:
            self._current._points[1] = (scene_pos.x(), scene_pos.y())
            self._current.prepareGeometryChange()
            self._current._after_edit()
            return ToolResult.HANDLED
        return ToolResult.IGNORED

    def mouse_release(self, event, scene_pos: QPointF) -> ToolResult:
        if self._current and self._creating:
            self._current = None
            self._creating = False
            self.canvas._save_timer.start(500)
            return ToolResult.HANDLED
        return ToolResult.IGNORED


class RectTool(_ShapeCreateTool):
    def __init__(self, draw_layer):
        super().__init__(draw_layer, "rect", RectGraphic)


class RoundRectTool(_ShapeCreateTool):
    def __init__(self, draw_layer):
        super().__init__(draw_layer, "round_rect", RoundRectGraphic)


class EllipseTool(_ShapeCreateTool):
    """椭圆工具（使用 RoundRectGraphic 实现，rx=ry=宽/2）"""
    def __init__(self, draw_layer):
        super().__init__(draw_layer, "ellipse", RoundRectGraphic)

    def mouse_press(self, event, scene_pos: QPointF) -> ToolResult:
        result = super().mouse_press(event, scene_pos)
        if self._current:
            # 椭圆模式下圆角半径设为极大值，形成椭圆效果
            self._current._rx = 9999
            self._current._ry = 9999
        return result


class ArrowTool(_ShapeCreateTool):
    def __init__(self, draw_layer):
        super().__init__(draw_layer, "arrow", ArrowGraphic)


class PolygonTool(ToolBase):
    """多边形工具 — 逐点点击创建"""

    def __init__(self, draw_layer):
        super().__init__(draw_layer, "polygon")
        self._current = None

    def on_activate(self):
        self.canvas.viewport().setCursor(Qt.CursorShape.PointingHandCursor)

    def mouse_press(self, event, scene_pos: QPointF) -> ToolResult:
        if event.button() != Qt.MouseButton.LeftButton:
            return ToolResult.IGNORED

        if not self._current:
            self._save_undo()
            g = PolygonGraphic()
            g.add_point(scene_pos.x(), scene_pos.y())
            g.add_point(scene_pos.x(), scene_pos.y())  # 临时第二点
            g.set_style(stroke_color=self._get_stroke(), fill_color=self._get_fill())
            self.canvas.scene.addItem(g)
            self.draw_layer.graphics.append(g)
            self._current = g
        else:
            self._current._points[-1] = (scene_pos.x(), scene_pos.y())  # 固定临时点
            self._current.add_point(scene_pos.x(), scene_pos.y())        # 新的临时点
            self._current.prepareGeometryChange()
        return ToolResult.HANDLED

    def mouse_move(self, event, scene_pos: QPointF) -> ToolResult:
        if self._current:
            self._current._points[-1] = (scene_pos.x(), scene_pos.y())
            self._current.prepareGeometryChange()
            return ToolResult.HANDLED
        return ToolResult.IGNORED

    def mouse_double_click(self, event, scene_pos: QPointF) -> ToolResult:
        """双击闭合多边形"""
        if self._current:
            if len(self._current._points) >= 2:
                self._current._points.pop()  # 移除最后的临时点
            if self._current.isFinished():
                self._current.update()
                self.canvas._save_timer.start(500)
            self._current = None
            return ToolResult.HANDLED
        return ToolResult.IGNORED

    def mouse_release(self, event, scene_pos: QPointF) -> ToolResult:
        return ToolResult.IGNORED
