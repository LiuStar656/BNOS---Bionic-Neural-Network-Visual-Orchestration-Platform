"""
硬件资源监测面板 - Dock版本（无标题栏）
实时显示CPU、内存、磁盘、网络占用
支持进程级资源监控和节点资源占用统计

与 resource_monitor.py 共享:
  - SystemResourceCollector: 系统+节点资源数据采集
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.core.dock.dock_panel_base import DockPanelBase
from ui.core.i18n import t
from ui.core.logger import logger
from ui.core.system.polling_manager import polling_manager
from ui.panels._shared.system_resource_collector import shared_resource_collector


class ResourceMonitorDock(DockPanelBase):
    """硬件资源监测面板（Dock版本）"""

    node_state_updated = Signal(str, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._system_stats = {}
        self._node_stats = {}

        polling_manager.node_status_changed.connect(self._on_node_status_changed)

        self.setMinimumSize(380, 400)
        self._init_ui()

        self._schedule_update(3000, self._update_stats)

        from PySide6.QtCore import QTimer

        QTimer.singleShot(500, self._update_stats)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 系统资源概览
        sys_group = QGroupBox(t("k_sys_resources"))
        sys_group.setStyleSheet("""
            QGroupBox {
                color: rgba(255, 255, 255, 200);
                font-size: 11px;
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)
        sys_layout = QVBoxLayout(sys_group)
        sys_layout.setContentsMargins(8, 4, 8, 8)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.addStretch()

        cpu_widget = self._build_stat_widget("CPU", "#4ec9b0", 90)
        self._cpu_bar = cpu_widget.findChild(QProgressBar)
        self._cpu_value = cpu_widget.findChildren(QLabel)[-1]
        top_row.addWidget(cpu_widget)

        ram_widget = self._build_stat_widget("RAM", "#569cd6", 90)
        self._ram_bar = ram_widget.findChild(QProgressBar)
        self._ram_value = ram_widget.findChildren(QLabel)[-1]
        top_row.addWidget(ram_widget)

        disk_widget = self._build_stat_widget("Disk", "#ce9178", 90)
        self._disk_bar = disk_widget.findChild(QProgressBar)
        self._disk_value = disk_widget.findChildren(QLabel)[-1]
        top_row.addWidget(disk_widget)

        top_row.addStretch()
        sys_layout.addLayout(top_row)

        # 网络
        net_layout = QHBoxLayout()
        self._net_label = QLabel("Net")
        self._net_label.setStyleSheet("color: #c586c0; font-size: 11px; font-weight: bold;")
        self._net_bar = QProgressBar()
        self._net_bar.setRange(0, 100)
        self._net_bar.setValue(0)
        self._net_bar.setStyleSheet(self._bar_css("#c586c0"))
        self._net_value = QLabel("0 KB/s")
        self._net_value.setStyleSheet("color: rgba(255,255,255,120); font-size: 10px;")
        net_layout.addWidget(self._net_label)
        net_layout.addWidget(self._net_bar)
        net_layout.addWidget(self._net_value)
        net_layout.addStretch()
        sys_layout.addLayout(net_layout)

        layout.addWidget(sys_group)

        self._net_detail = QLabel()
        self._net_detail.setStyleSheet("color: rgba(255,255,255,100); font-size: 10px;")
        layout.addWidget(self._net_detail)

        # 节点资源监控
        node_group = QGroupBox(t("k_node_resources"))
        node_group.setStyleSheet(sys_group.styleSheet())
        node_layout = QVBoxLayout(node_group)
        node_layout.setContentsMargins(8, 4, 8, 8)

        self._node_table = QTableWidget()
        self._node_table.setColumnCount(4)
        self._node_table.setHorizontalHeaderLabels([t("k_node_name"), "CPU", t("k_memory"), t("k_status")])
        self._node_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(30, 30, 30, 200);
                border: none;
                gridline-color: rgba(255, 255, 255, 10);
                font-size: 11px;
            }
            QTableWidget::item { color: rgba(255, 255, 255, 180); padding: 4px; }
            QHeaderView::section {
                background-color: rgba(40, 40, 40, 200);
                color: rgba(255, 255, 255, 150);
                font-size: 10px; padding: 4px; border: none;
            }
        """)
        self._node_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._node_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._node_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._node_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._node_table.setColumnWidth(1, 60)
        self._node_table.setColumnWidth(2, 80)
        self._node_table.setColumnWidth(3, 60)
        self._node_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        node_layout.addWidget(self._node_table)

        layout.addWidget(node_group)
        layout.addStretch()

    @staticmethod
    def _build_stat_widget(label_text, color, width):
        """构建 CPU/RAM/Disk 统计小组件"""
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bar = QProgressBar()
        bar.setObjectName("progress")
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setFixedWidth(width)
        bar.setStyleSheet(f"""
            QProgressBar {{
                height: 8px; border-radius: 4px;
                background-color: rgba(255, 255, 255, 10);
            }}
            QProgressBar::chunk {{
                background-color: {color}; border-radius: 4px;
            }}
        """)
        val = QLabel("0%")
        val.setStyleSheet("color: rgba(255,255,255,120); font-size: 9px;")
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl)
        lay.addWidget(bar)
        lay.addWidget(val)
        return w

    @staticmethod
    def _bar_css(color):
        return f"""
            QProgressBar {{
                height: 8px; border-radius: 4px;
                background-color: rgba(255, 255, 255, 10);
            }}
            QProgressBar::chunk {{
                background-color: {color}; border-radius: 4px;
            }}
        """

    # ──── 数据更新（委托 shared_resource_collector）────

    def _update_stats(self):
        """更新资源统计"""
        try:
            stats = shared_resource_collector.collect_system_stats()
            self._system_stats.update(stats)

            self._cpu_bar.setValue(int(stats["cpu_percent"]))
            self._cpu_value.setText(f"{stats['cpu_percent']}%")

            self._ram_bar.setValue(int(stats["memory_percent"]))
            used_gb = stats["memory_used"] / (1024**3)
            total_gb = stats["memory_total"] / (1024**3)
            self._ram_value.setText(f"{used_gb:.1f}/{total_gb:.1f} GB ({stats['memory_percent']}%)")

            self._disk_bar.setValue(int(stats["disk_percent"]))
            used_gb = stats["disk_used"] / (1024**3)
            total_gb = stats["disk_total"] / (1024**3)
            self._disk_value.setText(f"{used_gb:.1f}/{total_gb:.1f} GB ({stats['disk_percent']}%)")

            total_net = (stats["net_sent_per_sec"] + stats["net_recv_per_sec"]) / 1024
            self._net_bar.setValue(min(int(total_net / 10), 100))
            self._net_value.setText(f"{total_net:.1f} KB/s")
            self._net_detail.setText(
                f"↓ {stats['net_recv_per_sec'] / 1024:.1f} KB/s  ↑ {stats['net_sent_per_sec'] / 1024:.1f} KB/s"
            )
        except Exception as e:
            logger.warning("系统资源更新失败: %s", e)

        self._update_node_stats()

    def _update_node_stats(self):
        """更新节点资源占用表（含复合节点 orchestrator 进程）。"""
        if not self.parent_window:
            return

        canvas = getattr(self.parent_window, "canvas", None)

        if not canvas or not hasattr(canvas, "nodes") or not canvas.nodes:
            self._node_stats.clear()
            self._update_node_table()
            return

        nodes_data = getattr(self.parent_window, "nodes_data", {})
        project_path = getattr(self.parent_window, "current_project_path", "")
        comp_mgr = getattr(canvas, "_composite_manager", None)
        composites = comp_mgr.get_all_composites() if comp_mgr else {}

        canvas_names = set(canvas.nodes.keys())

        # 复合节点子节点集合
        all_comp_subnodes: set[str] = set()
        for _comp_id, comp in composites.items():
            all_comp_subnodes.update(comp.get("nodes", []))

        # 清理
        current_names = set(self._node_stats.keys())
        for name in current_names - canvas_names:
            if name in self._node_stats:
                del self._node_stats[name]

        # Phase 1: 复合节点单独监测（orchestrator PID）
        import psutil

        for comp_id, comp in composites.items():
            pid = shared_resource_collector.get_composite_pid(project_path, comp_id)
            display = comp.get("display_name") or comp_id
            if pid and psutil.pid_exists(pid):
                cpu, mem = shared_resource_collector.collect_process_resources(pid)
                if cpu is not None and mem is not None:
                    self._node_stats[comp_id] = {
                        "cpu": cpu,
                        "memory": mem,
                        "memory_rss": int(mem * 1024 * 1024),
                        "name": display,
                        "status": "running",
                        "_is_composite": True,
                        "_sub_nodes": comp.get("nodes", []),
                        "_pid": pid,
                    }
                else:
                    self._node_stats[comp_id] = {
                        "cpu": 0.0,
                        "memory": 0.0,
                        "memory_rss": 0,
                        "name": display,
                        "status": "stopped",
                        "_is_composite": True,
                        "_sub_nodes": comp.get("nodes", []),
                        "_pid": None,
                    }
            else:
                self._node_stats[comp_id] = {
                    "cpu": 0.0,
                    "memory": 0.0,
                    "memory_rss": 0,
                    "name": display,
                    "status": "stopped",
                    "_is_composite": True,
                    "_sub_nodes": comp.get("nodes", []),
                    "_pid": None,
                }

        # Phase 2: 独立节点
        for name in canvas_names:
            if name in all_comp_subnodes:
                continue
            if name in composites:
                continue
            if name in nodes_data:
                node_info = nodes_data[name]
                stats = shared_resource_collector.collect_single_node_stats(node_info, name)
                stats["name"] = node_info.get("name", name)
                stats["_is_composite"] = False
                self._node_stats[name] = stats
                self.node_state_updated.emit(name, stats["cpu"], stats["memory"])

        self._update_node_table()

    def _update_node_table(self):
        """更新节点表格。

        层级结构:
          ▶ composite: xxx                    ← 复合节点 orchestrator 进程
            inference [sub]                   ← 子节点（在 orchestrator 内）
          standalone_node                     ← 普通节点
        """
        from ui.core.node.composite_node import GROUP_COLOR

        canvas = getattr(self.parent_window, "canvas", None)
        comp_mgr = getattr(canvas, "_composite_manager", None)
        composites = comp_mgr.get_all_composites() if comp_mgr else {}
        nodes_data = getattr(self.parent_window, "nodes_data", {})

        rows: list[dict] = []
        visited_names: set[str] = set()

        for comp_id, comp in composites.items():
            stats = self._node_stats.get(comp_id, {})
            display = comp.get("display_name") or comp_id
            sub_nodes = comp.get("nodes", [])
            is_running = stats.get("status") == "running"
            pid = stats.get("_pid")

            pid_suffix = f"  PID={pid}" if pid else ""
            rows.append(
                {
                    "name": f"> {display}{pid_suffix}",
                    "cpu": f"{stats.get('cpu', 0.0):.1f}%" if is_running else "—",
                    "memory": f"{stats.get('memory', 0.0):.1f} MB" if is_running else "—",
                    "status": "running" if is_running else "stopped",
                    "color": GROUP_COLOR,
                }
            )
            visited_names.add(comp_id)

            for sn in sub_nodes:
                if comp_mgr and comp_mgr.is_running(comp_id):
                    rows.append(
                        {
                            "name": f"    {sn} [sub]",
                            "cpu": "—",
                            "memory": "—",
                            "status": "managed",
                            "color": "#4ec9b060",
                        }
                    )
                else:
                    if sn in nodes_data:
                        sn_stats = shared_resource_collector.collect_single_node_stats(nodes_data[sn], sn)
                        sn_running = sn_stats.get("status") == "running"
                        rows.append(
                            {
                                "name": f"    {sn} [sub]",
                                "cpu": f"{sn_stats.get('cpu', 0.0):.1f}%" if sn_running else "—",
                                "memory": f"{sn_stats.get('memory', 0.0):.1f} MB" if sn_running else "—",
                                "status": "running" if sn_running else "stopped",
                                "color": "#4ec9b060",
                            }
                        )
                    else:
                        rows.append(
                            {
                                "name": f"    {sn} [sub]",
                                "cpu": "—",
                                "memory": "—",
                                "status": "unknown",
                                "color": "#4ec9b060",
                            }
                        )
                visited_names.add(sn)

        for name, stats in self._node_stats.items():
            if name in visited_names:
                continue
            if stats.get("_is_composite"):
                continue
            rows.append(
                {
                    "name": stats.get("name", name),
                    "cpu": f"{stats.get('cpu', 0.0):.1f}%",
                    "memory": f"{stats.get('memory', 0.0):.1f} MB",
                    "status": stats.get("status", "stopped"),
                    "color": None,
                }
            )

        self._node_table.setRowCount(len(rows))
        status_map = {
            "running": t("k_status_running"),
            "stopped": t("k_status_stopped"),
            "managed": t("k_status_idle"),
            "unknown": "?",
        }

        for i, r in enumerate(rows):
            name_item = QTableWidgetItem(r["name"])
            name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            if r["color"]:
                name_item.setForeground(QColor(r["color"]))

            cpu_item = QTableWidgetItem(r["cpu"])
            cpu_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            mem_item = QTableWidgetItem(r["memory"])
            mem_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            mem_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            status_item = QTableWidgetItem(status_map.get(r["status"], r["status"]))
            status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if r["status"] == "running":
                status_item.setForeground(QColor("#4ec9b0"))
            elif r["status"] == "managed":
                status_item.setForeground(QColor("#4ec9b080"))
            else:
                status_item.setForeground(QColor("#858585"))

            self._node_table.setItem(i, 0, name_item)
            self._node_table.setItem(i, 1, cpu_item)
            self._node_table.setItem(i, 2, mem_item)
            self._node_table.setItem(i, 3, status_item)

    def _on_node_status_changed(self, node_name, new_status):
        if node_name in self._node_stats:
            self._node_stats[node_name]["status"] = new_status
            self._update_node_table()

    def update_node_stats(self, node_stats):
        """外部调用接口"""
        self._node_stats = node_stats
        self._update_node_table()
