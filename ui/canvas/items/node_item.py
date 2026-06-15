"""
节点项（对应VueFlow节点）
继承自 QGraphicsRectItem，负责节点的视觉渲染、锚点管理和交互处理
"""
import os
from PySide6.QtWidgets import (QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem,
    QGraphicsItem, QGraphicsProxyWidget)
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QColor, QBrush, QFont, QPainterPath
from datetime import datetime
from ui.core.logger import logger

from ui.canvas.items.anchor_item import AnchorItem, ANCHOR_SIZE, ANCHOR_HALF
from ui.canvas.items.anchor_manager import AnchorManager
from ui.canvas.items.styles import DetailedNodeStyle
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
        
        # 节点样式（默认面板模式）
        self._style = style or DetailedNodeStyle()
        self._style.node_width = w
        self._style.node_height = h
        
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)
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

        # 初始化状态显示组件（所有节点都用，无进度条，仅文本）
        self._status_widget = NodeStatusWidget(self)
        self._status_widget.set_compact(True)
        self._status_widget.set_visible(True)
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
        """更新选中环 — 面板模式下由 paint 方法直接绘制选中高亮"""
        self._selection_ring.setVisible(False)

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
            self._status_widget.update_status(cpu_percent, mem_mb)
    
    def _try_initialize_start_time(self):
        """尝试从节点数据中初始化开始时间"""
        if not self.canvas or not self.canvas.parent_window:
            return
            
        if self.node_name in self.canvas.parent_window.nodes_data:
            node_info = self.canvas.parent_window.nodes_data[self.node_name]
            # 如果节点正在运行，记录开始时间
            if node_info.get('status') in ['running', 'idle']:
                self._start_time = datetime.now()

    def dispose(self):
        """断开所有外部信号连接并清理子对象（防止信号/内存泄漏）

        应在节点从画布移除或画布销毁前调用。
        """
        # 1. 断开资源监测面板信号
        if self.canvas and self.canvas.parent_window:
            parent = self.canvas.parent_window
            try:
                if hasattr(parent, 'resource_monitor_floating') and parent.resource_monitor_floating:
                    parent.resource_monitor_floating.node_state_updated.disconnect(self._on_status_updated)
            except (TypeError, RuntimeError):
                pass
            try:
                if hasattr(parent, 'resource_monitor') and parent.resource_monitor:
                    if hasattr(parent.resource_monitor, 'node_state_updated'):
                        parent.resource_monitor.node_state_updated.disconnect(self._on_status_updated)
            except (TypeError, RuntimeError):
                pass

        # 2. 停止状态组件的计时器
        if self._status_widget:
            try:
                self._status_widget.stop_timer()
            except Exception:
                pass

        # 3. 清理 proxy widget
        for pw in self._proxy_widgets:
            try:
                if pw and pw.widget():
                    pw.widget().deleteLater()
            except Exception:
                pass
        self._proxy_widgets.clear()
        self._param_widgets.clear()

        # 4. 清除像素缓存（防止 QGraphicsScene 继续持有渲染数据）
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)

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
            elif self._style.status_show:
                # 仅当当前样式支持状态显示时才创建（节点模式/面板模式不创建）
                self._status_widget = NodeStatusWidget(self)
                self._status_widget.set_visible(True)
                self._start_time = datetime.now()
                self._connect_resource_monitor_signals()
        else:
            # 节点停止了，清除开始时间
            self._start_time = None
                    
    def set_style(self, style):
        """设置节点样式（统一使用面板模式）"""
        # 销毁所有 Proxy 控件
        if hasattr(self, '_proxy_widgets') and self._proxy_widgets:
            self._destroy_detailed()

        # 只有 DetailedNodeStyle 被支持
        self._style = style or DetailedNodeStyle()
        self._style.node_width = self.rect().width() or 340
        self._style.node_height = self.rect().height() or 80

        # 应用新样式
        self.setCacheMode(self.CacheMode.NoCache)
        self.prepareGeometryChange()
        self.setRect(0, 0, self._style.node_width, self._style.node_height)
        self._style.apply(self)
        self._style.apply_status(self, self.status)

        # 同步显示状态控件
        if not self._status_widget:
            self._status_widget = NodeStatusWidget(self)
        self._status_widget.set_compact(True)
        self._status_widget.set_visible(True)
        self._status_widget.update_layout()
        self._start_time = None
        self._connect_resource_monitor_signals()

        self._update_selection_ring(self.isSelected())

        if self.scene():
            self.scene().update()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self._ensure_rect(self._style.node_width, self._style.node_height))

    def _ensure_rect(self, w, h):
        """兜底：事件循环后强制校正节点尺寸"""
        if self._style.style_key == "detailed":
            return  # 详细版由内容驱动尺寸
        current_rect = self.rect()
        if abs(current_rect.width() - w) > 0.5 or abs(current_rect.height() - h) > 0.5:
            self.prepareGeometryChange()
            self.setCacheMode(self.CacheMode.NoCache)
            self.setRect(0, 0, w, h)
            self.setCacheMode(self.CacheMode.DeviceCoordinateCache)
            self.update()
      
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
            except Exception:
                pass
        if 'custom_border_color' in config:
            try:
                custom_color = QColor(config['custom_border_color'])
                if custom_color.isValid():
                    self.setPen(QPen(custom_color, 2))
            except Exception:
                pass
        
        # 应用自定义文字色
        if 'custom_text_color' in config:
            try:
                custom_color = QColor(config['custom_text_color'])
                if custom_color.isValid():
                    self.name_text.setDefaultTextColor(custom_color)
            except Exception:
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
        """返回形状区域用于命中检测 — 面板模式下使用节点矩形"""
        return super().shape()

    def paint(self, painter, option, widget=None):
        """绘制节点 — 圆角矩形 + 选中高亮（面板模式）"""
        from PySide6.QtGui import QPainterPath, QPainter
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = self.rect()
        w = rect.width()
        h = rect.height()

        corner_radius = self._style.CORNER_RADIUS
        body_bg = self._style.body_bg
        body_border = self._style.body_border
        node_rect = QRectF(0, 0, w, h)

        # 1. 主体圆角矩形背景
        body_path = QPainterPath()
        body_path.addRoundedRect(node_rect, corner_radius, corner_radius)
        painter.setBrush(QBrush(QColor(body_bg)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(body_path)

        # 2. 边框（选中状态高亮）
        border_color = QColor("#66b0ff") if self.isSelected() else QColor(body_border)
        border_width = 2 if self.isSelected() else 1
        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(QBrush())
        painter.drawPath(body_path)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            pos_in_item = self.mapFromScene(event.scenePos())
            w = self.rect().width()
            h = self.rect().height()

            # 展开按钮（保留扩展点）
            if self._expand_btn_rect.contains(pos_in_item):
                if self.on_expand_requested:
                    self.on_expand_requested(self.node_name)
                event.accept()
                return

            # 输出锚点（开始连线）
            clicked_output = self.find_nearest_output_anchor(pos_in_item, max_dist=20)
            if clicked_output is None:
                default_output_rect = QRectF(w - ANCHOR_HALF, h / 2 - ANCHOR_HALF, ANCHOR_SIZE, ANCHOR_SIZE)
                if default_output_rect.contains(pos_in_item):
                    clicked_output = self.anchor_manager.get_output("default")
            if clicked_output:
                port_label = (
                    clicked_output.port_name
                    if getattr(clicked_output, "port_name", None)
                    else "default"
                )
                logger.debug("NodeItem[%s]: 输出锚点命中 %s", self.node_name, port_label)
                if self.canvas:
                    self.canvas.start_connection_from_output(self, clicked_output)
                event.accept()
                return

            # 输入锚点（完成连线）
            clicked_anchor = self.find_nearest_input_anchor(pos_in_item, max_dist=20)
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
                logger.debug("NodeItem[%s]: 输入锚点命中 %s", self.node_name, port_label)
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
        """面板模式构建：主体显示参数控件，节点外显示名称/状态灯/语言标签

        关键点：
          - 使用 self._style（实例），而非 DetailedNodeStyle 类
          - 即使 config 为空或无参数，也必须设置节点尺寸 + 文本/状态灯/语言标签
          - 参数控件容器仅在有参数时构建
        """
        self._destroy_detailed()
        self._param_row_positions.clear()

        from PySide6.QtGui import QFont, QColor
        style = self._style  # 用实例，不用类

        # --- 读取 config（允许为空，空 config 也应正确渲染节点本体） ---
        config = self._get_node_config()
        input_port_defs = []
        param_defs = []
        has_content = False
        if config:
            from ui.core.node_config_parser import NodeConfigParser, ParameterDef
            input_port_defs = NodeConfigParser.parse_input_ports(config) or []
            input_port_defs = [p for p in input_port_defs if getattr(p, "source", "") == "node"]
            param_defs = NodeConfigParser.parse(config) or []
            has_content = bool(input_port_defs or param_defs)

        # --- 默认尺寸（无内容时也能显示节点本体） ---
        min_container_w = 340
        default_height = 80  # 无参数时的默认高度
        final_w = max(style.node_width if style and hasattr(style, "node_width") and style.node_width else min_container_w,
                      min_container_w)
        final_h = default_height

        if has_content:
            # --- 有内容：构建参数控件容器 ---
            from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                          QGraphicsProxyWidget, QSizePolicy)
            from PySide6.QtCore import Qt
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

            row_types = []

            # 1) 输入端口行
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

            # 2) 参数行
            for p in param_defs:
                current = config.get(p.name, p.default)
                w = ParameterWidget.create(p, current)
                if hasattr(w, "value_changed"):
                    w.value_changed.connect(self._on_param_changed)
                w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                v_layout.addWidget(w)
                self._param_widgets[p.name] = w
                row_types.append("param")

            # 3) 输出行
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

            container.setMinimumWidth(min_container_w)
            container.layout().activate()
            sh = container.sizeHint()
            content_w = sh.width() if sh.isValid() else min_container_w
            content_h = sh.height() if sh.isValid() else (len(row_types) * 36 + 20)

            style.set_sizes(content_w, content_h)
            final_w = max(style.node_width, content_w)
            final_h = style.node_height
            self.setRect(0, 0, final_w, final_h)
            container.setFixedWidth(final_w)

            proxy = QGraphicsProxyWidget(self)
            proxy.setWidget(container)
            proxy.setPos(0, 0)  # 无标题栏，从 y=0 开始
            proxy.setZValue(5)
            proxy.setFlag(proxy.GraphicsItemFlag.ItemClipsChildrenToShape, False)
            proxy.setFlag(proxy.GraphicsItemFlag.ItemClipsToShape, False)
            proxy.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._proxy_widgets.append(proxy)

            # 计算锚点位置
            from ui.canvas.items.anchor_item import ANCHOR_SIZE, ANCHOR_SIZE_SMALL
            small_center_x = style.ANCHOR_ZONE_WIDTH + style.LEFT_INNER_PADDING - ANCHOR_SIZE_SMALL / 2 - 2
            margins_top = v_layout.contentsMargins().top() if v_layout.contentsMargins() else 0
            running_y = 0
            est_ys = []
            for _j in range(len(row_types)):
                est_ys.append(running_y + style.ROW_HEIGHT / 2)
                running_y += style.ROW_HEIGHT + style.ROW_SPACING

            for i, rtype in enumerate(row_types):
                item = v_layout.itemAt(i) if v_layout else None
                geom = item.geometry() if item and item.widget() else None
                if geom is None or geom.width() <= 0 or geom.height() <= 0:
                    center_y = margins_top + est_ys[i] if i < len(est_ys) else (
                        margins_top + i * (style.ROW_HEIGHT + style.ROW_SPACING) + style.ROW_HEIGHT / 2
                    )
                else:
                    row_top = geom.y()
                    center_y = row_top + geom.height() / 2.0

                if rtype == "input_port":
                    port_idx = row_types[:i].count("input_port")
                    if port_idx < len(input_port_defs):
                        port = input_port_defs[port_idx]
                        self._param_row_positions[port.name] = (
                            small_center_x, center_y, ANCHOR_SIZE_SMALL,
                        )
                elif rtype == "output":
                    out_cx = final_w
                    out_cy = final_h / 2.0
                    self._param_row_positions["__output__"] = (out_cx, out_cy, ANCHOR_SIZE)
        else:
            # 无参数：直接用默认尺寸，确保节点本体有大小
            self.setRect(0, 0, final_w, final_h)

        # --- 以下所有节点都必须执行：名称/状态灯/语言标签 ---
        # 节点名称：UI外上方
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        self.name_text.setFont(title_font)
        self.name_text.setDefaultTextColor(QColor(style.header_text_color))
        self.name_text.setZValue(6)
        self.name_text.setPlainText(self.node_name)
        text_rect = self.name_text.boundingRect()
        title_x = max(4.0, (final_w - text_rect.width()) / 2)
        title_y = -text_rect.height()  # 节点矩形上方
        self.name_text.setPos(title_x, title_y)
        self.name_text.setVisible(True)

        # 状态指示灯（右上角，UI内）
        indicator_size = 10
        indicator_x = final_w - indicator_size - 8
        indicator_y = 4
        self.status_indicator.setRect(indicator_x, indicator_y, indicator_size, indicator_size)
        self.status_indicator.setZValue(7)
        self.status_indicator.setVisible(True)
        style.apply_status(self, self.status)

        # 语言标签：UI外底部居中
        lang_font = QFont()
        lang_font.setPointSize(8)
        self.lang_text.setFont(lang_font)
        self.lang_text.setDefaultTextColor(QColor("#888888"))
        self.lang_text.setZValue(6)
        self.lang_text.setPlainText(self.language)
        lr = self.lang_text.boundingRect()
        lang_x = (final_w - lr.width()) / 2
        lang_y = final_h + 2
        self.lang_text.setPos(lang_x, lang_y)
        self.lang_text.setVisible(True)

        # CPU/MEM 文本：与语言标签在同一水平线，靠左对齐
        if self._status_widget:
            self._status_widget.set_bottom_y(lang_y)

        self._subscribe_config_changes()

    def _destroy_detailed(self):
        """销毁详细版控件（样式切换时调用），恢复缓存模式和默认尺寸"""
        for p in self._proxy_widgets:
            w = p.widget()
            if w:
                w.deleteLater()
            p.setWidget(None)
            if self.scene():
                self.scene().removeItem(p)
        self._proxy_widgets.clear()
        self._param_widgets.clear()
        # 先禁用缓存再重置 rect，确保旧缓存在尺寸变更后被彻底丢弃
        self.setCacheMode(self.CacheMode.NoCache)
        self.setRect(0, 0, self._style.node_width, self._style.node_height)

    def _get_label_font(self):
        """获取端口标签字体"""
        from PySide6.QtGui import QFont
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
        """获取当前节点的 config 字典（合并磁盘 config.json + 内存运行时状态）

        解决 start.json 启动时整体替换 node_info['config'] 导致 parameters/input_ports
        元数据丢失的问题——始终从磁盘加载完整 config.json，仅对运行时字段
        （listen_upper_file/output_file/out_connections 等）用内存值覆盖。
        """
        pw = self._get_parent_window()
        if not pw:
            return None
        path = pw.nodes_data.get(self.node_name, {}).get('path', '')
        if not path:
            return None
        # 从磁盘加载完整 config.json（始终包含 parameters/input_ports）
        cfg_path = os.path.join(path, 'config.json')
        merged = {}
        try:
            if os.path.exists(cfg_path):
                import json
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    merged = json.load(f)
        except Exception:
            pass
        # 运行时字段：用内存中的值覆盖（这些值是执行过程中动态更新的）
        mem_config = pw.nodes_data.get(self.node_name, {}).get('config', {})
        for key in ('listen_upper_file', 'output_file', 'out_connections', 'filter', 'output_type', 'port_mappings'):
            if key in mem_config:
                merged[key] = mem_config[key]
        return merged

    def _save_node_config(self, config: dict):
        """保存 config 到文件并同步内存（保护 parameters/input_ports 不被覆盖丢失）

        解决 start.json 启动覆盖导致元数据丢失后，保存回来的 config 不含
        parameters/input_ports，再次加载时无法构建面板的问题。
        """
        pw = self._get_parent_window()
        if not pw:
            return
        node_path = pw.nodes_data[self.node_name].get('path', '')
        if not node_path:
            return
        import json
        cfg_path = os.path.join(node_path, 'config.json')
        # 从磁盘加载完整 config（保护 parameters/input_ports 等元数据）
        saved_config = dict(config)
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    disk_config = json.load(f)
                for key in ('parameters', 'input_ports', 'output_ports'):
                    if key in disk_config and key not in saved_config:
                        saved_config[key] = disk_config[key]
        except Exception:
            pass
        pw.nodes_data[self.node_name]['config'] = saved_config
        try:
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(saved_config, f, indent=2, ensure_ascii=False)
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