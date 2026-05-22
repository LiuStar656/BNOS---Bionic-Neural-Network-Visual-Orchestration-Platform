"""
画布子进程入口 — 独立 QApplication + NodeCanvas + IPC 通信

主进程通过 QLocalSocket 发送命令，本进程回传事件。
作为子进程运行时，需确保项目根目录在 sys.path 中。
"""
import sys
import os

# 确保项目根目录在 sys.path（子进程启动时 cwd 不一定包含）
_proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

import json
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.core.ipc import IPCClient, A_ADD_NODE, A_REMOVE_NODE, A_UPDATE_STATUS
from ui.core.ipc import A_CREATE_EDGE, A_REMOVE_EDGE, A_SYNC_DATA, A_CLEAR_ALL
from ui.core.ipc import E_NODE_SELECTED, E_NODE_DBLCLICKED, E_EDGE_CREATED, E_EDGE_REMOVED
from ui.core.logger import logger
from ui.core.i18n import init_i18n


class CanvasProcessApp:
    """画布子进程应用，内嵌 NodeCanvas"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("BNOS Canvas Process")

        init_i18n()

        self.ipc = IPCClient()

        # 延迟初始化画布（连接后再创建）
        self.canvas = None
        self._init_done = False

        self.ipc.connected.connect(self._on_connected)
        self.ipc.disconnected.connect(self._on_disconnected)
        self.ipc.message_received.connect(self._on_message)

        if not self.ipc.connect_to_server(timeout=10000):
            logger.error("无法连接到主进程，3秒后退出")
            QTimer.singleShot(3000, self.app.quit)
            return

        self._setup_canvas()

    def _setup_canvas(self):
        from ui.canvas.canvas_view import NodeCanvas
        self.canvas = NodeCanvas(None)
        self.canvas.setWindowTitle("BNOS Canvas")
        self.canvas.resize(1200, 800)
        self.canvas.show()

        self._init_done = True
        logger.info("画布子进程就绪")

    def _on_connected(self):
        logger.info("画布进程已连接到主进程")

    def _on_disconnected(self):
        logger.warning("与主进程断开连接，退出")
        self.app.quit()

    def _on_message(self, msg):
        action = msg.get("action")
        params = msg.get("params", {})

        if not self._init_done or not self.canvas:
            return

        if action == A_ADD_NODE:
            node_name = params.get("node_name")
            if node_name and hasattr(self, '_main_data'):
                info = self._main_data.get(node_name)
                if info:
                    self.canvas.add_node_to_canvas(node_name, info)
        elif action == A_REMOVE_NODE:
            node_name = params.get("node_name")
            if node_name:
                self.canvas.remove_node_from_canvas(node_name)
        elif action == A_UPDATE_STATUS:
            node_name = params.get("node_name")
            status = params.get("status")
            if node_name and status:
                self.canvas.update_node_status(node_name, status)
        elif action == A_SYNC_DATA:
            self._main_data = params.get("nodes_data", {})
            self.canvas.nodes = {}
            for name, info in self._main_data.items():
                self.canvas.nodes[name] = info
            self.canvas.sync_all_nodes_display()
        elif action == A_CLEAR_ALL:
            self.canvas.clear_canvas()

    def run(self):
        self.app.exec()


def main():
    app = CanvasProcessApp()
    app.run()


if __name__ == "__main__":
    main()
