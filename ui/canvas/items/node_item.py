"""
节点项（对应VueFlow节点）
继承自 QGraphicsRectItem，负责节点的视觉渲染、锚点管理和交互处理

v2 — 拆分后：主类仅保留生命周期编排，具体实现委托给 node_components/ 子模块。
"""
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsItem
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QColor, QRectF

from ui.core.logger import logger

from ui.canvas.items.anchor_item import AnchorItem, ANCHOR_SIZE, ANCHOR_HALF
from ui.canvas.items.anchor_manager import AnchorManager
from ui.canvas.items.styles import DetailedNodeStyle
from ui.canvas.items.node_status_widget import NodeStatusWidget

# ── 子组件模块 ──
from ui.canvas.items.node_components.rendering import NodeRendering
from ui.canvas.items.node_components.subcomponents import NodeSubComponents
from ui.canvas.items.node_components.status_manager import NodeStatusManager
from ui.canvas.items.node_components.config_manager import NodeConfigManager
from ui.canvas.items.node_components.geometry_handler import NodeGeometryHandler
from ui.canvas.items.node_components.interaction_handler import NodeInteractionHandler
from ui.canvas.items.node_components.style_manager import NodeStyleManager
from ui.canvas.items.node_components.param_panel import NodeParamPanel


class NodeItem(QGraphicsRectItem):
    """节点项（对应VueFlow节点）"""

    on_expand_requested = None

    def __init__(self, node_name, language="Python", status="stopped",
                 x=0, y=0, w=140, h=80, canvas=None, style=None):
        super().__init__(x, y, w, h, None)
        self.node_name = node_name
        self.language = language
        self.status = status
        self.canvas = canvas

        # 节点样式
        self._style = style or DetailedNodeStyle()
        self._style.node_width = w
        self._style.node_height = h

        # ── 初始化子组件（组合模式，非多重继承）──
        self._rendering = NodeRendering(self)
        self._subcomponents = NodeSubComponents(self)
        self._status_manager = NodeStatusManager(self)
        self._config_manager = NodeConfigManager(self)
        self._geometry = NodeGeometryHandler(self)
        self._interaction = NodeInteractionHandler(self)
        self._style_manager = NodeStyleManager(self)
        self._param_panel = NodeParamPanel(self)

        # ── Qt 设施 ──
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(2)
        self.setRect(QRectF(0, 0, w, h))

        # ── 锚点系统 ──
        self.anchor_manager = AnchorManager(self)
        self._param_row_positions: dict = {}

        # ── 子控件构造 ──
        self._subcomponents.build_all()

        # ── 详细版参数控件（空初始化，由 style.apply() 触发构建）──
        self._proxy_widgets: list = []
        self._param_widgets: dict = {}

        # ── 应用样式 + 自定义颜色 ──
        self._style.apply(self)
        self._style.apply_status(self, status)
        self._rendering.apply_custom_colors()

        # ── 状态组件 ──
        self._init_status_widget()
        self._status_manager.connect_resource_monitor_signals()

        # ── 运行时间 ──
        self._start_time = None
        if self.status in ("running", "idle"):
            self._status_manager.try_initialize_start_time()

    # ========== 兼容层（对外 API 不变）==========

    @property
    def input_anchor(self) -> AnchorItem:
        return self.anchor_manager.get_default_input()

    @property
    def output_anchor(self) -> AnchorItem:
        return self.anchor_manager.get_default_output()

    def build_anchors_from_config(self, config: dict | None):
        self.anchor_manager.build_from_config(
            config,
            row_positions=self._param_row_positions,
            node_w=self.rect().width(),
            node_h=self.rect().height(),
        )

    def find_nearest_input_anchor(self, local_pos: QPointF, max_dist: int = 20) -> AnchorItem | None:
        return self.anchor_manager.find_nearest_input(local_pos, max_dist)

    def find_nearest_output_anchor(self, local_pos: QPointF, max_dist: int = 20) -> AnchorItem | None:
        return self.anchor_manager.find_nearest_output(local_pos, max_dist)

    def all_input_anchors(self) -> list:
        return self.anchor_manager.all_input()

    def all_output_anchors(self) -> list:
        return self.anchor_manager.all_output()

    def _update_selection_ring(self, selected):
        self._interaction.update_selection_ring(selected)

    # ========== 生命周期 ==========

    def dispose(self):
        """断开所有外部信号连接并清理子对象"""
        self._status_manager.dispose_signals()
        self._status_manager.dispose_status_widget()
        for pw in self._proxy_widgets:
            try:
                if pw and pw.widget():
                    pw.widget().deleteLater()
            except Exception:
                pass
        self._proxy_widgets.clear()
        self._param_widgets.clear()
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)

    def update_status(self, status):
        """更新节点状态 — 委托给 StatusManager"""
        self._status_manager.update_status(status)

    # ========== 样式管理 ==========

    def set_style(self, style):
        """设置节点样式 — 委托给 StyleManager"""
        self._style_manager.set_style(style)

    def update_display(self, node_name=None, language=None, status=None):
        """更新显示信息 — 委托给 StyleManager"""
        self._style_manager.update_display(node_name, language, status)

    def sync_with_data(self, node_data):
        """从字典同步 — 委托给 StyleManager"""
        self._style_manager.sync_with_data(node_data)

    # ========== 参数面板 ==========

    def _build_detailed_view(self):
        """构建详细视图 — 委托给 ParamPanel"""
        self._param_panel.build_detailed_view()

    def _destroy_detailed(self):
        """销毁详细视图 — 委托给 ParamPanel"""
        self._param_panel._destroy_detailed()

    # ========== 配置管理 ==========

    def _on_param_changed(self, name: str, value):
        self._config_manager.on_param_changed(name, value)

    def _get_node_config(self):
        return self._config_manager.get_node_config()

    def _save_node_config(self, config: dict):
        self._config_manager.save_node_config(config)

    def _get_parent_window(self):
        return self._config_manager.get_parent_window()

    def _subscribe_config_changes(self):
        self._config_manager.subscribe_config_changes()

    def _on_external_config_change(self, node_name: str):
        self._config_manager._on_external_config_change(node_name)

    # ========== 状态/信号 ==========

    def _connect_resource_monitor_signals(self):
        self._status_manager.connect_resource_monitor_signals()

    def _on_status_updated(self, node_name, cpu_percent, mem_mb):
        self._status_manager._on_status_updated(node_name, cpu_percent, mem_mb)

    def _try_initialize_start_time(self):
        self._status_manager.try_initialize_start_time()

    # ========== 内部辅助 ==========

    def _init_status_widget(self):
        """初始化状态显示组件"""
        self._status_widget = NodeStatusWidget(self)
        self._status_widget.set_compact(True)
        self._status_widget.set_visible(True)

    def _ensure_rect(self, w, h):
        """兜底尺寸校正 — 委托给 StyleManager"""
        self._style_manager._ensure_rect(w, h)

    def _load_node_custom_colors(self):
        """加载自定义颜色 — 委托给 Rendering（对外兼容旧调用）"""
        self._rendering.apply_custom_colors()

    # ========== Qt 虚方法（委托给子组件）==========

    def paint(self, painter, option, widget=None):
        self._rendering.paint(painter, option, widget)

    def mousePressEvent(self, event):
        handled = self._interaction.handle_mouse_press(event)
        if not handled:
            super().mousePressEvent(event)

    def itemChange(self, change, value):
        """几何变化 — GeometryHandler 做前置处理，然后传给父类"""
        # _avoid_overlap 在 GeometryHandler.item_change 内部处理
        value = self._geometry.item_change(change, value)
        return value  # item_change 内部已调 super()

    def shape(self):
        """命中检测 — 使用节点矩形"""
        return super().shape()
