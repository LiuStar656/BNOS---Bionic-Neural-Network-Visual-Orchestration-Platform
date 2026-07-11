# BNOS UI 组件模块化说明

## 📦 Toast 通知系统

### 文件结构

```
ui/
├── toast_notification.py    # Toast 通知组件（独立模块）
├── toast_examples.py        # 使用示例和最佳实践
├── main_window.py           # 主窗口（保留原始 Toast 代码）
└── __init__.py              # 包初始化（导出 ToastNotification）
```

### 核心组件

#### `ToastNotification` 类

**位置**: `ui/toast_notification.py`

**功能特性**:
- ✅ 60fps 流畅淡入淡出动画
- ✅ 支持堆叠显示（无数量上限）
- ✅ 自动位置调整
- ✅ 4 种通知类型（info/success/warning/error）
- ✅ 自定义显示时长
- ✅ 智能边界检测
- ✅ 资源自动清理

**基本用法**:

```python
from ui.toast_notification import ToastNotification

# 创建并显示 Toast
toast = ToastNotification(
    message="操作成功！",
    parent=self,
    duration=3000,
    toast_type="success"
)
toast.show_toast()
```

### 通知类型

| 类型 | 颜色 | 用途 |
|------|------|------|
| `info` | 深灰色 | 一般信息提示 |
| `success` | 绿色 | 操作成功提示 |
| `warning` | 橙色 | 警告或注意事项 |
| `error` | 红色 | 错误或失败提示 |

### 高级用法

#### 1. 堆叠管理

```python
class MainWindow:
    def __init__(self):
        self.active_toasts = []  # 管理当前显示的 Toast 列表
    
    def show_toast(self, message, toast_type="info", duration=3000):
        # 更新现有 Toast 位置
        for i, existing_toast in enumerate(self.active_toasts):
            existing_toast.stack_index = i + 1
            existing_toast.update_position()
        
        # 创建新 Toast
        toast = ToastNotification(
            message=message,
            parent=self,
            duration=duration,
            toast_type=toast_type,
            stack_index=0
        )
        
        self.active_toasts.insert(0, toast)
        toast.show_toast()
        
        # 设置关闭回调
        original_close = toast.close
        def custom_close():
            if toast in self.active_toasts:
                self.active_toasts.remove(toast)
                for i, remaining_toast in enumerate(self.active_toasts):
                    remaining_toast.stack_index = i
                    remaining_toast.update_position()
            original_close()
        
        toast.close = custom_close
```

#### 2. 在不同场景中使用

```python
# 节点操作反馈
main_window.show_toast(f"节点 {node_name} 已启动", "success")

# 项目操作反馈
main_window.show_toast(f"已打开项目: {project_name}", "success")

# 异步任务进度
main_window.show_toast("开始执行任务...", "info", duration=2000)
```

### 技术细节

#### 动画机制
- **刷新率**: 60fps (16ms 间隔)
- **淡入时间**: 300ms
- **淡出时间**: 300ms
- **停留时间**: 可自定义（默认 3000ms）
- **定时器类型**: `Qt.TimerType.PreciseTimer`（高精度）

#### 定位策略
- **基准位置**: 窗口右上角
- **水平偏移**: 距离右边缘 20px
- **垂直偏移**: 距离顶部 100px（留出工具栏空间）
- **堆叠间距**: 每个 Toast 间隔 60px
- **边界检测**: 自动限制在屏幕范围内

#### 样式设计
- **背景**: 半透明圆角矩形
- **字体**: 14px 粗体
- **内边距**: 12px 上下，20px 左右
- **圆角**: 8px
- **透明度**: 230/255

### 模块化优势

1. **独立维护**: Toast 逻辑与主窗口解耦
2. **易于测试**: 可以单独测试 Toast 功能
3. **代码复用**: 其他模块可直接导入使用
4. **清晰职责**: 单一职责原则
5. **向后兼容**: 保留 main_window.py 中的原始代码

### 迁移指南

如果要将其他模块的 Toast 代码迁移到独立模块：

1. **导入新模块**:
   ```python
   from ui.toast_notification import ToastNotification
   ```

2. **替换创建逻辑**:
   ```python
   # 旧代码
   toast = QLabel(message, parent)
   # ... 手动设置样式和属性
   
   # 新代码
   toast = ToastNotification(message, parent, duration, toast_type)
   ```

3. **删除重复代码**:
   - 移除 main_window.py 中的 ToastNotification 类定义
   - 保留 show_toast() 等业务方法

### 注意事项

⚠️ **重要提示**:

1. **parent 参数**: 必须传入有效的 QWidget 父对象，否则无法正确定位
2. **线程安全**: Toast 必须在主线程中创建和显示
3. **资源清理**: 确保在窗口关闭时清理 active_toasts 列表
4. **性能考虑**: 避免在短时间内创建大量 Toast（建议最多同时显示 5-10 个）

### 未来扩展

可能的改进方向：

- [ ] 添加点击事件处理
- [ ] 支持自定义图标
- [ ] 添加进度条样式
- [ ] 支持多行文本
- [ ] 添加音效提示
- [ ] 支持 Toast 队列优先级

---

**最后更新**: 2026-05-20  
**维护者**: BNOS 开发团队
