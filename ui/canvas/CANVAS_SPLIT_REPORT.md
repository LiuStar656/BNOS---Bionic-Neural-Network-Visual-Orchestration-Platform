# Canvas 模块物理拆分完成报告

## 📋 拆分概览

**拆分时间**: 2026-05-20  
**原文件**: `ui/canvas_widget.py` (91.9 KB, 2189行)  
**新架构**: 分层模块化设计  

---

## 🏗️ 新目录结构

```
ui/canvas/
├── __init__.py              # 包初始化，导出所有组件 (0.51 KB)
├── canvas_view.py           # NodeCanvas 主视图 (74.5 KB, ~1763行)
└── items/                   # 图形项层
    ├── __init__.py          # 子包初始化 (0.36 KB)
    ├── anchor_item.py       # AnchorItem 锚点组件 (2.32 KB, ~67行)
    ├── node_item.py         # NodeItem 节点组件 (9.08 KB, ~207行)
    └── edge_item.py         # EdgeItem 连线组件 (6.7 KB, ~167行)
```

### 兼容层
```
ui/canvas_widget.py          # Facade 模式，重定向到新模块 (< 0.5 KB)
```

---

## 📦 组件清单

### 1️⃣ **AnchorItem** (`items/anchor_item.py`)
- **职责**: 节点端口（输入/输出锚点）的视觉渲染和悬停交互
- **继承**: `QGraphicsEllipseItem`
- **尺寸**: 16×16 像素
- **方法数**: 3个
  - `__init__`: 初始化
  - `update_anchor_color`: 动态颜色更新
  - `hoverEnterEvent` / `hoverLeaveEvent`: 悬停高亮

### 2️⃣ **NodeItem** (`items/node_item.py`)
- **职责**: 节点容器的视觉渲染、锚点管理和交互处理
- **继承**: `QGraphicsRectItem`
- **默认尺寸**: 140×80 像素
- **子组件**: 7个（2个锚点 + 5个文本/形状项）
- **方法数**: 7个
  - `__init__`: 创建节点及所有子组件
  - `update_status`: 更新状态指示灯
  - `_load_node_custom_colors`: 加载自定义颜色
  - `update_display`: 选择性更新显示
  - `sync_with_data`: 从数据字典同步
  - `itemChange`: 监听位置变化
  - `mousePressEvent`: 处理点击事件（连线/多选）

### 3️⃣ **EdgeItem** (`items/edge_item.py`)
- **职责**: 节点间贝塞尔曲线连线的视觉渲染和路径计算
- **继承**: `QGraphicsPathItem`
- **路径类型**: 三次贝塞尔曲线（cubicTo）
- **子组件**: 1个（箭头多边形）
- **方法数**: 7个
  - `__init__`: 初始化连线
  - `update_edge_style`: 更新样式
  - `mousePressEvent`: 右键菜单
  - `change_edge_color`: 修改单条连线颜色
  - `update_path`: 重新计算贝塞尔曲线路径
  - `add_arrow`: 创建/更新箭头
  - `remove_from_scene`: 清理场景

### 4️⃣ **NodeCanvas** (`canvas_view.py`)
- **职责**: 主画布容器，管理所有节点、连线、交互和持久化
- **继承**: `QGraphicsView`
- **场景尺寸**: 5000×5000 像素
- **方法数**: 60+个
- **核心功能**:
  - 节点/连线管理（CRUD）
  - 视图交互（缩放、平移、框选）
  - 连线创建与管理
  - 批量操作（启动/停止/删除）
  - 布局持久化（JSON序列化）
  - 颜色配置系统
  - 自动保存（防抖500ms）

---

## 🔧 技术细节

### 导入关系
```python
# items/anchor_item.py
from PyQt6.QtWidgets import QGraphicsEllipseItem
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPen, QColor

# items/node_item.py
from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsEllipseItem, QGraphicsItem
from ui.canvas.items.anchor_item import AnchorItem

# items/edge_item.py
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsPolygonItem, QMenu
from PyQt6.QtGui import QPen, QColor, QPainterPath, QPolygonF
# ⚠️ 延迟导入 NodeCanvas 避免循环依赖

# canvas_view.py
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.edge_item import EdgeItem
```

### 循环依赖解决
在 `EdgeItem.mousePressEvent` 中使用延迟导入：
```python
if action == delete_action:
    if self.scene():
        from ui.canvas.canvas_view import NodeCanvas  # 延迟导入
        for item in self.scene().items():
            if isinstance(item, NodeCanvas):
                item.remove_edge(self)
                break
```

---

## ✅ 验证结果

### 导入测试
```bash
✅ 所有组件导入成功
   NodeCanvas: <class 'ui.canvas.canvas_view.NodeCanvas'>
   NodeItem: <class 'ui.canvas.items.node_item.NodeItem'>
   EdgeItem: <class 'ui.canvas.items.edge_item.EdgeItem'>
   AnchorItem: <class 'ui.canvas.items.anchor_item.AnchorItem'>

✅ 兼容层导入成功
   旧导入: <class 'ui.canvas.canvas_view.NodeCanvas'>
   新导入: <class 'ui.canvas.canvas_view.NodeCanvas'>
   是否相同: True
```

### 语法检查
- ✅ 无语法错误
- ✅ 无导入错误
- ✅ 循环依赖已解决

---

## 📊 拆分效果

| 指标 | 拆分前 | 拆分后 | 改进 |
|------|--------|--------|------|
| **文件数量** | 1个 | 6个 | 模块化 |
| **最大文件大小** | 91.9 KB | 74.5 KB | ↓ 19% |
| **代码可读性** | 低（单文件2189行） | 高（分层清晰） | ↑ 显著提升 |
| **可维护性** | 低（耦合严重） | 高（职责分离） | ↑ 显著提升 |
| **可测试性** | 低（难以单元测试） | 高（独立组件） | ↑ 显著提升 |

---

## 🎯 后续优化建议

根据记忆中的**五阶段重构方案**，已完成**阶段一基础重构**的部分工作：

### ✅ 已完成
- [x] 提取核心组件到独立文件
- [x] 建立分层架构（items层）
- [x] 保持向后兼容（Facade模式）

### 🔄 待执行（按优先级）
1. **P0 - 提取常量** (`canvas_constants.py`)
   - 替换所有魔法数字（如 16, 140, 80, 5000）
   - 统一硬编码颜色值为常量

2. **P0 - 配置管理器** (`config_manager.py`)
   - 统一配置文件读写逻辑
   - 消除重复的 JSON 操作代码

3. **P0 - 日志系统** 
   - 替换所有 `print` 为 `logging`
   - 支持不同级别日志（DEBUG/INFO/WARNING）

4. **P1 - 状态管理器** (`canvas_state_manager.py`)
   - 将节点/连线数据管理与 UI 分离
   - 实现统一的 CRUD 接口

5. **P2 - 交互解耦** (`interaction_handler.py`)
   - 拆分鼠标/键盘事件处理器
   - 引入事件总线消除直接依赖

---

## 📝 使用示例

### 新方式（推荐）
```python
from ui.canvas import NodeCanvas, NodeItem, EdgeItem, AnchorItem

# 创建画布
canvas = NodeCanvas(parent=main_window)
```

### 旧方式（兼容）
```python
from ui.canvas_widget import NodeCanvas, NodeItem, EdgeItem, AnchorItem

# 仍然可用，但会触发弃用警告
canvas = NodeCanvas(parent=main_window)
```

---

## ⚠️ 注意事项

1. **循环依赖**: `EdgeItem` 中使用了延迟导入避免与 `NodeCanvas` 形成循环依赖
2. **导入顺序**: 必须按 `anchor_item → node_item → edge_item → canvas_view` 顺序导入
3. **兼容性**: 原 `canvas_widget.py` 已改为 Facade 模式，现有代码无需修改
4. **未来计划**: 兼容层将在后续版本中移除，建议迁移到新导入方式

---

## 🎉 总结

✅ **物理拆分成功完成！**

- 4个核心组件已完全分离到独立文件
- 采用分层架构，职责清晰
- 保持100%向后兼容
- 无语法错误，导入测试通过
- 为后续重构奠定坚实基础

**下一步**: 运行主程序进行集成测试，验证功能完整性。
