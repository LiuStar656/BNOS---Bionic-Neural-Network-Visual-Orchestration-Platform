"""
统一更新调度器（对标 Photoshop requestAnimationFrame 单帧循环）

设计原则:
- 只用一个 QTimer，所有面板共享
- 面板创建时 subscribe()，销毁时自动 unsubscribe()
- 同一间隔组的回调共享触发频率
- 替代所有面板独立的 QTimer，消除事件循环拥塞

用法:
    from ui.core.update_scheduler import update_scheduler
    update_scheduler.subscribe(panel, 1000, panel._update_ui)
    # panel 销毁时自动 unsubscribe
"""
import time
from collections import defaultdict
from PySide6.QtCore import QObject, QTimer, QMutex


class _Subscriber:
    """订阅者信息"""

    def __init__(self, owner, interval_ms, callback):
        self.owner = owner          # 所有者（通常是面板 widget）
        self.interval_ms = interval_ms
        self.callback = callback
        self.last_fire = 0          # 上次触发的时间戳


class UpdateScheduler(QObject):
    """统一更新调度器（单例）"""

    _instance = None
    _lock = QMutex()

    # 基础调度间隔（所有面板间隔的最大公约数）
    BASE_INTERVAL_MS = 1000

    def __init__(self):
        if UpdateScheduler._instance is not None:
            raise RuntimeError("UpdateScheduler 是单例，请使用 UpdateScheduler.instance()")
        super().__init__()
        self._subscribers: dict[int, list[_Subscriber]] = defaultdict(list)
        self._tick_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(self.BASE_INTERVAL_MS)
        self._busy = False  # 防止回调堆积
        UpdateScheduler._instance = self

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._lock.lock()
            try:
                if cls._instance is None:
                    cls._instance = cls()
            finally:
                cls._lock.unlock()
        return cls._instance

    def subscribe(self, owner, interval_ms: int, callback):
        """注册更新回调

        Args:
            owner: 所有者（QObject），用于自动 unsubscribe
            interval_ms: 触发间隔（毫秒），必须是 BASE_INTERVAL_MS 的倍数
            callback: 回调函数，无参数
        """
        if owner is None:
            return
        # 确保 interval 是 base 的倍数，最小为 base
        interval_ms = max(interval_ms, self.BASE_INTERVAL_MS)
        interval_ms = (interval_ms // self.BASE_INTERVAL_MS) * self.BASE_INTERVAL_MS

        # 防止重复订阅
        for sub in self._subscribers.get(interval_ms, []):
            if sub.owner is owner:
                sub.callback = callback  # 更新回调
                return

        sub = _Subscriber(owner, interval_ms, callback)
        self._subscribers[interval_ms].append(sub)

    def unsubscribe(self, owner):
        """注销所有更新回调

        Args:
            owner: 之前注册的所有者
        """
        if owner is None:
            return
        for interval_ms in list(self._subscribers.keys()):
            self._subscribers[interval_ms] = [
                s for s in self._subscribers[interval_ms]
                if s.owner is not owner
            ]
            if not self._subscribers[interval_ms]:
                del self._subscribers[interval_ms]

    def unsubscribe_all(self, interval_ms=None):
        """注销所有订阅者
        
        Args:
            interval_ms: 如果指定，只注销该间隔组的订阅者
        """
        if interval_ms is not None:
            self._subscribers.pop(interval_ms, None)
        else:
            self._subscribers.clear()

    def _tick(self):
        """定时器触发"""
        if self._busy:
            return  # 上一帧未完成，跳过避免堆积
        self._busy = True
        try:
            self._tick_count += 1
            now = time.monotonic()

            for interval_ms, subs in list(self._subscribers.items()):
                if self._tick_count % (interval_ms // self.BASE_INTERVAL_MS) != 0:
                    continue

                for sub in subs[:]:
                    try:
                        sub.last_fire = now
                        sub.callback()
                    except RuntimeError:
                        self.unsubscribe(sub.owner)
                    except Exception:
                        pass
        finally:
            self._busy = False

    def active_subscriber_count(self) -> int:
        """当前活跃订阅者总数"""
        return sum(len(subs) for subs in self._subscribers.values())

    def shutdown(self):
        """停止调度器（应用退出时调用）"""
        self._timer.stop()
        self._subscribers.clear()


# 全局单例
update_scheduler = UpdateScheduler.instance()
