"""
节点项（对应VueFlow节点）
继承自 QGraphicsRectItem，负责节点的视觉渲染、锚点管理和交互处理
"""
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsItem
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPen, QColor, QBrush, QFont
from ui.core.logger import logger

from ui.canvas.items.anchor_item import AnchorItem


class NodeItem(QGraphicsRectItem):
    """节点项（对应VueFlow节点）"""

    # QGraphicsRectItem 不继承 QObject，使用回调代替信号
    on_expand_requested = None  # 类型: Callable[[str], None]
    
    def __init__(self, node_name, language="Python", status="stopped", x=0, y=0, w=140, h=80, canvas=None):
        super().__init__(x, y, w, h, None)  # parent为None
        self.node_name = node_name
        self.language = language
        self.status = status
        self.canvas = canvas  # 引用画布对象
        
        # 可视区域渲染：节点缓存，只渲染视口内可见节点
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        
        # 设置可移动和可选中
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        
        # 样式（使用画布的颜色配置）
        if canvas:
            self.setBrush(QBrush(QColor(canvas.node_bg_color)))
            self.setPen(QPen(QColor(canvas.node_border_color), 2))
        else:
            self.setBrush(QBrush(QColor("#f8f9fa")))
            self.setPen(QPen(QColor("#dee2e6"), 2))
        self.setZValue(1)
        
        # 加载节点的自定义颜色（如果有）
        self._load_node_custom_colors()
        
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
        text_color = QColor(canvas.node_text_color) if canvas else QColor("#333")
        self.name_text.setDefaultTextColor(text_color)
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

        # 展开按钮（右上角，14x14 小方块 + ">>" 文字）
        expand_x = w - 20
        expand_y = 4
        self._expand_btn = QGraphicsRectItem(expand_x, expand_y, 14, 14, self)
        self._expand_btn.setBrush(QBrush(QColor("#555555")))
        self._expand_btn.setPen(QPen(QColor("#444444"), 1))
        self._expand_btn.setZValue(2)
        self._expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # 标记，用于 mousePressEvent 中识别
        self._expand_btn_rect = QRectF(expand_x, expand_y, 14, 14)

        self._expand_label = QGraphicsTextItem(">>", self)
        self._expand_label.setDefaultTextColor(QColor("#cccccc"))
        font_tiny2 = QFont("Arial", 7, QFont.Weight.Bold)
        self._expand_label.setFont(font_tiny2)
        self._expand_label.setPos(expand_x - 1, expand_y - 1)
        self._expand_label.setZValue(3)
        
    def update_status(self, status):
        """更新节点状态"""
        self.status = status
        # 启动时为红色，关闭时为绿色
        color = QColor("#FF0000") if status == "running" else QColor("#00FF00")
        self.status_indicator.setBrush(QBrush(color))
        
        # 添加边框以增强可见性
        border_color = QColor("#CC0000") if status == "running" else QColor("#00CC00")
        self.status_indicator.setPen(QPen(border_color, 1.5))
    
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

            # 检查是否点击了展开按钮（右上角）
            if self._expand_btn_rect.contains(pos_in_item):
                if self.on_expand_requested:
                    self.on_expand_requested(self.node_name)
                event.accept()
                return

            # 检查是否点击了输出锚点（开始连线）
            # 输出锚点在右侧中间，现在是16x16，中心点在(w-8, h/2)
            w = self.rect().width()
            h = self.rect().height()
            output_anchor_rect = QRectF(w - 8, h/2 - 8, 16, 16)
            
            if output_anchor_rect.contains(pos_in_item):
                if self.canvas:
                    self.canvas.start_connection_from_output(self)
                    logger.debug("开始从 %s 的输出锚点连线", self.node_name)
                return  # 不继续处理，避免触发拖拽
            
            # 检查是否点击了输入锚点（左侧中间）
            input_anchor_rect = QRectF(-8, h/2 - 8, 16, 16)
            if input_anchor_rect.contains(pos_in_item):
                # 如果正在连线中，完成连线
                if self.canvas and self.canvas.is_connecting:
                    self.canvas.complete_connection_to_input(self)
                    logger.debug("完成到 %s 的输入锚点连线", self.node_name)
                return
            
            # ✅ 检测Ctrl+左键：切换节点选中状态（多选）
            if (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and self.canvas:
                self.canvas._toggle_node_selection(self.node_name)
                event.accept()
                return  # ✅ 关键：立即返回，不调用 super()，防止事件传播到父项
            
            # 其他区域：正常拖拽和选中
            if self.canvas:
                self.canvas.on_node_selected(self)
        
        super().mousePressEvent(event)
