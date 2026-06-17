"""
节点画布 - VueFlow 风格的无限画布（QGraphicsView + 组合模式）

架构说明（按目录组织）：
- canvas_view.py（本文件）：NodeCanvas 主类，负责组合装配与 Qt 事件转发
- mixins/：7 个 Mixin（connections / box_select / batch_ops / menus / layout / colors
           以及 4 个组合层 selection / background_renderer / node_manager / event_handlers）
           与 controllers.py（控制器组合层）
- drawing/：绘图层（draw_layer / draw_toolbar / graphic_items）
- items/：纯 UI 渲染组件（node_item / edge_item / anchor_item 等）
- parameter_widgets/：参数编辑控件

组合层使用方式：
    self = NodeCanvas(parent)
    self.events.mousePressEvent(event)                 # 事件处理
    self.background.drawBackground(painter, rect)      # 背景渲染
    self.node_mgr.add_node_to_canvas(name)             # 节点管理
    self.selection.on_node_selected(node)              # 选择管理

旧有 Mixin 仍保留（因为 CanvasBoxSelectMixin 等有大量代码），但新增的功能都通过组合层实现。
"""
import os
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsItem,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter

from ui.core.logger import logger
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.edge_item import EdgeItem
from ui.canvas.items.anchor_item import AnchorItem
from ui.canvas.mixins.canvas_colors import CanvasColorsMixin
from ui.canvas.mixins.canvas_layout import CanvasLayoutMixin
from ui.canvas.mixins.canvas_menus import CanvasMenusMixin

from ui.canvas.mixins.canvas_connections import CanvasConnectionsMixin
from ui.canvas.mixins.canvas_box_select import CanvasBoxSelectMixin
from ui.canvas.mixins.canvas_batch_ops import CanvasBatchOpsMixin
from ui.canvas.drawing.draw_layer import DrawLayer

# 拆分出的组合层模块
from ui.canvas.mixins.canvas_selection import SelectionManager
from ui.canvas.mixins.canvas_background_renderer import BackgroundRenderer
from ui.canvas.mixins.canvas_node_manager import NodeManager
from ui.canvas.mixins.canvas_event_handlers import EventHandlers


class NodeCanvas(
    CanvasConnectionsMixin,
    CanvasBatchOpsMixin,
    CanvasBoxSelectMixin,
    CanvasMenusMixin,
    CanvasLayoutMixin,
    CanvasColorsMixin,
    QGraphicsView,
):
    """节点画布（VueFlow 风格）

    核心思想：组合优于继承。
    大功能模块由独立类（SelectionManager / BackgroundRenderer / NodeManager / EventHandlers）
    实现，NodeCanvas 只负责装配和 Qt 虚函数转发。
    """

    # ── 初始化 ──

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # ===== 画布场景尺寸 =====
        self.canvas_width = 5000
        self.canvas_height = 5000

        # 创建场景
        half_width = self.canvas_width // 2
        half_height = self.canvas_height // 2
        self.scene = QGraphicsScene(-half_width, -half_height, self.canvas_width, self.canvas_height, self)
        self.setScene(self.scene)

        # 设置视图属性
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)

        # ===== 颜色配置 =====
        self.canvas_bg_color = "#1e1e1e"
        self.grid_color = "#2a2a2a"
        self.grid_opacity = 0.3
        self.node_bg_color = "#2d2d30"
        self.node_border_color = "#454545"
        self.node_text_color = "#d4d4d4"
        self.node_selected_color = "#007acc"
        self.input_anchor_color = "#6a9955"
        self.output_anchor_color = "#007acc"
        self.edge_color = "#007acc"
        self.edge_width = 2

        # 应用背景色
        from PySide6.QtGui import QColor

        self.setBackgroundBrush(QColor(self.canvas_bg_color))
        self.resetCachedContent()
        vp = self.viewport()
        vp.setAutoFillBackground(False)
        vp.setStyleSheet("background: transparent;")
        vp.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        # 节点与连线存储
        self.nodes = {}
        self.edges = []

        # 绘图层（独立模块，已有实现）
        self.draw_layer = DrawLayer(self)
        self._draw_toolbar = self.draw_layer.attach_toolbar()
        self._draw_property_panel = self.draw_layer.attach_property_panel()

        # 连线状态（事件处理器用到）
        self.is_connecting = False
        self.connect_source = None
        self.temp_edge = None

        # ===== 画布交互状态 =====
        self.is_pan_mode = False
        self.pan_start_pos = None
        self.is_space_pressed = False
        self.space_mode_active = False
        self._last_space_event_time = 0
        self._space_event_debounce_ms = 100

        self.is_box_selecting = False
        self.box_select_start_pos = None
        self.box_select_rect = None
        self.box_selected_nodes = []

        # 自动保存定时器（防抖）
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._auto_save_layout)

        # ===== 组合层初始化（核心拆分点） =====
        self._init_controllers()

        # 组合层：选择管理 + 命令录制
        self.selection = SelectionManager(self)

        # 组合层：背景与网格渲染
        self.background = BackgroundRenderer(self)

        # 组合层：节点管理（增删改 + 状态同步 + 面板 + 委托）
        self.node_mgr = NodeManager(self)

        # 组合层：事件处理（鼠标 / 键盘 / 滚轮 / 窗口）
        self.events = EventHandlers(self)

        # 从 app_config 加载绘图工具栏显示状态
        self.events._load_draw_toolbar_config()

        logger.info("NodeCanvas 已初始化（组合模式：选择/背景/节点/事件）")

    def _init_controllers(self):
        """初始化控制器组合层（与旧逻辑保持一致）"""
        from ui.canvas.mixins.controllers import (
            CanvasConnectionController,
            CanvasBatchOperations,
            BoxSelectionController,
            CanvasMenuController,
            CanvasLayoutController,
            CanvasColorController,
            CanvasZoomController,
        )

        self.connections = CanvasConnectionController(self)
        self.batch_ops = CanvasBatchOperations(self)
        self.box_select = BoxSelectionController(self)
        self.menus = CanvasMenuController(self)
        self.layout_ctrl = CanvasLayoutController(self)
        self.colors = CanvasColorController(self)
        self.zoom_ctrl = CanvasZoomController(self)
        logger.info("Canvas 控制器组合层已激活（7 个控制器，委托模式）")

    # ── Qt 虚函数重写（转发给对应组合层） ──

    def drawBackground(self, painter, rect):
        """背景绘制 → 转发给 BackgroundRenderer"""
        self.background.drawBackground(painter, rect)

    def mouseMoveEvent(self, event):
        """鼠标移动 → 转发给 EventHandlers"""
        self.events.mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """鼠标按下 → 转发给 EventHandlers"""
        self.events.mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放 → 转发给 EventHandlers"""
        self.events.mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """鼠标双击 → 转发给 EventHandlers"""
        self.events.mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        """键盘按下 → 转发给 EventHandlers"""
        self.events.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """键盘释放 → 转发给 EventHandlers"""
        self.events.keyReleaseEvent(event)

    def wheelEvent(self, event):
        """滚轮 → 转发给 EventHandlers"""
        self.events.wheelEvent(event)

    def resizeEvent(self, event):
        """窗口大小改变 → 转发给 EventHandlers"""
        self.events.resizeEvent(event)

    # ── 节点管理（转发给 NodeManager） ──

    def add_node_to_canvas(self, node_name, node_info=None):
        self.node_mgr.add_node_to_canvas(node_name, node_info)

    def remove_node_from_canvas(self, node_name):
        self.node_mgr.remove_node_from_canvas(node_name)

    def remove_node_with_cleanup(self, node_name):
        self.node_mgr.remove_node_with_cleanup(node_name)

    def rename_node_in_canvas(self, old_name, new_name):
        self.node_mgr.rename_node_in_canvas(old_name, new_name)

    def clear_canvas(self):
        self.node_mgr.clear_canvas()

    def update_node_status(self, node_name, status):
        self.node_mgr.update_node_status(node_name, status)

    def detect_language(self, node_path):
        return self.node_mgr.detect_language(node_path)

    def sync_node_display(self, node_name):
        self.node_mgr.sync_node_display(node_name)

    def sync_all_nodes_display(self):
        self.node_mgr.sync_all_nodes_display()

    def start_single_node(self, node_name):
        self.node_mgr.start_single_node(node_name)

    def stop_single_node(self, node_name):
        self.node_mgr.stop_single_node(node_name)

    def export_node_from_canvas(self, node_name):
        self.node_mgr.export_node_from_canvas(node_name)

    def stop_all_nodes(self):
        self.node_mgr.stop_all_nodes()

    def open_node_config(self, node_name):
        self.node_mgr.open_node_config(node_name)

    def on_node_expand_requested(self, node_name):
        self.node_mgr.on_node_expand_requested(node_name)

    # ── 选择管理（转发给 SelectionManager） ──

    def on_node_selected(self, node):
        self.selection.on_node_selected(node)

    def _toggle_node_selection(self, node_name):
        self.selection._toggle_node_selection(node_name)

    def get_selected_node(self):
        return self.selection.get_selected_node()

    def clear_selection(self):
        self.selection.clear_selection()

    # ── 命令录制（转发给 SelectionManager，保持向后兼容的方法名） ──

    def _begin_replay(self):
        self.selection._begin_replay()

    def _end_replay(self):
        self.selection._end_replay()

    @property
    def _is_replaying(self) -> bool:
        return self.selection._is_replaying

    def _record_create_node(self, node_name: str):
        self.selection._record_create_node(node_name)

    def _record_delete_node(self, node_name: str):
        self.selection._record_delete_node(node_name)

    def _record_create_edge(self, src_name: str, tgt_name: str):
        self.selection._record_create_edge(src_name, tgt_name)

    def _record_delete_edge(self, src_name: str, tgt_name: str,
                            target_port_name=None, source_port_name=None):
        self.selection._record_delete_edge(
            src_name, tgt_name, target_port_name, source_port_name
        )

    # ── 视图与绘图工具栏（转发给 EventHandlers） ──

    def reset_view(self):
        self.events.reset_view()

    def _toggle_draw_toolbar(self):
        self.events._toggle_draw_toolbar()

    def _auto_save_layout(self):
        self.events._auto_save_layout()

    # contextMenuEvent 已移至 CanvasMenusMixin（canvas_menus.py）
    # save_layout / load_layout 已移至 CanvasLayoutMixin（canvas_layout.py）
    # apply_color_settings 等颜色方法已移至 CanvasColorsMixin（canvas_colors.py）
