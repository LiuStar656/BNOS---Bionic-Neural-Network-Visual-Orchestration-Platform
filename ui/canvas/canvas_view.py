"""
节点画布 - VueFlow风格的无限画布（QGraphicsView + 自定义Item）
支持：无限画布、节点拖拽、锚点连线、贝塞尔曲线、缩放平移

【新增功能】画布中心坐标持久化：
- 自动保存当前窗口中心的画布坐标到 canvas_layout.json
- 下次打开项目时，自动恢复到上次的视野位置
- 触发时机：缩放、平移（滚轮/触控板/空格拖拽）后500ms自动保存
- 恢复逻辑：读取保存的中心坐标，调整滚动条使该坐标位于窗口中心

【交互优化】两阶段空格平移机制：
- 第一阶段：按住空格键 → 进入"空格快捷键模式"（光标变为手型）
- 第二阶段：在空格模式下按左键 → 进入"平移模式"（可拖拽画布）
- 释放顺序：先释放鼠标退出平移模式，再释放空格退出快捷键模式
- 优势：避免误触，提供更清晰的视觉反馈
"""
import os
import json
import math
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
    QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsTextItem,
    QMenu, QMessageBox, QGraphicsItem, QGraphicsPolygonItem, QGraphicsTextItem,
    QColorDialog
)
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont, QPainterPath,
    QPolygonF, QAction, QPixmap
)
from PyQt6.QtCore import QPointF

from ui.core.logger import logger
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.edge_item import EdgeItem
from ui.canvas.items.anchor_item import AnchorItem
from ui.canvas.canvas_colors import CanvasColorsMixin
from ui.canvas.canvas_layout import CanvasLayoutMixin
from ui.canvas.canvas_menus import CanvasMenusMixin

class NodeCanvas(CanvasMenusMixin, CanvasLayoutMixin, CanvasColorsMixin, QGraphicsView):
    """节点画布（VueFlow风格）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # ===== 画布场景尺寸配置 =====
        self.canvas_width = 5000   # 画布宽度（像素）
        self.canvas_height = 5000  # 画布高度（像素）
        
        # 创建场景（使用固定的初始大小）
        half_width = self.canvas_width // 2
        half_height = self.canvas_height // 2
        self.scene = QGraphicsScene(-half_width, -half_height, self.canvas_width, self.canvas_height, self)
        self.setScene(self.scene)
        
        # 设置视图属性
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)  # 右键拖拽平移
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        # 可视区域渲染优化：只更新变化区域，网格不限制
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.IndirectPainting, True)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)

        # 网格纹理缓存
        self._grid_texture = None
        self._grid_texture_key = None
        
        # ===== 颜色配置（支持自定义）— VSCode 深色主题 =====
        self.canvas_bg_color = '#1e1e1e'          # 画布背景（与标题栏统一）
        self.grid_color = '#2a2a2a'               # 网格线（极暗灰，若有若无）
        self.grid_opacity = 0.3                   # 网格透明度
        self.node_bg_color = '#2d2d30'            # 节点背景（略亮于画布）
        self.node_border_color = '#454545'        # 节点边框（微弱边框）
        self.node_text_color = '#d4d4d4'          # 节点文字（标准前景色）
        self.node_selected_color = '#007acc'      # 选中边框（VSCode 蓝）
        self.input_anchor_color = '#6a9955'       # 输入锚点（VSCode 绿）
        self.output_anchor_color = '#007acc'      # 输出锚点（VSCode 蓝）
        self.edge_color = '#007acc'               # 连线色（VSCode 蓝）
        self.edge_width = 2                       # 连线宽度
        
        # 应用背景色
        self.setBackgroundBrush(QColor(self.canvas_bg_color))
        
        # 网格背景（可选）
        self.draw_grid = True
        
        # 节点和连线存储
        self.nodes = {}  # {node_name: NodeItem}
        self.edges = []  # [EdgeItem]
        
        # 连线状态
        self.is_connecting = False
        self.connect_source = None
        self.temp_edge = None
        
        # 选中节点统一由 box_selected_nodes 管理（单选=列表仅1项）
        
        # 启用鼠标追踪
        self.setMouseTracking(True)
        
        # ===== 画布交互状态 =====
        self.is_pan_mode = False  # 平移模式（空格+左键拖拽）
        self.pan_start_pos = None  # 平移起始位置
        self.is_space_pressed = False  # 空格键按下状态
        self.space_mode_active = False  # 空格快捷键模式激活状态（按住空格后进入）
        # ✅ 新增：用于过滤操作系统键盘重复产生的虚假事件
        self._last_space_event_time = 0  # 上次空格事件的时间戳
        self._space_event_debounce_ms = 100  # 防抖时间（毫秒），小于此间隔的事件视为重复
        
        self.is_box_selecting = False  # 框选模式
        self.box_select_start_pos = None  # 框选起始位置
        self.box_select_rect = None  # 框选矩形项
        self.box_selected_nodes = []  # 框选中的节点列表
        
        # 自动保存定时器（防抖500ms）
        from PyQt6.QtCore import QTimer
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._auto_save_layout)

    def _build_grid_texture(self, tile_size=200):
        """预渲染网格纹理图块（一次性，后续平铺复用）"""
        grid = 20
        pix = QPixmap(tile_size, tile_size)
        pix.fill(QColor(self.canvas_bg_color))

        p = QPainter(pix)
        gc = QColor(self.grid_color)
        gc.setAlphaF(self.grid_opacity)
        p.setPen(QPen(gc, 0.5))

        for i in range(0, tile_size, grid):
            p.drawLine(i, 0, i, tile_size)
            p.drawLine(0, i, tile_size, i)
        p.end()
        return pix

    def drawBackground(self, painter, rect):
        """网格固定渲染：预烘焙纹理 → 平铺，不逐线重绘"""
        super().drawBackground(painter, rect)

        if not self.draw_grid:
            return

        # 缓存键：颜色+透明度变化时重建纹理
        cache_key = (self.grid_color, self.grid_opacity)
        if self._grid_texture is None or self._grid_texture_key != cache_key:
            self._grid_texture = self._build_grid_texture()
            self._grid_texture_key = cache_key

        tex = self._grid_texture
        tw, th = tex.width(), tex.height()

        # 计算可见场景区域的平铺范围
        vp = self.viewport()
        if not vp:
            return
        vr = self.mapToScene(vp.rect()).boundingRect()

        left = int(vr.left() // tw) * tw
        top = int(vr.top() // th) * th
        x, y = left, top
        while y < vr.bottom() + th:
            while x < vr.right() + tw:
                painter.drawPixmap(int(x), int(y), tex)
                x += tw
            x = left
            y += th
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 处理平移、框选和连线拖拽"""
        # 如果正在平移（空格+左键拖拽）
        if self.is_pan_mode and self.pan_start_pos:
            # 计算偏移量（使用 widget 坐标）
            delta = event.pos() - self.pan_start_pos
            
            # 直接移动滚动条
            h_scroll = self.horizontalScrollBar()
            v_scroll = self.verticalScrollBar()
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())
            
            # 更新起始位置
            self.pan_start_pos = event.pos()
            
            event.accept()
            return
        
        # 如果正在框选（左键长按拖拽）
        if self.is_box_selecting and self.box_select_rect and self.box_select_start_pos:
            # 使用 widget 坐标计算矩形
            current_pos = event.pos()
            
            # 创建 QRect（widget坐标）并规范化
            from PyQt6.QtCore import QRect
            widget_rect = QRect(self.box_select_start_pos, current_pos).normalized()
            
            # 将 widget 坐标转换为 scene 坐标
            top_left = self.mapToScene(widget_rect.topLeft())
            bottom_right = self.mapToScene(widget_rect.bottomRight())
            scene_rect = QRectF(top_left, bottom_right)
            
            self.box_select_rect.setRect(scene_rect)
            
            # 清空之前的选中列表，每次移动时重新计算
            self.box_selected_nodes = []
            
            # 检查哪些节点在框选区域内
            for node_name, node in self.nodes.items():
                node_rect = node.sceneBoundingRect()
                if scene_rect.intersects(node_rect):
                    node.setPen(QPen(QColor(self.node_selected_color), 3))
                    node.setSelected(True)
                    self.box_selected_nodes.append(node_name)
                else:
                    node.setPen(QPen(QColor(self.node_border_color), 2))
                    node.setSelected(False)
            
            event.accept()
            return
        
        # 如果正在连线中，更新临时连线的终点跟随鼠标
        if self.is_connecting and self.temp_edge and self.connect_source:
            scene_pos = self.mapToScene(event.position().toPoint())
            start_pos = self.connect_source.output_anchor.sceneBoundingRect().center()

            # 简单直线临时连线
            path = QPainterPath(start_pos)
            path.lineTo(scene_pos)

            self.temp_edge.setPath(path)
            self.viewport().update()
            event.accept()
            return
        
        # 默认处理（拖拽平移等）
        super().mouseMoveEvent(event)
    
    def wheelEvent(self, event):
        """滚轮事件 - Ctrl+滚轮缩放，触控板/滚轮平移"""
        # 检查是否按下Ctrl键
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+滚轮：放大缩小（保持原有行为）
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
        else:
            # ===== 触控板优化：支持双指平移 =====
            
            # 优先使用 pixelDelta（触控板提供像素级精度）
            pixel_delta = event.pixelDelta()
            if not pixel_delta.isNull():
                # 触控板事件：使用像素级滚动值，更平滑
                scroll_x = pixel_delta.x()
                scroll_y = pixel_delta.y()
            else:
                # 传统鼠标滚轮：使用角度增量（通常每格120）
                angle_delta = event.angleDelta()
                scroll_x = angle_delta.x()
                scroll_y = angle_delta.y()
            
            # 应用滚动（支持水平和垂直双向平移）
            h_scroll = self.horizontalScrollBar()
            v_scroll = self.verticalScrollBar()
            
            # 根据滚动类型调整灵敏度
            if not pixel_delta.isNull():
                # 触控板：直接使用像素值，保持1:1映射
                h_scroll.setValue(h_scroll.value() - scroll_x)
                v_scroll.setValue(v_scroll.value() - scroll_y)
            else:
                # 鼠标滚轮：可能需要调整系数（默认1:1）
                h_scroll.setValue(h_scroll.value() - scroll_x)
                v_scroll.setValue(v_scroll.value() - scroll_y)
            
            # 自动保存布局（包含视图状态）
            if self.parent_window and self.parent_window.current_project_path:
                self._save_timer.stop()
                self._save_timer.start(500)
            
            event.accept()
    
    def mousePressEvent(self, event):
        """鼠标按下事件 - 处理空格+左键平移、左键长按框选"""
        # 获取点击位置的项
        item = self.itemAt(event.position().toPoint())
        
        # ✅ 连线模式：点击锚点→完成连接，点击节点→完成连接，否则取消
        if self.is_connecting and event.button() == Qt.MouseButton.LeftButton:
            target_node = None
            probe = item
            while probe is not None:
                if isinstance(probe, NodeItem):
                    target_node = probe
                    break
                probe = probe.parentItem()
            if target_node and target_node != self.connect_source:
                self.complete_connection_to_input(target_node)
                logger.debug("连线完成到 %s", target_node.node_name)
                event.accept()
                return
            if not isinstance(item, AnchorItem):
                self.cancel_connection()
                logger.debug("取消连线")
                event.accept()
                return
        
        # 空格+左键：两阶段触发机制
        # 第一阶段：按住空格进入空格快捷键模式
        # 第二阶段：在空格模式下按左键进入平移模式
        if event.button() == Qt.MouseButton.LeftButton and self.space_mode_active:
            # ✅ 关键：检查点击目标
            # 如果点击的是节点、连线或锚点，不进入平移模式，让NodeItem自己处理Ctrl+Click多选
            if item is not None and (isinstance(item, NodeItem) or isinstance(item, EdgeItem) or isinstance(item, AnchorItem)):
                # 不调用 super()，直接返回，让子项处理
                logger.debug("点击了交互项，交给子项处理")
                return
            
            # 点击空白区域，进入平移模式（第二阶段）
            self.is_pan_mode = True
            # 使用 widget 坐标而不是 scene 坐标
            self.pan_start_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            
            # 临时禁用所有节点的移动标志，防止节点被拖动
            for node in self.nodes.values():
                node.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            
            logger.debug("进入平移模式（空格模式+左键）")
            event.accept()
            return
        
        # 左键：检查是否点击空白区域（准备框选）- 仅在未按空格时
        if event.button() == Qt.MouseButton.LeftButton and not self.is_space_pressed:
            # 沿 parentItem 链上溯，排除所有交互项及其子元素
            is_interactive = False
            probe = item
            while probe is not None:
                if isinstance(probe, (NodeItem, EdgeItem, AnchorItem)):
                    is_interactive = True
                    break
                probe = probe.parentItem()

            if not is_interactive:
                # 清除之前的选中状态并开始框选
                self.clear_box_selection()
                
                self.is_box_selecting = True
                self.box_select_start_pos = event.position().toPoint()
                
                from PyQt6.QtWidgets import QGraphicsRectItem
                self.box_select_rect = QGraphicsRectItem()
                self.box_select_rect.setPen(QPen(QColor("#2196F3"), 1.5, Qt.PenStyle.DashLine))
                self.box_select_rect.setBrush(QColor(33, 150, 243, 30))
                self.box_select_rect.setZValue(1)
                self.scene.addItem(self.box_select_rect)
                
                logger.debug("开始框选")
                event.accept()
                return

        # 其他情况：交给默认处理或子项处理
        super().mousePressEvent(event)
        return
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 结束平移或框选"""
        # 结束平移模式（第二阶段退出）
        if self.is_pan_mode and event.button() == Qt.MouseButton.LeftButton:
            self.is_pan_mode = False
            self.pan_start_pos = None
            
            # 如果空格键还按住，保持手型光标；否则恢复箭头
            if self.space_mode_active:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            
            # 恢复所有节点的移动标志
            for node in self.nodes.values():
                node.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            
            logger.debug("退出平移模式")
            
            # 自动保存布局（包含视图状态）
            if self.parent_window and self.parent_window.current_project_path:
                self._save_timer.stop()
                self._save_timer.start(500)
            
            event.accept()
            return
        
        # 结束框选模式
        if self.is_box_selecting and event.button() == Qt.MouseButton.LeftButton:
            self.is_box_selecting = False
            
            # 移除框选矩形
            if self.box_select_rect:
                self.scene.removeItem(self.box_select_rect)
                self.box_select_rect = None
            
            self.box_select_start_pos = None
            
            if self.box_selected_nodes:
                logger.debug("结束框选，选中 %d 个节点: %s", len(self.box_selected_nodes), self.box_selected_nodes)
            else:
                logger.debug("结束框选，未选中节点")
            
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件 - 双击节点打开配置对话框"""
        # 获取双击位置的项
        item = self.itemAt(event.position().toPoint())
        
        # 如果双击的是节点，打开配置对话框
        if isinstance(item, NodeItem):
            node_name = item.node_name
            logger.debug("双击节点: %s，打开配置对话框", node_name)
            
            # 调用打开配置的方法
            self.open_node_config(node_name)
            
            # 接受事件，阻止传播
            event.accept()
            return
        
        # 其他情况使用默认处理
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        """键盘按下事件 - 跟踪空格键状态"""
        if event.key() == Qt.Key.Key_Space:
            # ✅ 关键修复：使用Qt内置的isAutoRepeat()过滤系统自动重复事件
            if event.isAutoRepeat():
                # 这是Windows系统长按产生的自动重复事件，直接忽略
                event.accept()
                return
            
            # 首次按下空格（非自动重复），进入空格快捷键模式
            self.is_space_pressed = True
            self.space_mode_active = True
            logger.debug("进入空格快捷键模式")
            
            # 显示手型光标提示
            if not self.is_pan_mode:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            
            event.accept()
            return
        super().keyPressEvent(event)
    
    def keyReleaseEvent(self, event):
        """键盘释放事件 - 跟踪空格键状态"""
        if event.key() == Qt.Key.Key_Space:
            # ✅ 关键修复：使用Qt内置的isAutoRepeat()过滤虚假释放事件
            if event.isAutoRepeat():
                # 这是Windows系统产生的虚假release事件，直接忽略
                event.accept()
                return
            
            # 真正的释放（非自动重复）：退出空格快捷键模式
            self.is_space_pressed = False
            self.space_mode_active = False
            
            # 如果还在平移模式，强制退出
            if self.is_pan_mode:
                self.is_pan_mode = False
                self.pan_start_pos = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                
                # 恢复所有节点的移动标志
                for node in self.nodes.values():
                    node.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
                
                logger.debug("退出平移模式（空格键释放）")
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            
            logger.debug("退出空格快捷键模式")
            
            event.accept()
            return
        super().keyReleaseEvent(event)

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
        node.on_expand_requested = self.on_node_expand_requested  # 连接展开回调
        self.scene.addItem(node)
        self.nodes[node_name] = node  # 添加到nodes字典
        
        logger.info("节点 %s 已添加到画布 (位置: %d, %d)", node_name, x, y)
        
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
        
    # contextMenuEvent 已移至 CanvasMenusMixin（canvas_menus.py）

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
                    logger.info("已清除上游节点 %s 的监听配置", upstream_name)
                except Exception as e:
                    logger.info(f"❌ 保存配置失败: {e}")
        
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
                    logger.info("已清除下游节点 %s 的监听配置", downstream_name)
                except Exception as e:
                    logger.info(f"❌ 保存配置失败: {e}")
        
        # 5. 从画布中移除节点
        node = self.nodes[node_name]
        self.scene.removeItem(node)
        del self.nodes[node_name]
        
        logger.info("已从画布删除节点: %s", node_name)
        
        # 6. 自动保存布局
        if self.parent_window and self.parent_window.current_project_path:
            self._save_timer.stop()
            self._save_timer.start(500)
    
    def start_single_node(self, node_name):
        """启动单个节点（委托给父窗口）"""
        if self.parent_window:
            self.parent_window.start_selected_node_by_name(node_name)
    
    def stop_single_node(self, node_name):
        """停止单个节点（委托给父窗口）"""
        if self.parent_window:
            self.parent_window.stop_selected_node_by_name(node_name)
    
    def batch_start_selected_nodes(self):
        """批量启动选中的节点"""
        if not self.box_selected_nodes:
            return
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for node_name in self.box_selected_nodes[:]:  # 使用副本遍历
            if not self.parent_window or node_name not in self.parent_window.nodes_data:
                fail_count += 1
                continue
            
            node_info = self.parent_window.nodes_data[node_name]
            
            # 检查是否已在运行
            if node_info['status'] == 'running':
                skip_count += 1
                continue
            
            # 启动节点
            try:
                self.parent_window.start_selected_node_by_name(node_name)
                success_count += 1
            except Exception as e:
                logger.error("启动节点 %s 失败: %s", node_name, e)
                fail_count += 1
        
        # 显示结果
        result_msg = f"批量启动完成\n✅ 成功: {success_count}\n⏭️ 跳过: {skip_count}\n❌ 失败: {fail_count}"
        QMessageBox.information(self, "批量启动结果", result_msg)
        
        # 清除选择状态
        self.clear_box_selection()
    
    def batch_stop_selected_nodes(self):
        """批量停止选中的节点（仅停止正在运行的）"""
        if not self.box_selected_nodes:
            return
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for node_name in self.box_selected_nodes[:]:  # 使用副本遍历
            if not self.parent_window or node_name not in self.parent_window.nodes_data:
                fail_count += 1
                continue
            
            node_info = self.parent_window.nodes_data[node_name]
            
            # 检查是否在运行
            if node_info['status'] != 'running':
                skip_count += 1
                continue
            
            # 停止节点
            try:
                self.parent_window.stop_selected_node_by_name(node_name)
                success_count += 1
            except Exception as e:
                logger.error("停止节点 %s 失败: %s", node_name, e)
                fail_count += 1
        
        # 显示结果
        result_msg = f"批量停止完成\n✅ 成功: {success_count}\n⏭️ 跳过: {skip_count}\n❌ 失败: {fail_count}"
        QMessageBox.information(self, "批量停止结果", result_msg)
        
        # 清除选择状态
        self.clear_box_selection()
    
    def batch_remove_nodes_from_canvas(self):
        """批量从画布移除节点（不删除文件）"""
        if not self.box_selected_nodes:
            return
        
        count = len(self.box_selected_nodes)
        
        # 确认对话框，显示前10个节点名称
        preview_nodes = self.box_selected_nodes[:10]
        nodes_preview = "\n".join([f"  - {name}" for name in preview_nodes])
        if count > 10:
            nodes_preview += f"\n  ... 还有 {count - 10} 个节点"
        
        reply = QMessageBox.question(
            self, "确认从画布移除",
            f"确定要从画布中移除以下 {count} 个节点吗？\n\n"
            f"{nodes_preview}\n\n"
            f"注意：这只会从画布视图中移除节点显示和连线，\n"
            f"不会删除节点文件或配置文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        removed_count = 0
        for node_name in self.box_selected_nodes[:]:  # 使用副本遍历
            if node_name in self.nodes:
                # 仅从画布移除，不清理配置
                node = self.nodes[node_name]
                self.scene.removeItem(node)
                del self.nodes[node_name]
                removed_count += 1
                logger.info("已从画布移除节点: %s", node_name)
        
        # 清除所有相关连线
        edges_to_remove = []
        for edge in self.edges:
            source_name = None
            target_name = None
            for name, node_item in self.nodes.items():
                if node_item == edge.start_node:
                    source_name = name
                if node_item == edge.end_node:
                    target_name = name
            
            # 如果连线的任一端是被移除的节点，则删除该连线
            if source_name not in self.nodes or target_name not in self.nodes:
                edges_to_remove.append(edge)
        
        for edge in edges_to_remove:
            self.remove_edge(edge)
        
        logger.info("已从画布移除 %d 个节点", removed_count)
        
        # 清除选择状态
        self.clear_box_selection()
        
        # 自动保存布局
        if self.parent_window and self.parent_window.current_project_path:
            self._save_timer.stop()
            self._save_timer.start(500)
    
    def batch_clear_listen_config(self):
        """批量清除选中节点的 listen_upper_file 配置及画布连线"""
        if not self.box_selected_nodes:
            return
        
        cleared_count = 0
        for node_name in self.box_selected_nodes[:]:
            if self.parent_window and node_name in self.parent_window.nodes_data:
                node_info = self.parent_window.nodes_data[node_name]
                config = node_info['config']
                
                if config.get('listen_upper_file'):
                    config['listen_upper_file'] = ""
                    
                    config_path = os.path.join(node_info['path'], "config.json")
                    try:
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                        cleared_count += 1
                        logger.info("已清除节点 %s 的监听配置", node_name)
                    except Exception as e:
                        logger.info(f"❌ 保存配置失败: {e}")
        
        # 清除这些节点的所有输入连线
        edges_to_remove = []
        for edge in self.edges:
            target_name = None
            for name, node_item in self.nodes.items():
                if node_item == edge.end_node:
                    target_name = name
                    break
            
            if target_name in self.box_selected_nodes:
                edges_to_remove.append(edge)
        
        for edge in edges_to_remove:
            self.remove_edge(edge)
        
        QMessageBox.information(self, "清除配置完成", f"已清除 {cleared_count} 个节点的监听配置")
        
        # 清除选择状态
        self.clear_box_selection()
        
        # 自动保存布局
        if self.parent_window and self.parent_window.current_project_path:
            self._save_timer.stop()
            self._save_timer.start(500)
    
    def open_node_config(self, node_name):
        """打开节点配置对话框"""
        if self.parent_window and node_name in self.parent_window.nodes_data:
            node_info = self.parent_window.nodes_data[node_name]
            config = node_info['config']
            node_path = node_info['path']
            
            from ui.panels.property_panel import NodeConfigDialog
            dialog = NodeConfigDialog(node_name, config, node_path, self.parent_window)
            dialog.exec()
    
    def on_node_expand_requested(self, node_name):
        """节点展开按钮回调 — 以节点中心为基准展开浮动面板"""
        from ui.panels.node_expand_panel import NodeExpandPanel

        # 如果同节点已有展开面板，关闭旧的
        if hasattr(self, '_expand_panel') and self._expand_panel is not None:
            try:
                if self._expand_panel.isVisible() and self._expand_panel.node_name == node_name:
                    self._expand_panel._close()
            except RuntimeError:
                pass  # 面板已被销毁

        # 窗口中心与节点中心重合
        if node_name in self.nodes:
            node = self.nodes[node_name]
            scene_pos = node.pos() + node.rect().center()
            view_pos = self.mapFromScene(scene_pos)
            global_pos = self.viewport().mapToGlobal(view_pos)
            panel_w, panel_h = 620, 380  # 与 NodeExpandPanel.__init__ 一致
            x = global_pos.x() - panel_w // 2
            y = global_pos.y() - panel_h // 2
        else:
            x, y = 300, 200

        panel = NodeExpandPanel(node_name, self.parent_window)
        panel.move(x, y)
        panel.show()
        self._expand_panel = panel
    
    def reset_view(self):
        """重置视图到默认状态"""
        self.resetTransform()
        self.centerOn(0, 0)
        logger.info("✅ 视图已重置")
    
    # ===== 颜色设置方法 =====
    
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
        elif os.path.exists(os.path.join(node_path, "src", "main.rs")) or os.path.exists(os.path.join(node_path, "Cargo.toml")):
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
        """普通单击选中节点（单选，清除之前的多选）"""
        # 如果点击的节点已在多选列表中，只取消其他节点的Qt选中,保留此节点可拖动
        if node.node_name in self.box_selected_nodes:
            # 确保它是唯一被Qt选中的项，支持拖动
            for name in self.box_selected_nodes:
                if name in self.nodes:
                    self.nodes[name].setSelected(name == node.node_name)
            return
        
        # 清除之前所有选中节点
        for name in self.box_selected_nodes:
            if name in self.nodes:
                self.nodes[name].setPen(QPen(QColor(self.node_border_color), 2))
                self.nodes[name].setSelected(False)
        self.box_selected_nodes = []
        
        # 选中当前节点
        self.box_selected_nodes.append(node.node_name)
        node.setPen(QPen(QColor(self.node_selected_color), 3))
        node.setSelected(True)
        logger.info("选中节点: %s", node.node_name)
    
    def _toggle_node_selection(self, node_name):
        """切换节点选中状态（用于Ctrl+单击多选）"""
        if node_name not in self.nodes:
            return
        
        node = self.nodes[node_name]
        
        if node_name in self.box_selected_nodes:
            self.box_selected_nodes.remove(node_name)
            node.setPen(QPen(QColor(self.node_border_color), 2))
            node.setSelected(False)
            logger.debug("取消选中节点: %s", node_name)
        else:
            self.box_selected_nodes.append(node_name)
            node.setPen(QPen(QColor(self.node_selected_color), 3))
            node.setSelected(True)
            logger.info("选中节点: %s (共%d个)", node_name, len(self.box_selected_nodes))
    
    def get_selected_node(self):
        """获取当前选中的节点名称（单选优先取第一个）"""
        return self.box_selected_nodes[0] if self.box_selected_nodes else None
    
    def clear_selection(self):
        """清除节点选择"""
        self.clear_box_selection()
    
    def clear_box_selection(self):
        """清除框选状态"""
        # 移除框选矩形
        if self.box_select_rect:
            self.scene.removeItem(self.box_select_rect)
            self.box_select_rect = None
        
        # 恢复所有节点的边框颜色并取消Qt选中
        for node_name, node in self.nodes.items():
            node.setPen(QPen(QColor(self.node_border_color), 2))
            node.setSelected(False)
        
        # 清空选中列表
        self.box_selected_nodes = []
        self.is_box_selecting = False
        self.box_select_start_pos = None
                    
    def _start_connection_by_name(self, node_name):
        """按节点名称开始连线（供右键菜单调用）"""
        if node_name not in self.nodes:
            return
        self.start_connection_from_output(self.nodes[node_name])
    
    def start_connection_from_output(self, source_node):
        """从输出锚点开始连线"""
        self.is_connecting = True
        self.connect_source = source_node
        
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        
        self.temp_edge = QGraphicsPathItem()
        self.temp_edge.setZValue(2)  # 浮于网格+节点之上
        pen = QPen(QColor("#4A90E2"), 2, Qt.PenStyle.DashLine)
        self.temp_edge.setPen(pen)
        self.scene.addItem(self.temp_edge)

        # 初始直线临时连线
        cursor_pos = self.mapFromGlobal(self.cursor().pos())
        scene_pos = self.mapToScene(cursor_pos)
        start = source_node.output_anchor.sceneBoundingRect().center()

        path = QPainterPath()
        path.moveTo(start)
        path.lineTo(scene_pos)
        self.temp_edge.setPath(path)
        
    def complete_connection_to_input(self, target_node):
        """完成连线到输入锚点"""
        if self.connect_source and self.connect_source != target_node:
            self.create_edge(self.connect_source, target_node)
        
        if self.temp_edge:
            self.scene.removeItem(self.temp_edge)
            self.temp_edge = None
        
        self.is_connecting = False
        self.connect_source = None
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
    
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
                
                logger.info("已配置 %s 监听 %s 的输出", target_name, source_name)
                logger.debug("   listen_upper_file: %s", source_output_path)
            except Exception as e:
                logger.info(f"❌ 保存配置失败: {e}")
        
        # 创建连线条（此时不会自动更新路径）
        edge = EdgeItem(source_node, target_node, self)
        
        # 先添加到场景
        self.scene.addItem(edge)
        self.edges.append(edge)
        
        # 添加到场景后再更新路径和箭头
        edge.update_path()
        
        logger.info("创建连线: %s -> %s", source_name, target_name)
        
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
                    logger.info("已清空 %s 的监听配置", target_name)
                except Exception as e:
                    logger.info(f"❌ 保存配置失败: {e}")
            
            # 从场景中移除
            edge.remove_from_scene()
            self.edges.remove(edge)
            
            # 自动保存布局（防抖500ms）
            if self.parent_window and self.parent_window.current_project_path:
                self._save_timer.stop()
                self._save_timer.start(500)

    def complete_connection_to_input(self, target_node):
        """完成连线到输入锚点"""
        if self.connect_source and self.connect_source != target_node:
            self.create_edge(self.connect_source, target_node)
        
        if self.temp_edge:
            self.scene.removeItem(self.temp_edge)
            self.temp_edge = None
        
        self.is_connecting = False
        self.connect_source = None
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
    
    def cancel_connection(self):
        """取消连线"""
        if self.temp_edge:
            self.scene.removeItem(self.temp_edge)
            self.temp_edge = None
        
        self.is_connecting = False
        self.connect_source = None
        self.viewport().setCursor(Qt.CursorShape.ArrowCursor)

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
            
        logger.info("画布已清空")

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
            
            logger.info("画布节点已重命名: %s -> %s", old_name, new_name)

    # save_layout / load_layout 已移至 CanvasLayoutMixin（canvas_layout.py）

    def _auto_save_layout(self):
        """自动保存布局（防抖）"""
        if self.parent_window and self.parent_window.current_project_path:
            self.save_layout(self.parent_window.current_project_path)
    
    # apply_color_settings 等颜色方法已移至 CanvasColorsMixin（canvas_colors.py）
