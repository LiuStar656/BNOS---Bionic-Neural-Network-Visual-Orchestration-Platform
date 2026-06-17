"""
绘图管理层 — 工具分发 + 多选管理 + 属性面板 + 撤销重做

注入到 NodeCanvas，作为绘图层 (z=0) 在节点层下方。
"""
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QGraphicsItem, QMenu
from PySide6.QtGui import QAction

from ui.core.i18n import t
from ui.canvas.drawing.graphic_items import (
    RectGraphic, RoundRectGraphic, PolygonGraphic, ArrowGraphic, TextGraphic,
    GraphicBase, C_STROKE, C_FILL, STROKE_W
)
from ui.canvas.drawing.draw_toolbar import DrawToolbar
from ui.canvas.drawing.tools import (
    SelectionTool, RectTool, RoundRectTool, EllipseTool,
    PolygonTool, ArrowTool, TextTool, ToolResult,
)
from ui.canvas.drawing.components import DrawPropertyPanel
from ui.canvas.drawing.styles import apply_preset, PRESETS
from ui.core.logger import logger
from ui.core.app_config import AppConfig


class DrawLayer:
    """绘图层管理器，嵌入 NodeCanvas — 工具分发架构"""

    MAX_UNDO = 50

    def __init__(self, canvas):
        self.canvas = canvas
        self.graphics = []         # 所有图形
        self._tool = ""            # 当前工具 ID
        self._locked = False       # 图层锁定
        self._visible = True       # 图层可见
        self._alt_mode = False     # Alt 编辑模式

        self._undo_stack = []
        self._redo_stack = []

        # 样式缓存
        self._stroke = C_STROKE
        self._fill = C_FILL
        self._stroke_w = STROKE_W

        self.toolbar = None
        self._toolbar_visible = False
        self.property_panel = None

        # 工具注册表
        self._tools = {}
        self._active_tool = None
        self._register_tools()

    def _register_tools(self):
        """注册所有绘图工具"""
        self._tools = {
            "select": SelectionTool(self),
            "rect": RectTool(self),
            "round_rect": RoundRectTool(self),
            "ellipse": EllipseTool(self),
            "polygon": PolygonTool(self),
            "arrow": ArrowTool(self),
            "text": TextTool(self),
        }
        # 默认使用选择工具
        self._set_active_tool("select")

    def _set_active_tool(self, tool_id: str):
        """切换激活工具"""
        if self._active_tool:
            self._active_tool.on_deactivate()
        self._tool = tool_id
        self._active_tool = self._tools.get(tool_id)
        if self._active_tool:
            self._active_tool.on_activate()

    # ── 工具栏 ──

    def attach_toolbar(self):
        """创建并挂载绘图工具栏到画布左侧（默认隐藏）"""
        if self.toolbar:
            return self.toolbar
        self.toolbar = DrawToolbar(self.canvas)
        self.toolbar.setParent(self.canvas)
        self.toolbar.setGeometry(0, 0, 36, self.canvas.viewport().height())
        self.toolbar.tool_changed.connect(self.set_tool)
        self.toolbar.style_changed.connect(self._on_style)
        self.toolbar.layer_locked.connect(self.set_locked)
        self.toolbar.layer_visible.connect(self.set_visible)
        self.toolbar.undo_requested.connect(self.undo)
        self.toolbar.redo_requested.connect(self.redo)
        self.toolbar.delete_requested.connect(self.delete_selected)
        self.toolbar.clear_requested.connect(self.clear_all)

        try:
            app_config = AppConfig()
            self._toolbar_visible = app_config.get("draw_toolbar_visible", False)
        except Exception as e:
            logger.warning("读取绘图工具栏初始配置失败: %s", e)
            self._toolbar_visible = False

        # 根据配置显示/隐藏工具栏
        if self._toolbar_visible:
            self.toolbar.show()
        else:
            self.toolbar.hide()

        return self.toolbar

    def show_toolbar(self):
        if not self.toolbar:
            return
        self.toolbar.show()
        self._toolbar_visible = True
        logger.debug("绘图工具栏已显示")
        self._save_toolbar_config(True)

    def hide_toolbar(self):
        if not self.toolbar:
            return
        self.toolbar.hide()
        self._toolbar_visible = False
        logger.debug("绘图工具栏已隐藏")
        self._save_toolbar_config(False)

    def toggle_toolbar(self):
        new_visible = not self._toolbar_visible
        if new_visible:
            self.show_toolbar()
        else:
            self.hide_toolbar()
        return self._toolbar_visible

    def _save_toolbar_config(self, visible):
        try:
            app_config = AppConfig()
            app_config.set("draw_toolbar_visible", visible)
            app_config.save()
        except Exception as e:
            logger.warning("保存绘图工具栏配置失败: %s", e)

    # ── 属性面板 ──

    def attach_property_panel(self):
        """创建并挂载属性面板"""
        if self.property_panel:
            return self.property_panel
        self.property_panel = DrawPropertyPanel(self, self.canvas)
        self.property_panel.setParent(self.canvas)
        self.property_panel.hide()
        return self.property_panel

    def _refresh_property_panel(self):
        """刷新属性面板显示状态"""
        if self.property_panel:
            self.property_panel.refresh()
            if self.property_panel.isVisible():
                self.property_panel.move(44, 10)

    # ── 工具/样式/图层控制 ──

    def set_tool(self, tool):
        """切换工具（空字符串表示选择工具）"""
        tool_id = tool if tool else "select"
        self._set_active_tool(tool_id)
        # 取消正在创建的图形状态
        if hasattr(self._active_tool, "_current"):
            self._active_tool._current = None
        if hasattr(self._active_tool, "_creating"):
            self._active_tool._creating = False

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
            self._set_active_tool("select")
            return True
        if event.key() == Qt.Key.Key_D and not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.toggle_toolbar()
            return True
        # 交给当前工具处理
        if self._active_tool:
            result = self._active_tool.key_press(event)
            if result != ToolResult.IGNORED:
                return True
        return False

    def key_release(self, event):
        if event.key() == Qt.Key.Key_Alt:
            self._alt_mode = False
            # 恢复之前的工具（如果有）
            if self._tool == "select" and self.toolbar:
                # 简单处理：Alt 松开后保持选择工具，用户可手动切回其他工具
                pass
            return True
        if self._active_tool:
            result = self._active_tool.key_release(event)
            if result != ToolResult.IGNORED:
                return True
        return False

    # ── 鼠标事件（工具分发）──

    def mouse_press(self, event):
        if self._locked:
            return False
        pos = self.canvas.mapToScene(event.pos())

        # 右键菜单：只在点击绘图图形或工具栏可见时显示绘图菜单
        if event.button() == Qt.MouseButton.RightButton:
            item = self.canvas.scene.itemAt(pos, self.canvas.transform())
            graphic = None
            while item:
                if isinstance(item, (GraphicBase, TextGraphic)) and item in self.graphics:
                    graphic = item
                    break
                item = item.parentItem()

            if graphic:
                self._show_context_menu(event, pos)
                return True
            elif self._toolbar_visible:
                self._show_context_menu(event, pos)
                return True
            else:
                return False

        if self._active_tool and self._toolbar_visible:
            result = self._active_tool.mouse_press(event, pos)
            if result != ToolResult.IGNORED:
                self._refresh_property_panel()
                return True
        return False

    def mouse_move(self, event):
        if self._locked:
            return False
        pos = self.canvas.mapToScene(event.pos())
        if self._active_tool and self._toolbar_visible:
            result = self._active_tool.mouse_move(event, pos)
            if result != ToolResult.IGNORED:
                return True
        return False

    def mouse_release(self, event):
        if self._locked:
            return False
        pos = self.canvas.mapToScene(event.pos())
        if self._active_tool and self._toolbar_visible:
            result = self._active_tool.mouse_release(event, pos)
            if result != ToolResult.IGNORED:
                self._refresh_property_panel()
                return True
        return False

    def mouse_double_click(self, event):
        if self._locked:
            return False
        pos = self.canvas.mapToScene(event.pos())
        if self._active_tool:
            result = self._active_tool.mouse_double_click(event, pos)
            if result != ToolResult.IGNORED:
                return True
        return False

    # ── 右键菜单 ──

    def _show_context_menu(self, event, scene_pos):
        item = self.canvas.scene.itemAt(scene_pos, self.canvas.transform())
        graphic = None
        while item:
            if isinstance(item, (GraphicBase, TextGraphic)) and item in self.graphics:
                graphic = item
                break
            item = item.parentItem()

        menu = QMenu(self.canvas.viewport())
        menu.setStyleSheet("""
            QMenu { background-color: #333; color: #FFF; border: 1px solid #555; }
            QMenu::item:selected { background-color: #00AAFF; }
        """)

        if graphic:
            # 确保该图形被选中
            if graphic not in self.selected_graphics():
                self.select_graphic(graphic)

            if graphic.gtype == "text":
                edit_action = QAction(t("编辑文本"), menu)
                edit_action.triggered.connect(lambda: self.start_text_editing(graphic))
                menu.addAction(edit_action)
                menu.addSeparator()

            copy_action = QAction(t("复制"), menu)
            copy_action.triggered.connect(self.copy_selected)
            menu.addAction(copy_action)

            delete_action = QAction(t("删除"), menu)
            delete_action.triggered.connect(self.delete_selected)
            menu.addAction(delete_action)
            menu.addSeparator()

            # 预设样式子菜单
            preset_menu = QMenu(t("预设样式"), menu)
            for key, preset in PRESETS.items():
                action = QAction(preset.name, preset_menu)
                action.triggered.connect(lambda checked, k=key: self._apply_preset_to_selected(k))
                preset_menu.addAction(action)
            menu.addMenu(preset_menu)
            menu.addSeparator()

            top_action = QAction(t("置顶"), menu)
            top_action.triggered.connect(lambda: self._reorder_graphic(graphic, "top"))
            menu.addAction(top_action)

            bottom_action = QAction(t("置底"), menu)
            bottom_action.triggered.connect(lambda: self._reorder_graphic(graphic, "bottom"))
            menu.addAction(bottom_action)

            lock_action = QAction(t("锁定") if not getattr(graphic, "_locked", False) else t("解锁"), menu)
            lock_action.triggered.connect(lambda: self._toggle_lock(graphic))
            menu.addAction(lock_action)
        else:
            paste_action = QAction(t("粘贴"), menu)
            paste_action.triggered.connect(self.paste_clipboard)
            menu.addAction(paste_action)

            clear_action = QAction(t("清空全部"), menu)
            clear_action.triggered.connect(self.clear_all)
            menu.addAction(clear_action)

        menu.exec(event.globalPos())

    def _apply_preset_to_selected(self, preset_key: str):
        self._save_undo()
        for g in self.selected_graphics():
            apply_preset(g, preset_key)
        self._refresh_property_panel()
        self.canvas._save_timer.start(500)

    def _reorder_graphic(self, graphic, direction: str):
        if graphic not in self.graphics:
            return
        self._save_undo()
        self.graphics.remove(graphic)
        if direction == "top":
            self.graphics.append(graphic)
        else:
            self.graphics.insert(0, graphic)
        for i, g in enumerate(self.graphics):
            g.setZValue(i)
        self.canvas._save_timer.start(500)

    def _toggle_lock(self, graphic):
        locked = getattr(graphic, "_locked", False)
        graphic._locked = not locked
        graphic.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, not graphic._locked)
        graphic.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, not graphic._locked)

    # ── 选择管理 ──

    def selected_graphics(self):
        """返回当前选中的图形列表"""
        return [g for g in self.graphics if g.isSelected()]

    def select_graphic(self, graphic, append=False):
        """选中图形"""
        if not append:
            self.deselect_all()
        graphic.setSelected(True)
        self._refresh_property_panel()

    def deselect_graphic(self, graphic):
        """取消选中"""
        graphic.setSelected(False)
        self._refresh_property_panel()

    def deselect_all(self):
        """取消所有选中"""
        for g in self.graphics:
            g.setSelected(False)
        self._refresh_property_panel()

    def select_all(self):
        """全选所有图形"""
        for g in self.graphics:
            g.setSelected(True)
        self._refresh_property_panel()

    # ── 复制粘贴 ──

    def copy_selected(self):
        """复制选中图形到剪贴板（内存）"""
        selected = self.selected_graphics()
        if not selected:
            return
        self._clipboard = [g.to_dict() for g in selected]

    def paste_clipboard(self):
        """粘贴剪贴板图形"""
        if not hasattr(self, "_clipboard") or not self._clipboard:
            return
        self._save_undo()
        self.deselect_all()
        offset = 20
        for data in self._clipboard:
            data = dict(data)  # 深拷贝
            # 偏移位置
            if "points" in data:
                data["points"] = [[p[0] + offset, p[1] + offset] for p in data["points"]]
            if "x" in data:
                data["x"] += offset
            if "y" in data:
                data["y"] += offset
            g = GraphicBase.from_dict(data)
            if g:
                self.canvas.scene.addItem(g)
                self.graphics.append(g)
                g.setSelected(True)
        self._refresh_property_panel()
        self.canvas._save_timer.start(500)

    # ── 文本编辑 ──

    def start_text_editing(self, text_graphic):
        """开始编辑文本图形"""
        if not hasattr(text_graphic, "start_editing"):
            return
        self._save_undo()
        text_graphic.start_editing()
        # 编辑完成后自动保存
        self.canvas._save_timer.start(500)

    # ── 删除 ──

    def delete_selected(self):
        selected = self.selected_graphics()
        if selected:
            self.delete_graphics(selected)

    def delete_graphics(self, graphics):
        """删除指定图形列表"""
        self._save_undo()
        for g in list(graphics):
            self.canvas.scene.removeItem(g)
            if g in self.graphics:
                self.graphics.remove(g)
        self.deselect_all()
        self.canvas._save_timer.start(500)

    def clear_all(self):
        self._save_undo()
        for g in self.graphics:
            self.canvas.scene.removeItem(g)
        self.graphics.clear()
        self.canvas._save_timer.start(500)

    # ── 撤销/重做（复用现有快照系统）──

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
            if g:
                self.canvas.scene.addItem(g)
                self.graphics.append(g)
        self._refresh_property_panel()

    # ── 持久化 ──

    def to_json(self):
        return [g.to_dict() for g in self.graphics]

    def from_json(self, data):
        for g in self.graphics:
            self.canvas.scene.removeItem(g)
        self.graphics.clear()
        for d in (data or []):
            g = GraphicBase.from_dict(d)
            if g:
                self.canvas.scene.addItem(g)
                self.graphics.append(g)
        self._refresh_property_panel()

    def resize_toolbar(self):
        if self.toolbar and self._toolbar_visible:
            self.toolbar.setGeometry(0, 0, 36, self.canvas.height())
