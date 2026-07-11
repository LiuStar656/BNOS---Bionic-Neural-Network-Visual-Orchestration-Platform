# BNOS 画布标注工具迭代方案

> 定位：专注于**节点标注与分类**的画布辅助工具，不引入复杂图层管理，重点解决"画完即死"的二次编辑难题。

---

## 一、现状与核心痛点

### 1.1 现有能力

| 能力 | 状态 |
|------|------|
| 创建图形 | 矩形、圆角矩形、多边形、箭头、文本（5 种） |
| 变形编辑 | 控制点拖拽调整大小/形状 |
| 位置移动 | 拖拽整体移动 |
| 序列化 | `to_json()` / `from_json()` 已实现，但**未接入画布持久化** |
| 撤销 | 快照式全量 undo/redo |

### 1.2 核心痛点

1. **无法二次编辑属性**：创建后无法修改颜色、线宽、圆角、箭头样式等
2. **文本一次性**：文本创建后无法修改内容，只能删除重画
3. **无持久化**：画布刷新/项目重开后，所有标注图形丢失
4. **选择能力弱**：仅支持单选，无多选、无框选、无右键菜单
5. **缺少语义**：无法快速标记"错误/警告/成功"等分类语义

---

## 二、迭代目标

在**不引入图层系统**的前提下，实现：

- 已创建图形的**全属性二次编辑**
- 标注图形的**持久化保存与恢复**
- **多选 + 框选 + 右键菜单**的完整工作流
- **分类预设样式**提升标注效率
- **精细化撤销重做**（属性级而非全量快照）

---

## 三、迭代阶段

### 阶段一：属性编辑与持久化（P0 — 核心刚需）

#### 3.1 属性面板（DrawPropertyPanel）

新建浮动面板 `ui/panels/draw_property_panel.py`：

- **触发方式**：选中任意图形时自动显示；无选中时隐藏或置灰
- **通用属性**（所有图形）：
  - 描边颜色：色块 + 取色器
  - 填充颜色：色块 + 取色器 + "无填充"按钮
  - 描边宽度：1-20px 滑块
  - 不透明度：0-100% 滑块
- **文本特有**：
  - 文字内容：多行输入框，实时同步
  - 字体大小：8-72px 滑块
  - 文字颜色：色块
  - 背景填充开关
- **矩形特有**：
  - 圆角半径：0-50px 滑块
- **箭头特有**：
  - 箭头大小：滑块
  - 箭头方向：单向 / 双向 / 无箭头
- **多边形特有**：
  - 闭合 / 开放 切换

**实时预览**：属性修改即时应用到选中图形，无需确认。

#### 3.2 文本二次编辑

- **双击文本图形**：激活 `QGraphicsTextItem` 的文本交互模式（`TextEditorInteraction`），直接在画布上编辑
- **回车确认**：失去焦点或按 `Enter` 退出编辑模式
- **取消**：按 `Esc` 回退到编辑前内容

#### 3.3 持久化接入

修改 `ui/canvas/mixins/canvas_layout.py`：

**保存时**：
```json
{
  "canvas": { ... },
  "nodes": { ... },
  "edges": { ... },
  "drawing": {
    "toolbar_visible": true,
    "graphics": [
      {"type": "rect", "points": [...], "style": {...}},
      {"type": "text", "text": "TODO", "x": 100, "y": 200, "style": {...}}
    ]
  }
}
```

**加载时**：
- 读取 `drawing.graphics`，调用 `DrawLayer.from_json()` 恢复
- 兼容旧文件：无 `drawing` 字段时静默跳过

**自动保存**：图形变更（创建、移动、属性修改）触发画布自动保存（现有 500ms 防抖）。

---

### 阶段二：选择与工作流（P1 — 效率提升）

#### 2.1 多选支持

- **Ctrl + 单击**：切换单个图形的选中状态（加选/减选）
- **框选**：在空白区域拖拽框选多个图形（蓝色半透明选框，与节点框选视觉区分）
- **全选**：`Ctrl+A` 选中所有图形
- **取消选择**：`Esc` 或 `Ctrl+D`

**多选时的属性面板**：
- 显示"多选（N 个）"提示
- 修改属性时**批量应用**到所有选中图形
- 若属性不一致，显示"—"占位，修改后统一覆盖

#### 2.2 右键菜单

右键点击图形时弹出上下文菜单：

| 菜单项 | 功能 |
|--------|------|
| 编辑文本 | 仅文本可用，进入编辑模式 |
| 复制 | `Ctrl+C`，复制选中图形 |
| 粘贴 | `Ctrl+V`，在鼠标位置粘贴副本（偏移 10px） |
| 删除 | `Delete`，移除选中 |
| 置顶 | 将图形移到列表末尾（视觉上置顶） |
| 置底 | 将图形移到列表开头（视觉上置底） |
| 锁定 | 锁定后不可选中/编辑/移动 |
| 预设样式 → | 子菜单：错误/警告/成功/信息/高亮/注释 |

#### 2.3 快捷键

| 快捷键 | 功能 |
|--------|------|
| Delete / Backspace | 删除选中图形 |
| Ctrl+C | 复制 |
| Ctrl+V | 粘贴 |
| Ctrl+D | 取消选择 |
| Ctrl+A | 全选图形 |
| 方向键 | 微调位置（1px），Shift+方向键（10px） |
| [ / ] | 降低/提高描边宽度 |
| Shift+[ / Shift+] | 降低/提高字体大小（仅文本） |

---

### 阶段三：标注分类专业化（P1 — 场景价值）

#### 3.1 预设样式系统

为节点标注场景预设 6 套样式，一键应用：

| 预设 | 描边 | 填充 | 文字颜色 | 适用场景 |
|------|------|------|----------|----------|
| 错误 | `#F44336` 2px | `rgba(244,67,54,0.15)` | `#F44336` | 标记异常节点 |
| 警告 | `#FF9800` 2px | `rgba(255,152,0,0.15)` | `#FF9800` | 标记警告节点 |
| 成功 | `#4CAF50` 2px | `rgba(76,175,80,0.15)` | `#4CAF50` | 标记正常节点 |
| 信息 | `#2196F3` 2px | `rgba(33,150,243,0.15)` | `#2196F3` | 普通注释 |
| 高亮 | 无描边 | `rgba(255,235,59,0.4)` | `#333` | 高亮重点区域 |
| 注释 | `#9E9E9E` 1px 虚线 | `rgba(158,158,158,0.1)` | `#CCC` | 待确认/备注 |

**应用方式**：
- 右键菜单 → 预设样式
- 属性面板顶部预设色块快捷栏
- 创建图形时默认使用上次预设

#### 3.2 分类标签徽章

每个图形可绑定一个分类标签：

- **显示**：标签文字显示在图形左上角（小圆角矩形徽章），如"异常"、"待优化"
- **颜色**：与预设样式联动，错误预设自动显示红色徽章
- **筛选**：图层面板（简化版列表）可按标签筛选

#### 3.3 对齐与分布

属性面板底部增加对齐按钮组（选中 2+ 图形时激活）：

- **对齐**：左对齐、水平居中、右对齐、顶对齐、垂直居中、底对齐
- **分布**：水平均分、垂直均分
- **参考**：以画布为参考 / 以选区包围盒为参考

**技术实现**：计算选中图形的 `sceneBoundingRect()`，统一调整 `setPos()`。

---

### 阶段四：撤销重做精细化（P2 — 体验 polish）

当前快照式 undo 在图形多时有性能问题和语义不清的问题。改为**命令级撤销**：

```python
class DrawCommand(Command):
    """绘图层操作基类"""
    pass

class AddGraphicCommand(DrawCommand): ...
class DeleteGraphicCommand(DrawCommand): ...
class MoveGraphicCommand(DrawCommand): ...
class StyleChangeCommand(DrawCommand):
    # 记录修改前后的完整 style dict
    ...
class ReorderCommand(DrawCommand): ...
```

**接入 HistoryManager**：
- 所有绘图层操作统一走 `HistoryManager.execute_command(cmd)`
- 与节点/连线的历史记录共存于同一列表
- 历史面板自动显示："创建矩形"、"修改文本内容"、"应用错误预设"、"移动标注" 等语义描述

---

## 四、界面调整

### 4.1 工具栏优化

在现有 `draw_toolbar.py` 基础上调整：

- 顶部增加**预设样式色块条**（6 个颜色小方块，点击直接设置当前预设）
- 底部增加**属性面板触发按钮**（点击展开/收起属性面板）
- 删除独立的描边/填充按钮（移至属性面板）

### 4.2 新增面板

| 面板 | 文件 | 说明 |
|------|------|------|
| 标注属性面板 | `ui/panels/draw_property_panel.py` | 选中图形的属性编辑 |
| 标注列表面板 | `ui/panels/draw_list_panel.py`（可选） | 简化列表，显示所有图形名称+标签，支持筛选和跳转 |

### 4.3 选中视觉反馈

- **单选**：虚线包围框（marching ants 动画）+ 控制点
- **多选**：统一的虚线包围框（包含所有选中图形）
- **Hover**：半透明浅色遮罩，提示可点击

---

## 五、技术实现要点

### 5.1 持久化兼容性

```python
# canvas_layout.py 保存时
layout_data["drawing"] = {
    "toolbar_visible": self.draw_layer._toolbar_visible,
    "graphics": self.draw_layer.to_json(),
}

# canvas_layout.py 加载时
drawing_data = layout_data.get("drawing", {})
if drawing_data:
    self.draw_layer.from_json(drawing_data.get("graphics", []))
    if drawing_data.get("toolbar_visible"):
        self.draw_layer.show_toolbar()
```

旧版 `canvas_layout.json` 无 `drawing` 字段，静默兼容。

### 5.2 属性面板与图形的双向绑定

```python
# DrawPropertyPanel 中
self.stroke_color_picker.color_changed.connect(
    lambda c: self._apply_to_selection(lambda g: g.set_style(stroke_color=c))
)

def _apply_to_selection(self, fn):
    for g in self.draw_layer.selected_graphics():
        fn(g)
    self.draw_layer.canvas._save_timer.start(500)
```

### 5.3 文本编辑模式切换

```python
# TextGraphic 中
def start_editing(self):
    self._text_item.setTextInteractionFlags(Qt.TextEditorInteraction)
    self._text_item.setFocus()

def finish_editing(self):
    self._text_item.setTextInteractionFlags(Qt.NoTextInteraction)
    self._text = self._text_item.toPlainText()
```

### 5.4 性能注意

- 属性面板使用 `QSlider` + `valueChanged` 时，用 `editingFinished` 或 100ms 防抖避免频繁重绘
- 多选批量修改时，先 `blockSignals(True)` 再统一 `update()`

---

## 六、实施排期

| 阶段 | 内容 | 工期 | 产出 |
|------|------|------|------|
| **阶段一** | 属性面板 + 文本二次编辑 + 持久化接入 | 2-3 天 | 图形可编辑、可保存恢复 |
| **阶段二** | 多选框选 + 右键菜单 + 快捷键 | 2 天 | 完整选择工作流 |
| **阶段三** | 预设样式 + 分类标签 + 对齐分布 | 2-3 天 | 标注效率质变 |
| **阶段四** | 命令级撤销 + 选中视觉优化 | 1-2 天 | 体验 polish |

**总计：7-10 天**

**MVP 版本（3-4 天可见效果）**：阶段一（属性面板 + 持久化）+ 阶段二的复制粘贴删除。

---

## 七、与 PS 方案的区别

| 维度 | PS 对标方案 | 本方案 |
|------|------------|--------|
| 图层系统 | 完整 Layer 树 + Group + BlendMode | 扁平列表，无图层概念 |
| 画笔/像素 | 完整 BrushEngine + PixelLayer | 不实现 |
| 钢笔路径 | Bezier 路径 + 锚点编辑 | 不实现 |
| 图层样式 | 投影/发光/浮雕/渐变叠加 | 简化为 6 套预设 |
| 核心目标 | 专业图像编辑 | 节点标注与分类 |
| **二次编辑** | 有 | **重点强化** |
| **持久化** | 有 | **重点强化** |
| **分类语义** | 无 | **新增核心能力** |

---

*方案制定：2026-06-17*
