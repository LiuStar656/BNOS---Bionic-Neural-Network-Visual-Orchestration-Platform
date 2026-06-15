"""
节点状态显示组件 — 实时显示CPU、内存占用信息
"""
from PySide6.QtWidgets import QGraphicsTextItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from ui.core.logger import logger


class NodeStatusWidget:
    """节点状态显示组件 — 仅显示 CPU/MEM 文本，无进度条
    
    布局模式：
      - 紧凑模式(detailed)：CPU/MEM 并列在节点外底部左下角
      - 普通模式(rect)：CPU/MEM 显示在节点内底部
    """
    
    def __init__(self, node_item):
        self.node_item = node_item
        self.canvas = node_item.canvas
        self._style = node_item._style
        self._compact = True  # 默认紧凑模式（仅文本）
        self._custom_y_offset = None  # 自定义 Y 偏移（None 表示用默认位置）
        
        # CPU 文本
        self.cpu_text = QGraphicsTextItem("CPU: 0%", node_item)
        self.cpu_text.setZValue(4)
        self.cpu_text.setDefaultTextColor(QColor("#4ecdc4"))
        
        # 内存文本
        self.mem_text = QGraphicsTextItem("MEM: 0MB", node_item)
        self.mem_text.setZValue(4)
        self.mem_text.setDefaultTextColor(QColor("#ff6b6b"))
        
        # 状态数据
        self.cpu_percent = 0
        self.mem_mb = 0
        
        # 字体与布局
        self._setup_fonts()
        self._layout_widgets()

    def set_compact(self, enable: bool):
        """设置模式：compact 模式下 CPU/MEM 并列在节点外左下角"""
        self._compact = enable
        self._layout_widgets()

    def set_bottom_y(self, y_bottom: int):
        """设置自定义底部 Y 坐标 — 用于让 CPU/MEM 文本紧贴在语言标签下方"""
        self._custom_y_offset = y_bottom
        self._layout_widgets()

    def _setup_fonts(self):
        """设置字体样式"""
        font = QFont("Arial", 7)
        font.setBold(True)
        self.cpu_text.setFont(font)
        self.mem_text.setFont(font)
        
    def _layout_widgets(self):
        """布局 CPU/MEM 文本 — 居中对齐并紧贴节点最底端"""
        current_style = self.node_item._style
        w, h = current_style.node_width, current_style.node_height
        
        if self._compact:
            # 紧凑模式：CPU/MEM 靠左显示在节点外底部（与语言标签在同一水平线）
            y_pos = self._custom_y_offset if self._custom_y_offset is not None else h
            self.cpu_text.setPos(8, y_pos)
            self.cpu_text.setVisible(True)
            cpu_w = self.cpu_text.boundingRect().width()
            self.mem_text.setPos(8 + cpu_w + 12, y_pos)
            self.mem_text.setVisible(True)
        else:
            # 普通模式：CPU/MEM 居中显示在节点底部内侧
            bottom_y = h - 18
            cpu_w = self.cpu_text.boundingRect().width()
            mem_w = self.mem_text.boundingRect().width()
            total_w = cpu_w + 12 + mem_w
            start_x = max(0, (w - total_w) / 2)
            self.cpu_text.setPos(start_x, bottom_y)
            self.cpu_text.setVisible(True)
            self.mem_text.setPos(start_x + cpu_w + 12, bottom_y)
            self.mem_text.setVisible(True)
        
    def update_status(self, cpu_percent, mem_mb):
        """更新状态信息"""
        self.cpu_percent = max(0, min(100, cpu_percent))
        self.mem_mb = max(0, mem_mb)
        
        self.cpu_text.setPlainText(f"CPU: {int(self.cpu_percent)}%")
        self.mem_text.setPlainText(f"MEM: {int(self.mem_mb)}MB")
        self._layout_widgets()
        
    def set_visible(self, visible):
        """设置组件可见性"""
        self.cpu_text.setVisible(visible)
        self.mem_text.setVisible(visible)
        
    def update_layout(self):
        """更新布局（节点大小变化时调用）"""
        self._layout_widgets()
        self.update_status(self.cpu_percent, self.mem_mb)
