"""
ApplicationContext - 应用全局状态聚合器

提供统一的服务访问入口，避免全局变量分散。

集成了 AppState 集中式状态管理器，支持：
- 单一数据源：所有状态集中存储
- 响应式：状态变化自动通知订阅者
- 可追踪：支持状态变更历史

用法:
    from ui.core.application_context import ApplicationContext
    
    ctx = ApplicationContext()
    ctx.config.save()
    ctx.node_control.start_node(node_id)
    
    # 使用状态管理
    ctx.state.set('project.current', '/path/to/project')
    project_path = ctx.state.get('project.current')
"""


class ApplicationContext:
    """
    应用上下文单例类
    聚合所有全局状态持有者，提供统一访问入口
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def initialize(self):
        """
        初始化所有服务
        必须在应用启动时调用一次
        
        注意：需要主窗口的服务（如 PanelManager）不在此初始化，
        应在主窗口创建后调用 initialize_ui_services()
        """
        if self._initialized:
            return
        
        # 延迟导入避免循环依赖
        from ui.core.app_config import AppConfig
        from ui.core.polling_manager import PollingManager
        from ui.core.node_control_service import NodeControlService
        from ui.core.toast.toast_queue_manager import ToastQueueManager
        from ui.core.file_operation_manager import FileOperationManager
        from ui.core.import_export_manager import ImportExportManager
        from ui.core.process_manager import ProcessManager
        from ui.core.event_bus import EventBus
        from ui.core.app_state import AppState
        from ui.core.node_debugger import NodeDebugger
        
        # 配置服务
        self._config = AppConfig()
        
        # 集中式状态管理
        self._state = AppState()
        self._state.initialize()
        
        # 事件总线
        self._event_bus = EventBus()
        
        # 核心服务（不依赖主窗口）
        self._polling = PollingManager.instance()
        self._node_control = NodeControlService()
        
        # 调试管理器
        self._debugger = NodeDebugger()
        self._debugger.initialize()
        
        self._process_manager = ProcessManager()
        
        # Toast 管理器
        self._toast_manager = ToastQueueManager()
        
        # 文件操作服务
        self._file_operation = FileOperationManager()
        
        # 需要主窗口的服务（延迟初始化）
        self._import_export = None
        self._panel_manager = None
        self._dock_manager = None
        self._shortcut_manager = None
        
        self._initialized = True
    
    def initialize_ui_services(self, main_window):
        """
        初始化依赖主窗口的 UI 服务
        
        Args:
            main_window: 主窗口实例
        """
        if not self._initialized:
            raise RuntimeError("ApplicationContext 尚未初始化")
        
        from ui.core.panel_manager import PanelManager
        from ui.core.dock_manager import DockManager
        from ui.core.shortcut_manager import ShortcutManager
        from ui.core.import_export_manager import ImportExportManager
        
        self._import_export = ImportExportManager(main_window)
        self._panel_manager = PanelManager(main_window, self._config.config_file)
        self._dock_manager = DockManager(main_window)
        self._shortcut_manager = ShortcutManager(self._config)
    
    @property
    def config(self):
        """配置服务"""
        return self._config
    
    @property
    def event_bus(self):
        """事件总线"""
        return self._event_bus
    
    @property
    def polling(self):
        """轮询管理器"""
        return self._polling
    
    @property
    def node_control(self):
        """节点控制服务"""
        return self._node_control
    
    @property
    def process_manager(self):
        """进程管理器"""
        return self._process_manager
    
    @property
    def panel_manager(self):
        """面板管理器"""
        return self._panel_manager
    
    @property
    def dock_manager(self):
        """Dock 管理器"""
        return self._dock_manager
    
    @property
    def toast_manager(self):
        """Toast 管理器"""
        return self._toast_manager
    
    @property
    def shortcut_manager(self):
        """快捷键管理器"""
        return self._shortcut_manager
    
    @property
    def file_operation(self):
        """文件操作管理器"""
        return self._file_operation
    
    @property
    def import_export(self):
        """导入导出管理器"""
        return self._import_export
    
    @property
    def state(self):
        """集中式状态管理器"""
        return self._state
    
    @property
    def debugger(self):
        """节点调试管理器"""
        return self._debugger
    
    def shutdown(self):
        """
        关闭所有服务
        在应用退出时调用
        """
        if not self._initialized:
            return
        
        # 停止轮询
        if hasattr(self, '_polling'):
            self._polling.stop()
        
        # 停止进程
        if hasattr(self, '_process_manager'):
            self._process_manager.stop_all()
        
        # 保存配置
        if hasattr(self, '_config'):
            self._config.save()
        
        self._initialized = False


# 全局便捷访问函数
def get_context() -> ApplicationContext:
    """获取应用上下文（便捷函数）"""
    return ApplicationContext()
