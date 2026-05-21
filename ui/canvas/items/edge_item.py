"""
连线条（贝塞尔曲线，对应VueFlow连线）
继承自 QGraphicsPathItem，负责节点间连线的视觉渲染和路径计算
"""
import math
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsPolygonItem, QMenu, QStyle
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QColor, QPainterPath, QPolygonF, QPainterPathStroker
from ui.core.logger import logger


class EdgeItem(QGraphicsPathItem):
    """连线条（贝塞尔曲线，对应VueFlow连线）"""

    # 连线被点击时的视觉加宽量
    HOVER_WIDTH_DELTA = 4
    # shape 点击检测区域的额外宽度
    SHAPE_HIT_WIDTH = 8

    def __init__(self, start_node, end_node, canvas=None):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.canvas = canvas
        self._is_selected = False
        self._base_width = 2.5

        # 可视区域渲染：连线缓存
        self.setCacheMode(QGraphicsPathItem.CacheMode.DeviceCoordinateCache)

        # 样式（使用画布配置）
        self.update_edge_style()

        # 启用选中 + 悬停
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        # 箭头项（初始为None）
        self.arrow_item = None

    def update_edge_style(self):
        """更新连线样式（使用画布的颜色配置）"""
        if self.canvas:
            color = QColor(self.canvas.edge_color)
            width = self.canvas.edge_width
        else:
            color = QColor("#4A90E2")
            width = 2.5

        self._base_width = width
        self._edge_color = color
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)

    # ── 选中与悬停视觉反馈 ──

    def paint(self, painter, option, widget=None):
        """自定义绘制：选中/悬停时加宽连线"""
        if self.isSelected() or option.state & QStyle.StateFlag.State_MouseOver:
            pen = QPen(self._edge_color, self._base_width + self.HOVER_WIDTH_DELTA)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
        else:
            painter.setPen(self.pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # 更新箭头颜色（选中时加粗箭头无意义，仅同步颜色）
        if self.arrow_item:
            if self.isSelected():
                self.arrow_item.setBrush(QColor("#007acc"))
            elif option.state & QStyle.StateFlag.State_MouseOver:
                self.arrow_item.setBrush(self._edge_color.lighter(130))
            else:
                self.arrow_item.setBrush(self._edge_color)

    def shape(self):
        """返回加宽的 shape 用于点击检测"""
        stroker = QPainterPathStroker()
        stroker.setWidth(self.SHAPE_HIT_WIDTH)
        return stroker.createStroke(self.path())

    # ── 右键菜单 ──

    def contextMenuEvent(self, event):
        """连线右键菜单 - 移除此处的菜单处理，统一由 CanvasMenusMixin 处理"""
        # 不处理，让事件传递到 canvas 的 contextMenuEvent
        event.ignore()

    def mousePressEvent(self, event):
        """鼠标按下：左键选中，右键交给 canvas 处理"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.setSelected(True)
            event.accept()
            return
        elif event.button() == Qt.MouseButton.RightButton:
            # 确保右键时该连线被选中（便于 canvas 菜单判断）
            if not self.isSelected():
                # 清除画布其他选中，单选该连线
                if self.scene():
                    self.scene().clearSelection()
                self.setSelected(True)
            event.ignore()  # 让 canvas 的 contextMenuEvent 接管
            return
        super().mousePressEvent(event)

    # ── 颜色修改 ──

    def change_edge_color(self):
        """修改单条连线的颜色"""
        from PyQt6.QtWidgets import QColorDialog

        current_color = QColor("#4A90E2")
        if self.canvas:
            current_color = QColor(self.canvas.edge_color)

        color = QColorDialog.getColor(current_color, None, "选择连线颜色")

        if color.isValid():
            self._edge_color = color
            pen = QPen(color, self._base_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            self.setPen(pen)

            if hasattr(self, 'arrow_item') and self.arrow_item:
                self.arrow_item.setBrush(color)

            self.update()
            logger.debug("连线颜色已更改为: %s", color.name())

    # ── 路径与箭头 ──

    def update_path(self):
        """更新连线路径"""
        if not self.start_node or not self.end_node:
            return

        # 获取起点和终点的世界坐标（锚点中心）
        start_center = self.start_node.output_anchor.sceneBoundingRect().center()
        end_center = self.end_node.input_anchor.sceneBoundingRect().center()

        # 创建贝塞尔曲线路径
        path = QPainterPath()
        path.moveTo(start_center)

        dx = abs(end_center.x() - start_center.x()) * 0.5
        ctrl1 = QPointF(start_center.x() + dx, start_center.y())
        ctrl2 = QPointF(end_center.x() - dx, end_center.y())

        path.cubicTo(ctrl1, ctrl2, end_center)

        # 先清缓存再设路径（避免旧缓存干扰 shape()）
        self.setCacheMode(QGraphicsPathItem.CacheMode.NoCache)
        self.setPath(path)
        self.setCacheMode(QGraphicsPathItem.CacheMode.DeviceCoordinateCache)

        self.add_arrow(start_center, end_center)

    def add_arrow(self, start_pos, end_pos):
        """在终点添加箭头"""
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        angle = math.atan2(dy, dx)

        arrow_size = 10
        arrow_angle = math.pi / 6

        p1_x = end_pos.x() - arrow_size * math.cos(angle - arrow_angle)
        p1_y = end_pos.y() - arrow_size * math.sin(angle - arrow_angle)
        p2_x = end_pos.x() - arrow_size * math.cos(angle + arrow_angle)
        p2_y = end_pos.y() - arrow_size * math.sin(angle + arrow_angle)

        arrow = QPolygonF([
            QPointF(end_pos.x(), end_pos.y()),
            QPointF(p1_x, p1_y),
            QPointF(p2_x, p2_y)
        ])

        scene = self.scene()
        if scene is None:
            return

        if hasattr(self, 'arrow_item') and self.arrow_item:
            scene.removeItem(self.arrow_item)

        self.arrow_item = QGraphicsPolygonItem(self)  # 设为 EdgeItem 子项
        self.arrow_item.setPolygon(arrow)
        self.arrow_item.setBrush(self._edge_color if hasattr(self, '_edge_color') else QColor("#4A90E2"))
        self.arrow_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.arrow_item.setZValue(2)
        self.arrow_item.setAcceptHoverEvents(False)
        self.arrow_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def remove_from_scene(self):
        """从场景中移除连线（箭头作为子项自动移除）"""
        scene = self.scene()
        if scene:
            scene.removeItem(self)
