"""
AppState - 集中式状态管理器

基于观察者模式 + 事件总线，实现应用全局状态的统一管理。

设计原则：
- 单一数据源：所有状态集中存储
- 不可变性：状态变更通过 action 触发，不允许直接修改
- 响应式：状态变化自动通知订阅者
- 可追踪：支持状态变更历史

状态分类：
- project: 项目相关状态（当前项目路径、节点列表、布局等）
- ui: UI 相关状态（面板可见性、主题、缩放等）
- node: 节点相关状态（运行状态、日志、输出等）
- system: 系统相关状态（CPU、内存、进程等）

用法:
    from ui.core.app_state import app_state
    
    # 订阅状态变更
    app_state.subscribe('project.current', callback)
    
    # 获取状态
    project_path = app_state.get('project.current')
    
    # 设置状态
    app_state.set('project.current', '/path/to/project')
    
    # 获取整个状态树
    state = app_state.state
"""
from __future__ import annotations

import threading
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ui.core.logger import logger


class StateChangeType(Enum):
    """状态变更类型"""
    SET = 'set'
    UPDATE = 'update'
    DELETE = 'delete'
    RESET = 'reset'


@dataclass
class StateChange:
    """状态变更记录"""
    path: str
    old_value: Any
    new_value: Any
    change_type: StateChangeType
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    action: str = ""


class AppState:
    """集中式状态管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        """初始化状态管理器"""
        if self._initialized:
            return

        self._state: Dict[str, Any] = {
            'project': {
                'current': None,
                'nodes': {},
                'layout': {},
                'history': {},
            },
            'ui': {
                'theme': 'dark',
                'zoom': 1.0,
                'pan': {'x': 0, 'y': 0},
                'panels': {
                    'node_list': True,
                    'resource_monitor': False,
                    'node_monitor': False,
                    'terminal': False,
                    'properties': False,
                },
                'active_canvas': None,
                'selected_nodes': [],
                'selected_edges': [],
            },
            'node': {
                'running': {},
                'logs': {},
                'output': {},
                'errors': {},
            },
            'system': {
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'process_count': 0,
                'polling_frequency': 2,
            },
        }

        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self._history: List[StateChange] = []
        self._max_history_length = 1000

        self._initialized = True
        logger.info("AppState initialized")

    def get(self, path: str, default: Any = None) -> Any:
        """获取状态值
        
        Args:
            path: 状态路径，支持点分隔符，如 'project.current', 'ui.theme'
            default: 默认值
        
        Returns:
            状态值或默认值
        """
        keys = path.split('.')
        value = self._state
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, path: str, value: Any, action: str = ""):
        """设置状态值
        
        Args:
            path: 状态路径
            value: 新值
            action: 关联的动作描述（用于追踪）
        """
        keys = path.split('.')
        old_value = self.get(path)
        
        with self._lock:
            parent = self._state
            for key in keys[:-1]:
                if key not in parent:
                    parent[key] = {}
                parent = parent[key]
            
            parent[keys[-1]] = value
        
        self._record_change(path, old_value, value, StateChangeType.SET, action)
        self._notify(path, value, old_value)
        logger.debug("State set: %s = %s", path, value)

    def update(self, path: str, value: Any, action: str = ""):
        """更新状态值（合并字典）
        
        Args:
            path: 状态路径
            value: 要合并的值
            action: 关联的动作描述
        """
        current_value = self.get(path)
        if isinstance(current_value, dict) and isinstance(value, dict):
            merged = {**current_value, **value}
            self.set(path, merged, action)
        else:
            self.set(path, value, action)

    def delete(self, path: str, action: str = ""):
        """删除状态值
        
        Args:
            path: 状态路径
            action: 关联的动作描述
        """
        keys = path.split('.')
        old_value = self.get(path)
        
        with self._lock:
            parent = self._state
            for key in keys[:-1]:
                if key not in parent:
                    return
                parent = parent[key]
            
            if keys[-1] in parent:
                del parent[keys[-1]]
        
        self._record_change(path, old_value, None, StateChangeType.DELETE, action)
        self._notify(path, None, old_value)
        logger.debug("State deleted: %s", path)

    def reset(self):
        """重置所有状态"""
        old_state = dict(self._state)
        self.initialize()
        self._record_change('*', old_state, self._state, StateChangeType.RESET, 'reset')
        self._notify('*', self._state, old_state)
        logger.info("AppState reset")

    def subscribe(self, path: str, handler: Callable):
        """订阅状态变更
        
        Args:
            path: 状态路径，支持通配符 '*'，如 'project.*', 'ui.*'
            handler: 回调函数，签名: handler(new_value, old_value, path)
        """
        with self._lock:
            self._subscribers.setdefault(path, [])
            if handler not in self._subscribers[path]:
                self._subscribers[path].append(handler)

    def unsubscribe(self, path: str, handler: Callable):
        """取消订阅
        
        Args:
            path: 状态路径
            handler: 回调函数
        """
        with self._lock:
            handlers = self._subscribers.get(path, [])
            try:
                handlers.remove(handler)
            except ValueError:
                pass

    def _notify(self, path: str, new_value: Any, old_value: Any):
        """通知订阅者"""
        matched_paths = []
        
        for subscribed_path in self._subscribers.keys():
            if subscribed_path == path:
                matched_paths.append(subscribed_path)
            elif subscribed_path.endswith('.*'):
                prefix = subscribed_path[:-2]
                if path.startswith(prefix):
                    matched_paths.append(subscribed_path)
            elif subscribed_path == '*':
                matched_paths.append(subscribed_path)
        
        for matched_path in matched_paths:
            handlers = list(self._subscribers.get(matched_path, []))
            for handler in handlers:
                try:
                    handler(new_value, old_value, path)
                except Exception as e:
                    logger.warning("State subscriber error for '%s': %s", matched_path, e)

    def _record_change(self, path: str, old_value: Any, new_value: Any,
                       change_type: StateChangeType, action: str):
        """记录状态变更历史"""
        change = StateChange(
            path=path,
            old_value=old_value,
            new_value=new_value,
            change_type=change_type,
            action=action
        )
        
        self._history.append(change)
        
        if len(self._history) > self._max_history_length:
            self._history = self._history[-self._max_history_length:]

    @property
    def state(self) -> Dict[str, Any]:
        """获取完整状态树（只读副本）"""
        return dict(self._state)

    @property
    def history(self) -> List[StateChange]:
        """获取状态变更历史"""
        return list(self._history)

    def get_history_since(self, timestamp: float) -> List[StateChange]:
        """获取指定时间戳之后的变更历史"""
        return [c for c in self._history if c.timestamp >= timestamp]

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典（用于持久化）"""
        return {
            'state': self._state,
            'history_count': len(self._history),
            'timestamp': datetime.now().timestamp(),
        }

    def from_dict(self, data: Dict[str, Any]):
        """从字典加载状态"""
        if 'state' in data:
            with self._lock:
                self._state = data['state']
            logger.info("AppState loaded from dict")


# 全局实例
app_state = AppState()

# 便捷模块级函数
def get_state(path: str, default: Any = None): return app_state.get(path, default)
def set_state(path: str, value: Any, action: str = ""): app_state.set(path, value, action)
def update_state(path: str, value: Any, action: str = ""): app_state.update(path, value, action)
def delete_state(path: str, action: str = ""): app_state.delete(path, action)
def subscribe_state(path: str, handler: Callable): app_state.subscribe(path, handler)
def unsubscribe_state(path: str, handler: Callable): app_state.unsubscribe(path, handler)