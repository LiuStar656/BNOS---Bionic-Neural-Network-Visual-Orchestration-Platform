"""
连线条（ComfyUI 风格直角正交直线 + 反复折叠）
继承自 QGraphicsPathItem，负责节点间连线的视觉渲染和路径计算
"""
import math
import copy
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsPolygonItem
from PyQt6.QtCore import Qt, QPointF, QLineF, QRectF
from PyQt6.QtGui import QPen, QColor, QPainterPath, QPolygonF, QPainterPathStroker
from ui.core.logger import logger


class EdgeItem(QGraphicsPathItem):
    """连线条（ComfyUI 风格直角正交直线 + 可折叠）

    渲染策略：
      - 贝塞尔曲线 → 直角正交直线
      - 支持自动路由和手动折叠点（waypoints）
      - 双击线段添加折叠点，双击折叠点删除
    """

    HOVER_WIDTH_DELTA = 4
    SHAPE_HIT_WIDTH = 8
    _STEP = 40   # 直角转弯的水平偏移量

    def __init__(self, start_node, end_node, canvas=None):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.canvas = canvas
        self._is_selected = False
        self._base_width = 2.5

        # 手动折叠点（场景坐标），空列表 = 自动路由
        self._waypoints = []

        # 渲染缓存
        self.setCacheMode(QGraphicsPathItem.CacheMode.DeviceCoordinateCache)
        self.update_edge_style()

        # 交互
        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)

        # 箭头
        self.arrow_item = None

    # ═══════════════════════════════════════════
    #  样式
    # ═══════════════════════════════════════════

    def update_edge_style(self):
        """更新连线样式"""
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
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)

    def change_edge_color(self):
        """修改单条连线颜色"""
        from PyQt6.QtWidgets import QColorDialog
        current = QColor(self.canvas.edge_color) if self.canvas else QColor("#4A90E2")
        color = QColorDialog.getColor(current, None, "选择连线颜色")
        if color.isValid():
            self._edge_color = color
            pen = QPen(color, self._base_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            self.setPen(pen)
            if self.arrow_item:
                self.arrow_item.setBrush(color)
            self.update()

    # ═══════════════════════════════════════════
    #  选中与悬停
    # ═══════════════════════════════════════════

    def paint(self, painter, option, widget=None):
        """选中/悬停时加宽"""
        if self.isSelected() or option.state & option.StateFlag.State_MouseOver:
            pen = QPen(self._edge_color, self._base_width + self.HOVER_WIDTH_DELTA)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
        else:
            painter.setPen(self.pen())
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        if self.arrow_item:
            if self.isSelected():
                self.arrow_item.setBrush(QColor("#007acc"))
            elif option.state & option.StateFlag.State_MouseOver:
                self.arrow_item.setBrush(self._edge_color.lighter(130))
            else:
                self.arrow_item.setBrush(self._edge_color)

    def shape(self):
        """点击检测区域"""
        stroker = QPainterPathStroker()
        stroker.setWidth(self.SHAPE_HIT_WIDTH)
        return stroker.createStroke(self.path())

    # ═══════════════════════════════════════════
    #  右键菜单（委托给 canvas）
    # ═══════════════════════════════════════════

    def contextMenuEvent(self, event):
        event.ignore()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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

    def mouseDoubleClickEvent(self, event):
        """双击添加/删除折叠点"""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return

        pos = event.scenePos()
        segments = self._get_orthogonal_points()

        # 检查是否双击了现有的折叠点
        for i, wp in enumerate(self._waypoints):
            if QLineF(wp, pos).length() < 12:
                del self._waypoints[i]
                self.update_path()
                logger.debug("删除折叠点 #%d", i)
                return

        # 找到最近的线段插入折叠点
        best_seg = -1
        best_dist = 1e9
        for i in range(len(segments) - 1):
            a, b = segments[i], segments[i + 1]
            line = QLineF(a, b)
            # 投影距离
            line_len = line.length()
            if line_len < 1:
                continue
            t = max(0.0, min(1.0, QLineF.dotProduct(pos - a, b - a) / (line_len * line_len)))
            proj = a + (b - a) * t
            dist = QLineF(pos, proj).length()
            if dist < best_dist:
                best_dist = dist
                best_seg = i

        if best_seg >= 0 and best_dist < 30:
            # 在该线段位置插入新折叠点
            a, b = segments[best_seg], segments[best_seg + 1]
            line = QLineF(a, b)
            line_len = line.length()
            if line_len > 0:
                t_clamped = max(0.1, min(0.9, QLineF.dotProduct(pos - a, b - a) / (line_len * line_len)))
                new_wp = a + (b - a) * t_clamped
                # 如果线段是水平线，投影到垂直方向；如果是垂直线，投影到水平方向
                if abs(a.x() - b.x()) < 5:  # 垂直线段
                    new_wp = QPointF(new_wp.x(), pos.y())
                else:  # 水平线段
                    new_wp = QPointF(pos.x(), new_wp.y())

                self._waypoints.append(new_wp)
                self.update_path()
                logger.debug("添加折叠点 @ (%.0f, %.0f)", new_wp.x(), new_wp.y())

        super().mouseDoubleClickEvent(event)

    # ═══════════════════════════════════════════
    #  路径计算（核心）
    # ═══════════════════════════════════════════

    def _get_orthogonal_points(self):
        """计算所有直角路径点（从源锚点到目标锚点）

        有手动折叠点时使用缝合；无则自动路由。

        Returns:
            list[QPointF] 从源锚点到目标锚点的所有拐点
        """
        start = self.start_node.output_anchor.sceneBoundingRect().center()
        end = self.end_node.input_anchor.sceneBoundingRect().center()

        if self._waypoints:
            # 手动折叠模式：缝合源 → 折叠点 → 目标
            return [start] + list(self._waypoints) + [end]

        return self._auto_route(start, end)

    def _auto_route(self, src, dst):
        """ComfyUI 风格自动正交路由

        规则：
          - 源锚点在节点右边缘，目标锚点在左边缘
          - src.x < dst.x（正常情况）：L 形右拐
          - src.x >= dst.x（需要折叠）：反向折叠路径
        """
        step = self._STEP

        if src.x() + step + 20 < dst.x():
            # 源在左侧有足够空间 → 简单 L 形
            return [
                src,
                QPointF(src.x() + step, src.y()),
                QPointF(src.x() + step, dst.y()),
                dst,
            ]
        else:
            # 源在右侧或间距不足 → 折叠路径
            # 向源右侧延伸 → 垂直折回 → 水平左行 → 垂直对齐 → 进入目标
            mid_y = (src.y() + dst.y()) / 2
            return [
                src,
                QPointF(src.x() + step, src.y()),           # → 右出
                QPointF(src.x() + step, mid_y),             # ─ 垂直折到中间
                QPointF(dst.x() - step, mid_y),             # ← 水平左行
                QPointF(dst.x() - step, dst.y()),           # ─ 垂直对齐目标
                dst,
            ]

    def update_path(self):
        """重建连线路径（直角正交直线）"""
        if not self.start_node or not self.end_node:
            return

        points = self._get_orthogonal_points()
        path = QPainterPath()
        path.moveTo(points[0])
        for p in points[1:]:
            path.lineTo(p)

        self.setCacheMode(QGraphicsPathItem.CacheMode.NoCache)
        self.setPath(path)
        self.setCacheMode(QGraphicsPathItem.CacheMode.DeviceCoordinateCache)

        # 箭头方向基于最后一段线段
        if len(points) >= 2:
            self._add_arrow(points[-2], points[-1])

    def _add_arrow(self, seg_start, seg_end):
        """在终点添加箭头（基于最后一条线段的方向）"""
        dx = seg_end.x() - seg_start.x()
        dy = seg_end.y() - seg_start.y()
        angle = math.atan2(dy, dx)

        arrow_size = 10
        arrow_angle = math.pi / 6

        p1 = QPointF(
            seg_end.x() - arrow_size * math.cos(angle - arrow_angle),
            seg_end.y() - arrow_size * math.sin(angle - arrow_angle),
        )
        p2 = QPointF(
            seg_end.x() - arrow_size * math.cos(angle + arrow_angle),
            seg_end.y() - arrow_size * math.sin(angle + arrow_angle),
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
        self.arrow_item.setAcceptHoverEvents(False)
        self.arrow_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    # ═══════════════════════════════════════════
    #  折叠点管理
    # ═══════════════════════════════════════════

    @property
    def waypoints(self):
        """获取折叠点列表（场景坐标副本）"""
        return list(self._waypoints)

    def set_waypoints(self, points):
        """设置折叠点并刷新路径"""
        self._waypoints = [QPointF(p) for p in points]
        self.update_path()

    def clear_waypoints(self):
        """清除手动折叠点，恢复自动路由"""
        self._waypoints.clear()
        self.update_path()

    def add_waypoint(self, pos: QPointF):
        """添加单个折叠点"""
        self._waypoints.append(QPointF(pos))
        self.update_path()

    def remove_waypoint_at(self, index: int):
        """删除指定索引的折叠点"""
        if 0 <= index < len(self._waypoints):
            del self._waypoints[index]
            self.update_path()

    def _find_nearest_segment(self, pos: QPointF):
        """查找离 pos 最近的线段索引"""
        points = self._get_orthogonal_points()
        best, best_dist = -1, 1e9
        for i in range(len(points) - 1):
            a, b = points[i], points[i + 1]
            line = QLineF(a, b)
            ll = line.length()
            if ll < 1:
                continue
            t = max(0.0, min(1.0, QLineF.dotProduct(pos - a, b - a) / (ll * ll)))
            proj = a + (b - a) * t
            dist = QLineF(pos, proj).length()
            if dist < best_dist:
                best_dist = dist
                best = i
        return best, best_dist

    # ═══════════════════════════════════════════
    #  序列化
    # ═══════════════════════════════════════════

    def to_dict(self):
        """序列化折叠点"""
        if self._waypoints:
            return {"waypoints": [(p.x(), p.y()) for p in self._waypoints]}
        return {}

    def from_dict(self, data: dict):
        """从字典恢复折叠点"""
        if data and "waypoints" in data:
            self._waypoints = [QPointF(x, y) for x, y in data["waypoints"]]
        else:
            self._waypoints = []

    # ═══════════════════════════════════════════
    #  生命周期
    # ═══════════════════════════════════════════

    def remove_from_scene(self):
        scene = self.scene()
        if scene:
            scene.removeItem(self)
