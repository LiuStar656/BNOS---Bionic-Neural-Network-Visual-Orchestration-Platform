"""
Toast 通知系统使用示例

本文件展示了如何在 BNOS 项目中使用独立的 ToastNotification 组件
"""

# ==========================================
# 示例 1: 在 MainWindow 中使用 Toast
# ==========================================

from ui.toast_notification import ToastNotification

class MyMainWindow:
    def __init__(self):
        self.active_toasts = []  # 管理当前显示的 Toast 列表
    
    def show_toast(self, message, toast_type="info", duration=3000):
        """显示 Toast 通知（支持堆叠显示）
        
        Args:
            message: 通知文本内容
            toast_type: 类型 (info/success/warning/error)
            duration: 显示时长（毫秒），默认3000
        """
        # 先更新所有现有Toast的位置（向下移动一位，为新Toast腾出顶部空间）
        for i, existing_toast in enumerate(self.active_toasts):
            existing_toast.stack_index = i + 1
            existing_toast.update_position()
        
        # 创建新的Toast，设置堆叠索引为0（最顶部）
        stack_index = 0
        toast = ToastNotification(
            message=message,
            parent=self,
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


# ==========================================
# 示例 2: 简单的单次 Toast 显示
# ==========================================

def simple_toast_example(parent_widget):
    """简单示例：显示一个 Toast 通知"""
    
    # 成功提示
    toast = ToastNotification(
        message="操作成功！",
        parent=parent_widget,
        duration=3000,
        toast_type="success"
    )
    toast.show_toast()
    
    # 警告提示
    warning_toast = ToastNotification(
        message="请注意检查配置",
        parent=parent_widget,
        duration=4000,
        toast_type="warning"
    )
    warning_toast.show_toast()
    
    # 错误提示
    error_toast = ToastNotification(
        message="操作失败，请重试",
        parent=parent_widget,
        duration=5000,
        toast_type="error"
    )
    error_toast.show_toast()


# ==========================================
# 示例 3: 在不同场景中使用 Toast
# ==========================================

# 场景 1: 节点操作反馈
def node_operation_feedback(main_window, node_name, operation):
    """节点操作后的 Toast 反馈"""
    if operation == "start":
        main_window.show_toast(f"节点 {node_name} 已启动", "success")
    elif operation == "stop":
        main_window.show_toast(f"节点 {node_name} 已停止", "info")
    elif operation == "delete":
        main_window.show_toast(f"节点 {node_name} 已删除", "warning")


# 场景 2: 项目操作反馈
def project_operation_feedback(main_window, project_name, operation):
    """项目操作后的 Toast 反馈"""
    if operation == "create":
        main_window.show_toast(f"已创建项目: {project_name}", "success")
    elif operation == "open":
        main_window.show_toast(f"已打开项目: {project_name}", "success")
    elif operation == "save":
        main_window.show_toast("项目已自动保存", "info")


# 场景 3: 异步任务进度提示
def async_task_progress(main_window, task_name, status):
    """异步任务的进度提示"""
    if status == "start":
        main_window.show_toast(f"开始执行: {task_name}", "info", duration=2000)
    elif status == "complete":
        main_window.show_toast(f"完成: {task_name}", "success")
    elif status == "error":
        main_window.show_toast(f"失败: {task_name}", "error", duration=5000)


# ==========================================
# Toast 类型说明
# ==========================================
"""
支持的 Toast 类型：

1. info (默认)
   - 颜色: 深灰色背景 rgba(50, 50, 50, 230)
   - 用途: 一般信息提示
   
2. success
   - 颜色: 绿色背景 rgba(76, 175, 80, 230)
   - 用途: 操作成功提示
   
3. warning
   - 颜色: 橙色背景 rgba(255, 152, 0, 230)
   - 用途: 警告或注意事项
   
4. error
   - 颜色: 红色背景 rgba(244, 67, 54, 230)
   - 用途: 错误或失败提示
"""


# ==========================================
# 高级特性
# ==========================================

"""
Toast 的高级特性：

1. 堆叠显示
   - 多个 Toast 可以同时在右上角显示
   - 新 Toast 出现在顶部，旧 Toast 自动下移
   - 每个 Toast 间隔 60px 垂直排列

2. 流畅动画
   - 60fps 淡入淡出动画（16ms 刷新率）
   - 淡入时间: 300ms
   - 淡出时间: 300ms
   - 停留时间: 可自定义（默认 3000ms）

3. 自动定位
   - 固定在窗口右上角
   - 自动边界检测，不会超出屏幕
   - 窗口移动/调整大小时自动更新位置

4. 资源管理
   - 自动清理定时器资源
   - 关闭时正确释放内存
   - 支持手动提前关闭

5. 响应式设计
   - 自适应文本大小
   - 圆角边框设计
   - 半透明背景效果
"""


# ==========================================
# 最佳实践
# ==========================================

"""
使用 Toast 的最佳实践：

1. 选择合适的类型
   - 成功操作用 success
   - 一般操作用 info
   - 需要注意用 warning
   - 错误情况用 error

2. 合理设置时长
   - 简短提示: 2000-3000ms
   - 重要信息: 4000-5000ms
   - 错误详情: 5000-8000ms

3. 避免过度使用
   - 不要在循环中频繁显示 Toast
   - 关键操作才使用 Toast 反馈
   - 考虑合并多个相关提示

4. 文案简洁明了
   - 控制在 20-30 个字符以内
   - 使用清晰的操作结果描述
   - 避免技术术语，使用用户友好语言

5. 配合其他 UI 元素
   - Toast 作为辅助反馈
   - 重要状态变化应同步更新 UI
   - 不要完全依赖 Toast 传达关键信息
"""
