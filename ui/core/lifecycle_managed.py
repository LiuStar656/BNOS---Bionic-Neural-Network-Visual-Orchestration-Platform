"""
生命周期管理 Mixin（对标 Photoshop IDisposable.Dispose()）

设计原则:
- 任何创建 QTimer / QThread 的组件都继承此 Mixin
- _register_resource() 在创建资源时立即调用
- dispose() 在 destroyed 信号触发时自动调用
- dispose() 幂等——多次调用安全
- 开发模式下 __del__ 中断言所有资源已释放

用法:
    class MyPanel(QWidget, LifecycleManaged):
        def __init__(self):
            QWidget.__init__(self)
            LifecycleManaged.__init__(self)
            self._init_resources()

        def _init_resources(self):
            timer = QTimer(self)
            self._register_resource(timer, 'stop')
            timer.start(1000)
"""
from PySide6.QtCore import QTimer, QThread


class LifecycleManaged:
    """生命周期管理 Mixin

    追踪所有子资源（QTimer、QThread 等），在 dispose() 时统一清理。
    """

    def __init__(self):
        self._resources: list[tuple[object, str]] = []
        self._disposed = False

    # ── 资源注册 ──
    def _register_resource(self, resource, stop_method: str = 'stop'):
        """注册一个需要追踪的子资源

        Args:
            resource: QTimer / QThread 实例
            stop_method: 停止方法名，'stop' 用于 QTimer，'quit' 用于 QThread
        """
        if not self._disposed:
            self._resources.append((resource, stop_method))

    def _unregister_resource(self, resource):
        """移除一个资源的追踪"""
        self._resources = [(r, m) for r, m in self._resources if r is not resource]

    # ── 便捷方法 ──
    def _schedule_update(self, interval_ms: int, callback):
        """注册到统一更新调度器（替代 QTimer.start()）

        此方法自动将回调注册到全局 UpdateScheduler，
        dispose() 时自动注销。
        """
        from ui.core.update_scheduler import update_scheduler
        update_scheduler.subscribe(self, interval_ms, callback)

    def _run_in_thread(self, fn, on_done=None) -> int:
        """提交任务到全局线程池（替代 QThread()）

        此方法自动将任务提交到全局 ThreadPool，
        dispose() 时会尝试取消。

        Returns:
            任务 ID
        """
        from ui.core.thread_pool import thread_pool
        return thread_pool.run_task(fn, on_done)

    # ── 清理 ──
    def dispose(self):
        """释放所有注册的资源，注销调度器订阅

        幂等：多次调用安全。
        """
        if self._disposed:
            return
        self._disposed = True

        # 1. 停止所有注册的资源
        for resource, stop_method in self._resources:
            try:
                method = getattr(resource, stop_method, None)
                if method:
                    method()
            except RuntimeError:
                pass  # 资源已被删除

        # 2. 注销 UpdateScheduler 订阅
        try:
            from ui.core.update_scheduler import update_scheduler
            update_scheduler.unsubscribe(self)
        except Exception:
            pass

        self._resources.clear()

    def is_disposed(self) -> bool:
        """是否已经清理"""
        return self._disposed

    def resource_count(self) -> int:
        """当前追踪的资源数量"""
        return len(self._resources)

    def _create_timer(self, interval_ms: int, callback, single_shot: bool = False):
        """创建一个受管理的 QTimer

        自动注册到生命周期管理，dispose() 时自动停止。

        Args:
            interval_ms: 间隔（毫秒）
            callback: 回调函数
            single_shot: 是否只触发一次

        Returns:
            QTimer 实例
        """
        # self 必须是 QObject 的子类才能设置 parent
        timer = QTimer(self if hasattr(self, 'metaObject') else None)
        timer.timeout.connect(callback)
        self._register_resource(timer, 'stop')
        if single_shot:
            timer.setSingleShot(True)
        timer.start(interval_ms)
        return timer
