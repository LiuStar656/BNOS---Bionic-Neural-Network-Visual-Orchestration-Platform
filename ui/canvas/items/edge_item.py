"""
连线条（贝塞尔曲线，对应VueFlow连线）
继承自 QGraphicsPathItem，负责节点间连线的视觉渲染和路径计算
"""
import math
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsPolygonItem, QMenu
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QColor, QPainterPath, QPolygonF
from ui.core.logger import logger


class EdgeItem(QGraphicsPathItem):
    """连线条（贝塞尔曲线，对应VueFlow连线）"""
    
    def __init__(self, start_node, end_node, canvas=None):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.canvas = canvas
        
        # 可视区域渲染：连线缓存
        self.setCacheMode(QGraphicsPathItem.CacheMode.DeviceCoordinateCache)
        
        # 样式（使用画布配置）
        self.update_edge_style()
        
        # 启用鼠标事件
        self.setAcceptHoverEvents(True)
        
        # 箭头项（初始为None）
        self.arrow_item = None
        
        # 注意：不在这里调用update_path()，因为此时还没有添加到场景
        # update_path() 会在 addToScene() 或 itemChange() 中被调用
    
    def update_edge_style(self):
        """更新连线样式（使用画布的颜色配置）"""
        if self.canvas:
            color = QColor(self.canvas.edge_color)
            width = self.canvas.edge_width
        else:
            color = QColor("#4A90E2")
            width = 2.5
        
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self.setPen(pen)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.RightButton:
            # 显示右键菜单
            menu = QMenu()
            
            # 删除连线
            delete_action = menu.addAction("🗑️ 删除连线")
            
            menu.addSeparator()
            
            # 连线颜色设置
            color_action = menu.addAction("🎨 修改连线颜色")
            color_action.triggered.connect(lambda: self.change_edge_color())
            
            action = menu.exec(event.screenPos())
            
            if action == delete_action:
                # 通知画布删除此连线（延迟导入避免循环依赖）
                if self.scene():
                    from ui.canvas.canvas_view import NodeCanvas
                    for item in self.scene().items():
                        if isinstance(item, NodeCanvas):
                            item.remove_edge(self)
                            break
            
            event.accept()
            return
        
        super().mousePressEvent(event)
    
    def change_edge_color(self):
        """修改单条连线的颜色"""
        from PyQt6.QtWidgets import QColorDialog
        
        current_color = QColor("#4A90E2")
        if self.canvas:
            current_color = QColor(self.canvas.edge_color)
        
        color = QColorDialog.getColor(current_color, None, "选择连线颜色")
        
        if color.isValid():
            # 创建自定义颜色的画笔
            pen = QPen(color, self.canvas.edge_width if self.canvas else 2.5)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            self.setPen(pen)
            
            # 更新箭头颜色
            if hasattr(self, 'arrow_item') and self.arrow_item:
                self.arrow_item.setBrush(color)
            
            logger.debug("连线颜色已更改为: %s", color.name())

    def update_path(self):
        """更新连线路径"""
        if not self.start_node or not self.end_node:
            return
        
        # 获取起点和终点的世界坐标（锚点中心）
        # 使用 sceneBoundingRect().center() 直接获取锚点的中心点场景坐标
        start_center = self.start_node.output_anchor.sceneBoundingRect().center()
        end_center = self.end_node.input_anchor.sceneBoundingRect().center()
        
        # 调试信息：锚点和状态指示灯的位置
        logger.debug("更新连线: %s -> %s", self.start_node.node_name, self.end_node.node_name)
        logger.debug("   输出锚点中心: (%.1f, %.1f)", start_center.x(), start_center.y())
        logger.debug("   输入锚点中心: (%.1f, %.1f)", end_center.x(), end_center.y())
        
        # 检查状态指示灯位置（用于对比）
        status_indicator_pos = self.start_node.status_indicator.scenePos()
        logger.debug("   状态指示灯 scenePos: (%.1f, %.1f)", status_indicator_pos.x(), status_indicator_pos.y())
        
        # 创建贝塞尔曲线路径
        path = QPainterPath()
        path.moveTo(start_center)
        
        # 计算控制点（使曲线更平滑）
        dx = abs(end_center.x() - start_center.x()) * 0.5
        ctrl1 = QPointF(start_center.x() + dx, start_center.y())
        ctrl2 = QPointF(end_center.x() - dx, end_center.y())
        
        path.cubicTo(ctrl1, ctrl2, end_center)
        self.setPath(path)
        
        # 添加箭头
        self.add_arrow(start_center, end_center)
        
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
