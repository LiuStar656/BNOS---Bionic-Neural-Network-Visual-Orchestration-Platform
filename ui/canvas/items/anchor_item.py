"""
锚点项（输入/输出端口）
继承自 QGraphicsEllipseItem，负责节点端口的视觉渲染、悬停交互和双向绑定

重构说明（多锚点系统）：
- 尺寸常量统一为 ANCHOR_SIZE / ANCHOR_HALF
- 新增 port_name / port_type / port_label 属性，记录该锚点对应的端口信息
- 单锚点（默认 "default"）与多锚点（根据 input_ports 定义生成）共用同一类
"""
from PyQt6.QtWidgets import QGraphicsEllipseItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor


# 锚点几何常量。全系统共用，避免分散在各文件里硬编码 16/8。
ANCHOR_SIZE = 16          # 默认锚点尺寸（listen_upper_file / output）
ANCHOR_HALF = ANCHOR_SIZE // 2  # = 8
ANCHOR_SIZE_SMALL = 10    # 小锚点尺寸（input_port 贴在标签右侧）
ANCHOR_HALF_SMALL = ANCHOR_SIZE_SMALL // 2  # = 5


class AnchorItem(QGraphicsEllipseItem):
    """锚点项（输入/输出端口）
    支持两种尺寸：
      - 大锚点（16px）：listen_upper_file（主输入）、output（主输出）
      - 小锚点（10px）：其他 input_port（贴在标签右侧）
    """

    def __init__(self, x, y, anchor_type="input", parent=None,
                 port_name: str | None = None, port_type: str = "default",
                 port_label: str = "", size: int = ANCHOR_SIZE):
        super().__init__(x, y, size, size, parent)
        self.anchor_type = anchor_type  # "input" 或 "output"

        # 端口元信息（多锚点系统使用；单锚点默认场景下保持 None/"default"）
        self.port_name = port_name
        self.port_type = port_type
        self.port_label = port_label
        self._size = size  # 锚点尺寸（大锚点=16，小锚点=10）

        # 连接到本锚点的连线列表（双向绑定）
        self.edges: list = []

        # 视觉样式（从画布配置读取颜色）
        self.update_anchor_color()
        # 小锚点的边框更细，视觉上更"小"
        pen_w = 1.5 if size < ANCHOR_SIZE else 2
        self.setPen(QPen(QColor("#333"), pen_w))

        # 悬停效果
        self.setAcceptHoverEvents(True)

    # ---------- 双向绑定 API ----------

    def add_edge(self, edge):
        if edge is not None and edge not in self.edges:
            self.edges.append(edge)

    def remove_edge(self, edge):
        if edge in self.edges:
            self.edges.remove(edge)

    def clear_edges(self):
        self.edges.clear()

    # ---------- 视觉 / 交互 ----------

    def update_anchor_color(self):
        """更新锚点颜色（从画布配置读取）"""
        if self.parentItem() and hasattr(self.parentItem(), 'canvas') and self.parentItem().canvas:
            canvas = self.parentItem().canvas
            color_hex = canvas.input_anchor_color if self.anchor_type == "input" else canvas.output_anchor_color
            color = QColor(color_hex)
        else:
            color = QColor("#4CAF50" if self.anchor_type == "input" else "#2196F3")
        self.setBrush(color)

    def hoverEnterEvent(self, event):
        """鼠标进入时高亮"""
        if self.parentItem() and hasattr(self.parentItem(), 'canvas') and self.parentItem().canvas:
            canvas = self.parentItem().canvas
            base_color = canvas.input_anchor_color if self.anchor_type == "input" else canvas.output_anchor_color
            highlight_color = QColor(base_color)
            highlight_color.setAlpha(200)
        else:
            highlight_color = QColor("#66BB6A" if self.anchor_type == "input" else "#42A5F5")

        self.setBrush(highlight_color)
        self.setPen(QPen(QColor("#000"), 2.5))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # 显示端口信息 tooltip（多锚点模式下才显示端口名）
        if self.port_name and self.port_name != "default":
            label = self.port_label or self.port_name
            tip = f"{label} ({self.port_type})"
            self.setToolTip(tip)
        else:
            self.setToolTip("")

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        """鼠标离开时恢复"""
        self.update_anchor_color()
        # 根据实际尺寸决定边框粗细（大锚点 2px，小锚点 1.5px）
        size = getattr(self, "_size", ANCHOR_SIZE)
        pen_w = 1.5 if size < ANCHOR_SIZE else 2
        self.setPen(QPen(QColor("#333"), pen_w))
        super().hoverLeaveEvent(event)
