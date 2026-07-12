"""
ui/canvas/items/composite_node_item.py
Composite node canvas element.
Appearance: dashed border + teal color + node count + ⊞ icon + anchor ports.
"""

from __future__ import annotations

from pathlib import Path

import psutil
from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsTextItem,
    QMenu,
    QStyleOptionGraphicsItem,
    QWidget,
)

from ui.canvas.items.anchor_item import AnchorItem
from ui.core.i18n import t
from ui.core.utils.dialog_utils import themed_message

ANCHOR_RADIUS = 5
ANCHOR_SPACING = 22
PADDING_TOP = 35
PADDING_BOTTOM = 12
BASE_WIDTH = 180


class CompositeNodeItem(QGraphicsRectItem):
    """Composite node canvas element with input/output anchors."""

    BORDER_COLOR = QColor("#4ec9b0")
    FILL_COLOR = QColor("#1e3a3a")
    SELECTED_BORDER = QColor("#6ee9d0")
    INPUT_ANCHOR_COLOR = QColor("#4fc34f")
    OUTPUT_ANCHOR_COLOR = QColor("#f06060")

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
        self._canvas = canvas
        self._input_ports = input_ports or []
        self._output_ports = output_ports or []
        self._anchors = []
        self._is_expanded = False

        self._calc_geometry()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(10)
        self.setAcceptHoverEvents(True)

        self._pen = QPen(self.BORDER_COLOR, 2, Qt.PenStyle.DashLine)
        self._brush = QBrush(self.FILL_COLOR)
        self._font_bold = QFont("Segoe UI", 11, QFont.Weight.Bold)
        self._font_small = QFont("Segoe UI", 9)

        # 资源监控 — 画布上小型 CPU/MEM 文本
        self._status_indicator = QGraphicsTextItem(self)
        self._status_indicator.setZValue(4)
        self._status_indicator.setVisible(False)
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

        self._create_anchors()

    def _calc_geometry(self):
        port_rows = max(len(self._input_ports), len(self._output_ports), 1)
        self._height = max(60, PADDING_TOP + port_rows * ANCHOR_SPACING + PADDING_BOTTOM)
        self.setRect(0, 0, BASE_WIDTH, self._height)

    def _create_anchors(self):
        for a in self._anchors:
            if a.scene():
                a.scene().removeItem(a)
        self._anchors.clear()

        in_count = len(self._input_ports)
        out_count = len(self._output_ports)

        # Input anchors (left side)
        for i in range(in_count):
            y = PADDING_TOP + i * ANCHOR_SPACING
            anchor = AnchorItem(
                0,
                y,
                anchor_type="input",
                port_name=self._input_ports[i]["port_name"],
                port_type="input",
                size=ANCHOR_RADIUS * 2,
                parent=self,
            )
            anchor.setBrush(QBrush(self.INPUT_ANCHOR_COLOR))
            anchor.setPen(QPen(QColor("#3a7a3a"), 1))
            self._anchors.append(anchor)

        # Output anchors (right side)
        for i in range(out_count):
            y = PADDING_TOP + i * ANCHOR_SPACING
            anchor = AnchorItem(
                BASE_WIDTH,
                y,
                anchor_type="output",
                port_name=self._output_ports[i]["port_name"],
                port_type="output",
                size=ANCHOR_RADIUS * 2,
                parent=self,
            )
            anchor.setBrush(QBrush(self.OUTPUT_ANCHOR_COLOR))
            anchor.setPen(QPen(QColor("#8a3a3a"), 1))
            self._anchors.append(anchor)

    def update_ports(self, input_ports: list, output_ports: list):
        self._input_ports = input_ports
        self._output_ports = output_ports
        self._calc_geometry()
        self._create_anchors()
        self.update()

    def find_anchor_by_port(self, port_name: str, port_type: str):
        """Find an anchor by port_name and type ('input' or 'output')."""
        for a in self._anchors:
            if getattr(a, "port_name", "") == port_name and getattr(a, "port_type", "") == port_type:
                return a
        return None

    # ── Compatibility with connection system ──

    @property
    def node_name(self) -> str:
        """Compatibility: connection system expects node_name."""
        return self.comp_id

    @property
    def input_anchor(self):
        """Return first visible input anchor (for connection system)."""
        for a in self._anchors:
            if getattr(a, "port_type", "") == "input" and a.isVisible():
                return a
        return None

    @property
    def output_anchor(self):
        """Return first visible output anchor (for connection system)."""
        for a in self._anchors:
            if getattr(a, "port_type", "") == "output" and a.isVisible():
                return a
        return None

    def find_nearest_input_anchor(self, local_pos, max_dist=60):
        """Compatibility: find nearest input anchor for connection target."""
        best = None
        best_dist = max_dist
        for a in self._anchors:
            if getattr(a, "port_type", "") == "input":
                d = (a.pos() - local_pos).manhattanLength()
                if d < best_dist:
                    best_dist = d
                    best = a
        return best

    def find_nearest_output_anchor(self, local_pos, max_dist=60):
        """Find nearest output anchor for starting a connection."""
        best = None
        best_dist = max_dist
        for a in self._anchors:
            if getattr(a, "port_type", "") == "output":
                d = (a.pos() - local_pos).manhattanLength()
                if d < best_dist:
                    best_dist = d
                    best = a
        return best

    # ── Expand/collapse state ──

    @property
    def is_expanded(self) -> bool:
        return self._is_expanded

    @is_expanded.setter
    def is_expanded(self, val: bool):
        self._is_expanded = val
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            if self._canvas:
                # Update connected edges so lines follow the composite node
                for edge in self._canvas.edges:
                    if edge.start_node is self or edge.end_node is self:
                        edge.update_path()
                if hasattr(self._canvas, "_composite_manager"):
                    mgr = self._canvas._composite_manager
                    comp = mgr._composites.get(self.comp_id)
                    if comp:
                        comp["canvas_position"] = {"x": value.x(), "y": value.y()}
                        mgr.save_debounced()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect()

        # Background
        painter.setBrush(self._brush)
        if self.isSelected():
            painter.setPen(QPen(self.SELECTED_BORDER, 2.5, Qt.PenStyle.DashLine))
        else:
            painter.setPen(self._pen)
        painter.drawRoundedRect(rect, 8, 8)

        # Icon area (left ⊞)
        icon_rect = QRectF(rect.x() + 8, rect.y() + 8, 24, 24)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#4ec9b0"))
        painter.drawRoundedRect(icon_rect, 4, 4)

        painter.setPen(QColor("#1e1e1e"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, "\u229e")

        # Name
        name_rect = QRectF(icon_rect.right() + 6, rect.y() + 7, rect.width() - icon_rect.right() - 16, 20)
        painter.setPen(QColor("#4ec9b0"))
        painter.setFont(self._font_bold)
        if self.display_name:
            label = self.display_name
        else:
            short_id = self.comp_id.replace("composite_", "")[:6]
            label = f"Composite {short_id}"
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)

        # Node count
        sub_rect = QRectF(name_rect.x(), name_rect.bottom(), name_rect.width(), 18)
        painter.setPen(QColor("#888"))
        painter.setFont(self._font_small)

        runtime = "inprocess"
        if self._canvas and hasattr(self._canvas, "_composite_manager"):
            runtime = self._canvas._composite_manager.get_runtime(self.comp_id) or "inprocess"

        painter.drawText(sub_rect, Qt.AlignmentFlag.AlignLeft, f"{self.node_count} nodes  {runtime}")

        # Port labels
        painter.setFont(QFont("Segoe UI", 7))
        len(self._input_ports)
        len(self._output_ports)

        for i, port in enumerate(self._input_ports):
            y = PADDING_TOP + i * ANCHOR_SPACING + 4
            painter.setPen(QColor("#4fc34f"))
            painter.drawText(QRectF(6, y - 3, 70, 12), Qt.AlignmentFlag.AlignLeft, port.get("display_name", "")[:10])

        for i, port in enumerate(self._output_ports):
            y = PADDING_TOP + i * ANCHOR_SPACING + 4
            painter.setPen(QColor("#f06060"))
            painter.drawText(
                QRectF(BASE_WIDTH - 76, y - 3, 70, 12), Qt.AlignmentFlag.AlignRight, port.get("display_name", "")[:10]
            )

    # ── Mouse events ──

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.setStyleSheet("QMenu { background: #2b2b2b; color: #ccc; }")

        # Read expanded state from manager (authoritative), not self._is_expanded
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
        if self._canvas and hasattr(self._canvas, "_composite_manager"):
            mgr = self._canvas._composite_manager
            if hasattr(mgr, "toggle_expand"):
                mgr.toggle_expand(self.comp_id)

    def _get_manager(self):
        if self._canvas and hasattr(self._canvas, "_composite_manager"):
            return self._canvas._composite_manager
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
        runtime = mgr.get_runtime(self.comp_id) or "inprocess"
        if runtime == "inprocess":
            ok, msg = mgr.start_inprocess(self.comp_id)
        else:
            ok, msg = mgr.start_process_mode(self.comp_id)
        if not ok:
            themed_message(None, t("k_title_error"), msg, "error")
        else:
            self._start_monitoring()

    def _stop(self):
        mgr = self._get_manager()
        if mgr:
            mgr.stop_composite(self.comp_id)
        self._stop_monitoring()

    # ── 资源监控 ──

    def _get_composite_pid(self) -> int | None:
        """读取复合节点 orchestrator 进程 PID。"""
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
        """启动复合节点资源监控（1 秒轮询）。"""
        if not self._is_expanded:
            self._layout_status_widgets()
        self._monitoring_timer.start(1000)

    def _stop_monitoring(self):
        """停止监控并隐藏状态文本。"""
        self._monitoring_timer.stop()
        self._status_indicator.setVisible(False)
        self._status_cpu_text.setVisible(False)
        self._status_mem_text.setVisible(False)

    def _poll_composite_status(self):
        """轮询复合节点资源（psutil 进程树聚合）。"""
        pid = self._get_composite_pid()
        if pid is None or not psutil.pid_exists(pid):
            self._stop_monitoring()
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

            self._status_indicator.setHtml('<span style="color:#4CAF50;font-size:10px;">● running</span>')
            self._status_cpu_text.setPlainText(f"CPU: {cpu_total:.0f}%")
            mem_mb = mem_total / (1024 * 1024)
            if mem_mb >= 1024:
                self._status_mem_text.setPlainText(f"MEM: {mem_mb / 1024:.2f} GB")
            else:
                self._status_mem_text.setPlainText(f"MEM: {mem_mb:.0f} MB")

            visible = not self._is_expanded
            self._status_indicator.setVisible(visible)
            self._status_cpu_text.setVisible(visible)
            self._status_mem_text.setVisible(visible)
        except Exception:
            self._stop_monitoring()

    def _layout_status_widgets(self):
        """布局 CPU/MEM 文本 — 显示在复合节点矩形底部。"""
        font = QFont("Arial", 7)
        font.setBold(True)
        self._status_indicator.setFont(font)
        self._status_cpu_text.setFont(font)
        self._status_mem_text.setFont(font)

        y_base = self._height + 2
        # 状态指示符
        self._status_indicator.setPos(8, y_base)
        # CPU 文本靠左，状态指示符右侧
        self._status_cpu_text.setPos(70, y_base)
        self._status_mem_text.setPos(130, y_base)
