"""
性能分析面板 - 高级性能监控和分析工具（优化版）
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGroupBox, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QComboBox, QSpinBox, QCheckBox, QTabWidget
)
from PySide6.QtCore import Qt, Signal, QThread, QMutex, QMutexLocker
from PySide6.QtGui import QColor, QPen, QPainter, QPainterPath
from ui.core.i18n import t
from ui.core.logger import logger
from ui.panels._shared.system_resource_collector import shared_resource_collector
from ui.core.dock_panel_base import DockPanelBase
import time


class StatsCollectorThread(QThread):
    """后台数据收集线程（系统+节点+进程）"""
    
    stats_ready = Signal(dict, dict)
    processes_ready = Signal(list)
    
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self._parent_window = parent_window
        self._mutex = QMutex()
        self._running = True
        self._iteration = 0
    
    def stop(self):
        self._running = False
        self.wait()
    
    def run(self):
        while self._running:
            try:
                # 系统+节点资源采集（每 2 秒）
                system_stats = shared_resource_collector.collect_system_stats()
                
                node_stats = {}
                if self._parent_window:
                    canvas = getattr(self._parent_window, 'canvas', None)
                    if canvas and hasattr(canvas, 'nodes') and canvas.nodes:
                        nodes_data = getattr(self._parent_window, 'nodes_data', {})
                        for name in canvas.nodes.keys():
                            if name in nodes_data:
                                stats = shared_resource_collector.collect_single_node_stats(nodes_data[name], name)
                                node_stats[name] = stats
                
                self.stats_ready.emit(system_stats, node_stats)
                
                # 进程列表采集（每 3 次迭代 = 6 秒，避免过于频繁）
                self._iteration += 1
                if self._iteration % 3 == 0:
                    self._collect_processes()
                    
            except Exception as e:
                logger.warning("后台数据收集失败: %s", e)
            
            self.msleep(2000)
    
    def _collect_processes(self):
        """在后台线程采集进程列表（避免主线程 psutil 卡顿）"""
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    cpu = proc.cpu_percent()
                    mem = proc.memory_info().rss / (1024 ** 2)
                    if cpu > 0 or mem > 1:
                        processes.append((proc.pid, proc.name(), cpu, mem))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            processes.sort(key=lambda x: x[2], reverse=True)
            self.processes_ready.emit(processes[:20])
        except ImportError:
            pass


class ChartCanvas(QWidget):
    """图表画布 - 使用 paintEvent 进行绘制"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._history = {'cpu': [], 'mem': []}
        self._history_mutex = QMutex()
        self.setMinimumHeight(200)
    
    def set_history(self, history):
        """设置历史数据"""
        with QMutexLocker(self._history_mutex):
            self._history = history
        self.update()
    
    def paintEvent(self, event):
        """绘制图表"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        painter.fillRect(rect, QColor("#1e1e1e"))
        
        padding = 30
        chart_rect = rect.adjusted(padding, padding, -padding, -padding)
        
        cpu_color = QColor("#4CAF50")
        mem_color = QColor("#2196F3")
        
        with QMutexLocker(self._history_mutex):
            cpu_data = list(self._history.get('cpu', []))
            mem_data = list(self._history.get('mem', []))
        
        if len(cpu_data) < 2:
            return
        
        points = len(cpu_data)
        x_step = chart_rect.width() / (points - 1)
        
        cpu_path = QPainterPath()
        mem_path = QPainterPath()
        
        for i in range(points):
            x = chart_rect.left() + i * x_step
            cpu_y = chart_rect.bottom() - (cpu_data[i] / 100) * chart_rect.height()
            mem_y = chart_rect.bottom() - (mem_data[i] / 100) * chart_rect.height()
            
            if i == 0:
                cpu_path.moveTo(x, cpu_y)
                mem_path.moveTo(x, mem_y)
            else:
                cpu_path.lineTo(x, cpu_y)
                mem_path.lineTo(x, mem_y)
        
        painter.setPen(QPen(cpu_color, 2))
        painter.drawPath(cpu_path)
        painter.setPen(QPen(mem_color, 2))
        painter.drawPath(mem_path)
        
        painter.setPen(QPen(QColor("#444")))
        for i in range(5):
            y = chart_rect.top() + (chart_rect.height() / 4) * i
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)
        
        painter.setPen(QPen(QColor("#666")))
        for i in range(5):
            y = chart_rect.top() + (chart_rect.height() / 4) * i
            painter.drawText(padding - 25, y + 4, f"{100 - i * 25}%")


class PerformancePanel(DockPanelBase):
    """性能分析面板"""

    performance_alert = Signal(str, str, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self._system_stats = {}
        self._node_stats = {}
        self._history = {}
        self._max_history_points = 60
        self._alert_thresholds = {
            'cpu': 80,
            'memory': 85,
            'network': 90
        }
        self._stats_mutex = QMutex()
        self._process_cache = []

        self.resize(800, 600)
        self.setMinimumSize(600, 450)
        self._init_ui()

        self._schedule_update(1000, self._update_ui)

        self._collector_thread = StatsCollectorThread(self.parent_window, self)
        self._register_resource(self._collector_thread, 'stop')
        self._collector_thread.stats_ready.connect(self._on_stats_ready)
        self._collector_thread.processes_ready.connect(self._on_processes_ready)
        self._collector_thread.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部标题栏
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #252526; border-bottom: 1px solid #3c3c3c;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(8, 4, 8, 4)

        title_label = QLabel(t("k_performance"))
        title_label.setStyleSheet("color: rgba(255,255,255,180); font-size: 11px; font-weight: bold; border: none;")
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        layout.addWidget(top_bar)

        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.setSpacing(8)

        splitter = QSplitter(Qt.Vertical)

        top_tab = QTabWidget()
        top_tab.addTab(self._build_system_tab(), t("k_system"))
        top_tab.addTab(self._build_nodes_tab(), t("k_nodes"))
        splitter.addWidget(top_tab)

        bottom_tab = QTabWidget()
        bottom_tab.addTab(self._build_chart_tab(), t("k_trends"))
        bottom_tab.addTab(self._build_process_tab(), t("k_processes"))
        splitter.addWidget(bottom_tab)

        splitter.setSizes([300, 300])
        content_layout.addWidget(splitter)

        self._build_alert_section(content_layout)

        layout.addWidget(content_area, 1)

    def _build_system_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(12)

        self._sys_cpu_widget = self._build_gauge_widget(t("k_cpu"), "#4CAF50")
        self._sys_ram_widget = self._build_gauge_widget(t("k_memory"), "#2196F3")
        self._sys_disk_widget = self._build_gauge_widget(t("k_disk"), "#FF9800")
        self._sys_net_widget = self._build_gauge_widget(t("k_network"), "#9C27B0")

        grid_layout.addWidget(self._sys_cpu_widget)
        grid_layout.addWidget(self._sys_ram_widget)
        grid_layout.addWidget(self._sys_disk_widget)
        grid_layout.addWidget(self._sys_net_widget)
        grid_layout.addStretch()

        layout.addLayout(grid_layout)

        detail_group = QGroupBox(t("k_details"))
        detail_layout = QVBoxLayout(detail_group)
        detail_layout.setContentsMargins(8, 4, 8, 8)

        self._detail_table = QTableWidget()
        self._detail_table.setColumnCount(2)
        self._detail_table.setHorizontalHeaderLabels([t("k_metric"), t("k_value")])
        self._detail_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._detail_table.verticalHeader().setVisible(False)
        self._detail_table.setStyleSheet("""
            QTableWidget { background-color: #1a1a1a; color: #b0b0b0; font-size: 11px; }
            QHeaderView::section { background-color: #2d2d30; color: #d4d4d4; font-size: 10px; }
        """)
        self._detail_table.setRowCount(8)
        for i in range(8):
            self._detail_table.setItem(i, 0, QTableWidgetItem(""))
            self._detail_table.setItem(i, 1, QTableWidgetItem(""))
        detail_layout.addWidget(self._detail_table)

        layout.addWidget(detail_group)

        return widget

    def _build_nodes_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._node_table = QTableWidget()
        self._node_table.setColumnCount(6)
        self._node_table.setHorizontalHeaderLabels([
            t("k_node_name"), t("k_cpu"), t("k_memory"),
            t("k_network"), t("k_status"), t("k_peak_cpu")
        ])
        self._node_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._node_table.verticalHeader().setVisible(False)
        self._node_table.setStyleSheet("""
            QTableWidget { background-color: #1a1a1a; color: #b0b0b0; font-size: 11px; }
            QHeaderView::section { background-color: #2d2d30; color: #d4d4d4; font-size: 10px; }
        """)
        layout.addWidget(self._node_table)

        return widget

    def _build_chart_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        chart_container = QWidget()
        chart_container.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(10, 10, 10, 10)

        self._chart_label = QLabel(t("k_select_node"))
        self._chart_label.setStyleSheet("color: #888; font-size: 12px;")
        self._chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chart_layout.addWidget(self._chart_label)

        self._node_combo = QComboBox()
        self._node_combo.addItem(t("k_system"))
        self._node_combo.currentTextChanged.connect(self._on_node_selected_for_chart)
        chart_layout.addWidget(self._node_combo)

        self._chart_canvas = ChartCanvas()
        self._chart_canvas.setStyleSheet("background-color: #1e1e1e; border: 1px solid #333;")
        chart_layout.addWidget(self._chart_canvas)

        layout.addWidget(chart_container)

        legend_layout = QHBoxLayout()
        self._cpu_legend = QLabel(t("k_cpu"))
        self._cpu_legend.setStyleSheet("color: #4CAF50;")
        self._mem_legend = QLabel(t("k_memory"))
        self._mem_legend.setStyleSheet("color: #2196F3;")
        legend_layout.addWidget(self._cpu_legend)
        legend_layout.addWidget(self._mem_legend)
        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        return widget

    def _build_process_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._process_table = QTableWidget()
        self._process_table.setColumnCount(4)
        self._process_table.setHorizontalHeaderLabels([
            t("k_pid"), t("k_name"), t("k_cpu"), t("k_memory")
        ])
        self._process_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._process_table.verticalHeader().setVisible(False)
        self._process_table.setStyleSheet("""
            QTableWidget { background-color: #1a1a1a; color: #b0b0b0; font-size: 11px; }
            QHeaderView::section { background-color: #2d2d30; color: #d4d4d4; font-size: 10px; }
        """)
        layout.addWidget(self._process_table)

        return widget

    def _build_alert_section(self, parent_layout):
        alert_group = QGroupBox(t("k_alerts"))
        alert_layout = QHBoxLayout(alert_group)
        alert_layout.setContentsMargins(8, 4, 8, 8)
        alert_layout.setSpacing(12)

        cpu_label = QLabel(t("k_cpu") + ":")
        cpu_label.setStyleSheet("color: #888; font-size: 11px;")
        self._cpu_threshold = QSpinBox()
        self._cpu_threshold.setRange(1, 100)
        self._cpu_threshold.setValue(self._alert_thresholds['cpu'])
        self._cpu_threshold.setSuffix("%")
        alert_layout.addWidget(cpu_label)
        alert_layout.addWidget(self._cpu_threshold)

        mem_label = QLabel(t("k_memory") + ":")
        mem_label.setStyleSheet("color: #888; font-size: 11px;")
        self._mem_threshold = QSpinBox()
        self._mem_threshold.setRange(1, 100)
        self._mem_threshold.setValue(self._alert_thresholds['memory'])
        self._mem_threshold.setSuffix("%")
        alert_layout.addWidget(mem_label)
        alert_layout.addWidget(self._mem_threshold)

        self._alert_enabled = QCheckBox(t("k_enable_alerts"))
        self._alert_enabled.setChecked(True)
        alert_layout.addWidget(self._alert_enabled)

        parent_layout.addWidget(alert_group)

    def _build_gauge_widget(self, label_text, color):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        label = QLabel(label_text)
        label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setStyleSheet(f"""
            QProgressBar {{
                height: 16px; border-radius: 8px;
                background-color: rgba(255, 255, 255, 10);
            }}
            QProgressBar::chunk {{
                background-color: {color}; border-radius: 8px;
            }}
        """)
        layout.addWidget(bar)

        value_label = QLabel("0%")
        value_label.setStyleSheet("color: rgba(255,255,255,150); font-size: 11px;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        return widget

    def _on_stats_ready(self, system_stats, node_stats):
        """后台数据收集完成回调"""
        with QMutexLocker(self._stats_mutex):
            self._system_stats = system_stats
            for name, stats in node_stats.items():
                if name not in self._node_stats:
                    self._node_stats[name] = {'peak_cpu': 0, 'peak_mem': 0}
                self._node_stats[name].update(stats)
                self._node_stats[name]['peak_cpu'] = max(
                    self._node_stats[name]['peak_cpu'], stats.get('cpu', 0)
                )
                self._node_stats[name]['peak_mem'] = max(
                    self._node_stats[name]['peak_mem'], stats.get('memory', 0)
                )

    def _update_ui(self):
        """更新UI（轻量级，只更新已有控件）"""
        with QMutexLocker(self._stats_mutex):
            system_stats = self._system_stats.copy()
            node_stats = self._node_stats.copy()

        if system_stats:
            self._update_system_ui(system_stats)
        
        if node_stats:
            self._refresh_node_table(node_stats)
            self._update_node_combo(node_stats)
        
        self._update_history()
        self._check_alerts()

    def _update_system_ui(self, stats):
        """更新系统资源UI"""
        cpu_bar = self._sys_cpu_widget.findChild(QProgressBar)
        cpu_label = self._sys_cpu_widget.findChildren(QLabel)[-1]
        cpu_bar.setValue(int(stats['cpu_percent']))
        cpu_label.setText(f"{stats['cpu_percent']}%")

        ram_bar = self._sys_ram_widget.findChild(QProgressBar)
        ram_label = self._sys_ram_widget.findChildren(QLabel)[-1]
        ram_bar.setValue(int(stats['memory_percent']))
        used_gb = stats['memory_used'] / (1024**3)
        total_gb = stats['memory_total'] / (1024**3)
        ram_label.setText(f"{used_gb:.1f}/{total_gb:.1f} GB")

        disk_bar = self._sys_disk_widget.findChild(QProgressBar)
        disk_label = self._sys_disk_widget.findChildren(QLabel)[-1]
        disk_bar.setValue(int(stats['disk_percent']))
        disk_label.setText(f"{stats['disk_percent']}%")

        net_bar = self._sys_net_widget.findChild(QProgressBar)
        net_label = self._sys_net_widget.findChildren(QLabel)[-1]
        total_kb = (stats['net_sent_per_sec'] + stats['net_recv_per_sec']) / 1024
        max_bw = 100000
        net_percent = min((total_kb / max_bw) * 100, 100)
        net_bar.setValue(int(net_percent))
        net_label.setText(f"{total_kb:.1f} KB/s")

        self._update_detail_table(stats)

    def _update_detail_table(self, stats):
        """更新详细信息表（复用已有Item）"""
        details = [
            (t("k_cpu_cores"), stats.get('cpu_count', 0)),
            (t("k_cpu_used"), f"{stats.get('cpu_percent', 0)}%"),
            (t("k_memory_used"), f"{stats.get('memory_used', 0) / (1024**3):.2f} GB"),
            (t("k_memory_total"), f"{stats.get('memory_total', 0) / (1024**3):.2f} GB"),
            (t("k_disk_used"), f"{stats.get('disk_used', 0) / (1024**3):.2f} GB"),
            (t("k_disk_total"), f"{stats.get('disk_total', 0) / (1024**3):.2f} GB"),
            (t("k_network_in"), f"{stats.get('net_recv_per_sec', 0) / 1024:.1f} KB/s"),
            (t("k_network_out"), f"{stats.get('net_sent_per_sec', 0) / 1024:.1f} KB/s"),
        ]

        for i, (name, value) in enumerate(details):
            self._detail_table.item(i, 0).setText(str(name))
            self._detail_table.item(i, 1).setText(str(value))

    def _refresh_node_table(self, node_stats):
        """刷新节点表格（复用已有Item）"""
        if self._node_table.rowCount() != len(node_stats):
            self._node_table.setRowCount(len(node_stats))
            for i in range(len(node_stats)):
                for j in range(6):
                    self._node_table.setItem(i, j, QTableWidgetItem(""))

        for i, (name, stats) in enumerate(node_stats.items()):
            self._node_table.item(i, 0).setText(name)
            self._node_table.item(i, 1).setText(f"{stats.get('cpu', 0):.1f}%")
            self._node_table.item(i, 2).setText(f"{stats.get('memory', 0):.1f} MB")
            self._node_table.item(i, 3).setText(f"{stats.get('network', 0):.1f} KB/s")
            
            status_map = {'running': t("k_status_running"), 'idle': t("k_status_idle"), 'stopped': t("k_status_stopped")}
            self._node_table.item(i, 4).setText(status_map.get(stats.get('status'), stats.get('status', '')))
            self._node_table.item(i, 5).setText(f"{stats.get('peak_cpu', 0):.1f}%")

            status_color = QColor("#999")
            if stats.get('status') == 'running':
                status_color = QColor("#4CAF50")
            elif stats.get('status') == 'idle':
                status_color = QColor("#F0A030")
            self._node_table.item(i, 4).setForeground(status_color)

            for j in range(1, 6):
                self._node_table.item(i, j).setTextAlignment(Qt.AlignmentFlag.AlignRight)

    def _update_node_combo(self, node_stats):
        """更新节点选择下拉框"""
        current_text = self._node_combo.currentText()
        self._node_combo.blockSignals(True)
        self._node_combo.clear()
        self._node_combo.addItem(t("k_system"))
        for name in node_stats.keys():
            self._node_combo.addItem(name)
        if current_text:
            self._node_combo.setCurrentText(current_text)
        self._node_combo.blockSignals(False)

    def _on_processes_ready(self, processes):
        """后台进程数据就绪 → 主线程更新表格"""
        if self._process_table.rowCount() != len(processes):
            self._process_table.setRowCount(len(processes))
            for i in range(len(processes)):
                for j in range(4):
                    self._process_table.setItem(i, j, QTableWidgetItem(""))

        for i, (pid, name, cpu, mem) in enumerate(processes):
            self._process_table.item(i, 0).setText(str(pid))
            self._process_table.item(i, 1).setText(name)
            self._process_table.item(i, 2).setText(f"{cpu:.1f}%")
            self._process_table.item(i, 3).setText(f"{mem:.1f} MB")

    def _update_history(self):
        """更新历史数据"""
        with QMutexLocker(self._stats_mutex):
            cpu_val = self._system_stats.get('cpu_percent', 0)
            mem_val = self._system_stats.get('memory_percent', 0)

        if 'system' not in self._history:
            self._history['system'] = {'cpu': [], 'mem': []}

        self._history['system']['cpu'].append(cpu_val)
        self._history['system']['mem'].append(mem_val)

        if len(self._history['system']['cpu']) > self._max_history_points:
            self._history['system']['cpu'] = self._history['system']['cpu'][-self._max_history_points:]
            self._history['system']['mem'] = self._history['system']['mem'][-self._max_history_points:]

        self._update_chart()

    def _update_chart(self):
        """更新图表显示"""
        selected = self._node_combo.currentText()
        if selected == t("k_system"):
            selected = "system"
        
        history = self._history.get(selected, {'cpu': [], 'mem': []})
        self._chart_canvas.set_history(history)

    def _on_node_selected_for_chart(self, node_name):
        """节点选择变化"""
        self._update_chart()

    def _check_alerts(self):
        """检查告警阈值"""
        if not self._alert_enabled.isChecked():
            return

        with QMutexLocker(self._stats_mutex):
            cpu_val = self._system_stats.get('cpu_percent', 0)
            mem_val = self._system_stats.get('memory_percent', 0)
            node_stats = self._node_stats.copy()

        cpu_threshold = self._cpu_threshold.value()
        mem_threshold = self._mem_threshold.value()

        if cpu_val > cpu_threshold:
            self.performance_alert.emit('cpu', t("k_system"), cpu_val, cpu_threshold)

        if mem_val > mem_threshold:
            self.performance_alert.emit('memory', t("k_system"), mem_val, mem_threshold)

        for name, stats in node_stats.items():
            if stats.get('cpu', 0) > cpu_threshold:
                self.performance_alert.emit('cpu', name, stats.get('cpu', 0), cpu_threshold)

    def _on_drag_start(self):
        """拖动开始：暂停所有更新"""
        from ui.core.update_scheduler import update_scheduler
        update_scheduler.unsubscribe(self)

    def _on_drag_end(self):
        """拖动结束：恢复所有更新"""
        self._schedule_update(1000, self._update_ui)
        self._update_ui()

    def dispose(self):
        """面板销毁时清理"""
        if self._disposed:
            return
        if hasattr(self, '_collector_thread') and self._collector_thread.isRunning():
            self._collector_thread.stop()
            self._collector_thread.quit()
            self._collector_thread.wait(1000)
        super().dispose()

    def get_stats(self):
        """获取所有统计数据"""
        with QMutexLocker(self._stats_mutex):
            return {
                'system': self._system_stats.copy(),
                'nodes': self._node_stats.copy(),
                'history': self._history.copy()
            }
