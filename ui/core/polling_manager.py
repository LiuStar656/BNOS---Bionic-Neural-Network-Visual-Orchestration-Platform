"""
统一轮询管理器 - 单例模式
将所有需要定时轮询的任务统一管理，避免多个定时器并行运行

【架构】PollingManager 运行在**后台线程**：
  - 主定时器 + 所有文件 IO（os.path.exists/getmtime/open）在后台线程执行
  - 检测到变更后通过 Qt Signal 发回主线程（Qt 自动跨线程排队）
  - 外部接口（watch_* / register_task / start / stop）线程安全，由主线程调用

【动态频率】基于系统 CPU 负载自动调整轮询频率：
  - 低负载 (< 30%): 高频模式，tick = 1秒，快速响应
  - 中负载 (30%-60%): 标准模式，tick = 2秒，平衡响应与性能
  - 高负载 (> 60%): 低频模式，tick = 4秒，降低 CPU 占用

管理职责：
  1. 节点进程健康状态检测
  2. 全局日志文件监控
  3. 全局配置文件监控
  4. 进程管理器健康检查
  5. 提供统一的任务注册接口
"""
import os
import json
import threading
from datetime import datetime
from PySide6.QtCore import QObject, QTimer, Qt, Signal, QThread
from ui.core.logger import logger

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class PollingManager(QObject):
    """统一轮询管理器（单例模式）- 文件 IO 在后台线程执行
    
    设计理念：
    - 所有轮询任务共享一个主定时器，避免定时器泛滥
    - 支持任务注册/注销机制
    - 支持不同轮询间隔的任务（通过计数实现）
    - 提供统一的信号接口供其他组件订阅
    - ✅ 文件 IO 在后台线程执行，不阻塞 UI
    
    用法：
        manager = PollingManager.instance()
        
        # 订阅信号（由主线程连接，自动跨线程排队）
        manager.node_status_changed.connect(handle_node_status)
        manager.log_file_changed.connect(handle_log_change)
        manager.config_file_changed.connect(handle_config_change)
        
        # 启动轮询（线程安全，可由主线程调用）
        manager.start(nodes_data)
    """
    
    # ---- 信号定义 ----
    # 节点状态相关
    node_status_changed = Signal(str, str)    # (node_name, new_status)
    
    # 日志文件相关
    log_file_changed = Signal(str, str)       # (node_path, log_filename)
    global_log_changed = Signal(str, str)     # (log_file, content)
    
    # 配置文件相关
    config_file_changed = Signal(str)         # (node_path) — config.json 变更
    global_config_changed = Signal(str)       # (config_file)
    output_json_changed = Signal(str, str)    # (node_path, content)
    
    # 应用状态相关
    app_state_changed = Signal(str)           # (state)
    
    _instance = None
    _initialized = False
    
    @classmethod
    def instance(cls, parent=None):
        """获取全局单例实例"""
        if cls._instance is None:
            cls._instance = cls(parent)
        return cls._instance
    
    def __init__(self, parent=None):
        # 【关键】对于 QObject 子类，必须始终调用 super().__init__()
        # 否则 Qt 的 C++ 层会报错：super-class __init__() was never called
        super().__init__(parent)
        
        # 单例检查：如果已初始化，跳过后续初始化逻辑
        if PollingManager._initialized:
            return
        
        PollingManager._initialized = True
        
        # ---- 线程安全锁：保护所有被主线程/后台线程共享的数据结构 ----
        self._lock = threading.RLock()
        
        # ---- 后台线程：承载主定时器与所有文件 IO 任务 ----
        self._worker_thread = QThread(self)
        self._worker_thread.setObjectName("PollingWorker")
        
        # ---- 基础路径 ----
        self._base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._logs_dir = os.path.join(self._base_dir, "logs")
        
        # ---- 频率模式常量 ----
        self.FREQ_HIGH = 1
        self.FREQ_NORMAL = 2
        self.FREQ_LOW = 4
        
        self.CPU_LOW_THRESHOLD = 30
        self.CPU_HIGH_THRESHOLD = 60
        
        # ---- 主定时器 ----
        self.tick_duration = self.FREQ_NORMAL
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(self.tick_duration * 1000)
        self._timer.timeout.connect(self._poll)
        
        # ---- 动态频率相关 ----
        self._last_cpu_check = 0
        self._cpu_check_interval = 10
        
        # ---- 轮询计数器 ----
        self._tick_count = 0
        
        # ---- 外部引用 ----
        self._nodes_data = None
        
        # ---- 任务注册列表 ----
        # {task_name: {interval: 轮询间隔(秒), callback: 回调函数, enabled: 是否启用}}
        self._tasks = {}
        
        # ---- 节点级监控 ----
        # 日志文件监听器 {(node_path, log_filename): last_mtime}
        self._log_watchers = {}
        # config.json 监听器 {node_path: (last_mtime, last_content)}
        self._config_watchers = {}
        # output.json 监听器 {node_path: (last_mtime, last_content)}
        self._output_watchers = {}
        
        # ---- 全局级监控 ----
        # {file_path: (last_mtime, last_content)}
        self._global_watched_files = {}
        # 全局日志缓存（最近1000行）
        self._log_cache = {
            "bnos.log": [],
            "bnos_error.log": []
        }
        
        # ---- 应用状态 ----
        self._app_state = "running"
        
        # ---- 初始化默认任务 ----
        self._init_default_tasks()
        self._init_global_watchers()
        
        # ---- 将 PollingManager 移至后台线程 ----
        # 【关键】self._timer 的父对象 self 移到 worker thread 后，
        # timer 也会属于 worker thread，其 timeout 会在 worker thread 触发
        self.moveToThread(self._worker_thread)
        logger.info("PollingManager initialized (background thread mode)")
    
    # ==================== 任务注册接口 ====================
    
    def register_task(self, task_name, interval, callback):
        """注册自定义轮询任务（线程安全，可由主线程调用）
        
        Args:
            task_name: 任务名称（唯一标识）
            interval: 轮询间隔（秒）
            callback: 回调函数（无参数）——在后台线程执行！
        """
        with self._lock:
            if task_name not in self._tasks:
                self._tasks[task_name] = {
                    'interval': interval,
                    'callback': callback,
                    'enabled': True
                }
                logger.debug(f"Registered polling task: {task_name} (interval: {interval}s)")
    
    def unregister_task(self, task_name):
        """注销轮询任务（线程安全）"""
        with self._lock:
            if task_name in self._tasks:
                del self._tasks[task_name]
                logger.debug(f"Unregistered polling task: {task_name}")
    
    def enable_task(self, task_name, enabled=True):
        """启用/禁用任务（线程安全）"""
        with self._lock:
            if task_name in self._tasks:
                self._tasks[task_name]['enabled'] = enabled
                logger.debug(f"Task {task_name} {'enabled' if enabled else 'disabled'}")

    # ==================== 清理接口 ====================

    def cleanup_node_watchers(self, node_path: str):
        """移除指定节点的所有监控器（线程安全）"""
        with self._lock:
            self._log_watchers = {
                k: v for k, v in self._log_watchers.items()
                if k[0] != node_path
            }
            self._config_watchers.pop(node_path, None)
            self._output_watchers.pop(node_path, None)

    def cleanup_all_watchers(self):
        """清空所有节点级监控器（线程安全）"""
        with self._lock:
            self._log_watchers.clear()
            self._config_watchers.clear()
            self._output_watchers.clear()
        logger.info("所有节点级监控器已清理")

    # ==================== 启动/停止 ====================
    
    def start(self, nodes_data=None):
        """启动轮询管理器（线程安全，可由主线程调用）
        
        启动后台线程 event loop，并在 worker thread 激活定时器。
        所有文件 IO 都在后台线程执行，不阻塞 UI。
        """
        with self._lock:
            self._nodes_data = nodes_data
        
        if not self._worker_thread.isRunning():
            self._worker_thread.start()
            logger.info("PollingManager worker thread started")
        
        # 【关键】通过信号跨线程调用 _start_timer
        # 因为 self 现在属于 _worker_thread，必须用 Qt.QueuedConnection
        # 让 _start_timer 在 worker thread 的 event loop 中执行
        QTimer.singleShot(0, self._start_timer)
        logger.info("PollingManager started")
    
    def _start_timer(self):
        """在 worker thread 内激活定时器（私有，仅供 start() 通过信号调用）"""
        if not self._timer.isActive():
            self._timer.start()
            logger.debug("Polling timer activated in worker thread")
    
    def stop(self):
        """停止轮询管理器（线程安全）"""
        # 跨线程停止定时器：通过 QTimer.singleShot 让 stop 在 worker thread 内执行
        QTimer.singleShot(0, self._timer.stop)
        # 终止 worker thread 事件循环（quit 是线程安全的，向 worker 投递退出事件）
        if hasattr(self, '_worker_thread') and self._worker_thread.isRunning():
            self._worker_thread.quit()
            # 等待线程真正退出（最多 2 秒，避免卡死）
            if not self._worker_thread.wait(2000):
                self._worker_thread.terminate()
                self._worker_thread.wait(1000)
        logger.info("PollingManager stopped")
    
    # ==================== 初始化 ====================
    
    def _init_default_tasks(self):
        """初始化默认轮询任务（interval 单位：主 tick 数，tick 时长根据 CPU 负载动态调整）
        
        默认频率（中负载）: tick = 2秒
        高频模式（低负载）: tick = 1秒
        低频模式（高负载）: tick = 4秒
        """
        # 节点健康检测（最高频，直接反映节点生死状态）
        self.register_task('node_health', 1, self._poll_node_health)

        # 全局日志检测（中高频）
        self.register_task('global_logs', 2, self._poll_global_logs)

        # 全局配置检测（中高频）
        self.register_task('global_config', 2, self._poll_global_config)

        # 节点日志检测（中高频）
        self.register_task('node_logs', 2, self._poll_node_logs)

        # 节点配置检测（中频，文件内容变化不频繁）
        self.register_task('node_config', 3, self._poll_node_config)

        # 节点输出检测（中频）
        self.register_task('node_output', 3, self._poll_node_output)

        # 应用状态检测（低频）
        self.register_task('app_state', 5, self._poll_app_state)
    
    def _init_global_watchers(self):
        """初始化全局文件监控器"""
        # 监控全局日志文件
        for log_file in ["bnos.log", "bnos_error.log"]:
            path = os.path.join(self._logs_dir, log_file)
            self._add_global_watcher(path)
        
        # 监控全局配置文件
        config_files = [
            os.path.join(self._base_dir, "app_config.json"),
            os.path.join(self._base_dir, "color_settings.json")
        ]
        for config_file in config_files:
            self._add_global_watcher(config_file)
    
    def _add_global_watcher(self, file_path):
        """添加全局文件监控"""
        if file_path not in self._global_watched_files:
            try:
                if os.path.exists(file_path):
                    mtime = os.path.getmtime(file_path)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    mtime = 0
                    content = ""
            except OSError:
                mtime = 0
                content = ""
            self._global_watched_files[file_path] = (mtime, content)
    
    # ==================== 主轮询逻辑 ====================
    
    def _poll(self):
        """主轮询回调 - 在 worker thread 执行，通过 _lock 保护共享数据"""
        try:
            self._tick_count += 1

            # 动态频率调整：定期检查 CPU 负载并调整轮询频率
            self._adjust_frequency()

            # 只读快照 _tasks，避免长时间持有锁
            with self._lock:
                tasks_snapshot = list(self._tasks.items())
                tick_count = self._tick_count

            # 执行所有到期的任务（任务回调内部会再次加锁读共享数据）
            for task_name, task_info in tasks_snapshot:
                if task_info['enabled'] and tick_count % task_info['interval'] == 0:
                    try:
                        task_info['callback']()
                    except Exception as e:
                        logger.error(f"Polling task {task_name} failed: {e}")
        except KeyboardInterrupt:
            logger.info("Polling interrupted by user")
            self.stop()
    
    # ==================== 动态频率调整 ====================
    
    def _adjust_frequency(self):
        """根据 CPU 负载动态调整轮询频率"""
        if not HAS_PSUTIL:
            return
        
        self._last_cpu_check += 1
        if self._last_cpu_check < self._cpu_check_interval:
            return
        
        self._last_cpu_check = 0
        cpu_usage = self._get_cpu_usage()
        
        if cpu_usage < self.CPU_LOW_THRESHOLD:
            new_freq = self.FREQ_HIGH
        elif cpu_usage <= self.CPU_HIGH_THRESHOLD:
            new_freq = self.FREQ_NORMAL
        else:
            new_freq = self.FREQ_LOW
        
        if new_freq != self.tick_duration:
            old_freq = self.tick_duration
            self.tick_duration = new_freq
            self._timer.setInterval(new_freq * 1000)
            logger.info(f"Polling frequency adjusted: {old_freq}s → {new_freq}s (CPU: {cpu_usage:.1f}%)")
    
    def _get_cpu_usage(self):
        """获取系统 CPU 使用率（百分比）"""
        if not HAS_PSUTIL:
            return 0.0
        try:
            return psutil.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"Failed to get CPU usage: {e}")
            return 0.0
    
    # ==================== 节点级检测任务 ====================
    
    def _poll_node_health(self):
        """节点进程健康检查（worker thread 执行）"""
        with self._lock:
            if self._nodes_data is None:
                return
            # 快照：避免在 check_running_processes 调用期间被修改
            nodes_data = self._nodes_data
        
        from ui.core.node_process import check_running_processes
        changes = check_running_processes(nodes_data)
        for name, code, new_status in changes:
            # ✅ 通过 Signal 发回主线程，Qt 自动跨线程排队
            self.node_status_changed.emit(name, new_status)
    
    def _poll_node_logs(self):
        """检查已订阅的节点日志文件（worker thread 执行）"""
        with self._lock:
            # 拷贝一份快照，避免在迭代过程中被主线程修改
            watchers_snapshot = list(self._log_watchers.items())
        
        changed = []
        for (node_path, log_filename), last_mtime in watchers_snapshot:
            full = os.path.join(node_path, "logs", log_filename)
            try:
                if not os.path.exists(full):
                    continue
                mtime = os.path.getmtime(full)
            except OSError:
                continue
            if mtime > last_mtime:
                changed.append(((node_path, log_filename), mtime))
        
        # 更新 state + emit signals
        if changed:
            with self._lock:
                for key, new_mtime in changed:
                    self._log_watchers[key] = new_mtime
            for (node_path, log_filename), _ in changed:
                self.log_file_changed.emit(node_path, log_filename)
    
    def _poll_node_config(self):
        """检查已订阅的节点 config.json（worker thread 执行）"""
        with self._lock:
            watchers_snapshot = list(self._config_watchers.items())
        
        changed = []  # [(node_path, new_mtime, new_content, should_notify)]
        for node_path, (last_mtime, last_content) in watchers_snapshot:
            config_path = os.path.join(node_path, "config.json")
            try:
                if not os.path.exists(config_path):
                    continue
                mtime = os.path.getmtime(config_path)
                if mtime <= last_mtime:
                    continue
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # mtime 变但内容不变（例如 atomic write / git restore）
                if content == last_content:
                    changed.append((node_path, mtime, content, False))
                    continue
                changed.append((node_path, mtime, content, True))
            except OSError:
                pass
        
        if changed:
            with self._lock:
                for node_path, mtime, content, _ in changed:
                    self._config_watchers[node_path] = (mtime, content)
            for node_path, _, _, should_notify in changed:
                if should_notify:
                    self.config_file_changed.emit(node_path)
    
    def _poll_node_output(self):
        """检查已订阅的节点 output.json（worker thread 执行）"""
        with self._lock:
            watchers_snapshot = list(self._output_watchers.items())
        
        changed = []
        for node_path, (last_mtime, last_content) in watchers_snapshot:
            path = os.path.join(node_path, "output.json")
            try:
                if not os.path.exists(path):
                    continue
                mtime = os.path.getmtime(path)
                if mtime <= last_mtime:
                    continue
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content == last_content:
                    changed.append((node_path, mtime, content, False))
                    continue
                changed.append((node_path, mtime, content, True))
            except OSError:
                pass
        
        if changed:
            with self._lock:
                for node_path, mtime, content, _ in changed:
                    self._output_watchers[node_path] = (mtime, content)
            for node_path, _, content, should_notify in changed:
                if should_notify:
                    self.output_json_changed.emit(node_path, content)
    
    # ==================== 全局级检测任务 ====================
    
    def _poll_global_logs(self):
        """检查全局日志文件变化（worker thread 执行）"""
        with self._lock:
            watched_snapshot = dict(self._global_watched_files)
        
        changed = []
        for log_file in ["bnos.log", "bnos_error.log"]:
            path = os.path.join(self._logs_dir, log_file)
            if path not in watched_snapshot:
                continue
            last_mtime, last_content = watched_snapshot[path]
            try:
                if not os.path.exists(path):
                    continue
                mtime = os.path.getmtime(path)
                if mtime <= last_mtime:
                    continue
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content == last_content:
                    changed.append((path, mtime, content, False))
                    continue
                changed.append((path, mtime, content, True))
            except OSError as e:
                logger.warning(f"Error reading global log {log_file}: {e}")
        
        if changed:
            with self._lock:
                for path, mtime, content, _ in changed:
                    self._global_watched_files[path] = (mtime, content)
            for path, _, content, should_notify in changed:
                if should_notify:
                    log_file = os.path.basename(path)
                    self._update_log_cache(log_file, content)
                    self.global_log_changed.emit(log_file, content)
    
    def _poll_global_config(self):
        """检查全局配置文件变化（worker thread 执行）"""
        with self._lock:
            watched_snapshot = dict(self._global_watched_files)
        
        config_files = [
            os.path.join(self._base_dir, "app_config.json"),
            os.path.join(self._base_dir, "color_settings.json")
        ]
        changed = []
        for config_file in config_files:
            if config_file not in watched_snapshot:
                continue
            last_mtime, last_content = watched_snapshot[config_file]
            try:
                if not os.path.exists(config_file):
                    continue
                mtime = os.path.getmtime(config_file)
                if mtime <= last_mtime:
                    continue
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content == last_content:
                    changed.append((config_file, mtime, content, False))
                    continue
                changed.append((config_file, mtime, content, True))
            except OSError as e:
                logger.warning(f"Error reading config {config_file}: {e}")
        
        if changed:
            with self._lock:
                for path, mtime, content, _ in changed:
                    self._global_watched_files[path] = (mtime, content)
            for path, _, _, should_notify in changed:
                if should_notify:
                    self.global_config_changed.emit(os.path.basename(path))
    
    def _poll_app_state(self):
        """检查应用状态（worker thread 执行）"""
        new_state = self._detect_app_state()
        if new_state != self._app_state:
            with self._lock:
                self._app_state = new_state
            self.app_state_changed.emit(new_state)
    
    def _detect_app_state(self):
        """检测应用运行状态"""
        return "running"
    
    # ==================== 日志缓存管理 ====================
    
    def _update_log_cache(self, log_file, content):
        """更新日志缓存（worker thread 或主线程均可调用）"""
        lines = content.strip().split('\n')
        max_lines = 1000
        
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        
        with self._lock:
            self._log_cache[log_file] = lines
    
    # ==================== 节点级订阅接口（主线程调用，线程安全）====================
    
    def watch_log(self, node_path: str, log_filename: str):
        """订阅节点日志文件变化"""
        key = (node_path, log_filename)
        try:
            full = os.path.join(node_path, "logs", log_filename)
            mtime = os.path.getmtime(full) if os.path.exists(full) else 0
        except OSError:
            mtime = 0
        with self._lock:
            if key not in self._log_watchers:
                self._log_watchers[key] = mtime
    
    def unwatch_log(self, node_path: str, log_filename: str):
        """取消订阅节点日志文件"""
        key = (node_path, log_filename)
        with self._lock:
            self._log_watchers.pop(key, None)
    
    def watch_config(self, node_path: str):
        """订阅节点 config.json"""
        config_path = os.path.join(node_path, "config.json")
        try:
            if os.path.exists(config_path):
                mtime = os.path.getmtime(config_path)
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                mtime = 0
                content = ""
        except OSError:
            mtime = 0
            content = ""
        with self._lock:
            if node_path not in self._config_watchers:
                self._config_watchers[node_path] = (mtime, content)
    
    def unwatch_config(self, node_path: str):
        """取消订阅节点 config.json"""
        with self._lock:
            self._config_watchers.pop(node_path, None)
    
    def watch_output_json(self, node_path: str):
        """订阅节点 output.json"""
        path = os.path.join(node_path, "output.json")
        try:
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                mtime = 0
                content = ""
        except OSError:
            mtime = 0
            content = ""
        with self._lock:
            if node_path not in self._output_watchers:
                self._output_watchers[node_path] = (mtime, content)
    
    def unwatch_output_json(self, node_path: str):
        """取消订阅节点 output.json"""
        with self._lock:
            self._output_watchers.pop(node_path, None)
    
    # ==================== 公开查询接口（主线程调用，线程安全）====================
    
    def get_recent_logs(self, log_file=None, count=50):
        """获取最近的日志记录"""
        with self._lock:
            if log_file:
                if log_file in self._log_cache:
                    lines = self._log_cache[log_file][-count:]
                    return lines[::-1]
                return []
            
            all_lines = []
            for file_name, lines in self._log_cache.items():
                for line in lines[-count // 2:]:
                    all_lines.append((file_name, line))
            
        all_lines.sort(key=lambda x: x[1], reverse=True)
        return [f"[{name}] {line}" for name, line in all_lines[:count]]
    
    def get_log_file_content(self, log_file):
        """获取指定日志文件的完整内容"""
        path = os.path.join(self._logs_dir, log_file)
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except OSError:
                return ""
        return ""
    
    def get_app_config(self):
        """获取应用配置"""
        config_path = os.path.join(self._base_dir, "app_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return {}
        return {}
    
    def get_color_settings(self):
        """获取颜色配置"""
        color_path = os.path.join(self._base_dir, "color_settings.json")
        if os.path.exists(color_path):
            try:
                with open(color_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                return {}
        return {}
    
    def get_app_state(self):
        """获取当前应用状态"""
        with self._lock:
            return {
                "state": self._app_state,
                "timestamp": datetime.now().isoformat(),
                "watched_files_count": len(self._global_watched_files) + len(self._log_watchers),
                "log_cache_size": sum(len(lines) for lines in self._log_cache.values()),
                "registered_tasks": list(self._tasks.keys())
            }
    
    def get_watched_files(self):
        """获取所有被监控的文件列表"""
        with self._lock:
            return list(self._global_watched_files.keys())
    
    def get_registered_tasks(self):
        """获取所有已注册的轮询任务"""
        with self._lock:
            return {name: info['interval'] for name, info in self._tasks.items()}


# 全局便捷实例
polling_manager = PollingManager.instance()