"""
锚点项（输入/输出端口）
继承自 QGraphicsEllipseItem，负责节点端口的视觉渲染和悬停交互
"""
from PyQt6.QtWidgets import QGraphicsEllipseItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor


class AnchorItem(QGraphicsEllipseItem):
    """锚点项（输入/输出端口）"""
    
    def __init__(self, x, y, anchor_type="input", parent=None):
        super().__init__(x, y, 16, 16, parent)  # 增大到16x16
        self.anchor_type = anchor_type  # "input" 或 "output"
        
        # 设置颜色（从父节点获取画布配置）
        self.update_anchor_color()
        
        self.setPen(QPen(QColor("#333"), 2))  # 加粗边框
        self.setZValue(10)  # 确保在最上层
        
        # 悬停效果
        self.setAcceptHoverEvents(True)
    
    def update_anchor_color(self):
        """更新锚点颜色（从画布配置读取）"""
        if self.parentItem() and hasattr(self.parentItem(), 'canvas') and self.parentItem().canvas:
            canvas = self.parentItem().canvas
            color_hex = canvas.input_anchor_color if self.anchor_type == "input" else canvas.output_anchor_color
            color = QColor(color_hex)
        else:
            # 默认颜色
            color = QColor("#4CAF50" if self.anchor_type == "input" else "#2196F3")
        
        self.setBrush(color)
        
    def hoverEnterEvent(self, event):
        """鼠标进入时高亮"""
        if self.parentItem() and hasattr(self.parentItem(), 'canvas') and self.parentItem().canvas:
            canvas = self.parentItem().canvas
            base_color = canvas.input_anchor_color if self.anchor_type == "input" else canvas.output_anchor_color
            # 高亮色（稍微亮一点）
            highlight_color = QColor(base_color)
            highlight_color.setAlpha(200)
        else:
            highlight_color = QColor("#66BB6A" if self.anchor_type == "input" else "#42A5F5")
        
        self.setBrush(highlight_color)
        self.setPen(QPen(QColor("#000"), 2.5))  # 更粗的边框
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        """鼠标离开时恢复"""
        self.update_anchor_color()
        self.setPen(QPen(QColor("#333"), 2))
        super().hoverLeaveEvent(event)
