"""
BNOS 主窗口IPC通信模块

负责进程间通信（IPC）相关功能，包括：
- IPC Server 初始化和管理
- 子进程启动和监控
- 应用重启功能
- 画布同步（嵌入/远程通用）
"""
import sys
import os
from PyQt6.QtCore import QTimer
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.ipc import A_WIN_SYNC, A_SYNC_DATA, A_UPDATE_STATUS


class MainWindowIPCMixin:
    """IPC通信Mixin - 处理进程间通信和子进程管理"""

    def _init_ipc(self):
        """初始化 IPC Server，接收子进程连接"""
        self._ipc_server = None
        from ui.core.ipc import IPCServer
        self._ipc_server = IPCServer(self)
        if not self._ipc_server.start():
            logger.warning("IPC Server 启动失败，进程隔离不可用")
            return
        self._ipc_server.client_connected.connect(self._on_ipc_client_connected)
        self._ipc_server.message_received.connect(self._on_ipc_message)
        self._ipc_server.client_disconnected.connect(self._on_ipc_client_disconnected)
        logger.info("进程间通信已就绪")

    def _start_canvas_process(self):
        """启动画布子进程（可选，默认使用内嵌画布）"""
        if not self._ipc_server:
            return
        self._process_manager.register("canvas", "ui/canvas/canvas_process.py")
        proc = self._process_manager.get("canvas")
        proc.crashed.connect(self._on_canvas_crashed)
        proc.start()

    def _start_panel_process(self):
        """启动面板子进程（可选，默认使用内嵌面板）"""
        if not self._ipc_server:
            return
        self._process_manager.register("panel", "ui/panels/panel_process.py")
        proc = self._process_manager.get("panel")
        proc.crashed.connect(lambda pid: logger.warning("面板进程 %s 崩溃，自动重启", pid))
        proc.start()

    def _on_canvas_crashed(self, pid):
        """画布崩溃 → 自动重启"""
        self.show_toast(t("_k_canvas_crashed"), "warning")
        logger.warning("画布子进程 %s 崩溃，准备重启", pid)

    def _start_core_process(self):
        """启动核心业务子进程（可选，默认在主进程跑）"""
        if not self._ipc_server:
            return
        self._process_manager.register("core", "ui/core/core_process.py")
        proc = self._process_manager.get("core")
        proc.crashed.connect(lambda pid: logger.warning("核心进程 %s 崩溃，自动重启", pid))
        proc.start()

    def _on_ipc_client_connected(self, client_id):
        logger.info("IPC 客户端已连接: %s", client_id)

    def _on_ipc_client_disconnected(self, client_id):
        logger.info("IPC 客户端已断开: %s", client_id)

    def _on_ipc_message(self, client_id, msg):
        """处理子进程发来的事件"""
        action = msg.get("action")
        params = msg.get("params", {})
        logger.debug("IPC 收到: %s ← %s", action, client_id)

    def _start_canvas_and_load(self, project_path):
        """启动画布子进程并加载布局"""
        self._start_canvas_process()
        QTimer.singleShot(600, lambda: self._sync_canvas_geometry())
        QTimer.singleShot(800, lambda: self._canvas_ipc_sync() if self._ipc_server else None)

    def _sync_canvas_geometry(self):
        """发送主窗口几何信息给画布子进程，实现视觉一体化"""
        if not self._ipc_server:
            return
        g = self.geometry()
        self._ipc_server.broadcast(A_WIN_SYNC, {
            "x": g.x(), "y": g.y() + 40,
            "w": g.width(), "h": g.height() - 40,
        })

    def _canvas_ipc_sync(self):
        """同步 nodes_data 到画布（嵌入式绕过IPC直接用canvas）"""
        if self.canvas and self.canvas.parent_window:
            self.canvas.sync_all_nodes_display()
        elif self._ipc_server:
            self._ipc_server.broadcast(A_SYNC_DATA, {"nodes_data": self.nodes_data})

    def _canvas_ipc_update_status(self, node_name, status):
        if self.canvas and self.canvas.parent_window:
            self.canvas.update_node_status(node_name, status)
        elif self._ipc_server:
            self._ipc_server.broadcast(A_UPDATE_STATUS, {"node_name": node_name, "status": status})

    def _restart_application(self):
        """重启应用程序"""
        logger.info("正在重启应用...")

        if hasattr(self, '_canvas_host') and self._canvas_host:
            self._canvas_host._is_closing = True
            if hasattr(self._canvas_host, '_terminal_dock') and self._canvas_host._terminal_dock:
                self._canvas_host._terminal_dock._is_closing = True
                logger.info("[LOCK] 设置 TerminalDock._is_closing = True (重启)")

        running_nodes = []
        for node_name, node_info in self.nodes_data.items():
            status = node_info.get('status', 'unknown')
            process = node_info.get('process', None)
            if status == 'running' and process:
                running_nodes.append(node_name)

        logger.info("检测到 %d 个运行中的节点: %s", len(running_nodes), running_nodes)

        if running_nodes:
            nodes_list = "\n".join([f"• {name}" for name in running_nodes[:10]])
            if len(running_nodes) > 10:
                nodes_list += f"\n... 还有 {len(running_nodes) - 10} 个节点"

            from ui.core.utils.dialog_utils import MSG_ACCEPT, MSG_REJECT, MSG_CANCEL
            from ui.core.utils.dialog_utils import themed_message
            reply = themed_message(
                self, t("k_title_detect_running"),
                t("_k_close_running_nodes").format(count=len(running_nodes), nodes=nodes_list),
                "question3"
            )

            if reply == MSG_ACCEPT:
                logger.info("正在关闭 %d 个运行中的节点...", len(running_nodes))
                self._force_stop_all_nodes(running_nodes)
                self.show_toast(t("_k_nodes_closed").format(count=len(running_nodes)), "success")
            elif reply == MSG_REJECT:
                logger.info("%d 个节点将继续在后台运行", len(running_nodes))
                self.show_toast(t("_k_nodes_background").format(count=len(running_nodes)), "info")
            else:
                logger.info("用户取消了重启操作")
                self.show_toast(t("_k_restart_canceled"), "info")
                return

        self._shutdown_save_all_data()
        self._disconnect_terminal_signals()
        self._stop_terminal_subprocesses()

        self._process_manager.stop_all()
        if self._ipc_server:
            self._ipc_server.stop()

        logger.info("[RESTART] 准备重启应用...")
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().exit(42)