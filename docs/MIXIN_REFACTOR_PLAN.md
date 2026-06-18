# BNOS Canvas Mixin 架构修复方案

**日期**: 2026-06-18
**范围**: `ui/canvas/` 目录下所有 mixin / 组合层 / controller 相关代码
**核心目标**: 保留对外 API 不变，将"隐式依赖 + 脆弱初始化 + 重复路径"的 mixin 架构改造为"显式组合 + 状态所有权清晰"的架构

---

## 一、现状诊断

### 1.1 当前架构总览

```
NodeCanvas (QGraphicsView)
  ├── 继承自 6 个 Mixin 类
  │     ├── CanvasConnectionsMixin   ← 无 __init__，依赖宿主隐式提供
  │     ├── CanvasBatchOpsMixin      ← 同上
  │     ├── CanvasBoxSelectMixin     ← 同上
  │     ├── CanvasMenusMixin         ← 同上
  │     ├── CanvasLayoutMixin        ← 同上
  │     └── CanvasColorsMixin        ← 同上
  │
  ├── 同时创建 4 个"组合层"对象
  │     ├── self.selection (SelectionManager)
  │     ├── self.background (BackgroundRenderer)
  │     ├── self.node_mgr (NodeManager)
  │     └── self.events (EventHandlers)
  │
  ├── 同时创建 7 个"controller"对象（_init_controllers）
  │     ├── self.connections (CanvasConnectionController)
  │     ├── self.batch_ops (CanvasBatchOperations)
  │     ├── self.box_select (BoxSelectionController)
  │     ├── self.menus (CanvasMenuController)
  │     ├── self.layout_ctrl (CanvasLayoutController)
  │     ├── self.colors (CanvasColorController)
  │     └── self.zoom_ctrl (CanvasZoomController)
  │
  └── 在 __init__ 中直接创建 ~15 个状态变量（无主人）
        ├── self.nodes, self.edges, self.scene, self.parent_window
        ├── self.is_connecting, self.connect_source, self.temp_edge
        ├── self.is_pan_mode, self.pan_start_pos, self.is_space_pressed
        ├── self.is_box_selecting, self.box_select_rect, self.box_selected_nodes
        ├── self._save_timer
        └── self.canvas_bg_color, self.node_bg_color, ... (8 个颜色变量)
```

### 1.2 四大问题的证据

| 问题 | 证据 | 数量 |
|---|---|---|
| **状态所有权模糊** | `self._save_timer` 在 5 个模块中被直接调用 `stop()/start()`；`self.box_selected_nodes` 被 3 个 mixin 共享修改 | `_save_timer`: 5 处；`box_selected_nodes`: 3 处 |
| **隐式依赖** | mixin 全部无 `__init__`，对宿主的访问全靠 `hasattr()` 防御检查 | **24 处** `hasattr/getattr`，跨 10 个文件 |
| **初始化顺序脆弱** | `_init_controllers()` 在 `__init__` 中段执行，此时部分组合层对象尚未创建 | 任何顺序调换都可能触发 `AttributeError` |
| **单元测试形同虚设** | 整个 `ui/canvas/` 2,800+ 行 0 个测试；mixin 无法脱离完整 Qt 环境实例化 | 0 个测试 |

### 1.3 重复路径的具体例子

"选择节点" 这一概念同时存在于 3 个实现中：

1. `CanvasBoxSelectMixin.clear_box_selection()` (mixin)
2. `SelectionManager.on_node_selected()` (组合层)
3. `BoxSelectionController.start()` (controller)

三者功能重叠，但调用路径不同。类似的重复模式出现在：连线、节点增删、布局保存、菜单。

### 1.4 对外 API 清单（必须 100% 保留）

以下方法被外部模块（panels, window_state_manager, canvas_process）直接调用，签名不可变：

```python
# 节点
canvas.add_node_to_canvas(node_name, node_info=None)
canvas.remove_node_from_canvas(node_name)
canvas.remove_node_with_cleanup(node_name)

# 连线
canvas.start_connection_from_output(node, output_anchor)
canvas.complete_connection_to_input(target_node, input_anchor)
canvas.add_connection(source, target)
canvas.remove_connection(source, target)
canvas.clear_all_connections()

# 布局持久化
canvas.save_layout(path)
canvas.load_layout(path)
canvas.save_center_coordinates()

# 状态查询 / 操作
canvas.on_node_selected(node)
canvas._toggle_node_selection(node_name)
canvas.clear_box_selection()
canvas.select_all_nodes()
canvas.deselect_all_nodes()
canvas.delete_selected_nodes()
canvas.start_selected_nodes()
canvas.stop_selected_nodes()
canvas.show_context_menu(pos)
canvas.apply_color_scheme(scheme)

# 事件（Qt 虚函数，转发给内部处理器）
canvas.mousePressEvent(event)
canvas.mouseMoveEvent(event)
canvas.mouseReleaseEvent(event)
canvas.keyPressEvent(event)
canvas.wheelEvent(event)
canvas.resizeEvent(event)
```

---

## 二、设计原则

1. **对外 API 零变更**：所有被外部调用的方法签名和行为保持不变
2. **组合优于继承**：mixin 不再通过继承混入 `NodeCanvas`，而是作为内部组合成员
3. **一状态一主人**：每个状态变量有唯一 owner，其他模块通过 getter 访问
4. **初始化顺序可推导**：`NodeCanvas.__init__` 严格按 "Qt 基础设施 → 状态层 → 业务层 → 事件层"顺序创建
5. **所有依赖显式**：每个组件在 `__init__` 中声明并断言它需要的依赖

---

## 三、分阶段修复方案

### 阶段 1：状态所有权清晰化（1.5 小时）

**目标**: 将 ~15 个自由状态变量分组到 4 个"状态仓"，有唯一 owner

#### 3.1.1 新建 `ui/canvas/state.py`

创建 4 个状态仓类（纯数据 + 简单操作）：

```python
class ConnectionState:
    """连线会话状态。Owner: CanvasConnectionsMixin（将改名为 Connections）"""
    def __init__(self):
        self.is_connecting: bool = False
        self.connect_source: Optional[NodeItem] = None
        self.temp_edge: Optional[QGraphicsPathItem] = None
        self._connect_source_anchor = None

class SelectionState:
    """框选与节点选中状态。Owner: SelectionManager"""
    def __init__(self):
        self.is_box_selecting: bool = False
        self.box_select_start_pos: Optional[QPointF] = None
        self.box_select_rect: Optional[QGraphicsRectItem] = None
        self.box_selected_nodes: List[str] = []
        self._is_replaying: bool = False

class NavigationState:
    """画布平移/键盘交互状态。Owner: EventHandlers"""
    def __init__(self):
        self.is_pan_mode: bool = False
        self.pan_start_pos: Optional[QPointF] = None
        self.is_space_pressed: bool = False
        self.space_mode_active: bool = False
        self._last_space_event_time: int = 0
        self._space_event_debounce_ms: int = 100

class CanvasColorScheme:
    """颜色主题。Owner: CanvasColorsMixin（将改名为 ColorScheme）"""
    BG: str = "#1e1e1e"
    GRID: str = "#2a2a2a"
    GRID_OPACITY: float = 0.3
    NODE_BG: str = "#2d2d30"
    NODE_BORDER: str = "#454545"
    NODE_TEXT: str = "#d4d4d4"
    NODE_SELECTED: str = "#007acc"
    INPUT_ANCHOR: str = "#6a9955"
    OUTPUT_ANCHOR: str = "#007acc"
    EDGE: str = "#007acc"
    EDGE_WIDTH: int = 2

    def to_dict(self) -> dict: ...
    def update_from(self, data: dict) -> None: ...
```

#### 3.1.2 `NodeCanvas.__init__` 状态层改造

将原本散乱的状态变量改为聚合：

```python
def __init__(self, parent=None):
    # --- Qt 基础设施 (顺序固定) ---
    super().__init__(parent)
    self.parent_window = parent
    self.canvas_width = 5000
    self.canvas_height = 5000
    half_w, half_h = self.canvas_width // 2, self.canvas_height // 2
    self.scene = QGraphicsScene(-half_w, -half_h, self.canvas_width, self.canvas_height, self)
    self.setScene(self.scene)
    ...

    # --- 数据存储层 ---
    self.nodes: Dict[str, NodeItem] = {}
    self.edges: List[EdgeItem] = []

    # --- 状态仓（状态所有权起点） ---
    self.connection_state = ConnectionState()
    self.selection_state = SelectionState()
    self.navigation_state = NavigationState()
    self.colors = CanvasColorScheme()

    # --- 绘图层（已有，保持不变） ---
    self.draw_layer = DrawLayer(self)
    self._draw_toolbar = self.draw_layer.attach_toolbar()
    self._draw_property_panel = self.draw_layer.attach_property_panel()

    # --- 自动保存定时器（唯一主人：NodeCanvas） ---
    self._save_timer = QTimer(self)
    self._save_timer.setSingleShot(True)
    self._save_timer.timeout.connect(self._auto_save_layout)

    # --- 业务层（在状态层之后创建，因为它们依赖状态） ---
    # 由各组合对象自行调用 self.canvas.connection_state 等
    self.selection = SelectionManager(self)
    self.background = BackgroundRenderer(self)
    self.node_mgr = NodeManager(self)

    # 连接/批量/菜单/颜色/布局/缩放 6 个模块（取代原有 mixin）
    self.connections = Connections(self)
    self.batch_ops = BatchOperations(self)
    self.menus = CanvasMenu(self)
    self.layout_mgr = CanvasLayout(self)
    self.zoom = CanvasZoom(self)

    # --- 事件处理器（最后创建，因为它依赖所有其他层） ---
    self.events = EventHandlers(self)
    self.events._load_draw_toolbar_config()
```

**关键保证**: `self.events` 在最后创建，因为它需要所有其他模块都已就绪。

---

### 阶段 2：Mixin → 组合层迁移（2 小时）

**目标**: 6 个 mixin 类从继承改为组合成员，对外 API 通过 `NodeCanvas` 转发

#### 3.2.1 迁移策略

| 原 mixin 类 | 新组合类名 | 文件 | 所属状态仓 | 对外方法 |
|---|---|---|---|---|
| `CanvasConnectionsMixin` | `Connections` | `canvas_connections.py` | `self.connection_state` | `start_connection_from_output`, `complete_connection_to_input`, `cancel_connection`, `add_connection`, `remove_connection`, `clear_all_connections` |
| `CanvasBatchOpsMixin` | `BatchOperations` | `canvas_batch_ops.py` | `self.selection_state` | `start_selected_nodes`, `stop_selected_nodes`, `delete_selected_nodes`, `select_all_nodes`, `deselect_all_nodes`, `move_selected_nodes`, `copy_selected_nodes` |
| `CanvasBoxSelectMixin` | 并入 `SelectionManager` | `canvas_selection.py` | `self.selection_state` | `clear_box_selection` (由 SelectionManager 承担) |
| `CanvasMenusMixin` | `CanvasMenu` | `canvas_menus.py` | `self.selection_state` | `show_context_menu`, `show_canvas_menu` |
| `CanvasLayoutMixin` | `CanvasLayout` | `canvas_layout.py` | `self.nodes`, `self.edges`, `self.colors` | `save_layout`, `load_layout`, `save_center_coordinates`, `_auto_save_layout` |
| `CanvasColorsMixin` | 并入 `CanvasColorScheme` + `ColorOps` | `canvas_colors.py` | `self.colors` | `apply_color_scheme`, `_load_color_settings`, `_save_color_settings` |

**重要**: `CanvasBoxSelectMixin` 的逻辑实际上与 `SelectionManager` 完全重叠，直接删除该 mixin 文件，功能合并入 `SelectionManager`。

#### 3.2.2 NodeCanvas 中的转发方法（对外 API 保持不变）

```python
# 文件: ui/canvas/canvas_view.py

# === 连接相关（转发给 self.connections） ===
def start_connection_from_output(self, node, anchor):
    return self.connections.start_connection_from_output(node, anchor)

def complete_connection_to_input(self, target_node, anchor):
    return self.connections.complete_connection_to_input(target_node, anchor)

def cancel_connection(self):
    return self.connections.cancel_connection()

def add_connection(self, source, target):
    return self.connections.add_connection(source, target)

def remove_connection(self, source, target):
    return self.connections.remove_connection(source, target)

def clear_all_connections(self):
    return self.connections.clear_all_connections()

# === 选择相关（转发给 self.selection） ===
def on_node_selected(self, node):
    return self.selection.on_node_selected(node)

def _toggle_node_selection(self, node_name):
    return self.selection._toggle_node_selection(node_name)

def clear_box_selection(self):
    return self.selection.clear_box_selection()

def select_all_nodes(self):
    return self.batch_ops.select_all_nodes()

def deselect_all_nodes(self):
    return self.batch_ops.deselect_all_nodes()

def delete_selected_nodes(self):
    return self.batch_ops.delete_selected_nodes()

# === 批量操作（转发给 self.batch_ops） ===
def start_selected_nodes(self):
    return self.batch_ops.start_selected_nodes()

def stop_selected_nodes(self):
    return self.batch_ops.stop_selected_nodes()

# === 菜单（转发给 self.menus） ===
def show_context_menu(self, pos):
    return self.menus.show_context_menu(pos)

# === 布局（转发给 self.layout_mgr） ===
def save_layout(self, path=None):
    return self.layout_mgr.save_layout(path)

def load_layout(self, path=None):
    return self.layout_mgr.load_layout(path)

def save_center_coordinates(self):
    return self.layout_mgr.save_center_coordinates()

def _auto_save_layout(self):
    return self.layout_mgr._auto_save_layout()

# === 颜色（转发给 self.colors） ===
def apply_color_scheme(self, scheme):
    # 注意：这里转发给 self.colors，但 CanvasColorScheme 是数据类
    # 颜色操作逻辑在 ColorOps 中
    return self._apply_color_scheme(scheme)
```

#### 3.2.3 每个组合类的初始化签名

所有组合类必须显式声明依赖，通过依赖断言验证：

```python
# 文件: ui/canvas/connections.py
class Connections:
    """画布连线。依赖: canvas.scene, canvas.nodes, canvas.edges,
    canvas.connection_state, canvas.parent_window, canvas._save_timer"""

    def __init__(self, canvas):
        self.canvas = canvas
        self._assert_dependencies()

    def _assert_dependencies(self):
        required = ['scene', 'nodes', 'edges', 'connection_state',
                     'parent_window', '_save_timer']
        for attr in required:
            assert hasattr(self.canvas, attr), (
                f"Connections 依赖 canvas.{attr} 但未找到"
            )
```

---

### 阶段 3：删除重复的 Controller 层（30 分钟）

`_init_controllers()` 创建的 7 个 controller 完全是 mixin → controller 的半成品。新架构中，这些 controller 的功能由组合类直接承担。

删除 `ui/canvas/mixins/controllers.py`，删除 `NodeCanvas.__init__` 中的：

```python
# 删除这一行
self._init_controllers()
```

---

### 阶段 4：文件结构调整（30 分钟）

#### 3.4.1 新目录结构

```
ui/canvas/
  ├── canvas_view.py               ← NodeCanvas（精简，仅装配和转发）
  ├── canvas_process.py            ← 保持不变
  │
  ├── state.py                     ← [新增] ConnectionState, SelectionState, NavigationState, CanvasColorScheme
  ├── connections.py               ← [新增] Connections（原 CanvasConnectionsMixin 的逻辑）
  ├── batch_ops.py                 ← [新增] BatchOperations（原 CanvasBatchOpsMixin）
  ├── canvas_menu.py               ← [新增] CanvasMenu（原 CanvasMenusMixin）
  ├── canvas_layout.py             ← [新增] CanvasLayout（原 CanvasLayoutMixin）
  ├── canvas_zoom.py               ← [新增] CanvasZoom（原 zoom 逻辑）
  │
  ├── mixins/                      ← 保留，内容减少
  │     ├── __init__.py
  │     ├── canvas_node_manager.py ← 保持不变（NodeManager 已在组合层使用）
  │     ├── canvas_background_renderer.py ← 保持不变（BackgroundRenderer）
  │     └── canvas_event_handlers.py ← 保持不变（EventHandlers）
  │     └── canvas_selection.py     ← 保持不变（SelectionManager，吸收 CanvasBoxSelectMixin 功能）
  │     └── canvas_colors.py        ← [修改] 只保留 ColorOps（运行时颜色切换逻辑）
  │     └── canvas_connections.py   ← [删除]
  │     └── canvas_box_select.py    ← [删除]
  │     └── canvas_batch_ops.py     ← [删除]
  │     └── canvas_menus.py         ← [删除]
  │     └── canvas_layout.py        ← [删除]
  │     └── controllers.py          ← [删除]
  │
  ├── drawing/                      ← 保持不变（绘图层独立）
  ├── items/                        ← 保持不变（NodeItem 等）
  ├── parameter_widgets/            ← 保持不变
  └── ...
```

**说明**: `mixins/` 目录保留但只放真正需要通过 `self.` 访问宿主的组合类（那些访问 Qt 基类方法如 `setBackgroundBrush`, `mapToScene` 等的组件）。纯粹的业务逻辑（connections, layout, batch_ops, menus）移到 `ui/canvas/` 顶层，不混入任何继承。

---

### 阶段 5：可测试性基础（1.5 小时）

#### 3.5.1 增加 `CanvasTestHarness` 测试辅助类

在 `ui/canvas/state.py` 中增加一个轻量级测试辅助：

```python
class CanvasTestHarness:
    """测试用：创建一个极简 NodeCanvas 环境，无需真实 Qt 窗口"""

    def __init__(self):
        self.scene = QGraphicsScene()
        self.nodes: Dict[str, Any] = {}
        self.edges: List[Any] = []
        self.connection_state = ConnectionState()
        self.selection_state = SelectionState()
        self.navigation_state = NavigationState()
        self.colors = CanvasColorScheme()
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self.draw_layer = MagicMock()  # 绘图层用 mock
        self.parent_window = MagicMock()
        self.canvas_width = 5000
        self.canvas_height = 5000
```

#### 3.5.2 示例测试文件

在 `tests/` 目录下增加测试（后续补充完整）：

```
tests/canvas/
  ├── test_connection_state.py      ← 测试 ConnectionState 行为
  ├── test_selection_state.py       ← 测试 SelectionState 行为
  ├── test_connections.py           ← 测试 Connections 模块
  └── test_canvas_layout.py         ← 测试 CanvasLayout 模块
```

每个测试文件使用 `CanvasTestHarness` 作为 canvas 参数，避免构建完整 Qt 应用。

---

## 四、实施步骤与风险控制

### 4.1 分阶段实施（按上述阶段）

| 阶段 | 预计耗时 | 核心动作 | 验证方式 |
|---|---|---|---|
| 1 | 1.5h | 创建 `state.py`，在 `NodeCanvas.__init__` 中替换散状态变量为聚合对象 | 搜索 `self.is_connecting` / `self.box_selected_nodes` 等，确认都通过 `self.connection_state` 等访问 |
| 2 | 2h | 将 6 个 mixin 改为组合类，NodeCanvas 增加转发方法 | 逐个文件替换，编译通过后启动应用 |
| 3 | 0.5h | 删除 `controllers.py` 和 `_init_controllers()` | 编译通过 + 功能测试 |
| 4 | 0.5h | 文件重命名/移动，更新 `__init__.py` | 路径搜索确认无遗留旧引用 |
| 5 | 1.5h | 测试基础设施 + 4 个示例测试文件 | `python -m pytest tests/canvas/` 通过 |
| **总计** | **~6.5 小时** | | |

### 4.2 回退策略

每个阶段是独立的：
- 若阶段 1（状态聚合）有问题：回退 `NodeCanvas.__init__` 为散变量，删除 `state.py`
- 若阶段 2（mixin 迁移）有问题：恢复 `NodeCanvas` 的类继承声明，删除组合层对象
- 若阶段 3-5 有问题：仅影响新引入的文件，可单独删除

### 4.3 运行时兼容性保证

- **启动路径不变**：`main_window.canvas = NodeCanvas(self)` 调用方式不变
- **外部引用不变**：所有外部使用 `.canvas.add_node_to_canvas()` / `.canvas.save_layout()` 的代码无需修改
- **事件分发不变**：`mousePressEvent` 等 Qt 虚方法仍由 `NodeCanvas` 定义，只是内部转发给 `self.events`

---

## 五、验收标准

### 5.1 代码层面

1. ✅ `grep -rn "class.*Mixin" ui/canvas/` — 结果应为 0 个 mixin 继承类
2. ✅ `grep -rn "hasattr(self, " ui/canvas/mixins/` — 结果应为 0（状态仓代替防御检查）
3. ✅ 每个组合类的 `__init__` 第一行调用 `_assert_dependencies()`
4. ✅ `NodeCanvas.__init__` 的初始化顺序严格为: Qt → 数据 → 状态 → 绘图层 → 业务 → 事件

### 5.2 测试层面

5. ✅ `python -c "from ui.canvas.state import ConnectionState, SelectionState"` 无错误
6. ✅ `python -c "from ui.canvas.connections import Connections"` 无错误
7. ✅ 至少 4 个单元测试文件存在，并可独立运行（无需 GUI）

### 5.3 运行层面

8. ✅ `python bnos_console.py` 启动无 `AttributeError`
9. ✅ 打开项目 → 节点显示、连线创建、框选、保存布局 均正常
10. ✅ 无新的 warning/error 日志

---

## 六、后续优化方向（P3+，非本次范围）

- `NodeItem` 组件间也存在类似隐式依赖问题，本次不涉及
- `draw_layer.canvas.scene` 链式访问仍有，但绘图层是独立子系统，可后续处理
- 引入真正的 `pytest` 覆盖 `connections`, `layout`, `selection` 等核心模块
