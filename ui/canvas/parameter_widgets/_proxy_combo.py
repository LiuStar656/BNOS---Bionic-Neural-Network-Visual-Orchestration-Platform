"""QGraphicsProxyWidget 兼容的 ComboBox — 修复下拉弹窗坐标映射"""
from PySide6.QtWidgets import QComboBox, QGraphicsProxyWidget, QFrame


class _ProxyAwareComboBox(QComboBox):
    """在 QGraphicsProxyWidget 中使用的 ComboBox — 修复下拉弹窗的全局坐标映射 bug。

    问题背景：QComboBox.showPopup() 内部通过 mapToGlobal 计算弹窗位置，
    但当 widget 被嵌入 QGraphicsProxyWidget 后，mapToGlobal 返回错误坐标，
    导致弹窗被截断/出现在屏幕其他位置。
    解决：重写 showPopup，基于 QGraphicsProxyWidget 的 scene→view→屏幕坐标自己计算。
    """

    def showPopup(self):
        proxy = None
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "metaObject") and parent.metaObject() and \
               parent.metaObject().className() == b"QGraphicsProxyWidget":
                proxy = parent
                break
            try:
                if isinstance(parent, QGraphicsProxyWidget):
                    proxy = parent
                    break
            except Exception:
                pass
            parent = parent.parent() if hasattr(parent, "parent") else None

        if proxy is not None and hasattr(proxy, "scenePos"):
            scene = proxy.scene()
            views = scene.views() if scene else []
            if views:
                view = views[0]
                proxy_scene_bottom = proxy.mapToScene(proxy.rect().bottomLeft())
                view_pt = view.mapFromScene(proxy_scene_bottom)
                screen_pt = view.viewport().mapToGlobal(view_pt)
            else:
                screen_pt = self.mapToGlobal(self.rect().bottomLeft())
            popup_width = max(self.width(), 200)
            try:
                super().showPopup()
            except Exception:
                super().showPopup()
            for child in self.children():
                if isinstance(child, QFrame) and child.isWindow():
                    child.move(screen_pt)
                    child.resize(popup_width, min(child.height(), 400))
                    break
        else:
            super().showPopup()
