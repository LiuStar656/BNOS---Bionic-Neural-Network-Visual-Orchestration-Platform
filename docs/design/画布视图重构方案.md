# canvas_view.py 模块化拆分优化方案

**日期**: 2026-06-17
**状态**: 🔧 执行中
**类型**: 架构重构 / 代码拆分
**目标文件**: `ui/canvas/canvas_view.py`（当前 1044 行）

---

## 1. 问题概述

### 1.1 当前架构

```python
# 7 层 Mixin 继承
class NodeCanvas(
    CanvasConnectionsMixin,        # 连线
    CanvasBatchOpsMixin,            # 批量操作
    CanvasBoxSelectMixin,          # 框选
    CanvasMenusMixin,           # 菜单
    CanvasLayoutMixin,         # 布局
    CanvasColorsMixin,        # 颜色
    QGraphicsView               # Qt 基类
):
    """1 方法（1044 行
```

### 1.2 主要问题

| 问题 | 描述 | 影响 |
|------|-----|------|
| **MRO 继承层级过深 | 7 父类，方法解析顺序复杂，IDE 智能提示慢 | 维护难度 ↑
| **单文件过大 | 1044 行，阅读与检索效率低 | 开发效率 ↓
| **事件处理函数过大 | mousePressEvent 127 行，承担 4 种交互模式 | 阅读难
| **职责混合严重 | 初始化 + 渲染 + 事件 + 节点 + 选择 + 同步 + 录制 7 种职责混合 | 代码可读性 ↓
| **过渡状态未清理 | Controller 组合层已建但 Mixin 仍在使用 | 认知负担 ↑
| **方法分散 | 同主题方法分散在文件各处（节点相关方法在 15 处） | 定位成本 ↑

### 1.3 方法分类统计

| 类别 | 方法数 | 行数 | 占比 |
|------|---------|------|
| 初始化/场景（__init__, _init_controllers | 2 | ~166 | 16%
| 背景/网格渲染 | 2 | ~65 | 6%
| 鼠标/键盘事件 | 7 | ~360 | 34%
| 节点增删改 | 9 | ~230 | 22%
| 选择管理 | 5 | ~95 | 9%
| 状态同步 | 4 | ~55 | 5%
| 其他（委托 | 6 | ~70 | 7%
| **总计 | **35+** | **1044** | **100%**

---

## 2. 拆分原则

### 2.1 核心原则：**组合优于继承（Composition over Inheritance

1. **单一职责**（SRP）：每个模块只负责一件事
2. **最小变更**（OCP）：通过添加代码替换继承
3. **依赖倒置**（DIP）：模块依赖抽象而非具体
4. **最小化风险**（Minimize：分阶段实施，确保每阶段独立可回滚

### 2.2 拆分顺序

```
风险最低 → 风险最高

阶段 1：选择管理 + 命令录制（~95 行，🟢 低
阶段 2：背景/网格渲染（~65 行，🟢 低
阶段 3：节点管理（~230 行，🟡 中
阶段 4：事件处理（~360 行，🔴 高
```

### 2.3 设计模式

采用**组合模式（Composition

```python
# 拆分前（Mixin 继承）
class NodeCanvas(MixinA, MixinB, ...):   # 继承链复杂

# 拆分后（组合模式）
class NodeCanvas(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selection = SelectionManager(self)   # 组合
        self._renderer = BackgroundRenderer(self)   # 组合
        self._node_mgr = NodeManager(self)         # 组合
        self._events = EventHandlers(self)         # 组合

    # 事件处理：通过转发
    def mousePressEvent(self, event):
        self._events.mousePressEvent(event)        # 转发给事件处理器
```

---

## 3. 详细拆分方案

### 3.1 阶段 1：选择管理 + 命令录制

**输出文件**：`ui/canvas/canvas_selection.py`

**目标**：将选择状态管理和命令录制逻辑独立

**涉及方法**：

| 方法 | 行数 | 职责 |
|------|------|
| `on_node_selected` | 22 | 普通单击选中（单选 |
| `_toggle_node_selection` | 16 | 切换节点选中状态（Ctrl+单击多选 |
| `get_selected_node` | 2 | 获取当前选中的节点名称 |
| `clear_selection` | 1 | 清除节点选择 |
| `_begin_replay` | 2 | 进入命令重放模式 |
| `_end_replay` | 2 | 退出命令重放模式 |
| `_record_create_node` | ? | 录制创建节点命令 |
| `_record_delete_node` | ? | 录制删除节点命令 |

**状态字段**（需要从 NodeCanvas 中移动/封装：

```python
class SelectionManager:
    def __init__(self, canvas):
        self.canvas = canvas              # 反向引用主画布
        # 以下字段由 SelectionManager 封装管理
        # - box_selected_nodes = []（仍然由 NodeCanvas 持有但通过 self.canvas.box_selected_nodes 访问
```

**设计要点**：
- 命令录制方法与选择强相关，适合一起封装
- `box_selected_nodes` 保留在 NodeCanvas（因为它被多个模块（events、box_select 等）访问，避免循环依赖
- SelectionManager 通过 `self.canvas.box_selected_nodes 访问

---

### 3.2 阶段 2：背景/网格渲染

**输出文件**：`ui/canvas/canvas_background_renderer.py`

**目标**：将背景渲染逻辑完全独立

**涉及方法**：

| 方法 | 行数 | 职责 |
|------|------|------|
| `drawBackground` | 10 | 背景填充 + 调用网格 |
| `_ensure_grid_item` | 65 | 网格创建/DPR 感知/缓存 |
| `_grid_item` | - | 内部状态字段 |

**设计要点**：

```python
class BackgroundRenderer:
    """背景/网格渲染器
    
    完全独立的渲染器，持有对 canvas 的弱引用
    - 负责：背景填充、网格渲染、DPR 感知、网格缓存
    - 不涉及：事件、节点、选择
```

- Qt 的 `QGraphicsView.drawBackground(painter, rect)` 是虚函数，NodeCanvas 重写该方法
- 需要保留在 NodeCanvas 中保留一个薄包装转发给 Renderer

```python
# 在 NodeCanvas 中
def drawBackground(self, painter, rect):
    self._renderer.drawBackground(painter, rect)
```

---

### 3.3 阶段 3：节点管理

**输出文件**：`ui/canvas/canvas_node_manager.py`

**目标**：将节点的增删改、状态同步、面板管理等逻辑独立

**涉及方法**：

| 方法 | 行数 | 职责 |
|------|------|------|
| `add_node_to_canvas` | 60 | 添加节点到画布 |
| `remove_node_from_canvas` | 27 | 从画布移除节点 |
| `remove_node_with_cleanup` | 95 | 删除节点 + 清理上下游配置 |
| `rename_node_in_canvas` | 16 | 在画布中重命名节点 |
| `clear_canvas` | 20 | 清空画布 |
| `update_node_status` | 4 | 更新节点状态 |
| `detect_language` | 20 | 检测节点语言 |
| `sync_node_display` | 25 | 同步指定节点的显示 |
| `sync_all_nodes_display` | 4 | 同步所有节点的显示 |
| `start_single_node` | 3 | 启动单个节点（委托 |
| `stop_single_node` | 3 | 停止单个节点（委托 |
| `export_node_from_canvas` | 4 | 从画布导出节点（委托 |
| `stop_all_nodes` | 7 | 停止画布上所有节点进程 |
| `open_node_config` | 10 | 打开节点配置对话框 |
| `on_node_expand_requested` | 30 | 节点展开按钮回调

**设计要点**：
- 依赖 `self.parent_window.nodes_data` 等父窗口数据，通过 `self.canvas.parent_window 访问
- 需要频繁访问 `self.canvas.nodes` 和 `self.canvas.scene`
- 节点管理是业务逻辑的核心，拆分后显著降低主文件复杂度

---

### 3.4 阶段 4：事件处理

**输出文件**：`ui/canvas/canvas_event_handlers.py`

**目标**：将鼠标/键盘/滚轮事件处理逻辑独立

**涉及方法**：

| 方法 | 行数 | 职责 |
|------|------|------|
| `mouseMoveEvent` | 84 | 鼠标移动（平移/框选/连线拖拽 |
| `mousePressEvent` | 127 | 鼠标按下（空格+左键/Alt+左键/连线完成/取消选中 |
| `mouseReleaseEvent` | 50 | 鼠标释放（退出平移/框选 |
| `mouseDoubleClickEvent` | 20 | 鼠标双击（打开配置 |
| `keyPressEvent` | 59 | 键盘按下（空格进入/退出空格快捷键模式 |
| `keyReleaseEvent` | 60 | 键盘释放（跟踪空格键状态 |
| `wheelEvent` | 80 | 滚轮事件（Ctrl+缩放/触控板平移 |
| `resizeEvent` | 5 | 窗口大小改变 |
| `reset_view` | 5 | 重置视图到默认状态 |
| `_load_draw_toolbar_config` | 13 | 从 app_config 加载绘图工具栏显示状态 |
| `_toggle_draw_toolbar` | 5 | 切换绘图工具栏显示/隐藏 |

**设计要点**：

```python
class EventHandlers:
    """鼠标/键盘/滚轮事件处理
    
    - 持有 canvas 反向引用
    - 负责：交互模式判断、事件分派、调用选择管理
    - 不涉及：节点数据、渲染、持久化
```

- 事件处理器需要访问大量内部状态（is_pan_mode, is_connecting, is_box_selecting等）
- 这些状态保留在 NodeCanvas，但通过 self.canvas 访问
- Qt 的虚函数重写必须在 NodeCanvas 中保留薄包装转发

---

## 4. 最终架构

### 4.1 目标文件结构

```
ui/canvas/
├── __init__.py                      # 模块导出接口
│
├── canvas_view.py                      # ✅ 精简后的核心
│   └── NodeCanvas 类            # 仅负责组合+装配
│
├── canvas_event_handlers.py              # 阶段 4：事件处理
│   └── EventHandlers               # mouse/key/wheel 事件
│
├── canvas_node_manager.py                 # 阶段 3：节点管理
│   └── NodeManager            # 节点 CRUD + 状态同步
│
├── canvas_selection.py               # 阶段 1：选择管理 + 命令录制
│   └── SelectionManager
│
├── canvas_background_renderer.py      # 阶段 2：背景/网格渲染
│   └── BackgroundRenderer
│
│
├── canvas_connections.py            # ✅ 已有：CanvasConnectionsMixin
│   └── CanvasConnectionsMixin
│
├── canvas_batch_ops.py               # ✅ 已有：CanvasBatchOpsMixin
│
├── canvas_box_select.py             # ✅ 已有：CanvasBoxSelectMixin
│
├── canvas_menus.py              # ✅ 已有：CanvasMenusMixin
│
├── canvas_layout.py             # ✅ 已有：CanvasLayoutMixin
│
├── canvas_colors.py            # ✅ 已有：CanvasColorsMixin
│
├── controllers.py               # ✅ 已有：Controller 组合层
│
├── draw_layer.py                # ✅ 已有：绘图层
│
├── draw_toolbar.py             # ✅ 已有：绘图工具栏
│
└── items/                        # ✅ 已有：纯 UI 渲染组件
    ├── node_item.py
    ├── edge_item.py
    ├── anchor_item.py
    └── ...
```

### 4.2 拆分后 NodeCanvas 结构

```python
# 目标：约 200 行，仅负责组合和转发
class NodeCanvas(
    CanvasConnectionsMixin,        # 保留少量关键 Mixin（连线功能已独立但仍需继承
    QGraphicsView
):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # 组合模式（Composition）：4 个独立管理模块
        self._selection = SelectionManager(self)
        self._renderer = BackgroundRenderer(self)
        self._node_mgr = NodeManager(self)
        self._events = EventHandlers(self)

        # 核心字段（由各管理器通过 self.canvas.xxx 访问
        self.nodes = {}
        self.edges = []
        self.box_selected_nodes = []
        # ... 其他核心状态

        # 原有 Mixin 初始化调用
        # ...

    # ===== 事件转发（薄包装 =====
    def drawBackground(self, painter, rect):
        self._renderer.drawBackground(painter, rect)

    def mousePressEvent(self, event):
        self._events.mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._events.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._events.mouseReleaseEvent(event)

    # ... 其他事件转发

    # ===== 节点管理转发 =====
    def add_node_to_canvas(self, node_name, node_info=None):
        return self._node_mgr.add_node_to_canvas(node_name, node_info)

    def remove_node_from_canvas(self, node_name):
        return self._node_mgr.remove_node_from_canvas(node_name)

    # ... 其他节点方法转发

    # ===== 选择管理转发 =====
    def on_node_selected(self, node):
        return self._selection.on_node_selected(node)

    def clear_selection(self):
        return self._selection.clear_selection()

    # ... 其他选择方法转发
```

### 4.3 代码行数变化

| 文件 | 行数 | 说明 |
|------|------|------|
| canvas_view.py | 1044 | 200 | 组合与转发
| canvas_event_handlers.py | - | 360 | 事件处理
| canvas_node_manager.py | - | 230 | 节点管理
| canvas_selection.py | - | 95 | 选择与命令录制
| canvas_background_renderer.py | - | 65 | 背景渲染
| **总计** | **1044** | **~1200** | **净增加约 150 行包装代码**

---

## 5. 风险评估

### 5.1 各阶段风险评级

| 阶段 | 文件 | 行数 | 风险等级 | 原因 | 实施顺序
|------|------|------|---------|------|
| 1 选择管理 | canvas_selection.py | ~95 | 🟢 低 | 方法独立性强
| 5 背景渲染 | canvas_background_renderer.py | ~65 | 🟢 低 | 完全独立的渲染逻辑
| 3 节点管理 | canvas_node_manager.py | ~230 | 🟡 中 | 依赖 parent_window 数据
| 4 事件处理 | canvas_event_handlers.py | ~360 | 🔴 高 | 大量内部状态依赖 |

### 5.2 潜在问题与对策

| 潜在问题 | 风险 | 对策 |
|---------|------|
| 事件处理器访问大量内部状态 | 🔴 高 | 状态保留在 NodeCanvas，通过 self.canvas.xxx 访问
| `super().mouseXxxEvent 调用链在子类化后需正确传递 | 🟡 中 | EventHandlers 作为 Mixin，super() 仍指向 QGraphicsView
| `drawBackground` 是 QGraphicsView 虚函数，必须在 NodeCanvas 中保留 | 🟢 低 | 保留薄包装转发
| 选择状态 (`box_selected_nodes 被多模块访问 | 🟡 中 | 状态保留在 NodeCanvas，各管理器通过 self.canvas.box_selected_nodes 访问
| `_save_timer 在事件和节点操作中触发 | 🟡 中 | 保留在 NodeCanvas，各管理器通过 self.canvas._save_timer 访问
| `_replay_depth 命令录制深度 | 🟢 低 | 由 SelectionManager 管理
| 已有的 Mixin 与新组合模块并存 | 🟡 中 | 本方案不移除 Mixin，仅拆分新功能
| Qt 事件分发顺序 | 🟡 中 | 通过 super().mouseXxxEvent(event) 正确转发
| IDE 智能提示完整性 | 🟢 低 | 代码结构更清晰，IDE 提示更准确
| 测试覆盖不足 | 🔴 高 | 每个阶段后立即执行启动测试
| 导入循环依赖 | 🟡 中 | 通过弱引用或延迟导入

---

## 6. 验证方案

### 6.1 每个阶段的验证步骤

**阶段 1（canvas_selection.py）：
1. 创建新文件
2. 从 canvas_view.py 移动 选择相关方法到 SelectionManager
3. NodeCanvas 中删除原方法改为转发
4. `python -c "import ast; ast.parse(open('ui/canvas/canvas_selection.py').read()); print('OK')
5. 启动应用，测试：
   - 单击节点 → 选中状态正常
   - Ctrl+单击 → 多选正常
   - 框选 → 框选正常
   - 删除节点 → 正常

**阶段 2（canvas_background_renderer.py）：
1. 创建新文件
2. 移动 drawBackground 和 _ensure_grid_item
3. NodeCanvas 中保留 drawBackground 转发
4. `python -c "import ast; ast.parse(open('ui/canvas/canvas_background_renderer.py').read()); print('OK')
5. 启动应用，测试：
   - 背景颜色正常显示
   - 节点/边线正常显示
   - 缩放时网格线锐利（DPR 感知正常）

**阶段 3（canvas_node_manager.py）：
1. 创建新文件
2. 移动节点增删改、状态同步方法
3. NodeCanvas 中改为转发
4. `python -c "import ast; ast.parse(open('ui/canvas/canvas_node_manager.py').read()); print('OK')
5. 启动应用，测试：
   - 拖动节点到画布 → 节点正常显示
   - 删除节点 → 节点正常消失
   - 节点状态同步 → 状态图标变化正常
   - 节点面板打开 → 正常

**阶段 4（canvas_event_handlers.py）：
1. 创建新文件
2. 移动鼠标/键盘/滚轮事件处理方法
3. NodeCanvas 中保留 Qt 虚函数重写改为转发
4. `python -c "import ast; ast.parse(open('ui/canvas/canvas_event_handlers.py').read()); print('OK')
5. 启动应用，测试：
   - 空格+左键拖拽 → 平移正常
   - Alt+左键拖拽 → 框选正常
   - 滚轮缩放 → 正常（Ctrl+滚轮）
   - Ctrl+滚轮 → 放大/缩小正常
   - 节点拖拽到其他节点 → 连线正常

### 6.2 总体验证

每个阶段完成后执行：
```bash
# 语法检查
python -c "import ast; ast.parse(open('ui/canvas/canvas_view.py').read()); print('canvas_view.py: OK')

# 启动测试（通过 Qt 应用启动测试
python bnos_console.py
# 观察：
# 画布加载项目、节点、缩放/退出、无错误
```

---

## 7. 回滚策略

每个阶段都是独立可回滚

```bash
# 如果某阶段出现问题，执行：
git checkout HEAD -- ui/canvas/canvas_view.py
# 然后删除该阶段的新文件
rm ui/canvas/canvas_selection.py
rm ui/canvas/canvas_background_renderer.py
rm ui/canvas/canvas_node_manager.py
rm ui/canvas/canvas_event_handlers.py

# 重新运行测试
```

---

## 8. 后续优化方向（非本次拆分范围

1. **MRO 简化：移除 Mixin 继承，改为纯组合模式（需要大量工作
2. **Controller 层统一：将现有 controllers.py 的 Controller 与新模块合并
3. **状态字段封装：将 `is_xxx 状态独立为状态机或专用数据类
4. **单元测试：为每个新模块编写独立单元测试

---

## 9. 执行计划

| 步骤 | 操作 | 预计时间 |
|------|------|---------|
| 1 | 写优化方案 md 到 docs | 10 分钟
| 2 | 阶段 1：canvas_selection.py | 20 分钟 |
| 3 | 阶段 2：canvas_background_renderer.py | 20 分钟 |
| 4 | 阶段 3：canvas_node_manager.py | 30 分钟 |
| 5 | 阶段 4：canvas_event_handlers.py | 45 分钟 |
| 6 | 验证：语法+ 语法检查 + 启动测试 | 15 分钟 |
| **总计** | | **约 2 小时** |
