"""
BNOS Toast 管理器 - 管理多个 Toast 的堆叠显示

负责：
1. Toast 的创建和显示
2. 堆叠位置管理
3. 自动位置调整
4. 资源清理
"""
from ui.core.toast.toast_notification import ToastNotification


class ToastManager:
    """Toast 通知管理器
    
    管理多个 Toast 的堆叠显示，自动处理位置调整和生命周期
    """
    
    def __init__(self, parent=None):
        """初始化 Toast 管理器
        
        Args:
            parent: 父窗口对象
        """
        self.parent = parent
        self.active_toasts = []  # 当前显示的 Toast 列表
    
    def show_toast(self, message, toast_type="info", duration=3000):
        """显示 Toast 通知（支持堆叠显示）
        
        Args:
            message: 通知文本内容
            toast_type: 类型 (info/success/warning/error)
            duration: 显示时长（毫秒），默认3000
            
        Returns:
            ToastNotification: 创建的 Toast 对象
        """
        # 先更新所有现有Toast的位置（向下移动一位，为新Toast腾出顶部空间）
        for i, existing_toast in enumerate(self.active_toasts):
            existing_toast.stack_index = i + 1
            existing_toast.update_position()
        
        # 创建新的Toast，设置堆叠索引为0（最顶部）
        stack_index = 0
        toast = ToastNotification(
            message=message,
            parent=self.parent,
            duration=duration,
            toast_type=toast_type,
            stack_index=stack_index
        )
        
        # 添加到活动列表的最前面（最新的在最前）
        self.active_toasts.insert(0, toast)
        
        # 显示Toast
        toast.show_toast()
        
        # 当Toast关闭时，从列表中移除并更新其他Toast位置
        original_close = toast.close
        def custom_close():
            if toast in self.active_toasts:
                self.active_toasts.remove(toast)
                # 更新剩余Toast的位置
                for i, remaining_toast in enumerate(self.active_toasts):
                    remaining_toast.stack_index = i
                    remaining_toast.update_position()
            original_close()
        
        toast.close = custom_close
        
        return toast
    
    def clear_all(self):
        """清除所有 Toast"""
        for toast in self.active_toasts[:]:  # 使用副本避免修改列表时的错误
            toast.close()
        
        self.active_toasts.clear()
    
    def get_active_count(self):
        """获取当前活动的 Toast 数量
        
        Returns:
            int: 活动的 Toast 数量
        """
        return len(self.active_toasts)
    
    def info(self, message, duration=3000):
        """显示信息提示
        
        Args:
            message: 提示消息
            duration: 显示时长
        """
        return self.show_toast(message, "info", duration)
    
    def success(self, message, duration=3000):
        """显示成功提示
        
        Args:
            message: 成功消息
            duration: 显示时长
        """
        return self.show_toast(message, "success", duration)
    
    def warning(self, message, duration=4000):
        """显示警告提示
        
        Args:
            message: 警告消息
            duration: 显示时长
        """
        return self.show_toast(message, "warning", duration)
    
    def error(self, message, duration=5000):
        """显示错误提示
        
        Args:
            message: 错误消息
            duration: 显示时长
        """
        return self.show_toast(message, "error", duration)
