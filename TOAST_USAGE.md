# BNOS Toast通知使用指南

## 概述

ToastNotification是一个右下角自动消失的通知组件，用于提供非阻断性的用户反馈。

## 特性

- ✅ **流畅动画**：使用高精度定时器实现60fps淡入淡出效果
- ✅ **四种类型**：info（灰色）、success（绿色）、warning（橙色）、error（红色）
- ✅ **自动定位**：固定在窗口右下角，距离边缘20px
- ✅ **自动消失**：默认3秒后自动淡出关闭
- ✅ **半透明背景**：圆角设计，现代美观

## 使用方法

### 基本用法

```python
from ui.main_window import ToastNotification

# 在主窗口中显示Toast
toast = ToastNotification(
    message="操作成功！",
    parent=self,  # 主窗口实例
    duration=3000,  # 显示时长（毫秒）
    toast_type="success"  # 类型：info/success/warning/error
)
toast.show_toast()
```

### 不同类型示例

```python
# 信息提示
ToastNotification("这是一条普通信息", self, 2000, "info").show_toast()

# 成功提示
ToastNotification("节点创建成功！", self, 3000, "success").show_toast()

# 警告提示
ToastNotification("注意：此操作不可逆", self, 4000, "warning").show_toast()

# 错误提示
ToastNotification("连接失败，请检查网络", self, 5000, "error").show_toast()
```

### 在BNOSMainWindow中使用

```python
class BNOSMainWindow(QMainWindow):
    def some_action(self):
        # 执行某个操作...
        
        # 显示成功提示
        self.show_toast("节点已启动", "success")
    
    def show_toast(self, message, toast_type="info", duration=3000):
        """便捷方法：显示Toast通知"""
        toast = ToastNotification(
            message=message,
            parent=self,
            duration=duration,
            toast_type=toast_type
        )
        toast.show_toast()
```

## 参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| message | str | - | 通知文本内容 |
| parent | QWidget | None | 父窗口，用于定位 |
| duration | int | 3000 | 停留时长（毫秒） |
| toast_type | str | "info" | 类型：info/success/warning/error |

## 技术实现

- **动画引擎**：QTimer + PreciseTimer（16ms间隔，60fps）
- **透明度控制**：QGraphicsOpacityEffect手动插值
- **状态管理**：is_fading_in / is_fading_out / current_opacity
- **生命周期**：淡入(300ms) → 停留(duration) → 淡出(300ms) → 自动关闭

## 最佳实践

1. **选择合适的时长**：
   - 简短信息：2000ms
   - 一般提示：3000ms
   - 重要警告：4000-5000ms

2. **区分通知与确认**：
   - ✅ 使用Toast：操作成功、状态变更、一般提示
   - ❌ 不使用Toast：删除确认、覆盖警告、需要用户决策的操作

3. **避免频繁弹出**：
   - 短时间内不要连续显示多个Toast
   - 可以考虑合并多条信息为一条

## 测试

运行测试脚本验证效果：
```bash
python test_toast.py
```

然后点击不同按钮查看四种类型的Toast动画效果。
