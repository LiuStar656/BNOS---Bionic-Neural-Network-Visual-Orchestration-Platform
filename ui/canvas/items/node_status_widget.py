"""
节点状态显示组件 — 实时显示CPU、内存、运行时长等状态信息
"""
from PySide6.QtWidgets import QGraphicsTextItem, QGraphicsRectItem, QGraphicsItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QBrush, QPen, QFont
from ui.core.logger import logger


class NodeStatusWidget:
    """节点状态显示组件"""
    
    def __init__(self, node_item):
        self.node_item = node_item
        self.canvas = node_item.canvas
        self._style = node_item._style
        
        # CPU 占用显示
        self.cpu_text = QGraphicsTextItem("CPU: 0%", node_item)
        self.cpu_text.setZValue(4)
        self.cpu_text.setDefaultTextColor(QColor("#4ecdc4"))
        
        # CPU 进度条
        self.cpu_bar_bg = QGraphicsRectItem(node_item)
        self.cpu_bar_bg.setZValue(3)
        self.cpu_bar_bg.setBrush(QBrush(QColor("#333333")))
        self.cpu_bar_bg.setPen(QPen(QColor("#555555"), 1))
        
        self.cpu_bar = QGraphicsRectItem(node_item)
        self.cpu_bar.setZValue(3)
        self.cpu_bar.setBrush(QBrush(QColor("#4ecdc4")))
        self.cpu_bar.setPen(QPen(Qt.PenStyle.NoPen))
        
        # 内存使用显示
        self.mem_text = QGraphicsTextItem("MEM: 0MB", node_item)
        self.mem_text.setZValue(4)
        self.mem_text.setDefaultTextColor(QColor("#ff6b6b"))
        
        # 内存进度条
        self.mem_bar_bg = QGraphicsRectItem(node_item)
        self.mem_bar_bg.setZValue(3)
        self.mem_bar_bg.setBrush(QBrush(QColor("#333333")))
        self.mem_bar_bg.setPen(QPen(QColor("#555555"), 1))
        
        self.mem_bar = QGraphicsRectItem(node_item)
        self.mem_bar.setZValue(3)
        self.mem_bar.setBrush(QBrush(QColor("#ff6b6b")))
        self.mem_bar.setPen(QPen(Qt.PenStyle.NoPen))
        
        # 运行时长显示
        self.duration_text = QGraphicsTextItem("00:00:00", node_item)
        self.duration_text.setZValue(4)
        self.duration_text.setDefaultTextColor(QColor("#ffe66d"))
        
        # 初始化状态
        self.cpu_percent = 0
        self.mem_mb = 0
        self.duration_seconds = 0
        
        # 设置字体
        self._setup_fonts()
        # 布局组件
        self._layout_widgets()
        
    def _setup_fonts(self):
        """设置字体样式"""
        font = QFont("Arial", 7)
        font.setBold(True)
        
        self.cpu_text.setFont(font)
        self.mem_text.setFont(font)
        self.duration_text.setFont(font)
        
    def _layout_widgets(self):
        """布局状态显示组件 — 靠左从上到下排列。

        注意：始终从 node_item._style 读取当前尺寸，不缓存旧样式引用。
        这样切换样式（尤其是详细版 → 方形）时，状态栏会正确缩放到新尺寸。
        """
        # 始终读取当前 style，而不是缓存的引用
        current_style = self.node_item._style
        w, h = current_style.node_width, current_style.node_height
        left_margin = 10  # 左边距
        start_y = 12     # 起始Y坐标（在名称下方）
        
        # 运行时长布局（最上面，居中显示）
        dr = self.duration_text.boundingRect()
        self.duration_text.setPos((w - dr.width()) / 2, start_y)
        
        # CPU 信息布局（在时长下方）
        cpu_y = start_y + 20
        self.cpu_text.setPos(left_margin, cpu_y)
        self.cpu_bar_bg.setRect(left_margin, cpu_y + 12, w - 20, 6)
        self.cpu_bar.setRect(left_margin, cpu_y + 12, 0, 6)
        
        # 内存信息布局（在CPU下方）
        mem_y = cpu_y + 28
        self.mem_text.setPos(left_margin, mem_y)
        self.mem_bar_bg.setRect(left_margin, mem_y + 12, w - 20, 6)
        self.mem_bar.setRect(left_margin, mem_y + 12, 0, 6)
        
    def update_status(self, cpu_percent, mem_mb, duration_seconds):
        """更新状态信息。始终使用当前样式尺寸。"""
        self.cpu_percent = max(0, min(100, cpu_percent))
        self.mem_mb = max(0, mem_mb)
        self.duration_seconds = max(0, duration_seconds)

        current_style = self.node_item._style
        w, h = current_style.node_width, current_style.node_height
        left_margin = 10
        start_y = 12
        
        # 更新 CPU 显示
        self.cpu_text.setPlainText(f"CPU: {int(self.cpu_percent)}%")
        cpu_width = (w - 20) * (self.cpu_percent / 100)
        cpu_y = start_y + 20
        self.cpu_bar.setRect(left_margin, cpu_y + 12, cpu_width, 6)
        
        # 更新内存显示
        self.mem_text.setPlainText(f"MEM: {int(self.mem_mb)}MB")
        mem_width = (w - 20) * (min(self.mem_mb, 1024) / 1024)
        mem_y = cpu_y + 28
        self.mem_bar.setRect(left_margin, mem_y + 12, mem_width, 6)
        
        # 更新运行时长
        hours = int(self.duration_seconds // 3600)
        minutes = int((self.duration_seconds % 3600) // 60)
        seconds = int(self.duration_seconds % 60)
        self.duration_text.setPlainText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
    def set_visible(self, visible):
        """设置组件可见性"""
        self.cpu_text.setVisible(visible)
        self.cpu_bar_bg.setVisible(visible)
        self.cpu_bar.setVisible(visible)
        self.mem_text.setVisible(visible)
        self.mem_bar_bg.setVisible(visible)
        self.mem_bar.setVisible(visible)
        self.duration_text.setVisible(visible)
        
    def update_layout(self):
        """更新布局（节点大小变化时调用）"""
        self._layout_widgets()
        self.update_status(self.cpu_percent, self.mem_mb, self.duration_seconds)
