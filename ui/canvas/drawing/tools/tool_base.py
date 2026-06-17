"""
绘图工具基类 — 所有绘图工具的抽象接口
"""
from enum import Enum, auto
from PySide6.QtCore import Qt, QPointF


class ToolResult(Enum):
    """工具处理结果"""
    HANDLED = auto()    # 已处理，不继续传递事件
    IGNORED = auto()    # 未处理，继续传递
    FINISHED = auto()   # 操作完成，重置工具状态


class ToolBase:
    """绘图工具基类"""

    def __init__(self, draw_layer, tool_id: str):
        self.draw_layer = draw_layer
        self.tool_id = tool_id
        self.canvas = draw_layer.canvas
        self.scene = draw_layer.canvas.scene

    @property
    def name(self) -> str:
        return self.tool_id

    def on_activate(self):
        """工具被激活时调用"""
        pass

    def on_deactivate(self):
        """工具被切换时调用"""
        pass

    def mouse_press(self, event, scene_pos: QPointF) -> ToolResult:
        """鼠标按下"""
        return ToolResult.IGNORED

    def mouse_move(self, event, scene_pos: QPointF) -> ToolResult:
        """鼠标移动"""
        return ToolResult.IGNORED

    def mouse_release(self, event, scene_pos: QPointF) -> ToolResult:
        """鼠标释放"""
        return ToolResult.IGNORED

    def mouse_double_click(self, event, scene_pos: QPointF) -> ToolResult:
        """双击"""
        return ToolResult.IGNORED

    def key_press(self, event) -> ToolResult:
        """按键"""
        return ToolResult.IGNORED

    def key_release(self, event) -> ToolResult:
        """按键释放"""
        return ToolResult.IGNORED

    def _get_stroke(self) -> str:
        return self.draw_layer._stroke

    def _get_fill(self) -> str:
        return self.draw_layer._fill

    def _get_stroke_w(self) -> float:
        return self.draw_layer._stroke_w

    def _save_undo(self):
        self.draw_layer._save_undo()

    def _record_command(self, command):
        from ui.core.commands.history_manager import HistoryManager
        history = HistoryManager()
        history.execute_command(command)
