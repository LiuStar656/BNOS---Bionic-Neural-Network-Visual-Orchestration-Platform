"""
硬件资源监测面板 - 实时显示CPU、内存、磁盘、网络占用
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
from ui.core.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.polling_manager import polling_manager


class ResourceMonitor(FloatingPanel):
    """硬件资源监测面板（浮动半透明悬浮窗）"""

    def __init__(self, parent=None):
        super().__init__(parent, title=t("k_resource_monitor"))
        
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

        # psutil预热：第一次调用cpu_percent会返回0，需要先调用一次
        psutil.cpu_percent()
        psutil.net_io_counters()

        self.resize(450, 550)
        self.setMinimumSize(380, 400)
        self._init_ui()

        # 定时刷新（每秒更新）
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_stats)
        self._update_timer.start(1000)

        # 延迟500ms后第一次更新，确保psutil有足够时间获取数据
        QTimer.singleShot(500, self._update_stats)

    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
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
        sys_layout.setSpacing(6)

        # 第一行：CPU、RAM、Disk 水平排列
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # CPU
        cpu_widget = QWidget()
        cpu_layout = QVBoxLayout(cpu_widget)
        cpu_layout.setContentsMargins(0, 0, 0, 0)
        cpu_layout.setSpacing(2)
        cpu_label = QLabel("CPU")
        cpu_label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: bold;")
        cpu_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cpu_bar_widget = QProgressBar()
        self._cpu_bar_widget.setRange(0, 100)
        self._cpu_bar_widget.setValue(0)
        self._cpu_bar_widget.setFixedWidth(90)
        self._cpu_bar_widget.setStyleSheet("""
            QProgressBar {
                height: 10px;
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 10);
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        self._cpu_value_label = QLabel("0%")
        self._cpu_value_label.setStyleSheet("color: rgba(255,255,255,120); font-size: 9px;")
        self._cpu_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cpu_layout.addWidget(cpu_label)
        cpu_layout.addWidget(self._cpu_bar_widget)
        cpu_layout.addWidget(self._cpu_value_label)
        top_row.addWidget(cpu_widget)

        # RAM
        ram_widget = QWidget()
        ram_layout = QVBoxLayout(ram_widget)
        ram_layout.setContentsMargins(0, 0, 0, 0)
        ram_layout.setSpacing(2)
        ram_label = QLabel("RAM")
        ram_label.setStyleSheet("color: #2196F3; font-size: 11px; font-weight: bold;")
        ram_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ram_bar_widget = QProgressBar()
        self._ram_bar_widget.setRange(0, 100)
        self._ram_bar_widget.setValue(0)
        self._ram_bar_widget.setFixedWidth(90)
        self._ram_bar_widget.setStyleSheet("""
            QProgressBar {
                height: 10px;
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 10);
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 5px;
            }
        """)
        self._ram_value_label = QLabel("0%")
        self._ram_value_label.setStyleSheet("color: rgba(255,255,255,120); font-size: 9px;")
        self._ram_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ram_layout.addWidget(ram_label)
        ram_layout.addWidget(self._ram_bar_widget)
        ram_layout.addWidget(self._ram_value_label)
        top_row.addWidget(ram_widget)

        # Disk
        disk_widget = QWidget()
        disk_layout = QVBoxLayout(disk_widget)
        disk_layout.setContentsMargins(0, 0, 0, 0)
        disk_layout.setSpacing(2)
        disk_label = QLabel("Disk")
        disk_label.setStyleSheet("color: #FF9800; font-size: 11px; font-weight: bold;")
        disk_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._disk_bar_widget = QProgressBar()
        self._disk_bar_widget.setRange(0, 100)
        self._disk_bar_widget.setValue(0)
        self._disk_bar_widget.setFixedWidth(90)
        self._disk_bar_widget.setStyleSheet("""
            QProgressBar {
                height: 10px;
                border-radius: 5px;
                background-color: rgba(255, 255, 255, 10);
            }
            QProgressBar::chunk {
                background-color: #FF9800;
                border-radius: 5px;
            }
        """)
        self._disk_value_label = QLabel("0%")
        self._disk_value_label.setStyleSheet("color: rgba(255,255,255,120); font-size: 9px;")
        self._disk_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        disk_layout.addWidget(disk_label)
        disk_layout.addWidget(self._disk_bar_widget)
        disk_layout.addWidget(self._disk_value_label)
        top_row.addWidget(disk_widget)

        top_row.addStretch()
        sys_layout.addLayout(top_row)

        # 第二行：网络
        net_layout = QHBoxLayout()
        net_label = QLabel("Net")
        net_label.setStyleSheet("color: #9C27B0; font-size: 11px; font-weight: bold;")
        self._net_bar_widget = QProgressBar()
        self._net_bar_widget.setRange(0, 100)
        self._net_bar_widget.setValue(0)
        self._net_bar_widget.setStyleSheet("""
            QProgressBar {
                height: 8px;
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 10);
            }
            QProgressBar::chunk {
                background-color: #9C27B0;
                border-radius: 4px;
            }
        """)
        self._net_value_label = QLabel("0 KB/s")
        self._net_value_label.setStyleSheet("color: rgba(255,255,255,120); font-size: 10px;")
        net_layout.addWidget(net_label)
        net_layout.addWidget(self._net_bar_widget)
        net_layout.addWidget(self._net_value_label)
        net_layout.addStretch()
        sys_layout.addLayout(net_layout)

        # 网络详情
        self._net_layout = QHBoxLayout()
        self._net_sent_label = QLabel("↓ 0 KB/s")
        self._net_recv_label = QLabel("↑ 0 KB/s")
        self._net_sent_label.setStyleSheet("color: #4CAF50; font-size: 10px;")
        self._net_recv_label.setStyleSheet("color: #F44336; font-size: 10px;")
        self._net_layout.addWidget(self._net_sent_label)
        self._net_layout.addStretch()
        self._net_layout.addWidget(self._net_recv_label)
        sys_layout.addLayout(self._net_layout)

        layout.addWidget(sys_group)

        # ===== 节点资源占用 =====
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

        self._node_table = QTableWidget()
        self._node_table.setColumnCount(4)
        self._node_table.setHorizontalHeaderLabels([
            t("k_node_name"), t("k_cpu"), t("k_memory"), t("k_status")
        ])
        self._node_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._node_table.verticalHeader().setVisible(False)
        self._node_table.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a1a;
                color: #b0b0b0;
                border: 1px solid rgba(255, 255, 255, 10);
                border-radius: 3px;
                font-size: 11px;
            }
            QHeaderView::section {
                background-color: #2d2d30;
                color: #d4d4d4;
                font-size: 10px;
                padding: 4px;
                border: none;
            }
            QTableWidget::item {
                padding: 4px;
            }
        """)
        node_layout.addWidget(self._node_table)

        layout.addWidget(node_group)

        self.content_layout.addLayout(layout)

    def _create_progress_bar(self, label, color):
        """创建带标签的进度条"""
        bar_layout = QVBoxLayout()
        
        # 标签行
        label_layout = QHBoxLayout()
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
        value_widget = QLabel("0%")
        value_widget.setStyleSheet("color: rgba(255, 255, 255, 150); font-size: 11px;")
        label_layout.addWidget(label_widget)
        label_layout.addStretch()
        label_layout.addWidget(value_widget)
        bar_layout.addLayout(label_layout)

        # 进度条
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 10);
                border-radius: 4px;
                height: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        bar_layout.addWidget(bar)

        # 存储引用
        bar_layout.label_widget = label_widget
        bar_layout.value_widget = value_widget
        bar_layout.bar = bar
        bar_layout.color = color

        return bar_layout

    def _update_stats(self):
        """更新系统和节点资源统计"""
        # 更新系统资源
        try:
            # CPU
            self._system_stats['cpu_percent'] = psutil.cpu_percent()
            self._cpu_bar_widget.setValue(int(self._system_stats['cpu_percent']))
            self._cpu_value_label.setText(f"{self._system_stats['cpu_percent']}%")

            # 内存
            mem = psutil.virtual_memory()
            self._system_stats['memory_percent'] = mem.percent
            self._system_stats['memory_used'] = mem.used
            self._system_stats['memory_total'] = mem.total
            self._ram_bar_widget.setValue(int(self._system_stats['memory_percent']))
            used_gb = self._system_stats['memory_used'] / (1024 ** 3)
            total_gb = self._system_stats['memory_total'] / (1024 ** 3)
            self._ram_value_label.setText(f"{used_gb:.1f}/{total_gb:.1f} GB ({self._system_stats['memory_percent']}%)")

            # 磁盘
            disk = psutil.disk_usage('/')
            self._system_stats['disk_percent'] = disk.percent
            self._system_stats['disk_used'] = disk.used
            self._system_stats['disk_total'] = disk.total
            self._disk_bar_widget.setValue(int(self._system_stats['disk_percent']))
            used_gb = self._system_stats['disk_used'] / (1024 ** 3)
            total_gb = self._system_stats['disk_total'] / (1024 ** 3)
            self._disk_value_label.setText(f"{used_gb:.1f}/{total_gb:.1f} GB ({self._system_stats['disk_percent']}%)")

            # 网络
            net = psutil.net_io_counters()
            sent_diff = net.bytes_sent - self._last_net_sent
            recv_diff = net.bytes_recv - self._last_net_recv
            self._last_net_sent = net.bytes_sent
            self._last_net_recv = net.bytes_recv

            sent_kb = sent_diff / 1024
            recv_kb = recv_diff / 1024
            total_kb = sent_kb + recv_kb
            
            # 计算网络利用率（基于理论最大带宽估算）
            max_bandwidth_kb = 100000  # 假设最大100MB/s
            net_percent = min((total_kb / max_bandwidth_kb) * 100, 100)
            
            self._net_bar_widget.setValue(int(net_percent))
            self._net_value_label.setText(f"{total_kb:.1f} KB/s")
            self._net_sent_label.setText(f"↓ {recv_kb:.1f} KB/s")
            self._net_recv_label.setText(f"↑ {sent_kb:.1f} KB/s")

        except Exception as e:
            print(f"Error updating system stats: {e}")

        # 更新节点资源
        self._update_node_stats()

    def _update_node_stats(self):
        """更新节点资源占用表"""
        if not self.parent_window:
            return

        canvas = getattr(self.parent_window, 'canvas', None)
        if not canvas:
            return

        nodes_data = getattr(self.parent_window, 'nodes_data', {})
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
        self._refresh_node_table()

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
            'cpu': 0,
            'memory': 0,
            'memory_rss': 0,
            'status': node_info.get('status', 'stopped')
        }

        if pid and psutil.pid_exists(pid):
            try:
                process = psutil.Process(pid)
                # 获取进程及其子进程的总资源占用
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
                stats['memory'] = (mem_total / (1024 ** 2))  # MB
                stats['memory_rss'] = mem_total
                stats['status'] = node_info.get('status', 'running')
            except Exception as e:
                stats['status'] = 'stopped'

        self._node_stats[node_name] = stats

    def _refresh_node_table(self):
        """刷新节点资源表"""
        self._node_table.setRowCount(len(self._node_stats))
        
        for i, (name, stats) in enumerate(self._node_stats.items()):
            # 节点名称
            name_item = QTableWidgetItem(name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            
            # CPU占用
            cpu_item = QTableWidgetItem(f"{stats['cpu']:.1f}%")
            cpu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            # 内存占用
            mem_item = QTableWidgetItem(f"{stats['memory']:.1f} MB")
            mem_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            # 状态
            status_text = {
                'running': t("k_status_running"),
                'idle': t("k_status_idle"),
                'stopped': t("k_status_stopped")
            }.get(stats['status'], stats['status'])
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            
            # 设置状态颜色
            if stats['status'] == 'running':
                status_item.setForeground(QColor("#4CAF50"))
            elif stats['status'] == 'idle':
                status_item.setForeground(QColor("#F0A030"))
            else:
                status_item.setForeground(QColor("#999"))

            self._node_table.setItem(i, 0, name_item)
            self._node_table.setItem(i, 1, cpu_item)
            self._node_table.setItem(i, 2, mem_item)
            self._node_table.setItem(i, 3, status_item)

    def _on_node_status_changed(self, node_name, new_status):
        """处理全局节点状态变化信号"""
        if node_name in self._node_stats:
            self._node_stats[node_name]['status'] = new_status
            self._refresh_node_table()

    def _on_close(self):
        """关闭时清理"""
        self._update_timer.stop()
        super()._on_close()

    def get_system_stats(self):
        """获取当前系统资源统计"""
        return self._system_stats.copy()

    def get_node_stats(self):
        """获取当前节点资源统计"""
        return self._node_stats.copy()