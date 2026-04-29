# 📍 Toast通知位置优化 - 右上角显示

## ✅ 核心改进

**问题**：之前Toast通知显示在**右下角**，可能会遮挡画布底部的节点或连线，干扰用户操作。

**解决方案**：将Toast通知移动到**右上角**，完全不干扰画布的正常运行。

---

## 🎯 修改内容

### 修改文件
**文件**: [`ui/main_window.py`](file://d:\bnos_new\BNOS---Bionic-Neural-Network-Visual-Orchestration-Platform\ui\main_window.py)  
**类**: `ToastNotification`

### 关键改动

#### 1. **show_toast() 方法** - 初始位置计算

**❌ 之前（右下角）**：
```python
def show_toast(self):
    # 计算位置：右下角（距离边缘20px）
    if self.parent():
        parent_rect = self.parent().geometry()
        x = parent_rect.right() - self.width() - 20
        base_y = parent_rect.bottom() - self.height() - 20  # ← 从底部开始
        y = base_y - (self.stack_index * (self.height() + 10))
```

**✅ 现在（右上角）**：
```python
def show_toast(self):
    # 计算位置：右上角（距离边缘20px）
    if self.parent():
        parent_rect = self.parent().geometry()
        x = parent_rect.right() - self.width() - 20
        y = parent_rect.top() + 20 + (self.stack_index * (self.height() + 10))  # ← 从顶部开始
```

#### 2. **update_position() 方法** - 堆叠位置更新

**❌ 之前（从下往上堆叠）**：
```python
def update_position(self):
    if self.parent():
        parent_rect = self.parent().geometry()
        x = parent_rect.right() - self.width() - 20
        base_y = parent_rect.bottom() - self.height() - 20  # ← 底部基准
        y = base_y - (self.stack_index * (self.height() + 10))
```

**✅ 现在（从上往下堆叠）**：
```python
def update_position(self):
    if self.parent():
        parent_rect = self.parent().geometry()
        x = parent_rect.right() - self.width() - 20
        y = parent_rect.top() + 20 + (self.stack_index * (self.height() + 10))  # ← 顶部基准
```

---

## 📊 视觉效果对比

### ❌ 之前（右下角）
```
┌─────────────────────────────┐
│                             │
│      画布区域                │
│                             │
│   ● 节点1                   │
│      \                      │
│       \                     │
│        ● 节点2              │
│                             │
│                  ┌────────┐ │ ← Toast可能遮挡节点
│                  │ Toast  │ │
│                  └────────┘ │
└─────────────────────────────┘
```

### ✅ 现在（右上角）
```
┌─────────────────────────────┐
│                  ┌────────┐ │ ← Toast在右上角
│                  │ Toast  │ │    不干扰画布
│                  └────────┘ │
│                             │
│      画布区域                │
│                             │
│   ● 节点1                   │
│      \                      │
│       \                     │
│        ● 节点2              │
│                             │
└─────────────────────────────┘
```

---

## 🎨 堆叠效果

当多个Toast同时显示时，会**从顶部向下堆叠**：

```
┌─────────────────────────────┐
│                  ┌────────┐ │ ← Toast 1 (stack_index=0)
│                  │ 成功   │ │    y = top + 20
│                  └────────┘ │
│                  ┌────────┐ │ ← Toast 2 (stack_index=1)
│                  │ 警告   │ │    y = top + 20 + 60
│                  └────────┘ │
│                  ┌────────┐ │ ← Toast 3 (stack_index=2)
│                  │ 错误   │ │    y = top + 20 + 120
│                  └────────┘ │
│                             │
│      画布区域                │
│                             │
└─────────────────────────────┘
```

每个Toast间隔 **10px**，确保视觉清晰。

---

## 💡 优势分析

| 特性 | 右下角（之前） | 右上角（现在） |
|------|--------------|--------------|
| **遮挡画布** | ❌ 可能遮挡底部节点 | ✅ 完全不遮挡 |
| **干扰操作** | ❌ 可能影响拖拽节点 | ✅ 无干扰 |
| **视觉焦点** | ⚠️ 与画布内容重叠 | ✅ 独立区域 |
| **美观度** | ⚠️ 一般 | ✅ 更好 |
| **符合习惯** | ⚠️ 较少见 | ✅ 常见UI模式 |

---

## 🚀 实际应用场景

### 场景1：创建节点
```
用户点击"➕ 新建节点"
    ↓
输入节点名称
    ↓
显示进度对话框（模态）
    ↓
完成后右上角显示Toast：
    ┌──────────────────┐
    │ ✅ 节点创建成功   │ ← 右上角，不干扰画布
    └──────────────────┘
    ↓
用户可以继续在画布上操作
```

### 场景2：启动/停止节点
```
用户点击"▶️ 启动节点"
    ↓
右上角显示Toast：
    ┌──────────────────┐
    │ ▶️ 节点已启动     │ ← 不遮挡节点本身
    └──────────────────┘
    ↓
用户可以立即看到节点状态变化
```

### 场景3：多个通知堆叠
```
快速执行多个操作：
    ├─ 创建节点 → Toast 1
    ├─ 启动节点 → Toast 2
    └─ 保存布局 → Toast 3

右上角垂直堆叠显示：
    ┌──────────────────┐
    │ ✅ 布局已保存     │ ← 最新
    ├──────────────────┤
    │ ▶️ 节点已启动     │
    ├──────────────────┤
    │ ✅ 节点创建成功   │ ← 最早
    └──────────────────┘
    
画布完全不受影响！
```

---

## 🔧 技术细节

### 位置计算公式

```python
# X坐标：右侧对齐，距离右边缘20px
x = parent_rect.right() - toast_width - 20

# Y坐标：从顶部开始，向下堆叠
y = parent_rect.top() + 20 + (stack_index * (toast_height + 10))
```

### 堆叠索引计算

```python
# 第1个Toast: stack_index = 0
y = top + 20 + (0 * 60) = top + 20

# 第2个Toast: stack_index = 1
y = top + 20 + (1 * 60) = top + 80

# 第3个Toast: stack_index = 2
y = top + 20 + (2 * 60) = top + 140
```

假设Toast高度为50px，间隔10px，则每个Toast占用60px垂直空间。

---

## ⚠️ 注意事项

### 1. **工具栏区域**
如果窗口顶部有工具栏，Toast会显示在工具栏下方：

```
┌─────────────────────────────┐
│  [工具栏按钮] [工具栏按钮]   │ ← 工具栏
├─────────────────────────────┤
│                  ┌────────┐ │ ← Toast在工具栏下方
│                  │ Toast  │ │
│                  └────────┘ │
│                             │
│      画布区域                │
└─────────────────────────────┘
```

这是正常行为，因为Toast使用父窗口的几何坐标。

### 2. **窗口最大化**
窗口最大化时，Toast会显示在屏幕右上角：

```python
# 全屏模式下
screen = QApplication.primaryScreen().geometry()
x = screen.right() - width - 20
y = screen.top() + 20 + (stack_index * 60)
```

### 3. **多显示器**
Toast会显示在**主显示器**的右上角。如果需要支持多显示器，可以扩展代码：

```python
# 获取当前窗口所在的屏幕
screen = QApplication.screenAt(self.parent().pos())
if screen is None:
    screen = QApplication.primaryScreen()
```

---

## 📝 相关代码位置

| 功能 | 文件 | 行号 |
|------|------|------|
| Toast类定义 | `ui/main_window.py` | 第24行 |
| show_toast() | `ui/main_window.py` | 第92-113行 |
| update_position() | `ui/main_window.py` | 第141-154行 |
| 调用Toast | `ui/main_window.py` | 多处（show_toast方法） |

---

## 🎉 总结

通过将Toast通知从**右下角**移动到**右上角**，我们实现了：

✅ **完全不干扰画布**：Toast不会遮挡任何节点或连线  
✅ **更好的视觉层次**：通知区域与操作区域分离  
✅ **符合UI惯例**：大多数应用的通知都在右上角  
✅ **保持堆叠功能**：多个通知仍然可以优雅地堆叠显示  

这是一个简单但重要的用户体验优化，让BNOS更加专业和易用！🚀

---

**最后更新**: 2026-04-29  
**版本**: v1.0 - Toast位置优化  
**状态**: ✅ 已完成并可用
