"""
节点画布 - VueFlow风格的无限画布（QGraphicsView + 自定义Item）
支持：无限画布、节点拖拽、锚点连线、贝塞尔曲线、缩放平移
"""
import os
import json
import math
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
    QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsTextItem,
    QMenu, QMessageBox, QGraphicsItem, QGraphicsPolygonItem
)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QPainterPath,
    QPolygonF
)


class AnchorItem(QGraphicsEllipseItem):
    """锚点项（输入/输出端口）"""
    
    def __init__(self, x, y, anchor_type="input", parent=None):
        super().__init__(x, y, 16, 16, parent)  # 增大到16x16
        self.anchor_type = anchor_type  # "input" 或 "output"
        
        # 设置颜色
        color = QColor("#4CAF50" if anchor_type == "input" else "#2196F3")
        self.setBrush(color)
        self.setPen(QPen(QColor("#333"), 2))  # 加粗边框
        self.setZValue(10)  # 确保在最上层
        
        # 悬停效果
        self.setAcceptHoverEvents(True)
        
    def hoverEnterEvent(self, event):
        """鼠标进入时高亮"""
        highlight_color = QColor("#66BB6A" if self.anchor_type == "input" else "#42A5F5")
        self.setBrush(highlight_color)
        self.setPen(QPen(QColor("#000"), 2.5))  # 更粗的边框
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        """鼠标离开时恢复"""
        normal_color = QColor("#4CAF50" if self.anchor_type == "input" else "#2196F3")
        self.setBrush(normal_color)
        self.setPen(QPen(QColor("#333"), 2))
        super().hoverLeaveEvent(event)


class NodeItem(QGraphicsRectItem):
    """节点项（对应VueFlow节点）"""
    
    def __init__(self, node_name, language="Python", status="stopped", x=0, y=0, w=140, h=80, canvas=None):
        super().__init__(x, y, w, h, None)  # parent为None
        self.node_name = node_name
        self.language = language
        self.status = status
        self.canvas = canvas  # 引用画布对象
        
        # 设置可移动和可选中
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        
        # 样式
        self.setBrush(QBrush(QColor("#f8f9fa")))
        self.setPen(QPen(QColor("#dee2e6"), 2))
        self.setZValue(1)
        
        # 设置节点矩形（位置为0,0，实际位置由setPos控制）
        self.setRect(QRectF(0, 0, w, h))
        
        # 创建锚点（相对于节点左上角的局部坐标）
        # 输入锚点（左侧中间）- 增大到16x16，中心点在(-8, h/2)
        self.input_anchor = AnchorItem(-8, h/2 - 8, "input", self)
        
        # 输出锚点（右侧中间）- 增大到16x16，中心点在(w-8, h/2)
        self.output_anchor = AnchorItem(w - 8, h/2 - 8, "output", self)
        
        # 添加输入/输出标签
        input_label = QGraphicsTextItem("IN", self)
        input_label.setDefaultTextColor(QColor("#4CAF50"))
        font_tiny = QFont("Arial", 7)  # 稍微增大字体
        input_label.setFont(font_tiny)
        input_label.setPos(-22, h/2 - 5)
        
        output_label = QGraphicsTextItem("OUT", self)
        output_label.setDefaultTextColor(QColor("#2196F3"))
        output_label.setFont(font_tiny)
        output_label.setPos(w + 4, h/2 - 5)
        
        # 节点名称文本（居中显示）
        self.name_text = QGraphicsTextItem(node_name, self)
        self.name_text.setDefaultTextColor(QColor("#333"))
        font = QFont("Arial", 10, QFont.Weight.Bold)
        self.name_text.setFont(font)
        name_rect = self.name_text.boundingRect()
        self.name_text.setPos((w - name_rect.width()) / 2, 15)
        
        # 状态指示灯（左上角）
        self.status_indicator = QGraphicsEllipseItem(8, 8, 10, 10, self)
        self.update_status(status)
        
        # 语言标签（底部居中）
        self.lang_text = QGraphicsTextItem(language, self)
        self.lang_text.setDefaultTextColor(QColor("#666"))
        font_small = QFont("Arial", 8)
        self.lang_text.setFont(font_small)
        lang_rect = self.lang_text.boundingRect()
        self.lang_text.setPos((w - lang_rect.width()) / 2, h - 18)
        
    def update_status(self, status):
        """更新节点状态"""
        self.status = status
        color = QColor("#4CAF50") if status == "running" else QColor("#9E9E9E")
        self.status_indicator.setBrush(QBrush(color))
        
    def update_display(self, node_name=None, language=None, status=None):
        """更新节点显示信息（与数据同步）"""
        w = self.rect().width()
        h = self.rect().height()
        
        # 更新节点名称
        if node_name:
            self.node_name = node_name
            self.name_text.setPlainText(node_name)
            name_rect = self.name_text.boundingRect()
            self.name_text.setPos((w - name_rect.width()) / 2, 15)
        
        # 更新语言
        if language:
            self.language = language
            self.lang_text.setPlainText(language)
            lang_rect = self.lang_text.boundingRect()
            self.lang_text.setPos((w - lang_rect.width()) / 2, h - 18)
        
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
        """监听节点位置变化，自动保存布局并更新连线"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # 1. 更新所有相关连线的路径
            if self.canvas:
                for edge in self.canvas.edges:
                    if edge.start_node == self or edge.end_node == self:
                        edge.update_path()
            
            # 2. 节点位置改变后，自动保存布局（防抖500ms）
            if self.canvas and hasattr(self.canvas, '_save_timer'):
                self.canvas._save_timer.stop()
                self.canvas._save_timer.start(500)
        
        return super().itemChange(change, value)
        
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 获取点击位置相对于节点的坐标
            pos_in_item = self.mapFromScene(event.scenePos())
            
            # 检查是否点击了输出锚点（开始连线）
            # 输出锚点在右侧中间，现在是16x16，中心点在(w-8, h/2)
            w = self.rect().width()
            h = self.rect().height()
            output_anchor_rect = QRectF(w - 8, h/2 - 8, 16, 16)
            
            if output_anchor_rect.contains(pos_in_item):
                if self.canvas:
                    self.canvas.start_connection_from_output(self)
                    print(f"🔗 开始从 {self.node_name} 的输出锚点连线")
                return  # 不继续处理，避免触发拖拽
            
            # 检查是否点击了输入锚点（左侧中间）
            input_anchor_rect = QRectF(-8, h/2 - 8, 16, 16)
            if input_anchor_rect.contains(pos_in_item):
                # 如果正在连线中，完成连线
                if self.canvas and self.canvas.is_connecting:
                    self.canvas.complete_connection_to_input(self)
                    print(f"✅ 完成到 {self.node_name} 的输入锚点连线")
                return
            
            # 其他区域：正常拖拽和选中
            if self.canvas:
                self.canvas.on_node_selected(self)
        
        super().mousePressEvent(event)


class EdgeItem(QGraphicsPathItem):
    """连线条（贝塞尔曲线，对应VueFlow连线）"""
    
    def __init__(self, start_node, end_node):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        
        # 样式
        pen = QPen(QColor("#4A90E2"), 2.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)
        self.setZValue(0)  # 在节点下方
        
        # 启用鼠标事件
        self.setAcceptHoverEvents(True)
        
        # 箭头项（初始为None）
        self.arrow_item = None
        
        # 注意：不在这里调用update_path()，因为此时还没有添加到场景
        # update_path() 会在 addToScene() 或 itemChange() 中被调用
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.RightButton:
            # 显示右键菜单
            menu = QMenu()
            delete_action = menu.addAction("删除连线")
            action = menu.exec(event.screenPos())
            
            if action == delete_action:
                # 通知画布删除此连线
                if self.scene():
                    for item in self.scene().items():
                        if isinstance(item, NodeCanvas):
                            item.remove_edge(self)
                            break
            
            event.accept()
            return
        
        super().mousePressEvent(event)

    def update_path(self):
        """更新贝塞尔曲线路径"""
        # 获取锚点的全局坐标
        start_pos = self.start_node.output_anchor.sceneBoundingRect().center()
        end_pos = self.end_node.input_anchor.sceneBoundingRect().center()
        
        # 计算控制点（使曲线更平滑）
        dx = abs(end_pos.x() - start_pos.x())
        ctrl_offset = max(dx * 0.5, 50)
        
        # 创建贝塞尔曲线路径
        path = QPainterPath(start_pos)
        ctrl1 = QPointF(start_pos.x() + ctrl_offset, start_pos.y())
        ctrl2 = QPointF(end_pos.x() - ctrl_offset, end_pos.y())
        path.cubicTo(ctrl1, ctrl2, end_pos)
        
        self.setPath(path)
        
        # 添加箭头
        self.add_arrow(start_pos, end_pos)
        
    def add_arrow(self, start_pos, end_pos):
        """在终点添加箭头"""
        # 计算箭头方向
        dx = end_pos.x() - start_pos.x()
        dy = end_pos.y() - start_pos.y()
        angle = math.atan2(dy, dx)
        
        # 箭头大小
        arrow_size = 10
        arrow_angle = math.pi / 6  # 30度
        
        # 箭头两个点
        p1_x = end_pos.x() - arrow_size * math.cos(angle - arrow_angle)
        p1_y = end_pos.y() - arrow_size * math.sin(angle - arrow_angle)
        p2_x = end_pos.x() - arrow_size * math.cos(angle + arrow_angle)
        p2_y = end_pos.y() - arrow_size * math.sin(angle + arrow_angle)
        
        # 创建箭头多边形
        arrow = QPolygonF([
            QPointF(end_pos.x(), end_pos.y()),
            QPointF(p1_x, p1_y),
            QPointF(p2_x, p2_y)
        ])
        
        # 绘制箭头（作为子项）
        scene = self.scene()
        if scene is None:
            # 如果还没有添加到场景，先移除旧的箭头（如果有）
            if hasattr(self, 'arrow_item') and self.arrow_item:
                # 暂时不处理，等添加到场景后再添加箭头
                pass
            return
        
        if hasattr(self, 'arrow_item') and self.arrow_item:
            scene.removeItem(self.arrow_item)
            
        self.arrow_item = QGraphicsPolygonItem()
        self.arrow_item.setPolygon(arrow)
        self.arrow_item.setBrush(QColor("#4A90E2"))
        self.arrow_item.setPen(QPen(Qt.PenStyle.NoPen))
        self.arrow_item.setZValue(2)
        scene.addItem(self.arrow_item)

    def remove_from_scene(self):
        """从场景中移除连线和箭头"""
        if hasattr(self, 'arrow_item') and self.arrow_item:
            self.scene().removeItem(self.arrow_item)
        self.scene().removeItem(self)


class NodeCanvas(QGraphicsView):
    """节点画布（VueFlow风格）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # 创建场景
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # 设置视图属性
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)  # 右键拖拽平移
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        # 背景色
        self.setBackgroundBrush(QColor("#fafafa"))
        
        # 网格背景（可选）
        self.draw_grid = True
        
        # 节点和连线存储
        self.nodes = {}  # {node_name: NodeItem}
        self.edges = []  # [EdgeItem]
        
        # 连线状态
        self.is_connecting = False
        self.connect_source = None
        self.temp_edge = None
        
        # 启用鼠标追踪
        self.setMouseTracking(True)
        
        # 自动保存定时器（防抖500ms）
        from PyQt6.QtCore import QTimer
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._auto_save_layout)

    def drawBackground(self, painter, rect):
        """绘制背景网格"""
        super().drawBackground(painter, rect)
        
        if not self.draw_grid:
            return
        
        # 绘制淡灰色网格
        grid_size = 20
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)
        
        painter.setPen(QPen(QColor("#e0e0e0"), 0.5))
        
        # 垂直线
        x = left
        while x < int(rect.right()):
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
            x += grid_size
        
        # 水平线
        y = top
        while y < int(rect.bottom()):
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
            y += grid_size
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 修复连线拖拽跟随鼠标"""
        # 如果正在连线中，更新临时连线的终点
        if self.is_connecting and self.temp_edge and self.connect_source:
            # 获取鼠标在场景中的位置
            scene_pos = self.mapToScene(event.position().toPoint())
            
            # 获取源节点的输出锚点位置
            start_pos = self.connect_source.output_anchor.sceneBoundingRect().center()
            
            # 创建贝塞尔曲线路径（从源节点到鼠标位置）
            dx = abs(scene_pos.x() - start_pos.x())
            ctrl_offset = max(dx * 0.5, 50)
            
            path = QPainterPath(start_pos)
            ctrl1 = QPointF(start_pos.x() + ctrl_offset, start_pos.y())
            ctrl2 = QPointF(scene_pos.x() - ctrl_offset, scene_pos.y())
            path.cubicTo(ctrl1, ctrl2, scene_pos)
            
            # 更新临时连线路径
            self.temp_edge.setPath(path)
            
            # 刷新画布显示
            self.viewport().update()
            
            event.accept()
            return
        
        # 默认处理（拖拽平移等）
        super().mouseMoveEvent(event)
    
    def wheelEvent(self, event):
        """滚轮缩放事件"""
        # 计算缩放因子
        factor = 1.15 if event.angleDelta().y() > 0 else 1/1.15
        
        # 限制缩放范围
        current_scale = self.transform().m11()
        new_scale = current_scale * factor
        
        if 0.1 <= new_scale <= 5.0:
            self.scale(factor, factor)
            
            # 自动保存布局（包含视图状态）
            if self.parent_window and self.parent_window.current_project_path:
                self._save_timer.stop()
                self._save_timer.start(500)
        
        event.accept()

    def add_node_to_canvas(self, node_name):
        """添加节点到画布"""
        if node_name in self.nodes:
            QMessageBox.information(self, "提示", "节点已在画布中")
            return
        
        # 获取节点信息
        if self.parent_window and node_name in self.parent_window.nodes_data:
            node_info = self.parent_window.nodes_data[node_name]
            language = self.detect_language(node_info['path'])
            status = node_info.get('status', 'stopped')
        else:
            language = "Python"
            status = "stopped"
        
        # 计算新节点位置（避免重叠）
        if self.nodes:
            # 找到最右下角的节点位置
            max_x = max(node.pos().x() for node in self.nodes.values())
            max_y = max(node.pos().y() for node in self.nodes.values())
            x = max_x + 50
            y = max_y + 50
        else:
            # 第一个节点放在中心附近
            x = 200
            y = 150
        
        # 创建节点
        node = NodeItem(node_name, language, status, x, y, 140, 80, self)
        self.scene.addItem(node)
        self.nodes[node_name] = node  # 添加到nodes字典
        
        print(f"✅ 节点 '{node_name}' 已添加到画布 (位置: {x}, {y})")
        
    def remove_node_from_canvas(self, node_name):
        """从画布移除节点"""
        if node_name not in self.nodes:
            return
        
        node = self.nodes[node_name]
        
        # 删除相关连线
        edges_to_remove = []
        for edge in self.edges:
            if edge.start_node == node or edge.end_node == node:
                edges_to_remove.append(edge)
        
        for edge in edges_to_remove:
            self.remove_edge(edge)
        
        # 移除节点
        self.scene.removeItem(node)
        del self.nodes[node_name]
        
    def contextMenuEvent(self, event):
        """画布右键菜单"""
        # 获取点击位置的项
        item = self.itemAt(event.pos())
        
        # 如果点击的是节点，显示节点菜单
        if isinstance(item, NodeItem):
            menu = QMenu(self)
            
            # 删除节点
            delete_action = menu.addAction("🗑️ 从画布删除节点")
            delete_action.triggered.connect(lambda: self.remove_node_with_cleanup(item.node_name))
            
            menu.addSeparator()
            
            # 打开配置对话框
            config_action = menu.addAction("⚙️ 打开配置")
            config_action.triggered.connect(lambda: self.open_node_config(item.node_name))
            
            menu.exec(event.globalPos())
        else:
            # 点击空白区域，显示画布菜单
            menu = QMenu(self)
            
            # 清空所有连线
            clear_edges_action = menu.addAction("🧹 清空所有连线")
            clear_edges_action.triggered.connect(self.clear_edges)
            
            menu.addSeparator()
            
            # 重置视图
            reset_view_action = menu.addAction("🔍 重置视图")
            reset_view_action.triggered.connect(self.reset_view)
            
            menu.exec(event.globalPos())
    
    def remove_node_with_cleanup(self, node_name):
        """从画布删除节点并清理上下游配置"""
        if node_name not in self.nodes:
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要从画布中删除节点 '{node_name}' 吗？\n\n"
            f"这将：\n"
            f"1. 从画布中移除该节点\n"
            f"2. 删除所有相关连线\n"
            f"3. 清除上下游节点的 listen_upper_file 配置",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # 1. 找到所有与该节点相关的连线
        edges_to_remove = []
        upstream_nodes = set()  # 上游节点（连接到该节点的）
        downstream_nodes = set()  # 下游节点（该节点连接到的）
        
        for edge in self.edges:
            source_name = None
            target_name = None
            for name, node in self.nodes.items():
                if node == edge.start_node:
                    source_name = name
                if node == edge.end_node:
                    target_name = name
            
            if target_name == node_name:
                # 该节点是目标节点，source是上游
                if source_name:
                    upstream_nodes.add(source_name)
                edges_to_remove.append(edge)
            elif source_name == node_name:
                # 该节点是源节点，target是下游
                if target_name:
                    downstream_nodes.add(target_name)
                edges_to_remove.append(edge)
        
        # 2. 删除所有相关连线
        for edge in edges_to_remove:
            self.remove_edge(edge)
        
        # 3. 清除上游节点的 listen_upper_file（因为它们的下游被删除了）
        for upstream_name in upstream_nodes:
            if self.parent_window and upstream_name in self.parent_window.nodes_data:
                upstream_info = self.parent_window.nodes_data[upstream_name]
                upstream_config = upstream_info['config']
                upstream_config['listen_upper_file'] = ""
                
                config_path = os.path.join(upstream_info['path'], "config.json")
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(upstream_config, f, indent=2, ensure_ascii=False)
                    print(f"✅ 已清除上游节点 {upstream_name} 的监听配置")
                except Exception as e:
                    print(f"❌ 保存配置失败: {e}")
        
        # 4. 清除下游节点的 listen_upper_file（因为上游被删除了）
        for downstream_name in downstream_nodes:
            if self.parent_window and downstream_name in self.parent_window.nodes_data:
                downstream_info = self.parent_window.nodes_data[downstream_name]
                downstream_config = downstream_info['config']
                downstream_config['listen_upper_file'] = ""
                
                config_path = os.path.join(downstream_info['path'], "config.json")
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(downstream_config, f, indent=2, ensure_ascii=False)
                    print(f"✅ 已清除下游节点 {downstream_name} 的监听配置")
                except Exception as e:
                    print(f"❌ 保存配置失败: {e}")
        
        # 5. 从画布中移除节点
        node = self.nodes[node_name]
        self.scene.removeItem(node)
        del self.nodes[node_name]
        
        print(f"✅ 已从画布删除节点: {node_name}")
        
        # 6. 自动保存布局
        if self.parent_window and self.parent_window.current_project_path:
            self._save_timer.stop()
            self._save_timer.start(500)
    
    def open_node_config(self, node_name):
        """打开节点配置对话框"""
        if self.parent_window and node_name in self.parent_window.nodes_data:
            node_info = self.parent_window.nodes_data[node_name]
            config = node_info['config']
            node_path = node_info['path']
            
            from ui.property_panel import NodeConfigDialog
            dialog = NodeConfigDialog(node_name, config, node_path, self.parent_window)
            dialog.exec()
    
    def reset_view(self):
        """重置视图到默认状态"""
        self.resetTransform()
        self.centerOn(0, 0)
        print("✅ 视图已重置")

    def update_node_status(self, node_name, status):
        """更新节点状态"""
        if node_name in self.nodes:
            self.nodes[node_name].update_status(status)
            
    def detect_language(self, node_path):
        """检测节点语言"""
        if os.path.exists(os.path.join(node_path, "main.py")):
            return "Python"
        elif os.path.exists(os.path.join(node_path, "main.js")):
            return "Node.js"
        elif os.path.exists(os.path.join(node_path, "main.go")):
            return "Go"
        elif os.path.exists(os.path.join(node_path, "Main.java")):
            return "Java"
        elif os.path.exists(os.path.join(node_path, "main.cpp")):
            return "C++"
        elif os.path.exists(os.path.join(node_path, "main.rs")):
            return "Rust"
        elif os.path.exists(os.path.join(node_path, "main.sh")):
            return "Shell"
        else:
            return "Unknown"
            
    def sync_node_display(self, node_name):
        """同步指定节点的显示（从nodes_data获取最新数据）"""
        if not self.parent_window or node_name not in self.nodes:
            return
        
        if node_name not in self.parent_window.nodes_data:
            return
        
        node_data = self.parent_window.nodes_data[node_name]
        config = node_data.get('config', {})
        status = node_data.get('status', 'stopped')
        
        # 获取节点UI对象
        node_item = self.nodes[node_name]
        
        # 同步显示
        display_data = {
            'name': config.get('node_name', node_name),
            'language': self.detect_language(node_data.get('path', '')),
            'status': status
        }
        
        node_item.sync_with_data(display_data)
        
    def sync_all_nodes_display(self):
        """同步所有节点的显示"""
        for node_name in self.nodes.keys():
            self.sync_node_display(node_name)
            
    def on_node_selected(self, node):
        """节点被选中（已废弃，改用双击打开配置对话框）"""
        # 不再需要更新右侧面板，因为已经删除
        pass
                    
    def start_connection_from_output(self, source_node):
        """从输出锚点开始连线"""
        self.is_connecting = True
        self.connect_source = source_node
        
        # 创建临时连线
        self.temp_edge = QGraphicsPathItem()
        pen = QPen(QColor("#4A90E2"), 2, Qt.PenStyle.DashLine)
        self.temp_edge.setPen(pen)
        self.scene.addItem(self.temp_edge)
        
    def complete_connection_to_input(self, target_node):
        """完成连线到输入锚点"""
        if self.connect_source and self.connect_source != target_node:
            self.create_edge(self.connect_source, target_node)
        
        # 清理临时连线
        if self.temp_edge:
            self.scene.removeItem(self.temp_edge)
            self.temp_edge = None
        
        self.is_connecting = False
        self.connect_source = None
    
    def create_edge(self, source_node, target_node):
        """创建连线并配置上下游关系"""
        # 检查是否已存在相同连线
        for edge in self.edges:
            if edge.start_node == source_node and edge.end_node == target_node:
                QMessageBox.information(self, "提示", "该连线已存在")
                return
        
        # 获取节点名称
        source_name = None
        target_name = None
        for name, node in self.nodes.items():
            if node == source_node:
                source_name = name
            if node == target_node:
                target_name = name
        
        if not source_name or not target_name:
            return
        
        # 配置下游节点的listen_upper_file为上游output.json的绝对路径
        if self.parent_window and target_name in self.parent_window.nodes_data:
            target_info = self.parent_window.nodes_data[target_name]
            source_path = self.parent_window.nodes_data[source_name]['path']
            
            # 计算上游output.json的绝对路径
            source_output_path = os.path.abspath(
                os.path.join(source_path, "output.json")
            )
            
            # 更新下游节点配置
            target_config = target_info['config']
            target_config['listen_upper_file'] = source_output_path
            
            # 保存到文件
            config_path = os.path.join(target_info['path'], "config.json")
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(target_config, f, indent=2, ensure_ascii=False)
                
                print(f"✅ 已配置 {target_name} 监听 {source_name} 的输出")
                print(f"   listen_upper_file: {source_output_path}")
            except Exception as e:
                print(f"❌ 保存配置失败: {e}")
        
        # 创建连线条（此时不会自动更新路径）
        edge = EdgeItem(source_node, target_node)
        
        # 先添加到场景
        self.scene.addItem(edge)
        self.edges.append(edge)
        
        # 添加到场景后再更新路径和箭头
        edge.update_path()
        
        print(f"✅ 创建连线: {source_name} -> {target_name}")
        
        # 自动保存布局（防抖500ms）
        if self.parent_window and self.parent_window.current_project_path:
            self._save_timer.stop()
            self._save_timer.start(500)

    def remove_edge(self, edge):
        """移除连线"""
        if edge in self.edges:
            # 获取连线的目标节点名称
            target_name = None
            for name, node in self.nodes.items():
                if node == edge.end_node:
                    target_name = name
                    break
            
            # 清空下游节点的listen_upper_file
            if target_name and self.parent_window and target_name in self.parent_window.nodes_data:
                target_info = self.parent_window.nodes_data[target_name]
                target_config = target_info['config']
                target_config['listen_upper_file'] = ""
                
                # 保存到文件
                config_path = os.path.join(target_info['path'], "config.json")
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(target_config, f, indent=2, ensure_ascii=False)
                    print(f"✅ 已清空 {target_name} 的监听配置")
                except Exception as e:
                    print(f"❌ 保存配置失败: {e}")
            
            # 从场景中移除
            edge.remove_from_scene()
            self.edges.remove(edge)
            
            # 自动保存布局（防抖500ms）
            if self.parent_window and self.parent_window.current_project_path:
                self._save_timer.stop()
                self._save_timer.start(500)

    def clear_edges(self):
        """清空所有连线"""
        for edge in self.edges[:]:
            self.remove_edge(edge)
        self.edges.clear()

    def clear_canvas(self):
        """清空画布"""
        # 移除所有连线
        for edge in self.edges[:]:
            edge.remove_from_scene()
        self.edges.clear()
        
        # 移除所有节点
        for node_name, node in self.nodes.items():
            self.scene.removeItem(node)
        self.nodes.clear()
        
        # 重置连线状态
        self.is_connecting = False
        self.connect_source = None
        if self.temp_edge:
            self.scene.removeItem(self.temp_edge)
            self.temp_edge = None
            
        print("🗑️ 画布已清空")

    def rename_node_in_canvas(self, old_name, new_name):
        """在画布中重命名节点"""
        if old_name in self.nodes:
            node = self.nodes[old_name]
            # 更新节点内部名称
            node.node_name = new_name
            # 更新显示文本
            node.name_text.setPlainText(new_name)
            name_rect = node.name_text.boundingRect()
            w = node.rect().width()
            node.name_text.setPos((w - name_rect.width()) / 2, 15)
            
            # 更新字典键
            del self.nodes[old_name]
            self.nodes[new_name] = node
            
            print(f"✅ 画布节点已重命名: {old_name} -> {new_name}")

    def save_layout(self, project_path):
        """保存画布布局到JSON文件 - 完整持久化"""
        if not project_path:
            return
        
        layout_data = {
            "nodes": {},
            "edges": [],
            "view_state": {
                "scale": self.transform().m11(),
                "scroll_x": self.horizontalScrollBar().value(),
                "scroll_y": self.verticalScrollBar().value()
            }
        }
        
        # 保存节点位置和大小
        for node_name, node in self.nodes.items():
            pos = node.pos()
            layout_data["nodes"][node_name] = {
                "x": pos.x(),
                "y": pos.y(),
                "width": node.rect().width(),
                "height": node.rect().height()
            }
        
        # 保存连线关系
        for edge in self.edges:
            start_name = None
            end_name = None
            for name, node in self.nodes.items():
                if node == edge.start_node:
                    start_name = name
                if node == edge.end_node:
                    end_name = name
            
            if start_name and end_name:
                layout_data["edges"].append({
                    "source": start_name,
                    "target": end_name
                })
        
        # 保存到文件
        layout_file = os.path.join(project_path, "canvas_layout.json")
        try:
            with open(layout_file, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)
            print(f"✅ 画布布局已保存到: {layout_file}")
        except Exception as e:
            print(f"❌ 保存布局失败: {e}")
            
    def load_layout(self, project_path):
        """从JSON文件加载画布布局 - 完整还原（智能合并）"""
        if not project_path:
            return
        
        layout_file = os.path.join(project_path, "canvas_layout.json")
        if not os.path.exists(layout_file):
            print(f"ℹ️  未找到布局文件: {layout_file}")
            return
        
        try:
            with open(layout_file, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
            
            nodes_loaded = 0
            edges_loaded = 0
            
            # 第一步：恢复节点位置（对于已存在的节点）
            for node_name, pos_data in layout_data.get("nodes", {}).items():
                if node_name in self.nodes:
                    node = self.nodes[node_name]
                    node.setPos(pos_data["x"], pos_data["y"])
                    nodes_loaded += 1
            
            # 第二步：自动添加布局文件中记录但当前不在画布上的节点
            total_nodes_in_layout = len(layout_data.get("nodes", {}))
            nodes_added_auto = 0
            
            for node_name, pos_data in layout_data.get("nodes", {}).items():
                if node_name not in self.nodes:
                    # 检查节点是否存在于项目数据中
                    if self.parent_window and node_name in self.parent_window.nodes_data:
                        node_info = self.parent_window.nodes_data[node_name]
                        language = self.detect_language(node_info['path'])
                        status = node_info.get('status', 'stopped')
                        
                        # 使用保存的位置创建节点
                        x = pos_data.get("x", 200)
                        y = pos_data.get("y", 150)
                        w = pos_data.get("width", 140)
                        h = pos_data.get("height", 80)
                        
                        # 创建节点（位置参数会被构造函数忽略，需要后续setPos）
                        node = NodeItem(node_name, language, status, 0, 0, w, h, self)
                        node.setPos(x, y)  # 显式设置位置
                        self.scene.addItem(node)
                        self.nodes[node_name] = node
                        
                        nodes_added_auto += 1
                        print(f"   🔄 自动恢复节点: {node_name} (位置: {x}, {y})")

            # 第三步：恢复连线（避免重复，只恢复两端节点都在画布中的连线）
            existing_edges = set()
            for edge in self.edges:
                # 获取连线的源和目标节点名称
                source_name = None
                target_name = None
                for name, node in self.nodes.items():
                    if node == edge.start_node:
                        source_name = name
                    if node == edge.end_node:
                        target_name = name
                if source_name and target_name:
                    existing_edges.add((source_name, target_name))
            
            edges_restored = 0
            for edge_data in layout_data.get("edges", []):
                source_name = edge_data.get("source")
                target_name = edge_data.get("target")
                
                # 跳过已存在的连线
                if (source_name, target_name) in existing_edges:
                    continue
                
                if source_name in self.nodes and target_name in self.nodes:
                    start_node = self.nodes[source_name]
                    end_node = self.nodes[target_name]
                    
                    # 创建连线（此时不会自动更新路径）
                    edge = EdgeItem(start_node, end_node)
                    
                    # 先添加到场景
                    self.scene.addItem(edge)
                    self.edges.append(edge)
                    
                    # 添加到场景后再更新路径和箭头
                    edge.update_path()
                    
                    edges_restored += 1

            # 输出统计信息
            total_nodes = len(self.nodes)
            total_edges = len(self.edges)
            print(f"✅ 加载完成: {total_nodes}个节点, {total_edges}条连线")
            if nodes_added_auto > 0:
                print(f"   🔄 自动恢复: {nodes_added_auto}个节点")
            if edges_restored > 0:
                print(f"   🔗 恢复连线: {edges_restored}条")

            # 第四步：恢复视图状态（缩放、滚动位置）
            view_state = layout_data.get("view_state")
            if view_state:
                try:
                    # 恢复缩放
                    scale = view_state.get("scale", 1.0)
                    if scale > 0 and scale != 1.0:
                        self.resetTransform()
                        self.scale(scale, scale)
                    
                    # 恢复滚动位置
                    scroll_x = view_state.get("scroll_x", 0)
                    scroll_y = view_state.get("scroll_y", 0)
                    self.horizontalScrollBar().setValue(scroll_x)
                    self.verticalScrollBar().setValue(scroll_y)
                    
                    print(f"✅ 画布视图状态已恢复 (缩放: {scale:.2f}x)")
                except Exception as e:
                    print(f"⚠️  恢复画布视图状态失败: {e}")

        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  布局文件损坏，使用默认布局: {e}")
            # 备份损坏的文件
            try:
                import shutil
                backup_file = layout_file + ".bak"
                shutil.copy2(layout_file, backup_file)
                print(f"📦 已备份损坏的布局文件: {backup_file}")
            except:
                pass
        except Exception as e:
            print(f"❌ 加载布局失败: {e}")
            import traceback
            traceback.print_exc()

    def _auto_save_layout(self):
        """自动保存布局（防抖）"""
        if self.parent_window and self.parent_window.current_project_path:
            self.save_layout(self.parent_window.current_project_path)
