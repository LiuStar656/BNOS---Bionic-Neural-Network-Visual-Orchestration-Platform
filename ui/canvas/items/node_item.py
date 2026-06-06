"""
节点项（对应VueFlow节点）
继承自 QGraphicsRectItem，负责节点的视觉渲染、锚点管理和交互处理
"""
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsItem
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPen, QColor, QBrush, QFont, QPainterPath
from ui.core.logger import logger
from ui.core.node_monitor import node_monitor

from ui.canvas.items.anchor_item import AnchorItem
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
        
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        
        self.setZValue(2)  # 节点层：线条(z=0) < 锚点(z=1) < 节点(z=2) < 指示灯(z=3) < 文字(z=4)
        self.setRect(QRectF(0, 0, w, h))
        
        # 锚点（节点下一层，初始位置由样式设置）
        self.input_anchor = AnchorItem(0, 0, "input", self)
        self.output_anchor = AnchorItem(0, 0, "output", self)
        
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
        if self._style.status_show and not self._style.is_dot:
            self._status_widget = NodeStatusWidget(self)
            self._status_widget.set_visible(True)
            
            # 启动节点监控
            node_monitor.add_node(self.node_name)
            
            # 连接状态更新信号
            node_monitor.status_updated.connect(self._on_status_updated)
            
            # 如果节点正在运行，开始监控
            if self.status in ["running", "idle"]:
                # 获取节点PID
                if hasattr(self.canvas, 'node_process_manager'):
                    node_info = self.canvas.node_process_manager.get_node_info(self.node_name)
                    if node_info.get('pid'):
                        node_monitor.update_node_pid(self.node_name, node_info['pid'])
        
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
     
    def _on_status_updated(self, node_name, cpu_percent, mem_mb, duration_seconds):
        """状态更新回调"""
        if node_name == self.node_name and self._status_widget:
            self._status_widget.update_status(cpu_percent, mem_mb, duration_seconds)
            
    def update_status(self, status):
        """更新节点状态"""
        self.status = status
        self._style.apply_status(self, status)
        
        # 如果状态变为运行中，更新监控PID
        if status in ["running", "idle"] and self._status_widget:
            if hasattr(self.canvas, 'node_process_manager'):
                node_info = self.canvas.node_process_manager.get_node_info(self.node_name)
                if node_info.get('pid'):
                    node_monitor.update_node_pid(self.node_name, node_info['pid'])
                    
    def set_style(self, style):
        """设置节点样式"""
        self._style = style
        self._style.node_width = self.rect().width()
        self._style.node_height = self.rect().height()
        
        # 重新应用样式
        self._style.apply(self)
        self._style.apply_status(self, self.status)
        
        # 更新状态显示组件
        if self._style.status_show and not self._style.is_dot:
            if not self._status_widget:
                self._status_widget = NodeStatusWidget(self)
                self._status_widget.set_visible(True)
                node_monitor.add_node(self.node_name)
                node_monitor.status_updated.connect(self._on_status_updated)
        else:
             if self._status_widget:
                 self._status_widget.set_visible(False)
                 node_monitor.remove_node(self.node_name)
                 node_monitor.status_updated.disconnect(self._on_status_updated)
                 self._status_widget = None
      
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
                # 1. 更新所有连接到本节点锚点的连线（使用锚点的连线列表，确保引用正确）
                all_edges = set()
                
                # 收集输出锚点的连线
                if hasattr(self, 'output_anchor'):
                    for edge in self.output_anchor.edges[:]:
                        if edge and edge.end_node:
                            all_edges.add(edge)
                
                # 收集输入锚点的连线
                if hasattr(self, 'input_anchor'):
                    for edge in self.input_anchor.edges[:]:
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
        """绘制节点 — 选中环由 _selection_ring 处理（z=10 浮于节点之上）"""
        is_dot = hasattr(self, '_body') and self._body and self._body.isVisible()
        if is_dot:
            # 圆点样式不画默认方框
            # 选中环由 itemChange 控制 _selection_ring
            pass
        else:
            super().paint(painter, option, widget)
            if self.isSelected():
                pen = QPen(QColor(self._style.selected_color), self._style.selected_border_width)
                pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(self.rect())
    
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
                output_anchor_rect = QRectF(w - 8, h / 2 - 8, 16, 16)
                if output_anchor_rect.contains(pos_in_item):
                    if self.canvas:
                        self.canvas.start_connection_from_output(self)
                    event.accept()
                    return

                # 方块节点：输入锚点（完成连线）
                input_anchor_rect = QRectF(-8, h / 2 - 8, 16, 16)
                if input_anchor_rect.contains(pos_in_item):
                    logger.debug("NodeItem: 点击输入锚点 area, is_connecting=%s, canvas=%s",
                                 self.canvas.is_connecting if self.canvas else None, self.canvas is not None)
                    if self.canvas and self.canvas.is_connecting:
                        logger.debug("NodeItem: 完成连线到 %s", self.node_name)
                        self.canvas.complete_connection_to_input(self)
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