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
from PySide6.QtWidgets import (
    QGraphicsPathItem, QGraphicsPolygonItem, QStyle, QGraphicsItem, QApplication,
)
from PySide6.QtCore import Qt, QPointF, QLineF, QTimer
from PySide6.QtGui import (
    QPen, QColor, QPainterPath, QPolygonF, QPainterPathStroker, QBrush,
    QPainter,
)
from ui.core.logger import logger


class EdgeArrowItem(QGraphicsPolygonItem):
    """带抗锯齿的箭头项—— 使用填充多边形渲染，任意缩放平滑"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 禁用缓存：确保任意缩放都重新计算矢量路径
        self.setCacheMode(QGraphicsPolygonItem.CacheMode.NoCache)
        # 不描边，只填充：抗锯齿效果最佳（与三角形填充一致）
        self.setPen(QPen(Qt.PenStyle.NoPen))
    
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        super().paint(painter, option, widget)


class TempEdgeItem(QGraphicsPathItem):
    """带抗锯齿的临时连线（拖拽时显示）—— 使用矢量轮廓填充渲染"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 禁用缓存：确保任意缩放都重新计算矢量路径，避免缓存拉伸产生锯齿
        self.setCacheMode(QGraphicsPathItem.CacheMode.NoCache)
    
    def paint(self, painter, option, widget=None):
        # 抗锯齿 + 平滑变换
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        
        # 使用 QPainterPathStroker 填充法（与箭头/正式连线同样的渲染方式）
        pen = self.pen()
        if pen.style() != Qt.PenStyle.NoPen and pen.widthF() > 0:
            color = pen.color()
            stroker = QPainterPathStroker(pen)
            filled_path = stroker.createStroke(self.path())
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            painter.setBrush(QBrush(color))
            painter.drawPath(filled_path)


class EdgeItem(QGraphicsPathItem):
    """直线连线 + 人工折叠手柄"""

    HOVER_WIDTH_DELTA = 4
    SHAPE_HIT_WIDTH = 8
    HANDLE_RADIUS = 6
    HANDLE_HIT_RADIUS = 15
    WAYPOINT_RADIUS = 6        # 已有折叠点渲染半径
    WAYPOINT_HIT_RADIUS = 14   # 已有折叠点拖拽判定半径
    LONG_PRESS_MS = 250

    def __init__(self, start_node, end_node, canvas=None, target_anchor=None, source_anchor=None,
                 target_port_name=None, source_port_name=None):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.canvas = canvas
        self._target_anchor = target_anchor  # 显式指定的目标锚点
        self._source_anchor = source_anchor  # 显式指定的源锚点
        self._desired_target_port_name = target_port_name  # 期望绑定的目标端口名（如"prompt"/"context"等）
        self._desired_source_port_name = source_port_name  # 期望绑定的源端口名
        
        # 获取设备像素比，确保高DPI屏幕上显示正常
        self._device_pixel_ratio = self._get_device_pixel_ratio()
        self._base_width = 2.5 * self._device_pixel_ratio
        self._edge_color = QColor("#4A90E2")

        self._waypoints: list = []

        # 拖拽状态
        self._drag_wp_index = None   # 正在拖拽的折叠点索引（None = 未拖拽）
        self._drag_is_new = False    # True=新折叠点（从手柄创建）, False=拖已有折叠点
        self._press_pos = None
        self._press_on_handle = -1   # 按下的手柄索引（-1 = 按在线身上）
        self._long_press_fired = False

        self._long_press_timer = QTimer(QApplication.instance())
        self._long_press_timer.setSingleShot(True)
        self._long_press_timer.timeout.connect(self._on_long_press)

        self._hovered_handle = -1
        self._hovered_wp = -1

        # NoCache：禁用缓存，确保任意缩放抗锯齿始终生效（箭头就是这样）
        self.setCacheMode(QGraphicsPathItem.CacheMode.NoCache)
        self.setZValue(20)  # 线条层：最顶层，不被节点/锚点遮挡
        self.update_edge_style()

        self.setFlag(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
        )
        self.arrow_item = None
        
        # 锚点引用（双向绑定核心）
        self.start_anchor = None
        self.end_anchor = None
        
        # 建立双向绑定
        self._setup_anchor_binding()
    
    def _get_device_pixel_ratio(self):
        """获取设备像素比，用于高DPI屏幕适配"""
        try:
            if self.canvas and hasattr(self.canvas, 'viewport'):
                return self.canvas.viewport().devicePixelRatio()
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                screen = app.primaryScreen()
                if screen:
                    return screen.devicePixelRatio()
        except Exception:
            pass
        return 1.0
    
    def _setup_anchor_binding(self):
        """建立与锚点的双向绑定（支持多输入/输出端口）

        关键规则：
        - 如果指定了特定端口名（如 prompt / context）但找不到对应锚点，不 fallback 到 default，
          保持 end_anchor = None，后续 _validate_edge_anchor_binding 会尝试修复或发出警告
        - 只有在未指定端口名时才允许使用 default 锚点
        """
        # 输出端绑定
        if self._source_anchor:
            self.start_anchor = self._source_anchor
        elif self._desired_source_port_name and hasattr(self.start_node, 'anchor_manager'):
            self.start_anchor = self.start_node.anchor_manager.get_output(self._desired_source_port_name)
        elif hasattr(self.start_node, 'output_anchor'):
            self.start_anchor = self.start_node.output_anchor

        # 输入端绑定
        if self._target_anchor:
            self.end_anchor = self._target_anchor
        elif self._desired_target_port_name and hasattr(self.end_node, 'anchor_manager'):
            self.end_anchor = self.end_node.anchor_manager.get_input(self._desired_target_port_name)
        elif hasattr(self.end_node, 'input_anchor'):
            # 只有在未指定特定端口名时才允许 fallback 到 default
            if not self._desired_target_port_name:
                self.end_anchor = self.end_node.input_anchor
            else:
                logger.warning(
                    "[EdgeItem] 指定端口 '%s' 但找不到对应锚点，不绑定到默认锚点: %s → %s",
                    self._desired_target_port_name,
                    getattr(self.start_node, 'node_name', '?'),
                    getattr(self.end_node, 'node_name', '?')
                )

        logger.debug(
            "[EdgeItem] _setup_anchor_binding: desired_target_port=%s, found_end_anchor=%s, "
            "end_anchor.port_name=%s, start_anchor.port_name=%s",
            self._desired_target_port_name,
            self.end_anchor is not None,
            getattr(self.end_anchor, 'port_name', None) if self.end_anchor else None,
            getattr(self.start_anchor, 'port_name', None) if self.start_anchor else None
        )

        # 双向绑定：将连线注册到锚点
        if self.start_anchor:
            self.start_anchor.add_edge(self)
        if self.end_anchor:
            self.end_anchor.add_edge(self)

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
        from PySide6.QtWidgets import QColorDialog
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
        """获取连线端点的场景坐标 - 使用 mapToScene 确保坐标正确跟随节点移动"""
        # 安全检查：确保锚点存在且已添加到场景；否则回退到节点上现存的锚点
        def _resolve_anchor(node, prefer_attr: str, fallback_attr: str):
            anchor = getattr(self, prefer_attr, None)
            if anchor is not None and anchor.scene() is not None:
                return anchor
            # 锚点已从场景移除（可能是样式切换/重启时重建了锚点）
            # → 从 node 的 anchor_manager 查找可用锚点
            if node is None:
                return None
            am = getattr(node, "anchor_manager", None)
            if am is not None:
                if prefer_attr == "end_anchor":
                    # 优先保留原 port_name（如果锚点上还有记录）
                    port_name = getattr(anchor, "port_name", None) if anchor is not None else None
                    cand = am.get_input(port_name) if port_name else am.get_default_input()
                    if cand is not None and cand.scene() is not None:
                        return cand
                else:
                    port_name = getattr(anchor, "port_name", None) if anchor is not None else None
                    cand = am.get_output(port_name) if port_name else am.get_default_output()
                    if cand is not None and cand.scene() is not None:
                        return cand
            # 向后兼容：旧节点可能只有 .input_anchor / .output_anchor 属性
            cand = getattr(node, fallback_attr, None)
            if cand is not None and getattr(cand, "scene", lambda: None)() is not None:
                return cand
            # 最后兜底：直接返回 cand（可能是 QGraphicsItem 但 scene 为空）
            return cand if cand is not None else None

        start_anchor = _resolve_anchor(self.start_node, "start_anchor", "output_anchor")
        end_anchor = _resolve_anchor(self.end_node, "end_anchor", "input_anchor")

        # 确保双向绑定的 self.start_anchor / self.end_anchor 引用也是最新的
        if start_anchor is not None and start_anchor is not self.start_anchor:
            self.start_anchor = start_anchor
            try:
                start_anchor.add_edge(self)
            except Exception:
                pass
        if end_anchor is not None and end_anchor is not self.end_anchor:
            self.end_anchor = end_anchor
            try:
                end_anchor.add_edge(self)
            except Exception:
                pass

        if start_anchor is None or end_anchor is None:
            # 最终回退：节点中心（极端兜底）
            s_rect = self.start_node.sceneBoundingRect() if self.start_node else None
            e_rect = self.end_node.sceneBoundingRect() if self.end_node else None
            return (
                s_rect.center() if s_rect else self.start_node.pos() if self.start_node else None,
                e_rect.center() if e_rect else self.end_node.pos() if self.end_node else None,
            )

        # 计算锚点在父节点中的中心点（相对于节点的坐标）
        start_anchor_center = start_anchor.boundingRect().center()
        end_anchor_center = end_anchor.boundingRect().center()

        # 使用 mapToScene 转换到场景坐标
        start = start_anchor.mapToScene(start_anchor_center)
        end = end_anchor.mapToScene(end_anchor_center)

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
        
        # 如果还没有转换为相对坐标，且锚点已就绪，立即转换
        if self._waypoints and not isinstance(self._waypoints[0], tuple):
            # 检查锚点是否已添加到场景
            if self.start_anchor and self.start_anchor.scene() and self.end_anchor and self.end_anchor.scene():
                self._sync_abs_to_rel()
        
        # 如果是相对坐标格式，使用相对坐标解码（跟随节点移动）
        if self._waypoints and isinstance(self._waypoints[0], tuple):
            pts = [src]
            for rel in self._waypoints:
                pts.append(self._decode_rel(src, dst, rel))
            pts.append(dst)
            return pts
        
        # 旧格式（绝对坐标）：保留原始绝对坐标
        # 注意：在锚点就绪后第一次节点移动时会转换为相对坐标
        if self._waypoints:
            return [src] + [QPointF(p) if not isinstance(p, QPointF) else p for p in self._waypoints] + [dst]
        
        # 没有折叠点的情况
        return [src, dst]

    def update_path(self):
        if not self.start_node or not self.end_node:
            return

        pts = self._all_points()
        path = QPainterPath()
        path.moveTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)

        self.prepareGeometryChange()
        self.setPath(path)

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
        self.arrow_item = EdgeArrowItem(self)
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

        # 动态计算当前缩放倍数下的合适线条宽度（确保放大后仍有清晰平滑的边缘）
        # 通过 painter.transform 的 m11 获取当前 x 方向缩放比例
        transform = painter.transform()
        current_scale = max(abs(transform.m11()), abs(transform.m22()), 1.0)
        # 基础宽度 + 根据缩放调整：1x 显示 3px，放大后保持矢量平滑
        base_w = max(3.0, self._base_width)

        # 抗锯齿 + 平滑变换
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 选中=变色不加粗，悬停=微微提亮
        if selected:
            color = QColor("#2aaaff")
        elif hovered:
            color = self._edge_color.lighter(140)
        else:
            color = self.pen().color()

        # 用 QPainterPathStroker 将线条转为矢量轮廓填充（与箭头同样的填充渲染）
        # 这样在任意缩放倍数下，线条边缘都像多边形填充一样平滑，无锯齿
        stroker_pen = QPen(color, base_w)
        stroker_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        stroker = QPainterPathStroker(stroker_pen)
        filled_path = stroker.createStroke(self.path())
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(color))
        painter.drawPath(filled_path)

        pts = self._all_points()

        # 已有折叠点（可拖拽调整角度）— 使用填充椭圆，与箭头同样平滑
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

    def boundingRect(self):
        """覆盖手柄+折叠点范围，确保任何方向拖拽都能触发旧区域重绘"""
        r = max(self.HANDLE_RADIUS + 3, self.WAYPOINT_RADIUS + 2) + 4
        return self.path().boundingRect().adjusted(-r, -r, r, r)

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

    def from_dict(self, data: dict, defer_sync=False):
        """从字典恢复（兼容旧绝对坐标和新相对坐标）
        
        Args:
            data: 连线数据字典
            defer_sync: 是否延迟同步相对坐标（用于布局加载时避免锚点坐标未就绪）
        """
        if data and "waypoints" in data:
            raw = data["waypoints"]
            if raw and isinstance(raw[0], list) and len(raw[0]) == 3:
                # 新格式：(t, ox, oy)
                self._waypoints = [(float(r[0]), float(r[1]), float(r[2])) for r in raw]
            else:
                # 旧格式：绝对坐标 → 延迟转换，等待锚点坐标就绪
                self._waypoints = [QPointF(x, y) for x, y in raw]
                if not defer_sync:
                    self._sync_abs_to_rel()
                else:
                    # 标记需要延迟同步
                    self._needs_sync = True
        else:
            self._waypoints = []

    def remove_from_scene(self):
        """从场景移除连线，并解除与锚点的双向绑定"""
        # 停止定时器
        self._long_press_timer.stop()
        
        # 解除与锚点的双向绑定（关键：防止内存泄漏和引用残留）
        if self.start_anchor:
            self.start_anchor.remove_edge(self)
        if self.end_anchor:
            self.end_anchor.remove_edge(self)
        
        # 移除箭头
        if self.arrow_item:
            scene = self.arrow_item.scene()
            if scene:
                scene.removeItem(self.arrow_item)
            self.arrow_item = None
        
        # 从场景移除
        scene = self.scene()
        if scene:
            scene.removeItem(self)
        
        # 断开所有引用
        self.start_node = None
        self.end_node = None
        self.start_anchor = None
        self.end_anchor = None
        self.canvas = None