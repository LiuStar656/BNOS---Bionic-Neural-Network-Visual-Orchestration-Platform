"""
节点画布 - VueFlow 风格的无限画布（QGraphicsView + 组合模式）

架构说明（按目录组织）：
- canvas_view.py（本文件）：NodeCanvas 主类，负责装配与 Qt 事件转发
- mixins/：11 个组合层模块
  - connections.py            连线生命周期
  - batch_ops.py              批量启动/停止/移除
  - box_select.py             选择状态管理（合并到 SelectionManager）
  - menus.py                  右键菜单（Action 系统）
  - layout.py                 布局保存/加载
  - colors.py                 颜色设置
  - selection.py              选择管理（SelectionManager，含 box_selected_nodes 等）
  - background_renderer.py    背景与网格渲染
  - node_manager.py           节点增删改（NodeManager）
  - event_handlers.py         鼠标/键盘/滚轮/窗口事件
  - controllers.py            （遗留）不再使用
- drawing/：绘图层（draw_layer / draw_toolbar / graphic_items）
- items/：纯 UI 渲染组件（node_item / edge_item / anchor_item 等）
- parameter_widgets/：参数编辑控件

组合层使用方式：
    canvas = NodeCanvas(parent)
    canvas.events.mousePressEvent(event)         # 事件处理
    canvas.background.drawBackground(painter, rect)  # 背景渲染
    canvas.node_mgr.add_node_to_canvas(name)     # 节点管理
    canvas.selection.on_node_selected(node)      # 选择管理
    canvas.connections.start_connection_from_output(node, anchor)  # 连线
    canvas.menus.contextMenuEvent(event)         # 右键菜单
    canvas.layout_mgr.save_layout(path)          # 保存布局
"""
import os
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPainter

from ui.core.logger import logger
from ui.canvas.drawing.draw_layer import DrawLayer

# 4 个原有的组合层模块
from ui.canvas.mixins.canvas_selection import SelectionManager
from ui.canvas.mixins.canvas_background_renderer import BackgroundRenderer
from ui.canvas.mixins.canvas_node_manager import NodeManager
from ui.canvas.mixins.canvas_event_handlers import EventHandlers

# 6 个原 mixin 已重构为组合类
# (NodeCanvas.__init__ 中实例化，不再通过继承混入)
from ui.canvas.mixins.canvas_connections import CanvasConnections
from ui.canvas.mixins.canvas_batch_ops import CanvasBatchOps
from ui.canvas.mixins.canvas_menus import CanvasMenu
from ui.canvas.mixins.canvas_layout import CanvasLayout
from ui.canvas.mixins.canvas_colors import CanvasColors
from ui.canvas.mixins.canvas_box_select import CanvasBoxSelect


class NodeCanvas(QGraphicsView):
    """节点画布（VueFlow 风格）

    核心原则：组合优于继承。
    每个功能域由独立组合类负责，NodeCanvas 仅：
      1. 装配各组件（在 __init__ 中实例化）
      2. 暴露对外 API（转发到对应组合对象）
      3. 转发 Qt 虚函数事件
    """

    # ── 初始化 ──

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # ===== 画布场景尺寸 =====
        self.canvas_width = 5000
        self.canvas_height = 5000

        # ===== 场景与视图设置 =====
        from PySide6.QtWidgets import QGraphicsScene
        from PySide6.QtCore import Qt
        half_width = self.canvas_width // 2
        half_height = self.canvas_height // 2
        self.scene = QGraphicsScene(-half_width, -half_height, self.canvas_width, self.canvas_height, self)
        self.setScene(self.scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)

        # ===== 颜色配置（供各组合层读取） =====
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

        # ===== 数据存储层 =====
        self.nodes = {}   # name -> NodeItem（QGraphicsItem）
        self.edges = []   # EdgeItem 列表

        # ===== 绘图层（独立子系统） =====
        self.draw_layer = DrawLayer(self)
        self._draw_toolbar = self.draw_layer.attach_toolbar()
        self._draw_property_panel = self.draw_layer.attach_property_panel()

        # ===== 连线状态（事件处理器需要） =====
        # 由 CanvasConnections 管理，但保留在 canvas 上以便事件层访问
        self.is_connecting = False
        self.connect_source = None
        self._connect_source_anchor = None
        self.temp_edge = None

        # ===== 框选状态（由 CanvasBoxSelect/SelectionManager 管理）=====
        self.box_select_rect = None
        self.box_selected_nodes = []
        self.is_box_selecting = False
        self.box_select_start_pos = None

        # ===== 交互状态（事件处理器使用） =====
        self.is_pan_mode = False
        self.pan_start_pos = None
        self.is_space_pressed = False
        self.space_mode_active = False
        self._last_space_event_time = 0
        self._space_event_debounce_ms = 100

        # ===== 自动保存定时器（防抖） =====
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._auto_save_layout)

        # ===== 组合层装配（按依赖顺序） =====
        # 1. 选择管理（管理 box_selected_nodes 等状态）
        self.selection = SelectionManager(self)
        # 2. 背景渲染
        self.background = BackgroundRenderer(self)
        # 3. 节点管理
        self.node_mgr = NodeManager(self)
        # 4. 颜色管理
        self.colors = CanvasColors(self)
        # 5. 连线管理（需要访问 nodes/edges/scene）
        self.connections = CanvasConnections(self)
        # 6. 布局持久化（需要访问 nodes/edges）
        self.layout_mgr = CanvasLayout(self)
        # 7. 批量操作（需要访问 selection/parent_window）
        self.batch_ops = CanvasBatchOps(self)
        # 8. 框选状态清（轻量，与 SelectionManager 协作）
        self.box_select = CanvasBoxSelect(self)
        # 9. 右键菜单（需要访问 selection/connections）
        self.menus = CanvasMenu(self)
        # 10. 事件处理（最后创建，依赖所有以上）
        self.events = EventHandlers(self)

        # 从 app_config 加载绘图工具栏显示状态
        self.events._load_draw_toolbar_config()

        logger.info("NodeCanvas 已初始化（组合模式：10 个组件，无 mixin 继承）")

    # ── Qt 虚函数重写（转发给对应组合层） ──

    def drawBackground(self, painter, rect):
        """背景绘制 → BackgroundRenderer"""
        self.background.drawBackground(painter, rect)

    def mouseMoveEvent(self, event):
        """鼠标移动 → EventHandlers"""
        self.events.mouseMoveEvent(event)

    def mousePressEvent(self, event):
        """鼠标按下 → EventHandlers"""
        self.events.mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放 → EventHandlers"""
        self.events.mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """鼠标双击 → EventHandlers"""
        self.events.mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        """键盘按下 → EventHandlers"""
        self.events.keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """键盘释放 → EventHandlers"""
        self.events.keyReleaseEvent(event)

    def wheelEvent(self, event):
        """滚轮 → EventHandlers"""
        self.events.wheelEvent(event)

    def resizeEvent(self, event):
        """窗口大小改变 → EventHandlers"""
        self.events.resizeEvent(event)

    def contextMenuEvent(self, event):
        """右键菜单 → CanvasMenu"""
        self.menus.contextMenuEvent(event)

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

    # ── 框选（转发给 CanvasBoxSelect） ──

    def clear_box_selection(self):
        self.box_select.clear_box_selection()

    # ── 连线管理（转发给 CanvasConnections） ──

    def _start_connection_by_name(self, node_name):
        self.connections._start_connection_by_name(node_name)

    def start_connection_from_output(self, source_node, source_anchor=None):
        self.connections.start_connection_from_output(source_node, source_anchor)

    def complete_connection_to_input(self, target_node, clicked_anchor=None):
        self.connections.complete_connection_to_input(target_node, clicked_anchor)

    def create_edge(self, source_node, target_node, target_anchor=None, source_anchor=None):
        return self.connections.create_edge(source_node, target_node, target_anchor, source_anchor)

    def remove_edge(self, edge):
        self.connections.remove_edge(edge)

    def cancel_connection(self):
        self.connections.cancel_connection()

    def clear_edges(self):
        self.connections.clear_edges()

    # ── 批量操作（转发给 CanvasBatchOps） ──

    def batch_start_selected_nodes(self):
        self.batch_ops.batch_start_selected_nodes()

    def batch_stop_selected_nodes(self):
        self.batch_ops.batch_stop_selected_nodes()

    def batch_remove_nodes_from_canvas(self):
        self.batch_ops.batch_remove_nodes_from_canvas()

    def batch_clear_listen_config(self):
        self.batch_ops.batch_clear_listen_config()

    # ── 布局保存/加载（转发给 CanvasLayout） ──

    def save_layout(self, project_path=None):
        self.layout_mgr.save_layout(project_path)

    def load_layout(self, project_path=None):
        self.layout_mgr.load_layout(project_path)

    def save_center_coordinates(self):
        self.layout_mgr.save_center_coordinates()

    # ── 颜色设置（转发给 CanvasColors） ──

    def change_canvas_background_color(self):
        self.colors.change_canvas_background_color()

    def change_grid_color(self):
        self.colors.change_grid_color()

    def change_edge_color(self):
        self.colors.change_edge_color()

    def change_node_background_color(self, node_item):
        self.colors.change_node_background_color(node_item)

    def change_node_border_color(self, node_item):
        self.colors.change_node_border_color(node_item)

    def change_node_text_color(self, node_item):
        self.colors.change_node_text_color(node_item)

    def apply_color_settings(self, settings):
        self.colors.apply_color_settings(settings)

    def _save_color_settings(self):
        self.colors._save_color_settings()

    def _load_color_settings(self, project_path):
        self.colors._load_color_settings(project_path)

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

    # ── 节点样式切换（转发给 CanvasMenu） ──

    def _switch_node_style(self, style_key, node_item):
        self.menus._switch_node_style(style_key, node_item)

    # ── 依赖解析（供启动队列使用） ──

    def get_node_dependencies(self, node_name: str) -> list:
        """获取节点的上游依赖节点列表
        
        如果节点 A 的输出连接到节点 B 的输入，则 B 依赖 A
        返回 B 需要等待启动的上游节点名称列表
        """
        dependencies = []
        for edge in self.edges:
            if hasattr(edge, 'target_node') and edge.target_node == node_name:
                if hasattr(edge, 'source_node') and edge.source_node not in dependencies:
                    dependencies.append(edge.source_node)
        return dependencies

    def sort_nodes_by_dependency(self, node_names: list) -> list:
        """按依赖顺序排序节点列表
        
        使用拓扑排序，确保依赖节点先启动
        """
        if not node_names:
            return []

        in_degree = {name: 0 for name in node_names}
        adjacency = {name: [] for name in node_names}

        for edge in self.edges:
            if hasattr(edge, 'source_node') and hasattr(edge, 'target_node'):
                src = edge.source_node
                tgt = edge.target_node
                if src in node_names and tgt in node_names:
                    adjacency[src].append(tgt)
                    in_degree[tgt] += 1

        from collections import deque
        queue = deque([name for name in node_names if in_degree[name] == 0])
        result = []

        while queue:
            current = queue.popleft()
            result.append(current)
            for neighbor in adjacency[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        remaining = [name for name in node_names if name not in result]
        result.extend(remaining)

        return result
