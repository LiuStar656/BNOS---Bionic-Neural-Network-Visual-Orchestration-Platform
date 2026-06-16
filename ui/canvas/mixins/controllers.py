"""
Canvas控制器集合，将原来的mixin继承改为组合模式
当前阶段：委托层 — 控制器委托到现有mixin方法
后续阶段：将mixin逻辑迁移到控制器中，逐步移除mixin继承
"""
from typing import Optional
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QRubberBand


class CanvasConnectionController:
    """连线控制 — 委托到 CanvasConnectionsMixin
    """
    def __init__(self, canvas):
        self._c = canvas

    def add_connection(self, source, target):
        return self._c.add_connection(source, target)

    def remove_connection(self, source, target):
        return self._c.remove_connection(source, target)

    def clear_all_connections(self):
        return self._c.clear_all_connections()


class CanvasBatchOperations:
    """批量操作 — 委托到 CanvasBatchOpsMixin
    """
    def __init__(self, canvas):
        self._c = canvas

    def select_all_nodes(self):
        return getattr(self._c, 'select_all_nodes', lambda: None)()

    def deselect_all(self):
        return getattr(self._c, 'deselect_all_nodes', lambda: None)()

    def delete_selected(self):
        return getattr(self._c, 'delete_selected_nodes', lambda: None)()


class BoxSelectionController:
    """框选 — 委托到 CanvasBoxSelectMixin
    """
    def __init__(self, canvas):
        self._c = canvas
        self.rubber_band: Optional[QRubberBand] = None
        self._origin = QPointF()

    def start(self, pos: QPointF):
        if hasattr(self._c, 'start_box_select'):
            self._c.start_box_select(pos)
        else:
            self._origin = self._c.mapToScene(pos)
            if not self.rubber_band:
                self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self._c)
            self.rubber_band.setGeometry(int(pos.x()), int(pos.y()), 0, 0)
            self.rubber_band.show()

    def update(self, pos: QPointF):
        if self.rubber_band:
            r = QRectF(self._origin, self._c.mapToScene(pos)).normalized()
            self.rubber_band.setGeometry(int(r.left()), int(r.top()), int(r.width()), int(r.height()))

    def end(self):
        if self.rubber_band:
            self.rubber_band.hide()
            self.rubber_band = None

    def cancel(self):
        if self.rubber_band:
            self.rubber_band.hide()
            self.rubber_band = None


class CanvasMenuController:
    """右键菜单 — 委托到 CanvasMenusMixin
    """
    def __init__(self, canvas):
        self._c = canvas

    def show_context_menu(self, pos):
        if hasattr(self._c, 'show_context_menu'):
            self._c.show_context_menu(pos)

    def show_canvas_menu(self, pos):
        if hasattr(self._c, 'show_canvas_menu'):
            self._c.show_canvas_menu(pos)


class CanvasLayoutController:
    """布局持久化 — 委托到 CanvasLayoutMixin
    """
    def __init__(self, canvas):
        self._c = canvas

    def save_layout(self, path=None):
        if hasattr(self._c, 'save_canvas_layout'):
            self._c.save_canvas_layout(path)
        elif hasattr(self._c, 'save_all_layouts'):
            self._c.save_all_layouts(path)

    def load_layout(self, path=None):
        if hasattr(self._c, 'load_canvas_layout'):
            return self._c.load_canvas_layout(path)
        return None

    def save_center_coordinates(self):
        if hasattr(self._c, 'save_center_coordinates'):
            self._c.save_center_coordinates()


class CanvasColorController:
    """颜色主题 — 委托到 CanvasColorsMixin
    """
    def __init__(self, canvas):
        self._c = canvas

    def apply_color_scheme(self, scheme: dict):
        if hasattr(self._c, 'apply_color_scheme'):
            self._c.apply_color_scheme(scheme)

    def set_colors(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._c, key):
                setattr(self._c, key, value)
        if hasattr(self._c, 'apply_color_scheme'):
            self._c.apply_color_scheme({})

    def refresh_colors(self):
        self._c.setBackgroundBrush(
            QColor(getattr(self._c, 'canvas_bg_color', '#1e1e1e'))
        )
        self._c.resetCachedContent()
        self._c.viewport().update()


class CanvasZoomController:
    """缩放控制
    """
    def __init__(self, canvas):
        self._c = canvas

    def zoom_in(self):
        self._c.scale(1.15, 1.15)

    def zoom_out(self):
        self._c.scale(1 / 1.15, 1 / 1.15)

    def zoom_fit(self):
        rect = self._c.scene().itemsBoundingRect()
        if not rect.isEmpty():
            self._c.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_reset(self):
        self._c.resetTransform()
