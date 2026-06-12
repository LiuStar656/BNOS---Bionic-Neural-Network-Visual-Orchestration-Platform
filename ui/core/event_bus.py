"""
事件总线系统，用于解耦模块间的直接依赖关系
设计原则：基于 PyQt6 信号机制，线程安全，零侵入现有代码
"""
from typing import Dict, List, Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal
from ui.core.logger import logger
import threading


class EventBus(QObject):
    """事件总线 — 发布-订阅模式的核心实现"""

    # 单一通用信号：(事件类型, 数据载荷)
    event_signal = pyqtSignal(str, object)

    def __init__(self):
        super().__init__()
        self._handlers: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        self.event_signal.connect(self._dispatch)

    def subscribe(self, event_type: str, handler: Callable):
        """订阅事件类型"""
        with self._lock:
            self._handlers.setdefault(event_type, [])
            if handler not in self._handlers[event_type]:
                self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        """取消订阅"""
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            try:
                handlers.remove(handler)
            except ValueError:
                pass

    def publish(self, event_type: str, data: Any = None):
        """发布事件（线程安全）"""
        self.event_signal.emit(event_type, data)

    def _dispatch(self, event_type: str, data: Any):
        """内部分发到各订阅者"""
        with self._lock:
            handlers = list(self._handlers.get(event_type, []))
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.warning("[EventBus] Error handling '%s': %s", event_type, e)


# 全局事件总线单例
event_bus = EventBus()

# 便捷模块级函数（让调用方写起来更自然）
def subscribe(et: str, h: Callable): event_bus.subscribe(et, h)
def publish(et: str, d: Any = None): event_bus.publish(et, d)
def unsubscribe(et: str, h: Callable): event_bus.unsubscribe(et, h)
