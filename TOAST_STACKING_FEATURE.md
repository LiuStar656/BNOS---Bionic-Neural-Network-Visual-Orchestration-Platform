# Toast通知堆叠显示功能

## 📋 功能概述

BNOS平台现在支持Toast通知的**智能堆叠显示**，当多个通知同时出现时，它们会自动排列并管理显示数量。

## ✨ 核心特性

### 1. **自动堆叠布局**
- 新Toast出现在右下角底部位置
- 旧Toast自动向上移动，为新的让出空间
- 每个Toast之间保持10px间距

### 2. **最大数量限制**
- 最多同时显示 **3个** Toast通知
- 超过3个时，最旧的Toast自动淡出消失
- 确保界面不会过于拥挤

### 3. **流畅动画效果**
- 60fps高精度定时器驱动
- 平滑的位置调整和透明度变化
- 300ms淡入淡出过渡

## 🎯 使用示例

```python
# 基本用法 - 与之前相同
self.show_toast("操作成功！", "success")

# 连续显示多个Toast（自动堆叠）
self.show_toast("第1条通知", "info")      # 底部
self.show_toast("第2条通知", "success")   # 中间（第1条上移）
self.show_toast("第3条通知", "warning")   # 顶部（前2条继续上移）
self.show_toast("第4条通知", "error")     # 底部（第1条淡出，2、3上移）
```

## 🔧 技术实现

### 1. **ToastNotification类增强**

```python
class ToastNotification(QLabel):
    def __init__(self, message, parent=None, duration=3000, 
                 toast_type="info", stack_index=0):
        # stack_index: 堆叠索引（0=最底部，越大越靠上）
        self.stack_index = stack_index
        
    def update_position(self):
        """根据stack_index动态计算Y坐标"""
        base_y = parent_rect.bottom() - self.height() - 20
        y = base_y - (self.stack_index * (self.height() + 10))
        self.move(x, y)
```

### 2. **BNOSMainWindow队列管理**

```python
class BNOSMainWindow(QMainWindow):
    def __init__(self):
        self.active_toasts = []       # 当前显示的Toast列表
        self.max_toast_count = 3      # 最多显示3个
    
    def show_toast(self, message, toast_type="info", duration=3000):
        # 1. 如果已有3个，移除最旧的
        if len(self.active_toasts) >= self.max_toast_count:
            oldest_toast = self.active_toasts.pop(0)
            oldest_toast.start_fade_out()
        
        # 2. 创建新Toast，设置堆叠索引
        stack_index = len(self.active_toasts)
        toast = ToastNotification(..., stack_index=stack_index)
        self.active_toasts.append(toast)
        
        # 3. 更新所有现有Toast的位置（向上移动）
        for i, existing_toast in enumerate(self.active_toasts[:-1]):
            existing_toast.stack_index = i + 1
            existing_toast.update_position()
        
        # 4. Toast关闭时自动清理和重新排列
        toast.close = custom_close_handler
```

## 📊 工作流程图

```
用户调用 show_toast("新消息")
         ↓
检查 active_toasts 数量
         ↓
    ≥ 3个？
    ↙     ↘
  是       否
   ↓        ↓
移除最旧   继续
(淡出)      ↓
         ↓
创建新Toast (stack_index = 当前数量)
         ↓
添加到 active_toasts
         ↓
更新所有Toast位置
(旧的上移，新的在底部)
         ↓
显示Toast并开始动画
```

## 🧪 测试方法

运行测试脚本查看完整效果：

```bash
python test_toast_stacking.py
```

测试脚本会：
1. 连续显示6个Toast通知
2. 观察自动堆叠和淡出效果
3. 验证最多显示3个的限制

## 💡 应用场景

### ✅ 适合使用堆叠Toast的场景
- 批量操作反馈（如：批量启动节点）
- 连续状态更新（如：多个节点依次启动成功）
- 实时日志输出（如：系统事件流）

### ❌ 不适合的场景
- 需要用户确认的操作 → 使用 `QMessageBox.question`
- 严重错误需要立即处理 → 使用 `QMessageBox.critical`
- 重要信息需要长时间保留 → 增加duration参数或使用其他UI元素

## 🎨 视觉效果

```
┌─────────────────────────┐
│                         │
│                         │
│                         │
│                         │
│  ┌──────────────┐       │
│  │ ⚠️ 警告消息  │ ← 第3个（最旧，即将淡出）
│  └──────────────┘       │
│  ┌──────────────┐       │
│  │ ✨ 成功消息  │ ← 第2个
│  └──────────────┘       │
│  ┌──────────────┐       │
│  │ 🔔 信息消息  │ ← 第1个（最新）
│  └──────────────┘       │
│                         │
└─────────────────────────┘
```

## 🔍 关键代码位置

- **Toast通知类**: `ui/main_window.py` 第24-158行
- **队列管理**: `ui/main_window.py` 第323-370行
- **测试脚本**: `test_toast_stacking.py`

## 📝 注意事项

1. **内存管理**: Toast关闭后会自动从列表中移除，避免内存泄漏
2. **线程安全**: 所有操作都在主线程中执行，无需额外同步
3. **性能优化**: 使用PreciseTimer确保60fps流畅动画
4. **兼容性**: 完全向后兼容，不影响现有的单Toast使用场景

---

**更新时间**: 2026-04-29  
**版本**: v2.0 - 支持智能堆叠显示
