"""
核心业务子进程入口 — 无 UI，纯后台处理节点生命周期

主进程通过 QLocalSocket 发送命令（启动/停止节点、刷新项目等），
本进程执行并回传结果。
"""
import sys
import os

_proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

from PySide6.QtCore import QCoreApplication, QTimer
from ui.core.ipc import IPCClient
from ui.core.logger import logger
from ui.core.i18n import init_i18n


class CoreProcessApp:
    """核心业务后台进程，无 GUI"""

    def __init__(self):
        self.app = QCoreApplication(sys.argv)  # 无需 QApplication
        self.app.setApplicationName("BNOS Core Process")

        init_i18n()
        self.ipc = IPCClient()

        self._nodes_data = {}          # 节点数据副本
        self._current_project = None
        self._init_done = False

        self.ipc.connected.connect(self._on_connected)
        self.ipc.disconnected.connect(self._on_disconnected)
        self.ipc.message_received.connect(self._on_message)

        if not self.ipc.connect_to_server(timeout=10000):
            logger.error("核心进程无法连接到主进程，3秒后退出")
            QTimer.singleShot(3000, self.app.quit)
            return

        self._init_done = True
        print("[核心进程] 就绪，监听主进程命令...", flush=True)
        logger.info("核心业务进程就绪（后台无UI）")

    def _on_connected(self):
        print("[核心进程] 已连接到主进程", flush=True)
        logger.info("核心进程已连接到主进程")

    def _on_disconnected(self):
        logger.warning("核心进程与主进程断开，退出")
        self.app.quit()

    def _on_message(self, msg):
        action = msg.get("action")
        params = msg.get("params", {})
        # TODO: 根据 action 调用对应的 Manager
        logger.debug("核心进程收到: %s", action)

    def run(self):
        self.app.exec()


def main():
    app = CoreProcessApp()
    app.run()


if __name__ == "__main__":
    main()
