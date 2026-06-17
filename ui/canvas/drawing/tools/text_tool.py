"""
文本工具 — 创建文本、双击编辑
"""
from PySide6.QtCore import Qt, QPointF

from .tool_base import ToolBase, ToolResult
from ui.canvas.drawing.graphic_items import TextGraphic
from ui.core.i18n import t


class TextTool(ToolBase):
    """文本工具：点击创建，双击编辑"""

    def __init__(self, draw_layer):
        super().__init__(draw_layer, "text")

    def on_activate(self):
        self.canvas.viewport().setCursor(Qt.CursorShape.IBeamCursor)

    def mouse_press(self, event, scene_pos: QPointF) -> ToolResult:
        if event.button() != Qt.MouseButton.LeftButton:
            return ToolResult.IGNORED

        # 检查是否点击了现有文本，是则进入编辑
        item = self.canvas.scene.itemAt(scene_pos, self.canvas.transform())
        while item:
            if isinstance(item, TextGraphic) and item in self.draw_layer.graphics:
                self.draw_layer.start_text_editing(item)
                return ToolResult.HANDLED
            item = item.parentItem()

        # 创建新文本
        from ui.core.utils.dialog_utils import themed_input
        text = themed_input(self.canvas, t("_k_draw_text_title"), t("_k_draw_text_input"))
        if not text or not text.strip():
            return ToolResult.IGNORED

        self._save_undo()
        g = TextGraphic(text.strip(), scene_pos.x(), scene_pos.y())
        g.set_style(stroke_color=self._get_stroke(), fill_color=self._get_fill())
        self.canvas.scene.addItem(g)
        self.draw_layer.graphics.append(g)
        self.canvas._save_timer.start(500)
        return ToolResult.HANDLED

    def mouse_double_click(self, event, scene_pos: QPointF) -> ToolResult:
        item = self.canvas.scene.itemAt(scene_pos, self.canvas.transform())
        while item:
            if isinstance(item, TextGraphic) and item in self.draw_layer.graphics:
                self.draw_layer.start_text_editing(item)
                return ToolResult.HANDLED
            item = item.parentItem()
        return ToolResult.IGNORED
