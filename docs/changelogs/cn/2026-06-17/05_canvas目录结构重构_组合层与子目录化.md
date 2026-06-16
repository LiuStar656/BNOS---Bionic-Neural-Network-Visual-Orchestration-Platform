# Canvas 目录结构重构（组合层 + mixins + drawing 三目录）

---

## 背景

`ui/canvas/` 根目录长期堆积了 13 个 Python 文件，职责互相关联但未归类：

- `canvas_view.py` / `canvas_process.py` （入口 / 主类）
- `canvas_connections.py` / `canvas_box_select.py` / `canvas_batch_ops.py` / `canvas_menus.py` / `canvas_layout.py` / `canvas_colors.py` （Mixin 层）
- `canvas_selection.py` / `canvas_background_renderer.py` / `canvas_node_manager.py` / `canvas_event_handlers.py` （组合层，从 NodeCanvas 拆分出来的）
- `controllers.py` （控制器层）
- `draw_layer.py` / `draw_toolbar.py` + `graphic_items/` （绘图层）

**问题**：
1. 根目录文件过多，新人难以一眼辨识职责分层
2. Mixin / 组合层 / 绘图层 / 渲染项 四类文件完全没有目录隔离
3. 外部代码导入 `from ui.canvas.canvas_layout import ...` 等长路径与"根目录下一个文件"语义不一致

---

## 目标结构

```
ui/canvas/
├── __init__.py          ← 入口 + 旧路径兼容代理（sys.modules 别名）
├── canvas_view.py       ← NodeCanvas 主类（组合装配器 + Qt 虚函数转发）
├── canvas_process.py    ← 子进程启动入口（IPC 注册）
│
├── mixins/              ← 逻辑层（原堆在根目录的 11 个文件）
│   ├── canvas_connections.py
│   ├── canvas_box_select.py
│   ├── canvas_batch_ops.py
│   ├── canvas_menus.py
│   ├── canvas_layout.py
│   ├── canvas_colors.py
│   ├── canvas_selection.py
│   ├── canvas_background_renderer.py
│   ├── canvas_node_manager.py
│   ├── canvas_event_handlers.py
│   └── controllers.py   ← 7 个 Canvas 控制器（CanvasConnectionController 等）
│
├── drawing/             ← 绘图层
│   ├── draw_layer.py
│   ├── draw_toolbar.py
│   └── graphic_items/
│       ├── __init__.py
│       ├── _base.py
│       ├── arrow.py
│       ├── polygon.py
│       ├── rect.py
│       ├── round_rect.py
│       └── text.py
│
├── items/               ← 纯 UI 渲染（NodeItem / EdgeItem / AnchorItem / 节点样式）
│   └── styles/
│
└── parameter_widgets/   ← 参数编辑控件集合（保持不变）
```

**根目录现在只保留 3 个 Python 文件**（`__init__.py` / `canvas_view.py` / `canvas_process.py`），清晰明了。

---

## 实施方案

### 1. 文件迁移

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `ui/canvas/canvas_connections.py` | `ui/canvas/mixins/canvas_connections.py` | 连线 Mixin |
| `ui/canvas/canvas_box_select.py` | `ui/canvas/mixins/canvas_box_select.py` | 框选 Mixin |
| `ui/canvas/canvas_batch_ops.py` | `ui/canvas/mixins/canvas_batch_ops.py` | 批量操作 Mixin |
| `ui/canvas/canvas_menus.py` | `ui/canvas/mixins/canvas_menus.py` | 右键菜单 Mixin |
| `ui/canvas/canvas_layout.py` | `ui/canvas/mixins/canvas_layout.py` | 布局持久化 Mixin |
| `ui/canvas/canvas_colors.py` | `ui/canvas/mixins/canvas_colors.py` | 颜色设置 Mixin |
| `ui/canvas/canvas_selection.py` | `ui/canvas/mixins/canvas_selection.py` | 选择管理 + 命令录制（组合层） |
| `ui/canvas/canvas_background_renderer.py` | `ui/canvas/mixins/canvas_background_renderer.py` | 背景 + 网格（组合层） |
| `ui/canvas/canvas_node_manager.py` | `ui/canvas/mixins/canvas_node_manager.py` | 节点增删改（组合层） |
| `ui/canvas/canvas_event_handlers.py` | `ui/canvas/mixins/canvas_event_handlers.py` | 鼠标/键盘事件（组合层） |
| `ui/canvas/controllers.py` | `ui/canvas/mixins/controllers.py` | 7 个控制器（功能维度） |
| `ui/canvas/draw_layer.py` | `ui/canvas/drawing/draw_layer.py` | 绘图层主入口 |
| `ui/canvas/draw_toolbar.py` | `ui/canvas/drawing/draw_toolbar.py` | 绘图工具栏 UI |
| `ui/canvas/graphic_items/` | `ui/canvas/drawing/graphic_items/` | 绘图基元集合（整个目录） |

### 2. canvas_view.py 内部 import 迁移

`NodeCanvas.__init__` 中对 Mixin / 组合层 / 绘图层的导入全部更新为新路径：

```python
# 旧
from ui.canvas.canvas_colors import CanvasColorsMixin
from ui.canvas.canvas_layout import CanvasLayoutMixin
from ui.canvas.draw_layer import DrawLayer
from ui.canvas.canvas_selection import SelectionManager
from ui.canvas.canvas_background_renderer import BackgroundRenderer
from ui.canvas.canvas_node_manager import NodeManager
from ui.canvas.canvas_event_handlers import EventHandlers
# ...
from ui.canvas.controllers import CanvasConnectionController  # _init_controllers 内部

# 新
from ui.canvas.mixins.canvas_colors import CanvasColorsMixin
from ui.canvas.mixins.canvas_layout import CanvasLayoutMixin
from ui.canvas.mixins.canvas_connections import CanvasConnectionsMixin
from ui.canvas.mixins.canvas_box_select import CanvasBoxSelectMixin
from ui.canvas.mixins.canvas_batch_ops import CanvasBatchOpsMixin
from ui.canvas.drawing.draw_layer import DrawLayer
from ui.canvas.mixins.canvas_selection import SelectionManager
from ui.canvas.mixins.canvas_background_renderer import BackgroundRenderer
from ui.canvas.mixins.canvas_node_manager import NodeManager
from ui.canvas.mixins.canvas_event_handlers import EventHandlers
# ...
from ui.canvas.mixins.controllers import CanvasConnectionController
```

### 3. 旧路径兼容代理（核心）

为了不破坏项目中所有对 `ui.canvas.canvas_xxx` / `ui.canvas.draw_layer` / `ui.canvas.graphic_items` 的直接引用，在 `ui/canvas/__init__.py` 中注入 `sys.modules` 别名：

```python
# ui/canvas/__init__.py
import sys

# 注册 sys.modules 别名，使得：
#   from ui.canvas.canvas_layout import CanvasLayoutMixin （旧路径）
# 等同于：
#   from ui.canvas.mixins.canvas_layout import CanvasLayoutMixin （新路径）
_COMPAT_MAP = {
    # mixins / 组合层
    "ui.canvas.canvas_connections":      "ui.canvas.mixins.canvas_connections",
    "ui.canvas.canvas_box_select":       "ui.canvas.mixins.canvas_box_select",
    "ui.canvas.canvas_batch_ops":        "ui.canvas.mixins.canvas_batch_ops",
    "ui.canvas.canvas_menus":            "ui.canvas.mixins.canvas_menus",
    "ui.canvas.canvas_layout":           "ui.canvas.mixins.canvas_layout",
    "ui.canvas.canvas_colors":           "ui.canvas.mixins.canvas_colors",
    "ui.canvas.canvas_selection":        "ui.canvas.mixins.canvas_selection",
    "ui.canvas.canvas_background_renderer": "ui.canvas.mixins.canvas_background_renderer",
    "ui.canvas.canvas_node_manager":     "ui.canvas.mixins.canvas_node_manager",
    "ui.canvas.canvas_event_handlers":   "ui.canvas.mixins.canvas_event_handlers",
    # controllers
    "ui.canvas.controllers":             "ui.canvas.mixins.controllers",
    # drawing
    "ui.canvas.draw_layer":              "ui.canvas.drawing.draw_layer",
    "ui.canvas.draw_toolbar":            "ui.canvas.drawing.draw_toolbar",
    "ui.canvas.graphic_items":           "ui.canvas.drawing.graphic_items",
}

for alias, real in _COMPAT_MAP.items():
    try:
        mod = __import__(real, fromlist=["_"])
        sys.modules.setdefault(alias, mod)
    except Exception:
        pass
```

**关键特性**：
- 使用 `sys.modules.setdefault` — 仅在别名未被注册时注册，已注册的跳过
- 先真实导入模块再注入别名，保证 `alias is real`（两者是同一个模块对象，不会"同一文件被 import 两次"）
- 对 `import ui.canvas.canvas_layout as mod_old` 和 `import ui.canvas.mixins.canvas_layout as mod_new`，有 `mod_old is mod_new`

**保留对 items/ 子目录的引用不变**（这些文件本来就在子目录中，不需要兼容层）。

### 4. canvas_view.py 头部文档注释同步更新

在 `canvas_view.py` 顶部更新架构说明为 `ui/canvas/` 的新目录结构，作为活文档。

---

## 修改位置清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `ui/canvas/__init__.py` | 大幅修改 | 新增 sys.modules 别名注册；保留 NodeCanvas 导出 |
| `ui/canvas/canvas_view.py` | 部分修改 | 顶部架构说明 + import 路径全部指向新子目录 |
| `ui/canvas/mixins/`（11 个文件） | 新增 | 从根目录移动过来（内容无逻辑修改） |
| `ui/canvas/drawing/`（3 个文件 + graphic_items/） | 新增 | 从根目录移动过来 |
| 旧根目录下 11 个 .py 文件 + graphic_items/ + draw_layer.py + draw_toolbar.py | 已删除 | 文件迁移完成后删除 |

**无任何业务逻辑修改**，仅仅是文件物理位置重排 + import 路径重写 + 在 `__init__.py` 中加入兼容代理。

---

## 验证方法

### 测试 1：Python import 语法检查（独立脚本）
```python
import sys
sys.path.insert(0, ".")

# 新路径
from ui.canvas.canvas_view import NodeCanvas
from ui.canvas.mixins.canvas_layout import CanvasLayoutMixin
from ui.canvas.mixins.canvas_connections import CanvasConnectionsMixin
from ui.canvas.mixins.canvas_selection import SelectionManager
from ui.canvas.mixins.canvas_background_renderer import BackgroundRenderer
from ui.canvas.mixins.canvas_node_manager import NodeManager
from ui.canvas.mixins.canvas_event_handlers import EventHandlers
from ui.canvas.mixins.controllers import CanvasConnectionController
from ui.canvas.drawing.draw_layer import DrawLayer
from ui.canvas.drawing.draw_toolbar import DrawToolbar
from ui.canvas.drawing.graphic_items import GraphicBase
print("[OK] 新路径全部导入")

# 旧路径（向后兼容测试）
from ui.canvas.canvas_layout import CanvasLayoutMixin as CL2
from ui.canvas.canvas_menus import CanvasMenusMixin
from ui.canvas.canvas_connections import CanvasConnectionsMixin
from ui.canvas.draw_layer import DrawLayer as DL2
from ui.canvas.controllers import CanvasConnectionController as CCC2
from ui.canvas.canvas_selection import SelectionManager as SM2
from ui.canvas.graphic_items import GraphicBase as GB2
print("[OK] 旧路径全部导入（向后兼容）")

# 模块别名同一性验证
import ui.canvas.canvas_layout as mod_old
import ui.canvas.mixins.canvas_layout as mod_new
assert mod_old is mod_new, "模块别名不相同！"
print("[OK] 新旧路径的模块对象完全相同")
```
**期望结果**：✅ 三部分全部输出 OK，无 ImportError

### 测试 2：主程序启动（完整启动路径）
```bash
python bnos_console.py
```
**期望结果**：✅ 正常启动，观察关键日志：
```
[canvas_view.py] Canvas 控制器组合层已激活（7 个控制器，委托模式）
[canvas_view.py] NodeCanvas 已初始化（组合模式：选择/背景/节点/事件）
[canvas_layout.py] [load_layout] 已读取 canvas_layout.json: N 个节点位置
[canvas_layout.py] [load_layout] scene 已刷新, viewport 已刷新
[canvas_host.py]  CanvasHost: 画布 Dock 已创建（顶部停靠）
```
✅ 无 `ImportError: cannot import name 'xxx' from 'ui.canvas.xxx'`

### 测试 3：手动操作验证各子系统正常
- 从节点列表拖入新节点 → `NodeManager.add_node_to_canvas` → 节点出现 → 500ms 后 `canvas_layout.json` 保存
- 拖动节点 → 画布平滑滚动 + 节点重绘（BackgroundRenderer / EventHandlers 正常）
- Ctrl+点击多选 → SelectionManager.on_node_selected 正常，框选高亮
- 右键菜单 → CanvasMenusMixin 正常
- 连线 → CanvasConnectionsMixin + controllers.CanvasConnectionController 正常
- 切换两个项目的 canvas tab → 各自 layout 独立加载

### 测试 4：AST 语法检查（避免注释里藏了不合法的 Python 行）
```bash
python -c "import ast; [ast.parse(open(f).read()) for f in ['ui/canvas/__init__.py','ui/canvas/canvas_view.py','ui/canvas/canvas_process.py','ui/canvas/mixins/canvas_layout.py','ui/canvas/mixins/controllers.py','ui/canvas/drawing/draw_layer.py']]; print('OK')"
```
**期望结果**：✅ 输出 OK

---

## 关键设计决策

### 决策 1：保留旧路径的向后兼容代理（sys.modules 别名）
- **理由**：项目中可能还有其他文件（以及未来第三方代码）直接 `from ui.canvas.canvas_layout import ...`，一刀切破坏这些引用
- **影响**：无功能影响；启动时多一次 `__import__`，开销可忽略
- **回滚点**：如果某天确定没有外部依赖，直接删除 `_COMPAT_MAP` 那块即可

### 决策 2：不把 `canvas_view.py` 和 `canvas_process.py` 也塞进子目录
- **理由**：它们是整个 canvas 模块的"入口文件"，放在根目录语义更清晰；另外 `ui/main_window/ipc.py` 以 `ui/canvas/canvas_process.py` 作为 IPC 子进程路径，不动它可以省去不必要的修改
- **回滚点**：把它们搬到 `ui/canvas/app/` 之类的子目录是未来可选项，但当前不做

### 决策 3：controllers.py 归入 mixins/ 而非独立子目录
- **理由**：controllers.py 的 7 个类（`CanvasConnectionController` 等）本质上是"另一种 Mixin 思路"——按功能维度的组合器。它们体量小（约 100 行），单独占一个 `canvas/controllers/` 目录过于分散；和 mixins 放在一起查找方便
- **回滚点**：如果 controllers.py 增长到 ≥500 行，再独立出来也很简单（只需改 `__init__.py` 的兼容路径 + 移动文件）

### 决策 4：graphic_items/ 整个目录跟随 drawing/
- **理由**：graphic_items 是绘图层的基元（箭头/矩形/圆/多边形/文字），和 `draw_layer.py` / `draw_toolbar.py` 处于同一抽象层级，必须放在一起
- **回滚点**：无

---

## 向后兼容性矩阵

| 旧 import 写法 | 是否继续工作 | 备注 |
|----------------|-------------|------|
| `from ui.canvas.canvas_view import NodeCanvas` | ✅ | 位置没变 |
| `from ui.canvas.canvas_process import ...` | ✅ | 位置没变 |
| `from ui.canvas.items.node_item import NodeItem` | ✅ | items 子目录保持不变 |
| `from ui.canvas.canvas_layout import CanvasLayoutMixin` | ✅ | sys.modules 别名 |
| `from ui.canvas.canvas_menus import CanvasMenusMixin` | ✅ | sys.modules 别名 |
| `from ui.canvas.canvas_connections import CanvasConnectionsMixin` | ✅ | sys.modules 别名 |
| `from ui.canvas.canvas_colors import CanvasColorsMixin` | ✅ | sys.modules 别名 |
| `from ui.canvas.canvas_selection import SelectionManager` | ✅ | sys.modules 别名 |
| `from ui.canvas.canvas_background_renderer import BackgroundRenderer` | ✅ | sys.modules 别名 |
| `from ui.canvas.canvas_node_manager import NodeManager` | ✅ | sys.modules 别名 |
| `from ui.canvas.canvas_event_handlers import EventHandlers` | ✅ | sys.modules 别名 |
| `from ui.canvas.controllers import CanvasConnectionController` | ✅ | sys.modules 别名 |
| `from ui.canvas.draw_layer import DrawLayer` | ✅ | sys.modules 别名 |
| `from ui.canvas.draw_toolbar import DrawToolbar` | ✅ | sys.modules 别名 |
| `from ui.canvas.graphic_items import GraphicBase` | ✅ | sys.modules 别名 |
| `import ui.canvas.canvas_layout` | ✅ | 返回的是 `ui.canvas.mixins.canvas_layout` 同一个模块对象 |

---

## 变更规模与风险评估

| 维度 | 数值 | 说明 |
|------|------|------|
| 新增目录 | 2 | `ui/canvas/mixins/`, `ui/canvas/drawing/` |
| 移动文件数 | 14 | 11 个 mixins/controllers + 2 个 drawing 文件 + graphic_items/ 目录 |
| 删除根目录文件数 | 13 | 上述 11 个 .py + draw_layer.py + draw_toolbar.py |
| 业务代码改动 | 0 | 仅物理迁移 + import 重写 + 兼容代理 |
| 风险等级 | 极低 | 纯目录重构，所有调用路径通过 `sys.modules` 别名无缝衔接 |
| 回滚方式 | 把移动的文件原样拷回根目录并删除 `__init__.py` 中的 `_COMPAT_MAP` 块即可 | |

---

## 对后续开发的建议

1. **新增 canvas 模块时按职责归类**：逻辑类 → `mixins/`、绘图层 → `drawing/`、渲染项 → `items/`、新参数控件 → `parameter_widgets/`
2. **新代码优先使用新路径**：`from ui.canvas.mixins.canvas_xxx import ...` / `from ui.canvas.drawing.xxx import ...`，老路径只是兼容层
3. **下一轮优化方向**（可选）：
   - `controllers.py` 若增长到 ≥500 行，可独立为 `ui/canvas/controllers/` 目录（每个类一个文件）
   - `canvas_view.py` 的 Mixin 继承可改为组合模式（与 selection/background/node_manager/events 同样方式），彻底消除多重继承（需评估影响）
