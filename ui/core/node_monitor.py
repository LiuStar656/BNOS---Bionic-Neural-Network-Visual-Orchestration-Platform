"""
节点资源监控模块 — 实时收集节点的CPU、内存、运行时长等状态信息
"""
import psutil
import time
import threading
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from ui.core.logger import logger
from ui.core.node_process import start_node_process, stop_node_process, detect_running_nodes, _read_pid, _is_pid_alive


class NodeMonitor(QObject):
    """节点资源监控器"""
    
    # 状态更新信号
    status_updated = pyqtSignal(str, float, float, float)  # node_name, cpu_percent, mem_mb, duration_seconds
    
    def __init__(self):
        super().__init__()
        self._monitored_nodes = {}  # {node_name: {pid, start_time, cpu_history, mem_history}}
        self._monitor_thread = None
        self._running = False
        self._update_interval = 2  # 更新间隔（秒）
        
        # 使用QTimer进行定时更新
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_all_nodes)
        self._timer.setInterval(self._update_interval * 1000)
        
    def start_monitoring(self):
        """开始监控所有节点"""
        if not self._running:
            self._running = True
            self._timer.start()
            logger.info("节点监控模块已启动")
            
    def stop_monitoring(self):
        """停止监控"""
        if self._running:
            self._running = False
            self._timer.stop()
            self._monitored_nodes.clear()
            logger.info("节点监控模块已停止")
            
    def add_node(self, node_name, pid=None):
        """添加要监控的节点"""
        if node_name not in self._monitored_nodes:
            # 获取节点进程信息
            if not pid:
                # 尝试从节点目录读取PID
                import os
                node_path = os.path.join('nodes', node_name)
                pid = _read_pid(node_path)
            
            if pid and _is_pid_alive(pid):
                self._monitored_nodes[node_name] = {
                    'pid': pid,
                    'start_time': datetime.now(),
                    'cpu_history': [],
                    'mem_history': []
                }
                logger.debug(f"开始监控节点: {node_name} (PID: {pid})")
            else:
                logger.warning(f"无法获取节点 {node_name} 的有效PID，无法监控")
                
    def remove_node(self, node_name):
        """移除监控的节点"""
        if node_name in self._monitored_nodes:
            del self._monitored_nodes[node_name]
            logger.debug(f"停止监控节点: {node_name}")
            
    def update_node_pid(self, node_name, pid):
        """更新节点的PID"""
        if node_name in self._monitored_nodes:
            self._monitored_nodes[node_name]['pid'] = pid
            self._monitored_nodes[node_name]['start_time'] = datetime.now()
            logger.debug(f"更新节点PID: {node_name} -> {pid}")
            
    def get_node_status(self, node_name):
        """获取节点的当前状态"""
        if node_name not in self._monitored_nodes:
            return 0.0, 0.0, 0.0
            
        node_data = self._monitored_nodes[node_name]
        pid = node_data['pid']
        
        try:
            process = psutil.Process(pid)
            
            # 获取CPU占用率（取最近3次的平均值）
            cpu_percent = process.cpu_percent(interval=0.1)
            node_data['cpu_history'].append(cpu_percent)
            if len(node_data['cpu_history']) > 3:
                node_data['cpu_history'].pop(0)
            avg_cpu = sum(node_data['cpu_history']) / len(node_data['cpu_history'])
            
            # 获取内存使用
            mem_info = process.memory_info()
            mem_mb = mem_info.rss / (1024 * 1024)
            node_data['mem_history'].append(mem_mb)
            if len(node_data['mem_history']) > 3:
                node_data['mem_history'].pop(0)
            avg_mem = sum(node_data['mem_history']) / len(node_data['mem_history'])
            
            # 计算运行时长
            duration = datetime.now() - node_data['start_time']
            duration_seconds = duration.total_seconds()
            
            return avg_cpu, avg_mem, duration_seconds
            
        except psutil.NoSuchProcess:
            logger.warning(f"节点进程已结束: {node_name} (PID: {pid})")
            self.remove_node(node_name)
            return 0.0, 0.0, 0.0
        except Exception as e:
            logger.error(f"获取节点状态失败: {node_name}, 错误: {e}")
            return 0.0, 0.0, 0.0
            
    def _update_all_nodes(self):
        """更新所有监控节点的状态"""
        if not self._running:
            return
            
        node_names = list(self._monitored_nodes.keys())
        for node_name in node_names:
            cpu_percent, mem_mb, duration_seconds = self.get_node_status(node_name)
            self.status_updated.emit(node_name, cpu_percent, mem_mb, duration_seconds)
            
    def get_all_node_statuses(self):
        """获取所有节点的状态"""
        statuses = {}
        for node_name in self._monitored_nodes:
            cpu, mem, duration = self.get_node_status(node_name)
            statuses[node_name] = {
                'cpu_percent': cpu,
                'mem_mb': mem,
                'duration_seconds': duration
            }
        return statuses


# 全局单例
node_monitor = NodeMonitor()
