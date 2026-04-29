# 画布直接启动/停止节点功能

## 📋 功能概述

BNOS平台现已支持**从画布直接启动和停止节点**，无需切换到节点列表面板，大幅提升工作效率。

## ✨ 核心特性

### 1. **智能优先级选择**
- **优先检查画布**：首先从画布获取当前选中的节点
- **回退到列表**：如果画布未选中，则从节点列表获取
- **明确提示**：两者都未选中时，提示用户先选择节点

### 2. **清晰的视觉反馈**
- 选中节点显示**蓝色边框高亮**（3px宽）
- 点击空白区域自动清除选择
- 切换选中时自动清除前一个节点的高亮

### 3. **流畅的工作流程**
```
传统方式：
打开节点列表 → 选择节点 → 点击启动按钮

优化后：
画布点击节点 → 点击启动按钮 ✅
```

## 🎯 使用方法

### 方法一：画布直接操作（推荐）
1. 在画布上**点击节点**（节点会显示蓝色边框）
2. 点击工具栏的 **"▶️ 启动节点"** 或 **"⏹️ 停止节点"** 按钮
3. Toast通知显示操作结果

### 方法二：节点列表操作（兼容）
1. 打开节点列表面板（工具栏"📋 节点列表"按钮）
2. 在列表中右键选择节点
3. 使用工具栏按钮启动/停止

### 混合使用
- 可以同时在画布和节点列表中选择不同节点
- **画布选中始终优先**
- 适合快速切换不同节点进行操作

## 🔧 技术实现

### 1. **画布选中状态跟踪** (ui/canvas_widget.py)

```python
class NodeCanvas(QGraphicsView):
    def __init__(self):
        self.selected_node = None  # 当前选中的节点名称
    
    def on_node_selected(self, node):
        """节点被选中时的回调"""
        # 清除之前选中节点的边框
        if self.selected_node and self.selected_node in self.node_items:
            old_item = self.node_items[self.selected_node]
            old_item.set_border_color(old_item.default_border_color)
        
        # 设置新选中节点的蓝色边框
        node.set_border_color(QColor("#0066FF"))
        node.set_border_width(3)
        self.selected_node = node.name
    
    def get_selected_node(self):
        """获取当前选中的节点名称"""
        return self.selected_node
    
    def clear_selection(self):
        """清除节点选择"""
        if self.selected_node and self.selected_node in self.node_items:
            item = self.node_items[self.selected_node]
            item.set_border_color(item.default_border_color)
            item.set_border_width(2)
        self.selected_node = None
    
    def mousePressEvent(self, event):
        """点击空白区域时清除选择"""
        super().mousePressEvent(event)
        if not self.itemAt(event.pos()):
            self.clear_selection()
```

### 2. **主窗口优先级逻辑** (ui/main_window.py)

```python
def start_selected_node(self):
    """启动选中的节点（优先从画布获取，回退到节点列表）"""
    # 优先从画布获取选中节点
    selected_node = self.canvas.get_selected_node()
    
    # 如果画布未选中，回退到节点列表
    if not selected_node:
        selected_node = self.node_list_panel.get_selected_node()
    
    if not selected_node:
        self.show_toast("请先在画布或节点列表中选择一个节点", "warning")
        return
    
    # ... 执行启动逻辑
```

```python
def stop_selected_node(self):
    """停止选中的节点（优先从画布获取，回退到节点列表）"""
    # 采用相同的优先级逻辑
    selected_node = self.canvas.get_selected_node()
    if not selected_node:
        selected_node = self.node_list_panel.get_selected_node()
    
    if not selected_node:
        self.show_toast("请先在画布或节点列表中选择一个节点", "warning")
        return
    
    # ... 执行停止逻辑
```

## 📊 工作流程图

```
用户点击工具栏"启动节点"按钮
         ↓
检查 canvas.get_selected_node()
         ↓
    有选中？
    ↙     ↘
  是       否
   ↓        ↓
使用该节点  检查 node_list_panel.get_selected_node()
              ↓
          有选中？
          ↙     ↘
        是       否
         ↓        ↓
    使用该节点  显示Toast提示
                  ↓
             "请先选择节点"
```

## 💡 应用场景

### ✅ 适合使用画布选择的场景
- **可视化编排**：在画布上查看节点连接关系时直接操作
- **快速测试**：频繁启动/停止单个节点进行测试
- **调试流程**：沿着数据流依次启动各个节点
- **演示展示**：向他人展示时直接在画布上操作更直观

### ✅ 适合使用节点列表的场景
- **批量管理**：需要同时查看多个节点状态
- **远程节点**：节点不在当前可视区域内
- **精确查找**：通过搜索快速定位特定节点

## 🎨 视觉效果

```
┌─────────────────────────────┐
│                             │
│   ┌──────────┐              │
│   │  Node 1  │ ← 默认状态   │
│   └──────────┘              │
│                             │
│   ┏━━━━━━━━━━┓              │
│   ┃  Node 2  ┃ ← 选中状态   │
│   ┃ (蓝色边框)┃   (3px宽)   │
│   ┗━━━━━━━━━━┛              │
│                             │
│   ┌──────────┐              │
│   │  Node 3  │ ← 默认状态   │
│   └──────────┘              │
│                             │
└─────────────────────────────┘

工具栏: [▶️ 启动节点] [⏹️ 停止节点]
         ↑ 点击这里启动选中的Node 2
```

## 🔍 关键代码位置

- **画布选中管理**: `ui/canvas_widget.py` 第850-900行
  - `on_node_selected()` - 节点选中回调
  - `get_selected_node()` - 获取选中节点
  - `clear_selection()` - 清除选择
  - `mousePressEvent()` - 点击空白清除

- **优先级逻辑**: `ui/main_window.py` 
  - `start_selected_node()` - 第887-950行
  - `stop_selected_node()` - 第1020-1080行

## ⚠️ 注意事项

1. **状态同步**：画布和节点列表的状态始终保持同步
2. **视觉反馈**：选中节点有明显的蓝色边框，避免误操作
3. **兼容性**：完全向后兼容，不影响现有的节点列表操作
4. **多源输入**：遵循"主要交互区域优先"的设计原则

## 📝 更新日志

**v2.1 - 2026-04-29**
- ✅ 实现画布直接选中节点功能
- ✅ 添加智能优先级选择逻辑
- ✅ 优化视觉反馈（蓝色边框高亮）
- ✅ 保持与节点列表的兼容性

---

**相关文档**：
- [TOAST_STACKING_FEATURE.md](TOAST_STACKING_FEATURE.md) - Toast堆叠显示功能
- [TOAST_QUICK_GUIDE.md](TOAST_QUICK_GUIDE.md) - Toast快速使用指南
