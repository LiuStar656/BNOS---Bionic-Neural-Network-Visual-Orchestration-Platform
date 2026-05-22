"""
跨进程通信 (IPC) — QLocalServer + QLocalSocket + JSON 事件

主进程启动 Server，子进程通过 Socket 连接。
双向通信：主→子 发送命令，子→主 回传事件。
"""
import json
import uuid
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from ui.core.logger import logger

SERVER_NAME = "BNOS_IPC_Server"

# ── Action 常量 ──
A_ADD_NODE      = "canvas.add_node"
A_REMOVE_NODE   = "canvas.remove_node"
A_CREATE_EDGE   = "canvas.create_edge"
A_REMOVE_EDGE   = "canvas.remove_edge"
A_UPDATE_STATUS = "canvas.update_status"
A_SYNC_DATA     = "canvas.sync_data"
A_CLEAR_ALL     = "canvas.clear_all"

E_NODE_SELECTED    = "canvas.node_selected"
E_NODE_DBLCLICKED  = "canvas.node_dblclicked"
E_EDGE_CREATED     = "canvas.edge_created"
E_EDGE_REMOVED     = "canvas.edge_removed"


def make_message(action, params=None, request_id=None):
    return json.dumps({
        "action": action,
        "params": params or {},
        "request_id": request_id or str(uuid.uuid4())[:8]
    })


def parse_message(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


class IPCServer(QObject):
    """主进程 IPC 服务端，接受子进程连接"""
    message_received = pyqtSignal(str, object)   # (client_id, msg_dict)
    client_connected = pyqtSignal(str)            # client_id
    client_disconnected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._clients = {}   # client_id → QLocalSocket
        QLocalServer.removeServer(SERVER_NAME)

    def start(self):
        if not self._server.listen(SERVER_NAME):
            logger.error("IPC Server 启动失败: %s", self._server.errorString())
            return False
        self._server.newConnection.connect(self._on_new_connection)
        logger.info("IPC Server 已启动: %s", SERVER_NAME)
        return True

    def stop(self):
        for sock in list(self._clients.values()):
            sock.disconnectFromServer()
        self._server.close()
        logger.info("IPC Server 已停止")

    def send(self, client_id, action, params=None):
        sock = self._clients.get(client_id)
        if not sock or sock.state() != QLocalSocket.LocalSocketState.ConnectedState:
            return False
        msg = make_message(action, params)
        sock.write(msg.encode('utf-8'))
        sock.flush()
        return True

    def broadcast(self, action, params=None):
        for cid in list(self._clients.keys()):
            self.send(cid, action, params)

    def _on_new_connection(self):
        while self._server.hasPendingConnections():
            sock = self._server.nextPendingConnection()
            cid = str(uuid.uuid4())[:8]
            self._clients[cid] = sock
            self.client_connected.emit(cid)

            buffer = b""
            def on_ready():
                nonlocal buffer
                data = sock.readAll().data()
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    msg = parse_message(line.decode('utf-8'))
                    if msg:
                        self.message_received.emit(cid, msg)

            sock.readyRead.connect(on_ready)

            def on_disconnect():
                self._clients.pop(cid, None)
                self.client_disconnected.emit(cid)
            sock.disconnected.connect(on_disconnect)


class IPCClient(QObject):
    """子进程 IPC 客户端，连接主进程"""
    message_received = pyqtSignal(object)   # msg_dict
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._socket = QLocalSocket(self)
        self._buffer = b""

    def connect_to_server(self, timeout=3000):
        self._socket.connectToServer(SERVER_NAME)
        if not self._socket.waitForConnected(timeout):
            logger.error("IPC Client 连接失败: %s", self._socket.errorString())
            return False
        self._socket.readyRead.connect(self._on_ready)
        self._socket.disconnected.connect(self.disconnected.emit)
        self.connected.emit()
        logger.info("IPC Client 已连接")
        return True

    def send(self, action, params=None):
        if self._socket.state() != QLocalSocket.LocalSocketState.ConnectedState:
            return False
        msg = make_message(action, params)
        self._socket.write(msg.encode('utf-8'))
        self._socket.write(b'\n')
        self._socket.flush()
        return True

    def _on_ready(self):
        data = self._socket.readAll().data()
        self._buffer += data
        while b'\n' in self._buffer:
            line, self._buffer = self._buffer.split(b'\n', 1)
            msg = parse_message(line.decode('utf-8'))
            if msg:
                self.message_received.emit(msg)
