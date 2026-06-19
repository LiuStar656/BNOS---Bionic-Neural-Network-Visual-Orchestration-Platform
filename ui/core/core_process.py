"""
核心业务子进程入口 — 无 UI，纯后台处理节点生命周期

主进程通过 QLocalSocket 发送命令（启动/停止节点、刷新项目等），
本进程执行并回传结果。

支持的命令:
  - node.start       : 启动节点
  - node.stop        : 停止节点
  - node.status      : 获取节点状态
  - node.list        : 获取节点列表
  - project.refresh  : 刷新项目
  - project.load     : 加载项目
"""
import sys
import os
import json

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
        self.app = QCoreApplication(sys.argv)
        self.app.setApplicationName("BNOS Core Process")

        init_i18n()
        self.ipc = IPCClient()

        self._nodes_data = {}
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
        request_id = msg.get("request_id", "")

        logger.debug("核心进程收到命令: %s, params: %s", action, params)

        handlers = {
            "node.start": self._handle_start_node,
            "node.stop": self._handle_stop_node,
            "node.status": self._handle_node_status,
            "node.list": self._handle_node_list,
            "project.refresh": self._handle_project_refresh,
            "project.load": self._handle_project_load,
            "node.stop_all": self._handle_stop_all_nodes,
            "node.detect_running": self._handle_detect_running_nodes,
        }

        handler = handlers.get(action)
        if handler:
            try:
                result = handler(params)
                self._send_response(request_id, action, result, success=True)
            except Exception as e:
                logger.error("执行命令 %s 失败: %s", action, e)
                self._send_response(request_id, action, {"error": str(e)}, success=False)
        else:
            logger.warning("未知命令: %s", action)
            self._send_response(request_id, action, {"error": f"未知命令: {action}"}, success=False)

    def _send_response(self, request_id, action, data, success=True):
        response = {
            "request_id": request_id,
            "action": action,
            "success": success,
            "data": data
        }
        self.ipc.send("core.response", response)

    def _handle_start_node(self, params):
        from ui.core.node_process import start_node_process
        node_name = params.get("node_name")
        node_path = params.get("node_path")

        if not node_name or not node_path:
            return {"error": "缺少 node_name 或 node_path 参数"}

        node_info = {"path": node_path, "name": node_name}
        success, error = start_node_process(node_info)

        if success:
            self._nodes_data[node_name] = node_info
            return {"message": f"节点 {node_name} 启动成功", "pid": node_info.get('process').pid if node_info.get('process') else None}
        else:
            return {"error": error}

    def _handle_stop_node(self, params):
        from ui.core.node_process import stop_node_process
        node_name = params.get("node_name")

        if not node_name:
            return {"error": "缺少 node_name 参数"}

        node_info = self._nodes_data.get(node_name)
        if not node_info:
            return {"error": f"节点 {node_name} 不存在"}

        success, error = stop_node_process(node_info)
        if success:
            return {"message": f"节点 {node_name} 已停止"}
        else:
            return {"error": error}

    def _handle_node_status(self, params):
        node_name = params.get("node_name")

        if not node_name:
            return {"error": "缺少 node_name 参数"}

        node_info = self._nodes_data.get(node_name)
        if not node_info:
            return {"status": "unknown"}

        return {
            "status": node_info.get("status", "stopped"),
            "pid": node_info.get("process").pid if node_info.get("process") else None,
            "path": node_info.get("path", "")
        }

    def _handle_node_list(self, params):
        result = []
        for name, info in self._nodes_data.items():
            result.append({
                "name": name,
                "status": info.get("status", "stopped"),
                "path": info.get("path", ""),
                "pid": info.get("process").pid if info.get("process") else None
            })
        return {"nodes": result}

    def _handle_project_refresh(self, params):
        project_path = params.get("project_path")
        if not project_path:
            return {"error": "缺少 project_path 参数"}

        self._current_project = project_path
        nodes_data = self._scan_project_nodes(project_path)
        self._nodes_data = nodes_data

        return {
            "project_path": project_path,
            "node_count": len(nodes_data),
            "nodes": list(nodes_data.keys())
        }

    def _handle_project_load(self, params):
        project_path = params.get("project_path")
        if not project_path:
            return {"error": "缺少 project_path 参数"}

        self._current_project = project_path
        nodes_data = self._scan_project_nodes(project_path)
        self._nodes_data = nodes_data

        from ui.core.node_process import detect_running_nodes
        running_nodes = detect_running_nodes(self._nodes_data)

        return {
            "project_path": project_path,
            "node_count": len(nodes_data),
            "running_count": len(running_nodes),
            "running_nodes": [name for name, pid in running_nodes]
        }

    def _handle_stop_all_nodes(self, params):
        from ui.core.node_process import stop_node_process
        stopped_count = 0
        errors = []

        for node_name in list(self._nodes_data.keys()):
            node_info = self._nodes_data[node_name]
            if node_info.get("status") == "running":
                success, error = stop_node_process(node_info)
                if success:
                    stopped_count += 1
                else:
                    errors.append({"node": node_name, "error": error})

        return {"stopped_count": stopped_count, "errors": errors}

    def _handle_detect_running_nodes(self, params):
        from ui.core.node_process import detect_running_nodes
        running_nodes = detect_running_nodes(self._nodes_data)
        return {"running_nodes": [{"name": name, "pid": pid} for name, pid in running_nodes]}

    def _scan_project_nodes(self, project_path):
        nodes_dir = os.path.join(project_path, "nodes")
        nodes_data = {}

        if not os.path.isdir(nodes_dir):
            return nodes_data

        for node_name in os.listdir(nodes_dir):
            node_path = os.path.join(nodes_dir, node_name)
            if not os.path.isdir(node_path):
                continue

            config_path = os.path.join(node_path, "config.json")
            config = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                except Exception as e:
                    logger.warning("读取节点配置失败 %s: %s", node_name, e)

            nodes_data[node_name] = {
                "name": node_name,
                "path": node_path,
                "config": config,
                "status": "stopped",
                "process": None
            }

        return nodes_data

    def run(self):
        self.app.exec()


def main():
    app = CoreProcessApp()
    app.run()


if __name__ == "__main__":
    main()
