"""
连线条（ComfyUI 风格直线 + 人工折叠）
继承自 QGraphicsPathItem

交互模型：
  - 初始为源→目标的直线
  - 每条直线段中点渲染折叠手柄（小圆点）
  - 长按（300ms）手柄后拖拽 → 在该位置创建折叠点并继续拖拽
  - 松手后，新产生的两段直线各自在中点生成新的折叠手柄
  - 双击折叠点删除
"""
import math
from PyQt6.QtWidgets import (
    QGraphicsPathItem, QGraphicsPolygonItem, QStyle, QGraphicsEllipseItem,
)
from PyQt6.QtCore import Qt, QPointF, QLineF, QTimer
from PyQt6.QtGui import (
    QPen, QColor, QPainterPath, QPolygonF, QPainterPathStroker, QBrush,
)
from ui.core.logger import logger


class EdgeItem(QGraphicsPathItem):
    """直线连线 + 人工折叠手柄"""

    HOVER_WIDTH_DELTA = 4
    SHAPE_HIT_WIDTH = 8
    HANDLE_RADIUS = 5          # 手柄圆点半径
    HANDLE_HIT_MARGIN = 6      # 手柄点击容差
    LONG_PRESS_MS = 250        # 长按触发时间

    def __init__(self, start_node, end_node, canvas=None):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.canvas = canvas
        self._base_width = 2.5
        self._edge_color = QColor("#4A90E2")

        # 折叠点列表（场景坐标），空 = 直线
        self._waypoints: list = []

        # 拖拽状态
        self._drag_seg = -1          # 正在拖拽的线段索引
        self._drag_wp_index = None   # 正在拖拽的折叠点在 _waypoints 中的索引
        self._press_pos = None
        self._long_press_timer = QTimer(self)
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._on_long_press)

        # 手柄可视化：QGraphicsEllipseItem 列表
        self._handle_items: list[QGraphicsEllipseItem] = []

        self.setCacheMode(QGraphicsPathItem.CacheMode.DeviceCoordinateCache)
        self.update_edge_style()

        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
        )

        self.arrow_item = None

    # ═══════════════════════════════════════════
    #  样式
    # ═══════════════════════════════════════════

    def update_edge_style(self):
        if self.canvas:
            self._edge_color = QColor(self.canvas.edge_color)
            self._base_width = self.canvas.edge_width
        pen = QPen(self._edge_color, self._base_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)

    def change_edge_color(self):
        from PyQt6.QtWidgets import QColorDialog
        current = self._edge_color
        color = QColorDialog.getColor(current, None, "选择连线颜色")
        if color.isValid():
            self._edge_color = color
            pen = QPen(color, self._base_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            self.setPen(pen)
            if self.arrow_item:
                self.arrow_item.setBrush(color)
            self._refresh_handles()
            self.update()

    # ═══════════════════════════════════════════
    #  路径与手柄
    # ═══════════════════════════════════════════

    def _endpoints(self):
        """获取源锚点和目标锚点坐标"""
        start = self.start_node.output_anchor.sceneBoundingRect().center()
        end = self.end_node.input_anchor.sceneBoundingRect().center()
        return start, end

    def _polyline_points(self):
        """获取完整折线点序列：src → waypoints → dst"""
        src, dst = self._endpoints()
        return [src] + list(self._waypoints) + [dst]

    def _segment_midpoints(self):
        """返回所有线段中点在场景中的位置列表 [(seg_index, midpoint), ...]"""
        pts = self._polyline_points()
        mids = []
        for i in range(len(pts) - 1):
            mid = (pts[i] + pts[i + 1]) / 2.0
            mids.append((i, QPointF(mid.x(), mid.y())))
        return mids

    def update_path(self):
        if not self.start_node or not self.end_node:
            return

        pts = self._polyline_points()
        path = QPainterPath()
        path.moveTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)

        self.setCacheMode(QGraphicsPathItem.CacheMode.NoCache)
        self.setPath(path)
        self.setCacheMode(QGraphicsPathItem.CacheMode.DeviceCoordinateCache)

        if len(pts) >= 2:
            self._add_arrow(pts[-2], pts[-1])

        self._refresh_handles()

    def _refresh_handles(self):
        """重建手柄圆点"""
        # 清除旧手柄
        for h in self._handle_items:
            if h.scene():
                h.scene().removeItem(h)
        self._handle_items.clear()

        scene = self.scene()
        if scene is None:
            return

        for seg_i, mid in self._segment_midpoints():
            handle = QGraphicsEllipseItem(
                mid.x() - self.HANDLE_RADIUS,
                mid.y() - self.HANDLE_RADIUS,
                self.HANDLE_RADIUS * 2,
                self.HANDLE_RADIUS * 2,
                self,
            )
            handle.setBrush(QBrush(self._edge_color))
            handle.setPen(QPen(Qt.PenStyle.NoPen))
            handle.setZValue(3)
            handle.setAcceptHoverEvents(True)
            handle.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
            self._handle_items.append(handle)

    def _add_arrow(self, seg_start, seg_end):
        dx = seg_end.x() - seg_start.x()
        dy = seg_end.y() - seg_start.y()
        angle = math.atan2(dy, dx)

        arrow_size = 10
        aa = math.pi / 6
        p1 = QPointF(
            seg_end.x() - arrow_size * math.cos(angle - aa),
            seg_end.y() - arrow_size * math.sin(angle - aa),
        )
        p2 = QPointF(
            seg_end.x() - arrow_size * math.cos(angle + aa),
            seg_end.y() - arrow_size * math.sin(angle + aa),
        )

        arrow = QPolygonF([QPointF(seg_end), p1, p2])
        scene = self.scene()
        if scene is None:
            return
        if self.arrow_item:
            scene.removeItem(self.arrow_item)

        self.arrow_item = QGraphicsPolygonItem(self)
        self.arrow_item.setPolygon(arrow)
        self.arrow_item.setBrush(self._edge_color)
        self.arrow_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.arrow_item.setZValue(2)

    # ═══════════════════════════════════════════
    #  渲染
    # ═══════════════════════════════════════════

    def paint(self, painter, option, widget=None):
        # 直线本体
        if self.isSelected() or (option.state & QStyle.StateFlag.State_MouseOver):
            pen = QPen(self._edge_color, self._base_width + self.HOVER_WIDTH_DELTA)
        else:
            pen = self.pen()
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        # 折叠点小圆（非拖拽态时绘制）
        if self._drag_wp_index is None and (self.isSelected() or
                                             option.state & QStyle.StateFlag.State_MouseOver):
            for seg_i, mid in self._segment_midpoints():
                painter.setPen(QPen(Qt.PenStyle.NoPen))
                painter.setBrush(QBrush(self._edge_color))
                painter.drawEllipse(mid, self.HANDLE_RADIUS, self.HANDLE_RADIUS)

        # 箭头
        if self.arrow_item:
            if self.isSelected():
                self.arrow_item.setBrush(QColor("#007acc"))
            elif option.state & QStyle.StateFlag.State_MouseOver:
                self.arrow_item.setBrush(self._edge_color.lighter(130))
            else:
                self.arrow_item.setBrush(self._edge_color)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(self.SHAPE_HIT_WIDTH)
        return stroker.createStroke(self.path())

    # ═══════════════════════════════════════════
    #  交互：长按拖拽折叠
    # ═══════════════════════════════════════════

    def _hit_handle(self, pos: QPointF):
        """检测点击位置是否命中某个手柄，返回线段索引或 -1"""
        for seg_i, mid in self._segment_midpoints():
            if QLineF(mid, pos).length() <= self.HANDLE_RADIUS + self.HANDLE_HIT_MARGIN:
                return seg_i
        return -1

    def _hit_waypoint(self, pos: QPointF):
        """检测是否命中某个折叠点（双击删除用），返回 waypoints 索引或 -1"""
        for i, wp in enumerate(self._waypoints):
            if QLineF(wp, pos).length() <= 10:
                return i
        return -1

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.scenePos()

            # 检测双击折叠点（由 mouseDoubleClickEvent 处理，这里不拦截）
            seg = self._hit_handle(pos)
            if seg >= 0:
                # 命中手柄 → 开始长按计时
                self._press_pos = pos
                self._drag_seg = seg
                self._long_press_timer.start(self.LONG_PRESS_MS)
                event.accept()
                return

            # 未命中手柄 → 普通选中
            self.setSelected(True)
            event.accept()
            return

        elif event.button() == Qt.MouseButton.RightButton:
            if not self.isSelected():
                if self.scene():
                    self.scene().clearSelection()
                self.setSelected(True)
            event.ignore()
            return
        super().mousePressEvent(event)

    def _on_long_press(self):
        """长按触发：在拖拽手柄位置创建折叠点"""
        if self._drag_seg < 0:
            return
        pts = self._polyline_points()
        seg = self._drag_seg
        if seg >= len(pts) - 1:
            return
        # 在手柄中点位置插入新折叠点
        mid = (pts[seg] + pts[seg + 1]) / 2.0
        self._waypoints.insert(seg, QPointF(mid))
        self._drag_wp_index = seg
        self.update_path()
        logger.debug("长按折叠 线段#%d → 新折叠点 #%d", seg, seg)

    def mouseMoveEvent(self, event):
        if self._drag_wp_index is not None:
            # 拖拽折叠点
            wp_idx = self._drag_wp_index
            if 0 <= wp_idx < len(self._waypoints):
                self._waypoints[wp_idx] = event.scenePos()
                self.update_path()
            return

        # 如果长按计时器还在跑但鼠标移动了 → 取消长按
        if self._long_press_timer.isActive() and self._press_pos is not None:
            if QLineF(self._press_pos, event.scenePos()).length() > 5:
                self._long_press_timer.stop()
                self._drag_seg = -1

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._long_press_timer.stop()

        if self._drag_wp_index is not None:
            # 结束拖拽：折叠点保留，新线段自动生成手柄
            self._drag_wp_index = None
            self._drag_seg = -1
            self._press_pos = None
            self.update_path()
            return

        self._drag_seg = -1
        self._press_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """双击折叠点删除"""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return

        pos = event.scenePos()
        idx = self._hit_waypoint(pos)
        if idx >= 0:
            del self._waypoints[idx]
            self.update_path()
            logger.debug("双击删除折叠点 #%d", idx)
            return

        super().mouseDoubleClickEvent(event)

    # ═══════════════════════════════════════════
    #  右键（委托给 canvas）
    # ═══════════════════════════════════════════

    def contextMenuEvent(self, event):
        event.ignore()

    # ═══════════════════════════════════════════
    #  折叠点 API
    # ═══════════════════════════════════════════

    @property
    def waypoints(self):
        return list(self._waypoints)

    def set_waypoints(self, points):
        self._waypoints = [QPointF(p) for p in points]
        self.update_path()

    def clear_waypoints(self):
        self._waypoints.clear()
        self.update_path()

    def add_waypoint(self, pos: QPointF):
        self._waypoints.append(QPointF(pos))
        self.update_path()

    def remove_waypoint_at(self, index: int):
        if 0 <= index < len(self._waypoints):
            del self._waypoints[index]
            self.update_path()

    # ═══════════════════════════════════════════
    #  序列化
    # ═══════════════════════════════════════════

    def to_dict(self):
        if self._waypoints:
            return {"waypoints": [(p.x(), p.y()) for p in self._waypoints]}
        return {}

    def from_dict(self, data: dict):
        if data and "waypoints" in data:
            self._waypoints = [QPointF(x, y) for x, y in data["waypoints"]]
        else:
            self._waypoints = []

    # ═══════════════════════════════════════════
    #  生命周期
    # ═══════════════════════════════════════════

    def remove_from_scene(self):
        for h in self._handle_items:
            if h.scene():
                h.scene().removeItem(h)
        self._handle_items.clear()
        scene = self.scene()
        if scene:
            scene.removeItem(self)
