# EdgeKey 线条权威一致性（配置 ↔ UI 双向闭环）开发方案

## 一、方案背景（用户遇到的 4 个真实 Bug）

| # | Bug 描述 | 根因（已通过代码调研确认） |
|---|---|---|
| **Bug A** | 独立节点 E 连接复合节点 C（接收）→ 删除连线 → **C 的 composite.json external_connections.input 没有被清除**（下次启动项目又回来，或者被新的连线覆盖才变） | `clear_input_routing` 清了内存 `_port_routing` 后只触发 300ms debounce 写 composite.json；用户 300ms 内关项目/切项目就没写。见 [composite_node.py:L379-386](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/node/composite_node.py#L379-L386) + [L397-409 debounce 300ms](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/node/composite_node.py#L397-L409) |
| **Bug B** | 画布上存在**幽灵线条**：UI 有边但配置里 `listen_upper_file`/`external_connections` 没有任何上游节点 output.json 路径记录 | `EdgeItem.paint` 完全不查配置就渲染（只要 QGraphicsItem 可见就画），见 [edge_item.py:L443-510](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/items/edge_item.py#L443-L510) |
| **Bug C** | 项目重启后幽灵线条长期存在：重启按 `canvas_layout.json` edges 直接 `EdgeItem(...) + scene.addItem`，**不经过 create_edge 链路，不写任何配置**，导致画布有边但配置完全没边 | `load_layout` L393-410 绕过配置直接重建边；只做"配置→画布补"单向兜底，不做"画布→配置"反向裁剪。见 [canvas_layout.py:L393-410](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/mixins/canvas_layout.py#L393-L410) + [L415-458 单向兜底](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/mixins/canvas_layout.py#L415-L458) |
| **Bug D** | 展开复合节点 → 手动连接收端子节点到外部节点（写入 listen_upper_file）→ **折叠会丢失线条**；再展开重新连接子节点提示"已连接" | expand/collapse morph 过程中临时 edges 绕过 `connections.create_edge` 直接加 scene；morph 结束清理 `_morphed_edges = []` 时只清空列表，**没有真正从 scene/edges 移除**，留下 ORPHANED。见 [composite_node.py:L1149-1286](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/node/composite_node.py#L1149-L1286) |

### 补充：2026-07-15 用户最新反馈 3 类循环现象（编号 E/F/G）= 本方案要**特别增补的阶段**

| # | 用户最新现象（原文） | 直接根因（2026-07-15 通过代码调研确认） | 对应修复阶段 |
|---|---|---|---|
| **Bug E** | 节点 a→b，选 ab 右键"清除连线配置" → 正确清 2 个；但 a→c 时还是选 ab → 提示清 1 个（只清了 a.out_connections），**c.listen_upper_file 里还留着 a 的路径**。 | [canvas_batch_ops.py:L278-L331](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/mixins/canvas_batch_ops.py#L278-L331) 的 `batch_clear_listen_config`：①只对**选中集合**内部的节点清自己的 listen_upper_file，**不会把选中集合里作发送端的节点 → 其下游**未被选中**接收端的配置清掉**；② remove_edge 也只移除 target_name 在选中集里的边，a→c 边 target=c 不在 {a,b}，根本没触发 remove_edge→_clean_target_config(c)。 | **阶段 3.3（新增）** |
| **Bug F** | ①a 连折叠态复合节点 C → 展开后 UI 线条自动跳到 C 的接收端子节点，但子节点 listen_upper_file **没有 a 的路径**；②反过来：先展开 C，a 连接收端子节点（子节点 listen_upper_file 写了路径）→ 折叠后 UI 边在，但 composite.json **没写入 a 的路径**。 | expand/collapse morph 是"单向走 UI 替换"：①expand morph 只把 external→composite 边 `scene.addItem` 成 external→child，**没有把 `_port_routing.input[port]` 反向同步写子节点 listen_upper_file**；②collapse morph 只把 external→child 边替换成 external→composite，**没有把子节点 listen_upper_file 反向抄回 composite._port_routing.input**。两边各走一条路径，从不互通。见 [composite_node.py:set_input_routing](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/node/composite_node.py#L353-L363)（只在折叠态 connect 时调用，morph 不调用）。 | **阶段 4.1（6 条双向同步链路第 1/2/3 条）** |
| **Bug G** | Bug F 的循环版：先展开 C → a 连接收端子节点（子 listen_upper_file 写 a）→ 折叠 → 删 a→C 这条折叠态边 → 展开发现 UI 边真删了 **但子 listen_upper_file 还留 a** → 再连 a→子 提示"端口已连接" → 折叠再展开又自动连上 → 删边 这次能清子 listen_upper_file → 但**再次连接依然提示已连接**。 | 叠加 3 处清理缺漏：①折叠态删除 a→C 时 remove_edge 走的是 clear_input_routing(C, in_port)，本来因为 Bug F composite.json 里就空 → **清了个空气**；②remove_edge 的 _clean_target_config 传入 target_name 是 C（复合节点本体）→ 不会深入内部去把对应子节点 listen_upper_file 清；③"端口已连接"来源是 **锚点._edges 引用集合 + NodeStateManager 内存 ConnectionSM.upstream_state / _edge_keys**，这 3 处因为 expand morph 没走权威 remove_edge 链路，导致内存状态残留 → 即使配置清了也报"已连接"。 | **阶段 4.2 + 4.3（6 条链路第 4/5/6 条 + 锚点/内存四地同步）** |

本方案引入 **EdgeKey（结构化唯一线条 ID）+ 「配置文件是唯一权威源 SSOT」+ 配置↔UI 双向闭环 + expand/collapse morph 6 条互通链路**，一次性解决 A~G 全部 7 类 bug 以及线条长期存在的"配置不一致"问题。

---

## 二、方案核心设计

### 2.1 三大设计原则

1. **配置权威（SSOT）**：一条线条"是否真实存在"的**唯一判定标准** = 对应配置文件里是否有合法的**上游节点 output.json 路径记录**。`canvas.edges[]`、`canvas_layout.json.edges[]`、`scene.items()` 只做 UI 缓存，**不做权威判定**，不一致时立即以配置为准裁剪。
2. **EdgeKey 一一映射**：每条线条在系统中有唯一的结构化 ID（EdgeKey），能从 EdgeKey 推导出「上游 output.json 路径 + 下游配置文件路径 + 配置字段」，也能从配置全量反推出应有的 EdgeKey 集合（CanonicalEdgeSet）。
3. **双向闭环**：
   - 正向：UI 操作（拖线 / 删除线 / expand / collapse / undo / redo） → **先写配置（原子）** → 成功后再改 UI（加边 / 删边 / morph）
   - 反向：节点入画布、项目打开、配置外部修改、3s 扫描 → **用 CanonicalEdgeSet 对比画布** → 补「配置有 UI 没」+ 裁「UI 有配置没」

### 2.2 复合节点 output 字段差异 & 5 种 routing_type（关键！你最关心的点）

复合节点的 output 存储字段**完全不同于普通节点**，在 EdgeKey 中以首字段 `routing_type` 区分 5 类线条，每类对应独立的「配置读写 / 路径解析 / 清除」链路：

| routing_type | 典型连线 | ① 上游 output.json 真实路径（权威判定时解析） | ② 创建边时写哪些配置（正向） | ③ 删除边时清哪些配置（反向） |
|---|---|---|---|---|
| **STANDALONE** | 普通 A → 普通 B | `nodes[A目录]/output.json`（用 `nodes_data[A].path` 拼） | 下游 B：`node_config.json.listen_upper_file`（单入）或 `port_mappings{in_port: path}`（多入）<br>上游 A：`node_config.json.out_connections{out_port: "B|in_port"}` | 下游 B：del listen_upper_file / port_mappings[in_port]<br>上游 A：del out_connections[out_port] |
| **COMPOSITE_OUTPUT** | 复合 C → 普通 B | **不是 C 目录下的 output.json！** 而是：① 用 `_find_internal_by_port(C, out_port, "output")` / `_find_exit_node(C)` 解析出 C 内部**出口子节点 out_x** → ② 用 `out_x` 的 path 拼路径 → `nodes/复合C目录/子节点目录out_x/output.json`（见 [canvas_connections.py:L487-505](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/mixins/canvas_connections.py#L487-L505) 真实实现） | 下游 B：`node_config.json.listen_upper_file`/`port_mappings{}`（指向上面的 out_x 真实 output）<br>上游 C：`_port_routing.output[out_port]` → debounce + **立即同步** 到 `compositeC/composite.json.external_connections.output[out_port]` | 下游 B：del listen_upper_file / port_mappings[in_port]<br>上游 C：`clear_output_routing(C, out_port)` **+ 立即同步 composite.json**（修 Bug A 的 debounce 问题） |
| **COMPOSITE_INPUT** | 普通 E → 复合 C | `nodes[E目录]/output.json` | 上游 E：`node_config.json.out_connections{out_port: "C内部入口子节点名|in_port"}`（见 [canvas_connections.py:L572-586](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/mixins/canvas_connections.py#L572-L586)）<br>下游 C：`set_input_routing(C, in_port, E_output_path)` → debounce + **立即同步** 到 `compositeC/composite.json.external_connections.input[in_port]` | 上游 E：del out_connections[out_port]<br>下游 C：`clear_input_routing(C, in_port)` **+ 立即同步 composite.json**（修 Bug A 核心） |
| **COMPOSITE_INTERNAL** | 复合 C 内部 子节点 X → 子节点 Y | `nodes/C目录/子节点X目录/output.json` | 子 Y：`listen_upper_file` / `port_mappings{}`<br>子 X：`out_connections{}`<br>+ 同步到 `compositeC/composite.json.edges[]` DAG 拓扑 | 双向 del + del from composite.json.edges[] |
| **STANDALONE_PORT_MAP** | 普通 A → 普通 B 非默认输入口 | `nodes[A]/output.json` | 下游 B：`port_mappings{in_port: path}`<br>上游 A：`out_connections{out_port: "B|in_port"}` | 双向 del port_mappings[in_port] + out_connections[out_port] |

**特殊补充「复合互连线（C1→C2）」**：同时命中 COMPOSITE_OUTPUT+C1 和 COMPOSITE_INPUT+C2，上游走 COMPOSITE_OUTPUT 链路，下游走 COMPOSITE_INPUT 链路，两端的内部子节点各自解析，**中间不涉及任何普通节点 node_config.json**。

---

## 三、核心数据结构

### 3.1 EdgeKey（线条结构化唯一 ID，存在每条 EdgeItem._edge_key 上）

```python
EdgeKey = tuple[
    str,   # 1. routing_type: STANDALONE | COMPOSITE_OUTPUT | COMPOSITE_INPUT | COMPOSITE_INTERNAL | STANDALONE_PORT_MAP
    str,   # 2. upstream_node_name   （a 节点名：普通节点名 或 composite_xxx）
    str,   # 3. downstream_node_name （b 节点名：普通节点名 或 composite_xxx）
    str,   # 4. upstream_port        （上游出口端口，默认 "default"）
    str,   # 5. downstream_port      （下游入口端口，默认 "default" / COMPOSITE_INPUT 默认可能是 "data"）
]
```

**派生属性（不存 EdgeKey，运行时实时解析，防路径失效）**：
- `upstream_output_path: str` —— 按 2.2 节①的规则从 EdgeKey + nodes_data + composite_manager 实时算出（这就是你说的"edge_id 存上游 output 路径"，但用推导而非硬编码，避免项目换目录后 edge_id 永久失效）
- `downstream_config_path: str` —— 下游配置文件绝对路径（`node_config.json` / `composite.json`）
- `downstream_config_fields: list[tuple[str, str | None]]` —— 要写/清的 json 路径（例：`[("node_config", "listen_upper_file"), ("node_config", "port_mappings.data")]`）

### 3.2 CanonicalEdgeSet（权威边集合 = 配置反推出来的所有应存在的 EdgeKey 集合）

由新组件 `CanonicalEdgeResolver.infer_all_edges(project_path, nodes_data, composite_manager) -> set[EdgeKey]` 计算，是「反向闭环补边/裁边」的唯一输入。**它和 Canvas 上的 EdgeKey 集合按 2.2 节的 rules 做 diff 产生：补边集 + 裁边集**。

---

## 四、阶段化开发步骤（从最痛的 Bug A 开始，每步都可独立验收 + 回滚）

### 阶段 0：复合路由立即持久化（修 Bug A，半天，最高优先级） **✅ [已完成 2026-07-14]**

**目标**：删除外部→复合 / 复合→外部连线时，composite.json.external_connections 立即被写入，不再依赖 300ms debounce。
- 修改文件：[composite_node.py](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/node/composite_node.py)
- 改动点：
  1. `set_input_routing` L361、`set_output_routing` L377、`clear_input_routing` L386、`clear_output_routing` L395 —— 在 `save_debounced() + _sync_routing_debounced(comp_id)` 之后，**立即追加一行** `self._sync_routing_to_config(comp_id)`（同步写入 composite.json，debounce 留作兜底）
  2. `_sync_routing_to_config` L417 之前加一行日志：`logger.info("[COMPOSITE-ROUTE-SYNC] %s routing=%s", comp_id, routing)`，便于观察阶段 0 的写入是否真的立即发生。
- 验收：
  1. 外部 E 连复合 C（接收端）→ 立即看 `composite_C/composite.json.external_connections.input` 有 E/output.json
  2. **删除这条线（<300ms 内就 Ctrl+S 或关项目再打开）** → composite.json.external_connections.input 这条路由真的消失了（如果没立即同步就还在，说明没修好）

### 阶段 1：EdgeKey 定义 + 挂到现有 EdgeItem（1 天） **✅ [已完成 2026-07-14]**

**目标**：每条 UI 线条都有结构化 EdgeKey；在 create_edge/remove_edge 时赋值/销毁。
- 新增文件：`ui/core/edge/edge_key.py`
  - 定义 5 种 `ROUTING_TYPE_*` 常量
  - 定义 `make_edge_key(routing_type, up, down, up_port="default", down_port="default") -> EdgeKey`
  - 定义 `edge_upstream_output_path(key, nodes_data, comp_manager) -> str` 和 `edge_downstream_targets(key, nodes_data, comp_manager) -> list[tuple[config_path, json_path]]`（对应 2.2 节 ①③ 规则，5 类 routing_type 全覆盖）
- 修改文件：
  - `ui/canvas/items/edge_item.py`：给 EdgeItem 加 `_edge_key: EdgeKey | None` 属性，默认 None；`from_dict/to_dict` 要保存/加载 EdgeKey（存 5 个字段，不存派生路径）
  - `ui/canvas/mixins/canvas_connections.py`：`create_edge` L360 创建 EdgeItem 前，**先按 is_composite_source/is_composite_target + 端口名**算出 routing_type 和 EdgeKey，赋值给 `edge._edge_key = key`；同时在 NodeStateManager 里记录 `_edge_keys: set[EdgeKey]`。
- 验收：
  - 打开项目，日志里能看到 `[EDGE-KEY ASSIGN] key=...` 每条边都有合法 EdgeKey。
  - 5 类 routing_type 的 `edge_upstream_output_path()` 单测：返回路径和当前 create_edge 实际写入 listen_upper_file 的路径 **100% 字节相等**。

### 阶段 2：正向闭环（UI 操作 → 先原子写配置 → 后改 UI）修 undo/redo（2 天） **✅ [已完成 2026-07-14]**

**目标**：所有改线条的 UI 入口（create_edge / remove_edge / undo / redo / expand / collapse morph）全部走「先原子写 RouteCache → 成功再改 scene/edges」链路，不再 open/write 零散文件。
- 复用 `ui/core/state/route_cache.py` 已有的 RouteCache / Transaction。
- 新增 `ui/core/edge/edge_config_writer.py`：
  - `write_edge_config(key, ...) -> None`：按 routing_type 分 5 类，把配置写到 RouteCache 暂存区
  - `clear_edge_config(key, ...) -> None`：按 routing_type 分 5 类，清配置写 RouteCache
  - `flush_atomic()`：`RouteCache.extract_pending() + 一次性 flush 所有文件`（全成功或全回滚）
- 修改文件：
  - `canvas_connections.py`：create_edge → 先 `write_edge_config()` → `flush_atomic()` 成功 → 再 `EdgeItem + addItem + append`；remove_edge 先 `clear_edge_config() + flush_atomic()` 成功 → 再 removeItem + remove edges。
  - 阶段 0 里 composite 路由立即同步：因为 writer 里会直接 `_sync_routing_to_config`，不再靠 debounce。
  - `ui/core/commands/edge_commands.py`：`DeleteEdgeCommand.undo` 不再 new EdgeItem，改为**调 `connections.create_edge(..., _from_undo_redo=True)`**（走完整 write+flush 链路）；`CreateEdgeCommand.undo` 调 `connections.remove_edge(..., _from_undo_redo=True)`。
- 验收：
  - 连 5 类边 → 立即断网 / kill python 进程模拟崩溃 → 重启后所有 5 类边的配置和 UI 要么都存在（commit 前没崩）要么都不存在（commit 中崩，原子回滚），**绝不出现"只写了 B.listen_upper_file 没写 A.out_connections"**。
  - undo/redo 10 次循环，配置文件 diff 为 0（最终状态等于初始状态）。

### 阶段 3：反向闭环 + 渲染门（修 Bug B 幽灵线条 + Bug C 重启保留幽灵，3 天） **🔄 [进行中 2026-07-14]**

**目标**：实现「配置 → UI」的 3 大触发点补边 + 裁边；EdgeItem.paint 前渲染门（INVALID 边不画 + 告警）。
- 新增 `ui/core/edge/canonical_edge_resolver.py`：
  - `infer_all_edges(project_path, nodes_data, comp_manager) -> set[EdgeKey]`（按 2.2 节①规则，读所有 node_config.json + composite.json 反推 CanonicalEdgeSet）
- 三大反向闭环触发点：
  1. **`add_node_to_canvas`（拖节点进画布时）**：查 CanonicalEdgeSet 中已把该节点作为 downstream / upstream 的 edge_key → 自动调 `create_edge(..., _from_config_infer=True)` 画出来。
  2. **项目打开 `load_layout` 末尾**：
     - ① 算 CanonicalEdgeSet
     - ② 算 CanvasEdgeSet（现有每条 edge._edge_key 集合）
     - ③ `missing = canonical - canvas` → 自动 create_edge（**跳过已有边**）
     - ④ `ghost = canvas - canonical` → **从 canvas.edges 移除 + scene.removeItem + 打 [EDGE-PURGE load_layout] 日志**（修 Bug C 关键！之前只做③不做④）
  3. **QTimer 3s 弱扫描**：只做 diff + 日志计数（不删不补），用于上线前灰度观察差异率。
- 渲染门：修改 `edge_item.py` 的 `paint` 开头（[edge_item.py:L443](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/items/edge_item.py#L443)）：
  ```python
  # 渲染门（灰度）：先只打告警不 return，观察 1~2 周无误报再 return 不画
  key = getattr(self, "_edge_key", None)
  if key is not None:
      mgr = getattr(self.canvas, "_edge_state_mgr", None)
      if mgr and not mgr.is_edge_valid(key):
          logger.warning("[EDGE-GHOST DETECTED] key=%s not in canonical edges, would skip paint", key)
          # TODO 灰度后：return（真不画）+ 调 purge_single(key)（真删除）
  ```
- 验收：
  - 手动破坏 1 个配置（比如把 B.listen_upper_file 删掉）→ 3s 扫描出现 [EDGE-GHOST] 告警 → 下一次 load_layout 时这条边被真正删除。
  - 手动加配置（比如给 B.listen_upper_file 写 A/output.json）→ 下一次拖 B 进画布时，线条自动出现。
  - 3 天灰度日志 `EDGE-GHOST DETECTED` < 0.1% 连线操作。

### 阶段 3.3：批量清除连线配置的双向同步 + 作用域修复（修 Bug E，0.5 天） **❌ [未开始]**

**目标**：右键"清除连线配置"时，不仅清除选中集合自己作为接收端的 listen_upper_file，还要**跨选中集清除两端配置**，保证"UI 边被删 = 上下游配置双向都被清"。

- 修改 [canvas_batch_ops.py:L278-L331](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/mixins/canvas_batch_ops.py#L278-L331) `batch_clear_listen_config`：
  - **先不直接改配置**：改为「先收集和选中节点相关的所有真实 EdgeKey」→ 对每条 EdgeKey **直接复用 `EdgeConfigWriter.plan_remove_edge` + commit**，走权威原子写链路，不要手动 open/write json。
  - 选中集关联边收集规则（双向覆盖，解决 Bug E）：
    - 对每条画布上的 EdgeItem：
      - `edge.start_node in selected  OR edge.end_node in selected` → 这条边**都必须进 remove_edge 集合**（不再只看 end_node in 集）
      - 其中：
        - 若 `edge.start_node ∈ selected ∧ edge.end_node ∉ selected`：也要删这条边 → 触发 `plan_remove_edge` 自动把**未选中的下游节点 listen_upper_file 清空**（修 Bug E 核心点 1）
        - 若 `edge.end_node ∈ selected ∧ edge.start_node ∉ selected`：删边 → 自动把**未选中的上游节点 out_connections 对应端口清掉**
        - 若两端都在选中集：照常删
  - `cleared_count` 统计改为：**实际成功调用 `plan_remove_edge` + commit 的 EdgeKey 数**，不再按配置字段数量计数（老计数方式把 out_connections 整体清空算 1 次，无法反映真实清了几条线）。
- 验收（Bug E 复现）：
  - ① 创建 a→b + a→c（两条独立连线）。框选 a、b → 右键清除连线配置。
    - 期望结果 1：a→b 被删；a→c 也被删（**即使 c 不在框选里也必须被删**，因为 a 是上游）。
    - 期望结果 2：打开 c.node_config.json → `listen_upper_file == ""`；a 的 `out_connections` 对应端口也被清空；画布上 a→c 边不复存在。
  - ② 反向：a→b + c→b，框选 a、b → c 的 out_connections 对应端口被清空，b.listen_upper_file 为空。
  - ③ 复合节点场景：a→复合 C（折叠态），框选 a → 必须触发 `CompositeManager.clear_input_routing(C, in_port)` + composite.json.external_connections.input[in_port] 清空（和阶段 0/2 原子写打通）。

### 阶段 4：expand/collapse morph「先删后建 + 配置互斥切换」机制（修 Bug D / F / G，5 天） **🔄 [方案二次修订 2026-07-15]**

**核心设计原则（新增，2026-07-15 用户方案采纳）**：**「配置存在的位置 = 画布上真实存在的边类型」，二者严格一一对应，两边互斥、绝对不同时写。**
- 折叠态：画布上是 `external → composite_C: in_port` → **只写 composite.json.external_connections / _port_routing**，内部子节点 `listen_upper_file / port_mappings` 必须**强制为空**。
- 展开态：画布上是 `external → internal_child_X` → **只写内部子节点 node_config.json**，composite.json 的对应 `in_port` 必须**强制精确清空**（只清这一个 in_port，不影响其他端口）。
- 任何时候 expand/collapse 切换视觉形态时：**先完整 DELETE 旧边（物理删除 UI 边 + 清对应配置 + 4 地内存注销） → 再完全 CREATE 新边（全新 EdgeKey + 写对应配置 + 4 地内存注册）**，不允许做"边对象复用 / 锚点 morph 平移保留原边对象"等任何保留旧身份的操作，从根本上消除"这条边到底是复合边还是子节点边"的身份歧义。

本阶段包含 7 条必须严格遵守的**强制约束**（缺 1 条就会复现用户刚报告的循环 Bug）：

| # | 强制约束（MUST） | 解决哪类现象 | 具体要求 |
|---|---|---|---|
| 1 | 事务包裹原子性 | expand/collapse 中途崩溃导致"旧边被删新边没建" | 每一次 expand 或 collapse 必须包一层：① `QUndoStack.beginMacro("Expand " + comp_id)` 把 remove_edge+create_edge 合成 1 个 undo 原子；② `RouteCache.begin_transaction(tx_owner="expand:comp_id")` 把清旧配置 + 写新配置合成 1 个磁盘写入原子，失败回滚两边都不变。 |
| 2 | 配置互斥 + 精确端口清理（不能整体删字段） | 清一个 in_port 时把其他 in_port 也误清；或两边同时写造成不一致 | expand 时对每个 in_port：`clear_input_routing(comp_id, in_port_X)` **只清这一个端口**（不能 del comp._port_routing.input）；collapse 时对每个子节点：`RouteCache.set_listen_upper_file(child_path, "") + set_port_mapping(child_path, in_port, {})` **只清该子节点对应端口**。**绝不允许 composite.json in_port 值与 internal listen_upper_file 值同时非空且指向同一 upstream**。 |
| 3 | 权威判定来源：**配置文件 + MembershipSM，绝不扫 scene.items() 找边** | 幽灵边 / morph 中途临时隐藏边造成误判 | expand 前读 `comp._port_routing.input[in_port].target_node/target_port` 找出要建的 internal 边；collapse 前遍历 `MembershipSM(comp_id).child_node_names` 的**磁盘 node_config.json** 读 `listen_upper_file / port_mappings / out_connections` 找出要建的 composite 边。**禁止遍历 canvas.items() / scene.items() 作为 morph 的输入。** |
| 4 | 按端口维度批量处理，不逐条边处理 | 1 个 in_port 映射到 2 个子节点（N:1）漏处理；1 个复合节点多个 in_port 漏处理 | expand 时遍历 `_port_routing.input` 每个 in_port → 每个 in_port 可能多条 target 映射 → 每条映射独立 remove+create；collapse 时遍历所有子节点配置 → 每个子节点多条 upstream 映射独立 remove+create。出向 output 与入向完全对称，必须同时处理。 |
| 5 | **出向（comp 作为发送端）对称先删后建** | 展开后下游边的锚点挂在复合 C 上，出口子节点锚点是空的，看起来线"悬空" | 折叠态 `EdgeKey(COMPOSITE_OUTPUT, C, external_B, out1, default)`：expand 时先 remove_edge(C→B) + 清 comp._port_routing.output[out1] → 再 create_edge(internal_child_out → B) + 写 internal_child_out 的 out_connections[out_port] + B.listen_upper_file。collapse 完全反向。 |
| 6 | 删除链路 2 个深入钩子（与"互斥原则"互补，防止 morph 外的手动删除遗漏） | Bug G：删折叠态 a→C → 子节点配置还留；展开删 a→子 → 折叠后还残留 | 在 `remove_edge` 非 morph 场景加 2 个钩子：**删除 external→comp 时**根据 port_routing[in_port].target_node/target_port 深入把对应子 listen_upper_file 也清；**删除 external→internal_child 时**反查所属 comp_id + 反查匹配的 in_port → 把 comp._port_routing.input[in_port] 也清 + 同步 composite.json。 |
| 7 | **4 地内存永远走同一权威链路（禁止 scene.addItem/removeItem 直操）** | Bug G："端口已连接"假阳性（anchor._edges 没清）；morph 后 _edge_keys 与配置不一致 | expand/collapse 增删边、undo/redo 增删边、任何其他地方增删边 → **一律只能调 canvas_connections.create_edge / remove_edge 同一个函数**，保证：① anchor._edges；② NodeStateManager._edge_keys；③ ConnectionSM.upstream_state + metadata；④ RouteCache + 磁盘配置 —— 4 处永远一起走 register/unregister 链路，不允许直接操作任何 1 地。 |

---

#### 4.1.0 前置：两种「清空配置展开」场景澄清 + 4 种权威判定来源（回答：**"清空后如何判断外部节点是谁 + 该写入谁的路径"**）

**先澄清你问题的两种可能含义（含义 1 是互斥方案的核心顺序漏洞，必须先理解再实施）**：

| # | 你说的"清空配置展开"是什么 | 如何判断外部节点 + 写入什么路径 |
|---|---|---|
| **含义 1（互斥方案的正常流程，99% 情况）** | expand 流程按步骤 2 **主动精确清空 composite.json 对应 in_port** 后，步骤 3 需要创建子节点 listen_upper_file，此时从哪里拿 upstream + output 路径？ | **顺序修复：必须严格执行「三阶段分离」**：**先全量收集 morph_list 到局部内存变量（此时 comp 配置/UI 边/EdgeKey 全部完好未清，什么都能拿到） → 再统一删除旧边 + 统一清旧配置 → 最后统一创建新边 + 统一写子节点配置**。所有"外部节点是谁/写入什么路径"的信息，都来自阶段 A 收集好的 `morph_list` 局部 dict，**不从已清空的配置读**（§4.1.1 里的三阶段表格就是这个顺序，执行时一条都不能乱）。 |
| **含义 2（极端边界场景，极小概率）** | 用户/脚本手动把 composite.json.external_connections **全删了 + 所有子 node_config.json listen_upper_file 也全清了**，然后再点 expand。 | 没有配置就没有边 → **判断"没有任何外部节点要连"**。morph_list 是空的，expand 只显示子节点 UI，**不产生任何新连线、不写任何 listen_upper_file**。不存在任何"凭空猜外部节点是谁"的机制。**互斥断言此时会通过（两边都空=允许的互斥状态之一）**。 |

**4 种权威判定方式（每种用于不同时机；expand 场景唯一推荐第 ① 种）**：

| # | 判定方式 | 核心真相来源 | 适用时机 | 输出（你要的两个答案） |
|---|---|---|---|---|
| ① ✅ **唯一推荐（expand 场景权威）** | 从 `composite._port_routing[in_port].source_output_path` 直接拿路径 + 反查 nodes_data 全局注册表 | composite.json._port_routing.input[in_port]（expand 前完好未清的内存值） | **expand 步骤 1 阶段 A 收集 morph_list 时** | • **外部节点是谁** = `edge_resolver.path_to_edge_endpoint(source_output_path, nodes_data_global).upstream_node_id`<br>• **写入什么路径** = `source_output_path`（原封不动抄到内部子节点 listen_upper_file / port_mappings） |
| ② | 从子节点配置 `listen_upper_file` / `out_connections` 读路径，再反查 nodes_data | 所有 MembershipSM(comp_id).child_name 对应的**磁盘 node_config.json** | **collapse 步骤 1 阶段 A 收集时** | • **外部节点是谁** = `path_to_edge_endpoint(child.listen_upper_file).upstream_node_id`<br>• **写入 composite 什么路径** = 直接就是 `child.listen_upper_file` 原封不动写进 `composite._port_routing[in_port].source_output_path` |
| ③ | 从 ConnectionSM._upstream_metadata 拿内存中已注册的连接 | `NodeStateManager.get_connection_metadata(comp_id)[in_port]`（create_edge 时写入） | **阶段 4.2 删除链路深入钩子**（用户手动删 external→comp 不走 expand/collapse 流程时，深入清对应子配置用） | • target_node / target_port 直接从 metadata 读 → 直接去把子 listen_upper_file 清空 |
| ④（兜底/定时扫描用） | 从 EdgeKey + nodes_data 双查 | EdgeKey 5 元组 (routing_type, src, dst, src_port, dst_port) | load_layout 后/校准线条按钮点击时 diff 验证用 | • 外部节点是谁 = EdgeKey.src<br>• 路径 = nodes_data[src].output_paths[src_port]（**expand 场景不推荐作为权威来源**，因为 expand 前我们要 morph 的正是这些 EdgeKey 对应的边，马上要被删除，可能与 comp._port_routing 不一致） |

**第 ① 种判定方式的落地伪代码（必须在 expand 清配置之前执行并保存到局部变量）**：
```python
def collect_expand_morph_list(comp_id, composite_manager, nodes_data_global, edge_resolver) -> list[dict]:
    """
    expand 步骤 1 阶段 A：在 comp._port_routing 还未被清空的时机，全量抄一份 morph 计划到内存。
    返回的 morph_list 是 expand 函数内的局部变量，后续清磁盘/清内存配置都不会丢失它。
    """
    morph_list: list[dict] = []
    routing = composite_manager._get_port_routing(comp_id)

    # ====== 入向：external → comp.in_port ======
    for in_port, entry in routing.get("input", {}).items():
        source_output_path = entry.get("source_output_path", "")
        if not source_output_path:
            continue

        # STALE 路由跳过：source_output_path 指向的上游不在 nodes_data（节点被删）→ 不 morph，等下 purge_stale_routes 会统一清
        try:
            upstream_node_id, upstream_out_port = edge_resolver.path_to_edge_endpoint(
                source_output_path, nodes_data_global
            )
        except UpstreamNodeNotFound:
            logger.warning("[MORPH-SKIP-STALE] comp=%s in_port=%s upstream_path=%s not found in nodes_data — skip morph & mark stale",
                           comp_id, in_port, source_output_path)
            composite_manager.mark_routing_stale(comp_id, "input", in_port)  # 后续 purge 阶段会把这个 in_port 也清掉
            continue

        target_child_name = entry.get("target_node", "")
        target_child_port = entry.get("target_port", "default")
        if not target_child_name:
            logger.error("[MORPH-SKIP-NO-TARGET] comp=%s in_port=%s target_node empty — skip", comp_id, in_port)
            continue

        morph_list.append({
            "direction": "input",
            "in_port": in_port,
            "upstream_node_id": upstream_node_id,       # ← 答案 1：外部节点是谁
            "upstream_out_port": upstream_out_port,
            "source_output_path": source_output_path,   # ← 答案 2：写入子 listen_upper_file 的值
            "target_child_name": target_child_name,
            "target_child_port": target_child_port,
        })

    # ====== 出向：comp.out_port → external 对称处理 ======
    for out_port, entry in routing.get("output", {}).items():
        ...  与入向完全对称：target_output_path → 反查 downstream_node_id / downstream_in_port
    return morph_list
```

**STALE 无效路由的处理规则（expand 期间遇到死端口的决定）**：
- 上游节点已从画布删除 / upstream_node_id 不在 nodes_data 里：**跳过 morph，不创建新的 internal 边**，同时调 `composite_manager.mark_routing_stale` → expand 结束后 `purge_stale_routes` 钩子会把这个 in_port 从 composite.json 里清掉，避免无效路由永久膨胀（对应 §8.2 P1「定时自动清理无效路由」的内联版）。
- 上游节点在画布上但 output.json 文件不存在（节点还没跑过）：**照常 morph，照常写 listen_upper_file**（"未运行"不是"未连接"，是正常状态，上游运行后文件会自动生成，下游无需再手动连）。

---

#### 阶段 4.1：Morph 新机制落地 — expand 6 步 / collapse 6 步（修 Bug F ①②，2 天）

**目标**：用"先删后建 + 配置互斥交接"替换掉原来所有的「anchor morph 平移保留原边对象」代码。composite_node.py:_morph_composite 改为下面 2 套严格步骤：

> **执行铁律（阶段三严格分离，违反会出现你问的"清空后找不到上游"问题）**：
> **阶段 A（全量收集）→ 阶段 B（统一删除）→ 阶段 C（统一创建），三阶段必须完全独立分开执行**，禁止一条 morph 边在阶段 A 完成后立刻执行阶段 B/C（会导致同端口后续映射因 comp._port_routing 被提前清空拿不到上游信息；也会导致锚点状态变更被后续映射误判为重复连接）。

##### 4.1.1 Expand（展开复合 C）— 严格 6 步顺序执行（**三阶段 A/B/C 不可混合，禁止一条边 A 完立刻 B/C**）

```
步骤 0 [基础环境：包事务 + 包 undo 宏 = 双原子性保证]：
   QUndoStack.beginMacro("Expand " + comp_id)       # 保证 remove_edge+create_edge 多次子命令 = 用户视角 1 次 Ctrl+Z 回滚
   RouteCache.begin_transaction(tx_owner=f"expand:{comp_id}")  # 保证清 comp 配置 + 写子配置 = 磁盘 1 个原子写，失败回滚两边都不变
   ★ 事务隔离等级要求：整个 6 步期间，任何其他线程/用户操作对 comp 的配置写入要互斥（见 §8.3 ProjectFileLock）

===========================================================================
阶段 A 【步骤 1 = 全量收集，此时 comp 配置 / UI 边 / EdgeKey 全部完好未动】
===========================================================================
   morph_list = collect_expand_morph_list(comp_id, composite_manager, nodes_data_global, edge_resolver)
   ★ 阶段 A 只做只读操作，不写磁盘、不删 UI 边、不改任何内存集合
   ★ 【你问题的答案所在】：所有"外部节点是谁 + 写入什么路径"的信息，此时已经全量抄到了 morph_list 局部 dict 里，后续清配置不影响
   ★ STALE 无效路由（上游不在 nodes_data / target_node 为空）在阶段 A 跳过 morph，并 mark_routing_stale（阶段 B 之前 purge 钩子会清 composite 对应 in_port）

===========================================================================
阶段 B 【步骤 2 = 统一删除旧边 + 统一清旧配置 + 视觉移除复合本体】
        ★ 关键：整个阶段 B 里绝对不允许读 comp._port_routing 作为输入！要读只能去读 morph_list！
===========================================================================
   ① 先删 comp C → 外部出向边（先删出向防止 comp 隐藏后下游悬空）：
      for item in morph_list:
          if item["direction"] == "output":
              remove_edge(comp_id, item["out_port"],
                          item["downstream_node_id"], item["downstream_in_port"],
                          _from_morph=True, _skip_undo_push=True)
              # remove_edge(_from_morph=True) 内部保证执行 4 件事：
              #   anchor.remove_edge + NodeStateManager.unregister_edge + RouteCache.clear_output_routing(comp, out_port) + 从 canvas.edges 移除
   ② 再删外部 → comp C 入向边：
      for item in morph_list:
          if item["direction"] == "input":
              remove_edge(item["upstream_node_id"], item["upstream_out_port"],
                          comp_id, item["in_port"],
                          _from_morph=True, _skip_undo_push=True)
              # 内部清 comp._port_routing.input[in_port] = 精确空值（不影响其他 in_port）
   ③ 隐藏 comp C 本体的 UI 节点（hide()/从画布移除）—— 你提出的关键判断：
              "复合节点在画布上已经不存在了，所以复合的边 + 复合配置字段也必须被清除"
              此时已经完全做到：4 地内存集合里 external↔comp 的边全部注销；磁盘 composite.json 对应 in_port/out_port 全部精确清空

===========================================================================
阶段 C 【步骤 3 = 统一创建新边 + 统一写子节点配置（从 morph_list 读，不从已清空的 comp 读！）】
===========================================================================
   ① 建 internal_child ↔ 下游（出向）：
      for item in morph_list:
          if item["direction"] == "output":
              create_edge(item["child_source_name"], item["child_source_port"],
                          item["downstream_node_id"], item["downstream_in_port"],
                          _from_morph=True, _skip_undo_push=True)
              # create_edge 内部 4 件事：
              #   写 child.out_connections + 下游 listen_upper_file
              #   + anchor.add_edge + NodeStateManager.register_edge + 加入 canvas.edges
   ② 建上游 ↔ internal_child（入向）：【★ 这里写入子节点配置的路径 = morph_list[item]["source_output_path"]，原封不动抄】
      for item in morph_list:
          if item["direction"] == "input":
              create_edge(item["upstream_node_id"], item["upstream_out_port"],
                          item["target_child_name"], item["target_child_port"],
                          _from_morph=True, _skip_undo_push=True)
              # create_edge 此时：
              #   子 listen_upper_file = item["source_output_path"]（阶段 A 收集的那个，100% 和折叠前 comp.in_port 指向同一 upstream）
              #   或 target_child_port!="default" 时写 port_mappings[target_child_port]
              #   + ConnectionSM(internal_child).upstream_state = CONNECTED + anchor._edges 绑定 + _edge_keys 插入

步骤 4 [其余非 edge 行为]：子节点 UI 显示、位置计算、连线端点几何重算、comp C 的 anchor 隐藏

===========================================================================
步骤 5 [提交 + 失效缓存 + 互斥硬断言 + 4 地一致性断言 = fail-fast 两道闸门]
===========================================================================
   ① purge_stale_routes(comp_id) → 把阶段 A 标记的 stale in_port/out_port 从 composite.json 里清掉（无效路由永久不保留）
   ② RouteCache.commit() → 所有清 comp + 写子的配置文件变更一次性原子落盘
   ③ ConfigMtimeCache 失效：
        ConfigMtimeCache.invalidate(comp_config_path)
        for child in MembershipSM(comp_id).child_node_names:
            ConfigMtimeCache.invalidate(get_config_path(child))

   ④ 【第一道硬断言 · 互斥一致性】：_assert_mutex_consistency(comp_id, morph_list)
      断言规则（三选一，其他任何组合都 fail-fast）：
        - 展开态：composite.json.external_connections.input[in_port] 必空；
                  item["target_child_name"] 的 listen_upper_file / port_mappings[target_child_port] == item["source_output_path"]
        - 含义 2 两边都空：morph_list 为空，不写任何东西（断言允许）
      【彻底杜绝：两边同时写同一路径 = 互斥违背 = 后续 expand/collapse 循环歧义的根因】

   ⑤ 【第二道硬断言 · 4 地一致性】：
        canonical = canonical_resolver.infer_all_edges(project, nodes_data, comp_mgr)
        canvas_keys = {e._edge_key for e in canvas.edges if getattr(e,"_edge_key",None)}
        mem_keys    = node_state_manager.get_all_edges()
        assert canonical == canvas_keys == mem_keys

步骤 6 [结束 undo 宏]：QUndoStack.endMacro()
        → 从用户视角：Ctrl+Z 一次 = 整个 expand 操作整体回滚：
           子边删除 + comp 边恢复 + 子 listen_upper_file 清空 + comp.in_port 恢复
           （QUndoMacro 内部的 remove_edge/create_edge sub-command 会按顺序 reverse 执行）
```

**事务崩溃回滚验证（强制验收项）**：模拟 expand 阶段 B 完成后、阶段 C 未完成时 kill 进程（例如在 remove_edge 最后一条与 create_edge 第一条之间插入 `os._exit(1)`），重新启动项目 → 必须看到：① comp._port_routing[in_port] 回到 expand 前值（**没有变成"清一半"**）；② 子 listen_upper_file 仍然空（**没有写一半的脏数据**）；③ 4 地一致性断言重启后通过。因为我们用 RouteCache.commit() 一次性原子写，中途 crash 不会落盘任何东西。


##### 4.1.2 Collapse（折叠复合 C）— 严格 6 步完全反向（**三阶段 A/B/C 不可混合，同 expand 铁律**）

**collapse 阶段 A 收集用的关键函数说明（与 expand 的 collect_expand_morph_list 对称）**：

collapse 步骤 1 的 `collect_collapse_morph_list` 核心是**从所有子节点磁盘配置读真相**（不扫 scene！），然后调用 `resolve_or_create_comp_in_port` 来决定"这些 upstream 要映射到复合 C 的哪个 in_port"，**端口复用规则是关键**（能复用就不新增，防止 UI 锚点无限膨胀）：
```python
def resolve_or_create_comp_in_port(comp_id, upstream_node_id: str, upstream_out_port: str,
                                   target_child: str, target_child_port: str) -> str:
    """
    返回：已经存在的 in_port 名（如果满足"同一 upstream_node_id:upstream_out_port → 同一 target_child:target_child_port"就复用）
         否则新建 port_{idx}（并同步新增 comp C UI 的左侧输入锚点）
    关键点：不是"只要 upstream 相同就复用"——同一个 upstream 节点的不同 out_port 可能要进入不同 target_child 的不同 target_child_port，
            这时不能复用同一个 comp.in_port，必须新建！
    """
    routing = composite_manager._get_port_routing(comp_id)
    # 先找完全匹配（完全相同 = 复用）
    for in_port, entry in routing.get("input", {}).items():
        same_upstream = (entry.get("_upstream_node_id") == upstream_node_id
                         and entry.get("_upstream_out_port") == upstream_out_port)
        same_target   = (entry.get("target_node") == target_child
                         and entry.get("target_port") == target_child_port)
        if same_upstream and same_target:
            return in_port  # 完全匹配，直接复用
    # 不完全匹配：新建 port_{idx}
    existing_ports = set(routing.get("input", {}).keys())
    for idx in range(len(existing_ports) + 1):
        cand = f"port_{idx}" if idx > 0 else "port_0" if False else f"in_{idx}" if cand not in existing_ports:
            break
    # 同步新增 comp C UI 左侧的输入锚点（如果已经 expand 过锚点已经存在则跳过）
    composite_manager.ensure_comp_anchor_exists(comp_id, "input", cand)
    return cand
```

```
步骤 0 [基础环境：包事务 + 包 undo 宏]：与 expand 镜像（RouteCache.transaction + QUndoStack.beginMacro("Collapse " + comp_id)）

===========================================================================
阶段 A 【步骤 1 = 全量收集，此时所有子节点 UI 边 / 配置 / EdgeKey 全部完好未动】
===========================================================================
   morph_list = collect_collapse_morph_list(comp_id, membership_sm, edge_resolver, composite_manager, nodes_data_global)
   【collect_collapse_morph_list 内部逻辑（不能扫 scene，必须读磁盘 + MembershipSM）】：
     - 入向：for child_name in membership_sm(comp_id).child_node_names:
         child_cfg = disk_read(get_config_path(child_name))  # 读磁盘 node_config.json（不是内存缓存，防止脏值）
         · 默认端口：if child_cfg.get("listen_upper_file","") != "":
             upstream_node_id, upstream_out_port = edge_resolver.path_to_edge_endpoint(child_cfg["listen_upper_file"], nodes_data_global)
             # STALE 跳过：子节点配置里 upstream 不在 nodes_data（上游被删了）→ 跳过 morph，直接 purge 子 listen_upper_file
             in_port = resolve_or_create_comp_in_port(comp_id, upstream_node_id, upstream_out_port, child_name, "default")
             morph_list.append({
                 "direction":"input",
                 "upstream_node_id","upstream_out_port","source_output_path":child_cfg["listen_upper_file"],  # 写入 composite 的路径
                 "target_child_name":child_name,"target_child_port":"default",
                 "comp_in_port":in_port
             })
         · 多端口映射：for child_in_port, pm in child_cfg.get("port_mappings",{}).items():
             upstream_node_id, upstream_out_port = path_to_edge_endpoint(pm["source_output_path"])
             in_port = resolve_or_create_comp_in_port(comp_id, upstream_node_id, upstream_out_port, child_name, child_in_port)
             morph_list.append(...)
     - 出向：for child_name in child_node_names：对 child.out_connections 对称处理（source_output_path 反查 downstream_node_id / downstream_in_port）
   ★ 阶段 A 只做只读操作，不改任何磁盘/内存。
   ★ 所有"上游是谁 / 下游是谁 / 写 composite 什么路径 / 映射到 comp 的哪个 in_port"信息已保存到 morph_list 局部变量，后面清子配置不影响。

===========================================================================
阶段 B 【步骤 2 = 统一删除旧边 + 统一清子节点配置 + 视觉移除子节点】
        ★ 关键：整个阶段 B 里绝对不允许读子节点配置作为输入！要读只能去读 morph_list！
===========================================================================
   ① 先删 internal_child_out → 下游（出向）：
      for item in morph_list if direction=="output":
          remove_edge(item["child_source_name"], item["child_source_port"],
                      item["downstream_node_id"], item["downstream_in_port"],
                      _from_morph=True, _skip_undo_push=True)
          → 自动清 child.out_connections[source_port] + 下游 listen_upper_file
   ② 再删上游 → internal_child（入向）：
      for item in morph_list if direction=="input":
          remove_edge(item["upstream_node_id"], item["upstream_out_port"],
                      item["target_child_name"], item["target_child_port"],
                      _from_morph=True, _skip_undo_push=True)
          → 自动清 child.listen_upper_file / port_mappings[item.target_child_port]
   ③ 隐藏所有子节点 UI（hide/remove）→ 你提出的关键判断：子节点在画布不存在，所以子的边+配置必须清。

===========================================================================
阶段 C 【步骤 3 = 统一创建新边 external ↔ composite_C + 统一写 composite 配置（从 morph_list 读）】
===========================================================================
   ① 建 comp_C → 下游（出向）：
      for item in morph_list if direction=="output":
          create_edge(comp_id, item["comp_out_port"],
                      item["downstream_node_id"], item["downstream_in_port"],
                      _from_morph=True, _skip_undo_push=True)
          → comp._port_routing.output[comp_out_port] + composite.json.external_connections.output[comp_out_port]
   ② 建上游 → comp_C（入向）：【★ composite.json.source_output_path = morph_list[item]["source_output_path"] 原封不动抄】
      for item in morph_list if direction=="input":
          create_edge(item["upstream_node_id"], item["upstream_out_port"],
                      comp_id, item["comp_in_port"],
                      _from_morph=True, _skip_undo_push=True)
          → create_edge（target=comp_C + routing_type=COMPOSITE_INPUT）内部写：
              comp._port_routing.input[comp_in_port] = {
                  source_output_path: item["source_output_path"],  # 从阶段 A 抄的子 listen_upper_file 原路径
                  target_node: item["target_child_name"],
                  target_port: item["target_child_port"]
              }
            + 同步 composite.json.external_connections.input[comp_in_port]

步骤 4 [其余非 edge 行为]：子节点 UI hide、comp C UI show、连线端点几何重算

===========================================================================
步骤 5 [提交 + 失效缓存 + 互斥硬断言 + 4 地断言（与 expand 镜像）]
===========================================================================
   ① purge_stale_routes(comp_id) → 阶段 A 跳过的 STALE 子节点配置（上游被删的）此时从 composite.json 里也清理（因为 collapse 后 comp 不该再有它们的 in_port）
   ② RouteCache.commit() → 清子 + 写 comp 的原子落盘
   ③ 失效 comp + 所有子的 ConfigMtimeCache
   ④ 【互斥断言 · 折叠态】_assert_mutex_consistency(comp_id, morph_list)：
        comp._port_routing.input[in_port].source_output_path 非空 → 对应 target_child_name 的 listen_upper_file / port_mappings 必空
   ⑤ 4 地一致性断言 canonical == canvas_keys == mem_keys

步骤 6 [结束 undo 宏]：QUndoStack.endMacro() → Ctrl+Z 一次回到展开态（子边恢复 + comp 边删除 + 子 listen_upper_file 回到有值 + comp.in_port 被清）
```

**Collapse 崩溃回滚强制验收**：模拟 collapse 阶段 B 结束后 kill 进程（子边删完了，但 comp 新边还没建完）→ 重启后必须：① 子 listen_upper_file 回到 collapse 前值（**没有被永久清空**）；② composite.json.in_port 保持 collapse 前空值（**没有写一半脏数据**）；③ 4 地一致性断言通过。

**修改文件**：
- [composite_node.py](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/node/composite_node.py)：
  - 新增 `collect_expand_morph_list / collect_collapse_morph_list`（阶段 A 两个只读收集函数，不修改任何磁盘/内存）
  - 新增 `_assert_mutex_consistency(comp_id, morph_list)`：遍历刚 morph 的每条，校验互斥性（展开态→composite.in_port 空 + child 有值；折叠态→composite.in_port 有值 + child 空）
  - 新增 `resolve_or_create_comp_in_port`：collapse 时 comp 端口复用/新建的权威判定（完全匹配才复用，不同 upstream:out_port 或不同 target 必须新建）
  - `_expand_composite / _collapse_composite` 严格按上面 6 步三阶段分离改造；**彻底删除**所有「直接 EdgeItem() + scene.addItem / removeItem」、「anchor 平移 morph（保留原边对象）」这类保留旧边身份的代码。
- `ui/canvas/mixins/canvas_connections.py`：`create_edge / remove_edge` 签名新增 3 flag：`_from_morph / _skip_undo_push / _morph_skip_config`（互斥交接方案下 _morph_skip_config 默认 False，配置写必须跟随新边 create_edge 直接写，morph 前不提前写）。

**验收（Bug F 0 复现 + 互斥断言 0 失败 + 事务原子 0 损坏 + STALE 0 残留 = 阶段 4.1 通过）**：
- ① 折叠态连 a→C → expand 立刻开子配置：子 listen_upper_file **非空**，同时 composite.json.external_connections.input[in_port] **必空**（互斥，且字节级相等：子 listen_upper_file == expand 前 comp.in_port.source_output_path）。
- ② 展开态连 a→子 → 折叠立刻开 composite.json：in_port **非空**，同时子 listen_upper_file **必空**（互斥，且字节级相等：comp.in_port.source_output_path == collapse 前子 listen_upper_file）。
- ③ expand/collapse 各 200 次循环，`_assert_mutex_consistency` 零失败，**任何时候 composite.in_port 和对应 target_child:target_port 的 listen_upper_file 绝不同时非空指向同一 upstream**（互斥违背 = 立即 fail-fast，不允许进入用户态）。
- ④【事务原子】**expand 崩溃回滚专项**：在 expand 阶段 B 最后一条 remove_edge 与阶段 C 第一条 create_edge 之间插 `os._exit(1)` kill 进程 → 重启后：comp._port_routing[in_port] 回到 expand 前值（没有半清）；子 listen_upper_file 仍空（没有半写脏数据）；4 地一致性断言通过（RouteCache.commit 前 crash 不会落盘任何东西）。
- ⑤【事务原子】**collapse 崩溃回滚专项**：同样在 collapse 阶段 B 结束后 kill → 重启后：子 listen_upper_file 回到 collapse 前值（没有被永久清空）；composite.json.in_port 仍空（没有半写脏数据）；4 地一致性断言通过。
- ⑥【STALE 处理】手动删除上游节点 a（但 composite.json 仍保留 a 的路径）→ expand → 阶段 A 跳过该 in_port 不 morph（[MORPH-SKIP-STALE] 日志出现）→ expand 后该端口两边都空（互斥）→ purge_stale_routes 会把 composite.in_port 也清掉（无效路由永久不保留）。再折叠也不会出现任何 a→C 的边。

---

#### 阶段 4.2：删除链路双向深入钩子（约束 6，修 Bug G 删除后残留，1 天）

**修改文件**：
- [canvas_connections.py:L962-L1000 remove_edge → _clean_target_config / _clean_source_out_connections](file:///F:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/canvas/mixins/canvas_connections.py#L962-L1000) 外再套 2 个钩子（只在非 _from_morph 场景触发，因为 morph 场景的删除已经通过步骤 2 精确清干净了；这里是防止"用户手动删外部→comp"这类不走 expand/collapse 的删除场景遗漏）：
  - **钩子 1（删除 external→comp 时深入内部子节点清）**：
    ```python
    if edge._edge_key[0] == ROUTING_COMPOSITE_INPUT and not kwargs.get("_from_morph"):
        comp_id = edge._edge_key[2]; in_port = edge._edge_key[4]
        routing = composite_manager._get_port_routing(comp_id).get("input",{}).get(in_port)
        if routing:
            tgt_node = routing.get("target_node",""); tgt_port = routing.get("target_port","default")
            # 直接用 RouteCache 按精确端口清（不走 remove_edge 去删子节点 UI 边，因为子节点本来是隐藏的，UI 不关心）
            if tgt_port == "default":
                RouteCache.set_listen_upper_file(get_config_path(tgt_node), "")
            else:
                RouteCache.set_port_mapping(get_config_path(tgt_node), tgt_port, {})
    ```
  - **钩子 2（删除 external→internal_child 时反向清 comp routing）**：
    ```python
    target_membership = node_state_manager.get_state(target_name)["membership"]
    if target_membership == COMPOSITE_CHILD and not kwargs.get("_from_morph"):
        comp_id = node_state_manager._membership_sms[target_name].comp_id
        # 根据 target_node:target_port 反向查 comp._port_routing.input.*.target_node/target_port
        matched_in_port = composite_manager.reverse_lookup_input_routing(comp_id, target_node, target_port)
        if matched_in_port:
            RouteCache.clear_input_routing(comp_id, matched_in_port)
            # 同步 composite.json.external_connections.input 删除匹配项
    ```

**验收（Bug G 删除链路）**：
- 按用户描述的完整步骤执行 1 次：展开 C → a 连接收端子节点 → 折叠 → 删除 a→C → **立即打开内部子节点 config：listen_upper_file == ""**（不允许再残留，因为走了钩子 1）。
- 反向再执行：折叠态连 a→C → expand → 在展开态直接删 a→子的边 → 折叠 → composite.json.external_connections.input[in_port] == ""（钩子 2）。
- 互斥断言仍零失败（因为我们只清了一边，另一边本来就没有写）。

---

#### 阶段 4.3：4 地内存权威同步（约束 7，修"端口已连接"，1 天）

**目标**：把 morph 中所有「直接 scene.addItem / scene.removeItem + 手动绑 anchor」的代码全部删除，**任何时候改一条边的存在/不存在，必须走 canvas_connections.create_edge / remove_edge 同一个函数**，以保证这 4 个地方同时被更新：
1. `anchor._edges`（UI 锚点引用集合 —— 这是"端口已连接"提示的来源）
2. `NodeStateManager._edge_keys: set[EdgeKey]`（线条状态机）
3. `ConnectionSM.upstream_state + ConnectionSM._upstream_metadata`（节点状态机）
4. `RouteCache + 磁盘配置文件`（权威配置）

**修改文件**：
- `composite_node.py:_morph_composite`：
  - 删除所有 `EdgeItem(...) + scene.addItem / scene.removeItem` 的直接代码（全部改为步骤 2 的 remove_edge + 步骤 3 的 create_edge）
  - expand 完成后，`comp._morphed_edges = []` 之前：**对每条要丢弃的 morphed_edge，逐个显式调 canvas.connections.remove_edge(e, _from_morph=True, _skip_undo_push=True)**（不能只 scene.removeItem，否则 anchor._edges 留着 → 报"端口已连接"）。
  - 步骤 5 的"互斥一致性断言 + 4 地断言"必须硬执行，不能跳过；开发期开断言，灰度期关断言改为 logging.critical + 自动触发校准。

**验收（Bug G "端口已连接" 7 步循环零复现）**：
按用户步骤完整跑 10 次循环：
> 展开 C → a 连接收端子节点（成功）→ 折叠 → 删 a→C → 展开 → a 再连接收端子节点 → **必须允许连接成功，不提示"端口已连接"** → 折叠 → 展开 → 删边 → 连接 → 再折叠 → 再展开 → …… 循环 10 次，**任何一步都不出现"端口已连接"**。且每一步：
- composite.json / 子 node_config.json / anchor._edges / NodeStateManager._edge_keys **4 地完全没有任何同一 upstream→target 的残留**。

---

#### 阶段 4.4：与 EdgeCommands / undo/redo 对齐（约束 1 的宏机制 + 修 Bug D，0.5 天）

- `ui/core/commands/edge_commands.py`：undo 时不允许直接 `scene.removeItem`，改为调 `canvas.connections.remove_edge(edge, _from_undo=True)`；redo 调 `canvas.connections.create_edge(...)` 完整链路（与 expand/collapse 的 _from_morph 一样，走同一权威入口）。
- expand 的 QUndoMacro 必须包含「步骤 2 所有 remove_edge + 步骤 3 所有 create_edge」的 undo/redo 记录（用 _skip_undo_push=False，让 create_edge/remove_edge 内部自动往当前 macro 里 push sub-command，最后 endMacro 合成 1 个原子）。
- 验收：对 expand 后的 a→child 边按 Ctrl+Z 撤销 → undo 后：① anchor._edges 清；② ConnectionSM.upstream = DISCONNECTED；③ child.listen_upper_file 空；④ **composite.json.external_connections.input 也为空**（因为 expand macro 被整体 undo，回到展开前的折叠态，如果展开前 a→C 本就不存在，两边自然都空；如果展开前 a→C 存在，就会回到 composite.in_port 非空 + child 空的互斥折叠态）。

---

#### 阶段 4 总验收（8 条用例 0 失败 = 阶段通过）

1. Bug A 复合路由删除即时写（阶段 0 已验证） → 继续保持 0 复现
2. Bug E：框选 a+b（a→c 也存在）→ 右键清连线 → c.listen_upper_file 必空 + a→c UI 边必删
3. Bug F①：折叠态连 → 展开必看到子 listen_upper_file 有值 **且 composite.in_port 必空**（互斥）
4. Bug F②：展开态连子 → 折叠必看到 composite.json.external_connections 有值 **且 child.listen_upper_file 必空**（互斥）
5. **新增互斥一致性专项 200 次循环 0 失败**：expand/collapse 200 次循环（中间穿插手动连/删），`_assert_mutex_consistency` 零失败，任何时候 composite.in_port 和对应 target_node:target_port.listen_upper_file **绝不同时非空指向同一 upstream**。
6. Bug G：7 步循环 10 次 → 0 次 "端口已连接" 假阳性 + 每步 4 地无残留
7. Bug D：折叠丢失线条 100 次 expand/collapse 循环 + 中途手动连 → morph 后一致性断言零失败
8. undo/redo 对 expand 后的 internal 边执行 10 次循环 → 最终配置与初始完全相等（字节级 diff 0），且互斥断言继续 0 失败

### 阶段 5：Layout 文件去 edges 化（灰度 2 周后做，低风险前置都稳定才执行） **❌ [未开始]**

**目标**：`canvas_layout.json` 不再存 edges[] 结构 → edges 完全从 CanonicalEdgeSet 反推，彻底关闭 Bug C「layout 有边但配置没边」的路径。
- `save_layout`：`layout_data["edges"]` 只保留**折叠点几何数据 + EdgeKey**（不再存 source/target 等能推导出的信息）。
- `load_layout`：禁用 L349-410 的「从 layout edges 重建边」→ 改为：
  1. CanonicalEdgeResolver.infer_all_edges() 得到权威边集
  2. 对每条权威 edge 调 `create_edge(..., _from_layout_restore=True)`（走完整链路）
  3. edge 创建后，用它的 EdgeKey 去 layout_data["edges"] 里找折叠点数据 → **找不到就丢弃折叠点，不重建幽灵边**。
- save_layout 前强制调 `purge_all_invalid()`，确保不会把 ORPHANED 折叠点写进去。
- 验收：
  - 删除 canvas_layout.json → 重启项目 → 所有配置里的边完整出现，折叠点可能丢失（可接受）。
  - 10 次打开/关闭项目循环：CanonicalEdgeSet == CanvasEdgeSet 零 diff。

---

## 五、灰度发布 & 回滚策略（关键！）

| 阶段 | 运行模式 | 回滚方式 |
|---|---|---|
| 0 | 直接生效（立即写 composite.json，debounce 兜底还在） | 改 composite_node.py 把新增的 `_sync_routing_to_config` 那行注释掉 → 回退到纯 debounce |
| 1 | 直接生效（只加 EdgeKey，不做判定） | 回退 edge_key.py 修改 + EdgeItem._edge_key 赋值 |
| 2 | 直接生效（写 RouteCache 原子化） | 回退 writer 调用 → 改回 open/write 零散写 |
| 3 | **先灰度告警 2 周**：渲染门只打日志不 return；load_layout 只打印 diff 不删除 | 注释掉渲染门日志、load_layout diff 打印即可 |
| 3.2 | 灰度 2 周后：渲染门 return 不画 + load_layout 真删除 | 把 TODO 改回告警 + 注释 delete 调用 |
| 3.3 | 直接生效（只改 batch_clear_listen_config，旧方法作为 fallback 保留 1 周） | `canvas_batch_ops.py` 里把新 `edge_key_based_clear` 分支注释 → 走旧 open/write 兜底 |
| 4.1~4.4 | **灰度 1 周（2026-07-15 二次修订后策略）**：所有 morph 操作先走「**先删后建 + 配置互斥交接 6 步流程**」新机制，同时保留旧 morph 逻辑 parallel diff 执行一次（旧逻辑写临时内存不落盘），任一端不一致就打 `[MORPH-MUTEX-DIFF]` 严重告警；1 周 0 误报后再删旧代码。 | `composite_node.py` 顶部把 `USE_MORPH_MUTEX_SWITCH = True` 改成 False → 完全退回旧 anchor 平移 morph + 原双向写（仅开发期保留，灰度稳定 1 个月后删除旧代码分支） |
| 5 | 必须阶段 0~4 稳定 2 周再上 | 恢复「从 layout edges 重建边」的旧代码段 |

---

## 六、落地文件清单

| 路径 | 类型 | 作用 |
|---|---|---|
| `ui/core/edge/edge_key.py` | **新增** | EdgeKey 定义 + 5 类 routing_type 派生路径/配置目标解析函数 |
| `ui/core/edge/canonical_edge_resolver.py` | **新增** | 从所有配置读权威 CanonicalEdgeSet + mtime ConfigMtimeCache + purge_stale_routes |
| `ui/core/edge/edge_config_writer.py` | **新增** | 正向原子写/清配置（走 RouteCache），5 类 routing_type 全覆盖 |
| `ui/core/node/composite_node.py` | 修改 | 阶段 0（立即同步 composite.json）+ **阶段 4（二次修订：expand/collapse 6 步先删后建 morph + _assert_mutex_consistency 互斥断言函数 + QUndoMacro 包裹 + RouteCache 事务原子；删除所有直接 scene.addItem/removeItem + anchor morph 平移旧代码）** |
| `ui/canvas/items/edge_item.py` | 修改 | 阶段 1（加 _edge_key）+ 阶段 3（paint 渲染门 / 幽灵线条灰色虚线 + 警告三角 / set_render_gate_valid API） |
| `ui/canvas/mixins/canvas_connections.py` | 修改 | 阶段 1（create_edge 赋值 EdgeKey）+ 阶段 2（writer 原子化）+ **阶段 4（create_edge/remove_edge 新增 3 flag 签名：_from_morph / _skip_undo_push / _morph_skip_config；阶段 4.2 约束 6 非 morph 场景的 2 个删除链路深入钩子）** |
| `ui/canvas/mixins/canvas_batch_ops.py` | **修改（新增阶段 3.3 修 Bug E）** | batch_clear_listen_config：改走 EdgeKey 关联边收集 + plan_remove_edge 原子写；选中集跨边界双向清理（选中 start → 未选中下游也清；选中 end → 未选中上游 out_connections 也清） |
| `ui/canvas/mixins/canvas_edge_render_gate.py` | **新增（阶段 3c）** | QTimer 3s 定时扫描（失活暂停/激活延迟）+ 手动校准 QAction `action_calibrate_edges` + 渲染门批量打标 edge.set_render_gate_valid |
| `ui/canvas/mixins/canvas_layout.py` | 修改 | 阶段 3（load_layout 末尾 反向裁剪 ghost）+ 阶段 5（edges 去重/仅存折叠点） |
| `ui/core/commands/edge_commands.py` | 修改 | 阶段 2（undo/redo 走 create_edge/remove_edge 权威链路）+ **阶段 4.4（约束 1 QUndoMacro 子命令入栈机制；expand/collapse 6 步 morph 的 remove_edge/create_edge sub-command 自动并入当前宏；禁止 scene.addItem/removeItem 直操）** |
| `ui/core/state/node_state_manager.py` | 修改 | 阶段 1（存 `_edge_keys: set[EdgeKey]`）+ 阶段 3（`is_edge_valid_static` / is_edge_valid 渲染门核心判定）+ **阶段 4.3（约束 7：register_edge / unregister_edge / process_event 4 地同步权威入口；任何 morph 禁止绕开此 3 函数直接改内存集合）** |

---

## 七、成功指标（全部达成才算方案落地完成，2026-07-15 修订）

1. **Bug A 0 复现**：删除外部→复合 / 复合→外部边 100 次，每次 50ms 内关项目再打开，composite.json external_connections 立即清除 100%。
2. **Bug B 0 复现**：阶段 3.2 渲染门生效后，`[EDGE-GHOST DETECTED]` 日志 7 天 < 1 条。
3. **Bug C 0 复现**：阶段 3 load_layout 反向裁剪生效后，100 次重启项目，手动注入的幽灵边 100% 在 load_layout 里被删除。
4. **Bug D 0 复现**：expand/collapse 100 次循环 + 中途手动拖线，morph 后 4 地断言（canonical == canvas_keys == mem_keys）0 失败，没有"已连接"重复提示。
5. **Bug E 0 复现（2026-07-15 新增）**：a→c 存在 + 框选 a+b（c 不在选中集）→ 右键清除连线配置 → ① c.listen_upper_file == ""；② a→c UI 边不复存在；③ 反向场景（上游不在选中集）也同样清理。
6. **Bug F 0 复现（2026-07-15 新增）**：① 折叠态连 a→C，expand 后子 listen_upper_file 立即有值（字节级等于 composite.json 的 source_output_path）；② 展开态连 a→子，折叠后 composite.json.external_connections.input[in_port] 立即有值。
7. **Bug G 0 复现（2026-07-15 新增）**：用户描述的 7 步循环（展开连子 → 折叠 → 删除折叠态边 → 展开再连 → ……）执行 10 次完整循环，**0 次提示"端口已连接"假阳性**，且每一步的 composite.json / 子 node_config.json / anchor._edges / _edge_keys 4 地没有任何残留。
8. **一致性核心断言 100% 通过**：每次用户操作（connect / disconnect / expand / collapse / undo / redo / 重启 / 清除连线配置 / morph）后，`CanonicalEdgeSet == CanvasEdgeSet`。

---

## 八、落地实施补充（性能 / 容错 / 并发 / 体验 4 大类 12 项增强）

本章整合用户补充建议，按「实施方式 + 涉及文件 + 优先级（P0/P1/P2）」落地到方案中：

### 8.1 性能优化增补（P0：大项目必做，防主线程卡顿）

| 补充建议 | 实施方式 | 涉及文件 | 优先级 |
|---|---|---|---|
| ① 全局配置缓存池：记录每个节点配置文件 mtime，仅变更文件重新解析 EdgeKey | 新增 `ConfigMtimeCache {path: (mtime_ns, parsed_edge_refs)}`；`CanonicalEdgeResolver.infer_all_edges()` 先 `os.stat().st_mtime_ns` 比对缓存，**未变就跳过 json.load**；配置文件写回后主动失效对应条目。 | `ui/core/edge/canonical_edge_resolver.py`（新增 cache 模块） | **P0** |
| ② 3s 定时扫描：窗口失活（focusOut）时暂停，激活（focusIn）后延迟 500ms 合并执行，减少后台 IO | 在 NodeStateManager 启动扫描定时器时绑定 `parent_window.focusIn/focusOut`：失活 → `scan_timer.stop()`；激活 → `QTimer.singleShot(500, scan)`（避免 focus 快速切换抖动）。 | `ui/core/state/node_state_manager.py` | **P0** |
| ③ 大项目 infer_all_edges 异步执行：diff 完成后再刷新画布，避免主线程阻塞 | `infer_all_edges(project_path)` 放进 `QThreadPool / QThread`：子线程读 json + 算 CanonicalEdgeSet（不碰 UI）→ 主线程回调 `diff_and_refresh(missing, ghost)` 只做 addItem / removeItem（UI 操作必须主线程）；扫描期间 + 原子写期间加「文件读锁」（见 8.3），和用户写操作互斥。 | `ui/core/edge/canonical_edge_resolver.py` + `ui/core/state/node_state_manager.py` | **P0** |

### 8.2 完善异常容错（P0：避免损坏配置拖垮整个画布）

| 补充建议 | 实施方式 | 涉及文件 | 优先级 |
|---|---|---|---|
| ① 解析配置加 try-catch：损坏配置跳过 + 告警，不阻塞加载 | 每读 1 个 `node_config.json / composite.json` 外层包 `(json.JSONDecodeError, OSError, KeyError)`；异常时：`logger.critical("[EDGE-CONFIG-BROKEN] skip %s err=%s", path, repr(e))` → 在 `_broken_paths: set` 里记录，不把它的边放进 CanonicalEdgeSet（下次 scan 再次尝试解析，用户修好配置后自动恢复）。 | `canonical_edge_resolver.py` | **P0** |
| ② 定时自动清理无效路由：子节点删除、路径失效的 external_connections 自动清除（**防止配置永久膨胀**） | 在 `purge_all_invalid()` 里加反向清理钩子：<br>a) COMPOSITE_INPUT/OUTPUT：`_port_routing[port]` 里的节点名，如果 **不在 nodes_data / 不在 composite 子节点列表 / output.json 文件不存在** → 立即 `clear_input_routing / clear_output_routing` + 同步 composite.json；<br>b) STANDALONE：B.listen_upper_file 指向的路径不存在 → 立即 del listen_upper_file + 同步上游 out_connections。 | `canonical_edge_resolver.py` 的 `purge_stale_routes()` 钩子 + `edge_config_writer.clear_edge_config()` | **P1** |
| ③ EdgeKey 冲突处理规则：以最新写入的配置为准，删除旧冲突记录 | `create_edge / write_edge_config` 写入前先算要生成的 EdgeKey → 如果 `edge_keys 中已存在同 routing_type + up/down 节点 + 端口`：① 先调 `clear_edge_config(old_key)` 清旧配置（级联清 out_connections）；② 再写新配置；③ 日志 `[EDGE-KEY-CONFLICT] resolved by replacing old=%s new=%s"`。 | `edge_config_writer.py` + `canvas_connections.py` | **P1** |

### 8.3 并发编辑 & 文件锁（P0：防止 json 半写损坏）

| 补充建议 | 实施方式 | 涉及文件 | 优先级 |
|---|---|---|---|
| 项目文件读写锁：定时扫描、用户操作、自动保存互斥，避免并发写 json 导致文件损坏 | 新增全局 `ProjectFileLock`（挂在 parent_window，项目级单例）：<br>- 写操作（用户 connect/disconnect、阶段 2 writer.flush_atomic、自动保存 layout）→ **排他写锁**；<br>- 读操作（8.1 异步 infer_all_edges 扫描、节点入画布补边）→ **共享读锁**；<br>- 实现用 `threading.RWLock（fasteners 包或手写 Condition 双计数器）`，超时 1s 拿不到就打 `[EDGE-LOCK-CONTENTION]`，重试 3 次放弃并告警（不崩，下次扫描兜底）。<br>**关键**：写前先 `rename(old, old.tmp)` + 写 tmp + `os.replace(tmp, old)`，断电只丢 tmp 不损原文件（现在代码是直接 open(w)，会半写损坏 → 一起改掉）。 | `ui/core/utils/project_file_lock.py`（新增）+ 所有 `json.dump(open(w))` 处统一通过锁 + atomic replace 写 | **P0** |

### 8.4 用户体验兜底（P1：让用户感知 + 可手动干预）

| 补充建议 | 实施方式 | 涉及文件 | 优先级 |
|---|---|---|---|
| ① 画布增加「校准线条」手动按钮：主动触发 CanonicalEdgeSet 全量矫正 | 在画布右键菜单 / 主菜单增加 `QAction("校准线条 & 修复幽灵边")` → 点击后：<br>1) 强制清 ConfigMtimeCache 全量重读；<br>2) `purge_stale_routes()` 清无效路由；<br>3) `infer_all_edges + diff_and_refresh` 补/裁边；<br>4) 结束后弹 `QMessageBox` 报告"补了 X 条，删了 Y 条幽灵边，清了 Z 条无效路由"。 | `ui/canvas/mixins/canvas_context_menu.py` 或主窗口 action 栏 | **P1** |
| ② layout 几何数据兼容备份：EdgeKey 匹配失败时**保留基础线条位置**，不直接清空 | 阶段 5「layout 去 edges 化」时：保存旧 layout 时，**除了存折叠点 + EdgeKey**，额外留 `fallback_geometry_edges: [{source_ref, target_ref, up_port, dn_port, fold_points}]`；加载时如果 EdgeKey 在新推导集合里找不到 → 不丢弃，按 fallback_geometry_edges **临时创建一条灰边 + tooltip"此线条未在配置中记录，点击校准线条按钮修复"**，等用户点校准后再决定删不删（防止用户折叠点几何信息永久丢失）。 | `canvas_layout.py` save_layout / load_layout | **P1** |
| ③ 幽灵线条灰度期给用户弹窗提示：而非仅后台日志 | 阶段 3 渲染门告警 + load_layout diff：<br>- 如果单次 diff ghost > 3 条或 missing > 3 条 → 主窗口 `statusBar().showMessage("检测到 %d 条幽灵线条/缺失线条，建议点击【校准线条】按钮修复", 15000)`；<br>- 如果连续 3 次 3s 扫描都有同样的 `[EDGE-GHOST DETECTED]` → 弹 `QMessageBox.information` 非阻塞提示（带「不再提示」复选框存 settings，专业用户可关）。 | `ui/core/state/node_state_manager.py` 扫描完成钩子 + `parent_window` 状态栏/弹窗 | **P1** |

### 8.5 本章落地时序

```
阶段 0 修 Bug A → 阶段 1 EdgeKey → 阶段 2 原子写 + [8.3 P0 项目文件锁 + atomic replace]
                                                          ↓
                      阶段 3 反向闭环 + 渲染门 + [8.1 P0 缓存池/失活暂停/异步扫描]
                                               + [8.2 P0 损坏配置跳过]
                                                          ↓
                      阶段 4 morph 修复 → 阶段 5 layout 去 edges 化 + [8.4 P1 三个体验兜底]
                                               + [8.2 P1 无效路由自清理 / EdgeKey 冲突]
```

> 注：8.3 的「atomic replace 写文件」和 8.1 的「mtime 缓存池」要尽量前置到阶段 0/1 —— 它们是通用基础设施，能避免方案实施过程中引入的新写入路径造成并发损坏 / 大项目卡顿。

