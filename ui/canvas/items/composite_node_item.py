"""
ui/canvas/items/composite_node_item.py
Composite node canvas element - reuses regular node components for consistent appearance.
"""

from __future__ import annotations

from pathlib import Path

import psutil
from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QStyleOptionGraphicsItem,
    QVBoxLayout,
    QWidget,
)

from ui.canvas.items.anchor_manager import AnchorManager
from ui.canvas.items.node_components.param_panel import NodeParamPanel
from ui.canvas.items.node_components.rendering import NodeRendering
from ui.canvas.items.node_components.subcomponents import NodeSubComponents
from ui.canvas.items.styles import DetailedNodeStyle
from ui.core.i18n import t
from ui.core.utils.dialog_utils import themed_message


class CompositeNodeItem(QGraphicsRectItem):
    """Composite node canvas element - reuses regular node components."""

    def __init__(
        self,
        comp_id: str,
        node_count: int,
        node_names: list,
        display_name: str = "",
        canvas=None,
        parent=None,
        input_ports: list = None,
        output_ports: list = None,
    ):
        super().__init__(parent)
        self.comp_id = comp_id
        self.node_count = node_count
        self.node_names = node_names
        self.display_name = display_name
        self.canvas = canvas
        self._input_ports = input_ports or []
        self._output_ports = output_ports or []
        self._is_expanded = False

        self.node_name = comp_id
        self.language = "Composite"
        self.status = "stopped"

        self._style = DetailedNodeStyle()
        self._style.node_width = 340
        self._style.node_height = 80

        self._rendering = NodeRendering(self)
        self._subcomponents = NodeSubComponents(self)
        self._subcomponents.build_status_indicator()
        self._subcomponents.build_selection_ring()
        self._subcomponents.build_text_labels()

        self._proxy_widgets: list = []
        self._param_widgets: dict = {}
        self._param_row_positions: dict = {}

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(10)
        self.setAcceptHoverEvents(True)

        self.anchor_manager = AnchorManager(self)
        self._create_anchors_from_ports()

        self._status_indicator_widget = QGraphicsTextItem(self)
        self._status_indicator_widget.setZValue(4)
        self._status_indicator_widget.setVisible(False)
        self._status_cpu_text = QGraphicsTextItem(self)
        self._status_cpu_text.setZValue(4)
        self._status_cpu_text.setDefaultTextColor(QColor("#4ecdc4"))
        self._status_cpu_text.setVisible(False)
        self._status_mem_text = QGraphicsTextItem(self)
        self._status_mem_text.setZValue(4)
        self._status_mem_text.setDefaultTextColor(QColor("#ff6b6b"))
        self._status_mem_text.setVisible(False)
        self._monitoring_timer = QTimer()
        self._monitoring_timer.timeout.connect(self._poll_composite_status)

        self._param_panel = NodeParamPanel(self)
        self._build_detailed_view_with_ports()

    def update_status(self, status):
        """更新复合节点状态"""
        self.status = status
        if hasattr(self, "_style"):
            self._style.apply_status(self, status)

    def _create_anchors_from_ports(self):
        input_ports_normalized = []
        for p in self._input_ports:
            if isinstance(p, dict):
                port_name = p.get("name") or p.get("port_name")
                if not port_name:
                    continue
                entry_port = p.get("entry_port")
                if entry_port is None or entry_port == "" or entry_port == "data":
                    continue
                label = p.get("label") or p.get("display_name") or port_name
                input_ports_normalized.append(
                    {
                        "name": port_name,
                        "label": label,
                        "type": p.get("type", "default"),
                        "required": p.get("required", False),
                        "description": p.get("description", ""),
                        "source": p.get("source", "node"),
                    }
                )

        output_ports_normalized = []
        for p in self._output_ports:
            if isinstance(p, dict):
                port_name = p.get("name") or p.get("port_name")
                if not port_name:
                    continue
                if port_name.endswith("_out") or port_name.startswith("node_"):
                    continue
                label = p.get("label") or p.get("display_name") or port_name
                output_ports_normalized.append(
                    {
                        "name": port_name,
                        "label": label,
                        "type": p.get("type", "default"),
                        "description": p.get("description", ""),
                    }
                )

        config = {
            "listen_upper_file": "",
            "output_file": "./output.json",
            "input_ports": input_ports_normalized,
            "output_ports": output_ports_normalized,
        }
        self.anchor_manager.build_from_config(config, self._param_row_positions)

    def _build_detailed_view_with_ports(self):
        self._param_row_positions.clear()

        input_port_defs = []
        output_port_defs = []

        from ui.core.node.node_config_parser import NodeConfigParser

        input_ports_normalized = []
        for p in self._input_ports:
            if isinstance(p, dict):
                port_name = p.get("name") or p.get("port_name")
                if not port_name:
                    continue
                entry_port = p.get("entry_port")
                if entry_port is None or entry_port == "" or entry_port == "data":
                    continue
                label = p.get("label") or p.get("display_name") or port_name
                input_ports_normalized.append(
                    {
                        "name": port_name,
                        "label": label,
                        "type": p.get("type", "default"),
                        "required": p.get("required", False),
                        "description": p.get("description", ""),
                        "source": p.get("source", "node"),
                    }
                )

        output_ports_normalized = []
        for p in self._output_ports:
            if isinstance(p, dict):
                port_name = p.get("name") or p.get("port_name")
                if not port_name:
                    continue
                if port_name.endswith("_out") or port_name.startswith("node_"):
                    continue
                label = p.get("label") or p.get("display_name") or port_name
                output_ports_normalized.append(
                    {
                        "name": port_name,
                        "label": label,
                        "type": p.get("type", "default"),
                        "description": p.get("description", ""),
                    }
                )

        config = {
            "input_ports": input_ports_normalized,
            "output_ports": output_ports_normalized,
            "parameters": [],
        }

        input_port_defs = NodeConfigParser.parse_input_ports(config) or []
        input_port_defs = [p for p in input_port_defs if getattr(p, "source", "") == "node"]
        output_port_defs = NodeConfigParser.parse_output_ports(config) or []

        has_content = bool(input_port_defs or output_port_defs)

        min_container_w = 340
        default_height = 80
        final_w = max(
            self._style.node_width if hasattr(self._style, "node_width") else min_container_w,
            min_container_w,
        )
        final_h = default_height

        if has_content:
            from ui.canvas.items.anchor_item import ANCHOR_SIZE, ANCHOR_SIZE_SMALL
            from ui.canvas.parameter_widgets import ParameterWidget
            from ui.core.node.node_config_parser import ParameterDef

            container = QWidget()
            container.setStyleSheet("background: transparent;")

            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(38 + 8, 6, 8, 6)
            v_layout.setSpacing(6)

            row_types = []

            for port in input_port_defs:
                p_name = port.name
                label_text = getattr(port, "label", "") or port.name
                p_default = ""
                param_obj = ParameterDef(name=p_name, type="string", label=label_text, default=p_default)
                w = ParameterWidget.create(param_obj, p_default)
                w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                v_layout.addWidget(w)
                self._param_widgets[p_name] = w
                row_types.append("input_port")

            for port in output_port_defs:
                output_wrap = QWidget()
                output_wrap.setStyleSheet("background: transparent;")
                output_wrap.setMinimumHeight(32)
                output_h_layout = QHBoxLayout(output_wrap)
                output_h_layout.setContentsMargins(0, 0, 0, 0)
                output_h_layout.addStretch(1)
                output_label = QLabel(getattr(port, "label", "") or port.name)
                out_font = QFont()
                out_font.setPointSize(9)
                output_label.setFont(out_font)
                output_label.setStyleSheet("color: #88ccff;")
                output_h_layout.addWidget(output_label)
                v_layout.addWidget(output_wrap)
                row_types.append("output")
            else:
                output_wrap = QWidget()
                output_wrap.setStyleSheet("background: transparent;")
                output_wrap.setMinimumHeight(32)
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

            self._style.set_sizes(content_w, content_h)
            final_w = max(self._style.node_width, content_w)
            final_h = self._style.node_height
            self.setRect(0, 0, final_w, final_h)
            container.setFixedWidth(final_w)

            from PySide6.QtWidgets import QGraphicsProxyWidget

            proxy = QGraphicsProxyWidget(self)
            proxy.setWidget(container)
            proxy.setPos(0, 0)
            proxy.setZValue(5)
            proxy.setFlag(proxy.GraphicsItemFlag.ItemClipsChildrenToShape, False)
            proxy.setFlag(proxy.GraphicsItemFlag.ItemClipsToShape, False)
            proxy.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._proxy_widgets.append(proxy)

            small_center_x = 38 + 8 - ANCHOR_SIZE_SMALL / 2 - 2
            margins_top = v_layout.contentsMargins().top() if v_layout.contentsMargins() else 0
            running_y = 0
            est_ys = []
            for _j in range(len(row_types)):
                est_ys.append(running_y + 32 / 2)
                running_y += 32 + 6

            for i, rtype in enumerate(row_types):
                item = v_layout.itemAt(i) if v_layout else None
                geom = item.geometry() if item and item.widget() else None
                if geom is None or geom.width() <= 0 or geom.height() <= 0:
                    center_y = margins_top + est_ys[i] if i < len(est_ys) else (margins_top + i * (32 + 6) + 32 / 2)
                else:
                    row_top = geom.y()
                    center_y = row_top + geom.height() / 2.0

                if rtype == "input_port":
                    port_idx = row_types[:i].count("input_port")
                    if port_idx < len(input_port_defs):
                        port = input_port_defs[port_idx]
                        self._param_row_positions[port.name] = (
                            small_center_x,
                            center_y,
                            ANCHOR_SIZE_SMALL,
                        )
                elif rtype == "output":
                    out_cx = final_w
                    if output_port_defs:
                        out_idx = row_types[:i].count("output")
                        if out_idx < len(output_port_defs):
                            port = output_port_defs[out_idx]
                            self._param_row_positions[port.name] = (
                                out_cx,
                                center_y,
                                ANCHOR_SIZE_SMALL,
                            )
                    else:
                        out_cy = final_h / 2.0
                        self._param_row_positions["__output__"] = (out_cx, out_cy, ANCHOR_SIZE)
        else:
            self.setRect(0, 0, final_w, final_h)

        if hasattr(self, "_in_label") and self._in_label:
            self._in_label.setVisible(False)
        if hasattr(self, "_out_label") and self._out_label:
            self._out_label.setVisible(False)

        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        self.name_text.setFont(title_font)
        self.name_text.setDefaultTextColor(QColor(self._style.header_text_color))
        self.name_text.setZValue(6)
        display_name = self.display_name or f"Composite {self.comp_id.replace('composite_', '')[:6]}"
        self.name_text.setPlainText(display_name)
        text_rect = self.name_text.boundingRect()
        title_x = max(4.0, (final_w - text_rect.width()) / 2)
        title_y = -text_rect.height()
        self.name_text.setPos(title_x, title_y)
        self.name_text.setVisible(True)

        indicator_size = 10
        indicator_x = final_w - indicator_size - 8
        indicator_y = 4
        self.status_indicator.setRect(indicator_x, indicator_y, indicator_size, indicator_size)
        self.status_indicator.setZValue(7)
        self.status_indicator.setVisible(True)

        lang_font = QFont()
        lang_font.setPointSize(8)
        self.lang_text.setFont(lang_font)
        self.lang_text.setDefaultTextColor(QColor("#888888"))
        self.lang_text.setZValue(6)
        self.lang_text.setPlainText(f"{self.node_count} nodes")
        lr = self.lang_text.boundingRect()
        lang_x = (final_w - lr.width()) / 2
        lang_y = final_h + 2
        self.lang_text.setPos(lang_x, lang_y)
        self.lang_text.setVisible(True)

        self._create_anchors_from_ports()

    def update_ports(self, input_ports: list, output_ports: list):
        self._input_ports = input_ports
        self._output_ports = output_ports
        for p in self._proxy_widgets:
            w = p.widget()
            if w:
                w.deleteLater()
            p.setWidget(None)
            if self.scene():
                self.scene().removeItem(p)
        self._proxy_widgets.clear()
        self._param_widgets.clear()
        self._build_detailed_view_with_ports()

    def find_anchor_by_port(self, port_name: str, port_type: str):
        if port_type == "input":
            return self.anchor_manager.get_input(port_name)
        else:
            return self.anchor_manager.get_output(port_name)

    @property
    def input_anchor(self):
        return self.anchor_manager.get_default_input()

    @property
    def output_anchor(self):
        return self.anchor_manager.get_default_output()

    def find_nearest_input_anchor(self, local_pos, max_dist=60):
        return self.anchor_manager.find_nearest_input(local_pos, max_dist)

    def find_nearest_output_anchor(self, local_pos, max_dist=60):
        return self.anchor_manager.find_nearest_output(local_pos, max_dist)

    @property
    def is_expanded(self) -> bool:
        return self._is_expanded

    @is_expanded.setter
    def is_expanded(self, val: bool):
        self._is_expanded = val
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.canvas:
                for edge in self.canvas.edges:
                    if edge.start_node is self or edge.end_node is self:
                        edge.update_path()
                if hasattr(self.canvas, "_composite_manager"):
                    mgr = self.canvas._composite_manager
                    comp = mgr._composites.get(self.comp_id)
                    if comp:
                        comp["canvas_position"] = {"x": value.x(), "y": value.y()}
                        mgr.save_debounced()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        self._rendering.paint(painter, option, widget)

        rect = self.rect()

        dot_rect = QRectF(rect.x() + 8, rect.y() + 10, 6, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4ec9b0"))
        painter.drawEllipse(dot_rect)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("QMenu { background: #2b2b2b; color: #ccc; }")

        mgr = self._get_manager()
        is_expanded = False
        if mgr:
            comp = mgr._composites.get(self.comp_id)
            if comp:
                is_expanded = comp.get("_expanded", False)

        expand_action = menu.addAction("Collapse" if is_expanded else "Expand")
        expand_action.triggered.connect(self._toggle_expand)

        decompress_action = menu.addAction("Decompress")
        decompress_action.triggered.connect(self._decompress)

        menu.addSeparator()

        runtime_menu = menu.addMenu("Runtime Mode")
        mgr = self._get_manager()
        current_runtime = mgr.get_runtime(self.comp_id) if mgr else "inprocess"

        proc_action = runtime_menu.addAction("Process (separate)")
        inproc_action = runtime_menu.addAction("In-process (single)")
        proc_action.setCheckable(True)
        inproc_action.setCheckable(True)
        if current_runtime == "process":
            proc_action.setChecked(True)
        else:
            inproc_action.setChecked(True)
        proc_action.triggered.connect(lambda: self._set_runtime("process"))
        inproc_action.triggered.connect(lambda: self._set_runtime("inprocess"))

        menu.addSeparator()

        start_action = menu.addAction("Start")
        stop_action = menu.addAction("Stop")
        start_action.triggered.connect(self._start)
        stop_action.triggered.connect(self._stop)

        menu.exec(event.screenPos())

    def _toggle_expand(self):
        if self.canvas and hasattr(self.canvas, "_composite_manager"):
            mgr = self.canvas._composite_manager
            if hasattr(mgr, "toggle_expand"):
                mgr.toggle_expand(self.comp_id)

    def _get_manager(self):
        if self.canvas and hasattr(self.canvas, "_composite_manager"):
            return self.canvas._composite_manager
        return None

    def _decompress(self):
        ok = themed_message(
            None,
            t("k_composite_decompress_confirm_title"),
            t("k_composite_decompress_confirm_text").format(n=self.node_count),
            "question",
        )
        if not ok:
            return
        mgr = self._get_manager()
        if mgr:
            ok, msg = mgr.decompress(self.comp_id)
            if not ok:
                themed_message(None, t("k_title_error"), msg, "error")

    def _set_runtime(self, mode):
        mgr = self._get_manager()
        if mgr:
            mgr.set_runtime(self.comp_id, mode)
            self.update()

    def _start(self):
        mgr = self._get_manager()
        if not mgr:
            return

        from ui.core.node.node_startup_queue import startup_queue

        if startup_queue.is_queued(self.comp_id):
            themed_message(None, t("k_title_info"), "复合节点已在启动队列中", "info")
            return

        if self.canvas and hasattr(self.canvas, "parent_window") and self.canvas.parent_window:
            startup_queue.set_project_context(
                self.canvas.parent_window.current_project_path, self.canvas.parent_window.nodes_data, self.canvas
            )

        dependencies = []
        if self.canvas:
            dependencies = self.canvas.get_node_dependencies(self.comp_id)

        success = startup_queue.enqueue(self.comp_id, dependencies=dependencies)
        if success:
            if self.canvas:
                self.canvas.update_node_status(self.comp_id, "queued")
            if dependencies:
                themed_message(
                    None, t("k_title_info"), f"复合节点已加入启动队列（等待: {', '.join(dependencies)}）", "info"
                )
            else:
                themed_message(None, t("k_title_info"), "复合节点已加入启动队列", "info")
        else:
            themed_message(None, t("k_title_error"), "加入队列失败", "error")

    def _stop(self):
        mgr = self._get_manager()
        if mgr:
            mgr.stop_composite(self.comp_id)
        self._stop_monitoring()

    def _get_composite_pid(self) -> int | None:
        mgr = self._get_manager()
        if not mgr:
            return None
        pid_file = Path(mgr._project_path) / f"__composite_{self.comp_id}.pid"
        if not pid_file.exists():
            return None
        try:
            return int(pid_file.read_text().strip())
        except Exception:
            return None

    def _start_monitoring(self):
        if not self._is_expanded:
            self._layout_status_widgets()
        self._monitoring_timer.start(1000)

    def _stop_monitoring(self):
        self._monitoring_timer.stop()
        self._status_indicator_widget.setVisible(False)
        self._status_cpu_text.setVisible(False)
        self._status_mem_text.setVisible(False)

    def _poll_composite_status(self):
        pid = self._get_composite_pid()
        if pid is None:
            self._stop_monitoring()
            return
        if not psutil.pid_exists(pid):
            self._monitoring_timer.stop()
            self._status_indicator_widget.setText("\u2713")
            self._status_indicator_widget.setStyleSheet("color: #4ec9b0; font-weight: bold; font-size: 14px;")
            self._status_indicator_widget.setVisible(True)
            self._status_cpu_text.setVisible(False)
            self._status_mem_text.setVisible(False)
            return

        try:
            proc = psutil.Process(pid)
            cpu_total = 0.0
            mem_total = 0

            for child in proc.children(recursive=True):
                try:
                    cpu_total += child.cpu_percent()
                    mem_total += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            try:
                cpu_total += proc.cpu_percent()
                mem_total += proc.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            self._status_indicator_widget.setHtml('<span style="color:#4CAF50;font-size:10px;">● running</span>')
            self._status_cpu_text.setPlainText(f"CPU: {cpu_total:.0f}%")
            mem_mb = mem_total / (1024 * 1024)
            if mem_mb >= 1024:
                self._status_mem_text.setPlainText(f"MEM: {mem_mb / 1024:.2f} GB")
            else:
                self._status_mem_text.setPlainText(f"MEM: {mem_mb:.0f} MB")

            visible = not self._is_expanded
            self._status_indicator_widget.setVisible(visible)
            self._status_cpu_text.setVisible(visible)
            self._status_mem_text.setVisible(visible)
        except Exception:
            self._stop_monitoring()

    def _layout_status_widgets(self):
        font = QFont("Arial", 7)
        font.setBold(True)
        self._status_indicator_widget.setFont(font)
        self._status_cpu_text.setFont(font)
        self._status_mem_text.setFont(font)

        y_base = self.rect().height() + 2
        self._status_indicator_widget.setPos(8, y_base)
        self._status_cpu_text.setPos(70, y_base)
        self._status_mem_text.setPos(130, y_base)
