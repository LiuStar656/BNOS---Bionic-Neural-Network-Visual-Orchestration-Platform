# Canvas 模块（画布系统）

> 画布模块：BNOS 项目的图形化工作区。
> 提供节点布局、连线绘制、参数编辑、视图管理等核心可视化功能。

---

## 📁 模块结构

```
ui/canvas/
├── canvas_view.py         # 画布视图（QGraphicsView）— 主容器
├── canvas_layout.py       # 布局加载/保存（canvas_layout.json 持久化）
├── canvas_connections.py  # 连线创建/删除管理
├── canvas_menus.py        # 右键菜单（ActionFactory 驱动）
├── canvas_process.py      # 画布进程管理
├── canvas_batch_ops.py    # 批量操作（批量启动/停止/清除监听）
├── canvas_box_select.py   # 框选/多选操作
├── canvas_colors.py       # 颜色配置（连线/节点色）
├── controllers.py         # 画布控制器（save_layout/load_layout 代理）
├── draw_layer.py          # 绘图层（手绘/标注）
├── draw_toolbar.py        # 绘图工具栏（按需显示）
├── graphic_items.py       # 图形辅助项
├── parameter_widgets.py   # 参数控件工厂（11 种参数类型，Panel 模式用）
├── items/                 # 图形项模块（见 items/README.md）
│   ├── node_item.py       # 节点
│   ├── edge_item.py       # 连线
│   ├── anchor_item.py     # 锚点
│   ├── anchor_manager.py  # 锚点管理器
│   ├── node_style.py      # 样式系统
│   └── node_status_widget.py # 状态指示器
└── __init__.py
```

---

## 🎯 核心功能

### 1. 画布视图（canvas_view.py）

**类 `NodeCanvas(QGraphicsView)`**：主画布容器，承载所有图形项。

**关键属性**：
- `self.nodes: dict[str, NodeItem]` → 节点名 → 节点图形项
- `self.edges: list[EdgeItem]` → 所有连线
- `self._save_timer: QTimer` → 自动保存定时器（节点移动/连线变化后 500ms 触发）
- `self.canvas_width / canvas_height` → 画布逻辑尺寸

**关键方法**：
- `save_layout(project_path)` → 保存到 `canvas_layout.json`
- `load_layout(project_path)` → 从 `canvas_layout.json` 恢复
- `_save_timer.start(500)` → 自动保存触发（V2.0.11 起在 `load_layout` 开始时先 stop）

### 2. 布局持久化（canvas_layout.py）

**Save 流程**：
```python
1. 遍历 self.nodes → 写入 x/y/width/height/style/custom_colors
2. 遍历 self.edges → 写入 source/target/source_port/target_port
   - edge.end_anchor.port_name → target_port（如果锚点存在）
   - edge._desired_target_port_name → 锚点被销毁时的 fallback
3. 保存视图状态（scale/scroll/center）
4. 写入 <project>/canvas_layout.json
```

**Load 流程**（V2.0.11 强化）：
```python
1. _save_timer.stop()  ← 关键：防止加载过程中保存损坏状态
2. 读取 canvas_layout.json
3. 遍历 nodes → 创建 NodeItem（如果不存在），应用 style
4. 遍历 edges → 【关键】先查找锚点：
     a. src_port = ed.get("source_port")
     b. tgt_port = ed.get("target_port")
     c. src_anchor = source_node.anchor_manager.get_output(src_port)
     d. tgt_anchor = target_node.anchor_manager.get_input(tgt_port)
     e. 【V2.0.11+】如果指定了非 default 端口但找不到锚点
        → 记录 WARNING，跳过该连线（不降级到 default）
     f. 创建 EdgeItem(..., target_port_name=tgt_port, source_port_name=src_port)
5. _validate_edge_anchor_binding() → 修复锚点重建后引用失效的 edge
6. 恢复视图状态（scale/scroll/center）
```

**去重逻辑**（防止重复连线）：
- 加载 edges 前，先收集画布上已存在的 edges → `existing: set[(src, tgt, port)]`
- 新 edge 的 `(sn, tn, tp)` 如果已在 `existing` 中 → 跳过
- Config 推断的连线使用 `canvas_pair_set: set[(src, tgt)]` 进行第二层去重

### 3. 连线管理（canvas_connections.py）

**创建连线**：`create_edge(source_node, target_node, target_anchor, source_anchor)`

```python
1. 检查是否已存在相同锚点的连线
2. 创建 EdgeItem 并传入 target_port_name / source_port_name
   （从 target_anchor.port_name 提取）
3. 更新 target_node 的 config.json：
   - port_name == "default" 或 None → listen_upper_file = source_path
   - port_name == "prompt"/"context"... → port_mappings[port_name] = source_path
4. 更新 source_node 的 config.json：
   - out_connections[source_port_name] = target_name|target_port
5. _save_timer.start(500) → 触发布局保存
```

**删除连线**：`remove_edge(edge)` → 从 config.json 中清除对应端口映射

### 4. 菜单系统（canvas_menus.py）

完全由 **Action 系统**驱动：
```python
# 画布右键菜单（无选中节点）
canvas_actions = ActionFactory.get_canvas_actions()
# 节点右键菜单（选中节点后）
node_actions = ActionFactory.get_node_actions()
# 由 menu_manager 渲染
```

**Action 列表**（50+ 个 Action）：
- 画布级：new_node / import_node / batch_clear / save_layout / export_image...
- 节点级：start/stop/restart / open_folder / config_dialog / switch_style / delete...
- 视窗级：zoom_in / zoom_out / fit_view / reset_view / toggle_draw...

### 5. 批量操作（canvas_batch_ops.py）

```python
batch_start_all_nodes()    # 启动所有节点（异步，不阻塞 GUI）
batch_stop_all_nodes()     # 停止所有节点
batch_clear_listen_config() # 清除所有节点的 listen_upper_file 和 port_mappings
```

### 6. 绘图层（draw_layer.py）

在画布上叠加一层 `QGraphicsPixmapItem`，支持手绘/擦除/标注。
由 `draw_toolbar.py` 控制工具切换（画笔/橡皮擦/颜色/线宽/清除）。

**工具状态持久化**（V2.0.8+）：工具栏显示状态写入 `app_config.json`，重启恢复。

---

## ⚙️ 配置文件

### canvas_layout.json（项目级）

```json
{
  "nodes": {
    "node_python_1": {"x": 100, "y": 200, "width": 140, "height": 80, "style": "rect"},
    "node_python_2": {"x": 400, "y": 200, "width": 140, "height": 80, "style": "detailed"}
  },
  "edges": [
    {"source": "node_python_2", "target": "node_python_1",
     "source_port": "default", "target_port": "default"},
    {"source": "node_python_3", "target": "node_python_1",
     "source_port": "default", "target_port": "prompt"}
  ],
  "view_state": {"scale": 1.0, "scroll_x": 0, "scroll_y": 0, "center_x": 0, "center_y": 0},
  "canvas_size": {"width": 4000, "height": 3000},
  "toolbar_visible": false
}
```

### nodes/<node_name>/config.json（节点级）

```json
{
  "name": "node_python_1",
  "language": "python",
  "listen_upper_file": "../node_python_2/output.json",
  "port_mappings": {
    "prompt": "../node_python_3/output.json",
    "context": "../node_python_4/output.json"
  },
  "out_connections": {
    "default": "node_python_1|prompt"
  },
  "input_ports": [
    {"name": "default", "type": "default", "source": "node"},
    {"name": "prompt", "type": "string", "source": "node", "required": true},
    {"name": "context", "type": "string", "source": "node"}
  ],
  "parameters": [
    {"name": "max_tokens", "type": "int", "label": "最大 Token 数", "default": 2048}
  ],
  "custom_bg_color": "#2d2d30",
  "status": "stopped"
}
```

---

## 🔄 数据流

```
用户拖拽节点 → NodeItem.setPos()
                ↓
    NodeCanvas.scene().changed（信号）
                ↓
    _save_timer.start(500) ← 延迟保存，防抖
                ↓
    save_layout(current_project_path)
                ↓
    写入 <project>/canvas_layout.json


用户创建连线 → canvas_connections.create_edge()
                    ↓
    EdgeItem(..., target_port_name="prompt") ← 记忆端口名
    ↓                                   ↓
edge.end_anchor = target_anchor    edge._desired_target_port_name = "prompt"
    ↓                                   ↓
target_anchor.add_edge(edge)      （用于锚点重建后的重绑定）
                    ↓
    更新 target_node.config.json（port_mappings）
                    ↓
    _save_timer.start(500) → save_layout


切换节点样式 → node_item._switch_node_style("detailed")
                    ↓
    _style.apply(self) → _build_detailed_view()
                    ↓
    anchor_manager.build_from_config(config, _param_row_positions, w, h)
                    ↓
    1. 收集旧锚点上的 edges → old_input_edges = [(port_name, edges), ...]
    2. 销毁旧锚点
    3. 创建新锚点（default + prompt + context...）
    4. 遍历 old_input_edges:
         new_anchor = input_anchors.get(port_name)
         if new_anchor: edge.end_anchor = new_anchor; new_anchor.add_edge(edge)
                    ↓
    _validate_edge_anchor_binding() ← 兜底检查
```

---

## ⚠️ 关键约束与修复历史

| Issue | 影响版本 | 修复版本 | 修复说明 |
|-------|---------|---------|---------|
| load_layout 被调用两次 | ≤ V2.0.8 | V2.0.9 | `main_window._auto_open_project` 和 `project_manager.project_open` 中各调用一次 → 第二次调用时锚点已重建，edges 重复创建 |
| 锚点位置依赖 Qt 布局几何 | ≤ V2.0.9 | V2.0.10 | `_build_detailed_view` 中 `item.geometry()` 在布局完成前返回空 → 使用 `est_ys[i]` 估算 y 坐标兜底 |
| Edge 重建后绑定到错误锚点 | ≤ V2.0.9 | V2.0.11 | `edge.end_anchor` 可能引用已销毁的旧锚点 → `_desired_target_port_name` 记忆原始端口名，`_validate_edge_anchor_binding` 用它重新查找 |
| 指定端口锚点缺失时 fallback 到 default | ≤ V2.0.10 | V2.0.11 | `get_input("prompt")` 返回 None 时，EdgeItem 绑定到 `input_anchor` → 增加"不降级"保护：指定了端口名但找不到锚点时，保持 None 并警告 |
| canvas_layout.json 被错误改写 | ≤ V2.0.10 | V2.0.11 | 保存时从 `end_anchor.port_name` 取端口名，而 edge 已错绑到 default → 通过期望端口名机制 + 加载期跳过策略解决 |
| 自动保存在加载过程中触发 | ≤ V2.0.10 | V2.0.11 | `load_layout` 开头添加 `_save_timer.stop()`，防止保存损坏状态 |

---

## 📖 相关文档

- [Items 模块详细说明](items/README.md)
- [Multi-Anchor 重构计划](../docs/MULTI_ANCHOR_REFACTOR_PLAN.md)
- [Canvas 拆分报告](CANVAS_SPLIT_REPORT.md)
- [更新日志](../../docs/changelogs/README.md)

---

## 🔧 调试提示

1. **连线没绑定到指定端口**：检查 `EdgeItem._desired_target_port_name` 是否被正确设置，以及 `target_node.anchor_manager.input_anchors` 中是否有对应端口名的锚点
2. **锚点未创建**：检查 `node._param_row_positions` 中是否有该端口的位置条目，以及 `config.input_ports` 中 `source` 是否为 `"node"`
3. **canvas_layout.json 被改写**：检查 `_save_timer` 是否在加载过程中触发，搜索 `save_layout` 调用链，查看 `edge.end_anchor.port_name` 的实际值
4. **样式切换后连线悬空**：`_validate_edge_anchor_binding` 中 `edge.end_anchor.scene()` 为 `None` → 说明锚点对象已被销毁，需用 `_desired_target_port_name` 重新查找
