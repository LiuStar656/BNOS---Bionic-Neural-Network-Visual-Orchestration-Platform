"""
终端进程 - 封装 QProcess 管理子进程
"""

from __future__ import annotations

import platform
import re

from PySide6.QtCore import QObject, QProcess, Signal

from ui.core.logger import logger


class TerminalProcess(QObject):
    """终端进程 - 封装 QProcess"""

    output_received = Signal(str)
    error_received = Signal(str)
    process_started = Signal()
    process_finished = Signal(int)

    def __init__(self, working_dir: str = None):
        super().__init__()
        self.process = QProcess()  # 无 parent，避免 Qt C++ 树先于 __del__ 清理时误报 Destroyed warning
        self.working_dir = working_dir
        self._stopped = False

        # 连接信号
        self.process.readyReadStandardOutput.connect(self._on_stdout)
        self.process.readyReadStandardError.connect(self._on_stderr)
        self.process.started.connect(self.process_started)
        self.process.finished.connect(self.process_finished)

        if working_dir:
            self.process.setWorkingDirectory(working_dir)

    def _strip_ansi(self, text: str) -> str:
        """去除 ANSI 转义序列"""
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[.*?[a-zA-Z])")
        return ansi_escape.sub("", text)

    def start(self, terminal_type: str = "powershell"):
        """启动终端"""
        system = platform.system()
        program = ""
        args = []

        if system == "Windows":
            if terminal_type == "powershell":
                program = "powershell.exe"
                args = ["-NoExit", "-NonInteractive"]
            elif terminal_type == "cmd":
                program = "cmd.exe"
                args = ["/k"]
        elif system == "Darwin":
            program = "bash"
        else:
            program = "bash"

        logger.info(f"启动终端: {program} {args}, 工作目录: {self.working_dir}")
        self.process.start(program, args)

    def write(self, command: str):
        """写入命令到终端"""
        self.process.write((command + "\n").encode("utf-8"))

    def _on_stdout(self):
        """处理标准输出"""
        data_bytes = self.process.readAllStandardOutput().data()
        try:
            data = data_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                data = data_bytes.decode("gbk")
            except Exception:
                data = data_bytes.decode("utf-8", errors="replace")

        data = self._strip_ansi(data)
        self.output_received.emit(data)

    def _on_stderr(self):
        """处理标准错误"""
        data_bytes = self.process.readAllStandardError().data()
        try:
            data = data_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                data = data_bytes.decode("gbk")
            except Exception:
                data = data_bytes.decode("utf-8", errors="replace")

        data = self._strip_ansi(data)
        self.error_received.emit(data)

    def stop(self):
        """安全终止子进程"""
        if self._stopped:
            return
        self._stopped = True

        try:
            state = self.process.state()
        except RuntimeError:
            # C++ 对象已被 Qt 销毁（如父控件先于本对象被 GC）
            return

        if state == QProcess.ProcessState.NotRunning:
            logger.debug("TerminalProcess: 进程已结束，无需终止")
            self._disconnect_process()
            return

        pid = self.process.processId()
        logger.info("TerminalProcess: 正在终止子进程 (PID=%d)...", pid if pid else 0)
        # 先尝试温和终止（Windows 上对控制台进程无效，但仍尝试）
        self.process.terminate()
        if not self.process.waitForFinished(3000):
            # 3秒内未退出则强制杀死
            logger.warning("TerminalProcess: 子进程未响应终止信号，强制杀死")
            self.process.kill()
            if not self.process.waitForFinished(2000):
                # QProcess.kill() 也未奏效，用系统级 taskkill 兜底
                logger.warning("TerminalProcess: QProcess.kill() 失败，尝试 taskkill")
                self._os_kill(pid)
        logger.info("TerminalProcess: 子进程已终止")
        # 断开信号连接，防止析构时残留回调
        self._disconnect_process()
        # 关闭 QProcess 通道
        try:
            self.process.close()
        except RuntimeError:
            pass

    def _os_kill(self, pid: int):
        """系统级强制杀进程"""
        if not pid or pid <= 0:
            return
        try:
            import os
            import subprocess

            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                import signal

                os.kill(pid, signal.SIGKILL)
        except Exception as e:
            logger.warning("TerminalProcess: OS kill 失败: %s", e)

    def _disconnect_process(self):
        """断开 QProcess 的所有信号连接，防止析构时触发回调"""
        try:
            self.process.readyReadStandardOutput.disconnect()
        except (RuntimeError, TypeError):
            pass
        try:
            self.process.readyReadStandardError.disconnect()
        except (RuntimeError, TypeError):
            pass
        try:
            self.process.started.disconnect()
        except (RuntimeError, TypeError):
            pass
        try:
            self.process.finished.disconnect()
        except (RuntimeError, TypeError):
            pass

    def dispose(self):
        """显式清理：终止子进程并断开信号。

        调用方应在 TerminalWidget.close_terminal() 中显式调用此方法，
        不依赖 __del__ 不确定性清理。
        """
        self.stop()
        # 帮助 Qt 尽早释放 C++ 资源
        try:
            self.process.deleteLater()
        except RuntimeError:
            pass
