"""
系统资源数据采集器 — 纯数据层，不涉及 UI

为 ResourceMonitor(浮动版) 和 ResourceMonitorDock(Dock版) 提供统一的
系统资源和节点资源数据采集逻辑。

用法:
    from ui.panels._shared.system_resource_collector import SystemResourceCollector
    
    collector = SystemResourceCollector()
    sys_stats = collector.collect_system_stats()
    node_stats = collector.collect_node_stats(canvas_nodes, nodes_data)
"""
import os
import psutil
from ui.core.logger import logger


class SystemResourceCollector:
    """系统+节点资源数据采集器（纯数据层，不涉及 UI 渲染）"""

    def __init__(self):
        self._last_net_sent = 0
        self._last_net_recv = 0
        # 预热 psutil（第一次调用 cpu_percent 返回 0）
        psutil.cpu_percent()
        try:
            psutil.net_io_counters()
        except Exception:
            pass

    # ──── 系统级资源采集 ────

    def collect_system_stats(self) -> dict:
        """采集系统级资源（CPU/RAM/Disk/Net），返回标准化字典"""
        stats = {
            'cpu_percent': 0,
            'memory_percent': 0,
            'memory_used': 0,
            'memory_total': 0,
            'disk_percent': 0,
            'disk_used': 0,
            'disk_total': 0,
            'net_sent_per_sec': 0,
            'net_recv_per_sec': 0,
        }
        try:
            stats['cpu_percent'] = psutil.cpu_percent()

            mem = psutil.virtual_memory()
            stats['memory_percent'] = mem.percent
            stats['memory_used'] = mem.used
            stats['memory_total'] = mem.total

            disk = psutil.disk_usage('/')
            stats['disk_percent'] = disk.percent
            stats['disk_used'] = disk.used
            stats['disk_total'] = disk.total

            net = psutil.net_io_counters()
            sent_diff = net.bytes_sent - self._last_net_sent
            recv_diff = net.bytes_recv - self._last_net_recv
            self._last_net_sent = net.bytes_sent
            self._last_net_recv = net.bytes_recv
            stats['net_sent_per_sec'] = sent_diff
            stats['net_recv_per_sec'] = recv_diff
        except Exception as e:
            logger.warning("系统资源采集失败: %s", e)

        return stats

    # ──── 节点级资源采集 ────

    def resolve_node_pid(self, node_info: dict) -> int | None:
        """从 node_info 中解析进程 PID（优先 process.pid，其次 .pid 文件）"""
        if 'process' in node_info and node_info['process']:
            return node_info['process'].pid

        pid_file = os.path.join(node_info.get('path', ''), '.pid')
        if not os.path.exists(pid_file):
            pid_file = os.path.join(node_info.get('path', ''), 'pid')

        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    return int(f.read().strip())
            except Exception:
                pass
        return None

    def collect_single_node_stats(self, node_info: dict, node_name: str = "") -> dict:
        """采集单个节点的资源统计（PID 检测 + 进程树遍历）

        Args:
            node_info: 节点数据字典（含 path, process, status 字段）
            node_name: 节点名称（用于日志）

        Returns:
            {'cpu': float, 'memory': float, 'memory_rss': int, 'status': str}
        """
        pid = self.resolve_node_pid(node_info)

        stats = {
            'cpu': 0.0,
            'memory': 0.0,
            'memory_rss': 0,
            'status': node_info.get('status', 'stopped'),
        }

        if pid and psutil.pid_exists(pid):
            try:
                process = psutil.Process(pid)
                cpu_total = 0.0
                mem_total = 0

                for child in process.children(recursive=True):
                    try:
                        cpu_total += child.cpu_percent()
                        mem_total += child.memory_info().rss
                    except Exception:
                        pass

                try:
                    cpu_total += process.cpu_percent()
                    mem_total += process.memory_info().rss
                except Exception:
                    pass

                stats['cpu'] = cpu_total
                stats['memory'] = mem_total / (1024 ** 2)  # MB
                stats['memory_rss'] = mem_total
                stats['status'] = 'running'  # 进程存在 → 强制为 running
            except Exception:
                stats['status'] = 'stopped'
        else:
            stats['status'] = 'stopped'

        return stats

    def collect_all_node_stats(self, canvas_nodes: dict, nodes_data: dict) -> dict:
        """批量采集画布上所有节点的资源统计

        Args:
            canvas_nodes: 画布节点字典 {name: NodeItem}
            nodes_data: 主窗口节点数据字典 {name: node_info}

        Returns:
            {node_name: {cpu, memory, memory_rss, name, status}}
        """
        result = {}
        for node_name in canvas_nodes:
            if node_name in nodes_data:
                node_info = nodes_data[node_name]
                stats = self.collect_single_node_stats(node_info, node_name)
                stats['name'] = node_info.get('name', node_name)
                result[node_name] = stats
        return result

    # ──── 节点资源统计（pid 文件方式，供 NodeLogSubPanel 使用）────

    @staticmethod
    def get_node_pid(node_path: str) -> int | None:
        """根据节点路径获取进程 PID（优先 .pid 文件）"""
        pid_file = os.path.join(node_path, '.pid')
        if not os.path.exists(pid_file):
            pid_file = os.path.join(node_path, 'pid')
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    return int(f.read().strip())
            except Exception:
                pass
        return None

    @staticmethod
    def collect_process_resources(pid: int) -> tuple[float, float] | tuple[None, None]:
        """采集指定 PID 的 CPU 和内存占用（含子进程）

        Returns:
            (cpu_percent, memory_mb) 或 (None, None)
        """
        if not pid or not psutil.pid_exists(pid):
            return None, None

        try:
            process = psutil.Process(pid)
            cpu_total = 0.0
            mem_total = 0

            for child in process.children(recursive=True):
                try:
                    cpu_total += child.cpu_percent()
                    mem_total += child.memory_info().rss
                except Exception:
                    pass

            try:
                cpu_total += process.cpu_percent()
                mem_total += process.memory_info().rss
            except Exception:
                pass

            return cpu_total, mem_total / (1024 ** 2)
        except Exception:
            return None, None


# 全局单例（供两个面板共享，避免各自维护 psutil 状态）
shared_resource_collector = SystemResourceCollector()
