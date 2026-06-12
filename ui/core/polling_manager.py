"""
统一轮询管理器 - 单例模式
将所有需要定时轮询的任务统一管理，避免多个定时器并行运行

管理职责：
  1. 节点进程健康状态检测
  2. 全局日志文件监控
  3. 全局配置文件监控
  4. 进程管理器健康检查
  5. 提供统一的任务注册接口
"""
import os
import json
from datetime import datetime
from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal
from ui.core.logger import logger


class PollingManager(QObject):
    """统一轮询管理器（单例模式）
    
    设计理念：
    - 所有轮询任务共享一个主定时器，避免定时器泛滥
    - 支持任务注册/注销机制
    - 支持不同轮询间隔的任务（通过计数实现）
    - 提供统一的信号接口供其他组件订阅
    
    用法：
        manager = PollingManager.instance()
        
        # 订阅信号
        manager.node_status_changed.connect(handle_node_status)
        manager.log_file_changed.connect(handle_log_change)
        manager.config_file_changed.connect(handle_config_change)
        
        # 启动轮询
        manager.start(nodes_data)
    """
    
    # ---- 信号定义 ----
    # 节点状态相关
    node_status_changed = pyqtSignal(str, str)    # (node_name, new_status)
    
    # 日志文件相关
    log_file_changed = pyqtSignal(str, str)       # (node_path, log_filename)
    global_log_changed = pyqtSignal(str, str)     # (log_file, content)
    
    # 配置文件相关
    config_file_changed = pyqtSignal(str)         # (node_path) — config.json 变更
    global_config_changed = pyqtSignal(str)       # (config_file)
    output_json_changed = pyqtSignal(str, str)    # (node_path, content)
    
    # 应用状态相关
    app_state_changed = pyqtSignal(str)           # (state)
    
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
        
        # ---- 基础路径 ----
        self._base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self._logs_dir = os.path.join(self._base_dir, "logs")
        
        # ---- 主定时器（1秒轮询一次，内部按任务间隔分发）----
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(1000)  # 1秒基础间隔
        self._timer.timeout.connect(self._poll)
        
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
    
    # ==================== 任务注册接口 ====================
    
    def register_task(self, task_name, interval, callback):
        """注册自定义轮询任务
        
        Args:
            task_name: 任务名称（唯一标识）
            interval: 轮询间隔（秒）
            callback: 回调函数（无参数）
        """
        if task_name not in self._tasks:
            self._tasks[task_name] = {
                'interval': interval,
                'callback': callback,
                'enabled': True
            }
            logger.debug(f"Registered polling task: {task_name} (interval: {interval}s)")
    
    def unregister_task(self, task_name):
        """注销轮询任务"""
        if task_name in self._tasks:
            del self._tasks[task_name]
            logger.debug(f"Unregistered polling task: {task_name}")
    
    def enable_task(self, task_name, enabled=True):
        """启用/禁用任务"""
        if task_name in self._tasks:
            self._tasks[task_name]['enabled'] = enabled
            logger.debug(f"Task {task_name} {'enabled' if enabled else 'disabled'}")
    
    # ==================== 启动/停止 ====================
    
    def start(self, nodes_data=None):
        """启动轮询管理器"""
        self._nodes_data = nodes_data
        self._timer.start()
        logger.info("PollingManager started")
    
    def stop(self):
        """停止轮询管理器"""
        self._timer.stop()
        logger.info("PollingManager stopped")
    
    # ==================== 初始化 ====================
    
    def _init_default_tasks(self):
        """初始化默认轮询任务"""
        # 节点健康检测（2秒）
        self.register_task('node_health', 2, self._poll_node_health)
        
        # 全局日志检测（2秒）
        self.register_task('global_logs', 2, self._poll_global_logs)
        
        # 全局配置检测（2秒）
        self.register_task('global_config', 2, self._poll_global_config)
        
        # 节点日志检测（2秒）
        self.register_task('node_logs', 2, self._poll_node_logs)
        
        # 节点配置检测（2秒）
        self.register_task('node_config', 2, self._poll_node_config)
        
        # 节点输出检测（2秒）
        self.register_task('node_output', 2, self._poll_node_output)
        
        # 应用状态检测（5秒）
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
        """主轮询回调 - 按间隔分发任务"""
        try:
            self._tick_count += 1
            
            # 执行所有到期的任务
            for task_name, task_info in list(self._tasks.items()):
                if task_info['enabled'] and self._tick_count % task_info['interval'] == 0:
                    try:
                        task_info['callback']()
                    except Exception as e:
                        logger.error(f"Polling task {task_name} failed: {e}")
        except KeyboardInterrupt:
            logger.info("Polling interrupted by user")
            self.stop()
    
    # ==================== 节点级检测任务 ====================
    
    def _poll_node_health(self):
        """节点进程健康检查"""
        if self._nodes_data is None:
            return
        
        from ui.core.node_process import check_running_processes
        changes = check_running_processes(self._nodes_data)
        for name, code, new_status in changes:
            self.node_status_changed.emit(name, new_status)
    
    def _poll_node_logs(self):
        """检查已订阅的节点日志文件"""
        for (node_path, log_filename), last_mtime in list(self._log_watchers.items()):
            full = os.path.join(node_path, "logs", log_filename)
            try:
                if not os.path.exists(full):
                    continue
                mtime = os.path.getmtime(full)
            except OSError:
                continue
            if mtime > last_mtime:
                self._log_watchers[(node_path, log_filename)] = mtime
                self.log_file_changed.emit(node_path, log_filename)
    
    def _poll_node_config(self):
        """检查已订阅的节点 config.json"""
        for node_path, (last_mtime, last_content) in list(self._config_watchers.items()):
            config_path = os.path.join(node_path, "config.json")
            try:
                if not os.path.exists(config_path):
                    continue
                mtime = os.path.getmtime(config_path)
                if mtime <= last_mtime:
                    continue
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if content == last_content:
                    self._config_watchers[node_path] = (mtime, content)
                    continue
                self._config_watchers[node_path] = (mtime, content)
                self.config_file_changed.emit(node_path)
            except OSError:
                pass
    
    def _poll_node_output(self):
        """检查已订阅的节点 output.json"""
        for node_path, (last_mtime, last_content) in list(self._output_watchers.items()):
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
                    self._output_watchers[node_path] = (mtime, content)
                    continue
                self._output_watchers[node_path] = (mtime, content)
                self.output_json_changed.emit(node_path, content)
            except OSError:
                pass
    
    # ==================== 全局级检测任务 ====================
    
    def _poll_global_logs(self):
        """检查全局日志文件变化"""
        for log_file in ["bnos.log", "bnos_error.log"]:
            path = os.path.join(self._logs_dir, log_file)
            if path not in self._global_watched_files:
                continue
            
            last_mtime, last_content = self._global_watched_files[path]
            
            try:
                if not os.path.exists(path):
                    continue
                
                mtime = os.path.getmtime(path)
                if mtime <= last_mtime:
                    continue
                
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if content == last_content:
                    self._global_watched_files[path] = (mtime, content)
                    continue
                
                self._update_log_cache(log_file, content)
                self._global_watched_files[path] = (mtime, content)
                self.global_log_changed.emit(log_file, content)
                
            except OSError as e:
                logger.warning(f"Error reading global log {log_file}: {e}")
    
    def _poll_global_config(self):
        """检查全局配置文件变化"""
        config_files = [
            os.path.join(self._base_dir, "app_config.json"),
            os.path.join(self._base_dir, "color_settings.json")
        ]
        
        for config_file in config_files:
            if config_file not in self._global_watched_files:
                continue
            
            last_mtime, last_content = self._global_watched_files[config_file]
            
            try:
                if not os.path.exists(config_file):
                    continue
                
                mtime = os.path.getmtime(config_file)
                if mtime <= last_mtime:
                    continue
                
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if content == last_content:
                    self._global_watched_files[config_file] = (mtime, content)
                    continue
                
                self._global_watched_files[config_file] = (mtime, content)
                self.global_config_changed.emit(os.path.basename(config_file))
                
            except OSError as e:
                logger.warning(f"Error reading config {config_file}: {e}")
    
    def _poll_app_state(self):
        """检查应用状态"""
        new_state = self._detect_app_state()
        if new_state != self._app_state:
            self._app_state = new_state
            self.app_state_changed.emit(new_state)
    
    def _detect_app_state(self):
        """检测应用运行状态"""
        return "running"
    
    # ==================== 日志缓存管理 ====================
    
    def _update_log_cache(self, log_file, content):
        """更新日志缓存"""
        lines = content.strip().split('\n')
        max_lines = 1000
        
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        
        self._log_cache[log_file] = lines
    
    # ==================== 节点级订阅接口 ====================
    
    def watch_log(self, node_path: str, log_filename: str):
        """订阅节点日志文件变化"""
        key = (node_path, log_filename)
        if key not in self._log_watchers:
            full = os.path.join(node_path, "logs", log_filename)
            try:
                mtime = os.path.getmtime(full) if os.path.exists(full) else 0
            except OSError:
                mtime = 0
            self._log_watchers[key] = mtime
    
    def unwatch_log(self, node_path: str, log_filename: str):
        """取消订阅节点日志文件"""
        key = (node_path, log_filename)
        self._log_watchers.pop(key, None)
    
    def watch_config(self, node_path: str):
        """订阅节点 config.json"""
        if node_path not in self._config_watchers:
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
            self._config_watchers[node_path] = (mtime, content)
    
    def unwatch_config(self, node_path: str):
        """取消订阅节点 config.json"""
        self._config_watchers.pop(node_path, None)
    
    def watch_output_json(self, node_path: str):
        """订阅节点 output.json"""
        if node_path not in self._output_watchers:
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
            self._output_watchers[node_path] = (mtime, content)
    
    def unwatch_output_json(self, node_path: str):
        """取消订阅节点 output.json"""
        self._output_watchers.pop(node_path, None)
    
    # ==================== 公开查询接口 ====================
    
    def get_recent_logs(self, log_file=None, count=50):
        """获取最近的日志记录"""
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
        return {
            "state": self._app_state,
            "timestamp": datetime.now().isoformat(),
            "watched_files_count": len(self._global_watched_files) + len(self._log_watchers),
            "log_cache_size": sum(len(lines) for lines in self._log_cache.values()),
            "registered_tasks": list(self._tasks.keys())
        }
    
    def get_watched_files(self):
        """获取所有被监控的文件列表"""
        return list(self._global_watched_files.keys())
    
    def get_registered_tasks(self):
        """获取所有已注册的轮询任务"""
        return {name: info['interval'] for name, info in self._tasks.items()}


# 全局便捷实例
polling_manager = PollingManager.instance()