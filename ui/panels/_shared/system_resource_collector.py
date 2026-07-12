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

from __future__ import annotations

from pathlib import Path

import psutil

from ui.core.logger import logger


class SystemResourceCollector:
    """系统+节点资源数据采集器（纯数据层，不涉及 UI 渲染）"""

    def __init__(self):
        # 预热 psutil（第一次调用 cpu_percent 返回 0；net_io 防止首次差分为累计总量）
        psutil.cpu_percent()
        try:
            io = psutil.net_io_counters()
            self._last_net_sent = io.bytes_sent
            self._last_net_recv = io.bytes_recv
        except (psutil.AccessDenied, OSError):
            pass

    # ──── 系统级资源采集 ────

    def collect_system_stats(self) -> dict:
        """采集系统级资源（CPU/RAM/Disk/Net），返回标准化字典"""
        stats = {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used": 0,
            "memory_total": 0,
            "disk_percent": 0,
            "disk_used": 0,
            "disk_total": 0,
            "net_sent_per_sec": 0,
            "net_recv_per_sec": 0,
        }
        try:
            stats["cpu_percent"] = psutil.cpu_percent()

            mem = psutil.virtual_memory()
            stats["memory_percent"] = mem.percent
            stats["memory_used"] = mem.used
            stats["memory_total"] = mem.total

            disk = psutil.disk_usage("/")
            stats["disk_percent"] = disk.percent
            stats["disk_used"] = disk.used
            stats["disk_total"] = disk.total

            net = psutil.net_io_counters()
            sent_diff = net.bytes_sent - self._last_net_sent
            recv_diff = net.bytes_recv - self._last_net_recv
            self._last_net_sent = net.bytes_sent
            self._last_net_recv = net.bytes_recv
            stats["net_sent_per_sec"] = sent_diff
            stats["net_recv_per_sec"] = recv_diff
        except Exception as e:
            logger.warning("系统资源采集失败: %s", e)

        return stats

    # ──── 节点级资源采集 ────

    def resolve_node_pid(self, node_info: dict) -> int | None:
        """从 node_info 中解析进程 PID（优先 process.pid，其次 .pid 文件）"""
        if "process" in node_info and node_info["process"]:
            return node_info["process"].pid

        node_path = node_info.get("path", "")
        pid_file = Path(node_path) / ".pid"
        if not pid_file.exists():
            pid_file = Path(node_path) / "pid"

        if pid_file.exists():
            try:
                with pid_file.open() as f:
                    return int(f.read().strip())
            except (ValueError, OSError):
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
            "cpu": 0.0,
            "memory": 0.0,
            "memory_rss": 0,
            "status": node_info.get("status", "stopped"),
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
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                try:
                    cpu_total += process.cpu_percent()
                    mem_total += process.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

                stats["cpu"] = cpu_total
                stats["memory"] = mem_total / (1024**2)  # MB
                stats["memory_rss"] = mem_total
                stats["status"] = "running"  # 进程存在 → 强制为 running
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                stats["status"] = "stopped"
        else:
            stats["status"] = "stopped"

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
                stats["name"] = node_info.get("name", node_name)
                result[node_name] = stats
        return result

    # ──── 节点资源统计（pid 文件方式，供 NodeLogSubPanel 使用）────

    @staticmethod
    def get_node_pid(node_path: str) -> int | None:
        """根据节点路径获取进程 PID（优先 .pid 文件，回退到复合节点 PID）"""
        pid_file = Path(node_path) / ".pid"
        if not pid_file.exists():
            pid_file = Path(node_path) / "pid"
        if pid_file.exists():
            try:
                with pid_file.open() as f:
                    return int(f.read().strip())
            except (ValueError, OSError):
                pass

        # 回退：复合节点 PID 文件（位于项目根目录，不在节点目录下）
        try:
            p = Path(node_path)
            comp_id = p.name  # 节点目录名即 comp_id
            # 向上找项目根目录：通过 node_clusters.json 的存在性验证
            for parent in p.parents:
                if (parent / "node_clusters.json").exists():
                    comp_pid = parent / f"__composite_{comp_id}.pid"
                    if comp_pid.exists():
                        return int(comp_pid.read_text().strip())
                    break
        except (ValueError, OSError):
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
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            try:
                cpu_total += process.cpu_percent()
                mem_total += process.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            return cpu_total, mem_total / (1024**2)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None, None

    # ──── 复合节点资源组采集 ────

    @staticmethod
    def get_composite_pid(project_path: str, comp_id: str) -> int | None:
        """获取复合节点的 orchestrator PID。

        查找顺序:
          1. __composite_{comp_id}.pid（项目根目录）
          2. composite_nodes/<comp_id>/ 下的 node_registry.json 中各子节点 PID
        """
        # 方式 1: 项目根目录 pid 文件
        pid_file = Path(project_path) / f"__composite_{comp_id}.pid"
        if pid_file.exists():
            try:
                return int(pid_file.read_text().strip())
            except (ValueError, OSError):
                pass
        return None

    def collect_group_stats(self, project_path: str, comp_id: str, node_names: list[str], nodes_data: dict) -> dict:
        """采集复合节点资源组的总资源使用量。

        使用 orchestrator PID 进程树聚合所有子进程资源。

        Args:
            project_path: 项目根目录
            comp_id: 复合节点 ID
            node_names: 子节点名称列表
            nodes_data: 节点数据字典 {name: node_info}

        Returns:
            {
                'cpu': float,           # 总 CPU %
                'memory': float,        # 总内存 MB
                'memory_formatted': str, # 格式化显示
                'status': str,          # 'running' | 'stopped'
                'child_count': int,     # 子节点数量
            }
        """
        result = {
            "cpu": 0.0,
            "memory": 0.0,
            "memory_formatted": "0 MB",
            "status": "stopped",
            "child_count": len(node_names),
        }

        pid = self.get_composite_pid(project_path, comp_id)
        if pid and psutil.pid_exists(pid):
            cpu, mem = self.collect_process_resources(pid)
            if cpu is not None and mem is not None:
                result["cpu"] = cpu
                result["memory"] = mem
                result["memory_formatted"] = self._format_memory(mem)
                result["status"] = "running"
                return result

        # 回退：聚合各独立运行子节点的资源
        cpu_total = 0.0
        mem_total = 0.0
        any_running = False
        for n in node_names:
            if n in nodes_data:
                stats = self.collect_single_node_stats(nodes_data[n], n)
                if stats["status"] == "running":
                    cpu_total += stats["cpu"]
                    mem_total += stats["memory"]
                    any_running = True
        if any_running:
            result["cpu"] = cpu_total
            result["memory"] = mem_total
            result["memory_formatted"] = self._format_memory(mem_total)
            result["status"] = "running"
        return result

    @staticmethod
    def _format_memory(memory_mb: float) -> str:
        """格式化内存大小为人类可读字符串。"""
        if memory_mb < 1024:
            return f"{memory_mb:.1f} MB"
        return f"{memory_mb / 1024:.2f} GB"


# 全局单例（供两个面板共享，避免各自维护 psutil 状态）
shared_resource_collector = SystemResourceCollector()
