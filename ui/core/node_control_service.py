"""
节点控制服务，负责管理节点的启动、停止和其他操作

【统一重构】本服务现在委托给 node_process.py 的标准化实现，
消除代码重复，保证行为一致性。
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
    QUEUED = "queued"
    BLOCKED = "blocked"
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
    """节点控制服务 — 统一委托给 node_process.py"""

    def __init__(self):
        self.nodes: Dict[str, NodeInfo] = {}
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self._status_callbacks: List[Callable] = []
        self._monitor_threads: Dict[str, QThread] = {}

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

        from ui.core.node_process import start_node_process

        try:
            node_info.status = NodeStatus.STARTING
            self._notify(name, NodeStatus.STARTING)

            node_dict = {
                "path": node_info.path,
                "name": name,
                "config": {},
                "process": None,
                "status": "stopped"
            }

            success, error = start_node_process(node_dict)

            if success:
                node_info.process = node_dict.get('process')
                node_info.pid = node_dict.get('process').pid if node_dict.get('process') else None
                node_info.status = NodeStatus.RUNNING
                self._active_processes[name] = node_info.process
                self._notify(name, NodeStatus.RUNNING)
                self._monitor(name, node_info.process)
                return True
            else:
                logger.error("启动节点 %s 失败: %s", name, error)
                node_info.status = NodeStatus.ERROR
                self._notify(name, NodeStatus.ERROR)
                return False
        except Exception as e:
            logger.error("启动节点 %s 失败: %s", name, e)
            node_info.status = NodeStatus.ERROR
            self._notify(name, NodeStatus.ERROR)
            return False

    def stop_node(self, name: str) -> bool:
        if name not in self.nodes:
            return False
        node_info = self.nodes[name]
        if node_info.status not in [NodeStatus.RUNNING, NodeStatus.STARTING]:
            return False

        from ui.core.node_process import stop_node_process

        try:
            node_info.status = NodeStatus.STOPPING
            self._notify(name, NodeStatus.STOPPING)

            node_dict = {
                "path": node_info.path,
                "process": node_info.process
            }

            success, error = stop_node_process(node_dict)

            if success:
                node_info.process = None
                node_info.pid = None
                node_info.status = NodeStatus.STOPPED
                self._notify(name, NodeStatus.STOPPED)
                return True
            else:
                logger.error("停止节点 %s 失败: %s", name, error)
                node_info.status = NodeStatus.ERROR
                self._notify(name, NodeStatus.ERROR)
                return False
        except Exception as e:
            logger.error("停止节点 %s 失败: %s", name, e)
            node_info.status = NodeStatus.ERROR
            self._notify(name, NodeStatus.ERROR)
            return False
        finally:
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
        def run():
            try:
                process.wait()
                if name in self.nodes and name not in self._active_processes:
                    self.nodes[name].status = NodeStatus.ERROR
                    self._notify(name, NodeStatus.ERROR)
            except Exception as e:
                logger.warning("节点 %s 监控异常: %s", name, e)
        self._cleanup_monitor_thread(name)
        monitor_thread = QThread()
        monitor_worker = QObject()
        monitor_worker.moveToThread(monitor_thread)
        monitor_thread.started.connect(run)
        monitor_thread.finished.connect(monitor_thread.deleteLater)
        self._monitor_threads[name] = monitor_thread
        monitor_thread.start()

    def _cleanup_monitor_thread(self, name: str):
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
