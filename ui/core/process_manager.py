"""
进程管理器 — 子进程启动/停止/崩溃监控/自动重启

管理所有子进程（画布、面板、核心业务）的生命周期。
"""
import os
import sys
import subprocess
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from ui.core.logger import logger

# 项目根目录（从 process_manager.py: ui/core/ → 项目根）
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_THIS_DIR))


class ManagedProcess(QObject):
    """受管理的子进程"""
    crashed = pyqtSignal(str)       # process_id
    started = pyqtSignal(str)
    stopped = pyqtSignal(str)

    def __init__(self, process_id: str, script_path: str, parent=None):
        super().__init__(parent)
        self.id = process_id
        self.script = script_path
        self.process = None
        self._restart_on_crash = True
        self._max_restarts = 5
        self._restart_count = 0
        self._health_timer = QTimer(self)
        self._health_timer.setInterval(2000)
        self._health_timer.timeout.connect(self._check_health)

    def start(self):
        if self.process and self.process.poll() is None:
            return True
        try:
            python = sys.executable
            self.process = subprocess.Popen(
                [python, self.script],
                cwd=_PROJECT_ROOT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            self._health_timer.start()
            self.started.emit(self.id)
            logger.info("子进程已启动: %s (PID=%d)", self.id, self.process.pid)
            return True
        except Exception as e:
            logger.error("启动子进程 %s 失败: %s", self.id, e)
            return False

    def stop(self):
        self._restart_on_crash = False
        self._health_timer.stop()
        if self.process:
            try:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)],
                                   capture_output=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    self.process.terminate()
                    self.process.wait(timeout=5)
            except Exception:
                pass
            self.process = None
        self.stopped.emit(self.id)
        logger.info("子进程已停止: %s", self.id)

    def restart(self):
        self.stop()
        self._restart_on_crash = True
        return self.start()

    def is_alive(self):
        return self.process is not None and self.process.poll() is None

    def _check_health(self):
        if not self.process:
            return
        exit_code = self.process.poll()
        if exit_code is not None:
            self._health_timer.stop()
            self.crashed.emit(self.id)
            logger.warning("子进程 %s 已退出 (exit=%d)", self.id, exit_code)
            if self._restart_on_crash and self._restart_count < self._max_restarts:
                self._restart_count += 1
                logger.info("正在重启子进程 %s (第 %d/%d 次)",
                            self.id, self._restart_count, self._max_restarts)
                self.start()
            else:
                logger.error("子进程 %s 已达到最大重启次数，停止重试", self.id)


class ProcessManager(QObject):
    """进程管理器，统一管理所有子进程"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._processes = {}   # process_id → ManagedProcess

    def register(self, process_id: str, script_path: str):
        proc = ManagedProcess(process_id, script_path, self)
        self._processes[process_id] = proc
        return proc

    def start(self, process_id: str):
        proc = self._processes.get(process_id)
        if proc:
            return proc.start()
        return False

    def stop(self, process_id: str):
        proc = self._processes.get(process_id)
        if proc:
            proc.stop()

    def stop_all(self):
        for proc in self._processes.values():
            proc.stop()

    def get(self, process_id: str):
        return self._processes.get(process_id)

    @property
    def all_alive(self):
        return all(p.is_alive() for p in self._processes.values())
