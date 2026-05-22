"""
连线条（ComfyUI 风格直线 + 人工折叠）
继承自 QGraphicsPathItem

交互模型：
  - 初始为源→目标的直线
  - 每条直线段中点渲染折叠手柄（小圆点，始终可见）
  - 短按手柄 → 选中线条
  - 长按手柄后拖拽 → 在该位置创建折叠点并继续拖拽
  - 松手后，新产生的两段直线各自在中点生成新的折叠手柄
  - 直接拖拽已有折叠点调整角度
  - 双击折叠点删除
  - 鼠标靠近线段中点时自动高亮手柄
"""
import math
from PyQt6.QtWidgets import (
    QGraphicsPathItem, QGraphicsPolygonItem, QStyle,
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
    HANDLE_RADIUS = 6
    HANDLE_HIT_RADIUS = 15
    WAYPOINT_RADIUS = 6        # 已有折叠点渲染半径
    WAYPOINT_HIT_RADIUS = 14   # 已有折叠点拖拽判定半径
    LONG_PRESS_MS = 250

    def __init__(self, start_node, end_node, canvas=None):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.canvas = canvas
        self._base_width = 2.5
        self._edge_color = QColor("#4A90E2")

        self._waypoints: list = []

        # 拖拽状态
        self._drag_wp_index = None   # 正在拖拽的折叠点索引（None = 未拖拽）
        self._drag_is_new = False    # True=新折叠点（从手柄创建）, False=拖已有折叠点
        self._press_pos = None
        self._press_on_handle = -1   # 按下的手柄索引（-1 = 按在线身上）
        self._long_press_fired = False

        self._long_press_timer = QTimer()
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._on_long_press)

        self._hovered_handle = -1
        self._hovered_wp = -1

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
        color = QColorDialog.getColor(self._edge_color, None, "选择连线颜色")
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
    #  坐标
    # ═══════════════════════════════════════════

    def _endpoints(self):
        start = self.start_node.output_anchor.sceneBoundingRect().center()
        end = self.end_node.input_anchor.sceneBoundingRect().center()
        return start, end

    # ── 相对坐标系统：折叠点以投影比例存储，随节点移动 ──
    # _waypoints_rel: [(t, off_x, off_y), ...]  其中 t∈[0,1] 是沿 src→dst 的投影比例

    @staticmethod
    def _encode_rel(src: QPointF, dst: QPointF, wp_abs: QPointF):
        """绝对坐标 → 相对参数 (t, off_x, off_y)"""
        vec = dst - src
        v2 = vec.x() * vec.x() + vec.y() * vec.y()
        if v2 < 1e-6:
            return (0.5, wp_abs.x() - src.x(), wp_abs.y() - src.y())
        t = max(0.0, min(1.0, QPointF.dotProduct(wp_abs - src, vec) / v2))
        proj = src + vec * t
        return (t, wp_abs.x() - proj.x(), wp_abs.y() - proj.y())

    @staticmethod
    def _decode_rel(src: QPointF, dst: QPointF, rel):
        """相对参数 → 绝对坐标"""
        t, ox, oy = rel
        vec = dst - src
        proj = src + vec * t
        return QPointF(proj.x() + ox, proj.y() + oy)

    def _sync_abs_to_rel(self):
        """当前 _waypoints 视为绝对坐标 → 编码为相对坐标"""
        if not self._waypoints:
            self._waypoints = []
            return
        if not isinstance(self._waypoints[0], tuple):
            src, dst = self._endpoints()
            self._waypoints = [
                self._encode_rel(src, dst, QPointF(p) if not isinstance(p, QPointF) else p)
                for p in self._waypoints
            ]

    def _all_points(self):
        """完整点序列（相对参数解码为绝对坐标）"""
        src, dst = self._endpoints()
        if self._waypoints and isinstance(self._waypoints[0], tuple):
            pts = [src]
            for rel in self._waypoints:
                pts.append(self._decode_rel(src, dst, rel))
            pts.append(dst)
            return pts
        # 兼容旧格式（绝对坐标）
        return [src] + [QPointF(p) if not isinstance(p, QPointF) else p for p in self._waypoints] + [dst]

    def update_path(self):
        if not self.start_node or not self.end_node:
            return
        pts = self._all_points()
        path = QPainterPath()
        path.moveTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
        self.setCacheMode(QGraphicsPathItem.CacheMode.NoCache)
        self.setPath(path)
        self.setCacheMode(QGraphicsPathItem.CacheMode.DeviceCoordinateCache)
        if len(pts) >= 2:
            self._add_arrow(pts[-2], pts[-1])

    def _add_arrow(self, seg_start, seg_end):
        dx = seg_end.x() - seg_start.x()
        dy = seg_end.y() - seg_start.y()
        angle = math.atan2(dy, dx)
        sz, aa = 10, math.pi / 6
        p1 = QPointF(
            seg_end.x() - sz * math.cos(angle - aa),
            seg_end.y() - sz * math.sin(angle - aa),
        )
        p2 = QPointF(
            seg_end.x() - sz * math.cos(angle + aa),
            seg_end.y() - sz * math.sin(angle + aa),
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
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        selected = self.isSelected()
        base_w = self._base_width

        # 选中=变色不加粗，悬停=微微提亮
        if selected:
            pen = QPen(QColor("#2aaaff"), base_w)        # 选中 → 亮蓝
        elif hovered:
            pen = QPen(self._edge_color.lighter(140), base_w)  # 悬停 → 提亮
        else:
            pen = self.pen()
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(self.path())

        pts = self._all_points()

        # 已有折叠点（可拖拽调整角度）
        for i in range(1, len(pts) - 1):
            wp = pts[i]
            if self._hovered_wp == i - 1 or self._drag_wp_index == i - 1:
                r = self.WAYPOINT_RADIUS + 2
                painter.setBrush(QBrush(QColor("#ff8800")))
            else:
                r = self.WAYPOINT_RADIUS
                painter.setBrush(QBrush(QColor("#e67e22")))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.drawEllipse(QPointF(wp), r, r)

        # 手柄圆点（仅在非拖拽态绘制，拖拽时由折叠点接管）
        if self._drag_wp_index is None:
            for i in range(len(pts) - 1):
                mid = (pts[i] + pts[i + 1]) / 2.0
                if self._hovered_handle == i:
                    r = self.HANDLE_RADIUS + 3
                    painter.setBrush(QBrush(QColor("#ffffff")))
                else:
                    r = self.HANDLE_RADIUS
                    painter.setBrush(QBrush(self._edge_color))
                painter.setPen(QPen(Qt.PenStyle.NoPen))
                painter.drawEllipse(QPointF(mid), r, r)

        # 箭头
        if self.arrow_item:
            if selected:
                self.arrow_item.setBrush(QColor("#007acc"))
            elif hovered:
                self.arrow_item.setBrush(self._edge_color.lighter(130))
            else:
                self.arrow_item.setBrush(self._edge_color)

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(self.SHAPE_HIT_WIDTH)
        return stroker.createStroke(self.path())

    # ═══════════════════════════════════════════
    #  命中检测
    # ═══════════════════════════════════════════

    def _nearest_handle(self, pos: QPointF):
        pts = self._all_points()
        best_seg, best_dist = -1, float('inf')
        for i in range(len(pts) - 1):
            mid = (pts[i] + pts[i + 1]) / 2.0
            dist = QLineF(QPointF(mid), pos).length()
            if dist < best_dist:
                best_dist, best_seg = dist, i
        return best_seg, best_dist

    def _hit_handle(self, pos: QPointF):
        seg, dist = self._nearest_handle(pos)
        if seg >= 0 and dist <= self.HANDLE_HIT_RADIUS:
            return seg
        return -1

    def _nearest_waypoint(self, pos: QPointF):
        """返回 (index, distance) — index 是 _waypoints 中的位置"""
        best_i, best_d = -1, float('inf')
        src, dst = self._endpoints()
        for i, wp in enumerate(self._waypoints):
            wp_abs = self._decode_rel(src, dst, wp) if isinstance(wp, tuple) else QPointF(wp)
            d = QLineF(wp_abs, pos).length()
            if d < best_d:
                best_d, best_i = d, i
        return best_i, best_d

    def _hit_waypoint(self, pos: QPointF):
        i, d = self._nearest_waypoint(pos)
        if i >= 0 and d <= self.WAYPOINT_HIT_RADIUS:
            return i
        return -1

    # ═══════════════════════════════════════════
    #  悬停高亮
    # ═══════════════════════════════════════════

    def hoverMoveEvent(self, event):
        pos = event.scenePos()
        seg, hd = self._nearest_handle(pos)
        wi, wd = self._nearest_waypoint(pos)

        if wi >= 0 and wd <= self.WAYPOINT_HIT_RADIUS:
            self._hovered_wp = wi
            self._hovered_handle = -1
        elif seg >= 0 and hd <= self.HANDLE_HIT_RADIUS:
            self._hovered_handle = seg
            self._hovered_wp = -1
        else:
            self._hovered_handle = -1
            self._hovered_wp = -1
        self.update()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered_handle = -1
        self._hovered_wp = -1
        self.update()
        super().hoverLeaveEvent(event)

    # ═══════════════════════════════════════════
    #  交互
    # ═══════════════════════════════════════════

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.scenePos()

            # 优先：检测已有折叠点（直接拖拽，无需长按）
            wp_idx = self._hit_waypoint(pos)
            if wp_idx >= 0:
                self._drag_wp_index = wp_idx
                self._drag_is_new = False
                self._hovered_handle = -1
                self._hovered_wp = -1
                self.setSelected(True)
                event.accept()
                return

            # 其次：检测手柄（长按触发新建折叠点）
            seg = self._hit_handle(pos)
            if seg >= 0:
                self._press_pos = pos
                self._press_on_handle = seg
                self._long_press_fired = False
                self._long_press_timer.start(self.LONG_PRESS_MS)
                event.accept()
                return

            # 其他：点击线身体 → 选中
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
        """长按触发：在手柄位置创建新折叠点（存为相对坐标）"""
        self._long_press_fired = True
        if self._press_on_handle < 0:
            return
        src, dst = self._endpoints()
        pts = self._all_points()
        seg = self._press_on_handle
        if seg >= len(pts) - 1:
            return
        mid = (pts[seg] + pts[seg + 1]) / 2.0
        rel = self._encode_rel(src, dst, mid)
        self._waypoints.insert(seg, rel)
        self._drag_wp_index = seg
        self._drag_is_new = True
        self._hovered_handle = -1
        self._hovered_wp = seg
        self._press_on_handle = -1
        self.update_path()

    def mouseMoveEvent(self, event):
        # 拖拽已有折叠点 或 新折叠点（编码为相对坐标）
        if self._drag_wp_index is not None:
            wp_idx = self._drag_wp_index
            if 0 <= wp_idx < len(self._waypoints):
                src, dst = self._endpoints()
                self._waypoints[wp_idx] = self._encode_rel(src, dst, event.scenePos())
                self.update_path()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._long_press_timer.stop()

        if self._drag_wp_index is not None:
            # 结束拖拽
            self._drag_wp_index = None
            self._drag_is_new = False
            self._press_on_handle = -1
            self._press_pos = None
            self._long_press_fired = False
            self.update_path()
            return

        if self._press_on_handle >= 0 and not self._long_press_fired:
            # 短按手柄 → 选中线条
            self.setSelected(True)

        self._press_on_handle = -1
        self._press_pos = None
        self._long_press_fired = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return
        pos = event.scenePos()
        idx = self._hit_waypoint(pos)
        if idx >= 0:
            del self._waypoints[idx]
            self._drag_wp_index = None
            self.update_path()
            return
        super().mouseDoubleClickEvent(event)

    # ═══════════════════════════════════════════
    #  右键
    # ═══════════════════════════════════════════

    def contextMenuEvent(self, event):
        event.ignore()

    # ═══════════════════════════════════════════
    #  API
    # ═══════════════════════════════════════════

    @property
    def waypoints(self):
        """返回解码后的绝对坐标列表"""
        src, dst = self._endpoints()
        return [self._decode_rel(src, dst, w) if isinstance(w, tuple) else QPointF(w) for w in self._waypoints]

    def set_waypoints(self, points):
        src, dst = self._endpoints()
        self._waypoints = [
            self._encode_rel(src, dst, QPointF(p) if not isinstance(p, QPointF) else p)
            for p in points
        ]
        self.update_path()

    def clear_waypoints(self):
        self._waypoints.clear()
        self.update_path()

    def add_waypoint(self, pos: QPointF):
        src, dst = self._endpoints()
        self._waypoints.append(self._encode_rel(src, dst, pos))
        self.update_path()

    def remove_waypoint_at(self, index: int):
        if 0 <= index < len(self._waypoints):
            del self._waypoints[index]
            self.update_path()

    def to_dict(self):
        """序列化为相对坐标格式"""
        if self._waypoints:
            if isinstance(self._waypoints[0], tuple):
                return {"waypoints": [list(w) for w in self._waypoints]}
            else:
                return {"waypoints": [(p.x(), p.y()) for p in self._waypoints]}
        return {}

    def from_dict(self, data: dict):
        """从字典恢复（兼容旧绝对坐标和新相对坐标）"""
        if data and "waypoints" in data:
            raw = data["waypoints"]
            if raw and isinstance(raw[0], list) and len(raw[0]) == 3:
                # 新格式：(t, ox, oy)
                self._waypoints = [(float(r[0]), float(r[1]), float(r[2])) for r in raw]
            else:
                # 旧格式：绝对坐标 → 下次 update_path 自动转换
                self._waypoints = [QPointF(x, y) for x, y in raw]
                self._sync_abs_to_rel()
        else:
            self._waypoints = []

    def remove_from_scene(self):
        self._long_press_timer.stop()
        scene = self.scene()
        if scene:
            scene.removeItem(self)
