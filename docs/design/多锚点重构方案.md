# 多锚点输入系统重构方案

> 目标：在 **面板模式节点（DetailedNodeStyle）** 下，根据节点 `config.json` 中的 `input_ports` 定义生成对应锚点，
> 支持 **多上游节点同时连接** 到不同输入端口，彻底消除"连线被硬编码到默认锚点"的问题。

---

## 1. 现状与问题诊断

### 1.1 当前架构（5 个模块）

| 模块 | 文件 | 职责 |
|------|------|------|
| 配置解析层 | `ui/core/node_config_parser.py` | 解析 `config.json.input_ports` → `InputPortDef` |
| 节点渲染层 | `ui/canvas/items/node_item.py` | 构建/销毁多输入锚点 + 标签，处理点击 |
| 锚点视觉层 | `ui/canvas/items/anchor_item.py` | 单个锚点的视觉 + 悬停 + 双向绑定 |
| 连线条层 | `ui/canvas/items/edge_item.py` | 建立源/目标锚点的双向绑定，绘制带折叠点的直线 |
| 连线生命周期层 | `ui/canvas/canvas_connections.py` | 管理连线创建/删除，写回 `port_mappings` 到 config |

### 1.2 已识别的问题（4 个硬编码点）

#### 问题 A：`RectNodeStyle.apply()` 主动销毁多锚点（根因）

**位置**：`ui/canvas/items/node_style.py:191-192`

```python
# 框图模式不支持多输入端口，清理可能存在的多锚点
if hasattr(node_item, '_destroy_multi_input_anchors'):
    node_item._destroy_multi_input_anchors()
```

**后果**：`DetailedNodeStyle` 继承 `RectNodeStyle`，`_build_detailed_view()` 会先调用 `RectNodeStyle.apply()`，
此时多锚点被清掉。虽然 DetailedNodeStyle 紧接着又调用 `_build_multi_input_anchors()` 重建，
但任何后续重新 `apply` 样式都会再次丢失多锚点。

**同类问题**：`DotNodeStyle.apply()` 同样存在销毁逻辑（`node_style.py:307-308`）。

#### 问题 B：`CanvasView.mousePressEvent()` 点击完成连线时不传锚点信息

**位置**：`ui/canvas/canvas_view.py:396-397`

```python
if target_node and target_node != self.connect_source:
    self.complete_connection_to_input(target_node)   # ← 没有传 clicked_anchor
```

**后果**：从画布空白处点击节点完成连线时，永远连到默认 `input_anchor`，无法命中多输入端口。

#### 问题 C：`NodeItem.itemChange()` 节点移动时只刷新默认锚点的连线

**位置**：`ui/canvas/items/node_item.py:334-354`

仅遍历 `self.input_anchor.edges` 和 `self.output_anchor.edges`，**跳过 `self.input_anchors.values()`**。

**后果**：连到 `input2` 端口的连线在节点移动时路径不刷新（出现"脱节"视觉 Bug）。

#### 问题 D：多锚点坐标系不统一

点击检测用 `(click_x - (anchor_x + 8))`，锚点创建用 `setPos(anchor_x, anchor_y)`，
`AnchorItem` 的 `boundingRect` 又是 `(0,0,16,16)`——三处中心不一致，容易导致点击命中偏移。

---

## 2. 重构目标

| 编号 | 目标 | 验收标准 |
|------|------|----------|
| G1 | **统一锚点容器架构**：所有节点用同一套 `input_anchors` / `output_anchors` 字典 | 代码中不再存在 `input_anchor` / `output_anchor` 作为独立属性，它们只是 `input_anchors["default"]` 的别名 |
| G2 | **面板模式按 `input_ports` 生成多锚点** | 配置了 `input_ports` 的节点，每个端口都显示独立锚点 + 标签 |
| G3 | **支持多上游连接** | 多个上游节点可同时连接到同一下游节点的不同输入端口 |
| G4 | **点击任意锚点完成连线** | 画布视图中点击某个具体输入锚点，连线绑定到该锚点对应的端口 |
| G5 | **节点移动时所有连线路径自动刷新** | 拖动节点，所有 `input_anchors` 的边都实时更新路径 |
| G6 | **圆点/方框模式保留默认单锚点兼容** | 非面板模式继续使用单锚点（"default"），不影响现有用户体验 |
| G7 | **`port_mappings` 正确持久化** | 连到多输入端口时，下游节点 `config.json` 中 `port_mappings` 正确记录端口映射 |
| G8 | **清空画布 / 删除节点时正确清理引用** | `clear_edges`、删除节点、切换样式等操作不会残留锚点引用 |

---

## 3. 数据契约（config.json 格式）

### 3.1 输入端口定义

```json
{
  "input_ports": [
    {
      "name": "text",
      "label": "文本",
      "type": "string",
      "required": true,
      "description": "输入文本内容"
    },
    {
      "name": "context",
      "label": "上下文",
      "type": "string",
      "required": false,
      "description": "上下文文本（可选）"
    },
    {
      "name": "params",
      "label": "参数",
      "type": "json",
      "required": false
    }
  ],
  "parameters": [
    { "name": "temperature", "type": "float", "label": "温度", "default": 0.7 }
  ]
}
```

### 3.2 端口映射持久化

```json
{
  "port_mappings": {
    "text": "C:/project/nodes/node_a/output.json",
    "context": "C:/project/nodes/node_b/output.json"
  },
  "listen_upper_file": ""   // ← 保留旧字段，向后兼容：有 port_mappings 时优先读 port_mappings
}
```

> 读取优先级：`port_mappings` > `listen_upper_file`。无 `port_mappings` 时走旧逻辑。

### 3.3 输出端口（预留扩展位）

```json
{
  "output_ports": [
    { "name": "result", "label": "结果", "type": "string" },
    { "name": "log", "label": "日志", "type": "string" }
  ]
}
```

> 当前阶段只实现输入多锚点。输出端统一为 `["default"]`。输出多锚点放在第二期。

---

## 4. 架构设计

### 4.1 NodeItem 锚点统一容器（核心改动）

```
NodeItem (QGraphicsRectItem)
  │
  ├── input_anchors:    dict[str, AnchorItem]       # 核心容器（"default" 永远存在）
  ├── output_anchors:   dict[str, AnchorItem]       # 核心容器（"default" 永远存在）
  ├── input_port_labels: dict[str, QGraphicsTextItem]
  ├── output_port_labels: dict[str, QGraphicsTextItem]
  │
  ├── @property input_anchor  → self.input_anchors["default"]   # 兼容旧代码
  ├── @property output_anchor → self.output_anchors["default"]  # 兼容旧代码
  │
  ├── build_anchors_from_config(config)                # 根据 input_ports 重建
  ├── destroy_all_anchors()                            # 样式切换/销毁时调用
  ├── get_input_anchor(port_name: str | None)          # 返回指定端口，None=default
  ├── get_output_anchor(port_name: str | None)
  ├── find_nearest_input_anchor(pos: QPointF, max_dist: int)  # 点击检测
  └── all_input_anchors() → list[AnchorItem]
  └── all_output_anchors() → list[AnchorItem]
```

### 4.2 样式系统的锚点职责分离

| 样式 | 锚点策略 |
|------|----------|
| `DetailedNodeStyle`（面板模式） | **调用 `node_item.build_anchors_from_config()`**，根据 `input_ports` 生成多锚点 |
| `RectNodeStyle`（方框） | 调用 `node_item.ensure_default_input_anchor()`，只保留 default |
| `DotNodeStyle`（圆点） | 调用 `node_item.ensure_default_input_anchor()`，只保留 default |

**关键点**：所有 `_destroy_multi_input_anchors` 调用全部移除，统一由 `destroy_all_anchors()` 管理生命周期。

### 4.3 连线生命周期流程（重构后）

```
   用户点击节点 A 的输出锚点
        │
        ▼
   start_connection_from_output(A)
   → 记录 connect_source = A
   → 记录 source_anchor = A.output_anchors["default"]
   → 创建 temp_edge（跟随鼠标的虚线）
        │
        ▼
   用户点击节点 B 的某个输入锚点
        │
        ├── 画布视图层 (CanvasView.mousePressEvent)
        │     → 遍历 items(pos) 找到 AnchorItem
        │     → 拿到 target_node = anchor.parentItem()
        │     → 调用 complete_connection_to_input(target_node, clicked_anchor=anchor)
        │
        └── 节点层 (NodeItem.mousePressEvent)
              → 已经在多锚点点击逻辑里
              → 直接调用 complete_connection_to_input(self, clicked_anchor=anchor)
        │
        ▼
   create_edge(A, B, target_anchor=anchor)
   → 检查 anchor.port_name 是否已被同一源节点占用
   → 写入 B.config.port_mappings[anchor.port_name] = A.output_path
   → 创建 EdgeItem，端点锚点分别为 A.output_anchors["default"] 和 anchor
   → 双向绑定：edge.add_edge_to_anchors()
        │
        ▼
   节点移动 (NodeItem.itemChange)
   → 遍历 all_input_anchors() + all_output_anchors()
   → 每个 anchor.edges 中的 EdgeItem 都调用 update_path()
        │
        ▼
   删除连线 / 清空画布
   → remove_edge(edge) 删除 port_mappings 条目 + 解绑锚点
   → clear_edges() 遍历所有锚点清空
```

### 4.4 锚点坐标系统一

```python
# 全局常量（建议放到 anchor_item.py 顶部）
ANCHOR_SIZE = 16
ANCHOR_HALF = 8   # 8 = 16 / 2

# 锚点创建时：
anchor = AnchorItem(-ANCHOR_HALF, -ANCHOR_HALF, ANCHOR_SIZE, ANCHOR_SIZE, parent=self)
# 此时 boundingRect 中心 = (0,0)，setPos(anchor_x, anchor_y) 的 (x,y) 就是锚点几何中心

# 点击检测时（NodeItem 局部坐标）：
dist = ((click_x - anchor_x) ** 2 + (click_y - anchor_y) ** 2) ** 0.5
if dist <= ANCHOR_HALF + tolerance:
    # 命中该锚点
```

**好处**：`setPos(x, y)` 的坐标就是锚点中心，点击检测的距离就是真实几何距离，没有偏移 bug。

---

## 5. 详细改动清单（按文件组织）

### 5.1 `ui/canvas/items/anchor_item.py`

- [ ] 文件顶部新增常量：`ANCHOR_SIZE = 16`、`ANCHOR_HALF = 8`
- [ ] `AnchorItem.__init__` 接受 `port_name: str | None = None`、`port_type: str = "default"`、`port_label: str = ""`
- [ ] `AnchorItem` 新增属性：`port_name`、`port_type`、`port_label`（代替 NodeItem 里的零散设置）
- [ ] `hoverEnterEvent` / `hoverLeaveEvent` 保留（已有），但 **新增** tooltip 显示端口名称和数据类型

### 5.2 `ui/canvas/items/node_item.py`

**这是改动量最大的文件**。

- [ ] 删除 `self.input_anchor = AnchorItem(...)` 和 `self.output_anchor = AnchorItem(...)` 的初始化
- [ ] **新增** `self.input_anchors: dict[str, AnchorItem] = {}`
- [ ] **新增** `self.output_anchors: dict[str, AnchorItem] = {}`
- [ ] **新增** `self.input_port_labels: dict[str, QGraphicsTextItem] = {}`
- [ ] **新增** `self.output_port_labels: dict[str, QGraphicsTextItem] = {}`
- [ ] **新增 `@property input_anchor`** → 返回 `self.input_anchors["default"]`（兼容旧代码）
- [ ] **新增 `@property output_anchor`** → 返回 `self.output_anchors["default"]`（兼容旧代码）
- [ ] **新增方法 `_ensure_default_anchors()`**：创建 `input_anchors["default"]` 和 `output_anchors["default"]`（位置由样式设置）
- [ ] **新增方法 `build_anchors_from_config(config)`**：
  - 解析 `NodeConfigParser.parse_input_ports(config)`
  - 无端口 → `_ensure_default_anchors()`
  - 有端口 → 每个端口创建一个 `AnchorItem`，垂直分布
  - 位置计算：在 `header + divider` 以下均匀分布，`anchor_x = -ANCHOR_HALF`（左侧），`anchor_y` 均匀分布
  - 标签（label）在锚点右侧显示端口名称
  - **必需端口（required=True）** 用高亮色边框 / 填充区分
- [ ] **新增方法 `destroy_all_anchors()`**：清空 `input_anchors`、`output_anchors` 及对应 labels
- [ ] **新增方法 `find_nearest_input_anchor(local_pos: QPointF, max_dist: int = 16) -> AnchorItem | None`**：用于点击检测
- [ ] **修改 `mousePressEvent` 方块节点分支**：
  - 输出锚点：检测 `find_nearest_output_anchor`（目前只有一个 default）
  - 输入锚点：检测 `find_nearest_input_anchor`，命中后传 `clicked_anchor`
  - 圆点节点分支保持不变（只有 default）
- [ ] **修改 `itemChange(ItemPositionHasChanged)`**：遍历 `all_input_anchors()` + `all_output_anchors()` 的 `.edges`，全部 `update_path()`
- [ ] **修改 `_build_detailed_view()`**：移除旧的 `_build_multi_input_anchors` 调用，改为调用新的 `build_anchors_from_config(config)`
- [ ] **删除方法 `_build_multi_input_anchors()` 和 `_destroy_multi_input_anchors()`**（统一到新 API）
- [ ] **新增/修改 `_get_label_font()`**：复用现有实现，位置调用

### 5.3 `ui/canvas/items/node_style.py`

- [ ] **修改 `RectNodeStyle.apply()`**：
  - 删除 `_destroy_multi_input_anchors` 调用
  - 锚点设置逻辑改为调用 `node_item._ensure_default_anchors()`
  - 输出锚点位置：`setPos(w - ANCHOR_HALF, h/2 - ANCHOR_HALF)`
  - 输入锚点位置（default）：`setPos(-ANCHOR_HALF, h/2 - ANCHOR_HALF)`
- [ ] **修改 `DotNodeStyle.apply()`**：
  - 删除 `_destroy_multi_input_anchors` 调用
  - 调用 `node_item._ensure_default_anchors()`
  - 输入/输出锚点位置保持圆点中心（用大尺寸覆盖圆点区域）
- [ ] **修改 `DetailedNodeStyle.apply()`**：
  - 先 `_build_detailed_view()`（设置节点尺寸）
  - 再 `build_anchors_from_config(config)`（**在尺寸确定后**，因为锚点垂直分布依赖节点高度）
- [ ] **新增 `DetailedNodeStyle.apply()` 读取节点 config**：从 `parent_window.nodes_data[node_name]['config']` 获取

### 5.4 `ui/canvas/items/edge_item.py`

- [ ] **`_setup_anchor_binding()`** 维持现有逻辑（已支持 `target_anchor`）
- [ ] **`_endpoints()`** 维持现有 `mapToScene` 逻辑（已适配任意锚点）
- [ ] **新增断言/日志**：当 `start_anchor` 或 `end_anchor` 不在 `input_anchors/output_anchors` 中时，输出警告日志

### 5.5 `ui/canvas/canvas_connections.py`

- [ ] **修改 `start_connection_from_output(source_node)`**：记录 `self.connect_source_anchor = source_node.output_anchors["default"]`
- [ ] **修改 `complete_connection_to_input(target_node, clicked_anchor=None)`**：
  - 如果 `clicked_anchor is None`，**不要使用**旧的 `input_anchor`，改为使用 `target_node._default_input_anchor`（必需端口优先，否则第一个端口，否则 default）
  - 这样圆点/方框模式（没有多锚点）也能正确工作
- [ ] **`create_edge()` 里的端口映射保存**：维持现有逻辑，但要处理 `port_name = None` 的情况（即连到 default 端口时不写入 `port_mappings`，保持旧的 `listen_upper_file` 兼容）
- [ ] **`remove_edge()` 的引用清理**：遍历 `target_node.all_input_anchors()` 查找 anchor → edge 映射，确保正确删除
- [ ] **`clear_edges()`**：遍历 `node.all_input_anchors()` 和 `node.all_output_anchors()` 清空所有锚点的 edges

### 5.6 `ui/canvas/canvas_view.py`

- [ ] **修改 `mousePressEvent` 连线模式分支**（`canvas_view.py:380-405`）：
  - 遍历 `items(event.position().toPoint())` 时，**同时检测 `AnchorItem`**
  - 如果找到 AnchorItem：`target_node = anchor.parentItem()`，传入 `complete_connection_to_input(target_node, clicked_anchor=anchor)`
  - 否则走旧逻辑（连到默认锚点）

### 5.7 `ui/core/node_config_parser.py`

- [ ] **新增 `has_output_ports()`**、`parse_output_ports()`、`get_output_port_names()`（第二期用）
- [ ] **保留现有 `InputPortDef`** 字段（name / label / type / required / description）

---

## 6. 测试与验证清单

| 测试场景 | 预期结果 |
|----------|----------|
| 面板模式节点，配置了 3 个 `input_ports` | 节点左侧出现 3 个垂直分布的锚点 + 对应标签 |
| 未配置 `input_ports` 的面板模式节点 | 只显示一个默认锚点（位置在节点高度中间） |
| 3 个上游节点同时连到下游节点的 3 个不同端口 | 下游节点 `config.json` 中 `port_mappings` 记录 3 条映射 |
| 从画布视图点击某个输入锚点完成连线 | 连线绑定到该锚点，不会被"吸"到默认锚点 |
| 拖动节点移动 | 所有连到多锚点的连线都实时刷新路径 |
| 连到同一端口两次 | 提示"已存在连线到该端口"（和现有去重逻辑一致） |
| 删除连到多输入端口的连线 | `port_mappings` 对应条目被删除，其他保留 |
| 切换节点样式（面板 ↔ 方框） | 锚点系统跟随切换，没有残留引用和崩溃 |
| 保存/加载布局 | 多锚点连线路径和 `port_mappings` 正确还原 |
| 旧版无 `input_ports` 的节点（向后兼容） | 表现和单锚点旧系统一致 |

---

## 7. 实施顺序（建议 4 步，逐步验证）

### 第 1 步：NodeItem 统一锚点容器（~文件 node_item.py）
先做容器化，把 `input_anchor/output_anchor` 合并成字典。此阶段不涉及多锚点显示，只做 API 统一和 `@property` 兼容。

**完成标志**：现有功能（单锚点）一切正常，无回归。

### 第 2 步：样式系统改造（node_style.py）
移除所有 `_destroy_multi_input_anchors` 调用，改为 `destroy_all_anchors()` + `build_anchors_from_config()`。

**完成标志**：面板模式节点能按 `input_ports` 显示多锚点。

### 第 3 步：点击检测 + 画布视图链路打通（canvas_view.py, node_item.py）
让 `CanvasView.mousePressEvent` 能命中 `AnchorItem` 并传入 `clicked_anchor`。

**完成标志**：点击具体锚点完成连线，绑定到正确端口。

### 第 4 步：引用清理 + 路径刷新 + port_mappings 持久化（canvas_connections.py）
确保 `itemChange` 刷新所有锚点连线、`clear_edges/remove_edge` 正确清理、配置文件正确读写。

**完成标志**：所有测试场景通过，无残留引用崩溃。

---

## 8. 风险与回滚

| 风险 | 影响 | 对策 |
|------|------|------|
| `input_anchor` 被大量旧代码直接引用 | 重构初期可能有 AttributeError | 提供 `@property input_anchor` alias + 全局搜索替换 |
| 锚点位置计算依赖节点高度，DetailedNodeStyle 两阶段构建时序问题 | 锚点位置错位 | 在 `build_anchors_from_config` 开始前断言 `self.rect().height() > 0` |
| `AnchorItem` 被当作 `QGraphicsEllipseItem` 直接访问内部属性 | 重构后类型还是 `QGraphicsEllipseItem`，无风险 | - |
| 圆点节点的大锚点与 `AnchorItem` 尺寸冲突（目前 16→圆点是 40+） | 圆点模式被多锚点逻辑干扰 | 圆点模式调用 `_ensure_default_anchors()` 时显式设置大尺寸并覆盖默认大小 |
| 旧布局文件加载时连线端点映射失败 | 加载后连线路径错位 | `EdgeItem.from_dict` 维持现有兼容逻辑，端点用 `_default_input_anchor` 回退 |

**回滚策略**：每个阶段完成后提交一次独立 commit，发现回归可按阶段回退。

---

## 9. 后续扩展方向（第二期）

- **输出端多锚点**：按 `output_ports` 生成多个输出锚点，上游→下游连线可选择输出端口
- **端口类型匹配校验**：连线时检查源 `output_ports[type]` 和目标 `input_ports[type]` 是否兼容，给出友好提示
- **端口分组与折叠**：输入端口多时，按分类折叠显示，减少视觉噪音
- **端口颜色语义**：必需端口红色边框 / 警告色，可选端口灰色
- **拖拽调整端口顺序**：右键菜单 → 重排端口
