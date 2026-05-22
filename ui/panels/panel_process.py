"""
面板子进程入口 — 独立 QApplication + 所有面板 + IPC 通信

主进程通过 QLocalSocket 同步数据、接收用户操作事件。
"""
import sys
import os

_proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.core.ipc import IPCClient
from ui.core.logger import logger
from ui.core.i18n import init_i18n


class PanelProcessApp:
    """面板子进程应用，内嵌所有面板"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("BNOS Panel Process")

        init_i18n()
        self.ipc = IPCClient()

        self.node_list_panel = None
        self.property_panel = None
        self._init_done = False

        self.ipc.connected.connect(self._on_connected)
        self.ipc.disconnected.connect(self._on_disconnected)
        self.ipc.message_received.connect(self._on_message)

        if not self.ipc.connect_to_server(timeout=10000):
            logger.error("面板进程无法连接到主进程，3秒后退出")
            QTimer.singleShot(3000, self.app.quit)
            return

        self._setup_panels()

    def _setup_panels(self):
        from ui.panels.node_list_panel import NodeListPanel
        from ui.panels.property_panel import PropertyPanel

        self.node_list_panel = NodeListPanel(None)
        self.node_list_panel.setWindowTitle("Node List")
        self.node_list_panel.show()

        self.property_panel = PropertyPanel(None)
        self.property_panel.setWindowTitle("Properties")
        self.property_panel.resize(300, 600)
        self.property_panel.show()

        self._init_done = True
        logger.info("面板子进程就绪")

    def _on_connected(self):
        logger.info("面板进程已连接到主进程")

    def _on_disconnected(self):
        logger.warning("面板进程与主进程断开，退出")
        self.app.quit()

    def _on_message(self, msg):
        # TODO: 根据 action 分发到各面板
        pass

    def run(self):
        self.app.exec()


def main():
    app = PanelProcessApp()
    app.run()


if __name__ == "__main__":
    main()
