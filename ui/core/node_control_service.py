"""
节点控制服务，负责管理节点的启动、停止和其他操作
"""
from typing import Dict, List, Optional, Callable
from PySide6.QtCore import QObject, QThread
from pathlib import Path
from ui.core.logger import logger
import subprocess
import os
import signal
from enum import Enum


class NodeStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class NodeInfo:
    def __init__(self, name: str, path: str, pid: int = None, status: NodeStatus = NodeStatus.STOPPED):
        self.name = name
        self.path = path
        self.pid = pid
        self.status = status
        self.process: Optional[subprocess.Popen] = None


class NodeControlService:
    """节点控制服务"""

    def __init__(self):
        self.nodes: Dict[str, NodeInfo] = {}
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self._status_callbacks: List[Callable] = []
        self._monitor_threads: Dict[str, QThread] = {}   # 可追踪的监控线程

    def register_node(self, name: str, path: str):
        self.nodes[name] = NodeInfo(name, path)

    def unregister_node(self, name: str):
        if name in self.nodes:
            if self.nodes[name].status == NodeStatus.RUNNING:
                self.stop_node(name)
            del self.nodes[name]

    def start_node(self, name: str) -> bool:
        if name not in self.nodes:
            return False
        node_info = self.nodes[name]
        if node_info.status != NodeStatus.STOPPED:
            return False
        try:
            node_info.status = NodeStatus.STARTING
            self._notify(name, NodeStatus.STARTING)
            node_path = Path(node_info.path)
            # 检测节点类型
            if (node_path / "main.py").exists():
                cmd = ["python", str(node_path / "main.py")]
            elif (node_path / "index.js").exists():
                cmd = ["node", str(node_path / "index.js")]
            elif (node_path / "Cargo.toml").exists():
                cmd = ["cargo", "run"]
            else:
                cmd = ["python", str(node_path / "main.py")]
            cwd = str(node_path)
            process = subprocess.Popen(
                cmd, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            node_info.process = process
            node_info.pid = process.pid
            self._active_processes[name] = process
            node_info.status = NodeStatus.RUNNING
            self._notify(name, NodeStatus.RUNNING)
            self._monitor(name, process)
            return True
        except Exception as e:
            logger.error("启动节点 %s 失败: %s", name, e)
            node_info.status = NodeStatus.ERROR
            self._notify(name, NodeStatus.ERROR)
            return False

    def stop_node(self, name: str) -> bool:
        if name not in self.nodes or name not in self._active_processes:
            return False
        node_info = self.nodes[name]
        if node_info.status not in [NodeStatus.RUNNING, NodeStatus.STARTING]:
            return False
        try:
            node_info.status = NodeStatus.STOPPING
            self._notify(name, NodeStatus.STOPPING)
            process = self._active_processes[name]
            if os.name == 'nt':
                process.terminate()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if os.name == 'nt':
                    process.kill()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.wait()
            node_info.process = None
            node_info.pid = None
            node_info.status = NodeStatus.STOPPED
            self._notify(name, NodeStatus.STOPPED)
            return True
        except Exception as e:
            logger.error("停止节点 %s 失败: %s", name, e)
            node_info.status = NodeStatus.ERROR
            self._notify(name, NodeStatus.ERROR)
            return False
        finally:
            # 无论成功与否，清理进程引用和监控线程
            self._active_processes.pop(name, None)
            self._cleanup_monitor_thread(name)

    def stop_all_nodes(self):
        for name in list(self._active_processes.keys()):
            self.stop_node(name)

    def get_node_status(self, name: str) -> Optional[NodeStatus]:
        if name in self.nodes:
            return self.nodes[name].status
        return None

    def _monitor(self, name: str, process: subprocess.Popen):
        """监控节点进程退出（线程可追踪、可清理）"""
        def run():
            try:
                process.wait()
                if name in self.nodes and name not in self._active_processes:
                    self.nodes[name].status = NodeStatus.ERROR
                    self._notify(name, NodeStatus.ERROR)
            except Exception as e:
                logger.warning("节点 %s 监控异常: %s", name, e)
        # 先清理旧线程
        self._cleanup_monitor_thread(name)
        monitor_thread = QThread()
        monitor_worker = QObject()
        monitor_worker.moveToThread(monitor_thread)
        monitor_thread.started.connect(run)
        monitor_thread.finished.connect(monitor_thread.deleteLater)
        self._monitor_threads[name] = monitor_thread
        monitor_thread.start()

    def _cleanup_monitor_thread(self, name: str):
        """清理指定节点的监控线程"""
        thread = self._monitor_threads.pop(name, None)
        if thread and thread.isRunning():
            thread.quit()
            thread.wait(1000)

    def _notify(self, name: str, status: NodeStatus):
        for cb in self._status_callbacks:
            try:
                cb(name, status)
            except Exception as e:
                logger.warning("状态回调异常: %s", e)

    def subscribe(self, callback: Callable):
        self._status_callbacks.append(callback)

    def unsubscribe(self, callback: Callable):
        try:
            self._status_callbacks.remove(callback)
        except ValueError:
            pass


# 全局实例
node_control_service = NodeControlService()
