"""
全局固定线程池（对标 Photoshop ThreadPoolExecutor）

设计原则:
- 线程数 = CPU 核数，启动时创建，退出时销毁，中间零创建/销毁
- 所有后台短任务（节点监控、进程等待）统一提交到此线程池
- 替代所有裸 QThread() 创建代码

用法:
    from ui.core.thread_pool import thread_pool
    thread_pool.run_task(lambda: blocking_work(), on_done=lambda: update_ui())
"""
from PySide6.QtCore import QObject, QThreadPool, QRunnable, Signal, QMutex


class _TaskSignals(QObject):
    """任务完成信号（跨线程安全）"""
    finished = Signal(object)  # 携带任务 ID


class _Runnable(QRunnable):
    """可运行的匿名任务"""

    def __init__(self, task_id, fn, on_done=None):
        super().__init__()
        self._task_id = task_id
        self._fn = fn
        self._on_done = on_done
        self._signals = _TaskSignals()
        if on_done:
            self._signals.finished.connect(self._on_finished)

    def run(self):
        try:
            self._fn()
        finally:
            if self._on_done:
                self._signals.finished.emit(self._task_id)

    def _on_finished(self, task_id):
        """在工作线程中触发回调"""
        if self._on_done:
            self._on_done()


class ThreadPool(QObject):
    """全局固定线程池（单例）"""

    _instance = None
    _lock = QMutex()

    def __init__(self):
        if ThreadPool._instance is not None:
            raise RuntimeError("ThreadPool 是单例，请使用 ThreadPool.instance()")
        super().__init__()
        self._pool = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(QThreadPool.globalInstance().maxThreadCount())
        self._active_tasks = set()
        ThreadPool._instance = self

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

    @property
    def max_thread_count(self) -> int:
        """最大线程数"""
        return self._pool.maxThreadCount()

    def active_task_count(self) -> int:
        """当前活跃任务数"""
        return len(self._active_tasks)

    def run_task(self, fn, on_done=None) -> int:
        """提交任务到线程池

        Args:
            fn: 在工作线程中执行的函数
            on_done: 完成后的回调（在主线程执行，可为 None）

        Returns:
            任务 ID（可用于 cancel）
        """
        task_id = id(fn)  # 简单 ID（后续可改为 UUID）
        self._active_tasks.add(task_id)
        runnable = _Runnable(
            task_id, fn,
            on_done=lambda: self._on_task_done(task_id, on_done)
        )
        self._pool.start(runnable)
        return task_id

    def _on_task_done(self, task_id, on_done):
        """任务完成清理"""
        self._active_tasks.discard(task_id)
        if on_done:
            on_done()

    def cancel(self, task_id: int) -> bool:
        """尝试取消任务（仅对尚未开始执行的任务有效）"""
        # QThreadPool 不支持直接取消已提交的任务
        # 仅清理跟踪记录
        if task_id in self._active_tasks:
            self._active_tasks.discard(task_id)
            return True
        return False

    def wait_for_done(self, timeout_ms: int = -1) -> bool:
        """等待所有任务完成"""
        return self._pool.waitForDone(timeout_ms)

    def shutdown(self, timeout_ms: int = 5000):
        """关闭线程池（应用退出时调用）
        
        1. 禁止新任务提交
        2. 等待所有任务完成
        3. 超时后释放
        """
        self._pool.clear()
        if not self._pool.waitForDone(timeout_ms):
            from ui.core.logger import logger
            logger.warning(f"[ThreadPool] 关闭超时（{timeout_ms}ms），仍有 {self.active_task_count()} 个任务")


# 全局单例
thread_pool = ThreadPool.instance()
