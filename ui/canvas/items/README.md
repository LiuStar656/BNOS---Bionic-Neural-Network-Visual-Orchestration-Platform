# Canvas Items 模块（画布项系统）

> 画布项模块：节点、锚点、连线的可视化表示与交互管理。
> 负责 BNOS 画布上所有图形元素的创建、渲染、交互和数据绑定。

---

## 📁 模块结构

```
ui/canvas/items/
├── node_item.py          # 节点图形项（核心）
├── node_style.py         # 节点样式系统（3 种样式：Block/Node/Panel）
├── node_status_widget.py # 节点状态指示器（运行/停止/错误 灯）
├── anchor_item.py        # 锚点图形项（端口连接点）
├── anchor_manager.py     # 锚点管理器（多锚点创建、查找、edges 迁移）
├── edge_item.py          # 连线图形项（贝塞尔曲线 + 折叠点交互）
└── __init__.py
```

---

## 🎨 核心概念

### 1. NodeItem（节点）

画布上的基本单位，表示一个代码节点（Python/Rust/Node.js 等）。

**关键属性**：
- `node_name`: 节点唯一标识（对应文件夹名）
- `language`: 编程语言，用于图标显示
- `status`: 运行状态（stopped/running/error）
- `_style`: 节点样式对象（RectNodeStyle / CircleNodeStyle / DetailedNodeStyle）
- `anchor_manager`: 锚点管理器（管理输入/输出锚点）
- `_param_row_positions`: 面板模式下各参数/端口行的 Y 坐标（锚点定位依据）

**生命周期**：
1. `__init__` → 初始化基础属性，应用默认样式
2. `_style.apply(self)` → 根据样式创建具体图形元素
3. （面板模式）`_build_detailed_view()` → 解析 config.json，创建参数控件和小锚点
4. （面板模式）`build_anchors_from_config()` → 根据 config 创建多锚点系统
5. `setPos(x, y)` → 放置到画布
6. `on_expand_requested` 回调 → 响应展开/折叠请求

### 2. AnchorManager（锚点管理）

管理节点的输入/输出锚点，支持单锚点（Block/Node 样式）和多锚点（Panel 样式）两种模式。

**锚点类型**：
- **主输入锚点**：`port_name="default"`，16px 圆形，节点左侧垂直居中（所有样式都有）
- **附加输入锚点**：`port_name="prompt"/"context"` 等，10px 圆形，紧贴对应参数行左侧（仅 Panel 样式）
- **输出锚点**：`port_name="default"`，16px 圆形，节点右侧垂直居中

**关键方法**：
- `get_input(port_name)` → 按端口名查找输入锚点；`None`/`"default"` 返回主锚点
- `get_output(port_name)` → 按端口名查找输出锚点
- `build_from_config(config, positions, node_w, node_h)` → 根据 config.json 和行位置重建锚点系统
  - **关键**：重建前收集旧锚点上的 edges，销毁旧锚点，创建新锚点，然后按期望端口名迁移 edges

**Edge 迁移机制**（见 `anchor_manager.py` 110-175 行）：
1. 收集旧锚点 edges → `old_input_edges: [(port_name, edges), ...]`
2. 销毁旧锚点，创建新锚点
3. 遍历 `old_input_edges`，按 `port_name` 匹配新锚点
4. 找不到匹配时 fallback 到 default 锚点（仅在未指定特定端口名时）

### 3. EdgeItem（连线）

连接两个节点的贝塞尔曲线，支持人工折叠点（双击创建、拖拽调整、双击删除）。

**端口绑定机制**（V2.0.11 起增强）：
- `_desired_target_port_name`: 记忆原始 `target_port`（从 canvas_layout.json 读取）
- `_desired_source_port_name`: 记忆原始 `source_port`
- `_setup_anchor_binding()`: 绑定逻辑
  1. 优先使用期望端口名查找锚点
  2. 如果指定了特定端口但找不到 → **保持 None，不降级**
  3. 未指定特定端口 → 允许使用默认锚点（`end_node.input_anchor`）
- `update_path()`: 动态更新路径，锚点位置变化后自动重绘

**交互行为**：
- 鼠标悬停显示折叠手柄（HOVER_WIDTH_DELTA）
- 点击手柄 → 选中线条
- 长按拖拽 → 创建折叠点
- 双击折叠点 → 删除折叠点

### 4. NodeStyle 系统（3 种样式）

| 样式 | 类名 | 外观 | 适用场景 | 锚点系统 |
|------|------|------|----------|---------|
| Block（框图） | `RectNodeStyle` | 方框 + 标题/图标 | 逻辑流程清晰展示 | 单锚点（左右各一个） |
| Node（节点） | `CircleNodeStyle` | 圆形 + 状态灯 | 强调连接关系 | 单锚点（左右各一个） |
| Panel（面板） | `DetailedNodeStyle` | 可展开卡片 + 参数控件 | 节点参数编辑 | 多锚点（default + prompt + context...） |

**样式切换**：`node_item._switch_node_style(key)` → 销毁旧样式 → 应用新样式 → 重建锚点 → 迁移 edges

---

## 🔌 与其他模块的协作

### → canvas_layout.py（布局持久化）
- `save_layout()`: 遍历 `self.nodes` 和 `self.edges`，写入 `canvas_layout.json`
- `load_layout()`: 读取 JSON，创建 NodeItem/EdgeItem，绑定正确锚点
- `_validate_edge_anchor_binding()`: 样式切换后重新绑定 edge 到正确锚点

### → canvas_connections.py（连线创建）
- `create_edge(source_node, target_node, target_anchor, source_anchor)`: 用户拖拽创建连线
- 传入 `target_port_name`/`source_port_name` 参数以记忆端口绑定

### → node_config_parser.py（配置解析）
- `parse_input_ports(config)`: 提取 `input_ports` 定义（含 `source: "node"` 标记）
- `ParameterDef`: 参数定义数据类（int/float/string/bool/enum/color/range...）

### → parameter_widgets.py（参数控件）
- Panel 模式下在节点内嵌入 QGraphicsProxyWidget
- 参数修改即时写回 `config.json`

---

## ⚠️ 重要注意事项

### 1. `_param_row_positions` 的关键作用

`node_item._param_row_positions` 是一个 `dict[str, tuple[float, float, int]]`：
- Key: 端口名（如 `"prompt"`, `"context"`）
- Value: `(center_x, center_y, size)`

如果这个字典没有正确填充，`anchor_manager.build_from_config()` 就**不会**创建对应锚点，连线会找不到锚点而降级。

**修复（V2.0.10+）**：`_build_detailed_view` 中使用估算 y 坐标 `est_ys[i]` 兜底，确保即使 Qt 布局几何未就绪，锚点位置也能正确计算。

### 2. AnchorManager 重建的 Edge 迁移

当节点切换样式或重新加载时：
1. 旧锚点被销毁
2. 新锚点被创建
3. 旧锚点上的 edges 必须迁移到新锚点

迁移的**关键依据**是 `edge._desired_target_port_name`（V2.0.11+）。如果没有这个字段，会使用 `edge.end_anchor.port_name`，但这可能在旧锚点销毁前已经被错误设置。

### 3. config.json 的 `input_ports.source` 字段

只有 `source: "node"` 的端口才会在画布上生成锚点（`_build_detailed_view` 中的过滤逻辑）：

```python
input_port_defs = NodeConfigParser.parse_input_ports(config)
input_port_defs = [p for p in input_port_defs if getattr(p, "source", "") == "node"]
```

其他 `source` 值（如 `"edit"` / `"param"`）的端口在参数面板中以输入框形式呈现，不生成图形锚点。

---

## 📖 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|---------|
| V2.0.11 | 2026-06-11 | EdgeItem 期望端口名记忆、锚点缺失不降级、canvas_layout 防改写 |
| V2.0.10 | 2026-06-10 | 多锚点系统完善、锚点差异化尺寸、小锚点位置估算修复 |
| V2.0.4 | 2026-05-23 | 节点样式系统（Block/Node/Panel 三样式切换） |
| V2.0.3 | 2026-05-22 | ComfyUI 风格连线重构、人工折叠交互 |

---

## 🔗 相关文件

- `ui/canvas/items/node_item.py` - 节点图形项
- `ui/canvas/items/anchor_manager.py` - 锚点管理器
- `ui/canvas/items/anchor_item.py` - 锚点图形项
- `ui/canvas/items/edge_item.py` - 连线图形项
- `ui/canvas/items/node_style.py` - 节点样式系统
- `ui/canvas/canvas_layout.py` - 布局加载/保存
- `ui/core/node_config_parser.py` - 节点配置解析
