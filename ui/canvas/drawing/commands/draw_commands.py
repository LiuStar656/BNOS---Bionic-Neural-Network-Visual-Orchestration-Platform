"""
绘图层命令系统 — 接入 HistoryManager 的精细化撤销重做
"""
from ui.core.commands.base import Command


class DrawCommand(Command):
    """绘图层操作基类"""
    pass


class AddGraphicCommand(DrawCommand):
    """添加图形命令"""

    def __init__(self, draw_layer, graphic):
        self.draw_layer = draw_layer
        self.graphic = graphic
        self._executed = False

    def execute(self):
        if not self._executed:
            self.draw_layer.scene.addItem(self.graphic)
            self.draw_layer.graphics.append(self.graphic)
            self._executed = True

    def undo(self):
        if self._executed:
            self.draw_layer.scene.removeItem(self.graphic)
            if self.graphic in self.draw_layer.graphics:
                self.draw_layer.graphics.remove(self.graphic)
            self._executed = False

    def description(self) -> str:
        return f"创建{self.graphic.gtype}"


class DeleteGraphicCommand(DrawCommand):
    """删除图形命令"""

    def __init__(self, draw_layer, graphics):
        self.draw_layer = draw_layer
        self.graphics = list(graphics)
        self._executed = False

    def execute(self):
        for g in self.graphics:
            self.draw_layer.scene.removeItem(g)
            if g in self.draw_layer.graphics:
                self.draw_layer.graphics.remove(g)
        self._executed = True

    def undo(self):
        for g in self.graphics:
            self.draw_layer.scene.addItem(g)
            self.draw_layer.graphics.append(g)
        self._executed = False

    def description(self) -> str:
        return f"删除 {len(self.graphics)} 个图形"


class MoveGraphicCommand(DrawCommand):
    """移动图形命令"""

    def __init__(self, graphics, deltas):
        self.graphics = list(graphics)
        self.deltas = list(deltas)
        self._executed = False

    def execute(self):
        for g, (dx, dy) in zip(self.graphics, self.deltas):
            g.moveBy(dx, dy)
        self._executed = True

    def undo(self):
        for g, (dx, dy) in zip(self.graphics, self.deltas):
            g.moveBy(-dx, -dy)
        self._executed = False

    def description(self) -> str:
        return f"移动 {len(self.graphics)} 个图形"


class StyleChangeCommand(DrawCommand):
    """样式修改命令"""

    def __init__(self, graphics, old_styles, new_styles):
        self.graphics = list(graphics)
        self.old_styles = list(old_styles)
        self.new_styles = list(new_styles)
        self._executed = False

    def execute(self):
        for g, style in zip(self.graphics, self.new_styles):
            g.set_style(**style)
        self._executed = True

    def undo(self):
        for g, style in zip(self.graphics, self.old_styles):
            g.set_style(**style)
        self._executed = False

    def description(self) -> str:
        return f"修改 {len(self.graphics)} 个图形样式"


class ReorderCommand(DrawCommand):
    """图层顺序调整命令"""

    def __init__(self, draw_layer, graphic, old_index, new_index):
        self.draw_layer = draw_layer
        self.graphic = graphic
        self.old_index = old_index
        self.new_index = new_index

    def execute(self):
        self._move(self.new_index)

    def undo(self):
        self._move(self.old_index)

    def _move(self, idx):
        if self.graphic in self.draw_layer.graphics:
            self.draw_layer.graphics.remove(self.graphic)
            self.draw_layer.graphics.insert(idx, self.graphic)
            # zValue 同步
            for i, g in enumerate(self.draw_layer.graphics):
                g.setZValue(i)

    def description(self) -> str:
        return "调整图层顺序"


class TextEditCommand(DrawCommand):
    """文本编辑命令"""

    def __init__(self, text_graphic, old_text, new_text):
        self.text_graphic = text_graphic
        self.old_text = old_text
        self.new_text = new_text

    def execute(self):
        self.text_graphic.set_text(self.new_text)

    def undo(self):
        self.text_graphic.set_text(self.old_text)

    def description(self) -> str:
        return "修改文本内容"
