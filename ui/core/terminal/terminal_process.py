"""
终端进程 - 封装 QProcess 管理子进程
"""
import platform
import re
from PyQt6.QtCore import QProcess, QObject, pyqtSignal
from ui.core.logger import logger


class TerminalProcess(QObject):
    """终端进程 - 封装 QProcess"""

    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    process_started = pyqtSignal()
    process_finished = pyqtSignal(int)

    def __init__(self, working_dir: str = None):
        super().__init__()
        self.process = QProcess()
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
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[.*?[a-zA-Z])')
        return ansi_escape.sub('', text)

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
        self.process.write((command + "\n").encode('utf-8'))

    def _on_stdout(self):
        """处理标准输出"""
        data_bytes = self.process.readAllStandardOutput().data()
        try:
            data = data_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                data = data_bytes.decode('gbk')
            except Exception:
                data = data_bytes.decode('utf-8', errors='replace')
        
        data = self._strip_ansi(data)
        self.output_received.emit(data)

    def _on_stderr(self):
        """处理标准错误"""
        data_bytes = self.process.readAllStandardError().data()
        try:
            data = data_bytes.decode('utf-8')
        except UnicodeDecodeError:
            try:
                data = data_bytes.decode('gbk')
            except:
                data = data_bytes.decode('utf-8', errors='replace')
        
        data = self._strip_ansi(data)
        self.error_received.emit(data)

    def stop(self):
        """安全终止子进程"""
        if self._stopped:
            return
        self._stopped = True

        state = self.process.state()
        if state == QProcess.ProcessState.NotRunning:
            logger.debug("TerminalProcess: 进程已结束，无需终止")
            return

        logger.info("TerminalProcess: 正在终止子进程...")
        # 先尝试温和终止
        self.process.terminate()
        if not self.process.waitForFinished(3000):
            # 3秒内未退出则强制杀死
            logger.warning("TerminalProcess: 子进程未响应终止信号，强制杀死")
            self.process.kill()
            self.process.waitForFinished(2000)
        logger.info("TerminalProcess: 子进程已终止")

    def __del__(self):
        """析构时确保子进程被终止"""
        self.stop()
