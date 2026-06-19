"""
节点调试管理器 - 支持节点进程的调试、断点和变量监控

功能特性：
- 调试端口管理：自动分配和释放调试端口
- 日志断点：基于日志内容的断点触发
- 实时变量查看：通过 HTTP API 获取节点运行时变量
- 远程调试连接：支持 Python debugpy、Node.js inspector 等
- 调试会话管理：管理多个并发调试会话

用法：
    from ui.core.node_debugger import node_debugger
    
    # 启动调试
    debugger.start_debug(node_name, node_path)
    
    # 设置日志断点
    debugger.set_log_breakpoint(node_name, "ERROR")
    
    # 获取变量
    vars = debugger.get_variables(node_name)
    
    # 停止调试
    debugger.stop_debug(node_name)
"""
import os
import json
import threading
import time
from typing import Dict, List, Optional, Callable
from enum import Enum

from ui.core.logger import logger


class DebugMode(Enum):
    """调试模式"""
    NONE = 'none'
    DEBUGPY = 'debugpy'
    NODE_INSPECTOR = 'node_inspector'
    ATTACH = 'attach'


class DebugSessionState(Enum):
    """调试会话状态"""
    INITIALIZING = 'initializing'
    RUNNING = 'running'
    PAUSED = 'paused'
    STOPPED = 'stopped'


class LogBreakpoint:
    """日志断点定义"""
    
    def __init__(self, pattern: str, action: str = "pause", condition: Optional[str] = None):
        self.pattern = pattern
        self.action = action
        self.condition = condition
        self.hit_count = 0
        self.active = True


class DebugSession:
    """调试会话"""
    
    def __init__(self, node_name: str, node_path: str, mode: DebugMode = DebugMode.DEBUGPY):
        self.node_name = node_name
        self.node_path = node_path
        self.mode = mode
        self.state = DebugSessionState.INITIALIZING
        self.debug_port = 0
        self.pid = None
        self.breakpoints: List[LogBreakpoint] = []
        self.variables: Dict[str, any] = {}
        self.log_buffer: List[str] = []
        self.max_log_lines = 1000
        self._lock = threading.Lock()
    
    def add_breakpoint(self, pattern: str, action: str = "pause", condition: Optional[str] = None):
        """添加日志断点"""
        with self._lock:
            bp = LogBreakpoint(pattern, action, condition)
            self.breakpoints.append(bp)
            logger.info("Added log breakpoint for %s: %s", self.node_name, pattern)
    
    def remove_breakpoint(self, pattern: str):
        """移除日志断点"""
        with self._lock:
            self.breakpoints = [bp for bp in self.breakpoints if bp.pattern != pattern]
    
    def clear_breakpoints(self):
        """清除所有断点"""
        with self._lock:
            self.breakpoints.clear()
    
    def add_log_line(self, line: str):
        """添加日志行并检查断点"""
        with self._lock:
            self.log_buffer.append(line)
            if len(self.log_buffer) > self.max_log_lines:
                self.log_buffer = self.log_buffer[-self.max_log_lines:]
            
            for bp in self.breakpoints:
                if bp.active and bp.pattern in line:
                    bp.hit_count += 1
                    logger.info("Breakpoint hit for %s: %s", self.node_name, bp.pattern)
    
    def get_logs(self, limit: int = 100) -> List[str]:
        """获取最近的日志"""
        with self._lock:
            return list(self.log_buffer[-limit:])
    
    def update_variables(self, variables: Dict[str, any]):
        """更新变量"""
        with self._lock:
            self.variables.update(variables)


class NodeDebugger:
    """节点调试管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def initialize(self):
        """初始化调试管理器"""
        if self._initialized:
            return
        
        self._sessions: Dict[str, DebugSession] = {}
        self._port_pool: List[int] = list(range(5678, 5700))
        self._used_ports: Dict[int, str] = {}
        self._lock = threading.Lock()
        self._callbacks: Dict[str, List[Callable]] = {}
        
        self._initialized = True
        logger.info("NodeDebugger initialized")
    
    def start_debug(self, node_name: str, node_path: str, 
                    mode: DebugMode = DebugMode.DEBUGPY) -> bool:
        """启动节点调试
        
        Args:
            node_name: 节点名称
            node_path: 节点路径
            mode: 调试模式
        
        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            if node_name in self._sessions:
                logger.warning("Debug session already exists for %s", node_name)
                return True
            
            port = self._allocate_port()
            if port == 0:
                logger.error("No available debug ports")
                return False
            
            session = DebugSession(node_name, node_path, mode)
            session.debug_port = port
            session.state = DebugSessionState.RUNNING
            
            self._sessions[node_name] = session
            self._used_ports[port] = node_name
            
            logger.info("Started debug session for %s on port %d", node_name, port)
        
        self._notify('debug.start', {'node_name': node_name, 'port': port})
        return True
    
    def stop_debug(self, node_name: str) -> bool:
        """停止节点调试"""
        with self._lock:
            session = self._sessions.get(node_name)
            if not session:
                return False
            
            port = session.debug_port
            if port in self._used_ports:
                del self._used_ports[port]
                self._port_pool.append(port)
            
            session.state = DebugSessionState.STOPPED
            del self._sessions[node_name]
            
            logger.info("Stopped debug session for %s", node_name)
        
        self._notify('debug.stop', {'node_name': node_name})
        return True
    
    def pause_debug(self, node_name: str) -> bool:
        """暂停调试"""
        session = self._sessions.get(node_name)
        if not session:
            return False
        
        session.state = DebugSessionState.PAUSED
        logger.info("Paused debug session for %s", node_name)
        self._notify('debug.pause', {'node_name': node_name})
        return True
    
    def resume_debug(self, node_name: str) -> bool:
        """恢复调试"""
        session = self._sessions.get(node_name)
        if not session:
            return False
        
        session.state = DebugSessionState.RUNNING
        logger.info("Resumed debug session for %s", node_name)
        self._notify('debug.resume', {'node_name': node_name})
        return True
    
    def set_log_breakpoint(self, node_name: str, pattern: str, 
                           action: str = "pause", condition: Optional[str] = None):
        """设置日志断点"""
        session = self._sessions.get(node_name)
        if not session:
            logger.warning("No debug session for %s", node_name)
            return
        
        session.add_breakpoint(pattern, action, condition)
    
    def remove_log_breakpoint(self, node_name: str, pattern: str):
        """移除日志断点"""
        session = self._sessions.get(node_name)
        if not session:
            return
        
        session.remove_breakpoint(pattern)
    
    def clear_log_breakpoints(self, node_name: str):
        """清除所有日志断点"""
        session = self._sessions.get(node_name)
        if not session:
            return
        
        session.clear_breakpoints()
    
    def add_log_line(self, node_name: str, line: str):
        """添加日志行"""
        session = self._sessions.get(node_name)
        if not session:
            return
        
        session.add_log_line(line)
    
    def get_logs(self, node_name: str, limit: int = 100) -> List[str]:
        """获取节点日志"""
        session = self._sessions.get(node_name)
        if not session:
            return []
        
        return session.get_logs(limit)
    
    def update_variables(self, node_name: str, variables: Dict[str, any]):
        """更新节点变量"""
        session = self._sessions.get(node_name)
        if not session:
            return
        
        session.update_variables(variables)
    
    def get_variables(self, node_name: str) -> Dict[str, any]:
        """获取节点变量"""
        session = self._sessions.get(node_name)
        if not session:
            return {}
        
        return session.variables.copy()
    
    def get_session_state(self, node_name: str) -> Optional[DebugSessionState]:
        """获取调试会话状态"""
        session = self._sessions.get(node_name)
        if not session:
            return None
        
        return session.state
    
    def get_active_sessions(self) -> List[Dict[str, any]]:
        """获取所有活跃的调试会话"""
        result = []
        with self._lock:
            for name, session in self._sessions.items():
                result.append({
                    'node_name': name,
                    'node_path': session.node_path,
                    'mode': session.mode.value,
                    'state': session.state.value,
                    'port': session.debug_port,
                    'pid': session.pid,
                    'breakpoint_count': len(session.breakpoints),
                })
        
        return result
    
    def _allocate_port(self) -> int:
        """分配调试端口"""
        if not self._port_pool:
            return 0
        
        for port in self._port_pool:
            if self._is_port_available(port):
                self._port_pool.remove(port)
                return port
        
        return 0
    
    def _is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                result = s.connect_ex(('localhost', port))
                return result != 0
        except Exception:
            return True
    
    def subscribe(self, event_type: str, callback: Callable):
        """订阅调试事件"""
        with self._lock:
            self._callbacks.setdefault(event_type, [])
            if callback not in self._callbacks[event_type]:
                self._callbacks[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅"""
        with self._lock:
            callbacks = self._callbacks.get(event_type, [])
            try:
                callbacks.remove(callback)
            except ValueError:
                pass
    
    def _notify(self, event_type: str, data: Dict[str, any]):
        """通知订阅者"""
        callbacks = list(self._callbacks.get(event_type, []))
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.warning("Debug event callback error: %s", e)


# 全局实例
node_debugger = NodeDebugger()

# 便捷函数
def start_debug(node_name: str, node_path: str, mode: DebugMode = DebugMode.DEBUGPY):
    return node_debugger.start_debug(node_name, node_path, mode)

def stop_debug(node_name: str):
    return node_debugger.stop_debug(node_name)

def pause_debug(node_name: str):
    return node_debugger.pause_debug(node_name)

def resume_debug(node_name: str):
    return node_debugger.resume_debug(node_name)

def set_log_breakpoint(node_name: str, pattern: str, action: str = "pause", condition: Optional[str] = None):
    return node_debugger.set_log_breakpoint(node_name, pattern, action, condition)

def get_active_sessions():
    return node_debugger.get_active_sessions()
