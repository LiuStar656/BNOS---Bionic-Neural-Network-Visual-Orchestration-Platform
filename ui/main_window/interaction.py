"""
BNOS 主窗口交互模块

负责窗口的鼠标交互和窗口控制功能，包括：
- 窗口调整大小（自定义无边框窗口）
- 鼠标事件处理
- 最大化/最小化切换
- 快捷键处理
"""
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QMainWindow
from ui.core.theme import DARK_QSS


class MainWindowInteractionMixin:
    """窗口交互Mixin - 处理鼠标事件和窗口控制"""

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        if hasattr(self, '_title_bar'):
            self._title_bar.set_maximized_state(self.isMaximized())

    def changeEvent(self, event):
        QMainWindow.changeEvent(self, event)
        if event.type() == QEvent.Type.WindowStateChange and hasattr(self, '_title_bar'):
            self._title_bar.set_maximized_state(self.isMaximized())

    def setWindowTitle(self, title: str):
        QMainWindow.setWindowTitle(self, title)
        if hasattr(self, '_title_bar'):
            self._title_bar.set_title(title)

    def _get_resize_region(self, pos):
        x, y = pos.x(), pos.y()
        w, h, m = self.width(), self.height(), self._RESIZE_MARGIN
        t, b, l, r = y <= m, y >= h - m, x <= m, x >= w - m
        if t and l: return Qt.CursorShape.SizeFDiagCursor, "top-left"
        if t and r: return Qt.CursorShape.SizeBDiagCursor, "top-right"
        if b and l: return Qt.CursorShape.SizeBDiagCursor, "bottom-left"
        if b and r: return Qt.CursorShape.SizeFDiagCursor, "bottom-right"
        if t:      return Qt.CursorShape.SizeVerCursor, "top"
        if b:      return Qt.CursorShape.SizeVerCursor, "bottom"
        if l:      return Qt.CursorShape.SizeHorCursor, "left"
        if r:      return Qt.CursorShape.SizeHorCursor, "right"
        return None, None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self.isMaximized():
            _, direction = self._get_resize_region(event.pos())
            if direction:
                self._resize_direction = direction
                self._resize_start_pos = event.globalPosition().toPoint()
                self._resize_original_geometry = self.geometry()
                event.accept()
                return
        QMainWindow.mousePressEvent(self, event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if hasattr(self, '_resize_direction') and self._resize_direction:
            delta = event.globalPosition().toPoint() - self._resize_start_pos
            new_geo = self._resize_original_geometry

            if 'left' in self._resize_direction:
                new_width = max(self.minimumWidth(), new_geo.width() - delta.x())
                new_geo.setX(new_geo.x() + (new_geo.width() - new_width))
                new_geo.setWidth(new_width)

            if 'right' in self._resize_direction:
                new_geo.setWidth(max(self.minimumWidth(), self._resize_original_geometry.width() + delta.x()))

            if 'top' in self._resize_direction:
                new_height = max(self.minimumHeight(), new_geo.height() - delta.y())
                new_geo.setY(new_geo.y() + (new_geo.height() - new_height))
                new_geo.setHeight(new_height)

            if 'bottom' in self._resize_direction:
                new_geo.setHeight(max(self.minimumHeight(), self._resize_original_geometry.height() + delta.y()))

            self.setGeometry(new_geo)
        else:
            if not self.isMaximized():
                cursor, _ = self._get_resize_region(event.pos())
                if cursor:
                    self.setCursor(cursor)
                else:
                    self.unsetCursor()
        QMainWindow.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if hasattr(self, '_resize_direction') and self._resize_direction:
            self._resize_direction = None
            self._resize_start_pos = None
            self._resize_original_geometry = None
        QMainWindow.mouseReleaseEvent(self, event)

    @property
    def _canvas_mode(self):
        return self.CANVAS_PROCESS_MODE and self._process_manager is not None

    def _apply_dark_theme(self):
        self.setStyleSheet(DARK_QSS)

    def _on_ctrl_d(self):
        """Ctrl+D 统一删除：画布选区/节点列表/绘图图形/节点组"""
        if self.node_list_panel and self.node_list_panel.isVisible():
            try:
                from PySide6.QtWidgets import QApplication
                fw = QApplication.focusWidget()
                if fw and self.node_list_panel.isAncestorOf(fw):
                    sel = self.node_list_panel.get_selected_nodes()
                    if sel:
                        self.node_list_panel.batch_delete_nodes()
                        return
                    grps = self.node_list_panel.get_selected_groups()
                    for g in grps:
                        self.node_list_panel.delete_group(g)
                    if grps:
                        return
            except Exception:
                pass

        if self.canvas:
            if self.canvas.box_selected_nodes:
                self.canvas.batch_remove_nodes_from_canvas()
                return
            self.canvas.draw_layer.delete_selected()
            return

    def show_about(self):
        """显示关于对话框"""
        from ui.core.utils.dialog_utils import themed_message
        from ui.core.i18n import t
        themed_message(self, t("k_title_about"), t("_k_about_text"), "info")

    def _on_node_service_status(self, name: str, status):
        """接收节点控制服务的状态变化通知（解耦回调）"""
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_status(name, status.value)
        if self.canvas:
            self.canvas.sync_all_nodes_display()