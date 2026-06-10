"""
节点项（对应VueFlow节点）
继承自 QGraphicsRectItem，负责节点的视觉渲染、锚点管理和交互处理
"""
import os
from PyQt6.QtWidgets import (QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem,
    QGraphicsItem, QGraphicsProxyWidget)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPen, QColor, QBrush, QFont, QPainterPath
from datetime import datetime
from ui.core.logger import logger

from ui.canvas.items.anchor_item import AnchorItem, ANCHOR_SIZE, ANCHOR_HALF
from ui.canvas.items.anchor_manager import AnchorManager
from ui.canvas.items.node_style import DarkRectNodeStyle
from ui.canvas.items.node_status_widget import NodeStatusWidget


class NodeItem(QGraphicsRectItem):
    """节点项（对应VueFlow节点）"""

    on_expand_requested = None
    
    def __init__(self, node_name, language="Python", status="stopped", x=0, y=0, w=140, h=80, canvas=None, style=None):
        super().__init__(x, y, w, h, None)
        self.node_name = node_name
        self.language = language
        self.status = status
        self.canvas = canvas
        
        # 节点样式（默认深色）
        self._style = style or DarkRectNodeStyle()
        self._style.node_width = w
        self._style.node_height = h
        # 保存节点原始尺寸，以便切换样式后能还原到正常大小
        self._rect_default_width = w
        self._rect_default_height = h
        
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        
        self.setZValue(2)  # 节点层：锚点(z=10) < 节点(z=2) < 线条(z=20)
        self.setRect(QRectF(0, 0, w, h))
        
        # ── 锚点对接系统（AnchorManager 负责所有锚点生命周期/布局/点击检测） ──
        # 统一容器：anchor_manager.input_anchors / .output_anchors
        # 向后兼容：@property input_anchor / output_anchor 暴露默认锚点
        self.anchor_manager = AnchorManager(self)

        # 参数面板每行锚点位置缓存 — {port_name: (center_y_in_node_coord, row_height)}
        self._param_row_positions: dict[str, tuple[float, float]] = {}

        # IN / OUT 标签（文字层）
        self._in_label = QGraphicsTextItem("IN", self)
        self._in_label.setZValue(4)
        self._out_label = QGraphicsTextItem("OUT", self)
        self._out_label.setZValue(4)

        # 名称（文字层）
        self.name_text = QGraphicsTextItem(node_name, self)
        self.name_text.setZValue(4)

        # 状态灯（指示灯层）
        self.status_indicator = QGraphicsEllipseItem(8, 8, 10, 10, self)
        self.status_indicator.setZValue(3)

        # 语言标签（文字层）
        self.lang_text = QGraphicsTextItem(language, self)
        self.lang_text.setZValue(4)

        # 展开按钮（文字层）
        self._expand_btn = QGraphicsRectItem(0, 0, 14, 14, self)
        self._expand_btn.setZValue(4)
        self._expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._expand_btn_rect = QRectF(0, 0, 14, 14)

        self._expand_label = QGraphicsTextItem(">>", self)
        self._expand_label.setZValue(5)

        # 如果是圆点样式，不支持展开按钮
        if self._style.is_dot:
            self._expand_btn.setAcceptHoverEvents(False)
            self._expand_btn.setCursor(Qt.CursorShape.ArrowCursor)
            self._expand_label.setVisible(False)

        # 详细版参数控件（空初始化，由 DetailedNodeStyle.apply() 触发构建）
        self._proxy_widgets: list = []
        self._param_widgets: dict = {}

        # 选中环（最顶）
        self._selection_ring = QGraphicsEllipseItem(self)
        self._selection_ring.setZValue(10)
        self._selection_ring.setVisible(False)

        # 应用样式
        self._style.apply(self)
        self._style.apply_status(self, status)

        # 加载自定义颜色
        self._load_node_custom_colors()

        # 初始化状态显示组件
        self._status_widget = None
        self._start_time = None
        if self._style.status_show and not self._style.is_dot:
            self._status_widget = NodeStatusWidget(self)
            self._status_widget.set_visible(True)

            # 连接资源监测面板的信号（如果已创建）
            self._connect_resource_monitor_signals()

            # 如果节点正在运行，记录开始时间
            if self.status in ["running", "idle"]:
                self._try_initialize_start_time()

    # ========== 兼容层（让旧代码无需修改） ==========

    @property
    def input_anchor(self) -> AnchorItem:
        """返回默认输入锚点。多锚点场景下返回第一个端口的锚点。"""
        return self.anchor_manager.get_default_input()

    @property
    def output_anchor(self) -> AnchorItem:
        """返回默认输出锚点。"""
        return self.anchor_manager.get_default_output()

    # ========== 对外暴露的锚点 API（样式/连线系统调用） ==========

    def build_anchors_from_config(self, config: dict | None):
        """按 config.json 的 input_ports / output_ports 重建锚点布局。

        由 DetailedNodeStyle.apply() 调用。其他样式走 layout_for_rect()/layout_for_dot()。

        规则：
        - 输入端口（source=node）：锚点和对应参数行并排（左侧对齐）
        - 输出端口：永远只有一个 default 锚点（右侧水平居中）
        - 未声明 input_ports：保持旧的 default 单锚点兼容
        """
        # 确保 _param_row_positions 已填充（_build_detailed_view 先于本函数被调用）
        self.anchor_manager.build_from_config(config, row_positions=self._param_row_positions,
                                               node_w=self.rect().width(), node_h=self.rect().height())

    def find_nearest_input_anchor(self, local_pos: QPointF, max_dist: int = 20) -> AnchorItem | None:
        """点击检测：在节点局部坐标下查找离点击点最近的输入锚点。"""
        return self.anchor_manager.find_nearest_input(local_pos, max_dist)

    def find_nearest_output_anchor(self, local_pos: QPointF, max_dist: int = 20) -> AnchorItem | None:
        """点击检测：在节点局部坐标下查找离点击点最近的输出锚点（支持多输出端口）。"""
        return self.anchor_manager.find_nearest_output(local_pos, max_dist)

    def all_input_anchors(self) -> list:
        return self.anchor_manager.all_input()

    def all_output_anchors(self) -> list:
        return self.anchor_manager.all_output()

    def _update_selection_ring(self, selected):
        """更新选中环 — 仅圆点节点使用，方框节点走 paint()"""
        is_dot = hasattr(self, '_body') and self._body and self._body.isVisible()
        if not is_dot:
            self._selection_ring.setVisible(False)
            return
        
        if not selected or not self._body:
            self._selection_ring.setVisible(False)
            return
        
        r = self._body.rect().adjusted(-3, -3, 3, 3)
        self._selection_ring.setRect(r)
        self._selection_ring.setVisible(True)
        self._selection_ring.setPen(QPen(QColor(self._style.selected_color), 
                                         self._style.selected_border_width,
                                         Qt.PenStyle.DashLine))
        self._selection_ring.setBrush(QBrush())

    def _connect_resource_monitor_signals(self):
        """连接资源监测面板的信号"""
        if not self.canvas or not self.canvas.parent_window:
            return
        
        # 尝试连接浮动资源监测面板的信号
        if hasattr(self.canvas.parent_window, 'resource_monitor_floating') and self.canvas.parent_window.resource_monitor_floating:
            self.canvas.parent_window.resource_monitor_floating.node_state_updated.connect(self._on_status_updated)
        
        # 尝试连接Dock资源监测面板的信号
        if hasattr(self.canvas.parent_window, 'resource_monitor') and self.canvas.parent_window.resource_monitor:
            # 检查Dock版是否有这个信号
            if hasattr(self.canvas.parent_window.resource_monitor, 'node_state_updated'):
                self.canvas.parent_window.resource_monitor.node_state_updated.connect(self._on_status_updated)
    
    def _on_status_updated(self, node_name, cpu_percent, mem_mb):
        """状态更新回调（从资源监测面板接收）"""
        if node_name == self.node_name and self._status_widget:
            # 计算运行时长（如果还没记录开始时间，现在记录）
            duration_seconds = 0
            if self._start_time:
                duration_seconds = (datetime.now() - self._start_time).total_seconds()
            else:
                # 如果没有开始时间，尝试从进程信息获取
                self._try_initialize_start_time()
                if self._start_time:
                    duration_seconds = (datetime.now() - self._start_time).total_seconds()
            
            self._status_widget.update_status(cpu_percent, mem_mb, duration_seconds)
    
    def _try_initialize_start_time(self):
        """尝试从节点数据中初始化开始时间"""
        if not self.canvas or not self.canvas.parent_window:
            return
            
        if self.node_name in self.canvas.parent_window.nodes_data:
            node_info = self.canvas.parent_window.nodes_data[self.node_name]
            # 如果节点正在运行，记录开始时间
            if node_info.get('status') in ['running', 'idle']:
                self._start_time = datetime.now()
            
    def update_status(self, status):
        """更新节点状态"""
        self.status = status
        self._style.apply_status(self, status)
        
        # 如果状态变为运行中，记录开始时间并确保信号连接
        if status in ["running", "idle"]:
            if self._status_widget:
                if self._start_time is None:
                    self._start_time = datetime.now()
                self._connect_resource_monitor_signals()
            else:
                # 如果还没有状态组件，创建一个
                self._status_widget = NodeStatusWidget(self)
                self._status_widget.set_visible(True)
                self._start_time = datetime.now()
                self._connect_resource_monitor_signals()
        else:
            # 节点停止了，清除开始时间
            self._start_time = None
                    
    def set_style(self, style):
        """设置节点样式。

        关键：
          1. 切换前先销毁详细版控件
          2. 根据样式类型 EXPLICITLY 设置 node_width/node_height
             （不依赖类默认值，不依赖当前 rect 尺寸）
          3. 详细版由内容驱动尺寸，方形用原始尺寸，圆形用 DotNodeStyle 默认
        """
        # 1) 清理：销毁所有 Proxy 控件、恢复缓存模式
        if hasattr(self, '_proxy_widgets') and self._proxy_widgets:
            self._destroy_detailed()

        self._style = style

        # 2) 根据样式类型设置正确的尺寸（避免类默认值与实际不匹配）
        from ui.canvas.items.node_style import (
            RectNodeStyle, DotNodeStyle, DetailedNodeStyle
        )
        if isinstance(self._style, DotNodeStyle):
            self._style.node_width = self._style.__class__.node_width  # 80
            self._style.node_height = self._style.__class__.node_height  # 80
        elif isinstance(self._style, DetailedNodeStyle):
            # 详细版不硬编码，等 _build_detailed_view() 中 set_sizes() 计算
            pass
        elif isinstance(self._style, RectNodeStyle):
            # 方形节点用原始尺寸（节点创建时传入的 w/h）
            self._style.node_width = self._rect_default_width
            self._style.node_height = self._rect_default_height

        # 3) 应用新样式
        self._style.apply(self)
        self._style.apply_status(self, self.status)

        # 4) 同步显示状态控件 + 重新布局（新尺寸）
        if self._style.status_show and not self._style.is_dot:
            if not self._status_widget:
                self._status_widget = NodeStatusWidget(self)
            self._status_widget.set_visible(True)
            self._status_widget.update_layout()
            self._start_time = None
            self._connect_resource_monitor_signals()
        else:
             if self._status_widget:
                 self._status_widget.set_visible(False)
                 self._status_widget = None

        self._update_selection_ring(self.isSelected())
        # 强制刷新
        if self.scene():
            self.scene().update()
      
    def _load_node_custom_colors(self):
        """加载节点的自定义颜色配置"""
        if not self.canvas or not self.canvas.parent_window:
            return
        
        node_name = self.node_name
        if node_name not in self.canvas.parent_window.nodes_data:
            return
        
        node_info = self.canvas.parent_window.nodes_data[node_name]
        config = node_info.get('config', {})
        
        # 应用自定义背景色
        if 'custom_bg_color' in config:
            try:
                custom_color = QColor(config['custom_bg_color'])
                if custom_color.isValid():
                    self.setBrush(QBrush(custom_color))
            except:
                pass
        
        # 应用自定义边框色
        if 'custom_border_color' in config:
            try:
                custom_color = QColor(config['custom_border_color'])
                if custom_color.isValid():
                    self.setPen(QPen(custom_color, 2))
            except:
                pass
        
        # 应用自定义文字色
        if 'custom_text_color' in config:
            try:
                custom_color = QColor(config['custom_text_color'])
                if custom_color.isValid():
                    self.name_text.setDefaultTextColor(custom_color)
            except:
                pass
        
    def update_display(self, node_name=None, language=None, status=None):
        """更新节点显示信息（与数据同步）"""
        w = self.rect().width()
        h = self.rect().height()
        
        # 更新节点名称（只更新内容）
        if node_name:
            self.node_name = node_name
            self.name_text.setPlainText(node_name)
        
        # 更新语言（只更新内容）
        if language:
            self.language = language
            self.lang_text.setPlainText(language)
        
        # 如果有内容更新，重新应用样式以更新文字位置
        if node_name or language:
            self._style.apply(self)
        
        # 更新状态
        if status:
            self.update_status(status)
            
    def sync_with_data(self, node_data):
        """从节点数据字典同步所有信息"""
        if 'name' in node_data:
            self.update_display(node_name=node_data['name'])
        if 'language' in node_data:
            self.update_display(language=node_data['language'])
        if 'status' in node_data:
            self.update_display(status=node_data['status'])
            
    def itemChange(self, change, value):
        """监听节点变化：选中环显隐、防重叠、保存布局、更新连线"""
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self._update_selection_ring(value)
        
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            value = self._avoid_overlap(value)
        
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.canvas:
                # 1. 遍历所有锚点（包括多端口场景），更新所有连线
                all_edges = set()

                for anchor in self.all_output_anchors():
                    for edge in list(anchor.edges):
                        if edge and edge.end_node:
                            all_edges.add(edge)

                for anchor in self.all_input_anchors():
                    for edge in list(anchor.edges):
                        if edge and edge.start_node:
                            all_edges.add(edge)
                
                # 更新所有相关连线
                for edge in all_edges:
                    # 如果还在使用绝对坐标，立即转换为相对坐标
                    if edge._waypoints and not isinstance(edge._waypoints[0], tuple):
                        edge._sync_abs_to_rel()
                    edge.update_path()
                
                # 2. 自动保存布局（防抖500ms）
                if hasattr(self.canvas, '_save_timer'):
                    self.canvas._save_timer.stop()
                    self.canvas._save_timer.start(500)
        
        return super().itemChange(change, value)
    
    def _avoid_overlap(self, new_pos):
        """检测并避免节点重叠"""
        if not self.canvas:
            return new_pos
        
        rect = self.boundingRect()
        r1 = rect.translated(new_pos)
        
        for other in self.canvas.nodes.values():
            if other is self:
                continue
            r2 = other.boundingRect().translated(other.pos())
            if r1.intersects(r2):
                # 计算推开方向（从other中心指向self中心）
                cx1, cy1 = r1.center().x(), r1.center().y()
                cx2, cy2 = r2.center().x(), r2.center().y()
                dx = cx1 - cx2
                dy = cy1 - cy2
                # 如果中心重合，随机推开
                if dx == 0 and dy == 0:
                    dx, dy = 1, 0
                dist = (dx * dx + dy * dy) ** 0.5
                # 推开到不重叠的最小距离
                overlap_x = (r1.width() + r2.width()) / 2 - abs(dx)
                overlap_y = (r1.height() + r2.height()) / 2 - abs(dy)
                if overlap_x > 0 and overlap_y > 0:
                    nx = dx / dist
                    ny = dy / dist
                    # 优先横向推开
                    if overlap_x < overlap_y:
                        new_pos.setX(new_pos.x() + nx * overlap_x)
                    else:
                        new_pos.setY(new_pos.y() + ny * overlap_y)
        
        return new_pos
        
    def shape(self):
        """返回精确的形状区域用于命中检测

        圆点节点：仅圆点本体可选中，名称文字不计入可选范围
        方框节点：使用默认矩形
        """
        is_dot = hasattr(self, '_body') and self._body and self._body.isVisible()
        if is_dot and self._body:
            path = QPainterPath()
            path.addEllipse(self._body.rect())
            return path
        return super().shape()

    def paint(self, painter, option, widget=None):
        """绘制节点 — ComfyUI 风格：圆角矩形 + 彩色标题栏。

        样式判断：
          - DetailedNodeStyle（面板模式，is_detailed=True）：圆角 + 标题栏
          - 其他（方框/圆点）：沿用老逻辑（super().paint 绘制矩形）
          - 选中时：绘制高亮边框
        """
        # —— 圆点样式：不绘制本体（由 _body 负责） ——
        is_dot = hasattr(self, '_body') and self._body and self._body.isVisible()
        if is_dot:
            return

        # —— 判断是否是 DetailedNodeStyle（面板模式） ——
        from ui.canvas.items.node_style import DetailedNodeStyle
        is_detailed = isinstance(self._style, DetailedNodeStyle)

        rect = self.rect()
        w = rect.width()
        h = rect.height()

        if is_detailed:
            # === ComfyUI 风格：圆角矩形 + 彩色标题栏 ===
            from PyQt6.QtGui import QPainterPath, QPainter
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            corner_radius = DetailedNodeStyle.CORNER_RADIUS
            header_h = DetailedNodeStyle.HEADER_HEIGHT
            body_bg = DetailedNodeStyle.body_bg
            body_border = DetailedNodeStyle.body_border
            header_color = DetailedNodeStyle.header_color_for(self.language)
            node_rect = QRectF(0, 0, w, h)

            # —— 1. 主体圆角矩形背景 ——
            body_path = QPainterPath()
            body_path.addRoundedRect(node_rect, corner_radius, corner_radius)
            painter.setBrush(QBrush(QColor(body_bg)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(body_path)

            # —— 2. 顶部标题栏（圆角裁剪后的顶部矩形） ——
            header_rect = QRectF(0, 0, w, header_h)
            painter.save()
            painter.setClipPath(body_path)
            painter.setBrush(QBrush(QColor(header_color)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(header_rect)
            painter.restore()

            # —— 3. 边框（圆角矩形描边） ——
            border_pen = QPen(QColor(body_border), 2)
            if self.isSelected():
                border_pen = QPen(QColor("#f0f0f0"), 2)
            painter.setPen(border_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(node_rect, corner_radius, corner_radius)

            # —— 4. 选中高亮环 ——
            if self.isSelected():
                highlight_pen = QPen(QColor("#66b0ff"), 3)
                painter.setPen(highlight_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                highlight_rect = QRectF(-2, -2, w + 4, h + 4)
                painter.drawRoundedRect(highlight_rect, corner_radius + 2, corner_radius + 2)
        else:
            # === 方框模式：沿用老逻辑 ===
            # 先画主体
            painter.setBrush(QBrush(QColor(self._style.bg_color)))
            painter.setPen(QPen(QColor(self._style.border_color), 2))
            painter.drawRect(rect)

            # 选中高亮
            if self.isSelected():
                pen = QPen(QColor(self._style.selected_color), self._style.selected_border_width)
                pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(rect)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos_in_item = self.mapFromScene(event.scenePos())
            is_dot = hasattr(self, '_body') and self._body and self._body.isVisible()
            w = self.rect().width()
            h = self.rect().height()

            # 调试：连线模式下的点击信息
            if self.canvas and self.canvas.is_connecting:
                logger.debug("NodeItem[%s].mousePress: pos=(%.1f,%.1f) rect=(%.0f,%.0f) is_dot=%s eventAccepted=%s",
                             self.node_name, pos_in_item.x(), pos_in_item.y(), w, h, is_dot, event.isAccepted())

            # 圆点节点：点击圆点本体 = 输入锚点（连线完成）/ 选中
            if is_dot:
                body_rect = self._body.rect()
                body_scene_rect = body_rect.translated(self._body.pos())
                if body_scene_rect.contains(pos_in_item):
                    if self.canvas and self.canvas.is_connecting:
                        self.canvas.complete_connection_to_input(self)
                        event.accept()
                        return
                    if self.canvas:
                        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                            self.canvas._toggle_node_selection(self.node_name)
                        else:
                            self.canvas.on_node_selected(self)
                    return

            # 方块节点：展开按钮
            if not is_dot and self._expand_btn_rect.contains(pos_in_item):
                if self.on_expand_requested:
                    self.on_expand_requested(self.node_name)
                event.accept()
                return

            w = self.rect().width()
            h = self.rect().height()

            # 方块节点：输出锚点（开始连线）
            if not is_dot:
                clicked_output = self.find_nearest_output_anchor(pos_in_item, max_dist=20)
                if clicked_output is None:
                    # 兜底：节点右侧单个 default 锚点范围内
                    default_output_rect = QRectF(w - ANCHOR_HALF, h / 2 - ANCHOR_HALF, ANCHOR_SIZE, ANCHOR_SIZE)
                    if default_output_rect.contains(pos_in_item):
                        clicked_output = self.anchor_manager.get_output("default")
                if clicked_output:
                    port_label = (
                        clicked_output.port_name
                        if getattr(clicked_output, "port_name", None)
                        else "default"
                    )
                    logger.debug(
                        "NodeItem[%s]: 输出锚点命中 %s",
                        self.node_name, port_label,
                    )
                    if self.canvas:
                        # 传入具体输出锚点，连线系统会绑定到正确端口
                        self.canvas.start_connection_from_output(self, clicked_output)
                    event.accept()
                    return

                # 方块节点：输入锚点（完成连线）- 统一使用 find_nearest_input_anchor
                clicked_anchor = self.find_nearest_input_anchor(pos_in_item, max_dist=20)

                # 兜底：节点左侧无锚点命中但处于"单端口默认锚点"范围时，仍然用 default
                if clicked_anchor is None:
                    if len(self.anchor_manager.input_anchors) == 1 and "default" in self.anchor_manager.input_anchors:
                        default_rect = QRectF(-ANCHOR_HALF, h / 2 - ANCHOR_HALF, ANCHOR_SIZE, ANCHOR_SIZE)
                        if default_rect.contains(pos_in_item):
                            clicked_anchor = self.anchor_manager.input_anchors["default"]

                if clicked_anchor:
                    port_label = (
                        clicked_anchor.port_name
                        if getattr(clicked_anchor, "port_name", None)
                        else "default"
                    )
                    logger.debug(
                        "NodeItem[%s]: 输入锚点命中 %s, is_connecting=%s",
                        self.node_name, port_label,
                        self.canvas.is_connecting if self.canvas else None,
                    )
                    if self.canvas and self.canvas.is_connecting:
                        self.canvas.complete_connection_to_input(self, clicked_anchor)
                    event.accept()
                    return

            # Ctrl+单击
            if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and self.canvas:
                self.canvas._toggle_node_selection(self.node_name)
                event.accept()
                return

            # 普通单击
            if self.canvas:
                self.canvas.on_node_selected(self)
        
        super().mousePressEvent(event)
    
    # ========================================================================
    #  详细版参数控件（ProxyWidget 系统）
    # ========================================================================
    
    def _build_detailed_view(self):
        """ComfyUI 风格面板模式构建：

        布局结构（节点坐标系）：
          [0, HEADER_HEIGHT]：标题栏（paint 绘制背景，name_text 显示节点名）
          [0, HEADER_HEIGHT + content_h]：主体（多行 ParameterWidget）
          每行由 ParameterWidget 管理 [标签 + 控件]，锚点由 AnchorManager 放在节点左右边界上

        关键点：
          - ParameterWidget 内部已包含标签（_make_label），**不要额外添加 QLabel**
          - 容器左边距 = ANCHOR_ZONE_WIDTH + LEFT_INNER_PADDING，为锚点留出空间
          - _param_row_positions 记录锚点的 y 坐标（节点坐标系）
        """
        self._destroy_detailed()
        self._param_row_positions.clear()

        config = self._get_node_config()
        if not config:
            return

        from ui.core.node_config_parser import NodeConfigParser, ParameterDef
        from ui.canvas.items.node_style import DetailedNodeStyle
        style = DetailedNodeStyle

        # --- 解析：输入端口（需锚点） + 参数 ---
        input_port_defs = NodeConfigParser.parse_input_ports(config) if config else []
        input_port_defs = [p for p in input_port_defs if getattr(p, "source", "") == "node"]
        param_defs = NodeConfigParser.parse(config) if config else []

        if not input_port_defs and not param_defs:
            return

        # --- 构建容器 ---
        from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                      QGraphicsProxyWidget, QSizePolicy)
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont, QColor
        from ui.canvas.parameter_widgets import ParameterWidget

        container = QWidget()
        container.setStyleSheet("background: transparent;")

        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(
            style.ANCHOR_ZONE_WIDTH + style.LEFT_INNER_PADDING,
            6,
            style.RIGHT_INNER_PADDING,
            6,
        )
        v_layout.setSpacing(style.ROW_SPACING)

        # 行类型标记："input_port" | "param" | "output" — 用于后续计算锚点 y
        row_types = []

        # --- 1) 输入端口行（有锚点，左侧） ---
        # ParameterWidget 内部已有 [标签 + 控件]，直接放入 v_layout
        # 注意：不强制 setMinimumHeight，让 ParameterWidget 自己决定高度
        for port in input_port_defs:
            p_name = port.name
            label_text = getattr(port, "label", "") or port.name
            p_default = config.get(p_name, "") if p_name in config else ""

            param_obj = ParameterDef(name=p_name, type="string", label=label_text, default=p_default)
            w = ParameterWidget.create(param_obj, p_default)
            if hasattr(w, "value_changed"):
                w.value_changed.connect(self._on_param_changed)
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            v_layout.addWidget(w)

            self._param_widgets[p_name] = w
            row_types.append("input_port")

        # --- 2) 参数行（无锚点，纯参数） ---
        for p in param_defs:
            current = config.get(p.name, p.default)
            w = ParameterWidget.create(p, current)
            if hasattr(w, "value_changed"):
                w.value_changed.connect(self._on_param_changed)
            w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            v_layout.addWidget(w)

            self._param_widgets[p.name] = w
            row_types.append("param")

        # --- 3) 输出行（右侧显示 "output" 标签，锚点在右边界） ---
        output_wrap = QWidget()
        output_wrap.setStyleSheet("background: transparent;")
        output_wrap.setMinimumHeight(style.ROW_HEIGHT)
        output_h_layout = QHBoxLayout(output_wrap)
        output_h_layout.setContentsMargins(0, 0, 0, 0)
        output_h_layout.addStretch(1)
        output_label = QLabel("output")
        out_font = QFont()
        out_font.setPointSize(9)
        output_label.setFont(out_font)
        output_label.setStyleSheet("color: #88ccff;")
        output_h_layout.addWidget(output_label)
        v_layout.addWidget(output_wrap)

        row_types.append("output")

        # --- 给容器一个合理的最小宽度，避免节点太窄 ---
        # 锚点区(16) + 左边距(12) + 标签(约 80) + 控件(约 200) + 右边距(12) = 约 320px
        min_container_w = 340
        container.setMinimumWidth(min_container_w)

        # --- 关键：让 Qt 布局计算实际尺寸，确保节点比内部窗口大 ---
        # 先让布局计算各子控件的最小尺寸
        container.layout().activate()
        # 用 sizeHint 获取内容的理想尺寸（比 adjustSize 更可靠）
        sh = container.sizeHint()
        content_w = sh.width() if sh.isValid() else min_container_w
        content_h = sh.height() if sh.isValid() else (len(row_types) * 36 + 20)

        # 设置节点尺寸（确保比内容大，不会截断内部控件）
        self._style.set_sizes(content_w, content_h)
        final_w = max(self._style.node_width, content_w)
        final_h = self._style.node_height
        self.setRect(0, 0, final_w, final_h)

        # 让容器宽度等于节点宽度（去掉 left/right margins 已经包含在内）
        # 实际上 container 宽度 = content_w（已包含 margins），节点宽度 = content_w
        # 所以容器宽度应该 = 节点宽度，这样内部控件会填满节点宽度
        container.setFixedWidth(final_w)

        # --- 把 proxy widget 放到节点坐标系中（标题栏下方） ---
        proxy = QGraphicsProxyWidget(self)
        proxy.setWidget(container)
        proxy.setPos(0, style.HEADER_HEIGHT)
        proxy.setZValue(5)
        proxy.setFlag(proxy.GraphicsItemFlag.ItemClipsChildrenToShape, False)
        proxy.setFlag(proxy.GraphicsItemFlag.ItemClipsToShape, False)
        proxy.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._proxy_widgets.append(proxy)

        # --- 精确计算锚点位置（基于容器的实际布局几何） ---
        # 关键：即使 Qt 布局还没计算好几何，也必须写入 _param_row_positions。
        # 否则 build_from_config 不会创建这些 port 的锚点，导致 edge 被回退绑定到 default 锚点。
        from ui.canvas.items.anchor_item import ANCHOR_SIZE, ANCHOR_SIZE_SMALL
        small_center_x = style.ANCHOR_ZONE_WIDTH + style.LEFT_INNER_PADDING - ANCHOR_SIZE_SMALL / 2 - 2  # = 21
        margins_top = v_layout.contentsMargins().top() if v_layout.contentsMargins() else 0

        # 预先计算每行估算 y（兜底：layout 几何未就绪时使用）
        # 关键：不依赖 itemAt(j) 的几何（此时 Qt 布局可能完全未算），
        # 一律用 style.ROW_HEIGHT + style.ROW_SPACING。
        running_y = 0
        est_ys = []
        for _j in range(len(row_types)):
            est_ys.append(running_y + style.ROW_HEIGHT / 2)
            running_y += style.ROW_HEIGHT + style.ROW_SPACING

        # 记录已分配的 input_port 索引，确保每个 input_port 都有位置
        input_port_count = sum(1 for r in row_types if r == "input_port")
        for i, rtype in enumerate(row_types):
            item = v_layout.itemAt(i) if v_layout else None
            geom = item.geometry() if item and item.widget() else None

            # 优先使用实际几何；几何无效时使用估算值（关键：不会跳过写入）
            if geom is None or geom.width() <= 0 or geom.height() <= 0:
                center_y = style.HEADER_HEIGHT + margins_top + est_ys[i] if i < len(est_ys) else (
                    style.HEADER_HEIGHT + margins_top + i * (style.ROW_HEIGHT + style.ROW_SPACING) + style.ROW_HEIGHT / 2
                )
            else:
                row_top = style.HEADER_HEIGHT + geom.y()
                center_y = row_top + geom.height() / 2.0

            if rtype == "input_port":
                port_idx = row_types[:i].count("input_port")
                if port_idx < len(input_port_defs):
                    port = input_port_defs[port_idx]
                    self._param_row_positions[port.name] = (
                        small_center_x, center_y, ANCHOR_SIZE_SMALL,
                    )
            elif rtype == "output":
                # (center_x, center_y, size) — 大锚点在节点右边界
                out_cx = final_w - ANCHOR_SIZE / 2
                self._param_row_positions["__output__"] = (out_cx, center_y, ANCHOR_SIZE)

        # --- 标题栏：节点名居中 ---
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        self.name_text.setFont(title_font)
        self.name_text.setDefaultTextColor(QColor(style.header_text_color))
        self.name_text.setZValue(6)
        self.name_text.setPlainText(self.node_name)
        text_rect = self.name_text.boundingRect()
        title_x = max(8.0, (final_w - text_rect.width()) / 2)
        title_y = (style.HEADER_HEIGHT - text_rect.height()) / 2 - 2
        self.name_text.setPos(title_x, title_y)
        self.name_text.setVisible(True)

        # 确保其他标签不可见
        if hasattr(self, "lang_text") and self.lang_text:
            self.lang_text.setVisible(False)

        self._subscribe_config_changes()

    def _destroy_detailed(self):
        """销毁详细版控件（样式切换时调用），恢复缓存模式"""
        for p in self._proxy_widgets:
            p.setWidget(None)
            if self.scene():
                self.scene().removeItem(p)
        self._proxy_widgets.clear()
        self._param_widgets.clear()
        # 恢复节点的 DeviceCoordinateCache（默认渲染性能优化）
        self.setCacheMode(self.CacheMode.DeviceCoordinateCache)

    def _get_label_font(self):
        """获取端口标签字体"""
        from PyQt6.QtGui import QFont
        font = QFont()
        font.setPointSize(10)
        return font
    
    def _on_param_changed(self, name: str, value):
        """参数变更 → 写回 config.json"""
        config = self._get_node_config()
        if config is not None:
            config[name] = value
            self._save_node_config(config)

    def _get_node_config(self):
        """获取当前节点的 config 字典"""
        pw = self._get_parent_window()
        if pw:
            data = pw.nodes_data.get(self.node_name, {})
            return data.get('config')
        return None

    def _save_node_config(self, config: dict):
        """保存 config 到文件并同步内存"""
        pw = self._get_parent_window()
        if not pw:
            return
        pw.nodes_data[self.node_name]['config'] = config
        node_path = pw.nodes_data[self.node_name].get('path', '')
        if node_path:
            import json
            cfg_path = os.path.join(node_path, 'config.json')
            try:
                with open(cfg_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning("Failed to save config for %s: %s", self.node_name, e)

    def _get_parent_window(self):
        """获取 main_window 引用"""
        if self.canvas and self.canvas.parent_window:
            return self.canvas.parent_window
        return None

    def _subscribe_config_changes(self):
        """订阅 config.json 外部变更信号（双向数据绑定）"""
        pw = self._get_parent_window()
        if pw and hasattr(pw, 'polling_manager'):
            try:
                pw.polling_manager.config_file_changed.connect(
                    self._on_external_config_change)
            except Exception:
                pass  # 重复连接忽略

    def _on_external_config_change(self, node_name: str):
        """外部修改 config.json → 刷新画布控件"""
        if node_name != self.node_name:
            return
        config = self._get_node_config()
        if config:
            for name, widget in self._param_widgets.items():
                if name in config:
                    widget.set_value(config[name])