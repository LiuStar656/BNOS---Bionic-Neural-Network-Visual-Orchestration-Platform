"""
Toast 队列管理器 - 实现提示信息的有序排队与依次显示

核心功能：
1. FIFO队列管理：确保提示按顺序显示
2. 智能替换机制：同节点同操作的提示可以替换（如"正在启动"替换为"启动成功"）
3. 堆叠显示支持：最多同时显示3个Toast
4. 立即显示优先：操作状态提示（如"正在启动"）优先显示
5. 生命周期回调：Toast关闭后自动处理队列
"""
from collections import deque
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from typing import Optional, Dict, Any, Callable


class ToastRequest:
    """Toast请求封装"""
    
    def __init__(self, message: str, toast_type: str = "info", duration: int = 3000,
                 node_name: Optional[str] = None, operation_type: Optional[str] = None,
                 is_status: bool = False):
        self.message = message
        self.toast_type = toast_type
        self.duration = duration
        self.node_name = node_name
        self.operation_type = operation_type
        self.is_status = is_status  # 是否为操作状态提示（应立即显示）


class ToastQueueManager(QObject):
    """Toast队列管理器 - 单例模式"""
    
    _instance = None
    
    # 信号：请求显示Toast
    show_toast_requested = pyqtSignal(dict)
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            instance = super().__new__(cls, *args, **kwargs)
            # 立即调用父类 __init__
            QObject.__init__(instance)
            cls._instance = instance
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        # 队列：存储待显示的Toast请求
        self._queue = deque()
        
        # 当前活动的Toast列表（最多3个堆叠显示）
        self._active_toasts = []
        self._max_active = 3
        
        # 智能替换映射：(node_name, operation_type) -> toast
        self._operation_toasts: Dict[tuple, Any] = {}
        
        # 回调函数：用于创建Toast
        self._create_toast_callback: Optional[Callable] = None
        
        # 父窗口引用
        self._parent_window = None
        
        self._initialized = True
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def initialize(self, parent_window, create_toast_callback):
        """初始化管理器"""
        self._parent_window = parent_window
        self._create_toast_callback = create_toast_callback
    
    def show_toast(self, message: str, toast_type: str = "info", duration: int = 3000,
                   node_name: Optional[str] = None, operation_type: Optional[str] = None):
        """
        请求显示Toast提示
        
        Args:
            message: 提示消息
            toast_type: 提示类型 (info/success/warning/error)
            duration: 显示时长（毫秒）
            node_name: 关联节点名称（用于智能替换）
            operation_type: 操作类型（用于智能替换）
        """
        # 判断是否为操作状态提示
        is_status = toast_type == "info" and (operation_type in ("start", "stop", "delete", "create"))
        
        # 智能替换：检查是否有同节点同操作的提示
        if node_name is not None and operation_type is not None:
            key = (node_name, operation_type)
            
            # 如果正在显示同节点同操作的Toast，替换它
            if key in self._operation_toasts:
                existing_toast = self._operation_toasts[key]
                if existing_toast and existing_toast.isVisible():
                    # 如果是状态提示替换状态提示，直接更新消息
                    if is_status:
                        existing_toast._label.setText(message)
                        existing_toast._stay_timer.start(duration)
                        return
                    # 如果是结果提示替换状态提示，关闭旧的并显示新的
                    else:
                        self._remove_toast(existing_toast, key)
            
            # 检查队列中是否有相同的请求，替换它
            for req in self._queue:
                if req.node_name == node_name and req.operation_type == operation_type:
                    req.message = message
                    req.toast_type = toast_type
                    req.duration = duration
                    req.is_status = is_status
                    return
        
        # 创建新请求
        request = ToastRequest(
            message=message,
            toast_type=toast_type,
            duration=duration,
            node_name=node_name,
            operation_type=operation_type,
            is_status=is_status
        )
        
        # 状态提示优先插入到队列前端
        if is_status:
            self._queue.appendleft(request)
        else:
            self._queue.append(request)
        
        # 尝试立即显示
        self._process_queue()
    
    def _process_queue(self):
        """处理队列，显示下一个Toast"""
        # 如果活动Toast已达上限，等待
        if len(self._active_toasts) >= self._max_active:
            return
        
        # 如果队列为空，返回
        if not self._queue:
            return
        
        # 获取下一个请求
        request = self._queue.popleft()
        
        # 创建Toast
        if self._create_toast_callback:
            stack_index = len(self._active_toasts)
            toast = self._create_toast_callback(
                message=request.message,
                toast_type=request.toast_type,
                duration=request.duration,
                stack_index=stack_index,
                node_name=request.node_name,
                operation_type=request.operation_type
            )
            
            # 存储映射
            if request.node_name is not None and request.operation_type is not None:
                key = (request.node_name, request.operation_type)
                self._operation_toasts[key] = toast
            
            # 添加到活动列表
            self._active_toasts.append(toast)
            
            # 设置关闭回调
            toast.closed.connect(lambda t=toast: self._on_toast_closed(t))
            
            # 显示Toast
            toast.show_toast()
    
    def _remove_toast(self, toast, key: tuple = None):
        """移除Toast"""
        # 停止动画和计时器
        toast._anim_timer.stop()
        if toast._stay_timer.isActive():
            toast._stay_timer.stop()
        
        # 从活动列表移除
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)
        
        # 从映射移除
        if key:
            if self._operation_toasts.get(key) == toast:
                del self._operation_toasts[key]
        
        # 关闭Toast
        toast.close()
        
        # 更新剩余Toast的位置
        self._update_positions()
        
        # 处理下一个队列请求
        QTimer.singleShot(50, self._process_queue)
    
    def _on_toast_closed(self, toast):
        """Toast关闭回调"""
        # 查找并移除映射
        keys_to_remove = []
        for key, t in self._operation_toasts.items():
            if t == toast:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._operation_toasts[key]
        
        # 从活动列表移除
        if toast in self._active_toasts:
            self._active_toasts.remove(toast)
        
        # 更新剩余Toast的位置
        self._update_positions()
        
        # 处理下一个队列请求
        QTimer.singleShot(50, self._process_queue)
    
    def _update_positions(self):
        """更新所有活动Toast的位置"""
        for i, toast in enumerate(self._active_toasts):
            if toast.stack_index != i:
                toast.stack_index = i
                toast.update_position()
    
    def clear_all(self):
        """清除所有Toast（包括队列和活动的）"""
        # 清空队列
        self._queue.clear()
        
        # 关闭所有活动Toast
        for toast in list(self._active_toasts):
            self._remove_toast(toast)
        
        # 清空映射
        self._operation_toasts.clear()
    
    def get_active_count(self):
        """获取当前活动Toast数量"""
        return len(self._active_toasts)
    
    def get_queue_size(self):
        """获取队列大小"""
        return len(self._queue)