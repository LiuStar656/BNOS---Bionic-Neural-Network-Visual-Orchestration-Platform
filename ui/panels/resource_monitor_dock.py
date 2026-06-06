"""
硬件资源监测面板 - Dock版本（无标题栏）
实时显示CPU、内存、磁盘、网络占用
支持进程级资源监控和节点资源占用统计
"""
import os
import psutil
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QGroupBox, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from ui.core.i18n import t
from ui.core.polling_manager import polling_manager


class ResourceMonitorDock(QWidget):
    """硬件资源监测面板（Dock版本 - 无标题栏）"""

    # 节点状态更新信号 - 转发给画布节点
    node_state_updated = pyqtSignal(str, float, float)  # node_name, cpu_percent, memory_mb

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        # 订阅全局节点状态变化
        polling_manager.node_status_changed.connect(self._on_node_status_changed)
        self._system_stats = {
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_used': 0,
            'memory_total': 0,
            'disk_percent': 0,
            'disk_used': 0,
            'disk_total': 0,
            'net_sent': 0,
            'net_recv': 0,
            'net_sent_per_sec': 0,
            'net_recv_per_sec': 0
        }
        self._node_stats = {}
        self._last_net_sent = 0
        self._last_net_recv = 0

        psutil.cpu_percent()
        psutil.net_io_counters()

        self.setMinimumSize(380, 400)
        self._init_ui()

        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_stats)
        self._update_timer.start(1000)

        QTimer.singleShot(500, self._update_stats)

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ===== 系统资源概览 =====
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

        # 第一行：CPU、RAM、Disk 水平排列（居中）
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.addStretch()

        # CPU
        cpu_widget = QWidget()
        cpu_layout = QVBoxLayout(cpu_widget)
        cpu_layout.setContentsMargins(0, 0, 0, 0)
        cpu_layout.setSpacing(2)
        self._cpu_label = QLabel("CPU")
        self._cpu_label.setStyleSheet("color: #4ec9b0; font-size: 11px; font-weight: bold;")
        self._cpu_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cpu_bar = self._create_progress_bar("#4ec9b0")
        self._cpu_bar.setFixedWidth(90)
        self._cpu_value = QLabel("0%")
        self._cpu_value.setStyleSheet("color: rgba(255,255,255,120); font-size: 9px;")
        self._cpu_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cpu_layout.addWidget(self._cpu_label)
        cpu_layout.addWidget(self._cpu_bar)
        cpu_layout.addWidget(self._cpu_value)
        top_row.addWidget(cpu_widget)

        # RAM
        ram_widget = QWidget()
        ram_layout = QVBoxLayout(ram_widget)
        ram_layout.setContentsMargins(0, 0, 0, 0)
        ram_layout.setSpacing(2)
        self._ram_label = QLabel("RAM")
        self._ram_label.setStyleSheet("color: #569cd6; font-size: 11px; font-weight: bold;")
        self._ram_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ram_bar = self._create_progress_bar("#569cd6")
        self._ram_bar.setFixedWidth(90)
        self._ram_value = QLabel("0%")
        self._ram_value.setStyleSheet("color: rgba(255,255,255,120); font-size: 9px;")
        self._ram_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ram_layout.addWidget(self._ram_label)
        ram_layout.addWidget(self._ram_bar)
        ram_layout.addWidget(self._ram_value)
        top_row.addWidget(ram_widget)

        # Disk
        disk_widget = QWidget()
        disk_layout = QVBoxLayout(disk_widget)
        disk_layout.setContentsMargins(0, 0, 0, 0)
        disk_layout.setSpacing(2)
        self._disk_label = QLabel("Disk")
        self._disk_label.setStyleSheet("color: #ce9178; font-size: 11px; font-weight: bold;")
        self._disk_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._disk_bar = self._create_progress_bar("#ce9178")
        self._disk_bar.setFixedWidth(90)
        self._disk_value = QLabel("0%")
        self._disk_value.setStyleSheet("color: rgba(255,255,255,120); font-size: 9px;")
        self._disk_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disk_layout.addWidget(self._disk_label)
        disk_layout.addWidget(self._disk_bar)
        disk_layout.addWidget(self._disk_value)
        top_row.addWidget(disk_widget)

        top_row.addStretch()
        sys_layout.addLayout(top_row)

        # 第二行：网络
        net_layout = QHBoxLayout()
        self._net_label = QLabel("Net")
        self._net_label.setStyleSheet("color: #c586c0; font-size: 11px; font-weight: bold;")
        self._net_bar = self._create_progress_bar("#c586c0")
        self._net_value = QLabel("0 KB/s")
        self._net_value.setStyleSheet("color: rgba(255,255,255,120); font-size: 10px;")
        net_layout.addWidget(self._net_label)
        net_layout.addWidget(self._net_bar)
        net_layout.addWidget(self._net_value)
        net_layout.addStretch()
        sys_layout.addLayout(net_layout)

        layout.addWidget(sys_group)

        # 网络详情
        self._net_detail = QLabel()
        self._net_detail.setStyleSheet("color: rgba(255,255,255,100); font-size: 10px;")
        layout.addWidget(self._net_detail)

        # ===== 节点资源监控 =====
        node_group = QGroupBox(t("k_node_resources"))
        node_group.setStyleSheet("""
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
        node_layout = QVBoxLayout(node_group)
        node_layout.setContentsMargins(8, 4, 8, 8)

        # 表格
        self._node_table = QTableWidget()
        self._node_table.setColumnCount(4)
        self._node_table.setHorizontalHeaderLabels([
            t("k_node_name"), "CPU", t("k_memory"), t("k_status")
        ])
        self._node_table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(30, 30, 30, 200);
                border: none;
                gridline-color: rgba(255, 255, 255, 10);
                font-size: 11px;
            }
            QTableWidget::item {
                color: rgba(255, 255, 255, 180);
                padding: 4px;
            }
            QHeaderView::section {
                background-color: rgba(40, 40, 40, 200);
                color: rgba(255, 255, 255, 150);
                font-size: 10px;
                padding: 4px;
                border: none;
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

    def _create_progress_bar(self, color):
        """创建进度条"""
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{
                height: 8px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 10);
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        return bar

    def _update_stats(self):
        """更新资源统计"""
        # 更新系统资源
        self._system_stats['cpu_percent'] = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        self._system_stats['memory_percent'] = mem.percent
        self._system_stats['memory_used'] = mem.used
        self._system_stats['memory_total'] = mem.total

        disk = psutil.disk_usage('/')
        self._system_stats['disk_percent'] = disk.percent
        self._system_stats['disk_used'] = disk.used
        self._system_stats['disk_total'] = disk.total

        net = psutil.net_io_counters()
        sent_diff = net.bytes_sent - self._last_net_sent
        recv_diff = net.bytes_recv - self._last_net_recv
        self._last_net_sent = net.bytes_sent
        self._last_net_recv = net.bytes_recv

        self._system_stats['net_sent_per_sec'] = sent_diff
        self._system_stats['net_recv_per_sec'] = recv_diff

        # 更新UI
        self._cpu_bar.setValue(int(self._system_stats['cpu_percent']))
        self._cpu_value.setText(f"{self._system_stats['cpu_percent']}%")

        self._ram_bar.setValue(int(self._system_stats['memory_percent']))
        used_gb = self._system_stats['memory_used'] / (1024**3)
        total_gb = self._system_stats['memory_total'] / (1024**3)
        self._ram_value.setText(f"{used_gb:.1f}/{total_gb:.1f} GB ({self._system_stats['memory_percent']}%)")

        self._disk_bar.setValue(int(self._system_stats['disk_percent']))
        used_gb = self._system_stats['disk_used'] / (1024**3)
        total_gb = self._system_stats['disk_total'] / (1024**3)
        self._disk_value.setText(f"{used_gb:.1f}/{total_gb:.1f} GB ({self._system_stats['disk_percent']}%)")

        total_net = sent_diff + recv_diff
        self._net_bar.setValue(min(int(total_net / 1024 / 10), 100))
        self._net_value.setText(f"{total_net / 1024:.1f} KB/s")

        # 网络详情
        self._net_detail.setText(f"↓ {recv_diff / 1024:.1f} KB/s  ↑ {sent_diff / 1024:.1f} KB/s")

        # 更新节点资源
        self._update_node_stats()

    def _update_node_stats(self):
        """更新节点资源占用表"""
        if not self.parent_window:
            return

        canvas = getattr(self.parent_window, 'canvas', None)
        nodes_data = getattr(self.parent_window, 'nodes_data', {})

        # 如果画布不存在或画布上没有节点，清空节点统计
        if not canvas or not hasattr(canvas, 'nodes') or not canvas.nodes:
            self._node_stats.clear()
            self._update_node_table()
            return

        current_names = set(self._node_stats.keys())
        canvas_names = set(canvas.nodes.keys())

        # 移除已不在画布上的节点
        for name in current_names - canvas_names:
            if name in self._node_stats:
                del self._node_stats[name]

        # 更新节点资源
        for name in canvas_names:
            if name in nodes_data:
                node_info = nodes_data[name]
                self._update_single_node_stats(name, node_info)

        # 更新表格显示
        self._update_node_table()

    def _update_single_node_stats(self, node_name, node_info):
        """更新单个节点的资源统计"""
        pid = None
        if 'process' in node_info and node_info['process']:
            pid = node_info['process'].pid
        elif os.path.exists(os.path.join(node_info['path'], ".pid")):
            try:
                with open(os.path.join(node_info['path'], ".pid"), 'r') as f:
                    pid = int(f.read().strip())
            except:
                pass

        stats = {
            'name': node_info.get('name', node_name),
            'cpu': 0,
            'memory': 0,
            'status': node_info.get('status', 'stopped')
        }

        if pid and psutil.pid_exists(pid):
            try:
                process = psutil.Process(pid)
                cpu_total = 0
                mem_total = 0

                for child in process.children(recursive=True):
                    try:
                        cpu_total += child.cpu_percent()
                        mem_total += child.memory_info().rss
                    except:
                        pass

                try:
                    cpu_total += process.cpu_percent()
                    mem_total += process.memory_info().rss
                except:
                    pass

                stats['cpu'] = cpu_total
                stats['memory'] = (mem_total / (1024 ** 2))
                # 如果进程存在，强制设置状态为running（覆盖可能过期的状态）
                stats['status'] = 'running'
            except Exception as e:
                stats['status'] = 'stopped'
        else:
            # 如果没有pid或进程不存在，状态为stopped
            stats['status'] = 'stopped'

        self._node_stats[node_name] = stats
        
        # 发送信号给画布上的节点状态显示组件
        self.node_state_updated.emit(node_name, stats['cpu'], stats['memory'])

    def update_node_stats(self, node_stats):
        """更新节点资源统计（外部调用接口）"""
        self._node_stats = node_stats
        self._update_node_table()

    def _update_node_table(self):
        """更新节点表格"""
        self._node_table.setRowCount(len(self._node_stats))
        row = 0
        for node_id, stats in self._node_stats.items():
            name_item = QTableWidgetItem(stats.get('name', node_id))
            name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            
            cpu_item = QTableWidgetItem(f"{stats.get('cpu', 0.0):.1f}%")
            cpu_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            mem_item = QTableWidgetItem(f"{stats.get('memory', 0.0):.1f} MB")
            mem_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            mem_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            status = stats.get('status', 'stopped')
            status_text = t("k_status_running") if status == 'running' else t("k_status_stopped")
            status_item = QTableWidgetItem(status_text)
            status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if status == 'running':
                status_item.setForeground(QColor("#4ec9b0"))
            else:
                status_item.setForeground(QColor("#858585"))
            
            self._node_table.setItem(row, 0, name_item)
            self._node_table.setItem(row, 1, cpu_item)
            self._node_table.setItem(row, 2, mem_item)
            self._node_table.setItem(row, 3, status_item)
            row += 1

    def _on_node_status_changed(self, node_name, new_status):
        """处理全局节点状态变化信号"""
        if node_name in self._node_stats:
            self._node_stats[node_name]['status'] = new_status
            self._update_node_table()