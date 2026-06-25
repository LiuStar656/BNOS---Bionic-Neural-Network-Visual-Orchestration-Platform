"""
BNOS 主窗口交互模块

负责窗口的鼠标交互和窗口控制功能，包括：
- 窗口调整大小（Windows WM_NCHITTEST 原生方案）
- 最大化/最小化切换
- 快捷键处理
"""
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QMainWindow
from ui.core.theme import DARK_QSS


class MainWindowInteractionMixin:
    """窗口交互Mixin - 处理窗口控制（缩放走 WM_NCHITTEST 原生方案）"""

    # ---- 窗口缩放：Windows WM_NCHITTEST 原生方案 ----
    # 与 bnos_dock/dock_manager 中的浮动 Dock 缩放方案一致。
    # 不使用 mousePressEvent/mouseMoveEvent 方案的原因是：
    # CanvasHost（centralWidget）和 DarkTitleBar（menuWidget）覆盖了
    # 整个主窗口区域，子控件的鼠标事件不会传播到主窗口，
    # 导致 _get_resize_region 永远检测不到边缘点击。

    def nativeEvent(self, eventType, message):
        """Windows 原生事件 — 无边框窗口边缘缩放"""
        import ctypes
        # 最大化时不处理（系统管理）
        if self.isMaximized():
            return False, 0
        if eventType != b"windows_generic_MSG":
            return False, 0

        class MSG(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("message", ctypes.c_uint),
                ("wParam", ctypes.c_ulonglong),
                ("lParam", ctypes.c_longlong),
                ("time", ctypes.c_uint),
                ("pt_x", ctypes.c_long),
                ("pt_y", ctypes.c_long),
            ]
        msg = MSG.from_address(int(message))
        if msg.message != 0x0084:  # WM_NCHITTEST
            return False, 0

        # 光标屏幕坐标
        x = msg.lParam & 0xFFFF
        y = (msg.lParam >> 16) & 0xFFFF

        # 窗口屏幕坐标
        geo = self.geometry()
        border = self._RESIZE_MARGIN

        left = x < geo.x() + border
        right = x >= geo.x() + geo.width() - border
        top = y < geo.y() + border
        bottom = y >= geo.y() + geo.height() - border

        HTLEFT, HTRIGHT, HTTOP, HTBOTTOM = 10, 11, 12, 15
        HTTOPLEFT, HTTOPRIGHT, HTBOTTOMLEFT, HTBOTTOMRIGHT = 13, 14, 16, 17

        if top and left:
            return True, HTTOPLEFT
        if top and right:
            return True, HTTOPRIGHT
        if bottom and left:
            return True, HTBOTTOMLEFT
        if bottom and right:
            return True, HTBOTTOMRIGHT
        if left:
            return True, HTLEFT
        if right:
            return True, HTRIGHT
        if top:
            return True, HTTOP
        if bottom:
            return True, HTBOTTOM

        return False, 0

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
        """显示关于对话框 — 加载根目录 README"""
        from ui.core.utils.changelog_viewer import show_about_readme
        show_about_readme(self)

    def show_changelog(self):
        """显示更新日志对话框"""
        from ui.core.utils.changelog_viewer import show_changelog
        show_changelog(self)

    def _on_node_service_status(self, name: str, status):
        """接收节点控制服务的状态变化通知（解耦回调）"""
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_status(name, status.value)
        if self.canvas:
            self.canvas.sync_all_nodes_display()